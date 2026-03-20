#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能测试工具 - 压测API响应时间
支持并发测试、统计分析、报告生成
"""

import os
import time
import json
import threading
import statistics
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class RequestResult:
    """请求结果"""
    success: bool
    status_code: int
    latency_ms: float
    response_size: int
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # 延迟统计（毫秒）
    avg_latency_ms: float = 0
    min_latency_ms: float = 0
    max_latency_ms: float = 0
    median_latency_ms: float = 0
    p95_latency_ms: float = 0
    p99_latency_ms: float = 0
    
    # 吞吐量
    requests_per_second: float = 0
    
    # 可用性
    success_rate: float = 0
    
    # 响应大小
    avg_response_size: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "latency": {
                "avg_ms": round(self.avg_latency_ms, 2),
                "min_ms": round(self.min_latency_ms, 2),
                "max_ms": round(self.max_latency_ms, 2),
                "median_ms": round(self.median_latency_ms, 2),
                "p95_ms": round(self.p95_latency_ms, 2),
                "p99_ms": round(self.p99_latency_ms, 2)
            },
            "throughput": {
                "requests_per_second": round(self.requests_per_second, 2)
            },
            "availability": {
                "success_rate": f"{self.success_rate:.2f}%"
            },
            "response_size": {
                "avg_bytes": self.avg_response_size
            }
        }


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self, target_url: str, api_key: str = None):
        """
        初始化性能测试器
        
        Args:
            target_url: 目标API URL
            api_key: API密钥（可选）
        """
        self.target_url = target_url
        self.api_key = api_key
        self.results: List[RequestResult] = []
        self._lock = threading.Lock()
    
    def _make_request(self, endpoint: str, method: str = "GET", 
                      data: Dict = None, headers: Dict = None) -> RequestResult:
        """执行单个请求"""
        url = f"{self.target_url}{endpoint}"
        
        req_headers = {"Content-Type": "application/json"}
        if self.api_key:
            req_headers["Authorization"] = f"Bearer {self.api_key}"
        if headers:
            req_headers.update(headers)
        
        start_time = time.time()
        
        try:
            if method == "GET":
                response = requests.get(url, headers=req_headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=req_headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            latency_ms = (time.time() - start_time) * 1000
            
            return RequestResult(
                success=response.status_code < 400,
                status_code=response.status_code,
                latency_ms=latency_ms,
                response_size=len(response.content)
            )
        
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return RequestResult(
                success=False,
                status_code=0,
                latency_ms=latency_ms,
                response_size=0,
                error=str(e)
            )
    
    def run_load_test(self, endpoint: str, num_requests: int = 100,
                      concurrent_users: int = 10, method: str = "GET",
                      data: Dict = None) -> PerformanceMetrics:
        """
        执行负载测试
        
        Args:
            endpoint: API端点
            num_requests: 总请求数
            concurrent_users: 并发用户数
            method: HTTP方法
            data: 请求数据
        """
        self.results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = []
            for _ in range(num_requests):
                future = executor.submit(
                    self._make_request, endpoint, method, data
                )
                futures.append(future)
            
            for future in as_completed(futures):
                result = future.result()
                with self._lock:
                    self.results.append(result)
        
        return self._calculate_metrics(start_time)
    
    def run_spike_test(self, endpoint: str, peak_users: int = 50,
                       duration_seconds: int = 10, method: str = "GET",
                       data: Dict = None) -> PerformanceMetrics:
        """
        执行峰值测试
        
        Args:
            endpoint: API端点
            peak_users: 峰值用户数
            duration_seconds: 持续时间（秒）
            method: HTTP方法
            data: 请求数据
        """
        self.results = []
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        with ThreadPoolExecutor(max_workers=peak_users) as executor:
            futures = []
            
            while time.time() < end_time:
                future = executor.submit(
                    self._make_request, endpoint, method, data
                )
                futures.append(future)
                time.sleep(0.01)  # 控制请求速率
            
            for future in as_completed(futures):
                result = future.result()
                with self._lock:
                    self.results.append(result)
        
        return self._calculate_metrics(start_time)
    
    def run_endurance_test(self, endpoint: str, requests_per_second: float = 10,
                           duration_seconds: int = 60, method: str = "GET",
                           data: Dict = None) -> PerformanceMetrics:
        """
        执行耐久测试
        
        Args:
            endpoint: API端点
            requests_per_second: 每秒请求数
            duration_seconds: 持续时间（秒）
            method: HTTP方法
            data: 请求数据
        """
        self.results = []
        start_time = time.time()
        end_time = start_time + duration_seconds
        interval = 1.0 / requests_per_second
        
        while time.time() < end_time:
            result = self._make_request(endpoint, method, data)
            with self._lock:
                self.results.append(result)
            time.sleep(interval)
        
        return self._calculate_metrics(start_time)
    
    def _calculate_metrics(self, start_time: float) -> PerformanceMetrics:
        """计算性能指标"""
        if not self.results:
            return PerformanceMetrics()
        
        metrics = PerformanceMetrics()
        metrics.total_requests = len(self.results)
        metrics.successful_requests = sum(1 for r in self.results if r.success)
        metrics.failed_requests = metrics.total_requests - metrics.successful_requests
        
        # 延迟统计
        latencies = [r.latency_ms for r in self.results if r.success]
        if latencies:
            metrics.avg_latency_ms = statistics.mean(latencies)
            metrics.min_latency_ms = min(latencies)
            metrics.max_latency_ms = max(latencies)
            metrics.median_latency_ms = statistics.median(latencies)
            
            # 百分位数
            sorted_latencies = sorted(latencies)
            metrics.p95_latency_ms = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            metrics.p99_latency_ms = sorted_latencies[int(len(sorted_latencies) * 0.99)]
        
        # 吞吐量
        elapsed_time = time.time() - start_time
        metrics.requests_per_second = metrics.total_requests / elapsed_time if elapsed_time > 0 else 0
        
        # 可用性
        metrics.success_rate = (
            metrics.successful_requests / metrics.total_requests * 100
            if metrics.total_requests > 0 else 0
        )
        
        # 响应大小
        sizes = [r.response_size for r in self.results if r.success]
        metrics.avg_response_size = int(statistics.mean(sizes)) if sizes else 0
        
        return metrics
    
    def generate_report(self, metrics: PerformanceMetrics, 
                        test_name: str = "Performance Test") -> str:
        """生成性能报告"""
        report = []
        report.append("=" * 60)
        report.append(f"AICostMonitor Performance Test Report")
        report.append("=" * 60)
        report.append(f"Test Name: {test_name}")
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append(f"Target URL: {self.target_url}")
        report.append("")
        report.append("Summary:")
        report.append(f"  Total Requests: {metrics.total_requests}")
        report.append(f"  Successful: {metrics.successful_requests}")
        report.append(f"  Failed: {metrics.failed_requests}")
        report.append(f"  Success Rate: {metrics.success_rate:.2f}%")
        report.append("")
        report.append("Latency (ms):")
        report.append(f"  Average: {metrics.avg_latency_ms:.2f}")
        report.append(f"  Min: {metrics.min_latency_ms:.2f}")
        report.append(f"  Max: {metrics.max_latency_ms:.2f}")
        report.append(f"  Median: {metrics.median_latency_ms:.2f}")
        report.append(f"  P95: {metrics.p95_latency_ms:.2f}")
        report.append(f"  P99: {metrics.p99_latency_ms:.2f}")
        report.append("")
        report.append("Throughput:")
        report.append(f"  Requests/sec: {metrics.requests_per_second:.2f}")
        report.append("")
        report.append("Response Size:")
        report.append(f"  Average (bytes): {metrics.avg_response_size}")
        report.append("=" * 60)
        
        return "\n".join(report)


def run_comprehensive_test(base_url: str = "http://106.13.110.26"):
    """运行综合性能测试"""
    tester = PerformanceTester(base_url)
    
    print("Starting comprehensive performance test...")
    print("=" * 60)
    
    # 1. 汇率API测试
    print("\n[1/5] Exchange Rate API Test...")
    exchange_result = tester._make_request("/api/exchange-rate")
    print(f"  Status: {'✓ OK' if exchange_result.success else '✗ FAIL'}")
    print(f"  Latency: {exchange_result.latency_ms:.2f}ms")
    
    # 2. 轻负载测试
    print("\n[2/5] Light Load Test (50 requests, 5 concurrent)...")
    light_metrics = tester.run_load_test(
        endpoint="/api/exchange-rate",
        num_requests=50,
        concurrent_users=5
    )
    print(f"  Success Rate: {light_metrics.success_rate:.2f}%")
    print(f"  Avg Latency: {light_metrics.avg_latency_ms:.2f}ms")
    print(f"  Requests/sec: {light_metrics.requests_per_second:.2f}")
    
    # 3. 中等负载测试
    print("\n[3/5] Medium Load Test (100 requests, 10 concurrent)...")
    medium_metrics = tester.run_load_test(
        endpoint="/api/exchange-rate",
        num_requests=100,
        concurrent_users=10
    )
    print(f"  Success Rate: {medium_metrics.success_rate:.2f}%")
    print(f"  Avg Latency: {medium_metrics.avg_latency_ms:.2f}ms")
    print(f"  Requests/sec: {medium_metrics.requests_per_second:.2f}")
    
    # 4. 高负载测试
    print("\n[4/5] Heavy Load Test (200 requests, 20 concurrent)...")
    heavy_metrics = tester.run_load_test(
        endpoint="/api/exchange-rate",
        num_requests=200,
        concurrent_users=20
    )
    print(f"  Success Rate: {heavy_metrics.success_rate:.2f}%")
    print(f"  Avg Latency: {heavy_metrics.avg_latency_ms:.2f}ms")
    print(f"  Requests/sec: {heavy_metrics.requests_per_second:.2f}")
    
    # 5. API响应测试
    print("\n[5/5] API Response Test (pricing endpoint)...")
    pricing_result = tester._make_request("/api/pricing/openai")
    print(f"  Status: {'✓ OK' if pricing_result.success else '✗ FAIL'}")
    print(f"  Latency: {pricing_result.latency_ms:.2f}ms")
    
    # 生成报告
    print("\n" + "=" * 60)
    print("Performance Test Summary")
    print("=" * 60)
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "target": base_url,
        "tests": {
            "light_load": light_metrics.to_dict(),
            "medium_load": medium_metrics.to_dict(),
            "heavy_load": heavy_metrics.to_dict()
        },
        "conclusion": _generate_conclusion(light_metrics, medium_metrics, heavy_metrics)
    }
    
    # 保存报告
    report_path = "/root/.openclaw/workspace/AICostMonitor/tests/performance_report.json"
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\nReport saved to: {report_path}")
    print("\nConclusion:")
    print(summary["conclusion"])
    
    return summary


def _generate_conclusion(light: PerformanceMetrics, 
                         medium: PerformanceMetrics,
                         heavy: PerformanceMetrics) -> str:
    """生成测试结论"""
    conclusions = []
    
    # 可用性评估
    if heavy.success_rate >= 99:
        conclusions.append("✓ High availability: 99%+ success rate under heavy load")
    elif heavy.success_rate >= 95:
        conclusions.append("⚠ Good availability: 95%+ success rate under heavy load")
    else:
        conclusions.append("✗ Low availability: <95% success rate under heavy load")
    
    # 性能评估
    if heavy.avg_latency_ms < 100:
        conclusions.append("✓ Excellent performance: <100ms average latency")
    elif heavy.avg_latency_ms < 500:
        conclusions.append("⚠ Good performance: <500ms average latency")
    else:
        conclusions.append("✗ Poor performance: >500ms average latency")
    
    # 扩展性评估
    latency_degradation = heavy.avg_latency_ms / light.avg_latency_ms if light.avg_latency_ms > 0 else 1
    if latency_degradation < 2:
        conclusions.append("✓ Good scalability: <2x latency degradation")
    elif latency_degradation < 5:
        conclusions.append("⚠ Moderate scalability: <5x latency degradation")
    else:
        conclusions.append("✗ Poor scalability: >5x latency degradation")
    
    # 吞吐量评估
    if heavy.requests_per_second > 100:
        conclusions.append("✓ High throughput: >100 requests/sec")
    elif heavy.requests_per_second > 50:
        conclusions.append("⚠ Moderate throughput: >50 requests/sec")
    else:
        conclusions.append("✗ Low throughput: <50 requests/sec")
    
    return "\n".join(conclusions)


if __name__ == "__main__":
    run_comprehensive_test()
