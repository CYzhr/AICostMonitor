#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AICostMonitor测试文件
"""

import sys
import os
import unittest
from datetime import datetime, timedelta

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from cost_calculator import CostCalculator, APICallRecord, Currency


class TestCostCalculator(unittest.TestCase):
    """成本计算器测试"""
    
    def setUp(self):
        """测试前设置"""
        self.calculator = CostCalculator()
    
    def test_calculate_cost_deepseek(self):
        """测试DeepSeek成本计算"""
        cost = self.calculator.calculate_cost(
            provider="deepseek",
            model="deepseek-v3.2",
            input_tokens=1000,
            output_tokens=500
        )
        
        # 预期成本：输入1*0.14 + 输出0.5*0.28 = 0.14 + 0.14 = 0.28
        expected_cost = 0.14 + 0.14
        self.assertAlmostEqual(cost, expected_cost, places=4)
    
    def test_calculate_cost_openai(self):
        """测试OpenAI成本计算（美元转人民币）"""
        cost = self.calculator.calculate_cost(
            provider="openai",
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500
        )
        
        # 预期成本：(1*1.0 + 0.5*2.0) * 7.2 = (1.0 + 1.0) * 7.2 = 14.4
        expected_cost = (1.0 + 1.0) * 7.2
        self.assertAlmostEqual(cost, expected_cost, places=4)
    
    def test_record_call(self):
        """测试API调用记录"""
        record = self.calculator.record_call(
            provider="deepseek",
            model="deepseek-v3.2",
            input_tokens=1500,
            output_tokens=800,
            metadata={"test": True}
        )
        
        self.assertIsInstance(record, APICallRecord)
        self.assertEqual(record.provider, "deepseek")
        self.assertEqual(record.model, "deepseek-v3.2")
        self.assertEqual(record.input_tokens, 1500)
        self.assertEqual(record.output_tokens, 800)
        self.assertIn("test", record.metadata)
        self.assertTrue(record.metadata["test"])
    
    def test_get_total_cost(self):
        """测试总成本计算"""
        # 添加多个记录
        self.calculator.record_call("deepseek", "deepseek-v3.2", 1000, 500)
        self.calculator.record_call("openai", "gpt-4", 800, 300)
        
        total_cost = self.calculator.get_total_cost()
        self.assertGreater(total_cost, 0)
    
    def test_get_cost_by_provider(self):
        """测试按提供商统计成本"""
        # 添加记录
        self.calculator.record_call("deepseek", "deepseek-v3.2", 1000, 500)
        self.calculator.record_call("deepseek", "deepseek-v3.2", 800, 400)
        self.calculator.record_call("openai", "gpt-4", 1200, 600)
        
        cost_by_provider = self.calculator.get_cost_by_provider()
        
        self.assertIn("deepseek", cost_by_provider)
        self.assertIn("openai", cost_by_provider)
        self.assertGreater(cost_by_provider["deepseek"], 0)
        self.assertGreater(cost_by_provider["openai"], 0)
    
    def test_get_daily_cost(self):
        """测试每日成本统计"""
        # 添加一些记录
        for i in range(5):
            self.calculator.record_call("deepseek", "deepseek-v3.2", 1000, 500)
        
        daily_cost = self.calculator.get_daily_cost(days=7)
        
        self.assertEqual(len(daily_cost), 7)
        
        # 检查今天应该有记录
        today = datetime.now().strftime("%Y-%m-%d")
        today_data = [d for d in daily_cost if d["date"] == today]
        self.assertGreater(len(today_data), 0)
    
    def test_unknown_provider_fallback(self):
        """测试未知提供商降级处理"""
        cost = self.calculator.calculate_cost(
            provider="unknown",
            model="unknown-model",
            input_tokens=1000,
            output_tokens=500
        )
        
        # 应该返回估算值而不是崩溃
        self.assertIsInstance(cost, float)
        self.assertGreater(cost, 0)


class TestAPICallRecord(unittest.TestCase):
    """API调用记录测试"""
    
    def test_record_creation(self):
        """测试记录创建"""
        record = APICallRecord(
            id="test123",
            provider="test",
            model="test-model",
            input_tokens=1000,
            output_tokens=500,
            timestamp=datetime.now(),
            cost_cny=0.5,
            metadata={"key": "value"}
        )
        
        self.assertEqual(record.id, "test123")
        self.assertEqual(record.provider, "test")
        self.assertEqual(record.input_tokens, 1000)
        self.assertEqual(record.cost_cny, 0.5)
        self.assertEqual(record.metadata["key"], "value")


if __name__ == "__main__":
    unittest.main()