# AICostMonitor - AI API成本监控工具

## 概述
AICostMonitor是一个开源的AI API成本监控工具，帮助开发者实时跟踪和管理多个AI提供商的API使用成本。

## 功能特性
- ✅ 实时计算DeepSeek、OpenAI、百度文心等API成本
- ✅ 多模型成本对比分析
- ✅ 用量统计和预算提醒
- ✅ 简单的Web管理界面
- ✅ 数据导出功能

## 支持提供商
- DeepSeek (qianfan/deepseek-v3.2)
- OpenAI (GPT-4, GPT-3.5)
- 百度文心系列
- 通义千问
- Claude系列 (如果可用)

## 技术栈
- Python 3.9+
- FastAPI (Web框架)
- SQLite (数据库)
- Jinja2 (模板引擎)
- Bootstrap 5 (前端样式)

## 快速开始

### 安装
```bash
git clone https://github.com/CYzhr/AICostMonitor.git
cd AICostMonitor
pip install -r requirements.txt
```

### 配置
1. 复制配置文件：
```bash
cp config.example.yaml config.yaml
```

2. 编辑`config.yaml`，添加你的API密钥：
```yaml
providers:
  deepseek:
    api_key: "your-deepseek-api-key"
    price_per_1k_input: 0.14  # 人民币/千token
    price_per_1k_output: 0.28
  openai:
    api_key: "your-openai-api-key"
    price_per_1k_input: 0.15  # 美元/千token
    price_per_1k_output: 0.30
```

### 运行
```bash
python src/main.py
```

访问 http://localhost:8000 查看监控面板。

## 贡献指南
欢迎贡献代码！请阅读[CONTRIBUTING.md](CONTRIBUTING.md)了解详细指南。

## 许可证
MIT License

## 联系方式
- 项目主页：https://github.com/CYzhr/AICostMonitor
- 问题反馈：GitHub Issues
- 功能建议：GitHub Discussions