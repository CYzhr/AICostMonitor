#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI提供商模块
支持多个AI API提供商
"""

from typing import Dict, List, Optional
from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """AI提供商基类"""
    
    def __init__(self, name: str, api_key: str = ""):
        self.name = name
        self.api_key = api_key
        self.enabled = bool(api_key)
    
    @abstractmethod
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """计算API调用成本"""
        pass
    
    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        pass
    
    def is_available(self) -> bool:
        """检查提供商是否可用"""
        return self.enabled and bool(self.api_key)


# 导出所有提供商
__all__ = ['BaseProvider']