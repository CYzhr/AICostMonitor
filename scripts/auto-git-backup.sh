#!/bin/bash
# Git 自动提交和备份脚本
# 每6小时执行一次，自动检测变化并提交，生成工作进展报告

set -e

# 配置Git用户信息（解决首次提交问题）
git config --local user.email "aicost@openclaw.ai" 2>/dev/null || git config user.email "aicost@openclaw.ai"
git config --local user.name "AICostMonitor" 2>/dev/null || git config user.name "AICostMonitor"

WORKSPACE_DIR="/root/.openclaw/workspace"
LOG_FILE="/root/.openclaw/workspace/memory/git-auto-backup.log"
REPORT_FILE="/root/.openclaw/workspace/memory/last-git-report.md"
BACKUP_DIR="/root/.openclaw/backups"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
GIT_REPO="$WORKSPACE_DIR"

# 确保备份目录存在
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 获取 Git 状态信息
get_git_status() {
    cd "$GIT_REPO"
    
    # 检查是否有未提交的更改
    if git status --porcelain | grep -q .; then
        CHANGED_FILES=$(git status --porcelain | wc -l)
        MODIFIED_FILES=$(git diff --name-only 2>/dev/null | wc -l || echo 0)
        UNTRACKED_FILES=$(git ls-files --others --exclude-standard | wc -l)
        
        echo "有 $CHANGED_FILES 个文件变更（修改：$MODIFIED_FILES，新增：$UNTRACKED_FILES）"
        
        # 显示主要变更文件（最多5个）
        echo "主要变更文件："
        git status --porcelain | head -5 | sed 's/^/  - /'
        
        if [ $CHANGED_FILES -gt 5 ]; then
            echo "  ... 还有 $(($CHANGED_FILES - 5)) 个文件"
        fi
    else
        echo "无文件变更"
    fi
}

# 执行 Git 提交
perform_git_commit() {
    cd "$GIT_REPO"
    
    # 检查是否在 Git 仓库中
    if [ ! -d ".git" ]; then
        log "错误：$GIT_REPO 不是 Git 仓库"
        return 1
    fi
    
    # 检查是否有变化
    if ! git status --porcelain | grep -q .; then
        log "无文件变化，跳过提交"
        return 0
    fi
    
    # 添加所有变更文件
    git add .
    
    # 生成提交消息
    COMMIT_COUNT=$(git status --porcelain | wc -l)
    COMMIT_MSG="自动提交 $TIMESTAMP ($COMMIT_COUNT 个文件)"
    
    # 提交
    git commit -m "$COMMIT_MSG"
    
    # 推送到远程仓库（如果有）
    if git remote -v | grep -q origin; then
        git push origin master 2>/dev/null || git push origin main 2>/dev/null || log "推送失败（可能需要配置远程仓库）"
    fi
    
    log "已提交 $COMMIT_COUNT 个文件：$COMMIT_MSG"
    echo "$COMMIT_COUNT"
}

# 创建备份
create_backup() {
    BACKUP_FILE="$BACKUP_DIR/workspace-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    
    # 排除一些不需要备份的目录
    tar --exclude='.git' \
        --exclude='node_modules' \
        --exclude='.cache' \
        --exclude='*.log' \
        -czf "$BACKUP_FILE" -C "$WORKSPACE_DIR" .
    
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "创建备份：$BACKUP_FILE ($BACKUP_SIZE)"
    
    # 清理旧备份（保留最近7天）
    find "$BACKUP_DIR" -name "workspace-backup-*.tar.gz" -mtime +7 -delete 2>/dev/null || true
    
    echo "$BACKUP_SIZE"
}

# 生成工作报告
generate_report() {
    cd "$GIT_REPO"
    
    REPORT="## 🚀 Git 自动化工作进展报告
**报告时间：** $TIMESTAMP
**执行周期：** 每6小时

### 📊 Git 仓库状态
- **仓库位置：** $GIT_REPO
- **当前分支：** $(git branch --show-current 2>/dev/null || echo '未设置')
- **提交历史：** $(git log --oneline | wc -l 2>/dev/null || echo 0) 次提交

### 🔄 本次执行结果
"

    # 获取 Git 状态
    GIT_STATUS=$(get_git_status)
    REPORT+="#### 1. 文件变更检测
$GIT_STATUS

"

    # 执行提交并获取结果
    COMMIT_RESULT=$(perform_git_commit 2>&1)
    if echo "$COMMIT_RESULT" | grep -q "已提交"; then
        COMMIT_COUNT=$(echo "$COMMIT_RESULT" | grep "已提交" | sed 's/.*已提交 \([0-9]*\).*/\1/')
        REPORT+="#### 2. 自动提交执行 ✅
- **提交状态：** 成功
- **提交数量：** $COMMIT_COUNT 个文件
- **提交消息：** 自动提交 $TIMESTAMP ($COMMIT_COUNT 个文件)

"
    elif echo "$COMMIT_RESULT" | grep -q "无文件变化"; then
        REPORT+="#### 2. 自动提交执行 ⏸️
- **提交状态：** 跳过（无文件变化）
- **说明：** 检测到工作空间无新增或修改文件

"
    else
        REPORT+="#### 2. 自动提交执行 ❌
- **提交状态：** 失败
- **错误信息：** $COMMIT_RESULT

"
    fi

    # 创建备份
    BACKUP_RESULT=$(create_backup 2>&1)
    if echo "$BACKUP_RESULT" | grep -q "创建备份"; then
        BACKUP_SIZE=$(echo "$BACKUP_RESULT" | grep "创建备份" | sed 's/.*创建备份：.*(\(.*\))/\1/')
        REPORT+="#### 3. 备份执行 ✅
- **备份状态：** 成功
- **备份大小：** $BACKUP_SIZE
- **备份位置：** /root/.openclaw/backups/
- **清理策略：** 自动保留最近7天备份

"
    else
        REPORT+="#### 3. 备份执行 ❌
- **备份状态：** 失败
- **错误信息：** $BACKUP_RESULT

"
    fi

    # 工作空间概览
    REPORT+="### 📁 工作空间概览
"

    # 统计各类型文件
    TOTAL_FILES=$(find "$WORKSPACE_DIR" -type f ! -path "*/.git/*" ! -name "*.log" | wc -l)
    CODE_FILES=$(find "$WORKSPACE_DIR" -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.go" -o -name "*.java" -o -name "*.cpp" -o -name "*.rs" \) ! -path "*/.git/*" | wc -l)
    DOC_FILES=$(find "$WORKSPACE_DIR" -type f \( -name "*.md" -o -name "*.txt" -o -name "*.rst" \) ! -path "*/.git/*" | wc -l)
    
    REPORT+="- **文件总数：** $TOTAL_FILES 个
- **代码文件：** $CODE_FILES 个
- **文档文件：** $DOC_FILES 个
- **目录结构：**
\`\`\`
$(ls -la "$WORKSPACE_DIR" | head -10)
\`\`\`

"

    # 项目健康度
    REPORT+="### 💪 项目健康度
- **Git 状态：** $(if [ -d "$GIT_REPO/.git" ]; then echo "✅ 已初始化"; else echo "❌ 未初始化"; fi)
- **备份状态：** ✅ 正常
- **日志记录：** ✅ 启用（$LOG_FILE）
- **下次执行：** 6小时后

---

**执行总结：** 自动化系统正常运行，将持续监控工作空间变化并定期备份。
"

    # 保存报告
    echo "$REPORT" > "$REPORT_FILE"
    log "工作报告已生成：$REPORT_FILE"
    
    # 输出报告摘要（用于 cron 任务）
    echo "📋 Git 自动化报告摘要："
    echo "========================"
    echo "1. Git 状态: $GIT_STATUS"
    echo "2. 提交结果: $(echo "$COMMIT_RESULT" | grep "已提交\|无文件变化\|错误" | head -1)"
    echo "3. 备份结果: $(echo "$BACKUP_RESULT" | grep "创建备份\|失败" | head -1)"
    echo "4. 文件统计: 总计 $TOTAL_FILES 文件（$CODE_FILES 代码，$DOC_FILES 文档）"
    echo "5. 详细报告: $REPORT_FILE"
    echo "========================"
}

# 主执行流程
log "开始执行 Git 自动提交和备份任务"
generate_report
log "任务执行完成"

# 显示报告摘要
tail -n 10 "$REPORT_FILE" 2>/dev/null || echo "报告生成完成"