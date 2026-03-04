#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度文心（千帆）提供商实现
支持ERNIE-4.0、ERNIE-3.5、ERNIE-Lite
国内API调用优化
"""

from typing import List, Dict, Any, Optional
import requests
from datetime import datetime
from .base import BaseProvider


class QianfanProvider(BaseProvider):
    """百度文心（千帆）API提供商"""
    
    # 百度文心模型定价（人民币/千token）
    MODEL_PRICING = {
        "ERNIE-4.0": {
            "input": 0.12,   # 输入token价格
            "output": 0.12,  # 输出token价格
            "context": 128000,
            "description": "旗舰模型，最强的理解与生成能力"
        },
        "ERNIE-3.5-8K": {
            "input": 0.012,
            "output": 0.012,
            "context": 8192,
            "description": "性价比最高的主力模型"
        },
        "ERNIE-3.5-128K": {
            "input": 0.012,
            "output": 0.012,
            "context": 128000,
            "description": "长文本支持的3.5版本"
        },
        "ERNIE-Lite-8K": {
            "input": 0.008,
            "output": 0.008,
            "context": 8192,
            "description": "轻量级模型，成本最低"
        },
        "ERNIE-Speed-8K": {
            "input": 0.004,
            "output": 0.004,
            "context": 8192,
            "description": "速度最快的模型"
        },
        "ERNIE-Speed-128K": {
            "input": 0.004,
            "output": 0.004,
            "context": 128000,
            "description": "长文本支持的快速模型"
        }
    }
    
    def __init__(self, api_key: str, secret_key: str):
        """
        初始化百度文心提供商
        
        Args:
            api_key: API Key
            secret_key: Secret Key
        """
        super().__init__(name="Baidu Qianfan")
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = "https://aip.baidubce.com"
        self.access_token = None
        self.token_expiry = None
    
    def _get_access_token(self) -> str:
        """获取Access Token"""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
        
        try:
            token_url = f"{self.base_url}/oauth/2.0/token"
            params = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key
            }
            response = requests.get(token_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                # 设置token过期时间（提前5分钟）
                expires_in = data.get("expires_in", 2592000) - 300
                self.token_expiry = datetime.fromtimestamp(
                    datetime.now().timestamp() + expires_in
                )
                return self.access_token
            else:
                raise Exception(f"获取token失败: {response.status_code}")
        except Exception as e:
            raise Exception(f"获取token异常: {str(e)}")
    
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
        
        return {
            "model": model,
            "provider": "Baidu Qianfan",
            "input_price": pricing["input"],  # 人民币/千token
            "output_price": pricing["output"],  # 人民币/千token
            "context_window": pricing["context"],
            "description": pricing.get("description", ""),
            "currency": "CNY",
            "updated_at": datetime.now().isoformat()
        }
    
    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            token = self._get_access_token()
            return bool(token)
        except Exception:
            return False
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计（需要百度商家后台API）"""
        # 百度目前没有公开的用量查询API
        return {
            "provider": "Baidu Qianfan",
            "note": "百度未提供公开用量API，请登录百度智能云控制台查看",
            "last_updated": datetime.now().isoformat()
        }
    
    def call_api(self, model: str, prompt: str, max_tokens: int = 1000) -> Dict[str, Any]:
        """
        调用文心API
        
        Args:
            model: 模型名称
            prompt: 输入文本
            max_tokens: 最大输出token数
            
        Returns:
            API响应结果
        """
        try:
            token = self._get_access_token()
            chat_url = f"{self.base_url}/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{model}"
            
            headers = {"Content-Type": "application/json"}
            params = {"access_token": token}
            
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "max_output_tokens": max_tokens,
                "temperature": 0.7
            }
            
            response = requests.post(
                chat_url,
                headers=headers,
                params=params,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"API调用失败: {response.status_code}, {response.text}")
        except Exception as e:
            raise Exception(f"API调用异常: {str(e)}")