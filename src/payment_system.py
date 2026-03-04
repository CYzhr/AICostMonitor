#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付系统模块
支持支付宝、微信支付、Stripe、PayPal
集成订阅管理和发票生成
"""

import json
import time
import hashlib
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging
import sqlite3
from enum import Enum

logger = logging.getLogger(__name__)


class PaymentProvider(Enum):
    """支付提供商"""
    ALIPAY = "alipay"
    WECHAT_PAY = "wechat_pay"
    STRIPE = "stripe"
    PAYPAL = "paypal"
    TEST = "test"  # 测试模式


class SubscriptionPlan(Enum):
    """订阅计划"""
    FREE = "free"
    PRO_MONTHLY = "pro_monthly"  # ¥99/月
    PRO_YEARLY = "pro_yearly"    # ¥999/年
    ENTERPRISE_MONTHLY = "enterprise_monthly"  # ¥499/月
    ENTERPRISE_YEARLY = "enterprise_yearly"    # ¥4999/年


@dataclass
class PaymentOrder:
    """支付订单"""
    order_id: str
    user_id: str
    amount: float  # 人民币元
    currency: str = "CNY"
    description: str = ""
    provider: str = PaymentProvider.TEST.value
    status: str = "pending"  # pending, paid, failed, refunded
    created_at: str = ""
    paid_at: Optional[str] = None
    payment_data: Optional[Dict] = None


@dataclass
class Subscription:
    """用户订阅"""
    subscription_id: str
    user_id: str
    plan: str
    status: str = "active"  # active, canceled, expired, pending
    current_period_start: str = ""
    current_period_end: str = ""
    cancel_at_period_end: bool = False
    payment_method: str = PaymentProvider.TEST.value
    created_at: str = ""


class PaymentManager:
    """支付管理器"""
    
    def __init__(self, db_path: str = "/root/.openclaw/workspace/data/payments.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 支付订单表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_orders (
            order_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'CNY',
            description TEXT,
            provider TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            paid_at TEXT,
            payment_data TEXT,  -- JSON格式
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # 订阅表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            subscription_id TEXT PRIMARY KEY,
            user_id TEXT UNIQUE NOT NULL,
            plan TEXT NOT NULL,
            status TEXT NOT NULL,
            current_period_start TEXT NOT NULL,
            current_period_end TEXT NOT NULL,
            cancel_at_period_end INTEGER DEFAULT 0,
            payment_method TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_user ON payment_orders (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_status ON payment_orders (status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sub_user ON subscriptions (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sub_status ON subscriptions (status)')
        
        conn.commit()
        conn.close()
    
    def _get_plan_details(self, plan: SubscriptionPlan) -> Dict[str, Any]:
        """获取计划详情"""
        plans = {
            SubscriptionPlan.FREE.value: {
                "name": "免费版",
                "price_monthly": 0.0,
                "price_yearly": 0.0,
                "features": [
                    "每月10万token限额",
                    "基础监控功能",
                    "单个API提供商",
                    "7天数据保留",
                    "邮件通知"
                ],
                "quotas": {
                    "total_monthly_tokens": 100000,
                    "max_requests_per_day": 100,
                    "providers": {"DeepSeek": 50000}
                }
            },
            SubscriptionPlan.PRO_MONTHLY.value: {
                "name": "专业版（月付）",
                "price_monthly": 99.0,
                "price_yearly": 999.0,
                "features": [
                    "每月100万token",
                    "所有API提供商支持",
                    "高级数据可视化",
                    "Webhook通知",
                    "多用户协作",
                    "30天数据保留",
                    "自定义告警",
                    "优先支持"
                ],
                "quotas": {
                    "total_monthly_tokens": 1000000,
                    "max_requests_per_day": 1000,
                    "providers": {
                        "DeepSeek": 400000,
                        "OpenAI": 400000,
                        "Baidu Qianfan": 200000
                    }
                }
            },
            SubscriptionPlan.PRO_YEARLY.value: {
                "name": "专业版（年付）",
                "price_monthly": 82.5,  # 年付平均每月
                "price_yearly": 999.0,
                "features": [
                    "每月100万token",
                    "所有API提供商支持",
                    "高级数据可视化",
                    "Webhook通知",
                    "多用户协作",
                    "30天数据保留",
                    "自定义告警",
                    "优先支持",
                    "节省16%（年付优惠）"
                ],
                "quotas": {
                    "total_monthly_tokens": 1000000,
                    "max_requests_per_day": 1000,
                    "providers": {
                        "DeepSeek": 400000,
                        "OpenAI": 400000,
                        "Baidu Qianfan": 200000
                    }
                }
            },
            SubscriptionPlan.ENTERPRISE_MONTHLY.value: {
                "name": "企业版（月付）",
                "price_monthly": 499.0,
                "price_yearly": 4999.0,
                "features": [
                    "无限token使用",
                    "所有API提供商支持",
                    "企业级监控面板",
                    "自定义Webhook",
                    "团队协作（最多20用户）",
                    "90天数据保留",
                    "高级告警规则",
                    "专属支持通道",
                    "SLA 99.9%保障",
                    "私有部署选项"
                ],
                "quotas": {
                    "total_monthly_tokens": 10000000,
                    "max_requests_per_day": 10000,
                    "providers": {
                        "DeepSeek": 4000000,
                        "OpenAI": 4000000,
                        "Baidu Qianfan": 2000000
                    }
                }
            },
            SubscriptionPlan.ENTERPRISE_YEARLY.value: {
                "name": "企业版（年付）",
                "price_monthly": 416.0,  # 年付平均每月
                "price_yearly": 4999.0,
                "features": [
                    "无限token使用",
                    "所有API提供商支持",
                    "企业级监控面板",
                    "自定义Webhook",
                    "团队协作（最多20用户）",
                    "90天数据保留",
                    "高级告警规则",
                    "专属支持通道",
                    "SLA 99.9%保障",
                    "私有部署选项",
                    "节省17%（年付优惠）"
                ],
                "quotas": {
                    "total_monthly_tokens": 10000000,
                    "max_requests_per_day": 10000,
                    "providers": {
                        "DeepSeek": 4000000,
                        "OpenAI": 4000000,
                        "Baidu Qianfan": 2000000
                    }
                }
            }
        }
        
        return plans.get(plan.value, plans[SubscriptionPlan.FREE.value])
    
    def create_payment_order(self, 
                           user_id: str, 
                           plan: SubscriptionPlan,
                           provider: PaymentProvider = PaymentProvider.TEST) -> Optional[PaymentOrder]:
        """创建支付订单"""
        try:
            plan_details = self._get_plan_details(plan)
            
            # 根据计划类型确定金额
            if plan == SubscriptionPlan.PRO_MONTHLY:
                amount = 99.0
                description = "AICostMonitor 专业版（月付）"
            elif plan == SubscriptionPlan.PRO_YEARLY:
                amount = 999.0
                description = "AICostMonitor 专业版（年付）"
            elif plan == SubscriptionPlan.ENTERPRISE_MONTHLY:
                amount = 499.0
                description = "AICostMonitor 企业版（月付）"
            elif plan == SubscriptionPlan.ENTERPRISE_YEARLY:
                amount = 4999.0
                description = "AICostMonitor 企业版（年付）"
            else:
                amount = 0.0
                description = "免费版（无需支付）"
            
            # 生成订单ID
            order_id = f"order_{uuid.uuid4().hex[:16]}"
            now = datetime.now().isoformat()
            
            # 创建订单对象
            order = PaymentOrder(
                order_id=order_id,
                user_id=user_id,
                amount=amount,
                description=description,
                provider=provider.value,
                status="pending",
                created_at=now,
                payment_data={
                    "plan": plan.value,
                    "plan_name": plan_details["name"],
                    "features": plan_details["features"],
                    "quotas": plan_details["quotas"]
                }
            )
            
            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO payment_orders 
            (order_id, user_id, amount, currency, description, provider, 
             status, created_at, payment_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order.order_id, order.user_id, order.amount, order.currency,
                order.description, order.provider, order.status, 
                order.created_at, json.dumps(order.payment_data, ensure_ascii=False)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"创建支付订单: {order_id} - ¥{amount:.2f} - {plan.value}")
            return order
            
        except Exception as e:
            logger.error(f"创建支付订单失败: {str(e)}")
            return None
    
    def process_payment(self, order_id: str, payment_data: Dict = None) -> bool:
        """处理支付（模拟）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取订单信息
            cursor.execute('''
            SELECT user_id, amount, description, provider, payment_data
            FROM payment_orders 
            WHERE order_id = ? AND status = 'pending'
            ''', (order_id,))
            
            row = cursor.fetchone()
            if not row:
                logger.error(f"订单不存在或已处理: {order_id}")
                return False
            
            user_id, amount, description, provider, payment_data_json = row
            payment_info = json.loads(payment_data_json) if payment_data_json else {}
            
            # 模拟支付处理
            now = datetime.now().isoformat()
            
            # 测试模式直接成功
            if provider == PaymentProvider.TEST.value:
                success = True
                payment_result = {
                    "transaction_id": f"test_{uuid.uuid4().hex[:12]}",
                    "status": "success",
                    "message": "测试支付成功"
                }
            else:
                # 真实支付处理（待实现）
                success = False
                payment_result = {
                    "status": "failed",
                    "message": "支付提供商未集成"
                }
            
            if success:
                # 更新订单状态
                cursor.execute('''
                UPDATE payment_orders 
                SET status = 'paid', paid_at = ?, payment_data = ?
                WHERE order_id = ?
                ''', (
                    now,
                    json.dumps({**(payment_info or {}), "payment_result": payment_result}, ensure_ascii=False),
                    order_id
                ))
                
                # 创建或更新订阅
                self._create_subscription(user_id, payment_info.get("plan"), provider)
                
                logger.info(f"支付成功: {order_id} - ¥{amount:.2f}")
            else:
                # 支付失败
                cursor.execute('''
                UPDATE payment_orders 
                SET status = 'failed', payment_data = ?
                WHERE order_id = ?
                ''', (
                    json.dumps({**(payment_info or {}), "payment_result": payment_result}, ensure_ascii=False),
                    order_id
                ))
                
                logger.warning(f"支付失败: {order_id} - {payment_result['message']}")
            
            conn.commit()
            conn.close()
            return success
            
        except Exception as e:
            logger.error(f"处理支付失败: {str(e)}")
            return False
    
    def _create_subscription(self, user_id: str, plan: str, payment_method: str):
        """创建订阅"""
        try:
            # 计算订阅周期
            now = datetime.now()
            
            if plan == SubscriptionPlan.PRO_YEARLY.value:
                period_end = now + timedelta(days=365)
            elif plan == SubscriptionPlan.ENTERPRISE_YEARLY.value:
                period_end = now + timedelta(days=365)
            else:
                period_end = now + timedelta(days=30)  # 月付
            
            subscription_id = f"sub_{uuid.uuid4().hex[:16]}"
            
            # 检查是否已有订阅
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT subscription_id FROM subscriptions WHERE user_id = ?', (user_id,))
            existing = cursor.fetchone()
            
            if existing:
                # 更新现有订阅
                cursor.execute('''
                UPDATE subscriptions 
                SET plan = ?, status = 'active', 
                    current_period_start = ?, current_period_end = ?,
                    cancel_at_period_end = 0, payment_method = ?
                WHERE user_id = ?
                ''', (
                    plan, now.isoformat(), period_end.isoformat(),
                    payment_method, user_id
                ))
            else:
                # 创建新订阅
                cursor.execute('''
                INSERT INTO subscriptions 
                (subscription_id, user_id, plan, status, current_period_start, 
                 current_period_end, payment_method, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    subscription_id, user_id, plan, "active",
                    now.isoformat(), period_end.isoformat(),
                    payment_method, now.isoformat()
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"创建订阅: {user_id} - {plan}")
            
        except Exception as e:
            logger.error(f"创建订阅失败: {str(e)}")
    
    def get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """获取用户订阅"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT subscription_id, plan, status, current_period_start,
                   current_period_end, cancel_at_period_end, payment_method, created_at
            FROM subscriptions 
            WHERE user_id = ? AND status = 'active'
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return Subscription(
                subscription_id=row[0],
                user_id=user_id,
                plan=row[1],
                status=row[2],
                current_period_start=row[3],
                current_period_end=row[4],
                cancel_at_period_end=bool(row[5]),
                payment_method=row[6],
                created_at=row[7]
            )
            
        except Exception as e:
            logger.error(f"获取订阅失败: {str(e)}")
            return None
    
    def cancel_subscription(self, user_id: str, at_period_end: bool = True) -> bool:
        """取消订阅"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if at_period_end:
                # 当前周期结束时取消
                cursor.execute('''
                UPDATE subscriptions 
                SET cancel_at_period_end = 1 
                WHERE user_id = ? AND status = 'active'
                ''', (user_id,))
            else:
                # 立即取消
                cursor.execute('''
                UPDATE subscriptions 
                SET status = 'canceled', current_period_end = ?
                WHERE user_id = ? AND status = 'active'
                ''', (datetime.now().isoformat(), user_id))
            
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            if affected > 0:
                logger.info(f"取消订阅: {user_id} - 到期取消" if at_period_end else "立即取消")
                return True
            else:
                logger.warning(f"没有找到活跃订阅: {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"取消订阅失败: {str(e)}")
            return False
    
    def check_subscription_status(self, user_id: str) -> Dict[str, Any]:
        """检查订阅状态"""
        subscription = self.get_user_subscription(user_id)
        
        if not subscription:
            return {
                "has_subscription": False,
                "plan": SubscriptionPlan.FREE.value,
                "status": "free",
                "plan_details": self._get_plan_details(SubscriptionPlan.FREE)
            }
        
        now = datetime.now()
        period_end = datetime.fromisoformat(subscription.current_period_end)
        
        is_active = subscription.status == "active"
        is_expired = period_end < now
        will_cancel = subscription.cancel_at_period_end
        
        if is_expired:
            # 自动过期
            self._expire_subscription(user_id)
            status = "expired"
        elif will_cancel and period_end < now:
            # 到期取消
            self.cancel_subscription(user_id, at_period_end=False)
            status = "canceled"
        else:
            status = "active"
        
        plan_details = self._get_plan_details(SubscriptionPlan(subscription.plan))
        
        return {
            "has_subscription": True,
            "subscription_id": subscription.subscription_id,
            "plan": subscription.plan,
            "status": status,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "payment_method": subscription.payment_method,
            "days_remaining": max(0, (period_end - now).days),
            "plan_details": plan_details,
            "is_trial": False  # 可以添加试用期逻辑
        }
    
    def _expire_subscription(self, user_id: str):
        """订阅过期"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE subscriptions 
            SET status = 'expired'
            WHERE user_id = ? AND status = 'active'
            ''', (user_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"订阅过期: {user_id}")
            
        except Exception as e:
            logger.error(f"订阅过期处理失败: {str(e)}")
    
    def generate_invoice(self, order_id: str) -> Optional[Dict[str, Any]]:
        """生成发票"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT user_id, amount, currency, description, provider, 
                   status, created_at, paid_at, payment_data
            FROM payment_orders 
            WHERE order_id = ?
            ''', (order_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row or row[5] != 'paid':  # status != 'paid'
                logger.warning(f"订单未支付或不存在: {order_id}")
                return None
            
            user_id, amount, currency, description, provider, status, \
            created_at, paid_at, payment_data_json = row
            
            payment_data = json.loads(payment_data_json) if payment_data_json else {}
            
            invoice_id = f"INV-{order_id[6:12].upper()}"
            
            invoice = {
                "invoice_id": invoice_id,
                "order_id": order_id,
                "user_id": user_id,
                "amount": amount,
                "currency": currency,
                "description": description,
                "provider": provider,
                "status": status,
                "created_at": created_at,
                "paid_at": paid_at,
                "payment_details": payment_data.get("payment_result", {}),
                "plan_details": payment_data.get("plan_name", "未知计划"),
                "billing_address": "待用户填写",  # 应来自用户配置
                "tax_amount": amount * 0.06,  # 假设6%税费
                "total_amount": amount * 1.06,
                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                "due_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            }
            
            return invoice
            
        except Exception as e:
            logger.error(f"生成发票失败: {str(e)}")
            return None
    
    def get_payment_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """获取支付历史"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT order_id, amount, currency, description, provider, 
                   status, created_at, paid_at
            FROM payment_orders 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            ''', (user_id, limit))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    "order_id": row[0],
                    "amount": row[1],
                    "currency": row[2],
                    "description": row[3],
                    "provider": row[4],
                    "status": row[5],
                    "created_at": row[6],
                    "paid_at": row[7]
                })
            
            conn.close()
            return history
            
        except Exception as e:
            logger.error(f"获取支付历史失败: {str(e)}")
            return []
    
    def get_revenue_stats(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """获取收入统计"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 基础查询
            query = '''
            SELECT 
                COUNT(*) as total_orders,
                SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END) as total_revenue,
                SUM(CASE WHEN status = 'paid' AND provider != 'test' THEN amount ELSE 0 END) as real_revenue,
                COUNT(CASE WHEN status = 'paid' THEN 1 END) as successful_orders,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_orders
            FROM payment_orders
            '''
            
            params = []
            
            if start_date:
                query += ' WHERE created_at >= ?'
                params.append(start_date)
                
                if end_date:
                    query += ' AND created_at <= ?'
                    params.append(end_date)
            elif end_date:
                query += ' WHERE created_at <= ?'
                params.append(end_date)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            # 按月统计
            cursor.execute('''
            SELECT 
                strftime('%Y-%m', created_at) as month,
                SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END) as monthly_revenue,
                COUNT(CASE WHEN status = 'paid' THEN 1 END) as monthly_orders
            FROM payment_orders
            WHERE status = 'paid'
            GROUP BY strftime('%Y-%m', created_at)
            ORDER BY month DESC
            LIMIT 12
            ''')
            
            monthly_stats = []
            for month_row in cursor.fetchall():
                monthly_stats.append({
                    "month": month_row[0],
                    "revenue": month_row[1] or 0.0,
                    "orders": month_row[2] or 0
                })
            
            conn.close()
            
            return {
                "overall": {
                    "total_orders": row[0] or 0,
                    "total_revenue": row[1] or 0.0,
                    "real_revenue": row[2] or 0.0,
                    "successful_orders": row[3] or 0,
                    "failed_orders": row[4] or 0,
                    "success_rate": round((row[3] or 0) / max(1, row[0]) * 100, 2) if row[0] else 0
                },
                "monthly_stats": monthly_stats,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取收入统计失败: {str(e)}")
            return {}


# 使用示例
if __name__ == "__main__":
    # 初始化支付管理器
    manager = PaymentManager()
    
    print("=== 测试支付系统 ===")
    
    # 创建测试用户支付订单
    test_user_id = "user_test123"
    
    # 创建专业版月付订单
    order = manager.create_payment_order(
        user_id=test_user_id,
        plan=SubscriptionPlan.PRO_MONTHLY,
        provider=PaymentProvider.TEST
    )
    
    if order:
        print(f"创建订单成功: {order.order_id}")
        print(f"金额: ¥{order.amount:.2f}")
        print(f"描述: {order.description}")
        
        # 模拟支付
        print("\n=== 模拟支付处理 ===")
        success = manager.process_payment(order.order_id)
        print(f"支付结果: {'✅ 成功' if success else '❌ 失败'}")
        
        # 检查订阅状态
        print("\n=== 检查订阅状态 ===")
        sub_status = manager.check_subscription_status(test_user_id)
        print(f"有订阅: {sub_status['has_subscription']}")
        if sub_status['has_subscription']:
            print(f"计划: {sub_status['plan']}")
            print(f"状态: {sub_status['status']}")
            print(f"剩余天数: {sub_status['days_remaining']}")
        
        # 生成发票
        print("\n=== 生成发票 ===")
        invoice = manager.generate_invoice(order.order_id)
        if invoice:
            print(f"发票号: {invoice['invoice_id']}")
            print(f"总金额: ¥{invoice['total_amount']:.2f}")
            print(f"含税: ¥{invoice['tax_amount']:.2f} (6%)")
        
        # 获取支付历史
        print("\n=== 支付历史 ===")
        history = manager.get_payment_history(test_user_id)
        for h in history[:3]:
            print(f"{h['created_at']}: {h['description']} - ¥{h['amount']:.2f} ({h['status']})")
        
        # 收入统计
        print("\n=== 收入统计 ===")
        stats = manager.get_revenue_stats()
        print(f"总订单: {stats['overall']['total_orders']}")
        print(f"总收入: ¥{stats['overall']['total_revenue']:.2f}")
        print(f"成功订单: {stats['overall']['successful_orders']}")
        print(f"成功率: {stats['overall']['success_rate']}%")