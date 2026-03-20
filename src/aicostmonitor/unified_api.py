#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一API接口 - 兼容OpenAI SDK
支持多提供商，统一调用方式
"""

import os
import time
import hashlib
import threading
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import requests


@dataclass
class APIKey:
    """API密钥配置"""
    key: str
    provider: str
    weight: int = 1
    health: bool = True
    last_used: float = 0
    fail_count: int = 0
    total_requests: int = 0


class LoadBalancer:
    """负载均衡器 - 支持多API Key轮询"""
    
    def __init__(self, strategy: str = "round_robin"):
        """
        初始化负载均衡器
        
        Args:
            strategy: 负载均衡策略
                - round_robin: 轮询（默认）
                - weighted: 加权轮询
                - least_used: 最少使用
                - random: 随机
        """
        self.strategy = strategy
        self.api_keys: Dict[str, List[APIKey]] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._round_robin_index: Dict[str, int] = {}
    
    def add_key(self, provider: str, api_key: str, weight: int = 1):
        """添加API密钥"""
        if provider not in self.api_keys:
            self.api_keys[provider] = []
            self._locks[provider] = threading.Lock()
            self._round_robin_index[provider] = 0
        
        self.api_keys[provider].append(APIKey(
            key=api_key,
            provider=provider,
            weight=weight
        ))
    
    def get_key(self, provider: str) -> Optional[APIKey]:
        """获取下一个可用的API密钥"""
        if provider not in self.api_keys:
            return None
        
        with self._locks[provider]:
            keys = [k for k in self.api_keys[provider] if k.health]
            
            if not keys:
                # 所有密钥都不健康，尝试重置
                for k in self.api_keys[provider]:
                    k.health = True
                    k.fail_count = 0
                keys = self.api_keys[provider]
            
            if not keys:
                return None
            
            selected = self._select_key(provider, keys)
            selected.last_used = time.time()
            selected.total_requests += 1
            
            return selected
    
    def _select_key(self, provider: str, keys: List[APIKey]) -> APIKey:
        """根据策略选择密钥"""
        if self.strategy == "round_robin":
            index = self._round_robin_index[provider] % len(keys)
            self._round_robin_index[provider] += 1
            return keys[index]
        
        elif self.strategy == "weighted":
            # 加权随机选择
            import random
            total_weight = sum(k.weight for k in keys)
            r = random.uniform(0, total_weight)
            current = 0
            for key in keys:
                current += key.weight
                if r <= current:
                    return key
            return keys[0]
        
        elif self.strategy == "least_used":
            # 选择使用次数最少的
            return min(keys, key=lambda k: k.total_requests)
        
        else:  # random
            import random
            return random.choice(keys)
    
    def mark_failure(self, provider: str, api_key: str):
        """标记密钥失败"""
        with self._locks[provider]:
            for key in self.api_keys[provider]:
                if key.key == api_key:
                    key.fail_count += 1
                    if key.fail_count >= 3:
                        key.health = False
                    break
    
    def mark_success(self, provider: str, api_key: str):
        """标记密钥成功"""
        with self._locks[provider]:
            for key in self.api_keys[provider]:
                if key.key == api_key:
                    key.fail_count = 0
                    key.health = True
                    break
    
    def get_stats(self) -> Dict[str, Any]:
        """获取负载均衡统计"""
        stats = {}
        for provider, keys in self.api_keys.items():
            stats[provider] = {
                "total_keys": len(keys),
                "healthy_keys": sum(1 for k in keys if k.health),
                "total_requests": sum(k.total_requests for k in keys),
                "keys": [
                    {
                        "key": k.key[:8] + "..." if len(k.key) > 8 else k.key,
                        "health": k.health,
                        "fail_count": k.fail_count,
                        "total_requests": k.total_requests,
                        "weight": k.weight
                    }
                    for k in keys
                ]
            }
        return stats


class CacheManager:
    """缓存管理器 - 相同请求缓存结果"""
    
    def __init__(self, enabled: bool = True, ttl: int = 3600, max_size: int = 1000):
        """
        初始化缓存管理器
        
        Args:
            enabled: 是否启用缓存
            ttl: 缓存过期时间（秒）
            max_size: 最大缓存条数
        """
        self.enabled = enabled
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def _generate_key(self, provider: str, model: str, messages: List[Dict], 
                      **kwargs) -> str:
        """生成缓存键"""
        content = f"{provider}:{model}:{str(messages)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, provider: str, model: str, messages: List[Dict], 
            **kwargs) -> Optional[Dict]:
        """获取缓存"""
        if not self.enabled:
            return None
        
        key = self._generate_key(provider, model, messages, **kwargs)
        
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry["timestamp"] < self.ttl:
                    self._stats["hits"] += 1
                    entry["access_count"] += 1
                    return entry["response"]
                else:
                    # 缓存过期，删除
                    del self._cache[key]
            
            self._stats["misses"] += 1
            return None
    
    def set(self, provider: str, model: str, messages: List[Dict], 
            response: Dict, **kwargs):
        """设置缓存"""
        if not self.enabled:
            return
        
        key = self._generate_key(provider, model, messages, **kwargs)
        
        with self._lock:
            # 检查是否需要清理
            if len(self._cache) >= self.max_size:
                self._evict()
            
            self._cache[key] = {
                "response": response,
                "timestamp": time.time(),
                "access_count": 0
            }
    
    def _evict(self):
        """清理缓存（LRU策略）"""
        if not self._cache:
            return
        
        # 删除最旧的条目
        sorted_keys = sorted(
            self._cache.keys(),
            key=lambda k: (self._cache[k]["access_count"], self._cache[k]["timestamp"])
        )
        
        # 删除25%的条目
        evict_count = max(1, len(sorted_keys) // 4)
        for key in sorted_keys[:evict_count]:
            del self._cache[key]
            self._stats["evictions"] += 1
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "enabled": self.enabled,
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": f"{hit_rate:.2f}%",
                "evictions": self._stats["evictions"]
            }


class FailoverManager:
    """故障转移管理器"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        初始化故障转移管理器
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retries": 0,
            "failovers": 0
        }
        self._lock = threading.Lock()
    
    def execute_with_failover(self, func, *args, fallback_func=None, **kwargs) -> Any:
        """
        执行函数，支持故障转移
        
        Args:
            func: 主函数
            fallback_func: 备用函数
            *args, **kwargs: 函数参数
        """
        with self._lock:
            self._stats["total_requests"] += 1
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                with self._lock:
                    self._stats["successful_requests"] += 1
                return result
            except Exception as e:
                last_error = e
                with self._lock:
                    self._stats["retries"] += 1
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        
        # 主函数失败，尝试备用函数
        if fallback_func:
            try:
                result = fallback_func(*args, **kwargs)
                with self._lock:
                    self._stats["successful_requests"] += 1
                    self._stats["failovers"] += 1
                return result
            except Exception as e:
                last_error = e
        
        with self._lock:
            self._stats["failed_requests"] += 1
        
        raise last_error
    
    def get_stats(self) -> Dict[str, Any]:
        """获取故障转移统计"""
        with self._lock:
            success_rate = (
                self._stats["successful_requests"] / self._stats["total_requests"] * 100
                if self._stats["total_requests"] > 0 else 0
            )
            
            return {
                **self._stats,
                "success_rate": f"{success_rate:.2f}%"
            }


class UnifiedClient:
    """统一API客户端 - 兼容OpenAI SDK"""
    
    def __init__(self, load_balancer: LoadBalancer = None, 
                 cache: CacheManager = None,
                 failover: FailoverManager = None,
                 monitor_url: str = "http://106.13.110.26"):
        """
        初始化统一客户端
        
        Args:
            load_balancer: 负载均衡器
            cache: 缓存管理器
            failover: 故障转移管理器
            monitor_url: 监控服务URL
        """
        self.load_balancer = load_balancer or LoadBalancer()
        self.cache = cache or CacheManager()
        self.failover = failover or FailoverManager()
        self.monitor_url = monitor_url
        
        # 提供商配置
        self.providers = {
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
            },
            "deepseek": {
                "base_url": "https://api.deepseek.com/v1",
                "models": ["deepseek-chat", "deepseek-coder"]
            },
            "qianfan": {
                "base_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
                "models": ["ernie-4.0-8k", "ernie-3.5-8k"]
            }
        }
    
    @property
    def chat(self):
        """兼容OpenAI SDK的chat接口"""
        return ChatNamespace(self)
    
    @property
    def completions(self):
        """兼容OpenAI SDK的completions接口"""
        return CompletionsNamespace(self)


class ChatNamespace:
    """Chat命名空间"""
    
    def __init__(self, client: UnifiedClient):
        self.client = client
        self.completions = ChatCompletions(client)


class ChatCompletions:
    """Chat Completions接口"""
    
    def __init__(self, client: UnifiedClient):
        self.client = client
    
    def create(self, model: str, messages: List[Dict], 
               provider: str = None, **kwargs) -> Dict:
        """
        创建Chat Completion（兼容OpenAI SDK）
        
        Args:
            model: 模型名称
            messages: 消息列表
            provider: 提供商（可选，自动推断）
            **kwargs: 其他参数（temperature, max_tokens等）
        """
        # 自动推断提供商
        if not provider:
            provider = self._infer_provider(model)
        
        # 检查缓存
        cached = self.client.cache.get(provider, model, messages, **kwargs)
        if cached:
            return cached
        
        # 获取API密钥
        api_key = self.client.load_balancer.get_key(provider)
        if not api_key:
            raise ValueError(f"No API key available for provider: {provider}")
        
        # 执行请求
        def make_request():
            return self._call_api(provider, api_key.key, model, messages, **kwargs)
        
        try:
            response = self.client.failover.execute_with_failover(make_request)
            
            # 标记成功
            self.client.load_balancer.mark_success(provider, api_key.key)
            
            # 设置缓存
            self.client.cache.set(provider, model, messages, response, **kwargs)
            
            # 记录监控
            self._record_usage(provider, model, response)
            
            return response
        
        except Exception as e:
            # 标记失败
            self.client.load_balancer.mark_failure(provider, api_key.key)
            raise
    
    def _infer_provider(self, model: str) -> str:
        """根据模型推断提供商"""
        if model.startswith("gpt"):
            return "openai"
        elif model.startswith("deepseek"):
            return "deepseek"
        elif model.startswith("ernie"):
            return "qianfan"
        else:
            return "openai"  # 默认
    
    def _call_api(self, provider: str, api_key: str, model: str, 
                  messages: List[Dict], **kwargs) -> Dict:
        """调用提供商API"""
        config = self.client.providers.get(provider)
        if not config:
            raise ValueError(f"Unknown provider: {provider}")
        
        url = f"{config['base_url']}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        return response.json()
    
    def _record_usage(self, provider: str, model: str, response: Dict):
        """记录使用量到监控服务"""
        try:
            usage = response.get("usage", {})
            requests.post(
                f"{self.client.monitor_url}/api/record",
                data={
                    "provider": provider,
                    "model": model,
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0)
                },
                timeout=2
            )
        except Exception:
            pass  # 监控失败不影响主流程


class CompletionsNamespace:
    """Completions命名空间（兼容旧版OpenAI SDK）"""
    
    def __init__(self, client: UnifiedClient):
        self.client = client
    
    def create(self, model: str, prompt: str, provider: str = None, **kwargs):
        """创建Completion"""
        # 转换为Chat格式
        messages = [{"role": "user", "content": prompt}]
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            provider=provider,
            **kwargs
        )


# 导出
__all__ = [
    'LoadBalancer',
    'CacheManager', 
    'FailoverManager',
    'UnifiedClient'
]
