#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI提供商完整实现
支持GPT-4、GPT-4-Turbo、GPT-3.5-Turbo
美元/人民币自动汇率转换
"""

from typing import List, Dict, Any, Optional
import requests
from datetime import datetime
from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI API提供商"""
    
    # OpenAI模型定价（美元/千token）
    MODEL_PRICING_USD = {
        # GPT-4系列
        "gpt-4o": {
            "input": 2.50,   # $2.50 per 1M input tokens
            "output": 10.00, # $10.00 per 1M output tokens
            "context": 128000
        },
        "gpt-4o-mini": {
            "input": 0.15,
            "output": 0.60,
            "context": 128000
        },
        "gpt-4-turbo": {
            "input": 10.00,
            "output": 30.00,
            "context": 128000
        },
        "gpt-4": {
            "input": 30.00,
            "output": 60.00,
            "context": 8192
        },
        
        # GPT-3.5系列
        "gpt-3.5-turbo": {
            "input": 0.50,
            "output": 1.50,
            "context": 16385
        },
        "gpt-3.5-turbo-instruct": {
            "input": 1.50,
            "output": 2.00,
            "context": 4096
        }
    }
    
    def __init__(self, api_key: str, exchange_rate: float = 7.2):
        """
        初始化OpenAI提供商
        
        Args:
            api_key: OpenAI API密钥
            exchange_rate: 美元兑人民币汇率，默认7.2
        """
        super().__init__(name="OpenAI")
        self.api_key = api_key
        self.exchange_rate = exchange_rate
        self.base_url = "https://api.openai.com/v1"
        
        # 转换定价为人民币
        self.MODEL_PRICING = self._convert_pricing_to_cny()
    
    def _convert_pricing_to_cny(self) -> Dict[str, Dict[str, float]]:
        """将美元定价转换为人民币定价"""
        cny_pricing = {}
        for model, pricing in self.MODEL_PRICING_USD.items():
            cny_pricing[model] = {
                "input": pricing["input"] * self.exchange_rate / 1000,  # 转换为人民币/千token
                "output": pricing["output"] * self.exchange_rate / 1000,
                "context": pricing["context"]
            }
        return cny_pricing
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        计算API调用成本
        
        Args:
            model: 模型名称
            input_tokens: 输入token数量
            output_tokens: 输出token数量
            
        Returns:
            总成本（人民币）
        """
        if model not in self.MODEL_PRICING:
            raise ValueError(f"不支持模型: {model}")
        
        pricing = self.MODEL_PRICING[model]
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        
        total_cost = input_cost + output_cost
        return round(total_cost, 4)
    
    def get_supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        return list(self.MODEL_PRICING.keys())
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型详细信息"""
        if model not in self.MODEL_PRICING:
            raise ValueError(f"不支持模型: {model}")
        
        pricing = self.MODEL_PRICING[model]
        usd_pricing = self.MODEL_PRICING_USD[model]
        
        return {
            "model": model,
            "provider": "OpenAI",
            "input_price_cny": pricing["input"],  # 人民币/千token
            "output_price_cny": pricing["output"],  # 人民币/千token
            "input_price_usd": usd_pricing["input"],  # 美元/千token
            "output_price_usd": usd_pricing["output"],  # 美元/千token
            "context_window": pricing["context"],
            "exchange_rate": self.exchange_rate,
            "currency": "CNY",
            "updated_at": datetime.now().isoformat()
        }
    
    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            response = requests.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计（需要实现）"""
        # TODO: 实现OpenAI用量API调用
        return {
            "total_tokens": 0,
            "total_cost_usd": 0,
            "total_cost_cny": 0,
            "last_updated": datetime.now().isoformat()
        }