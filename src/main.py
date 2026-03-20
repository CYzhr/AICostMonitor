#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AICostMonitor - AI API成本监控Web应用
基于FastAPI构建，支持USD/CNY双币计费
"""

import os
import sys
import yaml
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cost_calculator import CostCalculator, APICallRecord, Currency


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "data/aicost.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # API调用记录表（支持USD和CNY）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_calls (
            id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            cost_usd REAL NOT NULL,
            cost_cny REAL NOT NULL,
            timestamp DATETIME NOT NULL,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 用户配置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 提供商API密钥表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS provider_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT UNIQUE NOT NULL,
            api_key TEXT,
            api_secret TEXT,
            base_url TEXT,
            enabled INTEGER DEFAULT 1,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 预算提醒表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS budget_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            threshold_value REAL NOT NULL,
            threshold_currency TEXT DEFAULT 'USD',
            notify_email TEXT,
            notify_webhook TEXT,
            enabled INTEGER DEFAULT 1,
            last_triggered DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_calls_timestamp ON api_calls(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_calls_provider ON api_calls(provider)')
        
        conn.commit()
        conn.close()
    
    def save_call_record(self, record: APICallRecord):
        """保存API调用记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO api_calls 
        (id, provider, model, input_tokens, output_tokens, cost_usd, cost_cny, timestamp, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.id,
            record.provider,
            record.model,
            record.input_tokens,
            record.output_tokens,
            record.cost_usd,
            record.cost_cny,
            record.timestamp.isoformat(),
            json.dumps(record.metadata, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_calls(self, limit: int = 100) -> List[Dict]:
        """获取最近的API调用"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM api_calls 
        ORDER BY timestamp DESC 
        LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_cost_summary(self, days: int = 30) -> Dict[str, Any]:
        """获取成本摘要（支持USD和CNY）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总成本
        cursor.execute('SELECT SUM(cost_usd), SUM(cost_cny), COUNT(*) FROM api_calls')
        row = cursor.fetchone()
        total_cost_usd = row[0] or 0.0
        total_cost_cny = row[1] or 0.0
        total_calls = row[2] or 0
        
        # 按提供商统计
        cursor.execute('''
        SELECT provider, SUM(cost_usd) as cost_usd, SUM(cost_cny) as cost_cny, COUNT(*) as calls
        FROM api_calls 
        GROUP BY provider
        ORDER BY cost_usd DESC
        ''')
        by_provider = [
            {
                "provider": row[0], 
                "cost_usd": row[1], 
                "cost_cny": row[2], 
                "calls": row[3]
            }
            for row in cursor.fetchall()
        ]
        
        # 按模型统计
        cursor.execute('''
        SELECT provider, model, SUM(cost_usd) as cost_usd, SUM(cost_cny) as cost_cny, COUNT(*) as calls
        FROM api_calls 
        GROUP BY provider, model
        ORDER BY cost_usd DESC
        LIMIT 10
        ''')
        by_model = [
            {
                "provider": row[0],
                "model": row[1], 
                "cost_usd": row[2], 
                "cost_cny": row[3], 
                "calls": row[4]
            }
            for row in cursor.fetchall()
        ]
        
        # 按日期统计
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        cursor.execute('''
        SELECT 
            DATE(timestamp) as date,
            SUM(cost_usd) as daily_cost_usd,
            SUM(cost_cny) as daily_cost_cny,
            COUNT(*) as daily_calls
        FROM api_calls 
        WHERE timestamp >= ? AND timestamp <= ?
        GROUP BY DATE(timestamp)
        ORDER BY date ASC
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        daily_stats = [
            {
                "date": row[0], 
                "cost_usd": row[1], 
                "cost_cny": row[2], 
                "calls": row[3]
            }
            for row in cursor.fetchall()
        ]
        
        # 今日统计
        today = datetime.now().date()
        cursor.execute('''
        SELECT SUM(cost_usd), SUM(cost_cny), COUNT(*)
        FROM api_calls 
        WHERE DATE(timestamp) = ?
        ''', (today.isoformat(),))
        row = cursor.fetchone()
        today_stats = {
            "cost_usd": row[0] or 0.0,
            "cost_cny": row[1] or 0.0,
            "calls": row[2] or 0
        }
        
        # 本周统计
        week_start = today - timedelta(days=today.weekday())
        cursor.execute('''
        SELECT SUM(cost_usd), SUM(cost_cny), COUNT(*)
        FROM api_calls 
        WHERE DATE(timestamp) >= ?
        ''', (week_start.isoformat(),))
        row = cursor.fetchone()
        week_stats = {
            "cost_usd": row[0] or 0.0,
            "cost_cny": row[1] or 0.0,
            "calls": row[2] or 0
        }
        
        # 本月统计
        month_start = today.replace(day=1)
        cursor.execute('''
        SELECT SUM(cost_usd), SUM(cost_cny), COUNT(*)
        FROM api_calls 
        WHERE DATE(timestamp) >= ?
        ''', (month_start.isoformat(),))
        row = cursor.fetchone()
        month_stats = {
            "cost_usd": row[0] or 0.0,
            "cost_cny": row[1] or 0.0,
            "calls": row[2] or 0
        }
        
        conn.close()
        
        return {
            "total_cost_usd": total_cost_usd,
            "total_cost_cny": total_cost_cny,
            "total_calls": total_calls,
            "by_provider": by_provider,
            "by_model": by_model,
            "daily_stats": daily_stats,
            "today": today_stats,
            "week": week_stats,
            "month": month_stats
        }
    
    # 用户配置管理
    def get_user_config(self, key: str, default: Any = None) -> Any:
        """获取用户配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT config_value FROM user_config WHERE config_key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            try:
                return json.loads(row[0])
            except:
                return row[0]
        return default
    
    def set_user_config(self, key: str, value: Any):
        """设置用户配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO user_config (config_key, config_value, updated_at)
        VALUES (?, ?, ?)
        ''', (key, json.dumps(value), datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    # 提供商API密钥管理
    def get_provider_keys(self) -> List[Dict]:
        """获取所有提供商密钥配置"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM provider_keys ORDER BY provider')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_provider_key(self, provider: str) -> Optional[Dict]:
        """获取单个提供商密钥配置"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM provider_keys WHERE provider = ?', (provider,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def set_provider_key(self, provider: str, api_key: str = None, 
                        api_secret: str = None, base_url: str = None, enabled: bool = True):
        """设置提供商密钥配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO provider_keys 
        (provider, api_key, api_secret, base_url, enabled, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (provider, api_key, api_secret, base_url, 1 if enabled else 0, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def delete_provider_key(self, provider: str):
        """删除提供商密钥配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM provider_keys WHERE provider = ?', (provider,))
        conn.commit()
        conn.close()
    
    # 预算提醒管理
    def get_budget_alerts(self) -> List[Dict]:
        """获取所有预算提醒配置"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM budget_alerts ORDER BY alert_type')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def set_budget_alert(self, alert_type: str, threshold_value: float, 
                         threshold_currency: str = 'USD', notify_email: str = None,
                         notify_webhook: str = None, enabled: bool = True):
        """设置预算提醒"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO budget_alerts 
        (alert_type, threshold_value, threshold_currency, notify_email, notify_webhook, enabled)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (alert_type, threshold_value, threshold_currency, notify_email, notify_webhook, 1 if enabled else 0))
        conn.commit()
        conn.close()
    
    def delete_budget_alert(self, alert_id: int):
        """删除预算提醒"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM budget_alerts WHERE id = ?', (alert_id,))
        conn.commit()
        conn.close()


class AICostMonitor:
    """AI成本监控应用"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config.yaml"
        self.config = self.load_config()
        
        self.calculator = CostCalculator(config_path)
        self.db = DatabaseManager(self.config.get("database", {}).get("path", "data/aicost.db"))
        
        self.app = FastAPI(
            title="AICostMonitor",
            description="AI API成本监控工具 - 支持USD/CNY双币计费",
            version="2.0.0"
        )
        
        self.app.mount("/static", StaticFiles(directory="static"), name="static")
        self.templates = Jinja2Templates(directory="templates")
        
        self.setup_routes()
    
    def load_config(self) -> Dict:
        config_path = Path(self.config_path)
        if not config_path.exists():
            return {
                "server": {"host": "0.0.0.0", "port": 8000},
                "database": {"path": "data/aicost.db"}
            }
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            """首页"""
            summary = self.db.get_cost_summary(days=30)
            recent_calls = self.db.get_recent_calls(limit=50)
            exchange_rate = self.calculator.get_exchange_rate()
            display_currency = self.db.get_user_config("display_currency", "USD")
            providers = self.calculator.get_available_providers()
            
            return self.templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "summary": summary,
                    "recent_calls": recent_calls,
                    "providers": providers,
                    "exchange_rate": exchange_rate,
                    "display_currency": display_currency
                }
            )
        
        @self.app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard(request: Request):
            """仪表板页面"""
            summary = self.db.get_cost_summary(days=30)
            display_currency = self.db.get_user_config("display_currency", "USD")
            exchange_rate = self.calculator.get_exchange_rate()
            
            return self.templates.TemplateResponse(
                "dashboard.html",
                {
                    "request": request,
                    "summary": summary,
                    "display_currency": display_currency,
                    "exchange_rate": exchange_rate
                }
            )
        
        @self.app.get("/config", response_class=HTMLResponse)
        async def config_page(request: Request):
            """配置页面"""
            display_currency = self.db.get_user_config("display_currency", "USD")
            provider_keys = self.db.get_provider_keys()
            budget_alerts = self.db.get_budget_alerts()
            available_providers = self.calculator.get_available_providers()
            exchange_rate = self.calculator.get_exchange_rate()
            
            return self.templates.TemplateResponse(
                "config.html",
                {
                    "request": request,
                    "display_currency": display_currency,
                    "provider_keys": provider_keys,
                    "budget_alerts": budget_alerts,
                    "available_providers": available_providers,
                    "exchange_rate": exchange_rate
                }
            )
        
        # API端点
        @self.app.get("/api/summary")
        async def get_summary(days: int = 30):
            """获取成本摘要API"""
            summary = self.db.get_cost_summary(days=days)
            summary["exchange_rate"] = self.calculator.get_exchange_rate()
            return JSONResponse(summary)
        
        @self.app.get("/api/daily-stats")
        async def get_daily_stats(days: int = 30):
            """获取每日统计API"""
            summary = self.db.get_cost_summary(days=days)
            return JSONResponse(summary["daily_stats"])
        
        @self.app.post("/api/record")
        async def record_call(
            provider: str = Form(...),
            model: str = Form(...),
            input_tokens: int = Form(...),
            output_tokens: int = Form(...),
            metadata: Optional[str] = Form(None)
        ):
            """记录API调用"""
            try:
                meta_dict = {}
                if metadata:
                    meta_dict = json.loads(metadata)
                
                record = self.calculator.record_call(
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    metadata=meta_dict
                )
                
                self.db.save_call_record(record)
                
                return JSONResponse({
                    "success": True,
                    "record_id": record.id,
                    "cost_usd": record.cost_usd,
                    "cost_cny": record.cost_cny,
                    "message": "API调用记录成功"
                })
                
            except Exception as e:
                return JSONResponse({
                    "success": False,
                    "error": str(e)
                }, status_code=400)
        
        @self.app.get("/api/recent-calls")
        async def get_recent_calls(limit: int = 100):
            """获取最近的API调用"""
            calls = self.db.get_recent_calls(limit=limit)
            return JSONResponse(calls)
        
        @self.app.get("/api/providers")
        async def get_providers():
            """获取所有支持的提供商和模型"""
            providers = self.calculator.get_available_providers()
            return JSONResponse(providers)
        
        @self.app.get("/api/exchange-rate")
        async def get_exchange_rate():
            """获取汇率"""
            rate = self.calculator.get_exchange_rate()
            return JSONResponse({"usd_to_cny": rate})
        
        # 配置API
        @self.app.post("/api/config/currency")
        async def set_display_currency(currency: str = Form(...)):
            """设置显示货币"""
            if currency not in ["USD", "CNY"]:
                return JSONResponse({"success": False, "error": "无效的货币类型"}, status_code=400)
            
            self.db.set_user_config("display_currency", currency)
            return JSONResponse({"success": True, "currency": currency})
        
        @self.app.post("/api/config/provider-key")
        async def set_provider_key_api(
            provider: str = Form(...),
            api_key: str = Form(None),
            api_secret: str = Form(None),
            base_url: str = Form(None),
            enabled: bool = Form(True)
        ):
            """设置提供商API密钥"""
            self.db.set_provider_key(provider, api_key, api_secret, base_url, enabled)
            return JSONResponse({"success": True, "message": f"{provider} 配置已保存"})
        
        @self.app.delete("/api/config/provider-key/{provider}")
        async def delete_provider_key_api(provider: str):
            """删除提供商API密钥"""
            self.db.delete_provider_key(provider)
            return JSONResponse({"success": True, "message": f"{provider} 配置已删除"})
        
        @self.app.post("/api/config/budget-alert")
        async def set_budget_alert_api(
            alert_type: str = Form(...),
            threshold_value: float = Form(...),
            threshold_currency: str = Form("USD"),
            notify_email: str = Form(None),
            notify_webhook: str = Form(None),
            enabled: bool = Form(True)
        ):
            """设置预算提醒"""
            self.db.set_budget_alert(
                alert_type, threshold_value, threshold_currency, 
                notify_email, notify_webhook, enabled
            )
            return JSONResponse({"success": True, "message": "预算提醒已保存"})
        
        @self.app.delete("/api/config/budget-alert/{alert_id}")
        async def delete_budget_alert_api(alert_id: int):
            """删除预算提醒"""
            self.db.delete_budget_alert(alert_id)
            return JSONResponse({"success": True, "message": "预算提醒已删除"})
        
        @self.app.get("/api/pricing/{provider}")
        async def get_provider_pricing(provider: str):
            """获取提供商定价信息"""
            if provider not in self.calculator.pricing_config:
                return JSONResponse({"error": "未知的提供商"}, status_code=404)
            
            pricing_info = {}
            for model, pricing in self.calculator.pricing_config[provider].items():
                pricing_info[model] = {
                    "input_price_per_1k": pricing.input_price_per_1k,
                    "output_price_per_1k": pricing.output_price_per_1k,
                    "currency": pricing.currency.value
                }
            
            return JSONResponse({
                "provider": provider,
                "pricing": pricing_info
            })
        
        @self.app.get("/export")
        async def export_data(format: str = "json"):
            """导出数据"""
            if format == "json":
                summary = self.db.get_cost_summary(days=365)
                recent_calls = self.db.get_recent_calls(limit=10000)
                
                export_data = {
                    "export_time": datetime.now().isoformat(),
                    "exchange_rate": self.calculator.get_exchange_rate(),
                    "summary": summary,
                    "recent_calls": recent_calls
                }
                
                return JSONResponse(export_data)
            
            return JSONResponse({"error": "不支持的格式"}, status_code=400)
        
        # 支付相关API
        @self.app.post("/api/payment/create-order")
        async def create_payment_order(
            user_id: str = Form(...),
            amount: float = Form(...),
            currency: str = Form("USD"),
            description: str = Form(""),
            provider: str = Form("paypal")
        ):
            """创建支付订单"""
            order_id = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # 确保支付订单表存在
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_orders (
                order_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                description TEXT,
                provider TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                paid_at TEXT,
                payment_data TEXT
            )
            ''')
            
            cursor.execute('''
            INSERT INTO payment_orders 
            (order_id, user_id, amount, currency, description, provider, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, user_id, amount, currency, description, provider, 'pending', datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            # 返回PayPal支付链接
            paypal_link = f"https://www.paypal.com/paypalme/Cyzhr/{amount}{currency}"
            
            return JSONResponse({
                "success": True,
                "order_id": order_id,
                "paypal_link": paypal_link,
                "amount": amount,
                "currency": currency
            })
        
        @self.app.post("/api/payment/paypal-webhook")
        async def paypal_webhook(request: Request):
            """PayPal支付回调"""
            try:
                body = await request.json()
                
                # 记录支付事件
                order_id = body.get("resource", {}).get("invoice_id", "unknown")
                amount = body.get("resource", {}).get("amount", {}).get("value", 0)
                currency = body.get("resource", {}).get("amount", {}).get("currency_code", "USD")
                
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS payment_orders (
                    order_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    description TEXT,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    paid_at TEXT,
                    payment_data TEXT
                )
                ''')
                
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS payment_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT,
                    amount REAL,
                    currency TEXT,
                    status TEXT DEFAULT 'paid',
                    webhook_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # 记录支付通知
                cursor.execute('''
                INSERT INTO payment_notifications 
                (order_id, amount, currency, status, webhook_data)
                VALUES (?, ?, ?, ?, ?)
                ''', (order_id, amount, currency, 'paid', json.dumps(body, ensure_ascii=False)))
                
                # 更新订单状态
                cursor.execute('''
                UPDATE payment_orders SET status = 'paid', paid_at = ? 
                WHERE order_id = ?
                ''', (datetime.now().isoformat(), order_id))
                
                conn.commit()
                conn.close()
                
                return JSONResponse({"status": "ok"})
                
            except Exception as e:
                return JSONResponse({"status": "error", "message": str(e)}, status_code=400)
        
        @self.app.get("/api/payment/pending-notifications")
        async def get_pending_payment_notifications():
            """获取待通知的支付记录"""
            conn = sqlite3.connect(self.db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM payment_notifications 
            WHERE notified IS NULL OR notified = 0
            ORDER BY created_at DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            return JSONResponse({
                "count": len(rows),
                "payments": [dict(row) for row in rows]
            })
        
        @self.app.post("/api/payment/mark-notified")
        async def mark_payment_notified(notification_id: int = Form(...)):
            """标记支付已通知"""
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            ALTER TABLE payment_notifications ADD COLUMN notified INTEGER DEFAULT 0
            ''')
            
            cursor.execute('''
            UPDATE payment_notifications SET notified = 1 WHERE id = ?
            ''', (notification_id,))
            
            conn.commit()
            conn.close()
            
            return JSONResponse({"success": True})
    
    def run(self):
        """运行应用"""
        server_config = self.config.get("server", {})
        host = server_config.get("host", "0.0.0.0")
        port = server_config.get("port", 8000)
        debug = server_config.get("debug", False)
        
        print(f"启动 AICostMonitor v2.0.0...")
        print(f"访问地址：http://{host}:{port}")
        print(f"API文档：http://{host}:{port}/docs")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="debug" if debug else "info"
        )


def main():
    """主函数"""
    print("=" * 60)
    print("AICostMonitor - AI API成本监控工具 v2.0.0")
    print("支持 USD/CNY 双币计费")
    print("=" * 60)
    
    os.makedirs("static", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        print(f"配置文件 {config_path} 不存在，使用默认配置")
        if os.path.exists("config.example.yaml"):
            with open("config.example.yaml", "r", encoding="utf-8") as f:
                example_config = f.read()
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(example_config)
            print(f"已创建默认配置文件：{config_path}")
    
    app = AICostMonitor(config_path)
    app.run()


if __name__ == "__main__":
    main()
