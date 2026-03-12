#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Gemini 提供商完整实现
支持Gemini Pro, Gemini Ultra等模型
多模态和函数调用支持
"""

from typing import List, Dict, Any, Optional
import requests
from datetime import datetime
import json
from .base import BaseProvider


class GeminiProvider(BaseProvider):
    """Google Gemini API提供商"""
    
    # Gemini模型定价（美元/千token）
    MODEL_PRICING_USD = {
        # Gemini 1.5系列
        "gemini-1.5-pro-latest": {
            "input": 3.50,    # $3.50 per 1M input tokens
            "output": 10.50,  # $10.50 per 1M output tokens
            "context": 1000000,  # 1M上下文
            "vision": True,
            "multimodal": True
        },
        "gemini-1.5-flash-latest": {
            "input": 0.075,   # $0.075 per 1M input tokens (极低)
            "output": 0.30,   # $0.30 per 1M output tokens
            "context": 1000000,
            "vision": True,
            "multimodal": True
        },
        "gemini-1.5-pro": {
            "input": 3.50,
            "output": 10.50,
            "context": 128000,
            "vision": True,
            "multimodal": True
        },
        "gemini-1.5-flash": {
            "input": 0.075,
            "output": 0.30,
            "context": 128000,
            "vision": True,
            "multimodal": True
        },
        
        # Gemini 1.0系列
        "gemini-1.0-pro": {
            "input": 0.50,
            "output": 1.50,
            "context": 32768,
            "vision": False,
            "multimodal": False
        },
        "gemini-1.0-pro-vision": {
            "input": 0.50,
            "output": 1.50,
            "context": 16384,
            "vision": True,
            "multimodal": True
        },
        "gemini-1.0-ultra": {
            "input": 7.00,
            "output": 21.00,
            "context": 32768,
            "vision": False,
            "multimodal": False
        },
        
        # 其他Google模型
        "text-bison-001": {
            "input": 0.50,
            "output": 1.50,
            "context": 8192,
            "vision": False,
            "multimodal": False
        },
        "chat-bison-001": {
            "input": 0.50,
            "output": 1.50,
            "context": 8192,
            "vision": False,
            "multimodal": False
        }
    }
    
    # API基础配置
    API_BASE_URL = "https://generativelanguage.googleapis.com"
    
    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        """
        初始化Gemini提供商
        
        Args:
            api_key: Google AI Studio API密钥
            config: 配置参数
        """
        super().__init__(api_key, config)
        self.provider_name = "gemini"
        self.provider_display_name = "Google Gemini"
        self.default_model = "gemini-1.5-flash-latest"
        
        # 设置API头信息
        self.headers = {
            "Content-Type": "application/json"
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
                "context_window": pricing.get("context", 32768),
                "has_vision": pricing.get("vision", False),
                "is_multimodal": pricing.get("multimodal", False),
                "is_latest": "latest" in model_id,
                "description": self._get_model_description(model_id),
                "cost_efficiency": self._calculate_cost_efficiency(pricing)
            })
        
        # 按成本效率排序（性价比最高在前）
        models.sort(key=lambda x: x["cost_efficiency"], reverse=True)
        return models
    
    def _get_model_description(self, model_id: str) -> str:
        """获取模型描述"""
        descriptions = {
            "gemini-1.5-pro-latest": "Gemini 1.5 Pro最新版 - 强大功能，100万上下文",
            "gemini-1.5-flash-latest": "Gemini 1.5 Flash最新版 - 极快速度，成本极低",
            "gemini-1.5-pro": "Gemini 1.5 Pro - 平衡性能，多模态支持",
            "gemini-1.5-flash": "Gemini 1.5 Flash - 快速响应，经济实惠",
            "gemini-1.0-pro": "Gemini 1.0 Pro - 基础版本，稳定可靠",
            "gemini-1.0-pro-vision": "Gemini 1.0 Pro Vision - 视觉功能支持",
            "gemini-1.0-ultra": "Gemini 1.0 Ultra - 最强大模型",
            "text-bison-001": "Text Bison - 文本生成专用",
            "chat-bison-001": "Chat Bison - 对话优化版本"
        }
        return descriptions.get(model_id, "Google Gemini模型")
    
    def _calculate_cost_efficiency(self, pricing: Dict[str, Any]) -> float:
        """计算成本效率（越低越好）"""
        # 简单的效率计算：价格越低，上下文越长，效率越高
        price_per_token = (pricing["input"] + pricing["output"]) / 2
        context_size = pricing.get("context", 1000)
        
        if price_per_token <= 0:
            return 100.0  # 免费或极低价模型效率最高
        
        # 效率 = 上下文长度 / 价格（越高越好）
        efficiency = context_size / price_per_token
        return efficiency
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int, 
                      usage_data: Dict[str, Any] = None) -> Dict[str, float]:
        """
        计算Gemini使用成本
        
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
        
        # 计算成本（美元）- 注意：Gemini按每100万token计费
        input_cost_usd = (input_tokens / 1000000) * pricing["input"]
        output_cost_usd = (output_tokens / 1000000) * pricing["output"]
        total_cost_usd = input_cost_usd + output_cost_usd
        
        # 转换为人民币（按实时汇率，这里用固定汇率7.2）
        exchange_rate = self._get_exchange_rate()
        input_cost_cny = input_cost_usd * exchange_rate
        output_cost_cny = output_cost_usd * exchange_rate
        total_cost_cny = total_cost_usd * exchange_rate
        
        # Gemini特有：视觉token额外计算
        vision_cost = 0
        if usage_data and "vision_tokens" in usage_data:
            vision_tokens = usage_data["vision_tokens"]
            # 视觉token通常按输入token计算
            vision_cost_usd = (vision_tokens / 1000000) * pricing["input"]
            vision_cost_cny = vision_cost_usd * exchange_rate
            total_cost_usd += vision_cost_usd
            total_cost_cny += vision_cost_cny
            vision_cost = vision_cost_cny
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost_usd": round(input_cost_usd, 6),  # 价格很低，需要更多小数位
            "output_cost_usd": round(output_cost_usd, 6),
            "total_cost_usd": round(total_cost_usd, 6),
            "input_cost_cny": round(input_cost_cny, 4),
            "output_cost_cny": round(output_cost_cny, 4),
            "total_cost_cny": round(total_cost_cny, 4),
            "vision_cost_cny": round(vision_cost, 4),
            "exchange_rate": exchange_rate,
            "model": model,
            "provider": self.provider_name,
            "is_free_tier": total_cost_usd == 0  # Gemini有免费额度
        }
    
    def make_api_call(self, model: str, messages: List[Dict[str, str]], 
                     **kwargs) -> Dict[str, Any]:
        """
        调用Gemini API
        
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
            "contents": self._format_messages(messages),
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "topP": kwargs.get("top_p", 0.95),
                "topK": kwargs.get("top_k", 40),
                "maxOutputTokens": kwargs.get("max_tokens", 1024),
                "stopSequences": kwargs.get("stop_sequences", [])
            },
            "safetySettings": kwargs.get("safety_settings", [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ])
        }
        
        # 添加系统提示
        if "system" in kwargs:
            request_data["systemInstruction"] = {
                "parts": [{"text": kwargs["system"]}]
            }
        
        # 添加函数调用支持
        if "tools" in kwargs:
            request_data["tools"] = kwargs["tools"]
        
        try:
            # 发送API请求
            url = f"{self.API_BASE_URL}/v1beta/models/{model}:generateContent"
            params = {"key": self.api_key}
            
            response = requests.post(
                url,
                headers=self.headers,
                params=params,
                json=request_data,
                timeout=kwargs.get("timeout", 30)
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 提取使用信息
            usage_metadata = result.get("usageMetadata", {})
            prompt_token_count = usage_metadata.get("promptTokenCount", 0)
            candidates_token_count = usage_metadata.get("candidatesTokenCount", 0)
            total_token_count = usage_metadata.get("totalTokenCount", 0)
            
            # 计算成本
            cost_info = self.calculate_cost(
                model, 
                prompt_token_count, 
                candidates_token_count,
                {"vision_tokens": usage_metadata.get("visionTokens", 0)}
            )
            
            return {
                "success": True,
                "content": self._extract_content(result),
                "usage": {
                    "prompt_tokens": prompt_token_count,
                    "completion_tokens": candidates_token_count,
                    "total_tokens": total_token_count,
                    "vision_tokens": usage_metadata.get("visionTokens", 0)
                },
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
        """格式化消息为Gemini格式"""
        formatted = []
        for msg in messages:
            role = "user" if msg["role"] in ["user", "system"] else "model"
            formatted.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        return formatted
    
    def _extract_content(self, response: Dict[str, Any]) -> str:
        """从响应中提取内容"""
        try:
            candidates = response.get("candidates", [])
            if not candidates:
                return ""
            
            first_candidate = candidates[0]
            content = first_candidate.get("content", {})
            parts = content.get("parts", [])
            
            if not parts:
                return ""
            
            # 提取文本内容
            texts = []
            for part in parts:
                if "text" in part:
                    texts.append(part["text"])
                elif "functionCall" in part:
                    # 处理函数调用
                    func_call = part["functionCall"]
                    texts.append(f"[函数调用: {func_call.get('name', 'unknown')}]")
            
            return "\n".join(texts)
        except:
            return ""
    
    def get_provider_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        return {
            "name": self.provider_name,
            "display_name": self.provider_display_name,
            "website": "https://ai.google.dev",
            "api_docs": "https://ai.google.dev/gemini-api/docs",
            "pricing_page": "https://ai.google.dev/pricing",
            "status": "active",
            "supports_streaming": True,
            "supports_vision": True,
            "supports_function_calling": True,
            "max_context_length": 1000000,  # 1M token
            "has_free_tier": True,
            "free_tier_limits": "60 requests/minute, 免费额度每月",
            "featured_models": ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-1.0-pro"],
            "strengths": ["Google生态集成", "多模态能力", "免费额度", "长上下文支持"],
            "weaknesses": ["在中国访问可能受限", "安全限制较严格"]
        }
    
    def validate_api_key(self) -> bool:
        """验证API密钥是否有效"""
        try:
            # 简单的模型列表API调用测试
            url = f"{self.API_BASE_URL}/v1beta/models"
            params = {"key": self.api_key}
            
            test_response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=10
            )
            return test_response.status_code == 200
        except:
            return False