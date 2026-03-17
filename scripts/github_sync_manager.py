#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub同步管理器
自主解决GitHub连接问题，实现可靠的代码同步
"""

import os
import time
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GitHubSyncManager:
    """GitHub同步管理器"""
    
    def __init__(self):
        self.workspace_dir = "/root/.openclaw/workspace"
        self.backup_dir = "/root/.openclaw/backup"
        self.log_file = "/root/.openclaw/logs/github_sync.log"
        self.state_file = "/root/.openclaw/data/github_sync_state.json"
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        
        # 项目配置
        self.projects = {
            "AICostMonitor": {
                "local_path": f"{self.workspace_dir}/AICostMonitor",
                "remote_url": "https://github.com/CYzhr/AICostMonitor.git",
                "branch": "main"
            },
            "Android-SO-Security-Scanner": {
                "local_path": f"{self.workspace_dir}/Android-SO-Security-Scanner", 
                "remote_url": "https://github.com/CYzhr/Android-SO-Security-Scanner.git",
                "branch": "main"
            }
        }
        
        # 加载状态
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """加载同步状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # 默认状态
        return {
            "last_sync_check": None,
            "last_successful_push": None,
            "pending_commits": {},
            "connection_status": "unknown",
            "error_count": 0,
            "backup_count": 0
        }
    
    def _save_state(self):
        """保存同步状态"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"保存状态失败: {str(e)}")
    
    def test_github_connection(self) -> bool:
        """测试GitHub连接"""
        try:
            # 测试连接github.com
            result = subprocess.run(
                ["curl", "-s", "--connect-timeout", "10", "-I", "https://github.com"],
                capture_output=True,
                text=True
            )
            
            connected = result.returncode == 0 and "HTTP" in result.stdout
            self.state["connection_status"] = "connected" if connected else "disconnected"
            self.state["last_sync_check"] = datetime.now().isoformat()
            
            if connected:
                logger.info("✅ GitHub连接正常")
            else:
                logger.warning("❌ GitHub连接失败")
                
            return connected
            
        except Exception as e:
            logger.error(f"测试连接异常: {str(e)}")
            self.state["connection_status"] = "error"
            return False
    
    def check_project_status(self, project_name: str) -> Dict:
        """检查项目状态"""
        project = self.projects.get(project_name)
        if not project:
            return {"error": f"项目不存在: {project_name}"}
        
        local_path = project["local_path"]
        if not os.path.exists(local_path):
            return {"error": f"本地目录不存在: {local_path}"}
        
        status = {
            "project": project_name,
            "local_exists": True,
            "has_git": False,
            "uncommitted_changes": False,
            "unpushed_commits": 0,
            "last_commit": None
        }
        
        try:
            # 检查git状态
            os.chdir(local_path)
            
            # 检查是否是git仓库
            if os.path.exists(".git"):
                status["has_git"] = True
                
                # 检查未提交的更改
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True
                )
                status["uncommitted_changes"] = len(result.stdout.strip()) > 0
                
                # 检查未推送的提交
                result = subprocess.run(
                    ["git", "log", "--oneline", f"origin/{project['branch']}..{project['branch']}"],
                    capture_output=True,
                    text=True
                )
                status["unpushed_commits"] = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
                
                # 获取最后提交
                result = subprocess.run(
                    ["git", "log", "-1", "--format=%H %s", "--date=short"],
                    capture_output=True,
                    text=True
                )
                if result.stdout:
                    commit_hash, *commit_msg = result.stdout.strip().split(' ', 1)
                    status["last_commit"] = {
                        "hash": commit_hash[:8],
                        "message": commit_msg[0] if commit_msg else "",
                        "full": result.stdout.strip()
                    }
            
        except Exception as e:
            status["error"] = str(e)
        
        return status
    
    def create_local_backup(self, project_name: str) -> bool:
        """创建本地备份"""
        project = self.projects.get(project_name)
        if not project:
            logger.error(f"项目不存在: {project_name}")
            return False
        
        local_path = project["local_path"]
        backup_repo = f"{self.backup_dir}/{project_name}.git"
        
        try:
            # 确保备份目录存在
            os.makedirs(backup_repo, exist_ok=True)
            
            # 如果备份仓库不存在，初始化
            if not os.path.exists(f"{backup_repo}/HEAD"):
                subprocess.run(["git", "init", "--bare", backup_repo], check=True)
            
            # 创建临时工作副本
            import tempfile
            import shutil
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # 复制文件
                if os.path.exists(local_path):
                    # 使用rsync保留权限和时间戳
                    subprocess.run(
                        ["rsync", "-av", "--delete", 
                         f"{local_path}/", 
                         f"{temp_dir}/"],
                        check=True
                    )
                
                # 初始化git并提交
                os.chdir(temp_dir)
                
                # 如果已经有.git，移除它（我们要重新初始化）
                if os.path.exists(".git"):
                    shutil.rmtree(".git")
                
                subprocess.run(["git", "init"], check=True)
                subprocess.run(["git", "config", "user.name", "OpenClaw Backup"], check=True)
                subprocess.run(["git", "config", "user.email", "backup@openclaw.ai"], check=True)
                
                # 检查是否有文件
                result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
                if result.stdout.strip():
                    # 有文件，提交
                    subprocess.run(["git", "add", "-A"], check=True)
                    commit_msg = f"备份: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n项目: {project_name}\n自动备份"
                    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
                    
                    # 推送到备份仓库
                    subprocess.run(["git", "remote", "add", "backup", backup_repo], check=True)
                    subprocess.run(["git", "push", "backup", "main", "--force"], 
                                  capture_output=True, text=True)
                    
                    logger.info(f"✅ 本地备份创建成功: {project_name}")
                    self.state["backup_count"] = self.state.get("backup_count", 0) + 1
                    return True
                else:
                    logger.info(f"ℹ️  没有文件需要备份: {project_name}")
                    return True
                    
        except Exception as e:
            logger.error(f"创建本地备份失败: {str(e)}")
            return False
    
    def push_to_github(self, project_name: str, force: bool = False) -> Tuple[bool, str]:
        """推送到GitHub"""
        if not self.test_github_connection():
            return False, "GitHub连接失败"
        
        project = self.projects.get(project_name)
        if not project:
            return False, f"项目不存在: {project_name}"
        
        local_path = project["local_path"]
        if not os.path.exists(local_path):
            return False, f"本地目录不存在: {local_path}"
        
        try:
            os.chdir(local_path)
            
            # 检查是否是git仓库
            if not os.path.exists(".git"):
                return False, "不是git仓库"
            
            # 检查是否有未提交的更改
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                # 有未提交的更改，先提交
                subprocess.run(["git", "add", "-A"], check=True)
                subprocess.run(["git", "commit", "-m", f"自动提交: {datetime.now().isoformat()}"], check=True)
            
            # 检查是否有未推送的提交
            result = subprocess.run(
                ["git", "log", "--oneline", f"origin/{project['branch']}..{project['branch']}"],
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip() and not force:
                return True, "没有需要推送的提交"
            
            # 推送到GitHub
            push_cmd = ["git", "push", "origin", project['branch']]
            if force:
                push_cmd.append("--force")
            
            result = subprocess.run(
                push_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                self.state["last_successful_push"] = datetime.now().isoformat()
                self.state["error_count"] = 0
                logger.info(f"✅ GitHub推送成功: {project_name}")
                return True, "推送成功"
            else:
                self.state["error_count"] = self.state.get("error_count", 0) + 1
                logger.error(f"❌ GitHub推送失败: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            error_msg = "推送超时"
            self.state["error_count"] = self.state.get("error_count", 0) + 1
            logger.error(f"❌ {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"推送异常: {str(e)}"
            self.state["error_count"] = self_state.get("error_count", 0) + 1
            logger.error(f"❌ {error_msg}")
            return False, error_msg
    
    def sync_all_projects(self) -> Dict[str, Dict]:
        """同步所有项目"""
        results = {}
        
        # 先测试连接
        github_connected = self.test_github_connection()
        
        for project_name in self.projects:
            logger.info(f"同步项目: {project_name}")
            
            # 1. 创建本地备份（无论网络状态）
            backup_success = self.create_local_backup(project_name)
            
            # 2. 如果网络连接正常，尝试推送
            push_success, push_message = False, "网络未连接"
            if github_connected:
                push_success, push_message = self.push_to_github(project_name)
            
            # 3. 记录结果
            results[project_name] = {
                "backup_success": backup_success,
                "push_success": push_success,
                "push_message": push_message,
                "github_connected": github_connected,
                "timestamp": datetime.now().isoformat()
            }
        
        # 保存状态
        self._save_state()
        
        return results
    
    def run_scheduled_sync(self, interval_minutes: int = 30):
        """运行定时同步"""
        import schedule
        import time
        
        logger.info(f"启动定时同步，间隔: {interval_minutes}分钟")
        
        def sync_job():
            logger.info("=== 执行定时同步 ===")
            results = self.sync_all_projects()
            logger.info(f"同步结果: {json.dumps(results, indent=2)}")
        
        # 安排任务
        schedule.every(interval_minutes).minutes.do(sync_job)
        
        # 立即执行一次
        sync_job()
        
        # 运行调度器
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            logger.info("同步服务停止")
    
    def get_sync_report(self) -> Dict:
        """获取同步报告"""
        report = {
            "state": self.state,
            "projects": {},
            "recommendations": []
        }
        
        # 检查每个项目
        for project_name in self.projects:
            status = self.check_project_status(project_name)
            report["projects"][project_name] = status
            
            # 生成建议
            if status.get("uncommitted_changes"):
                report["recommendations"].append(f"{project_name}: 有未提交的更改")
            if status.get("unpushed_commits", 0) > 0:
                report["recommendations"].append(f"{project_name}: 有{status['unpushed_commits']}个未推送的提交")
        
        # 网络建议
        if self.state.get("connection_status") != "connected":
            report["recommendations"].append("GitHub连接失败，使用本地备份模式")
        
        if self.state.get("error_count", 0) > 3:
            report["recommendations"].append("GitHub错误次数过多，建议检查网络配置")
        
        report["timestamp"] = datetime.now().isoformat()
        return report


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub同步管理器")
    parser.add_argument("--action", choices=["sync", "report", "test", "backup", "daemon"], 
                       default="report", help="执行动作")
    parser.add_argument("--project", help="指定项目名称")
    parser.add_argument("--interval", type=int, default=30, help="守护进程间隔分钟数")
    
    args = parser.parse_args()
    
    manager = GitHubSyncManager()
    
    if args.action == "sync":
        if args.project:
            # 同步单个项目
            manager.create_local_backup(args.project)
            if manager.test_github_connection():
                success, message = manager.push_to_github(args.project)
                print(f"推送结果: {success}, {message}")
            else:
                print("GitHub连接失败，仅创建本地备份")
        else:
            # 同步所有项目
            results = manager.sync_all_projects()
            print(json.dumps(results, indent=2))
    
    elif args.action == "report":
        report = manager.get_sync_report()
        print(json.dumps(report, indent=2))
    
    elif args.action == "test":
        connected = manager.test_github_connection()
        print(f"GitHub连接: {'✅ 正常' if connected else '❌ 失败'}")
    
    elif args.action == "backup":
        if args.project:
            success = manager.create_local_backup(args.project)
            print(f"备份结果: {'✅ 成功' if success else '❌ 失败'}")
        else:
            for project in manager.projects:
                success = manager.create_local_backup(project)
                print(f"{project}: {'✅ 成功' if success else '❌ 失败'}")
    
    elif args.action == "daemon":
        manager.run_scheduled_sync(args.interval)


if __name__ == "__main__":
    main()