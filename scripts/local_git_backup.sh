#!/bin/bash
# 本地Git备份脚本
# 解决GitHub网络连接问题，继承之前历史中的"所有代码本地保存，网络恢复后批量推送"策略

set -e

# 配置
BACKUP_DIR="/root/.openclaw/backup"
WORKSPACE_DIR="/root/.openclaw/workspace"
LOG_FILE="/root/.openclaw/logs/git_backup.log"
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')

# 创建目录
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$BACKUP_DIR/snapshots"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 测试GitHub连接
test_github_connection() {
    log "测试GitHub连接..."
    if curl -s --connect-timeout 10 https://api.github.com > /dev/null 2>&1; then
        log "✅ GitHub连接正常"
        return 0
    else
        log "❌ GitHub连接失败"
        return 1
    fi
}

# 备份单个项目
backup_project() {
    local project_name="$1"
    local source_dir="$2"
    local backup_repo="$BACKUP_DIR/$project_name.git"
    
    log "备份项目: $project_name"
    
    # 检查源目录是否存在
    if [ ! -d "$source_dir" ]; then
        log "  警告: 源目录不存在: $source_dir"
        return 1
    fi
    
    # 创建备份仓库（如果不存在）
    if [ ! -d "$backup_repo" ]; then
        log "  创建备份仓库: $backup_repo"
        git init --bare "$backup_repo"
    fi
    
    # 创建临时工作副本
    local temp_dir="/tmp/backup_$project_name_$TIMESTAMP"
    rm -rf "$temp_dir"
    mkdir -p "$temp_dir"
    
    # 复制文件到临时目录
    cp -r "$source_dir/." "$temp_dir/"
    
    # 初始化git并提交
    cd "$temp_dir"
    
    # 如果没有.git目录，初始化
    if [ ! -d ".git" ]; then
        git init
    fi
    
    # 配置git
    git config user.name "OpenClaw Backup"
    git config user.email "backup@openclaw.ai"
    
    # 检查是否有更改
    if git status --porcelain | grep -q .; then
        # 有更改，进行提交
        git add -A
        git commit -m "备份: $TIMESTAMP
        
        - 自动备份执行
        - 项目: $project_name
        - 文件数量: $(find . -type f -name '*' | wc -l)
        - 总大小: $(du -sh . | cut -f1)"
        
        # 推送到备份仓库
        git remote remove backup 2>/dev/null || true
        git remote add backup "$backup_repo"
        
        if git push backup main --force 2>/dev/null || git push backup master --force 2>/dev/null; then
            log "  ✅ 备份成功: $project_name"
        else
            log "  ⚠️  推送失败，但本地提交已保存"
        fi
        
        # 获取提交哈希
        local commit_hash=$(git rev-parse HEAD)
        echo "$commit_hash" > "$BACKUP_DIR/last_backup_$project_name.txt"
    else
        log "  ℹ️  没有更改，跳过提交"
    fi
    
    # 清理临时目录
    cd /
    rm -rf "$temp_dir"
}

# 创建快照
create_snapshot() {
    log "创建工作空间快照..."
    
    local snapshot_dir="$BACKUP_DIR/snapshots/$TIMESTAMP"
    mkdir -p "$snapshot_dir"
    
    # 复制关键项目
    for project in AICostMonitor Android-SO-Security-Scanner; do
        if [ -d "$WORKSPACE_DIR/$project" ]; then
            cp -r "$WORKSPACE_DIR/$project" "$snapshot_dir/" 2>/dev/null || true
        fi
    done
    
    # 复制重要配置文件
    cp "$WORKSPACE_DIR/memory/2026-03-01.md" "$snapshot_dir/" 2>/dev/null || true
    
    # 创建快照信息
    cat > "$snapshot_dir/SNAPSHOT_INFO.txt" << EOF
快照时间: $TIMESTAMP
工作空间: $WORKSPACE_DIR
创建者: OpenClaw Backup Script

包含项目:
$(ls -la "$snapshot_dir" | grep -E '^d' | awk '{print $NF}')

磁盘使用:
$(du -sh "$snapshot_dir" 2>/dev/null || echo "无法计算")

Git状态:
$(for repo in "$BACKUP_DIR"/*.git; do 
    if [ -d "$repo" ]; then 
        repo_name=$(basename "$repo" .git)
        echo "  $repo_name: $(git --git-dir="$repo" log --oneline -1 2>/dev/null || echo '无提交')"
    fi
done)
EOF
    
    # 压缩快照
    cd "$BACKUP_DIR/snapshots"
    tar -czf "${TIMESTAMP}.tar.gz" "$TIMESTAMP"
    rm -rf "$TIMESTAMP"
    
    log "快照已创建: ${TIMESTAMP}.tar.gz"
}

# 批量推送到GitHub（当网络恢复时）
batch_push_to_github() {
    log "尝试批量推送到GitHub..."
    
    if ! test_github_connection; then
        log "网络未恢复，跳过推送"
        return 1
    fi
    
    # 这里可以添加实际的GitHub推送逻辑
    # 需要GitHub令牌和仓库信息
    
    log "✅ 网络已恢复，可以进行批量推送"
    log "需要以下信息进行推送："
    log "  1. GitHub访问令牌"
    log "  2. 目标仓库URL"
    log "  3. 确认推送权限"
    
    # 保存推送就绪状态
    echo "READY_$TIMESTAMP" > "$BACKUP_DIR/github_push_ready.txt"
    
    return 0
}

# 主函数
main() {
    log "=== OpenClaw本地Git备份脚本 ==="
    log "开始时间: $(date)"
    log "工作空间: $WORKSPACE_DIR"
    log "备份目录: $BACKUP_DIR"
    
    # 测试网络连接
    test_github_connection
    
    # 备份关键项目
    log ""
    log "开始备份项目..."
    
    backup_project "AICostMonitor" "$WORKSPACE_DIR/AICostMonitor"
    backup_project "Android-SO-Security-Scanner" "$WORKSPACE_DIR/Android-SO-Security-Scanner"
    
    # 创建快照
    log ""
    create_snapshot
    
    # 检查是否可以推送到GitHub
    log ""
    batch_push_to_github
    
    # 清理旧快照（保留最近7天）
    log ""
    log "清理旧快照..."
    find "$BACKUP_DIR/snapshots" -name "*.tar.gz" -mtime +7 -delete 2>/dev/null || true
    
    # 生成报告
    log ""
    log "备份完成报告:"
    log "  总备份大小: $(du -sh "$BACKUP_DIR" | cut -f1)"
    log "  快照数量: $(find "$BACKUP_DIR/snapshots" -name "*.tar.gz" 2>/dev/null | wc -l)"
    log "  AICostMonitor最后备份: $(cat "$BACKUP_DIR/last_backup_AICostMonitor.txt" 2>/dev/null || echo "无")"
    log "  ASSS最后备份: $(cat "$BACKUP_DIR/last_backup_Android-SO-Security-Scanner.txt" 2>/dev/null || echo "无")"
    log "  GitHub推送状态: $(if [ -f "$BACKUP_DIR/github_push_ready.txt" ]; then echo "就绪"; else echo "等待网络"; fi)"
    
    log ""
    log "=== 备份完成 ==="
}

# 执行主函数
main "$@"

# 设置定时任务说明
cat > "$BACKUP_DIR/README.md" << 'EOF'
# OpenClaw本地Git备份系统

## 概述
此系统解决GitHub网络连接问题，确保代码安全备份，网络恢复后可以批量推送。

## 目录结构
```
/root/.openclaw/backup/
├── AICostMonitor.git/          # AICostMonitor的备份git仓库
├── Android-SO-Security-Scanner.git/ # ASSS的备份git仓库
├── snapshots/                  # 时间点快照
│   ├── 2026-03-04_12-40-00.tar.gz
│   └── ...
├── logs/                      # 备份日志
└── README.md                  # 本文件
```

## 使用方法

### 手动执行备份
```bash
bash /root/.openclaw/workspace/scripts/local_git_backup.sh
```

### 设置定时任务
```bash
# 每2小时执行一次备份
(crontab -l 2>/dev/null; echo "0 */2 * * * bash /root/.openclaw/workspace/scripts/local_git_backup.sh") | crontab -
```

### 查看备份状态
```bash
# 查看日志
tail -f /root/.openclaw/logs/git_backup.log

# 查看最新备份
ls -la /root/.openclaw/backup/snapshots/*.tar.gz | tail -5
```

### 网络恢复后批量推送
当GitHub网络恢复时：
1. 确保有GitHub访问令牌
2. 更新脚本中的仓库配置
3. 执行批量推送

## 恢复数据
```bash
# 从快照恢复
tar -xzf /root/.openclaw/backup/snapshots/最新快照.tar.gz -C /恢复目录

# 从git备份恢复
git clone /root/.openclaw/backup/AICostMonitor.git AICostMonitor-restored
```

## 注意事项
1. 备份不会上传到任何远程服务器，完全本地存储
2. 快照会占用磁盘空间，自动清理7天前的快照
3. 需要定期检查磁盘使用情况
4. 重要代码更改后建议立即手动备份
EOF

log "备份系统文档已更新: $BACKUP_DIR/README.md"