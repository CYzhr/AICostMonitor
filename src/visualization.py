#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据可视化模块
成本趋势图表、提供商分布、使用量统计
继承之前历史中的"实现数据可视化"任务
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CostDataPoint:
    """成本数据点"""
    timestamp: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    user_id: Optional[str] = None


@dataclass
class UsageStats:
    """使用统计"""
    total_cost: float
    total_tokens: int
    api_calls: int
    start_date: str
    end_date: str


class CostVisualizer:
    """成本可视化生成器"""
    
    def __init__(self, data_storage_path: str = "/root/.openclaw/workspace/data"):
        """
        初始化可视化器
        
        Args:
            data_storage_path: 数据存储路径
        """
        self.data_path = data_storage_path
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        import os
        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path, exist_ok=True)
    
    def generate_cost_trend_chart(self, 
                                 data: List[CostDataPoint],
                                 chart_type: str = "line") -> Dict[str, Any]:
        """
        生成成本趋势图表数据
        
        Args:
            data: 成本数据点列表
            chart_type: 图表类型（line, bar, area）
            
        Returns:
            图表配置和数据
        """
        if not data:
            return self._empty_chart("成本趋势")
        
        # 按时间分组
        time_groups = {}
        for point in data:
            date = point.timestamp[:10]  # YYYY-MM-DD
            if date not in time_groups:
                time_groups[date] = []
            time_groups[date].append(point)
        
        # 计算每日成本
        dates = sorted(time_groups.keys())
        daily_costs = []
        provider_breakdown = {}
        
        for date in dates:
            day_data = time_groups[date]
            total_cost = sum(point.cost for point in day_data)
            daily_costs.append({
                "date": date,
                "cost": round(total_cost, 4)
            })
            
            # 提供商细分
            for point in day_data:
                if point.provider not in provider_breakdown:
                    provider_breakdown[point.provider] = 0
                provider_breakdown[point.provider] += point.cost
        
        # 生成图表配置
        chart_config = {
            "title": "AI API成本趋势",
            "type": chart_type,
            "data": {
                "labels": [item["date"] for item in daily_costs],
                "datasets": [
                    {
                        "label": "每日成本（元）",
                        "data": [item["cost"] for item in daily_costs],
                        "borderColor": "rgb(75, 192, 192)",
                        "backgroundColor": "rgba(75, 192, 192, 0.2)" if chart_type == "line" else "rgb(75, 192, 192)",
                        "fill": chart_type == "area"
                    }
                ]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"AI成本趋势（{dates[0]} 至 {dates[-1]}）"
                    },
                    "tooltip": {
                        "mode": "index",
                        "intersect": False
                    }
                },
                "scales": {
                    "x": {
                        "display": True,
                        "title": {
                            "display": True,
                            "text": "日期"
                        }
                    },
                    "y": {
                        "display": True,
                        "title": {
                            "display": True,
                            "text": "成本（元）"
                        },
                        "beginAtZero": True
                    }
                }
            }
        }
        
        return {
            "chart": chart_config,
            "summary": {
                "total_days": len(dates),
                "total_cost": round(sum(item["cost"] for item in daily_costs), 4),
                "avg_daily_cost": round(sum(item["cost"] for item in daily_costs) / len(dates), 4),
                "provider_distribution": {
                    provider: round(cost, 4) 
                    for provider, cost in provider_breakdown.items()
                }
            }
        }
    
    def generate_provider_distribution(self, 
                                      data: List[CostDataPoint]) -> Dict[str, Any]:
        """
        生成提供商分布图表
        
        Args:
            data: 成本数据点列表
            
        Returns:
            提供商分布图表
        """
        if not data:
            return self._empty_chart("提供商分布")
        
        # 按提供商分组
        provider_costs = {}
        for point in data:
            if point.provider not in provider_costs:
                provider_costs[point.provider] = 0
            provider_costs[point.provider] += point.cost
        
        # 计算百分比
        total_cost = sum(provider_costs.values())
        provider_percentages = {
            provider: round((cost / total_cost) * 100, 2)
            for provider, cost in provider_costs.items()
        }
        
        # 颜色映射
        colors = [
            "rgb(255, 99, 132)", "rgb(54, 162, 235)", "rgb(255, 205, 86)",
            "rgb(75, 192, 192)", "rgb(153, 102, 255)", "rgb(255, 159, 64)"
        ]
        
        chart_config = {
            "title": "提供商成本分布",
            "type": "pie",
            "data": {
                "labels": list(provider_costs.keys()),
                "datasets": [
                    {
                        "label": "成本分布（元）",
                        "data": [round(cost, 4) for cost in provider_costs.values()],
                        "backgroundColor": colors[:len(provider_costs)],
                        "hoverOffset": 4
                    }
                ]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"提供商成本分布（总计：¥{total_cost:.2f}）"
                    },
                    "tooltip": {
                        "callbacks": {
                            "label": "function(context) {"
                            "  let label = context.label || '';"
                            "  if (label) {"
                            "    label += ': ';"
                            "  }"
                            "  label += '¥' + context.parsed.toFixed(4);"
                            "  label += ' (' + context.dataset.data[context.dataIndex] + '%)';"
                            "  return label;"
                            "}"
                        }
                    }
                }
            }
        }
        
        return {
            "chart": chart_config,
            "summary": {
                "total_providers": len(provider_costs),
                "total_cost": round(total_cost, 4),
                "distribution": provider_percentages,
                "dominant_provider": max(provider_costs.items(), key=lambda x: x[1])[0] if provider_costs else None
            }
        }
    
    def generate_model_usage_chart(self, 
                                  data: List[CostDataPoint]) -> Dict[str, Any]:
        """
        生成模型使用量图表
        
        Args:
            data: 成本数据点列表
            
        Returns:
            模型使用量图表
        """
        if not data:
            return self._empty_chart("模型使用量")
        
        # 按模型分组
        model_stats = {}
        for point in data:
            key = f"{point.provider}:{point.model}"
            if key not in model_stats:
                model_stats[key] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0,
                    "api_calls": 0
                }
            model_stats[key]["input_tokens"] += point.input_tokens
            model_stats[key]["output_tokens"] += point.output_tokens
            model_stats[key]["cost"] += point.cost
            model_stats[key]["api_calls"] += 1
        
        # 准备图表数据
        models = list(model_stats.keys())
        input_tokens = [model_stats[m]["input_tokens"] for m in models]
        output_tokens = [model_stats[m]["output_tokens"] for m in models]
        costs = [model_stats[m]["cost"] for m in models]
        
        chart_config = {
            "title": "模型使用量分析",
            "type": "bar",
            "data": {
                "labels": models,
                "datasets": [
                    {
                        "label": "输入Token（千）",
                        "data": [tokens / 1000 for tokens in input_tokens],
                        "backgroundColor": "rgba(54, 162, 235, 0.5)",
                        "borderColor": "rgb(54, 162, 235)",
                        "borderWidth": 1
                    },
                    {
                        "label": "输出Token（千）",
                        "data": [tokens / 1000 for tokens in output_tokens],
                        "backgroundColor": "rgba(255, 99, 132, 0.5)",
                        "borderColor": "rgb(255, 99, 132)",
                        "borderWidth": 1
                    },
                    {
                        "label": "成本（元）",
                        "data": costs,
                        "backgroundColor": "rgba(75, 192, 192, 0.5)",
                        "borderColor": "rgb(75, 192, 192)",
                        "borderWidth": 1,
                        "yAxisID": "y1"
                    }
                ]
            },
            "options": {
                "responsive": True,
                "interaction": {
                    "mode": "index",
                    "intersect": False
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": "模型使用量对比"
                    }
                },
                "scales": {
                    "x": {
                        "stacked": False,
                        "title": {
                            "display": True,
                            "text": "模型"
                        }
                    },
                    "y": {
                        "type": "linear",
                        "display": True,
                        "position": "left",
                        "title": {
                            "display": True,
                            "text": "Token数量（千）"
                        }
                    },
                    "y1": {
                        "type": "linear",
                        "display": True,
                        "position": "right",
                        "title": {
                            "display": True,
                            "text": "成本（元）"
                        },
                        "grid": {
                            "drawOnChartArea": False
                        }
                    }
                }
            }
        }
        
        # 计算性价比排名
        cost_per_token = {}
        for model, stats in model_stats.items():
            total_tokens = stats["input_tokens"] + stats["output_tokens"]
            if total_tokens > 0:
                cost_per_token[model] = stats["cost"] / total_tokens
        
        sorted_by_value = sorted(cost_per_token.items(), key=lambda x: x[1])
        
        return {
            "chart": chart_config,
            "summary": {
                "total_models": len(models),
                "total_api_calls": sum(stats["api_calls"] for stats in model_stats.values()),
                "total_tokens": sum(stats["input_tokens"] + stats["output_tokens"] for stats in model_stats.values()),
                "total_cost": round(sum(costs), 4),
                "most_cost_effective": sorted_by_value[0][0] if sorted_by_value else None,
                "least_cost_effective": sorted_by_value[-1][0] if sorted_by_value else None
            }
        }
    
    def generate_dashboard_data(self, 
                               days: int = 7) -> Dict[str, Any]:
        """
        生成完整仪表板数据
        
        Args:
            days: 要分析的天数
            
        Returns:
            完整仪表板数据
        """
        # 模拟数据（实际应从数据库读取）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 生成模拟数据点
        mock_data = self._generate_mock_data(start_date, end_date)
        
        return {
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "charts": {
                "cost_trend": self.generate_cost_trend_chart(mock_data),
                "provider_distribution": self.generate_provider_distribution(mock_data),
                "model_usage": self.generate_model_usage_chart(mock_data)
            },
            "key_metrics": self._calculate_key_metrics(mock_data),
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_mock_data(self, 
                           start_date: datetime, 
                           end_date: datetime) -> List[CostDataPoint]:
        """生成模拟数据用于演示"""
        import random
        providers = ["OpenAI", "Baidu Qianfan", "DeepSeek"]
        models = {
            "OpenAI": ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"],
            "Baidu Qianfan": ["ERNIE-4.0", "ERNIE-3.5", "ERNIE-Lite"],
            "DeepSeek": ["deepseek-v3.2", "deepseek-chat"]
        }
        
        data = []
        current_date = start_date
        
        while current_date <= end_date:
            # 每天生成3-10个数据点
            num_points = random.randint(3, 10)
            for _ in range(num_points):
                provider = random.choice(providers)
                model = random.choice(models[provider])
                input_tokens = random.randint(100, 5000)
                output_tokens = random.randint(50, 2000)
                
                # 模拟成本计算
                base_cost = 0.01 if provider == "DeepSeek" else 0.02
                cost = (input_tokens * base_cost / 1000) + (output_tokens * base_cost * 2 / 1000)
                
                data.append(CostDataPoint(
                    timestamp=current_date.isoformat(),
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=round(cost, 4)
                ))
            
            current_date += timedelta(days=1)
        
        return data
    
    def _calculate_key_metrics(self, data: List[CostDataPoint]) -> Dict[str, Any]:
        """计算关键指标"""
        if not data:
            return {}
        
        total_cost = sum(point.cost for point in data)
        total_input_tokens = sum(point.input_tokens for point in data)
        total_output_tokens = sum(point.output_tokens for point in data)
        total_api_calls = len(data)
        
        # 按提供商统计
        provider_stats = {}
        for point in data:
            if point.provider not in provider_stats:
                provider_stats[point.provider] = {
                    "cost": 0,
                    "api_calls": 0,
                    "tokens": 0
                }
            provider_stats[point.provider]["cost"] += point.cost
            provider_stats[point.provider]["api_calls"] += 1
            provider_stats[point.provider]["tokens"] += point.input_tokens + point.output_tokens
        
        # 计算性价比
        avg_cost_per_token = total_cost / (total_input_tokens + total_output_tokens) if total_input_tokens + total_output_tokens > 0 else 0
        
        return {
            "total_cost": round(total_cost, 4),
            "total_tokens": total_input_tokens + total_output_tokens,
            "total_api_calls": total_api_calls,
            "avg_cost_per_token": round(avg_cost_per_token, 6),
            "cost_per_provider": {
                provider: {
                    "cost": round(stats["cost"], 4),
                    "percentage": round((stats["cost"] / total_cost) * 100, 2) if total_cost > 0 else 0,
                    "api_calls": stats["api_calls"],
                    "tokens": stats["tokens"]
                }
                for provider, stats in provider_stats.items()
            },
            "date_range": {
                "start": min(point.timestamp for point in data) if data else "",
                "end": max(point.timestamp for point in data) if data else ""
            }
        }
    
    def _empty_chart(self, title: str) -> Dict[str, Any]:
        """生成空图表"""
        return {
            "chart": {
                "title": title,
                "type": "line",
                "data": {
                    "labels": ["无数据"],
                    "datasets": [{
                        "label": "无数据",
                        "data": [0],
                        "borderColor": "rgb(200, 200, 200)",
                        "backgroundColor": "rgba(200, 200, 200, 0.2)"
                    }]
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": f"{title}（暂无数据）"
                        }
                    }
                }
            },
            "summary": {
                "note": "暂无数据，请开始使用AI API以生成统计"
            }
        }
    
    def export_chart_data(self, 
                         dashboard_data: Dict[str, Any],
                         format: str = "json") -> str:
        """
        导出图表数据
        
        Args:
            dashboard_data: 仪表板数据
            format: 导出格式（json, html, csv）
            
        Returns:
            导出的数据
        """
        if format == "json":
            return json.dumps(dashboard_data, indent=2, ensure_ascii=False)
        elif format == "html":
            return self._generate_html_report(dashboard_data)
        elif format == "csv":
            return self._generate_csv_report(dashboard_data)
        else:
            return json.dumps({"error": f"不支持格式: {format}"})
    
    def _generate_html_report(self, data: Dict[str, Any]) -> str:
        """生成HTML报告"""
        import json
        chart_data_json = json.dumps(data)
        
        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI成本监控报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .dashboard {{ max-width: 1200px; margin: 0 auto; }}
        .chart-container {{ margin-bottom: 40px; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric-card {{ padding: 15px; background: #f5f5f5; border-radius: 6px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
        .metric-label {{ font-size: 14px; color: #666; }}
        h1 {{ color: #333; }}
        h2 {{ color: #444; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
    </style>
</head>
<body>
    <div class="dashboard">
        <h1>📊 AI成本监控报告</h1>
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value">¥{data.get('key_metrics', {{}}).get('total_cost', 0):.2f}</div>
                <div class="metric-label">总成本</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{data.get('key_metrics', {{}}).get('total_tokens', 0):,}</div>
                <div class="metric-label">总Token数</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{data.get('key_metrics', {{}}).get('total_api_calls', 0):,}</div>
                <div class="metric-label">API调用次数</div>
            </div>
        </div>
        
        <h2>成本趋势</h2>
        <div class="chart-container">
            <canvas id="costTrendChart"></canvas>
        </div>
        
        <h2>提供商分布</h2>
        <div class="chart-container">
            <canvas id="providerDistributionChart"></canvas>
        </div>
        
        <h2>模型使用量</h2>
        <div class="chart-container">
            <canvas id="modelUsageChart"></canvas>
        </div>
    </div>
    
    <script>
        const dashboardData = {chart_data_json};
        
        // 渲染成本趋势图表
        const costTrendCtx = document.getElementById('costTrendChart').getContext('2d');
        new Chart(costTrendCtx, dashboardData.charts.cost_trend.chart);
        
        // 渲染提供商分布图表
        const providerDistCtx = document.getElementById('providerDistributionChart').getContext('2d');
        new Chart(providerDistCtx, dashboardData.charts.provider_distribution.chart);
        
        // 渲染模型使用量图表
        const modelUsageCtx = document.getElementById('modelUsageChart').getContext('2d');
        new Chart(modelUsageCtx, dashboardData.charts.model_usage.chart);
    </script>
</body>
</html>
"""
        return html_template
    
    def _generate_csv_report(self, data: Dict[str, Any]) -> str:
        """生成CSV报告"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入摘要信息
        writer.writerow(["AI成本监控报告"])
        writer.writerow([f"生成时间: {datetime.now().isoformat()}"])
        writer.writerow([])
        
        # 写入关键指标
        writer.writerow(["关键指标"])
        metrics = data.get('key_metrics', {})
        writer.writerow(["总成本（元）", f"{metrics.get('total_cost', 0):.4f}"])
        writer.writerow(["总Token数", metrics.get('total_tokens', 0)])
        writer.writerow(["API调用次数", metrics.get('total_api_calls', 0)])
        writer.writerow([])
        
        # 写入提供商分布
        writer.writerow(["提供商成本分布"])
        writer.writerow(["提供商", "成本（元）", "百分比", "API调用次数"])
        
        cost_per_provider = metrics.get('cost_per_provider', {})
        for provider, stats in cost_per_provider.items():
            writer.writerow([
                provider,
                f"{stats.get('cost', 0):.4f}",
                f"{stats.get('percentage', 0):.2f}%",
                stats.get('api_calls', 0)
            ])
        
        return output.getvalue()


# 使用示例
if __name__ == "__main__":
    # 初始化可视化器
    visualizer = CostVisualizer()
    
    # 生成仪表板数据
    dashboard = visualizer.generate_dashboard_data(days=7)
    
    print("仪表板数据生成完成！")
    print(f"总计成本: ¥{dashboard['key_metrics'].get('total_cost', 0):.2f}")
    print(f"提供商数量: {len(dashboard['key_metrics'].get('cost_per_provider', {}))}")
    
    # 导出JSON格式
    json_output = visualizer.export_chart_data(dashboard, "json")
    with open("/tmp/aicost_dashboard.json", "w") as f:
        f.write(json_output)
    
    print("数据已保存到 /tmp/aicost_dashboard.json")