#!/usr/bin/env python3
"""
AICostMonitor CLI
"""

import argparse
import sys
import os


def main():
    parser = argparse.ArgumentParser(
        description="AICostMonitor - AI API Cost Tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize project")
    init_parser.add_argument("--api-key", help="API key", required=True)
    init_parser.add_argument("--server", help="Server URL", default="https://aicostmonitor.com")
    init_parser.add_argument("--project", help="Project name", default="default")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show usage statistics")
    stats_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test tracking")
    test_parser.add_argument("--provider", default="openai", help="Provider name")
    test_parser.add_argument("--model", default="gpt-4o", help="Model name")
    test_parser.add_argument("--input-tokens", type=int, default=1000, help="Input tokens")
    test_parser.add_argument("--output-tokens", type=int, default=500, help="Output tokens")
    
    # Webhook command
    webhook_parser = subparsers.add_parser("webhook", help="Configure webhook")
    webhook_parser.add_argument("--url", required=True, help="Webhook URL")
    webhook_parser.add_argument("--test", action="store_true", help="Test webhook")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "init":
        print(f"Initializing AICostMonitor...")
        print(f"Server: {args.server}")
        print(f"Project: {args.project}")
        print(f"\nAdd this to your code:")
        print(f'\nimport aicostmonitor')
        print(f'aicostmonitor.init(api_key="{args.api_key}", server="{args.server}", project_name="{args.project}")')
        
    elif args.command == "stats":
        from aicostmonitor import init, get_stats
        
        api_key = os.environ.get("AICOSTMONITOR_API_KEY")
        if not api_key:
            print("Error: Set AICOSTMONITOR_API_KEY environment variable")
            sys.exit(1)
        
        init(api_key=api_key, auto_track=False)
        stats = get_stats()
        
        if args.json:
            import json
            print(json.dumps(stats, indent=2))
        else:
            print("\n=== AICostMonitor Statistics ===")
            print(f"Total calls: {stats['total_calls']:,}")
            print(f"Total tokens: {stats['total_input_tokens'] + stats['total_output_tokens']:,}")
            print(f"Total cost: ${stats['total_cost_usd']:.4f} USD (¥{stats['total_cost_cny']:.2f} CNY)")
            
            if stats['by_provider']:
                print("\nBy Provider:")
                for provider, data in stats['by_provider'].items():
                    print(f"  {provider}: ${data['cost_usd']:.4f} ({data['calls']} calls)")
    
    elif args.command == "test":
        from aicostmonitor import init, track
        
        api_key = os.environ.get("AICOSTMONITOR_API_KEY", "test-key")
        init(api_key=api_key, auto_track=False)
        
        result = track(
            provider=args.provider,
            model=args.model,
            input_tokens=args.input_tokens,
            output_tokens=args.output_tokens
        )
        
        print(f"\nTest tracking result:")
        print(f"  Provider: {args.provider}")
        print(f"  Model: {args.model}")
        print(f"  Input tokens: {args.input_tokens:,}")
        print(f"  Output tokens: {args.output_tokens:,}")
        print(f"  Cost: ${result['cost_usd']:.6f} USD")
        print(f"\n✓ Tracking successful!")
    
    elif args.command == "webhook":
        if args.test:
            import requests
            
            print(f"Testing webhook: {args.url}")
            
            try:
                response = requests.post(
                    args.url,
                    json={
                        "event": "test",
                        "message": "Test from AICostMonitor CLI",
                        "timestamp": "2024-01-01T00:00:00Z"
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    print("✓ Webhook test successful!")
                else:
                    print(f"✗ Webhook returned status {response.status_code}")
            except Exception as e:
                print(f"✗ Webhook test failed: {e}")
        else:
            print(f"Webhook URL: {args.url}")
            print("\nAdd this to your code:")
            print(f'\naicostmonitor.set_webhook("{args.url}")')


if __name__ == "__main__":
    main()
