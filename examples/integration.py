#!/usr/bin/env python3
"""
AICostMonitor 集成示例

使用方法：
1. 复制此文件到你的项目
2. 在你的AI API调用后调用 log_api_call()
3. 查看成本统计：http://106.13.110.26/dashboard
"""

import requests
from typing import Optional

# AICostMonitor服务地址
AICOSTMONITOR_URL = "http://106.13.110.26"

def log_api_call(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    metadata: Optional[dict] = None
) -> dict:
    """
    记录API调用到AICostMonitor
    
    参数:
        provider: 提供商名称 (openai, deepseek, anthropic, baidu, alibaba 等)
        model: 模型名称 (gpt-4, deepseek-v3, claude-3 等)
        input_tokens: 输入token数
        output_tokens: 输出token数
        metadata: 可选的元数据
    
    返回:
        包含成本信息的字典
    
    示例:
        result = log_api_call("openai", "gpt-4", 1000, 500)
        print(f"本次成本: ¥{result['cost_cny']}")
    """
    data = {
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens
    }
    
    if metadata:
        data["metadata"] = str(metadata)
    
    response = requests.post(f"{AICOSTMONITOR_URL}/api/record", data=data)
    return response.json()


def get_cost_summary(days: int = 30) -> dict:
    """
    获取成本摘要
    
    参数:
        days: 统计天数 (默认30天)
    
    返回:
        成本摘要字典
    """
    response = requests.get(f"{AICOSTMONITOR_URL}/api/summary", params={"days": days})
    return response.json()


# 使用示例
if __name__ == "__main__":
    # 示例1: 记录OpenAI调用
    result = log_api_call("openai", "gpt-4", 1000, 500)
    print(f"✅ OpenAI调用已记录: {result}")
    
    # 示例2: 记录DeepSeek调用
    result = log_api_call("deepseek", "deepseek-v3", 2000, 1000)
    print(f"✅ DeepSeek调用已记录: {result}")
    
    # 示例3: 查看成本统计
    summary = get_cost_summary()
    print(f"\n📊 成本统计:")
    print(f"   总成本: ¥{summary['total_cost']:.2f}")
    print(f"   总调用: {summary['total_calls']}次")
    for provider in summary['by_provider']:
        print(f"   {provider['provider']}: ¥{provider['cost']:.2f} ({provider['calls']}次)")
    
    print(f"\n🌐 查看详细统计: {AICOSTMONITOR_URL}/dashboard")
