#!/usr/bin/env python3
"""
AICostMonitor SDK Test Suite
"""

import sys
import os

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk'))

def test_sdk_import():
    """Test SDK imports correctly"""
    print("Testing SDK import...")
    import aicostmonitor
    
    assert hasattr(aicostmonitor, 'init')
    assert hasattr(aicostmonitor, 'track')
    assert hasattr(aicostmonitor, 'get_stats')
    assert hasattr(aicostmonitor, 'set_budget')
    assert hasattr(aicostmonitor, 'set_webhook')
    assert hasattr(aicostmonitor, 'OpenAI')
    assert hasattr(aicostmonitor, 'Anthropic')
    
    print("✓ SDK import successful")
    return True


def test_sdk_init():
    """Test SDK initialization"""
    print("\nTesting SDK initialization...")
    import aicostmonitor
    
    # Initialize without auto-track
    result = aicostmonitor.init(
        api_key="test_key_123",
        server="http://localhost:8000",
        auto_track=False,
        project_name="test_project"
    )
    
    assert result == True
    print("✓ SDK initialization successful")
    return True


def test_manual_tracking():
    """Test manual cost tracking"""
    print("\nTesting manual tracking...")
    import aicostmonitor
    
    # Track a call
    result = aicostmonitor.track(
        provider="openai",
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=500
    )
    
    assert result.get('tracked') == True
    assert 'cost_usd' in result
    assert 'cost_cny' in result
    print(f"  Cost: ${result['cost_usd']:.6f} USD")
    print("✓ Manual tracking successful")
    return True


def test_stats():
    """Test statistics retrieval"""
    print("\nTesting statistics...")
    import aicostmonitor
    
    stats = aicostmonitor.get_stats()
    
    assert 'total_calls' in stats
    assert 'total_cost_usd' in stats
    assert 'by_provider' in stats
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Total cost: ${stats['total_cost_usd']:.6f}")
    print("✓ Statistics retrieval successful")
    return True


def test_budget_setting():
    """Test budget setting"""
    print("\nTesting budget setting...")
    import aicostmonitor
    
    result = aicostmonitor.set_budget(
        limit=100.0,
        currency="USD",
        period="monthly",
        alert_at=0.8
    )
    
    assert result == True
    print("✓ Budget setting successful")
    return True


def test_webhook_setting():
    """Test webhook setting"""
    print("\nTesting webhook setting...")
    import aicostmonitor
    
    result = aicostmonitor.set_webhook(
        url="https://example.com/webhook",
        events=["budget_alert", "high_cost"]
    )
    
    assert result == True
    print("✓ Webhook setting successful")
    return True


def test_cost_calculation():
    """Test cost calculation accuracy"""
    print("\nTesting cost calculation...")
    import aicostmonitor
    from aicostmonitor.core import _calculate_cost
    
    # Test OpenAI GPT-4o
    cost = _calculate_cost("openai", "gpt-4o", 1000, 500)
    expected = (1000/1000 * 0.0025) + (500/1000 * 0.01)
    assert abs(cost - expected) < 0.000001, f"Expected {expected}, got {cost}"
    print(f"  GPT-4o (1000 in, 500 out): ${cost:.6f}")
    
    # Test Anthropic Claude 3.5 Sonnet
    cost = _calculate_cost("anthropic", "claude-3.5-sonnet", 1000, 500)
    expected = (1000/1000 * 0.003) + (500/1000 * 0.015)
    assert abs(cost - expected) < 0.000001, f"Expected {expected}, got {cost}"
    print(f"  Claude 3.5 Sonnet (1000 in, 500 out): ${cost:.6f}")
    
    # Test DeepSeek
    cost = _calculate_cost("deepseek", "deepseek-v3", 1000, 500)
    expected = (1000/1000 * 0.001) + (500/1000 * 0.002)
    assert abs(cost - expected) < 0.000001, f"Expected {expected}, got {cost}"
    print(f"  DeepSeek V3 (1000 in, 500 out): ${cost:.6f}")
    
    print("✓ Cost calculation accurate")
    return True


def test_multiple_providers():
    """Test tracking multiple providers"""
    print("\nTesting multiple providers...")
    import aicostmonitor
    
    providers = [
        ("openai", "gpt-4o", 1000, 500),
        ("anthropic", "claude-3.5-sonnet", 2000, 1000),
        ("google", "gemini-1.5-pro", 1500, 750),
        ("deepseek", "deepseek-v3", 3000, 1500),
    ]
    
    for provider, model, input_tokens, output_tokens in providers:
        result = aicostmonitor.track(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        print(f"  {provider}/{model}: ${result['cost_usd']:.6f}")
    
    stats = aicostmonitor.get_stats()
    print(f"\n  Total tracked: {stats['total_calls']} calls, ${stats['total_cost_usd']:.6f}")
    print("✓ Multiple provider tracking successful")
    return True


def test_wrapped_client():
    """Test wrapped OpenAI client (without actual API call)"""
    print("\nTesting wrapped client classes...")
    import aicostmonitor
    
    # Check that the classes exist
    assert hasattr(aicostmonitor, 'OpenAI')
    assert hasattr(aicostmonitor, 'Anthropic')
    
    print("  OpenAI client wrapper available")
    print("  Anthropic client wrapper available")
    print("✓ Wrapped client classes available")
    return True


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("AICostMonitor SDK Test Suite")
    print("=" * 60)
    
    tests = [
        test_sdk_import,
        test_sdk_init,
        test_manual_tracking,
        test_stats,
        test_budget_setting,
        test_webhook_setting,
        test_cost_calculation,
        test_multiple_providers,
        test_wrapped_client,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
