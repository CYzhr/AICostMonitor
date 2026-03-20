"""
AICostMonitor SDK - Zero-intrusion AI API Cost Tracking

Usage:
    import aicostmonitor
    aicostmonitor.init(api_key="your-api-key", server="https://your-server.com")
    
    # That's it! All OpenAI/Anthropic calls are automatically tracked.
"""

__version__ = "1.0.0"

from .core import init, track, get_stats, set_budget, set_webhook
from .proxy import enable_tracking, disable_tracking
from .clients import OpenAI, Anthropic

__all__ = [
    "init",
    "track", 
    "get_stats",
    "set_budget",
    "set_webhook",
    "enable_tracking",
    "disable_tracking",
    "OpenAI",
    "Anthropic"
]
