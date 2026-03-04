#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webhook集成模块
支持Slack、钉钉、企业微信、Discord通知
"""

import json
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class WebhookConfig:
    """Webhook配置"""
    name: str
    url: str
    type: str  # slack, dingtalk, wecom, discord
    enabled: bool = True
    headers: Optional[Dict[str, str]] = None
    template: Optional[str] = None


class WebhookManager:
    """Webhook管理器"""
    
    def __init__(self):
        self.webhooks: Dict[str, WebhookConfig] = {}
        self.default_templates = {
            "cost_alert": {
                "slack": self._slack_cost_alert_template,
                "dingtalk": self._dingtalk_cost_alert_template,
                "wecom": self._wecom_cost_alert_template,
                "discord": self._discord_cost_alert_template
            },
            "budget_exceeded": {
                "slack": self._slack_budget_exceeded_template,
                "dingtalk": self._dingtalk_budget_exceeded_template,
                "wecom": self._wecom_budget_exceeded_template,
                "discord": self._discord_budget_exceeded_template
            },
            "daily_report": {
                "slack": self._slack_daily_report_template,
                "dingtalk": self._dingtalk_daily_report_template,
                "wecom": self._wecom_daily_report_template,
                "discord": self._discord_daily_report_template
            }
        }
    
    def add_webhook(self, config: WebhookConfig) -> bool:
        """添加Webhook"""
        try:
            self.webhooks[config.name] = config
            logger.info(f"添加Webhook: {config.name} ({config.type})")
            return True
        except Exception as e:
            logger.error(f"添加Webhook失败: {str(e)}")
            return False
    
    def remove_webhook(self, name: str) -> bool:
        """移除Webhook"""
        if name in self.webhooks:
            del self.webhooks[name]
            logger.info(f"移除Webhook: {name}")
            return True
        return False
    
    def send_notification(self, 
                         event_type: str, 
                         data: Dict[str, Any],
                         webhook_names: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        发送通知
        
        Args:
            event_type: 事件类型
            data: 事件数据
            webhook_names: 指定要发送的Webhook名称列表，None表示发送所有
            
        Returns:
            每个Webhook的发送结果
        """
        results = {}
        
        # 确定要发送的Webhook
        targets = []
        if webhook_names:
            for name in webhook_names:
                if name in self.webhooks and self.webhooks[name].enabled:
                    targets.append(self.webhooks[name])
        else:
            targets = [wh for wh in self.webhooks.values() if wh.enabled]
        
        # 发送到每个目标
        for webhook in targets:
            try:
                success = self._send_to_webhook(webhook, event_type, data)
                results[webhook.name] = success
                if success:
                    logger.info(f"成功发送到 {webhook.name}")
                else:
                    logger.warning(f"发送到 {webhook.name} 失败")
            except Exception as e:
                logger.error(f"发送到 {webhook.name} 异常: {str(e)}")
                results[webhook.name] = False
        
        return results
    
    def _send_to_webhook(self, 
                        webhook: WebhookConfig, 
                        event_type: str, 
                        data: Dict[str, Any]) -> bool:
        """发送到单个Webhook"""
        # 选择模板
        if webhook.template:
            payload = json.loads(webhook.template)
        else:
            template_func = self.default_templates.get(event_type, {}).get(webhook.type)
            if template_func:
                payload = template_func(data)
            else:
                payload = self._default_template(data)
        
        # 发送请求
        headers = webhook.headers or {"Content-Type": "application/json"}
        
        try:
            response = requests.post(
                webhook.url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            # 不同平台的成功判断标准
            if webhook.type == "slack":
                return response.status_code == 200 and response.text == "ok"
            elif webhook.type == "dingtalk":
                return response.status_code == 200
            elif webhook.type == "wecom":
                return response.status_code == 200 and response.json().get("errcode") == 0
            elif webhook.type == "discord":
                return response.status_code in [200, 204]
            else:
                return response.status_code == 200
                
        except requests.RequestException as e:
            logger.error(f"请求异常: {str(e)}")
            return False
    
    # Slack模板
    def _slack_cost_alert_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 AI成本告警: {data.get('provider', '未知')}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*模型:*\n{data.get('model', '未知')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*成本:*\n¥{data.get('cost', 0):.4f}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*输入Token:*\n{data.get('input_tokens', 0):,}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*输出Token:*\n{data.get('output_tokens', 0):,}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*时间:* {data.get('timestamp', datetime.now().isoformat())}"
                    }
                }
            ]
        }
    
    # 钉钉模板
    def _dingtalk_cost_alert_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": "AI成本告警",
                "text": f"""## 🚨 AI成本告警\n
**提供商**: {data.get('provider', '未知')}\n
**模型**: {data.get('model', '未知')}\n
**成本**: ¥{data.get('cost', 0):.4f}\n
**输入Token**: {data.get('input_tokens', 0):,}\n
**输出Token**: {data.get('output_tokens', 0):,}\n
**时间**: {data.get('timestamp', datetime.now().isoformat())}\n
"""
            },
            "at": {
                "isAtAll": False
            }
        }
    
    # 企业微信模板
    def _wecom_cost_alert_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "msgtype": "markdown",
            "markdown": {
                "content": f"""<font color=\"warning\">AI成本告警</font>
>**提供商**: {data.get('provider', '未知')}
>**模型**: {data.get('model', '未知')}
>**成本**: <font color=\"warning\">¥{data.get('cost', 0):.4f}</font>
>**输入Token**: {data.get('input_tokens', 0):,}
>**输出Token**: {data.get('output_tokens', 0):,}
>**时间**: {data.get('timestamp', datetime.now().isoformat())}
"""
            }
        }
    
    # Discord模板
    def _discord_cost_alert_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "embeds": [
                {
                    "title": "🚨 AI成本告警",
                    "color": 16711680,  # 红色
                    "fields": [
                        {
                            "name": "提供商",
                            "value": data.get('provider', '未知'),
                            "inline": True
                        },
                        {
                            "name": "模型",
                            "value": data.get('model', '未知'),
                            "inline": True
                        },
                        {
                            "name": "成本",
                            "value": f"¥{data.get('cost', 0):.4f}",
                            "inline": True
                        },
                        {
                            "name": "输入Token",
                            "value": f"{data.get('input_tokens', 0):,}",
                            "inline": True
                        },
                        {
                            "name": "输出Token",
                            "value": f"{data.get('output_tokens', 0):,}",
                            "inline": True
                        }
                    ],
                    "timestamp": data.get('timestamp', datetime.now().isoformat()),
                    "footer": {
                        "text": "AICostMonitor"
                    }
                }
            ]
        }
    
    # 预算超支模板（Slack示例）
    def _slack_budget_exceeded_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 预算超支告警"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*当前月预算:* ¥{data.get('budget', 0):.2f}\n*已使用:* ¥{data.get('used', 0):.2f} ({data.get('percentage', 0):.1f}%)\n*超过限额:* ¥{data.get('exceeded', 0):.2f}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"建议措施:\n1. 检查高成本API调用\n2. 考虑优化模型选择\n3. 调整预算设置"
                    }
                }
            ]
        }
    
    # 每日报告模板（Slack示例）
    def _slack_daily_report_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        providers_summary = "\n".join([
            f"• {p['name']}: ¥{p['cost']:.2f} ({p['percentage']:.1f}%)"
            for p in data.get('providers', [])
        ])
        
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📊 每日成本报告 - {data.get('date', '今日')}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*总成本:* ¥{data.get('total_cost', 0):.2f}\n*API调用次数:* {data.get('api_calls', 0):,}\n*总Token数:* {data.get('total_tokens', 0):,}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*提供商分布:*\n{providers_summary}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*趋势:* {data.get('trend', '稳定')}\n*建议:* {data.get('suggestion', '成本控制良好')}"
                    }
                }
            ]
        }
    
    # 其他平台的预算超支和每日报告模板（简化实现）
    def _dingtalk_budget_exceeded_template(self, data):
        return self._dingtalk_cost_alert_template(data)
    
    def _wecom_budget_exceeded_template(self, data):
        return self._wecom_cost_alert_template(data)
    
    def _discord_budget_exceeded_template(self, data):
        return self._discord_cost_alert_template(data)
    
    def _dingtalk_daily_report_template(self, data):
        return self._dingtalk_cost_alert_template(data)
    
    def _wecom_daily_report_template(self, data):
        return self._wecom_cost_alert_template(data)
    
    def _discord_daily_report_template(self, data):
        return self._discord_cost_alert_template(data)
    
    def _default_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """默认模板"""
        return {
            "event": "cost_alert",
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "source": "AICostMonitor"
        }
    
    def test_connection(self, webhook_name: str) -> Dict[str, Any]:
        """测试Webhook连接"""
        if webhook_name not in self.webhooks:
            return {"success": False, "error": f"Webhook不存在: {webhook_name}"}
        
        webhook = self.webhooks[webhook_name]
        test_data = {
            "provider": "测试",
            "model": "test-model",
            "cost": 0.01,
            "input_tokens": 100,
            "output_tokens": 50,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            success = self._send_to_webhook(webhook, "cost_alert", test_data)
            return {"success": success, "webhook": webhook_name}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取Webhook统计"""
        enabled_count = sum(1 for wh in self.webhooks.values() if wh.enabled)
        disabled_count = len(self.webhooks) - enabled_count
        
        types_count = {}
        for wh in self.webhooks.values():
            types_count[wh.type] = types_count.get(wh.type, 0) + 1
        
        return {
            "total_webhooks": len(self.webhooks),
            "enabled": enabled_count,
            "disabled": disabled_count,
            "by_type": types_count,
            "last_updated": datetime.now().isoformat()
        }


# 使用示例
if __name__ == "__main__":
    # 初始化管理器
    manager = WebhookManager()
    
    # 添加Slack Webhook
    slack_config = WebhookConfig(
        name="slack-alerts",
        url="https://hooks.slack.com/services/...",
        type="slack",
        headers={"Content-Type": "application/json"}
    )
    manager.add_webhook(slack_config)
    
    # 添加钉钉Webhook
    dingtalk_config = WebhookConfig(
        name="dingtalk-alerts",
        url="https://oapi.dingtalk.com/robot/send?access_token=...",
        type="dingtalk"
    )
    manager.add_webhook(dingtalk_config)
    
    # 发送测试通知
    test_data = {
        "provider": "OpenAI",
        "model": "gpt-4",
        "cost": 0.125,
        "input_tokens": 500,
        "output_tokens": 250,
        "timestamp": datetime.now().isoformat()
    }
    
    results = manager.send_notification("cost_alert", test_data)
    print("发送结果:", results)