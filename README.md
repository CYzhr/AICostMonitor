# AICostMonitor - AI API成本监控工具

[![在线演示](https://img.shields.io/badge/在线演示-点击访问-green)](http://106.13.110.26/)
[![GitHub](https://img.shields.io/badge/GitHub-开源项目-blue)](https://github.com/CYzhr/AICostMonitor)

**实时监控你的AI API成本，节省20-30%开支！**

## 🚀 在线演示

- 📊 Dashboard: http://106.13.110.26/
- 📚 API文档: http://106.13.110.26/docs
- 💻 快速集成: [examples/integration.py](examples/integration.py)

## ✨ 功能特性

- ✅ **实时成本计算** - DeepSeek、OpenAI、Claude、百度文心、通义千问等
- ✅ **多模型对比** - 找出最具性价比的模型
- ✅ **预算提醒** - 超出预算自动通知
- ✅ **数据导出** - JSON/CSV格式导出
- ✅ **简单集成** - 3行代码即可使用

## 📦 快速开始

### 方法1: 使用在线服务（推荐）

```python
import requests

# 记录API调用
requests.post("http://106.13.110.26/api/record", data={
    "provider": "openai",
    "model": "gpt-4",
    "input_tokens": 1000,
    "output_tokens": 500
})

# 查看成本统计
# 访问 http://106.13.110.26/dashboard
```

### 方法2: 自托管

```bash
git clone https://github.com/CYzhr/AICostMonitor.git
cd AICostMonitor
pip install -r requirements.txt
python src/main.py
```

## 💰 定价

| 计划 | 价格 | 功能 |
|------|------|------|
| 免费版 | ¥0 | 无限API调用记录、基础统计 |
| 专业版 | ¥99/月 | 高级分析、多项目管理、预算提醒 |
| 企业版 | ¥499/月 | 团队协作、优先支持、定制开发 |

## 📞 联系方式

- PayPal: https://www.paypal.com/paypalme/Cyzhr
- 问题反馈: GitHub Issues