#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AICostMonitor SDK - 零侵入API成本追踪

使用方法：
    from aicostmonitor import track
    
    # 自动追踪OpenAI调用
    track.openai(api_key="sk-...")
    response = client.chat.completions.create(...)
    
    # 或使用装饰器
    @track.cost
    def my_ai_function():
        ...
"""

import os
import json
import time
import functools
import threading
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import requests

# 全局配置
_config = {
    "api_url": os.getenv("AICOSTMONITOR_URL", "http://106.13.110.26"),
    "api_key": os.getenv("AICOSTMONITOR_API_KEY", ""),
    "user_id": os.getenv("AICOSTMONITOR_USER_ID", "default"),
    "enabled": True,
    "debug": False
}


@dataclass
class UsageRecord:
    """使用记录"""
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cost_cny: float
    metadata: Dict[str, Any]


class AICostMonitor:
    """AI成本监控器"""
    
    def __init__(self, api_url: str = None, api_key: str = None, user_id: str = None):
        self.api_url = api_url or _config["api_url"]
        self.api_key = api_key or _config["api_key"]
        self.user_id = user_id or _config["user_id"]
        self._buffer = []
        self._lock = threading.Lock()
    
    def record(self, provider: str, model: str, 
               input_tokens: int, output_tokens: int,
               metadata: Dict = None) -> bool:
        """记录API调用"""
        if not _config["enabled"]:
            return False
        
        try:
            response = requests.post(
                f"{self.api_url}/api/record",
                data={
                    "provider": provider,
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "metadata": json.dumps(metadata or {})
                },
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if _config["debug"]:
                    print(f"[AICostMonitor] {provider}/{model}: "
                          f"${result.get('cost_usd', 0):.6f} "
                          f"(¥{result.get('cost_cny', 0):.4f})")
                return True
        except Exception as e:
            if _config["debug"]:
                print(f"[AICostMonitor] Error: {e}")
        
        return False
    
    def get_summary(self, days: int = 30) -> Dict:
        """获取成本摘要"""
        try:
            response = requests.get(
                f"{self.api_url}/api/summary",
                params={"days": days},
                timeout=5
            )
            return response.json()
        except Exception as e:
            if _config["debug"]:
                print(f"[AICostMonitor] Error: {e}")
            return {}
    
    def get_cost(self, provider: str, model: str,
                 input_tokens: int, output_tokens: int) -> Dict:
        """计算成本（不记录）"""
        try:
            response = requests.get(
                f"{self.api_url}/api/pricing/{provider}",
                timeout=5
            )
            if response.status_code == 200:
                pricing = response.json().get("pricing", {}).get(model, {})
                input_price = pricing.get("input_price_per_1k", 0)
                output_price = pricing.get("output_price_per_1k", 0)
                
                cost_usd = (input_tokens / 1000 * input_price + 
                           output_tokens / 1000 * output_price)
                
                # 获取汇率
                rate_response = requests.get(
                    f"{self.api_url}/api/exchange-rate",
                    timeout=5
                )
                rate = rate_response.json().get("usd_to_cny", 7.0)
                
                return {
                    "cost_usd": cost_usd,
                    "cost_cny": cost_usd * rate
                }
        except Exception as e:
            if _config["debug"]:
                print(f"[AICostMonitor] Error: {e}")
        
        return {"cost_usd": 0, "cost_cny": 0}


class OpenAITracker:
    """OpenAI自动追踪器"""
    
    def __init__(self, monitor: AICostMonitor, api_key: str = None):
        self.monitor = monitor
        self.api_key = api_key
        self._original_openai = None
        self._client = None
    
    def patch(self):
        """自动追踪OpenAI调用"""
        try:
            import openai
            
            # 保存原始方法
            self._original_openai = openai
            
            # 包装ChatCompletion
            original_create = openai.chat.completions.create
            
            @functools.wraps(original_create)
            def wrapped_create(*args, **kwargs):
                # 调用原始方法
                response = original_create(*args, **kwargs)
                
                # 记录使用量
                if hasattr(response, 'usage'):
                    model = kwargs.get('model', 'gpt-3.5-turbo')
                    self.monitor.record(
                        provider="openai",
                        model=model,
                        input_tokens=response.usage.prompt_tokens,
                        output_tokens=response.usage.completion_tokens,
                        metadata={"stream": False}
                    )
                
                return response
            
            openai.chat.completions.create = wrapped_create
            
            if _config["debug"]:
                print("[AICostMonitor] OpenAI tracking enabled")
            
            return True
        except ImportError:
            if _config["debug"]:
                print("[AICostMonitor] OpenAI not installed")
            return False
    
    def unpatch(self):
        """取消追踪"""
        if self._original_openai:
            import openai
            openai.chat.completions.create = self._original_openai.chat.completions.create


class AnthropicTracker:
    """Anthropic自动追踪器"""
    
    def __init__(self, monitor: AICostMonitor, api_key: str = None):
        self.monitor = monitor
        self.api_key = api_key
    
    def patch(self):
        """自动追踪Anthropic调用"""
        try:
            import anthropic
            
            original_create = anthropic.Anthropic.messages.create
            
            @functools.wraps(original_create)
            def wrapped_create(self_anthropic, *args, **kwargs):
                response = original_create(self_anthropic, *args, **kwargs)
                
                if hasattr(response, 'usage'):
                    model = kwargs.get('model', 'claude-3-sonnet')
                    self.monitor.record(
                        provider="anthropic",
                        model=model,
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens
                    )
                
                return response
            
            anthropic.Anthropic.messages.create = wrapped_create
            
            if _config["debug"]:
                print("[AICostMonitor] Anthropic tracking enabled")
            
            return True
        except ImportError:
            return False


def cost(func: Callable = None, provider: str = "auto", model: str = "auto"):
    """
    装饰器：自动追踪函数的API成本
    
    使用方法：
        @track.cost
        def call_openai(prompt):
            return openai.chat.completions.create(...)
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = f(*args, **kwargs)
            elapsed = time.time() - start_time
            
            # 尝试从结果中提取usage信息
            if hasattr(result, 'usage'):
                monitor.record(
                    provider=provider if provider != "auto" else "unknown",
                    model=model if model != "auto" else "unknown",
                    input_tokens=getattr(result.usage, 'prompt_tokens', 0),
                    output_tokens=getattr(result.usage, 'completion_tokens', 0),
                    metadata={"elapsed_seconds": elapsed}
                )
            
            return result
        return wrapper
    
    if func:
        return decorator(func)
    return decorator


# 全局实例
monitor = AICostMonitor()

# 导出的track对象
class TrackNamespace:
    """追踪命名空间"""
    
    def __init__(self):
        self._openai_tracker = None
        self._anthropic_tracker = None
    
    def openai(self, api_key: str = None):
        """启用OpenAI追踪"""
        self._openai_tracker = OpenAITracker(monitor, api_key)
        return self._openai_tracker.patch()
    
    def anthropic(self, api_key: str = None):
        """启用Anthropic追踪"""
        self._anthropic_tracker = AnthropicTracker(monitor, api_key)
        return self._anthropic_tracker.patch()
    
    def record(self, provider: str, model: str,
               input_tokens: int, output_tokens: int,
               metadata: Dict = None):
        """手动记录"""
        return monitor.record(provider, model, input_tokens, output_tokens, metadata)
    
    def cost(self, func: Callable = None, **kwargs):
        """成本追踪装饰器"""
        return cost(func, **kwargs)
    
    def summary(self, days: int = 30):
        """获取摘要"""
        return monitor.get_summary(days)
    
    def get_cost(self, provider: str, model: str,
                 input_tokens: int, output_tokens: int):
        """计算成本"""
        return monitor.get_cost(provider, model, input_tokens, output_tokens)


track = TrackNamespace()

# 便捷函数
def init(api_url: str = None, api_key: str = None, user_id: str = None, debug: bool = False):
    """初始化AICostMonitor"""
    global monitor, _config
    
    if api_url:
        _config["api_url"] = api_url
    if api_key:
        _config["api_key"] = api_key
    if user_id:
        _config["user_id"] = user_id
    _config["debug"] = debug
    
    monitor = AICostMonitor(api_url, api_key, user_id)
    
    if debug:
        print(f"[AICostMonitor] Initialized with {api_url}")


def auto_track():
    """自动追踪所有已安装的AI库"""
    enabled = []
    
    try:
        import openai
        if track.openai():
            enabled.append("openai")
    except ImportError:
        pass
    
    try:
        import anthropic
        if track.anthropic():
            enabled.append("anthropic")
    except ImportError:
        pass
    
    if _config["debug"]:
        print(f"[AICostMonitor] Auto-tracking enabled for: {enabled}")
    
    return enabled


# 导入统一API模块
from .unified_api import (
    LoadBalancer,
    CacheManager,
    FailoverManager,
    UnifiedClient
)

__all__ = [
    'track', 
    'monitor', 
    'init', 
    'auto_track', 
    'cost', 
    'AICostMonitor',
    'LoadBalancer',
    'CacheManager',
    'FailoverManager',
    'UnifiedClient'
]
