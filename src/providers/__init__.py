#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI提供商模块 - 支持多个主流AI平台
"""

from typing import Dict, List, Optional, Any, Type
from abc import ABC, abstractmethod
import importlib
import os


class BaseProvider(ABC):
    """AI提供商基类"""
    
    def __init__(self, api_key: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化提供商
        
        Args:
            api_key: API密钥
            config: 配置参数
        """
        self.api_key = api_key
        self.config = config or {}
        self.provider_name = ""
        self.provider_display_name = ""
        self.default_model = ""
    
    @abstractmethod
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int, 
                      usage_data: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """计算API调用成本"""
        pass
    
    @abstractmethod
    def get_supported_models(self) -> List[Dict[str, Any]]:
        """获取支持的模型列表"""
        pass
    
    @abstractmethod
    def make_api_call(self, model: str, messages: List[Dict[str, str]], 
                     **kwargs) -> Dict[str, Any]:
        """调用API"""
        pass
    
    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """获取提供商信息"""
        pass
    
    @abstractmethod
    def validate_api_key(self) -> bool:
        """验证API密钥是否有效"""
        pass
    
    def _get_exchange_rate(self) -> float:
        """获取汇率（美元兑人民币）"""
        # 这里可以使用实时汇率API
        # 暂时使用固定汇率
        return 7.2
    
    def is_available(self) -> bool:
        """检查提供商是否可用"""
        return bool(self.api_key) and self.validate_api_key()
    
    def get_name(self) -> str:
        """获取提供商名称"""
        return self.provider_name
    
    def get_display_name(self) -> str:
        """获取显示名称"""
        return self.provider_display_name


# Provider工厂类
class ProviderFactory:
    """提供商工厂，动态加载和管理所有提供商"""
    
    # 已支持的提供商列表
    SUPPORTED_PROVIDERS = {
        "openai": "OpenAI GPT系列",
        "deepseek": "深度求索 DeepSeek",
        "qianfan": "百度千帆",
        "claude": "Anthropic Claude",
        "gemini": "Google Gemini",
        "grok": "xAI Grok",
        "minimax": "Minimax AI",
        "ernie": "百度文心",
        "zhipu": "智谱清言",
        "tongyi": "阿里通义千问"
    }
    
    # 提供商优先级排序（按使用量/重要性）
    PROVIDER_PRIORITY = [
        "openai",      # 全球使用量第一
        "claude",      # 质量口碑第一
        "gemini",      # Google生态
        "deepseek",    # 性价比高
        "minimax",     # 中文优化出色
        "grok",        # 实时信息特色
        "qianfan",     # 百度生态
        "ernie",       # 百度文心
        "zhipu",       # 智谱
        "tongyi"       # 阿里
    ]
    
    @classmethod
    def create_provider(cls, provider_name: str, api_key: str, 
                       config: Optional[Dict[str, Any]] = None) -> Optional[BaseProvider]:
        """
        创建提供商实例
        
        Args:
            provider_name: 提供商名称
            api_key: API密钥
            config: 配置参数
            
        Returns:
            提供商实例或None
        """
        if provider_name not in cls.SUPPORTED_PROVIDERS:
            raise ValueError(f"不支持的提供商: {provider_name}")
        
        try:
            # 动态导入提供商模块
            module_name = f"src.providers.{provider_name}"
            module = importlib.import_module(module_name)
            
            # 获取提供商类名（首字母大写）
            class_name = provider_name.title().replace("-", "") + "Provider"
            provider_class = getattr(module, class_name)
            
            # 创建实例
            return provider_class(api_key, config)
            
        except ImportError as e:
            print(f"无法导入提供商模块 {provider_name}: {e}")
            return None
        except AttributeError as e:
            print(f"提供商类 {class_name} 不存在: {e}")
            return None
        except Exception as e:
            print(f"创建提供商 {provider_name} 时出错: {e}")
            return None
    
    @classmethod
    def get_all_providers(cls, api_keys: Dict[str, str], 
                         configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, BaseProvider]:
        """
        获取所有可用的提供商
        
        Args:
            api_keys: 各提供商的API密钥字典
            configs: 各提供商的配置字典
            
        Returns:
            提供商字典 {名称: 实例}
        """
        configs = configs or {}
        providers = {}
        
        for provider_name in cls.PROVIDER_PRIORITY:
            if provider_name in api_keys and api_keys[provider_name]:
                config = configs.get(provider_name, {})
                provider = cls.create_provider(provider_name, api_keys[provider_name], config)
                
                if provider and provider.is_available():
                    providers[provider_name] = provider
                    print(f"✅ 已加载提供商: {provider.get_display_name()}")
                else:
                    print(f"⚠️  提供商不可用或密钥无效: {provider_name}")
        
        return providers
    
    @classmethod
    def get_provider_info_list(cls) -> List[Dict[str, Any]]:
        """获取所有提供商的信息列表"""
        provider_list = []
        
        for provider_name, display_name in cls.SUPPORTED_PROVIDERS.items():
            # 尝试创建临时实例以获取信息
            try:
                module_name = f"src.providers.{provider_name}"
                module = importlib.import_module(module_name)
                class_name = provider_name.title().replace("-", "") + "Provider"
                provider_class = getattr(module, class_name)
                
                # 创建无密钥实例以获取基本信息
                empty_instance = provider_class("")
                
                provider_info = {
                    "name": provider_name,
                    "display_name": display_name,
                    "description": empty_instance.get_provider_info().get("description", ""),
                    "website": empty_instance.get_provider_info().get("website", ""),
                    "api_docs": empty_instance.get_provider_info().get("api_docs", ""),
                    "pricing_page": empty_instance.get_provider_info().get("pricing_page", ""),
                    "status": empty_instance.get_provider_info().get("status", "unknown"),
                    "priority": cls.PROVIDER_PRIORITY.index(provider_name) if provider_name in cls.PROVIDER_PRIORITY else 99,
                    "supported_models_count": len(empty_instance.get_supported_models())
                }
                
                provider_list.append(provider_info)
                
            except (ImportError, AttributeError, Exception) as e:
                # 如果无法加载，提供基本信息
                provider_list.append({
                    "name": provider_name,
                    "display_name": display_name,
                    "description": f"{display_name} AI服务",
                    "website": "",
                    "status": "not_loaded",
                    "priority": cls.PROVIDER_PRIORITY.index(provider_name) if provider_name in cls.PROVIDER_PRIORITY else 99,
                    "error": str(e)
                })
        
        # 按优先级排序
        provider_list.sort(key=lambda x: x["priority"])
        return provider_list


# 导出
__all__ = [
    'BaseProvider',
    'ProviderFactory'
]

# 自动加载所有提供商
try:
    # 这里可以添加自动发现机制
    pass
except Exception as e:
    print(f"自动加载提供商时出错: {e}")