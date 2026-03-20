# AICostMonitor - AI API成本监控工具

[![在线演示](https://img.shields.io/badge/在线演示-点击访问-green)](http://106.13.110.26/)
[![GitHub](https://img.shields.io/badge/GitHub-开源项目-blue)](https://github.com/CYzhr/AICostMonitor)
[![SDK](https://img.shields.io/badge/SDK-v2.0-purple)](./sdk)

**零侵入AI API成本追踪 + 企业级负载均衡 + 智能缓存 + 故障转移**

## 🚀 新特性 (v2.0) - 超越LiteLLM

### 核心对比

| 功能 | AICostMonitor | LiteLLM |
|------|---------------|---------|
| 零侵入SDK | ✅ | ✅ |
| 多提供商 | ✅ (8+) | ✅ |
| USD/CNY计费 | ✅ 实时汇率 | ❌ 仅USD |
| 负载均衡 | ✅ 多Key轮询 | ✅ |
| 故障转移 | ✅ 自动重试切换 | ✅ |
| 缓存机制 | ✅ LRU缓存 | ✅ |
| 统一接口 | ✅ OpenAI SDK兼容 | ✅ |
| 性能 | ⚡ 650+ req/s | ✅ |

### 零侵入SDK接入

```python
import aicostmonitor

# 初始化 - 只需要一行代码！
aicostmonitor.init(api_key="your-api-key")

# 现有的OpenAI/Anthropic代码无需修改，成本自动追踪！
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
# 成本已自动记录！
```

### 企业级功能

#### 1. 负载均衡 (多API Key轮询)

```python
from aicostmonitor import LoadBalancer

lb = LoadBalancer(strategy="round_robin")

# 添加多个API Key
lb.add_key("openai", "sk-primary-key-1", weight=2)
lb.add_key("openai", "sk-primary-key-2", weight=1)
lb.add_key("openai", "sk-backup-key", weight=1)

# 自动轮询选择最佳Key
key = lb.get_key("openai")
# 故障自动隔离
lb.mark_failure("openai", "sk-primary-key-1")
lb.mark_success("openai", "sk-primary-key-1")
```

#### 2. 智能缓存 (相同请求)

```python
from aicostmonitor import CacheManager

cache = CacheManager(enabled=True, ttl=3600)

# 自动缓存相同请求
response = cache.get("openai", "gpt-4o", messages)
if response is None:
    response = make_api_call()
    cache.set("openai", "gpt-4o", messages, response)

# 查看缓存统计
print(cache.get_stats())
# {'hits': 150, 'misses': 50, 'hit_rate': '75.00%'}
```

#### 3. 故障转移 (自动重试+切换)

```python
from aicostmonitor import FailoverManager

failover = FailoverManager(max_retries=3, retry_delay=1.0)

# 自动重试 + 故障转移
result = failover.execute_with_failover(
    primary_api_call,
    fallback_func=backup_api_call
)

print(failover.get_stats())
# {'success_rate': '99.5%', 'failovers': 12}
```

#### 4. 统一接口 (兼容OpenAI SDK)

```python
from aicostmonitor import UnifiedClient

client = UnifiedClient(
    load_balancer=lb,
    cache=cache,
    failover=failover
)

# 完全兼容OpenAI SDK！
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)

# 自动识别提供商
# gpt-* -> OpenAI
# deepseek-* -> DeepSeek  
# ernie-* -> 百度千帆
```

## 📦 快速开始

### 方式1: 使用SDK（推荐）

```bash
pip install aicostmonitor
```

```python
import aicostmonitor

# 方式1: 手动初始化
aicostmonitor.init(api_key="aicm_xxx")

# 方式2: 环境变量自动初始化
# export AICOSTMONITOR_API_KEY=aicm_xxx
# import aicostmonitor  # 自动初始化
```

### 方式2: 使用包装客户端

```python
import aicostmonitor

# 替换原有的导入
# from openai import OpenAI  # 原来的
client = aicostmonitor.OpenAI(api_key="sk-...")  # 改成这个

# 所有功能完全相同，成本自动追踪！
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### 方式3: 手动追踪

```python
import aicostmonitor

aicostmonitor.init(api_key="aicm_xxx", auto_track=False)

# 手动记录调用
aicostmonitor.track(
    provider="openai",
    model="gpt-4o",
    input_tokens=1000,
    output_tokens=500
)
```

## 📊 性能测试报告

```
============================================================
AICostMonitor Performance Test Report
============================================================

测试: 106.13.110.26 (生产环境API)

[轻负载] 50 requests, 5 concurrent
  - 成功率: 100.00%
  - 平均延迟: 7.68ms
  - 吞吐量: 605.91 req/s

[中负载] 100 requests, 10 concurrent
  - 成功率: 100.00%
  - 平均延迟: 12.76ms
  - 吞吐量: 667.43 req/s

[高负载] 200 requests, 20 concurrent
  - 成功率: 100.00%
  - 平均延迟: 23.82ms
  - 吞吐量: 659.17 req/s

结论:
✓ 高可用性: 99%+ 成功率
✓ 优秀性能: <100ms 平均延迟
✓ 高吞吐量: >650 req/s
```

## 🔔 预算提醒

```python
import aicostmonitor

aicostmonitor.init(api_key="aicm_xxx")

# 设置月度预算
aicostmonitor.set_budget(
    limit=100.0,  # $100 美元
    currency="USD",
    period="monthly",
    webhook="https://your-webhook.com/alerts",
    alert_at=0.8  # 使用80%时提醒
)
```

## 📊 查看统计

```python
stats = aicostmonitor.get_stats()

print(f"总调用: {stats['total_calls']}")
print(f"总成本: ${stats['total_cost_usd']:.2f}")
print(f"按提供商: {stats['by_provider']}")
```

## 🎁 开始3天免费试用

### 通过API

```bash
curl -X POST https://aicostmonitor.com/api/trial/start \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "name": "Your Name"}'
```

### 通过网页

访问 [https://aicostmonitor.com/trial](https://aicostmonitor.com/trial)

## 💰 定价

| 计划 | 价格 | 功能 |
|------|------|------|
| 免费试用 | ¥0 | 3天免费，所有功能 |
| 基础版 | ¥49/月 | 无限API记录，基础统计 |
| 专业版 | ¥99/月 | 高级分析，多项目，负载均衡，缓存，故障转移 |
| 企业版 | ¥499/月 | 团队协作，优先支持，定制开发 |

## 📚 API文档

- 在线文档: http://106.13.110.26/docs
- SDK文档: [./sdk/README.md](./sdk)

## 🔧 自托管

```bash
git clone https://github.com/CYzhr/AICostMonitor.git
cd AICostMonitor
pip install -r requirements.txt
python src/main.py
```

## 📞 联系方式

- PayPal: https://www.paypal.com/paypalme/Cyzhr
- 问题反馈: GitHub Issues

## 🤝 贡献

欢迎提交PR和Issue！

---

**让AI成本透明可控，一行代码开始追踪！**
