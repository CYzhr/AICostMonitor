#!/bin/bash
# Git结构修复脚本
# 修复工作空间和项目Git目录错位问题

WORKSPACE_ROOT="/root/.openclaw/workspace"

# 备份工作空间.git
if [ -d "$WORKSPACE_ROOT/.git" ]; then
    BACKUP_DIR="$WORKSPACE_ROOT/backups/git-fixes/$(date +%Y%m%d-%H%M)"
    mkdir -p "$BACKUP_DIR"
    mv "$WORKSPACE_ROOT/.git" "$BACKUP_DIR/"
    echo "工作空间.git已备份到: $BACKUP_DIR"
fi

# 确保项目目录正确
PROJECT_DIR="$WORKSPACE_ROOT/AICostMonitor"
if [ ! -d "$PROJECT_DIR/.git" ]; then
    echo "项目目录缺少.git，需要重新初始化"
    # 这里可以添加重新初始化的逻辑
fi

echo "Git结构修复完成"
