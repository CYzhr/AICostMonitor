#!/bin/bash
# Git一致性管理器
# 定期检查并修复工作空间和项目的Git一致性

set -e

WORKSPACE_ROOT="/root/.openclaw/workspace"
PROJECT_DIR="$WORKSPACE_ROOT/AICostMonitor"
LOG_FILE="$WORKSPACE_ROOT/memory/git-consistency.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    echo "$1"
}

check_consistency() {
    log_message "🔍 检查Git一致性..."
    
    # 检查工作空间是否错误包含.git
    if [ -d "$WORKSPACE_ROOT/.git" ]; then
        log_message "❌ 工作空间错误包含.git目录"
        return 1
    fi
    
    # 检查项目目录是否有.git
    if [ ! -d "$PROJECT_DIR/.git" ]; then
        log_message "❌ 项目目录缺少.git目录"
        return 1
    fi
    
    # 检查项目与远程同步
    cd "$PROJECT_DIR"
    git fetch origin 2>/dev/null || {
        log_message "⚠️ 无法获取远程更新"
        return 2
    }
    
    LOCAL_HASH=$(git rev-parse HEAD)
    REMOTE_HASH=$(git rev-parse origin/main 2>/dev/null || echo "")
    
    if [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
        log_message "⚠️ 项目与远程有差异"
        return 2
    fi
    
    log_message "✅ Git一致性检查通过"
    return 0
}

fix_if_needed() {
    check_consistency
    STATUS=$?
    
    case $STATUS in
        0)
            log_message "✅ 无需修复"
            ;;
        1)
            log_message "🔧 执行结构修复..."
            # 调用修复脚本
            "$WORKSPACE_ROOT/scripts/git-structure-fix.sh"
            ;;
        2)
            log_message "🔄 执行同步修复..."
            cd "$PROJECT_DIR"
            git pull origin main 2>/dev/null || log_message "⚠️ 同步失败"
            ;;
    esac
}

# 主函数
main() {
    log_message "=== Git一致性检查开始 ==="
    fix_if_needed
    log_message "=== Git一致性检查结束 ==="
}

main "$@"
