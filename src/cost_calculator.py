#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI API成本计算器
支持多个AI提供商的成本计算
"""

import yaml
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class Currency(Enum):
    """货币类型"""
    CNY = "CNY"  # 人民币
    USD = "USD"  # 美元
    EUR = "EUR"  # 欧元


@dataclass
class ProviderPricing:
    """提供商定价配置"""
    provider: str
    model: str
    input_price_per_1k: float  # 输入token价格（每千token）
    output_price_per_1k: float  # 输出token价格（每千token）
    currency: Currency = Currency.CNY
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
    cost_cny: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class CostCalculator:
    """AI API成本计算器"""
    
    # 默认定价配置（人民币/千token）
    DEFAULT_PRICING = {
        "deepseek": {
            "deepseek-v3.2": ProviderPricing(
                provider="deepseek",
                model="deepseek-v3.2",
                input_price_per_1k=0.14,
                output_price_per_1k=0.28,
                currency=Currency.CNY
            ),
            "deepseek-r1": ProviderPricing(
                provider="deepseek",
                model="deepseek-r1",
                input_price_per_1k=0.15,
                output_price_per_1k=0.30,
                currency=Currency.CNY
            )
        },
        "openai": {
            "gpt-4": ProviderPricing(
                provider="openai",
                model="gpt-4",
                input_price_per_1k=1.00,  # 1.00美元/千token
                output_price_per_1k=2.00,  # 2.00美元/千token
                currency=Currency.USD
            ),
            "gpt-3.5-turbo": ProviderPricing(
                provider="openai",
                model="gpt-3.5-turbo",
                input_price_per_1k=0.15,  # 0.15美元/千token
                output_price_per_1k=0.30,  # 0.30美元/千token
                currency=Currency.USD
            )
        },
        "qianfan": {
            "ERNIE-4.0": ProviderPricing(
                provider="qianfan",
                model="ERNIE-4.0",
                input_price_per_1k=0.12,
                output_price_per_1k=0.24,
                currency=Currency.CNY
            )
        }
    }
    
    # 汇率（示例汇率，需要实时更新）
    EXCHANGE_RATES = {
        "USD": 7.2,  # 1美元=7.2人民币
        "EUR": 7.8,  # 1欧元=7.8人民币
        "CNY": 1.0
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化成本计算器"""
        self.pricing_config = self.DEFAULT_PRICING.copy()
        self.records: List[APICallRecord] = []
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str):
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 更新定价配置
            if 'providers' in config:
                for provider_name, provider_config in config['providers'].items():
                    if provider_config.get('enabled', False) and 'pricing' in provider_config:
                        pricing = provider_config['pricing']
                        models = provider_config.get('models', [])
                        
                        for model in models:
                            if provider_name not in self.pricing_config:
                                self.pricing_config[provider_name] = {}
                            
                            currency_str = provider_config.get('currency', 'CNY')
                            currency = Currency(currency_str.upper())
                            
                            self.pricing_config[provider_name][model] = ProviderPricing(
                                provider=provider_name,
                                model=model,
                                input_price_per_1k=float(pricing.get('input_tokens', 0.1)),
                                output_price_per_1k=float(pricing.get('output_tokens', 0.2)),
                                currency=currency
                            )
            
            print(f"配置加载成功：{len(self.pricing_config)}个提供商")
            
        except Exception as e:
            print(f"配置加载失败：{e}")
            print("使用默认定价配置")
    
    def calculate_cost(self, provider: str, model: str, 
                      input_tokens: int, output_tokens: int) -> float:
        """计算单次调用成本"""
        try:
            # 获取定价配置
            if provider not in self.pricing_config:
                raise ValueError(f"未知的提供商：{provider}")
            
            if model not in self.pricing_config[provider]:
                # 使用该提供商第一个模型的定价
                model = list(self.pricing_config[provider].keys())[0]
                print(f"警告：模型{model}未找到定价，使用默认模型")
            
            pricing = self.pricing_config[provider][model]
            
            # 计算成本
            input_cost = (input_tokens / 1000) * pricing.input_price_per_1k
            output_cost = (output_tokens / 1000) * pricing.output_price_per_1k
            total_cost = input_cost + output_cost
            
            # 货币转换（转为人民币）
            if pricing.currency != Currency.CNY:
                exchange_rate = self.EXCHANGE_RATES.get(pricing.currency.value, 1.0)
                total_cost *= exchange_rate
            
            return round(total_cost, 4)
            
        except Exception as e:
            print(f"成本计算失败：{e}")
            # 返回估算成本
            return round((input_tokens + output_tokens) * 0.0002, 4)  # 估算值
    
    def record_call(self, provider: str, model: str,
                   input_tokens: int, output_tokens: int,
                   metadata: Optional[Dict] = None) -> APICallRecord:
        """记录API调用并计算成本"""
        cost_cny = self.calculate_cost(provider, model, input_tokens, output_tokens)
        
        record = APICallRecord(
            id=f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{provider}",
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            timestamp=datetime.now(),
            cost_cny=cost_cny,
            metadata=metadata or {}
        )
        
        self.records.append(record)
        return record
    
    def get_total_cost(self, start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> float:
        """获取总成本"""
        filtered_records = self._filter_records_by_date(start_date, end_date)
        return sum(record.cost_cny for record in filtered_records)
    
    def get_cost_by_provider(self, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> Dict[str, float]:
        """按提供商统计成本"""
        filtered_records = self._filter_records_by_date(start_date, end_date)
        
        cost_by_provider = {}
        for record in filtered_records:
            if record.provider not in cost_by_provider:
                cost_by_provider[record.provider] = 0.0
            cost_by_provider[record.provider] += record.cost_cny
        
        return cost_by_provider
    
    def get_cost_by_model(self, start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> Dict[str, float]:
        """按模型统计成本"""
        filtered_records = self._filter_records_by_date(start_date, end_date)
        
        cost_by_model = {}
        for record in filtered_records:
            model_key = f"{record.provider}/{record.model}"
            if model_key not in cost_by_model:
                cost_by_model[model_key] = 0.0
            cost_by_model[model_key] += record.cost_cny
        
        return cost_by_model
    
    def get_daily_cost(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取最近N天的每日成本"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        daily_cost = []
        for i in range(days):
            day_start = start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            day_records = self._filter_records_by_date(day_start, day_end)
            day_total = sum(record.cost_cny for record in day_records)
            
            daily_cost.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "total_cost": day_total,
                "call_count": len(day_records),
                "avg_cost_per_call": day_total / len(day_records) if day_records else 0
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
        data = {
            "export_time": datetime.now().isoformat(),
            "total_records": len(self.records),
            "total_cost_cny": self.get_total_cost(),
            "records": [
                {
                    "id": r.id,
                    "provider": r.provider,
                    "model": r.model,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "timestamp": r.timestamp.isoformat(),
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
        
        print("=" * 50)
        print("AI API成本监控摘要")
        print("=" * 50)
        print(f"总调用次数：{len(self.records)}")
        print(f"总成本：¥{total_cost:.2f} 人民币")
        print("\n按提供商统计：")
        for provider, cost in cost_by_provider.items():
            print(f"  {provider}: ¥{cost:.2f} ({cost/total_cost*100:.1f}%)")
        
        print("\n最近7天每日成本：")
        for day in daily_cost:
            print(f"  {day['date']}: ¥{day['total_cost']:.2f} ({day['call_count']}次调用)")
        print("=" * 50)


# 示例使用
if __name__ == "__main__":
    # 创建成本计算器
    calculator = CostCalculator()
    
    # 模拟一些API调用
    test_calls = [
        ("deepseek", "deepseek-v3.2", 1500, 800),
        ("openai", "gpt-4", 1200, 600),
        ("qianfan", "ERNIE-4.0", 800, 400),
        ("deepseek", "deepseek-r1", 2000, 1000),
    ]
    
    for provider, model, input_tokens, output_tokens in test_calls:
        record = calculator.record_call(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata={"purpose": "test"}
        )
        print(f"记录调用：{provider}/{model}, 成本：¥{record.cost_cny:.4f}")
    
    # 打印摘要
    calculator.print_summary()
    
    # 导出记录
    calculator.export_to_json("test_records.json")