# AICostMonitor - AI API成本追踪

**一行代码追踪所有AI API成本，节省20-30%开支**

## 🚀 快速开始

### 安装

```bash
pip install aicostmonitor
```

### 零侵入使用

```python
from aicostmonitor import track

# 一行代码启用追踪
track.openai()

# 正常使用OpenAI，成本自动记录
import openai
client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)

# 查看成本
print(track.summary())
```

## ✨ 特性

- ✅ **零侵入** - 改一行代码就能用
- ✅ **自动追踪** - 无需手动记录
- ✅ **多提供商** - OpenAI、Anthropic、Google、DeepSeek等10+
- ✅ **实时汇率** - USD/CNY双币计费
- ✅ **仪表板** - 可视化成本趋势
- ✅ **预算提醒** - 超支自动通知

## 📊 仪表板

访问 http://106.13.110.26/dashboard 查看实时成本

## 💰 定价

| 计划 | 价格 | 功能 |
|------|------|------|
| 免费版 | $0 | 基础统计、7天数据 |
| 专业版 | $9.99/月 | 高级分析、无限数据、预算提醒 |
| 企业版 | $49.99/月 | 团队协作、API访问、优先支持 |

**3天免费试用** - 先试用后付费

## 📖 文档

- [API文档](http://106.13.110.26/docs)
- [GitHub](https://github.com/CYzhr/AICostMonitor)

## 💳 支付

PayPal: https://www.paypal.com/paypalme/Cyzhr
