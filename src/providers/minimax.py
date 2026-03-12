#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimax 提供商完整实现
支持abab系列模型，中文优化出色
国内领先的AI公司
"""

from typing import List, Dict, Any, Optional
import requests
from datetime import datetime
import json
import hashlib
from .base import BaseProvider


class MinimaxProvider(BaseProvider):
    """Minimax AI提供商"""
    
    # Minimax模型定价（人民币/千token）
    MODEL_PRICING_CNY = {
        # abab 6系列 (最新)
        "abab6-chat": {
            "input": 0.010,   # ¥0.01 per 1K input tokens (极低)
            "output": 0.030,  # ¥0.03 per 1K output tokens
            "context": 128000,
            "supports_chinese": True,
            "is_multimodal": False
        },
        "abab6.5-chat": {
            "input": 0.012,
            "output": 0.036,
            "context": 128000,
            "supports_chinese": True,
            "is_multimodal": False
        },
        "abab6.5s-chat": {
            "input": 0.008,
            "output": 0.024,
            "context": 64000,
            "supports_chinese": True,
            "is_multimodal": False
        },
        
        # abab 5.5系列
        "abab5.5-chat": {
            "input": 0.015,
            "output": 0.045,
            "context": 64000,
            "supports_chinese": True,
            "is_multimodal": False
        },
        "abab5.5s-chat": {
            "input": 0.010,
            "output": 0.030,
            "context": 32000,
            "supports_chinese": True,
            "is_multimodal": False
        },
        
        # 视觉模型
        "abab6-vision": {
            "input": 0.020,
            "output": 0.060,
            "context": 128000,
            "supports_chinese": True,
            "is_multimodal": True,
            "vision": True
        },
        "abab5.5-vision": {
            "input": 0.025,
            "output": 0.075,
            "context": 64000,
            "supports_chinese": True,
            "is_multimodal": True,
            "vision": True
        },
        
        # 文本嵌入模型
        "embedding-001": {
            "input": 0.0001,  # ¥0.0001 per 1K tokens
            "output": 0.0,
            "context": 8192,
            "is_embedding": True,
            "embedding_dim": 1536
        },
        
        # 语音模型
        "speech-001": {
            "input": 0.015,   # ¥0.015 per second
            "output": 0.0,
            "is_speech": True,
            "supports_tts": True,
            "supports_stt": True
        }
    }
    
    # API基础配置
    API_BASE_URL = "https://api.minimax.chat"
    
    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        """
        初始化Minimax提供商
        
        Args:
            api_key: Minimax API密钥
            config: 配置参数
        """
        super().__init__(api_key, config)
        self.provider_name = "minimax"
        self.provider_display_name = "Minimax AI"
        self.default_model = "abab6-chat"
        
        # Minimax API需要group_id
        self.group_id = config.get("group_id", "") if config else ""
        
        # 设置API头信息
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 添加group_id到请求头
        if self.group_id:
            self.headers["Group-Id"] = self.group_id
        
        # Minimax可能需要签名
        self.requires_signature = config.get("requires_signature", False) if config else False
    
    def get_supported_models(self) -> List[Dict[str, Any]]:
        """
        获取支持的模型列表
        
        Returns:
            模型信息列表
        """
        models = []
        for model_id, pricing in self.MODEL_PRICING_CNY.items():
            model_info = {
                "id": model_id,
                "name": model_id,
                "provider": self.provider_name,
                "input_price_cny": pricing["input"],
                "output_price_cny": pricing["output"],
                "input_price_usd": round(pricing["input"] / 7.2, 6),  # 转换为美元
                "output_price_usd": round(pricing["output"] / 7.2, 6),
                "context_window": pricing.get("context", 32000),
                "supports_chinese": pricing.get("supports_chinese", True),
                "is_multimodal": pricing.get("is_multimodal", False),
                "is_embedding": pricing.get("is_embedding", False),
                "is_speech": pricing.get("is_speech", False),
                "has_vision": pricing.get("vision", False),
                "description": self._get_model_description(model_id),
                "cost_performance": self._calculate_cost_performance(pricing)
            }
            
            # 添加模型特定信息
            if pricing.get("is_embedding", False):
                model_info["embedding_dim"] = pricing.get("embedding_dim", 1536)
            
            if pricing.get("is_speech", False):
                model_info["supports_tts"] = pricing.get("supports_tts", False)
                model_info["supports_stt"] = pricing.get("supports_stt", False)
            
            models.append(model_info)
        
        # 按性价比排序（性价比高的在前）
        models.sort(key=lambda x: x["cost_performance"], reverse=True)
        return models
    
    def _get_model_description(self, model_id: str) -> str:
        """获取模型描述"""
        descriptions = {
            "abab6-chat": "abab6聊天模型 - 最新版本，中文优化，性价比极高",
            "abab6.5-chat": "abab6.5聊天模型 - 增强版本，性能更好",
            "abab6.5s-chat": "abab6.5s聊天模型 - 轻量版本，速度更快",
            "abab5.5-chat": "abab5.5聊天模型 - 稳定版本，广泛使用",
            "abab5.5s-chat": "abab5.5s聊天模型 - 轻量稳定版",
            "abab6-vision": "abab6视觉模型 - 支持图像理解",
            "abab5.5-vision": "abab5.5视觉模型 - 基础视觉功能",
            "embedding-001": "Embedding-001 - 文本嵌入模型",
            "speech-001": "Speech-001 - 语音识别和合成"
        }
        return descriptions.get(model_id, "Minimax AI模型")
    
    def _calculate_cost_performance(self, pricing: Dict[str, Any]) -> float:
        """计算性价比（越高越好）"""
        # 性价比 = 1 / (价格 * 权重)
        price_per_token = (pricing["input"] + pricing["output"]) / 2
        
        if price_per_token <= 0:
            return 100.0
        
        # 考虑上下文长度
        context_bonus = pricing.get("context", 1000) / 1000
        
        # 考虑功能丰富度
        feature_bonus = 1.0
        if pricing.get("is_multimodal", False):
            feature_bonus *= 1.5
        if pricing.get("supports_chinese", False):
            feature_bonus *= 1.2  # 中文支持是Minimax的优势
        
        performance = (context_bonus * feature_bonus) / price_per_token
        return performance
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int, 
                      usage_data: Dict[str, Any] = None) -> Dict[str, float]:
        """
        计算Minimax使用成本
        
        Args:
            model: 模型名称
            input_tokens: 输入token数
            output_tokens: 输出token数
            usage_data: 使用数据
            
        Returns:
            成本信息字典
        """
        if model not in self.MODEL_PRICING_CNY:
            raise ValueError(f"不支持的模型: {model}")
        
        pricing = self.MODEL_PRICING_CNY[model]
        
        # 特殊模型处理
        if pricing.get("is_embedding", False):
            # 嵌入模型按输入token计算
            input_cost_cny = (input_tokens / 1000) * pricing["input"]
            output_cost_cny = 0
            total_cost_cny = input_cost_cny
        
        elif pricing.get("is_speech", False):
            # 语音模型按秒计算
            seconds = usage_data.get("seconds", 1) if usage_data else 1
            input_cost_cny = seconds * pricing["input"]
            output_cost_cny = 0
            total_cost_cny = input_cost_cny
        
        else:
            # 普通聊天/视觉模型
            input_cost_cny = (input_tokens / 1000) * pricing["input"]
            output_cost_cny = (output_tokens / 1000) * pricing["output"]
            total_cost_cny = input_cost_cny + output_cost_cny
        
        # 转换为美元
        exchange_rate = self._get_exchange_rate()
        input_cost_usd = input_cost_cny / exchange_rate
        output_cost_usd = output_cost_cny / exchange_rate
        total_cost_usd = total_cost_cny / exchange_rate
        
        # 视觉token额外计算
        vision_cost = 0
        if pricing.get("vision", False) and usage_data:
            vision_tokens = usage_data.get("vision_tokens", 0)
            vision_cost_cny = (vision_tokens / 1000) * pricing["input"] * 1.5  # 视觉token通常更贵
            vision_cost_usd = vision_cost_cny / exchange_rate
            total_cost_cny += vision_cost_cny
            total_cost_usd += vision_cost_usd
            vision_cost = vision_cost_cny
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost_cny": round(input_cost_cny, 4),
            "output_cost_cny": round(output_cost_cny, 4),
            "total_cost_cny": round(total_cost_cny, 4),
            "input_cost_usd": round(input_cost_usd, 4),
            "output_cost_usd": round(output_cost_usd, 4),
            "total_cost_usd": round(total_cost_usd, 4),
            "vision_cost_cny": round(vision_cost, 4),
            "exchange_rate": exchange_rate,
            "model": model,
            "provider": self.provider_name,
            "is_chinese_optimized": pricing.get("supports_chinese", True),
            "is_embedding_model": pricing.get("is_embedding", False),
            "is_speech_model": pricing.get("is_speech", False),
            "is_vision_model": pricing.get("vision", False)
        }
    
    def make_api_call(self, model: str, messages: List[Dict[str, str]], 
                     **kwargs) -> Dict[str, Any]:
        """
        调用Minimax API
        
        Args:
            model: 模型名称
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            API响应
        """
        if model not in self.MODEL_PRICING_CNY:
            raise ValueError(f"不支持的模型: {model}")
        
        pricing = self.MODEL_PRICING_CNY[model]
        
        # 构建请求数据
        request_data = {
            "model": model,
            "messages": self._format_messages(messages),
            "stream": kwargs.get("stream", False),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.95),
            "max_tokens": kwargs.get("max_tokens", 1024),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
            "presence_penalty": kwargs.get("presence_penalty", 0.0)
        }
        
        # 添加系统提示
        if "system" in kwargs:
            request_data["prompt"] = kwargs["system"]
        
        # 添加bot设置
        request_data["bot_setting"] = kwargs.get("bot_setting", [{
            "bot_name": "AI助手",
            "content": "你是一个有帮助的AI助手"
        }])
        
        # 添加回复约束
        request_data["reply_constraints"] = kwargs.get("reply_constraints", {
            "sender_type": "BOT",
            "sender_name": "AI助手"
        })
        
        # 如果需要签名
        if self.requires_signature:
            timestamp = int(datetime.now().timestamp())
            signature = self._generate_signature(timestamp)
            request_data["timestamp"] = timestamp
            request_data["signature"] = signature
        
        try:
            # 确定API端点
            if pricing.get("is_embedding", False):
                endpoint = "/v1/embeddings"
            elif pricing.get("is_speech", False):
                endpoint = "/v1/speech"
            else:
                endpoint = "/v1/text/chatcompletion_v2"
            
            # 发送API请求
            response = requests.post(
                f"{self.API_BASE_URL}{endpoint}",
                headers=self.headers,
                json=request_data,
                timeout=kwargs.get("timeout", 30)
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 检查API响应状态
            if result.get("base_resp", {}).get("status_code", 0) != 0:
                error_msg = result.get("base_resp", {}).get("status_msg", "API错误")
                return {
                    "success": False,
                    "error": error_msg,
                    "cost": self.calculate_cost(model, 0, 0)
                }
            
            # 提取使用信息
            usage = result.get("usage", {})
            prompt_tokens = usage.get("total_tokens", 0)
            completion_tokens = 0
            
            # 对于聊天模型
            if "choices" in result and result["choices"]:
                completion_tokens = len(result["choices"][0].get("message", {}).get("content", "")) // 4
            
            # 计算成本
            usage_data = {
                "seconds": kwargs.get("seconds", 0) if pricing.get("is_speech", False) else 0,
                "vision_tokens": kwargs.get("vision_tokens", 0) if pricing.get("vision", False) else 0
            }
            
            cost_info = self.calculate_cost(model, prompt_tokens, completion_tokens, usage_data)
            
            # 提取内容
            content = ""
            if "choices" in result and result["choices"]:
                content = result["choices"][0].get("message", {}).get("content", "")
            elif "data" in result and result["data"]:  # 嵌入模型
                content = "[嵌入向量数据]"
            elif "audio" in result:  # 语音模型
                content = "[语音数据]"
            
            return {
                "success": True,
                "content": content,
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
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """格式化消息为Minimax格式"""
        formatted = []
        for msg in messages:
            role_map = {
                "system": "system",
                "user": "USER",
                "assistant": "BOT"
            }
            role = role_map.get(msg["role"], "USER")
            
            formatted.append({
                "sender_type": role,
                "sender_name": "用户" if role == "USER" else "AI助手",
                "text": msg["content"]
            })
        return formatted
    
    def _generate_signature(self, timestamp: int) -> str:
        """生成API签名（如果需要）"""
        # Minimax签名算法示例
        secret = self.config.get("api_secret", "") if self.config else ""
        if not secret:
            return ""
        
        # 简单的签名算法
        sign_str = f"{self.api_key}{timestamp}{secret}"
        return hashlib.md5(sign_str.encode()).hexdigest()
    
    def get_provider_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        return {
            "name": self.provider_name,
            "display_name": self.provider_display_name,
            "website": "https://www.minimaxi.com",
            "api_docs": "https://api.minimaxi.com/document",
            "pricing_page": "https://www.minimaxi.com/pricing",
            "status": "active",
            "is_chinese_company": True,
            "supports_streaming": True,
            "supports_chinese": True,  # 核心优势
            "supports_vision": True,
            "supports_speech": True,
            "supports_embedding": True,
            "max_context_length": 128000,
            "has_free_tier": True,
            "free_tier_limits": "每月一定免费额度",
            "featured_models": ["abab6-chat", "abab6.5-chat", "abab5.5-chat"],
            "strengths": ["中文优化出色", "价格极具竞争力", "功能全面", "国内访问速度快"],
            "weaknesses": ["国际知名度较低", "英文能力相对较弱", "文档主要为中文"],
            "recommended_for": ["中文项目", "成本敏感项目", "国内用户项目"]
        }
    
    def validate_api_key(self) -> bool:
        """验证API密钥是否有效"""
        try:
            # 尝试获取模型列表
            response = requests.get(
                f"{self.API_BASE_URL}/v1/models",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return True
            
            # 如果模型列表API不可用，尝试简单聊天测试
            test_data = {
                "model": "abab6-chat",
                "messages": [{
                    "sender_type": "USER",
                    "sender_name": "用户",
                    "text": "Hello"
                }],
                "bot_setting": [{
                    "bot_name": "测试助手",
                    "content": "你是一个测试助手"
                }],
                "reply_constraints": {
                    "sender_type": "BOT",
                    "sender_name": "测试助手"
                }
            }
            
            test_response = requests.post(
                f"{self.API_BASE_URL}/v1/text/chatcompletion_v2",
                headers=self.headers,
                json=test_data,
                timeout=5
            )
            
            return test_response.status_code == 200
            
        except:
            return False