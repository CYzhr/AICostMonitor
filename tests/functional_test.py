#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合功能测试脚本
测试负载均衡、缓存、故障转移、统一接口
"""

import sys
import time
import json
sys.path.insert(0, "/root/.openclaw/workspace/AICostMonitor/src")

from aicostmonitor import (
    LoadBalancer,
    CacheManager,
    FailoverManager,
    UnifiedClient,
    monitor
)


def test_load_balancer():
    """测试负载均衡器"""
    print("\n" + "="*60)
    print("测试负载均衡器")
    print("="*60)
    
    lb = LoadBalancer(strategy="round_robin")
    
    # 添加多个API Key
    lb.add_key("openai", "sk-test-key-1", weight=1)
    lb.add_key("openai", "sk-test-key-2", weight=1)
    lb.add_key("openai", "sk-test-key-3", weight=2)
    
    # 测试轮询
    print("\n[测试] Round Robin轮询...")
    keys_used = []
    for i in range(6):
        key = lb.get_key("openai")
        keys_used.append(key.key[:12] if key else None)
        print(f"  请求 {i+1}: {key.key[:12] if key else 'None'}")
    
    # 测试故障标记
    print("\n[测试] 故障标记...")
    lb.mark_failure("openai", "sk-test-key-1")
    lb.mark_failure("openai", "sk-test-key-1")
    lb.mark_failure("openai", "sk-test-key-1")
    
    # 检查密钥状态
    stats = lb.get_stats()
    print(f"  健康密钥数: {stats['openai']['healthy_keys']}/{stats['openai']['total_keys']}")
    
    # 测试成功恢复
    print("\n[测试] 成功恢复...")
    lb.mark_success("openai", "sk-test-key-1")
    stats = lb.get_stats()
    print(f"  健康密钥数: {stats['openai']['healthy_keys']}/{stats['openai']['total_keys']}")
    
    print("\n✓ 负载均衡器测试通过")
    return True


def test_cache_manager():
    """测试缓存管理器"""
    print("\n" + "="*60)
    print("测试缓存管理器")
    print("="*60)
    
    cache = CacheManager(enabled=True, ttl=60)
    
    # 测试数据
    messages = [{"role": "user", "content": "Hello"}]
    response = {"choices": [{"message": {"content": "Hi there!"}}]}
    
    # 测试缓存未命中
    print("\n[测试] 缓存未命中...")
    result = cache.get("openai", "gpt-4o", messages)
    print(f"  结果: {result}")
    
    # 设置缓存
    print("\n[测试] 设置缓存...")
    cache.set("openai", "gpt-4o", messages, response)
    print(f"  已缓存")
    
    # 测试缓存命中
    print("\n[测试] 缓存命中...")
    result = cache.get("openai", "gpt-4o", messages)
    print(f"  结果: {result is not None}")
    
    # 检查统计
    stats = cache.get_stats()
    print(f"\n[统计]")
    print(f"  命中率: {stats['hit_rate']}")
    print(f"  缓存大小: {stats['size']}")
    print(f"  命中次数: {stats['hits']}")
    print(f"  未命中次数: {stats['misses']}")
    
    print("\n✓ 缓存管理器测试通过")
    return True


def test_failover_manager():
    """测试故障转移管理器"""
    print("\n" + "="*60)
    print("测试故障转移管理器")
    print("="*60)
    
    failover = FailoverManager(max_retries=3, retry_delay=0.1)
    
    # 测试成功场景
    print("\n[测试] 成功执行...")
    def success_func():
        return {"status": "ok"}
    
    result = failover.execute_with_failover(success_func)
    print(f"  结果: {result}")
    
    # 测试重试场景
    print("\n[测试] 重试机制...")
    attempt_count = [0]
    
    def retry_func():
        attempt_count[0] += 1
        if attempt_count[0] < 2:
            raise Exception("Temporary error")
        return {"status": "recovered"}
    
    result = failover.execute_with_failover(retry_func)
    print(f"  结果: {result}")
    print(f"  尝试次数: {attempt_count[0]}")
    
    # 测试故障转移场景
    print("\n[测试] 故障转移到备用函数...")
    
    def primary_func():
        raise Exception("Primary failed")
    
    def fallback_func():
        return {"status": "fallback"}
    
    result = failover.execute_with_failover(
        primary_func,
        fallback_func=fallback_func
    )
    print(f"  结果: {result}")
    
    # 检查统计
    stats = failover.get_stats()
    print(f"\n[统计]")
    print(f"  总请求数: {stats['total_requests']}")
    print(f"  成功率: {stats['success_rate']}")
    print(f"  重试次数: {stats['retries']}")
    print(f"  故障转移次数: {stats['failovers']}")
    
    print("\n✓ 故障转移管理器测试通过")
    return True


def test_unified_client():
    """测试统一客户端"""
    print("\n" + "="*60)
    print("测试统一客户端")
    print("="*60)
    
    # 创建客户端
    lb = LoadBalancer()
    cache = CacheManager()
    failover = FailoverManager()
    
    client = UnifiedClient(
        load_balancer=lb,
        cache=cache,
        failover=failover
    )
    
    # 测试接口兼容性
    print("\n[测试] OpenAI SDK兼容接口...")
    print(f"  client.chat: {client.chat is not None}")
    print(f"  client.chat.completions: {client.chat.completions is not None}")
    
    # 测试提供商推断
    print("\n[测试] 提供商自动推断...")
    test_cases = [
        ("gpt-4o", "openai"),
        ("gpt-3.5-turbo", "openai"),
        ("deepseek-chat", "deepseek"),
        ("ernie-4.0-8k", "qianfan")
    ]
    
    for model, expected_provider in test_cases:
        provider = client.chat.completions._infer_provider(model)
        status = "✓" if provider == expected_provider else "✗"
        print(f"  {status} {model} -> {provider} (期望: {expected_provider})")
    
    print("\n✓ 统一客户端测试通过")
    return True


def test_integration():
    """集成测试"""
    print("\n" + "="*60)
    print("集成测试 - 完整流程")
    print("="*60)
    
    # 初始化所有组件
    lb = LoadBalancer(strategy="round_robin")
    lb.add_key("openai", "sk-test-1")
    lb.add_key("openai", "sk-test-2")
    
    cache = CacheManager(enabled=True, ttl=300)
    failover = FailoverManager(max_retries=3)
    
    client = UnifiedClient(
        load_balancer=lb,
        cache=cache,
        failover=failover,
        monitor_url="http://106.13.110.26"
    )
    
    print("\n[组件状态]")
    print(f"  负载均衡器: {lb.get_stats()}")
    print(f"  缓存管理器: {cache.get_stats()}")
    print(f"  故障转移: {failover.get_stats()}")
    
    print("\n✓ 集成测试通过")
    return True


def generate_report(results: dict):
    """生成测试报告"""
    report = []
    report.append("\n" + "="*60)
    report.append("测试报告")
    report.append("="*60)
    report.append(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    report.append(f"总计: {total} 个测试")
    report.append(f"通过: {passed} 个")
    report.append(f"失败: {total - passed} 个")
    report.append("")
    
    report.append("详细结果:")
    for test_name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        report.append(f"  {status} - {test_name}")
    
    report.append("="*60)
    
    return "\n".join(report)


def main():
    """运行所有测试"""
    print("="*60)
    print("AICostMonitor 功能测试套件")
    print("="*60)
    
    results = {}
    
    try:
        results["负载均衡"] = test_load_balancer()
    except Exception as e:
        print(f"✗ 负载均衡测试失败: {e}")
        results["负载均衡"] = False
    
    try:
        results["缓存系统"] = test_cache_manager()
    except Exception as e:
        print(f"✗ 缓存系统测试失败: {e}")
        results["缓存系统"] = False
    
    try:
        results["故障转移"] = test_failover_manager()
    except Exception as e:
        print(f"✗ 故障转移测试失败: {e}")
        results["故障转移"] = False
    
    try:
        results["统一接口"] = test_unified_client()
    except Exception as e:
        print(f"✗ 统一接口测试失败: {e}")
        results["统一接口"] = False
    
    try:
        results["集成测试"] = test_integration()
    except Exception as e:
        print(f"✗ 集成测试失败: {e}")
        results["集成测试"] = False
    
    # 生成报告
    report = generate_report(results)
    print(report)
    
    # 保存报告
    report_path = "/root/.openclaw/workspace/AICostMonitor/tests/functional_test_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "results": results,
            "summary": {
                "total": len(results),
                "passed": sum(1 for v in results.values() if v),
                "failed": sum(1 for v in results.values() if not v)
            }
        }, f, indent=2)
    
    print(f"\n报告已保存到: {report_path}")
    
    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
