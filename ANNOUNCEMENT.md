# AICostMonitor - 免费开源的AI API成本监控工具

## 问题

你在使用OpenAI、DeepSeek、Claude等AI API吗？
你是否知道每次调用花了多少钱？
你想监控和优化API成本吗？

## 解决方案

**AICostMonitor** - 一个简单的AI API成本监控工具

✅ **免费开源** - 完全自托管
✅ **简单集成** - 3行代码即可使用
✅ **多提供商支持** - OpenAI, DeepSeek, Claude, 百度文心, 通义千问等
✅ **实时统计** - 成本、调用次数、趋势分析

## 快速开始

```python
# 安装
pip install requests

# 集成示例（3行代码）
from integration import log_api_call

# 在你的AI调用后记录
log_api_call("openai", "gpt-4", input_tokens=1000, output_tokens=500)
```

## 在线演示

- 🌐 Dashboard: http://106.13.110.26/
- 📚 API文档: http://106.13.110.26/docs
- 💻 GitHub: https://github.com/CYzhr/AICostMonitor

## 功能

- 实时成本计算
- 多模型成本对比
- 预算提醒
- 数据导出
- Webhook集成

## 定价

- 免费版：无限API调用记录
- 专业版：¥99/月（高级分析、多项目管理）
- 企业版：¥499/月（团队协作、优先支持）

---

**感兴趣？** 
- 直接使用：http://106.13.110.26/
- 查看代码：https://github.com/CYzhr/AICostMonitor
- 问题反馈：GitHub Issues
