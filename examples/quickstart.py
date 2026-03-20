#!/usr/bin/env python3
"""
AICostMonitor SDK - Complete Integration Example

This example demonstrates all SDK features:
1. Zero-intrusion automatic tracking
2. Manual tracking
3. Budget alerts
4. Webhook notifications
5. Statistics retrieval
"""

import sys
import os

# Add SDK to path for local development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk'))

import aicostmonitor


def example_1_init():
    """Example 1: Initialize SDK"""
    print("\n" + "="*60)
    print("Example 1: SDK Initialization")
    print("="*60)
    
    # Initialize with your API key
    # Get your free API key at https://aicostmonitor.com/trial
    aicostmonitor.init(
        api_key="aicm_b86ea5bf359b4830bbc09a180917492f",  # Trial key
        server="http://localhost:8000",  # Or use https://aicostmonitor.com
        project_name="demo-project",
        tags={"environment": "development", "team": "ai"}
    )
    
    print("✓ SDK initialized successfully")


def example_2_manual_tracking():
    """Example 2: Manual cost tracking"""
    print("\n" + "="*60)
    print("Example 2: Manual Tracking")
    print("="*60)
    
    # Track individual API calls
    calls = [
        ("openai", "gpt-4o", 1000, 500),
        ("openai", "gpt-4o-mini", 5000, 2000),
        ("anthropic", "claude-3.5-sonnet", 2000, 1000),
        ("google", "gemini-1.5-pro", 3000, 1500),
        ("deepseek", "deepseek-v3", 10000, 5000),
    ]
    
    print("\nTracking API calls:")
    for provider, model, input_tokens, output_tokens in calls:
        result = aicostmonitor.track(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        print(f"  {provider}/{model}: ${result['cost_usd']:.6f} USD")
    
    print("\n✓ Manual tracking complete")


def example_3_stats():
    """Example 3: Get usage statistics"""
    print("\n" + "="*60)
    print("Example 3: Usage Statistics")
    print("="*60)
    
    stats = aicostmonitor.get_stats()
    
    print(f"\n📊 Total Usage:")
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Total tokens: {stats['total_input_tokens'] + stats['total_output_tokens']:,}")
    print(f"  Total cost: ${stats['total_cost_usd']:.4f} USD (¥{stats['total_cost_cny']:.2f} CNY)")
    
    print(f"\n📈 By Provider:")
    for provider, data in stats['by_provider'].items():
        print(f"  {provider}: ${data['cost_usd']:.4f} ({data['calls']} calls)")
    
    print("\n✓ Statistics retrieved")


def example_4_budget():
    """Example 4: Set budget alerts"""
    print("\n" + "="*60)
    print("Example 4: Budget Alerts")
    print("="*60)
    
    # Set a monthly budget
    aicostmonitor.set_budget(
        limit=10.0,  # $10 USD
        currency="USD",
        period="monthly",
        webhook="https://your-webhook.com/alerts",  # Optional
        alert_at=0.8  # Alert at 80% usage
    )
    
    print("  Monthly budget: $10 USD")
    print("  Alert threshold: 80%")
    print("  Webhook: https://your-webhook.com/alerts")
    
    print("\n✓ Budget alert configured")


def example_5_webhook():
    """Example 5: Configure webhook notifications"""
    print("\n" + "="*60)
    print("Example 5: Webhook Notifications")
    print("="*60)
    
    # Add webhook for notifications
    aicostmonitor.set_webhook(
        url="https://your-webhook.com/aicostmonitor",
        events=["budget_alert", "high_cost"]
    )
    
    print("  Webhook URL: https://your-webhook.com/aicostmonitor")
    print("  Events: budget_alert, high_cost")
    
    print("\n✓ Webhook configured")


def example_6_openai_client():
    """Example 6: Using wrapped OpenAI client"""
    print("\n" + "="*60)
    print("Example 6: Wrapped OpenAI Client")
    print("="*60)
    
    print("""
# Instead of:
# from openai import OpenAI
# client = OpenAI(api_key="sk-...")

# Use:
import aicostmonitor
client = aicostmonitor.OpenAI(api_key="sk-...")

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
# Cost automatically tracked!
""")
    print("\n✓ Wrapped client ready (requires openai package)")


def example_7_anthropic_client():
    """Example 7: Using wrapped Anthropic client"""
    print("\n" + "="*60)
    print("Example 7: Wrapped Anthropic Client")
    print("="*60)
    
    print("""
# Instead of:
# from anthropic import Anthropic
# client = Anthropic(api_key="sk-ant-...")

# Use:
import aicostmonitor
client = aicostmonitor.Anthropic(api_key="sk-ant-...")

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}]
)
# Cost automatically tracked!
""")
    print("\n✓ Wrapped client ready (requires anthropic package)")


def example_8_env_init():
    """Example 8: Initialize from environment variables"""
    print("\n" + "="*60)
    print("Example 8: Environment Variable Init")
    print("="*60)
    
    print("""
# Set environment variables:
export AICOSTMONITOR_API_KEY=aicm_xxx
export AICOSTMONITOR_SERVER=https://aicostmonitor.com

# SDK auto-initializes on import!
import aicostmonitor

# That's it! All OpenAI/Anthropic calls are tracked.
""")
    print("\n✓ Auto-init from environment")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("AICostMonitor SDK - Complete Examples")
    print("="*60)
    
    example_1_init()
    example_2_manual_tracking()
    example_3_stats()
    example_4_budget()
    example_5_webhook()
    example_6_openai_client()
    example_7_anthropic_client()
    example_8_env_init()
    
    print("\n" + "="*60)
    print("✓ All examples completed!")
    print("="*60)
    
    # Final stats
    stats = aicostmonitor.get_stats()
    print(f"\nFinal Statistics:")
    print(f"  Total tracked: {stats['total_calls']} API calls")
    print(f"  Total cost: ${stats['total_cost_usd']:.6f}")


if __name__ == "__main__":
    main()
