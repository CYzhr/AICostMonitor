#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预算告警系统
监控AI API使用成本，超过预算时发送告警
"""

import json
import yaml
import smtplib
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    threshold: float  # 阈值（人民币）
    period: str  # 时间周期：daily, weekly, monthly
    enabled: bool = True
    notification_type: List[str] = field(default_factory=lambda: ["log"])
    # 通知类型：log, email, webhook
    
    def __post_init__(self):
        if self.period not in ["daily", "weekly", "monthly"]:
            raise ValueError(f"无效的时间周期: {self.period}")


@dataclass
class AlertRecord:
    """告警记录"""
    id: str
    rule_name: str
    threshold: float
    actual_cost: float
    period: str
    triggered_at: datetime
    message: str
    notified: bool = False
    notified_at: Optional[datetime] = None


class BudgetAlertSystem:
    """预算告警系统"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化告警系统"""
        self.config_path = config_path
        self.config = self._load_config()
        self.rules: List[AlertRule] = []
        self.alerts: List[AlertRecord] = []
        self.db_path = self.config.get("database", {}).get("path", "data/aicost.db")
        
        self._init_rules()
        self._init_database()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path:
            return {}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"配置文件加载失败: {e}")
            return {}
    
    def _init_rules(self):
        """初始化告警规则"""
        # 默认规则
        default_rules = [
            AlertRule(
                name="每日预算告警",
                threshold=100.0,  # 100元/天
                period="daily",
                notification_type=["log", "email"]
            ),
            AlertRule(
                name="每周预算告警",
                threshold=500.0,  # 500元/周
                period="weekly",
                notification_type=["log"]
            ),
            AlertRule(
                name="每月预算告警",
                threshold=2000.0,  # 2000元/月
                period="monthly",
                notification_type=["log", "email"]
            )
        ]
        
        # 从配置文件加载自定义规则
        if "monitoring" in self.config and "budget_alerts" in self.config["monitoring"]:
            budget_config = self.config["monitoring"]["budget_alerts"]
            
            if budget_config.get("enabled", False):
                if "daily_limit" in budget_config:
                    default_rules[0].threshold = float(budget_config["daily_limit"])
                
                if "weekly_limit" in budget_config:
                    default_rules[1].threshold = float(budget_config["weekly_limit"])
                
                if "monthly_limit" in budget_config:
                    default_rules[2].threshold = float(budget_config["monthly_limit"])
        
        self.rules = default_rules
    
    def _init_database(self):
        """初始化告警数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建告警记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS budget_alerts (
            id TEXT PRIMARY KEY,
            rule_name TEXT NOT NULL,
            threshold REAL NOT NULL,
            actual_cost REAL NOT NULL,
            period TEXT NOT NULL,
            triggered_at DATETIME NOT NULL,
            message TEXT NOT NULL,
            notified INTEGER DEFAULT 0,
            notified_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_triggered_at ON budget_alerts(triggered_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_period ON budget_alerts(period)')
        
        conn.commit()
        conn.close()
    
    def check_budgets(self) -> List[AlertRecord]:
        """检查所有预算规则"""
        triggered_alerts = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            # 获取当前周期的成本
            current_cost = self._get_cost_for_period(rule.period)
            
            # 检查是否超过阈值
            if current_cost > rule.threshold:
                alert = self._create_alert(rule, current_cost)
                triggered_alerts.append(alert)
                
                # 保存到数据库
                self._save_alert(alert)
                
                # 发送通知
                self._send_notification(alert, rule.notification_type)
        
        return triggered_alerts
    
    def _get_cost_for_period(self, period: str) -> float:
        """获取指定时间周期的成本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        
        if period == "daily":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "monthly":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            conn.close()
            return 0.0
        
        cursor.execute('''
        SELECT SUM(cost_cny) FROM api_calls 
        WHERE timestamp >= ?
        ''', (start_date.isoformat(),))
        
        result = cursor.fetchone()[0]
        conn.close()
        
        return float(result or 0.0)
    
    def _create_alert(self, rule: AlertRule, actual_cost: float) -> AlertRecord:
        """创建告警记录"""
        alert_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{rule.name}"
        
        message = (
            f"⚠️ 预算告警: {rule.name}\n"
            f"预算阈值: ¥{rule.threshold:.2f}\n"
            f"实际成本: ¥{actual_cost:.2f}\n"
            f"超出金额: ¥{actual_cost - rule.threshold:.2f}\n"
            f"时间周期: {rule.period}\n"
            f"触发时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return AlertRecord(
            id=alert_id,
            rule_name=rule.name,
            threshold=rule.threshold,
            actual_cost=actual_cost,
            period=rule.period,
            triggered_at=datetime.now(),
            message=message
        )
    
    def _save_alert(self, alert: AlertRecord):
        """保存告警记录到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO budget_alerts 
        (id, rule_name, threshold, actual_cost, period, triggered_at, message, notified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.id,
            alert.rule_name,
            alert.threshold,
            alert.actual_cost,
            alert.period,
            alert.triggered_at.isoformat(),
            alert.message,
            0  # 未通知
        ))
        
        conn.commit()
        conn.close()
    
    def _send_notification(self, alert: AlertRecord, notification_types: List[str]):
        """发送通知"""
        for ntype in notification_types:
            try:
                if ntype == "log":
                    self._log_notification(alert)
                elif ntype == "email":
                    self._email_notification(alert)
                elif ntype == "webhook":
                    self._webhook_notification(alert)
            except Exception as e:
                print(f"发送{ntype}通知失败: {e}")
    
    def _log_notification(self, alert: AlertRecord):
        """日志通知"""
        print("=" * 50)
        print("预算告警通知")
        print("=" * 50)
        print(alert.message)
        print("=" * 50)
    
    def _email_notification(self, alert: AlertRecord):
        """邮件通知"""
        if "notifications" not in self.config.get("monitoring", {}):
            return
        
        email_config = self.config["monitoring"]["notifications"]
        email_to = email_config.get("email", "")
        
        if not email_to:
            return
        
        # 邮件配置（从配置文件读取或使用默认值）
        smtp_server = email_config.get("smtp_server", "smtp.gmail.com")
        smtp_port = email_config.get("smtp_port", 587)
        smtp_user = email_config.get("smtp_user", "")
        smtp_password = email_config.get("smtp_password", "")
        
        if not all([smtp_server, smtp_user, smtp_password]):
            print("邮件配置不完整，跳过邮件通知")
            return
        
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = email_to
            msg['Subject'] = f"AICostMonitor预算告警 - {alert.rule_name}"
            
            # 邮件正文
            body = alert.message.replace("\n", "<br>")
            msg.attach(MIMEText(body, 'html'))
            
            # 发送邮件
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            print(f"邮件告警已发送到: {email_to}")
            
        except Exception as e:
            print(f"发送邮件失败: {e}")
    
    def _webhook_notification(self, alert: AlertRecord):
        """Webhook通知"""
        if "notifications" not in self.config.get("monitoring", {}):
            return
        
        webhook_url = self.config["monitoring"]["notifications"].get("webhook", "")
        
        if not webhook_url:
            return
        
        try:
            import requests
            
            payload = {
                "alert_id": alert.id,
                "rule_name": alert.rule_name,
                "threshold": alert.threshold,
                "actual_cost": alert.actual_cost,
                "period": alert.period,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat()
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print(f"Webhook通知发送成功: {webhook_url}")
            else:
                print(f"Webhook通知失败: {response.status_code}")
                
        except ImportError:
            print("requests库未安装，无法发送Webhook通知")
        except Exception as e:
            print(f"发送Webhook通知失败: {e}")
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """获取最近的告警记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM budget_alerts 
        ORDER BY triggered_at DESC 
        LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_alert_summary(self, days: int = 7) -> Dict[str, Any]:
        """获取告警摘要"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days)
        
        # 总告警数
        cursor.execute('''
        SELECT COUNT(*) FROM budget_alerts 
        WHERE triggered_at >= ?
        ''', (start_date.isoformat(),))
        
        total_alerts = cursor.fetchone()[0] or 0
        
        # 按规则统计
        cursor.execute('''
        SELECT rule_name, COUNT(*) as count 
        FROM budget_alerts 
        WHERE triggered_at >= ?
        GROUP BY rule_name
        ORDER BY count DESC
        ''', (start_date.isoformat(),))
        
        by_rule = [
            {"rule": row[0], "count": row[1]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            "total_alerts": total_alerts,
            "period_days": days,
            "by_rule": by_rule
        }


# 使用示例
if __name__ == "__main__":
    # 测试告警系统
    alert_system = BudgetAlertSystem("config.example.yaml")
    
    print("测试预算告警系统...")
    
    # 检查预算
    triggered = alert_system.check_budgets()
    
    if triggered:
        print(f"触发告警: {len(triggered)} 条")
        for alert in triggered:
            print(f"  - {alert.rule_name}: ¥{alert.actual_cost:.2f} (阈值: ¥{alert.threshold:.2f})")
    else:
        print("未触发告警")
    
    # 获取最近告警
    recent = alert_system.get_recent_alerts(limit=5)
    print(f"最近告警记录: {len(recent)} 条")
    
    # 获取告警摘要
    summary = alert_system.get_alert_summary(days=30)
    print(f"30天告警摘要: {summary['total_alerts']} 条告警")