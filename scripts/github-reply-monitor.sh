#!/bin/bash
# ====================================
# GitHub Issue 回复自动监控脚本
# 用于: 检查之前留言的issue是否有人回复
# 作者: AICostMonitor Agent
# 更新: 2026-03-15
# ====================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

LOG_FILE="logs/github-monitor-$(date +%Y%m%d).log"
mkdir -p logs

log() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# ====================================
# 需要监控的Issue列表
# 格式: OWNER|REPO|IssueNumber|IssueTitle
# ====================================

MONITOR_ISSUES=(
    "BerriAI|litellm|23637|定价问题讨论"
    "AgentOps-AI|agentops|1258|功能请求"
    "Portkey-AI|gateway|XXX|AI网关成本"
    "langfuse|langfuse|XXX|LLM监控"
    "openai|evals|XXX|评估框架成本"
)

# ====================================
# 检查单个Issue的回复
# ====================================

check_issue() {
    local owner=$1
    local repo=$2
    local issue_num=$3
    local title=$4
    
    log "${YELLOW}检查: $owner/$repo #$issue_num${NC}"
    
    # 使用GitHub API获取issue评论
    local response=$(curl -s -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/$owner/$repo/issues/$issue_num/comments" 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        log "${RED}❌ API请求失败: $owner/$repo #$issue_num${NC}"
        return 1
    fi
    
    # 检查是否有新评论（评论数 > 0）
    local comment_count=$(echo "$response" | grep -o '"total_count":[0-9]*' | grep -o '[0-9]*' | head -1)
    
    if [ -z "$comment_count" ]; then
        comment_count=0
    fi
    
    if [ "$comment_count" -gt 0 ]; then
        log "${GREEN}✅ 发现 $comment_count 条评论!${NC}"
        # 这里可以添加邮件通知逻辑
        return 0
    else
        log "${YELLOW}⏳ 暂无回复${NC}"
        return 2
    fi
}

# ====================================
# 主循环
# ====================================

log "========================================="
log "GitHub Issue 监控开始"
log "========================================="

for issue_info in "${MONITOR_ISSUES[@]}"; do
    IFS='|' read -r owner repo issue_num title <<< "$issue_info"
    
    if [ "$issue_num" == "XXX" ]; then
        log "${RED}跳过: $owner/$repo - Issue未指定${NC}"
        continue
    fi
    
    check_issue "$owner" "$repo" "$issue_num" "$title"
done

log "========================================="
log "GitHub Issue 监控完成"
log "========================================="

# 简单报告输出
echo ""
echo "=== 今日检查摘要 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "检查数: ${#MONITOR_ISSUES[@]}"
echo "详细日志: $LOG_FILE"
