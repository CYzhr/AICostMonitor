#!/usr/bin/env python3
"""
AICostMonitor 快速测试服务器
为项目访问提供即时演示界面
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# 创建应用
app = FastAPI(title="AICostMonitor Demo", description="AI API成本监控演示")

# 设置静态文件和模板目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

# 创建必要的目录
os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

# 设置模板引擎
templates = Jinja2Templates(directory=templates_dir)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 模拟数据存储
class DemoData:
    def __init__(self):
        self.users = [
            {"id": 1, "name": "测试用户1", "email": "test1@example.com", "plan": "专业版", "usage": 12500},
            {"id": 2, "name": "测试用户2", "email": "test2@example.com", "plan": "基础版", "usage": 3200},
            {"id": 3, "name": "测试用户3", "email": "test3@example.com", "plan": "企业版", "usage": 45800},
        ]
        
        self.providers = [
            {"name": "OpenAI", "cost": 125.50, "tokens": 125000, "models": ["GPT-4", "GPT-3.5"]},
            {"name": "DeepSeek", "cost": 89.30, "tokens": 89300, "models": ["DeepSeek-V3"]},
            {"name": "Claude", "cost": 67.80, "tokens": 67800, "models": ["Claude-3"]},
            {"name": "百度文心", "cost": 45.20, "tokens": 45200, "models": ["ERNIE-4.0"]},
        ]
        
        self.transactions = [
            {"id": 1, "user": "测试用户1", "amount": 29.99, "currency": "USD", "status": "成功", "date": "2026-03-05"},
            {"id": 2, "user": "测试用户2", "amount": 9.99, "currency": "USD", "status": "成功", "date": "2026-03-05"},
            {"id": 3, "user": "测试用户3", "amount": 199.99, "currency": "USD", "status": "处理中", "date": "2026-03-06"},
        ]

demo_data = DemoData()

# 创建演示页面
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """主页面"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "AICostMonitor - AI成本监控",
        "total_cost": sum(p["cost"] for p in demo_data.providers),
        "total_users": len(demo_data.users),
        "total_transactions": sum(t["amount"] for t in demo_data.transactions if t["status"] == "成功"),
    })

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """仪表板页面"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "仪表板",
        "providers": demo_data.providers,
        "users": demo_data.users,
    })

@app.get("/cost-analysis", response_class=HTMLResponse)
async def cost_analysis(request: Request):
    """成本分析页面"""
    return templates.TemplateResponse("cost_analysis.html", {
        "request": request,
        "title": "成本分析",
        "providers": demo_data.providers,
        "total_cost": sum(p["cost"] for p in demo_data.providers),
    })

@app.get("/payment", response_class=HTMLResponse)
async def payment_page(request: Request):
    """支付页面"""
    return templates.TemplateResponse("payment.html", {
        "request": request,
        "title": "支付管理",
        "transactions": demo_data.transactions,
        "paypal_account": "CYzhr",
        "paypal_link": "https://www.paypal.com/paypalme/Cyzhr",
        "alipay_account": "13703930873",
    })

@app.get("/api/stats")
async def get_stats():
    """获取统计数据的API"""
    return {
        "total_cost": sum(p["cost"] for p in demo_data.providers),
        "total_users": len(demo_data.users),
        "total_tokens": sum(p["tokens"] for p in demo_data.providers),
        "providers": demo_data.providers,
        "revenue": {
            "total": sum(t["amount"] for t in demo_data.transactions if t["status"] == "成功"),
            "monthly": 289.97,
            "growth": 15.3,
        }
    }

@app.post("/api/simulate-payment")
async def simulate_payment(
    amount: float = Form(...),
    currency: str = Form("USD"),
    provider: str = Form("paypal")
):
    """模拟支付API"""
    transaction_id = len(demo_data.transactions) + 1
    new_transaction = {
        "id": transaction_id,
        "user": "演示用户",
        "amount": amount,
        "currency": currency,
        "status": "成功",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "provider": provider,
    }
    demo_data.transactions.append(new_transaction)
    
    return {
        "success": True,
        "transaction_id": transaction_id,
        "message": f"支付 {amount}{currency} 成功",
        "transaction": new_transaction,
    }

# 创建基础HTML模板
def create_templates():
    """创建演示用的HTML模板"""
    
    # 主页面
    index_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding-top: 20px; background-color: #f8f9fa; }
        .hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 60px 0; border-radius: 10px; margin-bottom: 30px; }
        .card { transition: transform 0.3s; border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .card:hover { transform: translateY(-5px); }
        .stat-card { background: white; padding: 20px; border-radius: 10px; text-align: center; }
        .stat-value { font-size: 2.5rem; font-weight: bold; color: #667eea; }
        .stat-label { color: #6c757d; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="container">
        <nav class="navbar navbar-expand-lg navbar-light bg-white rounded shadow-sm mb-4">
            <div class="container-fluid">
                <a class="navbar-brand fw-bold text-primary" href="/">AICostMonitor</a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNav">
                    <ul class="navbar-nav ms-auto">
                        <li class="nav-item"><a class="nav-link" href="/">首页</a></li>
                        <li class="nav-item"><a class="nav-link" href="/dashboard">仪表板</a></li>
                        <li class="nav-item"><a class="nav-link" href="/cost-analysis">成本分析</a></li>
                        <li class="nav-item"><a class="nav-link" href="/payment">支付管理</a></li>
                    </ul>
                </div>
            </div>
        </nav>

        <div class="hero text-center">
            <h1 class="display-4 fw-bold">AI API成本监控</h1>
            <p class="lead">实时跟踪、分析和优化您的AI API使用成本</p>
            <a href="/dashboard" class="btn btn-light btn-lg mt-3">开始监控</a>
        </div>

        <div class="row mb-4">
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-value">${{ "%.2f"|format(total_cost) }}</div>
                    <div class="stat-label">本月总成本</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-value">{{ total_users }}</div>
                    <div class="stat-label">活跃用户</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-value">${{ "%.2f"|format(total_transactions) }}</div>
                    <div class="stat-label">累计收入</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="stat-value">4</div>
                    <div class="stat-label">AI提供商</div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-6">
                <div class="card h-100">
                    <div class="card-body">
                        <h5 class="card-title">🚀 核心功能</h5>
                        <ul class="list-unstyled">
                            <li class="mb-2">✅ 多提供商API成本实时计算</li>
                            <li class="mb-2">✅ 智能预算提醒和预警</li>
                            <li class="mb-2">✅ 详细的成本分析和报告</li>
                            <li class="mb-2">✅ 支持PayPal和支付宝支付</li>
                            <li class="mb-2">✅ 用户管理和权限控制</li>
                        </ul>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card h-100">
                    <div class="card-body">
                        <h5 class="card-title">📊 项目状态</h5>
                        <div class="progress mb-3">
                            <div class="progress-bar" style="width: 85%">核心功能 85%</div>
                        </div>
                        <div class="progress mb-3">
                            <div class="progress-bar bg-success" style="width: 100%">支付系统 100%</div>
                        </div>
                        <div class="progress mb-3">
                            <div class="progress-bar bg-info" style="width: 70%">国际AI适配 70%</div>
                        </div>
                        <p class="small text-muted mt-3">预计首笔收入：2026-03-09 ~ 2026-03-12</p>
                    </div>
                </div>
            </div>
        </div>

        <footer class="mt-5 text-center text-muted">
            <p>© 2026 AICostMonitor. 这是一个演示版本。</p>
            <p class="small">部署时间: {{ now().strftime('%Y-%m-%d %H:%M:%S') }}</p>
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""
    
    # 仪表板页面
    dashboard_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - AICostMonitor</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding-top: 20px; background-color: #f5f7fb; }
        .sidebar { background: white; border-radius: 10px; padding: 20px; height: 100%; }
        .main-content { padding-left: 30px; }
        .provider-card { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #667eea; }
        .cost-badge { background: #667eea; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold; }
        .user-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #28a745; }
    </style>
</head>
<body>
    <div class="container">
        <nav class="navbar navbar-light bg-white rounded shadow-sm mb-4">
            <div class="container-fluid">
                <a class="navbar-brand fw-bold text-primary" href="/">AICostMonitor</a>
                <span class="navbar-text">仪表板</span>
            </div>
        </nav>

        <div class="row">
            <div class="col-md-3">
                <div class="sidebar">
                    <h5>📊 导航</h5>
                    <ul class="nav flex-column">
                        <li class="nav-item mb-2"><a class="nav-link text-dark" href="/dashboard"><strong>📈 概览</strong></a></li>
                        <li class="nav-item mb-2"><a class="nav-link text-dark" href="/cost-analysis">💰 成本分析</a></li>
                        <li class="nav-item mb-2"><a class="nav-link text-dark" href="/payment">💳 支付管理</a></li>
                    </ul>
                    <hr>
                    <h6>📈 实时数据</h6>
                    <div id="realtime-data">
                        <p>总成本: <span class="cost-badge">加载中...</span></p>
                        <p>活跃用户: <span class="badge bg-success">{{ users|length }}</span></p>
                    </div>
                </div>
            </div>

            <div class="col-md-9 main-content">
                <h3 class="mb-4">AI提供商成本分析</h3>
                
                {% for provider in providers %}
                <div class="provider-card">
                    <div class="row align-items-center">
                        <div class="col-md-6">
                            <h5>{{ provider.name }}</h5>
                            <p class="text-muted mb-1">支持模型: {{ provider.models|join(', ') }}</p>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <div class="cost-badge">${{ "%.2f"|format(provider.cost) }}</div>
                                <small class="text-muted">本月成本</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <div class="text-primary fw-bold">{{ "{:,}".format(provider.tokens) }}</div>
                <small class="text-muted">Token使用量</small>
                            </div>
                        </div>
                    </div>
                </div>
                {% endfor %}

                <h4 class="mt-5 mb-3">用户概览</h4>
                {% for user in users %}
                <div class="user-card">
                    <div class="row">
                        <div class="col-md-4">
                            <strong>{{ user.name }}</strong><br>
                            <small class="text-muted">{{ user.email }}</small>
                        </div>
                        <div class="col-md-4">
                            <span class="badge bg-primary">{{ user.plan }}</span>
                        </div>
                        <div class="col-md-4 text-end">
                            <span class="text-muted">用量: {{ "{:,}".format(user.usage) }} tokens</span>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <script>
        // 获取实时数据
        async function fetchRealtimeData() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.querySelector('#realtime-data p:first-child .cost-badge').textContent = 
                    '$' + data.total_cost.toFixed(2);
            } catch (error) {
                console.error('获取数据失败:', error);
            }
        }
        
        // 初始加载
        fetchRealtimeData();
        // 每30秒更新一次
        setInterval(fetchRealtimeData, 30000);
    </script>
</body>
</html>"""
    
    # 支付页面
    payment_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - AICostMonitor</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding-top: 20px; background-color: #f5f7fb; }
        .payment-card { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .payment-method { border: 2px solid #e9ecef; border-radius: 10px; padding: 20px; margin-bottom: 20px; cursor: pointer; transition: all 0.3s; }
        .payment-method:hover { border-color: #667eea; background-color: #f8f9ff; }
        .payment-method.selected { border-color: #667eea; background-color: #f0f4ff; }
        .transaction-row { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #28a745; }
        .status-success { color: #28a745; }
        .status-pending { color: #ffc107; }
    </style>
</head>
<body>
    <div class="container">
        <nav class="navbar navbar-light bg-white rounded shadow-sm mb-4">
            <div class="container-fluid">
                <a class="navbar-brand fw-bold text-primary" href="/">AICostMonitor</a>
                <span class="navbar-text">支付管理</span>
            </div>
        </nav>

        <div class="row">
            <div class="col-md-8">
                <div class="payment-card mb-4">
                    <h3 class="mb-4">💳 支付演示</h3>
                    
                    <div class="row mb-4">
                        <div class="col-md-6">
                            <div class="payment-method" onclick="selectPayment('paypal')" id="paypal-method">
                                <h5>PayPal</h5>
                                <p class="text-muted">账户: {{ paypal_account }}</p>
                                <a href="{{ paypal_link }}" target="_blank" class="btn btn-outline-primary btn-sm">前往PayPal.me</a>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="payment-method" onclick="selectPayment('alipay')" id="alipay-method">
                                <h5>支付宝</h5>
                                <p class="text-muted">账户: {{ alipay_account }}</p>
                                <button class="btn btn-outline-success btn-sm" disabled>扫码支付</button>
                            </div>
                        </div>
                    </div>

                    <form id="payment-form" onsubmit="processPayment(event)">
                        <div class="mb-3">
                            <label class="form-label">支付金额</label>
                            <div class="input-group">
                                <input type="number" class="form-control" id="amount" value="29.99" step="0.01" min="1" required>
                                <select class="form-select" id="currency" style="max-width: 120px;">
                                    <option value="USD">USD</option>
                                    <option value="CNY">CNY</option>
                                </select>
                            </div>
                        </div>

                        <div class="mb-3">
                            <label class="form-label">支付方式</label>
                            <div>
                                <div class="form-check form-check-inline">
                                    <input class="form-check-input" type="radio" name="provider" id="provider-paypal" value="paypal" checked>
                                    <label class="form-check-label" for="provider-paypal">PayPal</label>
                                </div>
                                <div class="form-check form-check-inline">
                                    <input class="form-check-input" type="radio" name="provider" id="provider-alipay" value="alipay">
                                    <label class="form-check-label" for="provider-alipay">支付宝</label>
                                </div>
                            </div>
                        </div>

                        <button type="submit" class="btn btn-primary w-100 py-3">
                            <span id="submit-text">模拟支付 $29.99 USD</span>
                            <div id="loading-spinner" class="spinner-border spinner-border-sm d-none" role="status"></div>
                        </button>
                    </form>

                    <div id="payment-result" class="mt-4 d-none">
                        <div class="alert alert-success" role="alert">
                            <h5 class="alert-heading">✅ 支付成功！</h5>
                            <p id="result-message"></p>
                        </div>
                    </div>
                </div>

                <h4 class="mb-3">📋 交易记录</h4>
                {% for transaction in transactions %}
                <div class="transaction-row">
                    <div class="row align-items-center">
                        <div class="col-md-3">
                            <strong>#{{ transaction.id }}</strong><br>
                            <small class="text-muted">{{ transaction.date }}</small>
                        </div>
                        <div class="col-md-3">
                            {{ transaction.user }}
                        </div>
                        <div class="col-md-3">
                            <strong>{{ transaction.amount }} {{ transaction.currency }}</strong>
                        </div>
                        <div class="col-md-3 text-end">
                            <span class="badge {% if transaction.status == '成功' %}bg-success{% else %}bg-warning{% endif %}">
                                {{ transaction.status }}
                            </span>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>

            <div class="col-md-4">
                <div class="payment-card">
                    <h5 class="mb-3">📊 收入统计</h5>
                    
                    <div class="mb-4">
                        <div class="d-flex justify-content-between mb-2">
                            <span>累计收入</span>
                            <strong>${{ transactions|selectattr('status', 'equalto', '成功')|map(attribute='amount')|sum }}</strong>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>本月收入</span>
                            <strong>$289.97</strong>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>增长率</span>
                            <strong class="text-success">+15.3%</strong>
                        </div>
                    </div>

                    <hr>

                    <h6 class="mb-3">🎯 收入目标</h6>
                    <div class="progress mb-3" style="height: 25px;">
                        <div class="progress-bar bg-success" style="width: 65%">65%</div>
                    </div>
                    <p class="text-muted small">目标: $500/月 (当前: $289.97)</p>

                    <div class="alert alert-info mt-4">
                        <h6>💡 支付系统状态</h6>
                        <ul class="mb-0 small">
                            <li>✅ PayPal账户: {{ paypal_account }}</li>
                            <li>✅ 支付宝账户: {{ alipay_account }}</li>
                            <li>⏳ 首笔收入目标: 3月9-12日</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let selectedPayment = 'paypal';
        
        function selectPayment(method) {
            selectedPayment = method;
            document.querySelectorAll('.payment-method').forEach(el => {
                el.classList.remove('selected');
            });
            document.getElementById(method + '-method').classList.add('selected');
            document.getElementById('provider-' + method).checked = true;
        }
        
        function updateSubmitText() {
            const amount = document.getElementById('amount').value;
            const currency = document.getElementById('currency').value;
            document.getElementById('submit-text').textContent = `模拟支付 ${amount} ${currency}`;
        }
        
        async function processPayment(event) {
            event.preventDefault();
            
            const amount = document.getElementById('amount').value;
            const currency = document.getElementById('currency').value;
            const provider = document.querySelector('input[name="provider"]:checked').value;
            
            // 显示加载状态
            document.getElementById('submit-text').classList.add('d-none');
            document.getElementById('loading-spinner').classList.remove('d-none');
            
            try {
                const formData = new FormData();
                formData.append('amount', amount);
                formData.append('currency', currency);
                formData.append('provider', provider);
                
                const response = await fetch('/api/simulate-payment', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                // 显示结果
                document.getElementById('result-message').textContent = result.message;
                document.getElementById('payment-result').classList.remove('d-none');
                
                // 刷新页面以显示新交易
                setTimeout(() => {
                    location.reload();
                }, 2000);
                
            } catch (error) {
                alert('支付失败: ' + error.message);
            } finally {
                // 恢复按钮状态
                document.getElementById('submit-text').classList.remove('d-none');
                document.getElementById('loading-spinner').classList.add('d-none');
            }
        }
        
        // 初始化
        selectPayment('paypal');
        document.getElementById('amount').addEventListener('input', updateSubmitText);
        document.getElementById('currency').addEventListener('change', updateSubmitText);
        updateSubmitText();
    </script>
</body>
</html>"""
    
    # 创建模板文件
    templates = {
        "index.html": index_html,
        "dashboard.html": dashboard_html,
        "payment.html": payment_html,
        "cost_analysis.html": dashboard_html.replace("仪表板", "成本分析")  # 先用仪表板替代
    }
    
    for filename, content in templates.items():
        with open(os.path.join(templates_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)
    
    print(f"✅ 创建了 {len(templates)} 个演示模板")

# 启动服务器
if __name__ == "__main__":
    # 创建模板
    create_templates()
    
    # 启动服务器
    print("🚀 启动AICostMonitor演示服务器...")
    print("📡 访问地址: http://localhost:8000")
    print("📊 仪表板: http://localhost:8000/dashboard")
    print("💰 支付演示: http://localhost:8000/payment")
    print("\n按 Ctrl+C 停止服务器")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )