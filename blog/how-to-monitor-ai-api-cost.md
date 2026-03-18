# 如何用3行代码监控你的AI API成本

## 问题

你在使用OpenAI、DeepSeek、Claude等AI API吗？你知道每次调用花了多少钱吗？

大多数开发者不知道，直到收到账单才发现超支了。

## 解决方案

AICostMonitor是一个免费开源的AI API成本监控工具，只需要3行代码就能集成。

### 快速开始

```python
import requests

# 记录API调用
requests.post("http://106.13.110.26/api/record", data={
    "provider": "openai",
    "model": "gpt-4",
    "input_tokens": 1000,
    "output_tokens": 500
})

# 返回: {"success": true, "cost_cny": 0.3}
```

### 查看统计

访问 http://106.13.110.26/dashboard 查看你的成本统计。

## 支持的提供商

- OpenAI (GPT-4, GPT-3.5)
- DeepSeek
- Claude
- 百度文心
- 通义千问
- 更多...

## 为什么选择AICostMonitor？

1. **免费开源** - 完全自托管，数据在你自己手中
2. **简单集成** - 不需要修改现有代码架构
3. **多提供商支持** - 一个工具监控所有AI API
4. **实时统计** - 知道每一分钱花在哪里

## 定价

- 免费版：无限API调用记录
- 专业版：¥99/月（高级分析）
- 企业版：¥499/月（团队协作）

## 链接

- 在线演示：http://106.13.110.26/
- GitHub：https://github.com/CYzhr/AICostMonitor
- 问题反馈：GitHub Issues

---

节省20-30%的AI成本，从今天开始！
