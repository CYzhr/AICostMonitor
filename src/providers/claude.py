#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude (Anthropic) 提供商完整实现
支持Claude-3系列模型：Opus, Sonnet, Haiku
"""

from typing import List, Dict, Any, Optional
import requests
from datetime import datetime
import json
from .base import BaseProvider


class ClaudeProvider(BaseProvider):
    """Anthropic Claude API提供商"""
    
    # Claude模型定价（美元/千token）
    MODEL_PRICING_USD = {
        # Claude 3.5系列 (最新)
        "claude-3-5-sonnet-20241022": {
            "input": 3.00,    # $3.00 per 1M input tokens
            "output": 15.00,  # $15.00 per 1M output tokens
            "context": 200000,
            "vision": True
        },
        "claude-3-5-haiku-20241022": {
            "input": 0.80,
            "output": 4.00,
            "context": 200000,
            "vision": False
        },
        
        # Claude 3系列
        "claude-3-opus-20240229": {
            "input": 15.00,
            "output": 75.00,
            "context": 200000,
            "vision": True
        },
        "claude-3-sonnet-20240229": {
            "input": 3.00,
            "output": 15.00,
            "context": 200000,
            "vision": True
        },
        "claude-3-haiku-20240307": {
            "input": 0.25,
            "output": 1.25,
            "context": 200000,
            "vision": False
        },
        
        # Claude 2系列 (旧版)
        "claude-2.1": {
            "input": 8.00,
            "output": 24.00,
            "context": 200000,
            "vision": False
        },
        "claude-2.0": {
            "input": 8.00,
            "output": 24.00,
            "context": 100000,
            "vision": False
        },
        
        # Claude Instant系列
        "claude-instant-1.2": {
            "input": 0.80,
            "output": 2.40,
            "context": 100000,
            "vision": False
        }
    }
    
    # API基础配置
    API_BASE_URL = "https://api.anthropic.com"
    API_VERSION = "2023-06-01"
    
    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        """
        初始化Claude提供商
        
        Args:
            api_key: Anthropic API密钥
            config: 配置参数
        """
        super().__init__(api_key, config)
        self.provider_name = "claude"
        self.provider_display_name = "Anthropic Claude"
        self.default_model = "claude-3-5-sonnet-20241022"
        
        # 设置API头信息
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION
        }
    
    def get_supported_models(self) -> List[Dict[str, Any]]:
        """
        获取支持的模型列表
        
        Returns:
            模型信息列表
        """
        models = []
        for model_id, pricing in self.MODEL_PRICING_USD.items():
            models.append({
                "id": model_id,
                "name": model_id,
                "provider": self.provider_name,
                "input_price_usd": pricing["input"],
                "output_price_usd": pricing["output"],
                "context_window": pricing.get("context", 100000),
                "has_vision": pricing.get("vision", False),
                "is_multimodal": pricing.get("vision", False),
                "description": self._get_model_description(model_id)
            })
        
        # 按价格排序（从便宜到贵）
        models.sort(key=lambda x: x["input_price_usd"])
        return models
    
    def _get_model_description(self, model_id: str) -> str:
        """获取模型描述"""
        descriptions = {
            "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet - 平衡性能与成本，支持视觉",
            "claude-3-5-haiku-20241022": "Claude 3.5 Haiku - 快速且经济，推理速度快",
            "claude-3-opus-20240229": "Claude 3 Opus - 最强大模型，复杂任务首选",
            "claude-3-sonnet-20240229": "Claude 3 Sonnet - 平衡性能，日常使用推荐",
            "claude-3-haiku-20240307": "Claude 3 Haiku - 最快最经济，简单任务",
            "claude-2.1": "Claude 2.1 - 上一代模型，稳定性好",
            "claude-2.0": "Claude 2.0 - 基础版本",
            "claude-instant-1.2": "Claude Instant - 快速响应，成本最低"
        }
        return descriptions.get(model_id, "Anthropic Claude模型")
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int, 
                      usage_data: Dict[str, Any] = None) -> Dict[str, float]:
        """
        计算Claude使用成本
        
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
        
        # 计算成本（美元）
        input_cost_usd = (input_tokens / 1000000) * pricing["input"]
        output_cost_usd = (output_tokens / 1000000) * pricing["output"]
        total_cost_usd = input_cost_usd + output_cost_usd
        
        # 转换为人民币（按实时汇率，这里用固定汇率7.2）
        exchange_rate = self._get_exchange_rate()
        input_cost_cny = input_cost_usd * exchange_rate
        output_cost_cny = output_cost_usd * exchange_rate
        total_cost_cny = total_cost_usd * exchange_rate
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost_usd": round(input_cost_usd, 4),
            "output_cost_usd": round(output_cost_usd, 4),
            "total_cost_usd": round(total_cost_usd, 4),
            "input_cost_cny": round(input_cost_cny, 4),
            "output_cost_cny": round(output_cost_cny, 4),
            "total_cost_cny": round(total_cost_cny, 4),
            "exchange_rate": exchange_rate,
            "model": model,
            "provider": self.provider_name
        }
    
    def make_api_call(self, model: str, messages: List[Dict[str, str]], 
                     **kwargs) -> Dict[str, Any]:
        """
        调用Claude API
        
        Args:
            model: 模型名称
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            API响应
        """
        if model not in self.MODEL_PRICING_USD:
            raise ValueError(f"不支持的模型: {model}")
        
        # 构建请求数据
        request_data = {
            "model": model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 1.0),
            "stream": kwargs.get("stream", False)
        }
        
        # 添加可选参数
        if "system" in kwargs:
            request_data["system"] = kwargs["system"]
        
        try:
            # 发送API请求
            response = requests.post(
                f"{self.API_BASE_URL}/v1/messages",
                headers=self.headers,
                json=request_data,
                timeout=kwargs.get("timeout", 30)
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 提取使用信息
            usage = result.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            
            # 计算成本
            cost_info = self.calculate_cost(model, input_tokens, output_tokens)
            
            return {
                "success": True,
                "content": result.get("content", []),
                "usage": usage,
                "cost": cost_info,
                "raw_response": result
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "cost": self.calculate_cost(model, 0, 0)
            }
    
    def get_provider_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        return {
            "name": self.provider_name,
            "display_name": self.provider_display_name,
            "website": "https://www.anthropic.com",
            "api_docs": "https://docs.anthropic.com",
            "pricing_page": "https://www.anthropic.com/pricing",
            "status": "active",
            "supports_streaming": True,
            "supports_vision": True,
            "max_context_length": 200000,
            "featured_models": ["claude-3-5-sonnet-20241022", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
            "strengths": ["长上下文", "推理能力", "安全性", "多模态支持"],
            "weaknesses": ["价格较高", "API调用限制较多"]
        }
    
    def validate_api_key(self) -> bool:
        """验证API密钥是否有效"""
        try:
            # 简单的API调用测试
            test_response = requests.get(
                f"{self.API_BASE_URL}/v1/models",
                headers=self.headers,
                timeout=10
            )
            return test_response.status_code == 200
        except:
            return False