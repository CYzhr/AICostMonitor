#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AICostMonitor - AI API成本监控Web应用
基于FastAPI构建
"""

import os
import sys
import yaml
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, Request, Form, Depends
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
        """初始化数据库"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建API调用记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_calls (
            id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            cost_cny REAL NOT NULL,
            timestamp DATETIME NOT NULL,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建成本统计表（每日汇总）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_summary (
            date DATE PRIMARY KEY,
            total_calls INTEGER NOT NULL,
            total_cost_cny REAL NOT NULL,
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
        (id, provider, model, input_tokens, output_tokens, cost_cny, timestamp, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.id,
            record.provider,
            record.model,
            record.input_tokens,
            record.output_tokens,
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
        """获取成本摘要"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总成本
        cursor.execute('SELECT SUM(cost_cny) FROM api_calls')
        total_cost = cursor.fetchone()[0] or 0.0
        
        # 按提供商统计
        cursor.execute('''
        SELECT provider, SUM(cost_cny) as cost, COUNT(*) as calls
        FROM api_calls 
        GROUP BY provider
        ''')
        by_provider = [
            {"provider": row[0], "cost": row[1], "calls": row[2]}
            for row in cursor.fetchall()
        ]
        
        # 按日期统计（最近N天）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        cursor.execute('''
        SELECT 
            DATE(timestamp) as date,
            SUM(cost_cny) as daily_cost,
            COUNT(*) as daily_calls
        FROM api_calls 
        WHERE timestamp >= ? AND timestamp <= ?
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        daily_stats = [
            {"date": row[0], "cost": row[1], "calls": row[2]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            "total_cost": total_cost,
            "total_calls": sum(item["calls"] for item in by_provider),
            "by_provider": by_provider,
            "daily_stats": daily_stats
        }


class AICostMonitor:
    """AI成本监控应用"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化应用"""
        self.config_path = config_path or "config.yaml"
        self.config = self.load_config()
        
        # 初始化组件
        self.calculator = CostCalculator(config_path)
        self.db = DatabaseManager(self.config.get("database", {}).get("path", "data/aicost.db"))
        
        # FastAPI应用
        self.app = FastAPI(
            title="AICostMonitor",
            description="AI API成本监控工具",
            version="1.0.0"
        )
        
        # 设置静态文件和模板
        self.app.mount("/static", StaticFiles(directory="static"), name="static")
        self.templates = Jinja2Templates(directory="templates")
        
        # 注册路由
        self.setup_routes()
    
    def load_config(self) -> Dict:
        """加载配置文件"""
        config_path = Path(self.config_path)
        if not config_path.exists():
            # 使用默认配置
            return {
                "server": {
                    "host": "0.0.0.0",
                    "port": 8000
                },
                "database": {
                    "path": "data/aicost.db"
                }
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
            
            return self.templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "summary": summary,
                    "recent_calls": recent_calls,
                    "providers": list(self.calculator.pricing_config.keys())
                }
            )
        
        @self.app.get("/api/summary")
        async def get_summary(days: int = 30):
            """获取成本摘要API"""
            summary = self.db.get_cost_summary(days=days)
            return JSONResponse(summary)
        
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
                # 解析metadata
                meta_dict = {}
                if metadata:
                    meta_dict = json.loads(metadata)
                
                # 计算成本并记录
                record = self.calculator.record_call(
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    metadata=meta_dict
                )
                
                # 保存到数据库
                self.db.save_call_record(record)
                
                return JSONResponse({
                    "success": True,
                    "record_id": record.id,
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
        
        @self.app.get("/dashboard")
        async def dashboard(request: Request):
            """仪表板页面"""
            return self.templates.TemplateResponse(
                "dashboard.html",
                {"request": request}
            )
        
        @self.app.get("/config")
        async def config_page(request: Request):
            """配置页面"""
            return self.templates.TemplateResponse(
                "config.html",
                {
                    "request": request,
                    "config": self.config,
                    "pricing_config": self.calculator.pricing_config
                }
            )
        
        @self.app.get("/export")
        async def export_data(format: str = "json"):
            """导出数据"""
            if format == "json":
                # 导出JSON格式
                summary = self.db.get_cost_summary(days=365)
                recent_calls = self.db.get_recent_calls(limit=1000)
                
                export_data = {
                    "export_time": datetime.now().isoformat(),
                    "summary": summary,
                    "recent_calls": recent_calls
                }
                
                return JSONResponse(export_data)
            
            else:
                return JSONResponse({"error": "不支持的格式"}, status_code=400)
    
    def run(self):
        """运行应用"""
        server_config = self.config.get("server", {})
        host = server_config.get("host", "0.0.0.0")
        port = server_config.get("port", 8000)
        debug = server_config.get("debug", False)
        
        print(f"启动 AICostMonitor...")
        print(f"访问地址：http://{host}:{port}")
        print(f"API文档：http://{host}:{port}/docs")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info" if debug else "warning"
        )


# 创建模板文件
def create_templates():
    """创建HTML模板"""
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)
    
    # 创建index.html
    index_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AICostMonitor - AI API成本监控</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
    <style>
        .cost-card { transition: transform 0.2s; }
        .cost-card:hover { transform: translateY(-2px); }
        .provider-badge { font-size: 0.8rem; }
        .chart-container { height: 300px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="bi bi-graph-up"></i> AICostMonitor
            </a>
            <div class="navbar-nav">
                <a class="nav-link" href="/">首页</a>
                <a class="nav-link" href="/dashboard">仪表板</a>
                <a class="nav-link" href="/config">配置</a>
                <a class="nav-link" href="/docs">API文档</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <!-- 概览卡片 -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card cost-card bg-primary text-white">
                    <div class="card-body">
                        <h5 class="card-title">总成本</h5>
                        <h2 class="card-text">¥{{ "%.2f"|format(summary.total_cost) }}</h2>
                        <p class="card-text">{{ summary.total_calls }} 次调用</p>
                    </div>
                </div>
            </div>
            
            <div class="col-md-9">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">成本分布</h5>
                        <div class="row">
                            {% for item in summary.by_provider %}
                            <div class="col-md-3">
                                <div class="d-flex justify-content-between">
                                    <span class="badge bg-secondary provider-badge">{{ item.provider }}</span>
                                    <span>¥{{ "%.2f"|format(item.cost) }}</span>
                                </div>
                                <div class="progress mt-1" style="height: 8px;">
                                    {% set percentage = (item.cost / summary.total_cost * 100) if summary.total_cost > 0 else 0 %}
                                    <div class="progress-bar" role="progressbar" style="width: {{ percentage }}%"></div>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 记录API调用 -->
        <div class="card mb-4">
            <div class="card-header">
                <h5 class="mb-0">记录API调用</h5>
            </div>
            <div class="card-body">
                <form id="recordForm" class="row g-3">
                    <div class="col-md-3">
                        <label class="form-label">提供商</label>
                        <select class="form-select" id="provider" required>
                            <option value="">选择提供商</option>
                            {% for provider in providers %}
                            <option value="{{ provider }}">{{ provider }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">模型</label>
                        <input type="text" class="form-control" id="model" placeholder="如：deepseek-v3.2" required>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">输入token数</label>
                        <input type="number" class="form-control" id="input_tokens" min="0" required>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">输出token数</label>
                        <input type="number" class="form-control" id="output_tokens" min="0" required>
                    </div>
                    <div class="col-md-2 d-flex align-items-end">
                        <button type="submit" class="btn btn-primary w-100">
                            <i class="bi bi-save"></i> 记录
                        </button>
                    </div>
                </form>
                <div id="recordResult" class="mt-2"></div>
            </div>
        </div>

        <!-- 最近调用记录 -->
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">最近API调用记录</h5>
                <a href="/export?format=json" class="btn btn-sm btn-outline-primary">
                    <i class="bi bi-download"></i> 导出数据
                </a>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>时间</th>
                                <th>提供商</th>
                                <th>模型</th>
                                <th>输入token</th>
                                <th>输出token</th>
                                <th>成本(¥)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for call in recent_calls %}
                            <tr>
                                <td>{{ call.timestamp[:19] }}</td>
                                <td><span class="badge bg-secondary">{{ call.provider }}</span></td>
                                <td><small>{{ call.model }}</small></td>
                                <td>{{ call.input_tokens }}</td>
                                <td>{{ call.output_tokens }}</td>
                                <td class="fw-bold">{{ "%.4f"|format(call.cost_cny) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <footer class="mt-5 py-3 bg-light text-center">
        <div class="container">
            <p class="mb-0">
                AICostMonitor v1.0.0 | 
                <a href="https://github.com/CYzhr/AICostMonitor" class="text-decoration-none">
                    <i class="bi bi-github"></i> GitHub
                </a>
            </p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // 提交API调用记录
        document.getElementById('recordForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData();
            formData.append('provider', document.getElementById('provider').value);
            formData.append('model', document.getElementById('model').value);
            formData.append('input_tokens', document.getElementById('input_tokens').value);
            formData.append('output_tokens', document.getElementById('output_tokens').value);
            
            const resultDiv = document.getElementById('recordResult');
            resultDiv.innerHTML = '<div class="alert alert-info">提交中...</div>';
            
            try {
                const response = await fetch('/api/record', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    resultDiv.innerHTML = `
                        <div class="alert alert-success">
                            <i class="bi bi-check-circle"></i> 记录成功！
                            成本：¥${data.cost_cny.toFixed(4)}
                        </div>
                    `;
                    // 清空表单
                    document.getElementById('recordForm').reset();
                    // 刷新页面
                    setTimeout(() => location.reload(), 1500);
                } else {
                    resultDiv.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="bi bi-exclamation-triangle"></i> 错误：${data.error}
                        </div>
                    `;
                }
            } catch (error) {
                resultDiv.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle"></i> 网络错误：${error.message}
                    </div>
                `;
            }
        });
    </script>
</body>
</html>
    """
    
    (templates_dir / "index.html").write_text(index_html, encoding="utf-8")
    
    # 创建简单的dashboard.html
    dashboard_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>仪表板 - AICostMonitor</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="bi bi-graph-up"></i> AICostMonitor
            </a>
            <a class="nav-link text-light" href="/">返回首页</a>
        </div>
    </nav>
    
    <div class="container mt-4">
        <div class="card">
            <div class="card-header">
                <h4>仪表板 (开发中)</h4>
            </div>
            <div class="card-body">
                <p>高级仪表板功能正在开发中，将包含：</p>
                <ul>
                    <li>实时成本图表</li>
                    <li>预算预警系统</li>
                    <li>多维度分析</li>
                    <li>自动报告生成</li>
                </ul>
                <a href="/" class="btn btn-primary">返回首页</a>
            </div>
        </div>
    </div>
</body>
</html>
    """
    
    (templates_dir / "dashboard.html").write_text(dashboard_html, encoding="utf-8")
    
    # 创建简单的config.html
    config_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>配置 - AICostMonitor</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="bi bi-graph-up"></i> AICostMonitor
            </a>
            <a class="nav-link text-light" href="/">返回首页</a>
        </div>
    </nav>
    
    <div class="container mt-4">
        <div class="card">
            <div class="card-header">
                <h4>配置管理</h4>
            </div>
            <div class="card-body">
                <p>配置管理功能正在开发中，将支持：</p>
                <ul>
                    <li>在线编辑配置文件</li>
                    <li>提供商API密钥管理</li>
                    <li>定价策略配置</li>
                    <li>通知设置</li>
                </ul>
                <div class="alert alert-info">
                    <strong>当前配置位置：</strong> config.yaml
                    <br>
                    请手动编辑配置文件后重启应用。
                </div>
                <a href="/" class="btn btn-primary">返回首页</a>
            </div>
        </div>
    </div>
</body>
</html>
    """
    
    (templates_dir / "config.html").write_text(config_html, encoding="utf-8")


def main():
    """主函数"""
    print("=" * 60)
    print("AICostMonitor - AI API成本监控工具")
    print("=" * 60)
    
    # 创建必要的目录
    os.makedirs("static", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # 创建模板文件
    create_templates()
    
    # 检查配置文件
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        print(f"配置文件 {config_path} 不存在，使用默认配置")
        # 创建默认配置文件
        with open("config.example.yaml", "r", encoding="utf-8") as f:
            example_config = f.read()
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(example_config)
        print(f"已创建默认配置文件：{config_path}")
    
    # 启动应用
    app = AICostMonitor(config_path)
    app.run()


if __name__ == "__main__":
    main()