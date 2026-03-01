#!/bin/bash

# AICostMonitor部署脚本

set -e  # 遇到错误时退出

echo "开始部署 AICostMonitor..."

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 检查依赖
if ! command -v pip3 &> /dev/null; then
    echo "错误: 未找到pip3"
    exit 1
fi

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 创建必要目录
echo "创建项目目录..."
mkdir -p data logs static templates

# 检查配置文件
if [ ! -f "config.yaml" ]; then
    if [ -f "config.example.yaml" ]; then
        echo "复制配置文件..."
        cp config.example.yaml config.yaml
        echo "请编辑 config.yaml 配置你的API密钥"
    else
        echo "错误: 未找到配置文件"
        exit 1
    fi
fi

# 运行测试
echo "运行测试..."
if python -m pytest tests/ -v; then
    echo "测试通过!"
else
    echo "测试失败，请检查代码"
    exit 1
fi

# 启动应用
echo "启动 AICostMonitor..."
echo "访问地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止应用"

python src/main.py

echo "部署完成!"