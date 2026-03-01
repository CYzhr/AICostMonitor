# 贡献指南

欢迎为AICostMonitor贡献代码！以下是一些指导原则。

## 开发环境设置

1. 克隆仓库：
```bash
git clone https://github.com/CYzhr/AICostMonitor.git
cd AICostMonitor
```

2. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

## 代码规范

### Python代码规范
- 遵循PEP 8规范
- 使用类型提示
- 添加docstring
- 保持代码简洁

### 提交信息规范
使用常规的提交信息格式：
```
类型: 描述

详细说明（可选）
```

类型包括：
- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- style: 代码格式调整
- refactor: 代码重构
- test: 测试相关
- chore: 构建过程或辅助工具变动

## 开发流程

1. 创建新分支：
```bash
git checkout -b feature/your-feature-name
```

2. 开发完成后运行测试：
```bash
pytest
```

3. 提交代码：
```bash
git add .
git commit -m "feat: 添加新功能描述"
```

4. 推送到远程：
```bash
git push origin feature/your-feature-name
```

5. 创建Pull Request

## 项目结构

```
AICostMonitor/
├── src/                    # 源代码
│   ├── __init__.py
│   ├── main.py           # FastAPI主应用
│   ├── cost_calculator.py # 成本计算核心
│   └── providers/        # 各AI提供商实现
├── tests/                # 测试代码
├── static/              # 静态文件
├── templates/           # HTML模板
├── data/               # 数据文件
├── logs/               # 日志文件
├── config.yaml         # 配置文件
└── requirements.txt    # 依赖列表
```

## 添加新的AI提供商

1. 在`src/providers/`目录下创建新文件，例如`new_provider.py`

2. 实现基础类：
```python
from .base import BaseProvider

class NewProvider(BaseProvider):
    def __init__(self, api_key: str):
        super().__init__(name="new_provider", api_key=api_key)
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        # 实现成本计算逻辑
        pass
```

3. 在`src/cost_calculator.py`中注册新的提供商

## 测试

运行所有测试：
```bash
pytest
```

运行特定测试：
```bash
pytest tests/test_cost_calculator.py
```

## 问题反馈

如果你遇到问题或有建议：
1. 查看[Issues](https://github.com/CYzhr/AICostMonitor/issues)是否已有相关讨论
2. 创建新的Issue，描述问题和复现步骤
3. 提供环境信息：Python版本、操作系统等

## 许可证

本项目采用MIT许可证。贡献代码即表示你同意按照该许可证授权你的贡献。

感谢你的贡献！