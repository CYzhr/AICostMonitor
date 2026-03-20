#!/usr/bin/env python3
"""
AICostMonitor 使用示例
展示零侵入接入方式
"""

# ============================================
# 方式1: 一行代码自动追踪OpenAI
# ============================================
from aicostmonitor import track

# 启用OpenAI自动追踪
track.openai()

# 正常使用OpenAI，成本自动记录
import openai
client = openai.OpenAI(api_key="sk-...")

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)

# 查看成本摘要
print(track.summary())


# ============================================
# 方式2: 自动追踪所有AI库
# ============================================
from aicostmonitor import auto_track

# 自动检测并追踪所有已安装的AI库
auto_track()
# 已启用: ['openai', 'anthropic']


# ============================================
# 方式3: 装饰器方式
# ============================================
from aicostmonitor import track

@track.cost
def call_gpt(prompt):
    return client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )


# ============================================
# 方式4: 手动记录
# ============================================
from aicostmonitor import track

# 手动记录调用
track.record(
    provider="openai",
    model="gpt-4",
    input_tokens=1000,
    output_tokens=500
)

# 计算成本（不记录）
cost = track.get_cost("openai", "gpt-4", 1000, 500)
print(f"Cost: ${cost['cost_usd']:.6f}")


# ============================================
# 方式5: 自定义配置
# ============================================
from aicostmonitor import init, track

# 自定义API地址
init(
    api_url="http://106.13.110.26",
    api_key="your-api-key",
    user_id="user-123",
    debug=True
)

# 启用追踪
track.openai()


# ============================================
# 完整示例: AI应用集成
# ============================================
from aicostmonitor import init, auto_track, track

# 初始化并启用自动追踪
init(debug=True)
auto_track()

# 你的AI应用代码
def chat_with_ai(user_message):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": user_message}]
    )
    return response.choices[0].message.content

# 查看今日成本
summary = track.summary(days=1)
print(f"今日成本: ${summary['today']['cost_usd']:.4f}")
print(f"今日调用: {summary['today']['calls']} 次")
