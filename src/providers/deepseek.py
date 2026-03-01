#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek提供商实现
"""

from typing import List, Dict, Any
from .base import BaseProvider


class DeepSeekProvider(BaseProvider):
    """DeepSeek API提供商"""
    
    # DeepSeek模型定价（人民币/千token）
    MODEL_PRICING = {
        "deepseek-v3.2": {
            "input": 0.14,   # 输入token价格
            "output": 0.28,  # 输出token价格
            "context": 128000  # 上下文长度
        },
        "deepseek-r1": {
            "input": 0.15,
            "output": 0.30,
            "context": 128000
        },
        "deepseek-coder": {
            "input": 0.12,
            "output": 0.24,
            "context": 64000
        },
        "deepseek-chat": {
            "input": 0.10,
            "output": 0.20,
            "context": 32000
        }
    }
    
    def __init__(self, api_key: str = ""):
        super().__init__(name="deepseek", api_key=api_key)
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """计算DeepSeek API调用成本"""
        if model not in self.MODEL_PRICING:
            # 使用默认模型定价
            model = "deepseek-v3.2"
        
        pricing = self.MODEL_PRICING[model]
        
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        
        return round(input_cost + output_cost, 4)
    
    def get_supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        return list(self.MODEL_PRICING.keys())
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型详细信息"""
        if model not in self.MODEL_PRICING:
            raise ValueError(f"不支持的模型: {model}")
        
        info = self.MODEL_PRICING[model].copy()
        info.update({
            "provider": self.name,
            "model": model,
            "currency": "CNY",
            "description": "DeepSeek AI模型"
        })
        
        return info
    
    def estimate_tokens(self, text: str) -> int:
        """估算文本的token数量（简单估算）"""
        # 简单估算：中文约1.5字符/token，英文约0.75字符/token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_chars = len(text) - chinese_chars
        
        estimated_tokens = int(chinese_chars * 1.5 + english_chars * 0.75)
        return max(estimated_tokens, 1)


# 使用示例
if __name__ == "__main__":
    provider = DeepSeekProvider(api_key="test-key")
    
    # 测试成本计算
    cost = provider.calculate_cost(
        model="deepseek-v3.2",
        input_tokens=1500,
        output_tokens=800
    )
    
    print(f"DeepSeek成本计算示例: ¥{cost}")
    print(f"支持的模型: {provider.get_supported_models()}")