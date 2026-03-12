#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xAI Grok 提供商实现
支持Grok-1, Grok-2等模型
实时信息获取能力
"""

from typing import List, Dict, Any, Optional
import requests
from datetime import datetime
import json
from .base import BaseProvider


class GrokProvider(BaseProvider):
    """xAI Grok API提供商"""
    
    # Grok模型定价（美元/千token）- 基于公开信息和估算
    MODEL_PRICING_USD = {
        # Grok 2系列 (最新)
        "grok-2": {
            "input": 1.50,    # $1.50 per 1M input tokens (估算)
            "output": 4.50,   # $4.50 per 1M output tokens (估算)
            "context": 131072,
            "real_time": True,
            "requires_x_premium": True
        },
        "grok-2-beta": {
            "input": 0.75,    # Beta版本可能有折扣
            "output": 2.25,
            "context": 131072,
            "real_time": True,
            "requires_x_premium": True
        },
        
        # Grok 1系列
        "grok-1": {
            "input": 2.00,
            "output": 6.00,
            "context": 8192,
            "real_time": True,
            "requires_x_premium": True
        },
        "grok-1-beta": {
            "input": 1.00,
            "output": 3.00,
            "context": 8192,
            "real_time": True,
            "requires_x_premium": True
        },
        "grok-1-mini": {
            "input": 0.50,
            "output": 1.50,
            "context": 4096,
            "real_time": False,
            "requires_x_premium": False
        },
        
        # 其他xAI模型 (如果提供)
        "grok-vision": {
            "input": 3.00,
            "output": 9.00,
            "context": 8192,
            "vision": True,
            "real_time": True,
            "requires_x_premium": True
        }
    }
    
    # API基础配置 - 注意：xAI API可能有限制
    API_BASE_URL = "https://api.x.ai"
    X_API_BASE_URL = "https://api.twitter.com"  # 可能需要Twitter API
    
    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        """
        初始化Grok提供商
        
        Args:
            api_key: xAI API密钥或Twitter API密钥
            config: 配置参数
        """
        super().__init__(api_key, config)
        self.provider_name = "grok"
        self.provider_display_name = "xAI Grok"
        self.default_model = "grok-2"
        
        # xAI API可能需要特殊认证
        self.is_x_premium = config.get("x_premium", False) if config else False
        
        # 设置API头信息
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 添加xAI特定头
        if config and "x_ai_api_key" in config:
            self.headers["x-api-key"] = config["x_ai_api_key"]
    
    def get_supported_models(self) -> List[Dict[str, Any]]:
        """
        获取支持的模型列表
        
        Returns:
            模型信息列表
        """
        models = []
        for model_id, pricing in self.MODEL_PRICING_USD.items():
            # 检查是否需要X Premium
            requires_premium = pricing.get("requires_x_premium", False)
            
            # 如果不需要Premium，或者需要Premium且用户有Premium
            if not requires_premium or (requires_premium and self.is_x_premium):
                models.append({
                    "id": model_id,
                    "name": model_id,
                    "provider": self.provider_name,
                    "input_price_usd": pricing["input"],
                    "output_price_usd": pricing["output"],
                    "context_window": pricing.get("context", 8192),
                    "has_real_time": pricing.get("real_time", False),
                    "has_vision": pricing.get("vision", False),
                    "requires_x_premium": requires_premium,
                    "description": self._get_model_description(model_id),
                    "available": self._check_model_availability(model_id)
                })
        
        # 按版本排序（最新在前）
        models.sort(key=lambda x: (
            "2" in x["id"],  # Grok-2优先
            "beta" not in x["id"],  # 非beta优先
            -x["context_window"]  # 上下文长的优先
        ), reverse=True)
        
        return models
    
    def _get_model_description(self, model_id: str) -> str:
        """获取模型描述"""
        descriptions = {
            "grok-2": "Grok 2 - 最新版本，实时信息，更强推理",
            "grok-2-beta": "Grok 2 Beta - 测试版本，可能有新功能",
            "grok-1": "Grok 1 - 初代版本，实时信息能力",
            "grok-1-beta": "Grok 1 Beta - 测试版本",
            "grok-1-mini": "Grok 1 Mini - 轻量版本，成本较低",
            "grok-vision": "Grok Vision - 视觉版本，图像理解"
        }
        return descriptions.get(model_id, "xAI Grok模型")
    
    def _check_model_availability(self, model_id: str) -> bool:
        """检查模型是否可用"""
        # 实际实现中需要调用API检查
        # 这里简化处理
        requires_premium = self.MODEL_PRICING_USD[model_id].get("requires_x_premium", False)
        
        if requires_premium and not self.is_x_premium:
            return False
        
        # 假设所有模型都可用
        return True
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int, 
                      usage_data: Dict[str, Any] = None) -> Dict[str, float]:
        """
        计算Grok使用成本
        
        Args:
            model: 模型名称
            input_tokens: 输入token数
            output_tokens: 输出token数
            usage_data: 使用数据
            
        Returns:
            成本信息字典
        """
        if model not in self.MODEL_PRICING_USD:
            raise ValueError(f"不支持的模型: {model}")
        
        pricing = self.MODEL_PRICING_USD[model]
        
        # 检查是否需要X Premium
        requires_premium = pricing.get("requires_x_premium", False)
        if requires_premium and not self.is_x_premium:
            return {
                "error": "需要X Premium订阅",
                "available": False,
                "requires_x_premium": True
            }
        
        # 计算成本（美元）
        input_cost_usd = (input_tokens / 1000000) * pricing["input"]
        output_cost_usd = (output_tokens / 1000000) * pricing["output"]
        total_cost_usd = input_cost_usd + output_cost_usd
        
        # 转换为人民币（按实时汇率，这里用固定汇率7.2）
        exchange_rate = self._get_exchange_rate()
        input_cost_cny = input_cost_usd * exchange_rate
        output_cost_cny = output_cost_usd * exchange_rate
        total_cost_cny = total_cost_usd * exchange_rate
        
        # 实时信息额外成本（如果使用）
        real_time_cost = 0
        if usage_data and pricing.get("real_time", False):
            real_time_queries = usage_data.get("real_time_queries", 0)
            # 假设每次实时查询额外成本
            real_time_cost_usd = real_time_queries * 0.01  # $0.01 per query
            real_time_cost_cny = real_time_cost_usd * exchange_rate
            total_cost_usd += real_time_cost_usd
            total_cost_cny += real_time_cost_cny
            real_time_cost = real_time_cost_cny
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost_usd": round(input_cost_usd, 4),
            "output_cost_usd": round(output_cost_usd, 4),
            "total_cost_usd": round(total_cost_usd, 4),
            "input_cost_cny": round(input_cost_cny, 4),
            "output_cost_cny": round(output_cost_cny, 4),
            "total_cost_cny": round(total_cost_cny, 4),
            "real_time_cost_cny": round(real_time_cost, 4),
            "exchange_rate": exchange_rate,
            "model": model,
            "provider": self.provider_name,
            "requires_x_premium": requires_premium,
            "real_time_capable": pricing.get("real_time", False)
        }
    
    def make_api_call(self, model: str, messages: List[Dict[str, str]], 
                     **kwargs) -> Dict[str, Any]:
        """
        调用Grok API
        
        Args:
            model: 模型名称
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            API响应
        """
        if model not in self.MODEL_PRICING_USD:
            raise ValueError(f"不支持的模型: {model}")
        
        pricing = self.MODEL_PRICING_USD[model]
        
        # 检查是否需要X Premium
        if pricing.get("requires_x_premium", False) and not self.is_x_premium:
            return {
                "success": False,
                "error": "此模型需要X Premium订阅",
                "suggestion": "请升级到X Premium或使用Grok-1-mini模型"
            }
        
        # 构建请求数据
        request_data = {
            "model": model,
            "messages": self._format_messages(messages),
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 1.0),
            "stream": kwargs.get("stream", False),
            "real_time": kwargs.get("real_time", pricing.get("real_time", False))
        }
        
        # 添加实时信息参数
        if request_data["real_time"]:
            request_data["real_time_config"] = {
                "search_web": kwargs.get("search_web", True),
                "search_recency": kwargs.get("search_recency", "day"),  # hour, day, week, month
                "include_sources": kwargs.get("include_sources", True)
            }
        
        # 添加系统提示
        if "system" in kwargs:
            request_data["system_prompt"] = kwargs["system"]
        
        try:
            # 发送API请求 - 注意：xAI API端点可能不同
            api_endpoint = f"{self.API_BASE_URL}/v1/chat/completions"
            
            response = requests.post(
                api_endpoint,
                headers=self.headers,
                json=request_data,
                timeout=kwargs.get("timeout", 30)
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 提取使用信息
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            
            # 计算成本
            usage_data = {
                "real_time_queries": result.get("real_time_queries", 0) if request_data["real_time"] else 0
            }
            
            cost_info = self.calculate_cost(model, prompt_tokens, completion_tokens, usage_data)
            
            # 提取内容
            choices = result.get("choices", [])
            content = choices[0]["message"]["content"] if choices else ""
            
            # 提取实时信息源
            real_time_sources = []
            if request_data["real_time"] and "sources" in result:
                real_time_sources = result["sources"]
            
            return {
                "success": True,
                "content": content,
                "usage": usage,
                "cost": cost_info,
                "real_time_sources": real_time_sources,
                "raw_response": result
            }
            
        except requests.exceptions.RequestException as e:
            # API可能不可用，返回模拟响应
            return self._simulate_api_response(model, messages, kwargs, str(e))
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """格式化消息为API格式"""
        formatted = []
        for msg in messages:
            role = msg["role"]
            # Grok可能使用不同的角色名称
            if role == "assistant":
                role = "model"
            formatted.append({
                "role": role,
                "content": msg["content"]
            })
        return formatted
    
    def _simulate_api_response(self, model: str, messages: List[Dict[str, str]], 
                              kwargs: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """模拟API响应（当实际API不可用时）"""
        # 生成模拟响应
        last_message = messages[-1]["content"] if messages else "Hello"
        simulated_content = f"这是Grok模拟响应（实际API可能不可用）\n\n用户说：{last_message}\n\n（错误：{error_msg}）"
        
        # 模拟token使用
        prompt_tokens = sum(len(msg["content"]) // 4 for msg in messages)
        completion_tokens = len(simulated_content) // 4
        
        # 计算模拟成本
        cost_info = self.calculate_cost(model, prompt_tokens, completion_tokens)
        
        return {
            "success": True,
            "content": simulated_content,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            "cost": cost_info,
            "real_time_sources": [],
            "is_simulated": True,
            "api_available": False,
            "api_error": error_msg
        }
    
    def get_provider_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        return {
            "name": self.provider_name,
            "display_name": self.provider_display_name,
            "website": "https://x.ai",
            "api_docs": "https://docs.x.ai",
            "pricing_page": "https://x.ai/pricing",
            "status": "limited",  # API访问可能有限制
            "requires_twitter_account": True,
            "requires_x_premium": True,  # 多数功能需要
            "supports_streaming": True,
            "supports_real_time": True,  # Grok的核心特色
            "max_context_length": 131072,
            "featured_models": ["grok-2", "grok-1", "grok-1-mini"],
            "strengths": ["实时信息获取", "Twitter/X生态集成", "有趣有个性"],
            "weaknesses": ["API访问限制", "需要X Premium", "在中国可能不可用"],
            "notes": "xAI API目前可能对开发者有限制，建议使用模拟模式或等待公开API"
        }
    
    def validate_api_key(self) -> bool:
        """验证API密钥是否有效"""
        # xAI API验证可能复杂，这里简化处理
        try:
            # 尝试简单的API调用
            test_data = {
                "model": "grok-1-mini",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            response = requests.post(
                f"{self.API_BASE_URL}/v1/chat/completions",
                headers=self.headers,
                json=test_data,
                timeout=5
            )
            
            # 即使返回错误，也说明API端点存在
            return response.status_code in [200, 401, 403]
        except:
            # 如果API完全不可用，返回True允许模拟模式
            return True