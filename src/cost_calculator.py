#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI API成本计算器
支持多个AI提供商的成本计算，支持USD/CNY双币计费
"""

import yaml
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import requests


class Currency(Enum):
    """货币类型"""
    CNY = "CNY"  # 人民币
    USD = "USD"  # 美元


@dataclass
class ProviderPricing:
    """提供商定价配置"""
    provider: str
    model: str
    input_price_per_1k: float  # 输入token价格（每千token）
    output_price_per_1k: float  # 输出token价格（每千token）
    currency: Currency = Currency.USD
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class APICallRecord:
    """API调用记录"""
    id: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: datetime
    cost_usd: float  # 美元成本
    cost_cny: float  # 人民币成本
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExchangeRateService:
    """汇率服务"""
    
    def __init__(self):
        self.rates = {"USD": 1.0, "CNY": 7.24}  # 默认汇率
        self.last_update = None
        self.cache_hours = 6
    
    def get_rate(self, from_currency: str, to_currency: str) -> float:
        """获取汇率"""
        # 尝试更新汇率
        self._update_rates_if_needed()
        
        if from_currency == to_currency:
            return 1.0
        
        # USD -> CNY
        if from_currency == "USD" and to_currency == "CNY":
            return self.rates.get("CNY", 7.24)
        
        # CNY -> USD
        if from_currency == "CNY" and to_currency == "USD":
            return 1.0 / self.rates.get("CNY", 7.24)
        
        return 1.0
    
    def _update_rates_if_needed(self):
        """按需更新汇率"""
        now = datetime.now()
        if self.last_update is None or (now - self.last_update).total_seconds() > self.cache_hours * 3600:
            try:
                # 使用免费汇率API
                response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self.rates["CNY"] = data.get("rates", {}).get("CNY", 7.24)
                    self.last_update = now
            except Exception:
                # 使用默认汇率
                pass
    
    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        """货币转换"""
        rate = self.get_rate(from_currency, to_currency)
        return round(amount * rate, 4)


class CostCalculator:
    """AI API成本计算器"""
    
    # 完整的定价配置（美元/千token）
    DEFAULT_PRICING = {
        # OpenAI - USD计费
        "openai": {
            "gpt-4o": ProviderPricing(
                provider="openai", model="gpt-4o",
                input_price_per_1k=0.0025, output_price_per_1k=0.01,
                currency=Currency.USD
            ),
            "gpt-4o-mini": ProviderPricing(
                provider="openai", model="gpt-4o-mini",
                input_price_per_1k=0.00015, output_price_per_1k=0.0006,
                currency=Currency.USD
            ),
            "gpt-4-turbo": ProviderPricing(
                provider="openai", model="gpt-4-turbo",
                input_price_per_1k=0.01, output_price_per_1k=0.03,
                currency=Currency.USD
            ),
            "gpt-4": ProviderPricing(
                provider="openai", model="gpt-4",
                input_price_per_1k=0.03, output_price_per_1k=0.06,
                currency=Currency.USD
            ),
            "gpt-3.5-turbo": ProviderPricing(
                provider="openai", model="gpt-3.5-turbo",
                input_price_per_1k=0.0005, output_price_per_1k=0.0015,
                currency=Currency.USD
            ),
        },
        
        # Anthropic Claude - USD计费
        "anthropic": {
            "claude-3.5-sonnet": ProviderPricing(
                provider="anthropic", model="claude-3.5-sonnet",
                input_price_per_1k=0.003, output_price_per_1k=0.015,
                currency=Currency.USD
            ),
            "claude-3-opus": ProviderPricing(
                provider="anthropic", model="claude-3-opus",
                input_price_per_1k=0.015, output_price_per_1k=0.075,
                currency=Currency.USD
            ),
            "claude-3-sonnet": ProviderPricing(
                provider="anthropic", model="claude-3-sonnet",
                input_price_per_1k=0.003, output_price_per_1k=0.015,
                currency=Currency.USD
            ),
            "claude-3-haiku": ProviderPricing(
                provider="anthropic", model="claude-3-haiku",
                input_price_per_1k=0.00025, output_price_per_1k=0.00125,
                currency=Currency.USD
            ),
        },
        
        # Google Gemini - USD计费
        "google": {
            "gemini-1.5-pro": ProviderPricing(
                provider="google", model="gemini-1.5-pro",
                input_price_per_1k=0.00125, output_price_per_1k=0.005,
                currency=Currency.USD
            ),
            "gemini-1.5-flash": ProviderPricing(
                provider="google", model="gemini-1.5-flash",
                input_price_per_1k=0.000075, output_price_per_1k=0.0003,
                currency=Currency.USD
            ),
            "gemini-pro": ProviderPricing(
                provider="google", model="gemini-pro",
                input_price_per_1k=0.00025, output_price_per_1k=0.0005,
                currency=Currency.USD
            ),
        },
        
        # xAI Grok - USD计费
        "xai": {
            "grok-1": ProviderPricing(
                provider="xai", model="grok-1",
                input_price_per_1k=0.005, output_price_per_1k=0.015,
                currency=Currency.USD
            ),
            "grok-2": ProviderPricing(
                provider="xai", model="grok-2",
                input_price_per_1k=0.002, output_price_per_1k=0.01,
                currency=Currency.USD
            ),
        },
        
        # DeepSeek - CNY计费（实际是人民币）
        "deepseek": {
            "deepseek-v3": ProviderPricing(
                provider="deepseek", model="deepseek-v3",
                input_price_per_1k=0.001, output_price_per_1k=0.002,
                currency=Currency.USD  # 转换为USD计费
            ),
            "deepseek-v3.2": ProviderPricing(
                provider="deepseek", model="deepseek-v3.2",
                input_price_per_1k=0.001, output_price_per_1k=0.002,
                currency=Currency.USD
            ),
            "deepseek-r1": ProviderPricing(
                provider="deepseek", model="deepseek-r1",
                input_price_per_1k=0.001, output_price_per_1k=0.002,
                currency=Currency.USD
            ),
            "deepseek-coder": ProviderPricing(
                provider="deepseek", model="deepseek-coder",
                input_price_per_1k=0.001, output_price_per_1k=0.002,
                currency=Currency.USD
            ),
        },
        
        # 百度文心一言 - CNY计费
        "baidu": {
            "ernie-4.0": ProviderPricing(
                provider="baidu", model="ernie-4.0",
                input_price_per_1k=0.12, output_price_per_1k=0.12,
                currency=Currency.CNY
            ),
            "ernie-3.5": ProviderPricing(
                provider="baidu", model="ernie-3.5",
                input_price_per_1k=0.008, output_price_per_1k=0.008,
                currency=Currency.CNY
            ),
            "ernie-lite": ProviderPricing(
                provider="baidu", model="ernie-lite",
                input_price_per_1k=0.003, output_price_per_1k=0.006,
                currency=Currency.CNY
            ),
        },
        
        # 阿里通义千问 - CNY计费
        "alibaba": {
            "qwen-turbo": ProviderPricing(
                provider="alibaba", model="qwen-turbo",
                input_price_per_1k=0.002, output_price_per_1k=0.006,
                currency=Currency.CNY
            ),
            "qwen-plus": ProviderPricing(
                provider="alibaba", model="qwen-plus",
                input_price_per_1k=0.004, output_price_per_1k=0.012,
                currency=Currency.CNY
            ),
            "qwen-max": ProviderPricing(
                provider="alibaba", model="qwen-max",
                input_price_per_1k=0.04, output_price_per_1k=0.12,
                currency=Currency.CNY
            ),
            "qwen-long": ProviderPricing(
                provider="alibaba", model="qwen-long",
                input_price_per_1k=0.0005, output_price_per_1k=0.002,
                currency=Currency.CNY
            ),
        },
        
        # 智谱AI - CNY计费
        "zhipu": {
            "glm-4": ProviderPricing(
                provider="zhipu", model="glm-4",
                input_price_per_1k=0.1, output_price_per_1k=0.1,
                currency=Currency.CNY
            ),
            "glm-3-turbo": ProviderPricing(
                provider="zhipu", model="glm-3-turbo",
                input_price_per_1k=0.001, output_price_per_1k=0.001,
                currency=Currency.CNY
            ),
        },
        
        # MiniMax - CNY计费
        "minimax": {
            "abab5.5": ProviderPricing(
                provider="minimax", model="abab5.5",
                input_price_per_1k=0.015, output_price_per_1k=0.015,
                currency=Currency.CNY
            ),
        },
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化成本计算器"""
        self.pricing_config = self.DEFAULT_PRICING.copy()
        self.records: List[APICallRecord] = []
        self.exchange_service = ExchangeRateService()
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str):
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if 'providers' in config:
                for provider_name, provider_config in config['providers'].items():
                    if provider_config.get('enabled', False) and 'pricing' in provider_config:
                        pricing = provider_config['pricing']
                        models = provider_config.get('models', [])
                        
                        for model in models:
                            if provider_name not in self.pricing_config:
                                self.pricing_config[provider_name] = {}
                            
                            currency_str = provider_config.get('currency', 'USD')
                            currency = Currency(currency_str.upper())
                            
                            self.pricing_config[provider_name][model] = ProviderPricing(
                                provider=provider_name,
                                model=model,
                                input_price_per_1k=float(pricing.get('input_tokens', 0.01)),
                                output_price_per_1k=float(pricing.get('output_tokens', 0.03)),
                                currency=currency
                            )
            
            print(f"配置加载成功：{len(self.pricing_config)}个提供商")
            
        except Exception as e:
            print(f"配置加载失败：{e}")
            print("使用默认定价配置")
    
    def get_available_providers(self) -> Dict[str, List[str]]:
        """获取所有可用的提供商和模型"""
        result = {}
        for provider, models in self.pricing_config.items():
            result[provider] = list(models.keys())
        return result
    
    def calculate_cost(self, provider: str, model: str, 
                      input_tokens: int, output_tokens: int) -> Dict[str, float]:
        """计算单次调用成本，返回USD和CNY两种货币"""
        try:
            if provider not in self.pricing_config:
                raise ValueError(f"未知的提供商：{provider}")
            
            if model not in self.pricing_config[provider]:
                # 尝试模糊匹配
                available_models = list(self.pricing_config[provider].keys())
                if available_models:
                    model = available_models[0]
                    print(f"警告：模型未找到，使用默认模型：{model}")
                else:
                    raise ValueError(f"提供商 {provider} 没有可用模型")
            
            pricing = self.pricing_config[provider][model]
            
            # 计算原始货币成本
            input_cost = (input_tokens / 1000) * pricing.input_price_per_1k
            output_cost = (output_tokens / 1000) * pricing.output_price_per_1k
            original_cost = input_cost + output_cost
            
            # 转换为USD和CNY
            if pricing.currency == Currency.USD:
                cost_usd = original_cost
                cost_cny = self.exchange_service.convert(original_cost, "USD", "CNY")
            else:
                cost_cny = original_cost
                cost_usd = self.exchange_service.convert(original_cost, "CNY", "USD")
            
            return {
                "usd": round(cost_usd, 6),
                "cny": round(cost_cny, 6),
                "original_currency": pricing.currency.value
            }
            
        except Exception as e:
            print(f"成本计算失败：{e}")
            # 返回估算成本
            estimated_usd = round((input_tokens + output_tokens) * 0.00001, 6)
            return {
                "usd": estimated_usd,
                "cny": self.exchange_service.convert(estimated_usd, "USD", "CNY"),
                "original_currency": "USD"
            }
    
    def record_call(self, provider: str, model: str,
                   input_tokens: int, output_tokens: int,
                   metadata: Optional[Dict] = None) -> APICallRecord:
        """记录API调用并计算成本"""
        costs = self.calculate_cost(provider, model, input_tokens, output_tokens)
        
        record = APICallRecord(
            id=f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{provider}",
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            timestamp=datetime.now(),
            cost_usd=costs["usd"],
            cost_cny=costs["cny"],
            metadata=metadata or {}
        )
        
        self.records.append(record)
        return record
    
    def get_exchange_rate(self) -> float:
        """获取USD到CNY的汇率"""
        return self.exchange_service.get_rate("USD", "CNY")
    
    def get_total_cost(self, start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> Dict[str, float]:
        """获取总成本（USD和CNY）"""
        filtered_records = self._filter_records_by_date(start_date, end_date)
        return {
            "usd": sum(r.cost_usd for r in filtered_records),
            "cny": sum(r.cost_cny for r in filtered_records)
        }
    
    def get_cost_by_provider(self, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> Dict[str, Dict[str, float]]:
        """按提供商统计成本"""
        filtered_records = self._filter_records_by_date(start_date, end_date)
        
        cost_by_provider = {}
        for record in filtered_records:
            if record.provider not in cost_by_provider:
                cost_by_provider[record.provider] = {"usd": 0.0, "cny": 0.0, "calls": 0}
            cost_by_provider[record.provider]["usd"] += record.cost_usd
            cost_by_provider[record.provider]["cny"] += record.cost_cny
            cost_by_provider[record.provider]["calls"] += 1
        
        return cost_by_provider
    
    def get_cost_by_model(self, start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> Dict[str, Dict[str, float]]:
        """按模型统计成本"""
        filtered_records = self._filter_records_by_date(start_date, end_date)
        
        cost_by_model = {}
        for record in filtered_records:
            model_key = f"{record.provider}/{record.model}"
            if model_key not in cost_by_model:
                cost_by_model[model_key] = {"usd": 0.0, "cny": 0.0, "calls": 0}
            cost_by_model[model_key]["usd"] += record.cost_usd
            cost_by_model[model_key]["cny"] += record.cost_cny
            cost_by_model[model_key]["calls"] += 1
        
        return cost_by_model
    
    def get_daily_cost(self, days: int = 30) -> List[Dict[str, Any]]:
        """获取最近N天的每日成本"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        daily_cost = []
        for i in range(days):
            day_start = start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            day_records = self._filter_records_by_date(day_start, day_end)
            day_usd = sum(r.cost_usd for r in day_records)
            day_cny = sum(r.cost_cny for r in day_records)
            
            daily_cost.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "cost_usd": round(day_usd, 6),
                "cost_cny": round(day_cny, 6),
                "call_count": len(day_records),
                "avg_cost_usd": round(day_usd / len(day_records), 6) if day_records else 0
            })
        
        return daily_cost
    
    def _filter_records_by_date(self, start_date: Optional[datetime],
                               end_date: Optional[datetime]) -> List[APICallRecord]:
        """按日期过滤记录"""
        filtered = self.records
        
        if start_date:
            filtered = [r for r in filtered if r.timestamp >= start_date]
        
        if end_date:
            filtered = [r for r in filtered if r.timestamp <= end_date]
        
        return filtered
    
    def export_to_json(self, filepath: str):
        """导出记录到JSON文件"""
        total_cost = self.get_total_cost()
        
        data = {
            "export_time": datetime.now().isoformat(),
            "total_records": len(self.records),
            "total_cost_usd": total_cost["usd"],
            "total_cost_cny": total_cost["cny"],
            "exchange_rate": self.get_exchange_rate(),
            "records": [
                {
                    "id": r.id,
                    "provider": r.provider,
                    "model": r.model,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "timestamp": r.timestamp.isoformat(),
                    "cost_usd": r.cost_usd,
                    "cost_cny": r.cost_cny,
                    "metadata": r.metadata
                }
                for r in self.records
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"记录已导出到：{filepath}")
    
    def print_summary(self):
        """打印成本摘要"""
        total_cost = self.get_total_cost()
        cost_by_provider = self.get_cost_by_provider()
        daily_cost = self.get_daily_cost(days=7)
        
        print("=" * 60)
        print("AI API成本监控摘要")
        print("=" * 60)
        print(f"总调用次数：{len(self.records)}")
        print(f"总成本：${total_cost['usd']:.4f} USD (¥{total_cost['cny']:.2f} CNY)")
        print(f"当前汇率：1 USD = {self.get_exchange_rate():.2f} CNY")
        print("\n按提供商统计：")
        
        for provider, costs in cost_by_provider.items():
            pct = (costs['usd'] / total_cost['usd'] * 100) if total_cost['usd'] > 0 else 0
            print(f"  {provider}: ${costs['usd']:.4f} ({pct:.1f}%) - {costs['calls']}次调用")
        
        print("\n最近7天每日成本：")
        for day in daily_cost[-7:]:
            print(f"  {day['date']}: ${day['cost_usd']:.4f} ({day['call_count']}次调用)")
        print("=" * 60)


# 示例使用
if __name__ == "__main__":
    calculator = CostCalculator()
    
    # 显示所有支持的提供商和模型
    print("支持的提供商和模型：")
    for provider, models in calculator.get_available_providers().items():
        print(f"\n{provider}:")
        for model in models:
            pricing = calculator.pricing_config[provider][model]
            print(f"  - {model}: ${pricing.input_price_per_1k:.4f}/${pricing.output_price_per_1k:.4f} per 1k tokens")
    
    # 测试计算
    test_calls = [
        ("openai", "gpt-4o", 1000, 500),
        ("anthropic", "claude-3.5-sonnet", 1000, 500),
        ("google", "gemini-1.5-pro", 1000, 500),
        ("baidu", "ernie-4.0", 1000, 500),
    ]
    
    print("\n\n测试成本计算：")
    for provider, model, input_tokens, output_tokens in test_calls:
        costs = calculator.calculate_cost(provider, model, input_tokens, output_tokens)
        print(f"{provider}/{model}: ${costs['usd']:.6f} USD (¥{costs['cny']:.4f} CNY)")
