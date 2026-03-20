# AICostMonitor SDK

**Zero-intrusion AI API cost tracking - One line of code integration**

## Quick Start

```bash
pip install aicostmonitor
```

```python
import aicostmonitor

# Initialize with your API key
aicostmonitor.init(api_key="your-api-key")

# That's it! All OpenAI and Anthropic calls are automatically tracked.
```

## Usage Patterns

### Pattern 1: Automatic Tracking (Recommended)

Just add one line after importing:

```python
import aicostmonitor
aicostmonitor.init(api_key="your-api-key")

# Your existing code works unchanged!
from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
# Cost automatically tracked!
```

### Pattern 2: Drop-in Replacement Client

Replace your imports:

```python
# Before: from openai import OpenAI
# After:
import aicostmonitor

client = aicostmonitor.OpenAI(api_key="sk-...")

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
# Same functionality, automatic tracking!
```

### Pattern 3: Manual Tracking

For custom implementations:

```python
import aicostmonitor
aicostmonitor.init(api_key="your-api-key", auto_track=False)

# Manually track calls
aicostmonitor.track(
    provider="openai",
    model="gpt-4o",
    input_tokens=1000,
    output_tokens=500
)
```

## Features

- ✅ **Zero code changes** - Works with existing OpenAI/Anthropic code
- ✅ **Automatic tracking** - All API calls tracked automatically
- ✅ **Budget alerts** - Set limits and get notified
- ✅ **Webhook notifications** - Real-time cost alerts
- ✅ **Real-time dashboard** - View costs at aicostmonitor.com
- ✅ **Project tagging** - Group costs by project/environment

## Budget Alerts

```python
import aicostmonitor

aicostmonitor.init(api_key="your-api-key")

# Set a monthly budget
aicostmonitor.set_budget(
    limit=100.0,  # $100 USD
    currency="USD",
    period="monthly",
    webhook="https://your-webhook.com/alerts",
    alert_at=0.8  # Alert at 80% usage
)
```

## Statistics

```python
# Get real-time statistics
stats = aicostmonitor.get_stats()
print(f"Total cost: ${stats['total_cost_usd']:.2f}")
print(f"Total calls: {stats['total_calls']}")
```

## Environment Variables

```bash
export AICOSTMONITOR_API_KEY=your-api-key
export AICOSTMONITOR_SERVER=https://aicostmonitor.com
```

## Supported Providers

- OpenAI (GPT-4, GPT-3.5, etc.)
- Anthropic (Claude 3.5, Claude 3, etc.)
- Google (Gemini Pro, Gemini Flash)
- DeepSeek (V3, R1)
- Baidu (ERNIE)
- Alibaba (Qwen)
- And more...

## License

MIT License
