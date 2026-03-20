"""
AICostMonitor SDK Core Module
"""

import os
import json
import threading
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger("aicostmonitor")

# Global state
_config = None
_stats = None
_budgets = {}
_webhooks = []
_enabled = False


@dataclass
class Config:
    """SDK Configuration"""
    api_key: str
    server: str = "http://localhost:8000"
    debug: bool = False
    auto_track: bool = True
    batch_size: int = 100
    flush_interval: float = 30.0  # seconds
    timeout: float = 5.0
    project_name: str = "default"
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass 
class Stats:
    """Usage statistics"""
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    total_cost_cny: float = 0.0
    by_provider: Dict[str, Dict] = field(default_factory=dict)
    by_model: Dict[str, Dict] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    

class BatchBuffer:
    """Buffer for batching API call records"""
    
    def __init__(self, config: Config):
        self.config = config
        self.buffer: List[Dict] = []
        self.lock = threading.Lock()
        self._flush_thread = None
        self._stop_event = threading.Event()
        
    def add(self, record: Dict):
        """Add a record to buffer"""
        with self.lock:
            self.buffer.append(record)
            if len(self.buffer) >= self.config.batch_size:
                self._flush()
    
    def _flush(self):
        """Flush buffer to server"""
        if not self.buffer:
            return
            
        records = self.buffer.copy()
        self.buffer.clear()
        
        try:
            self._send_batch(records)
        except Exception as e:
            logger.error(f"Failed to flush batch: {e}")
            # Re-add records on failure
            with self.lock:
                self.buffer = records + self.buffer
    
    def _send_batch(self, records: List[Dict]):
        """Send batch to server"""
        if not _config:
            return
            
        try:
            response = requests.post(
                f"{_config.server}/api/batch-record",
                json={"records": records, "api_key": _config.api_key},
                timeout=_config.timeout
            )
            if response.status_code != 200:
                logger.warning(f"Server returned {response.status_code}")
        except Exception as e:
            logger.error(f"Error sending batch: {e}")
    
    def start_flush_timer(self):
        """Start periodic flush timer"""
        def flush_loop():
            while not self._stop_event.is_set():
                self._stop_event.wait(self.config.flush_interval)
                with self.lock:
                    if self.buffer:
                        self._flush()
        
        self._flush_thread = threading.Thread(target=flush_loop, daemon=True)
        self._flush_thread.start()
    
    def stop(self):
        """Stop flush timer and flush remaining"""
        self._stop_event.set()
        with self.lock:
            self._flush()


_buffer: Optional[BatchBuffer] = None


def init(
    api_key: str,
    server: str = "https://aicostmonitor.com",
    debug: bool = False,
    auto_track: bool = True,
    project_name: str = "default",
    tags: Optional[Dict[str, str]] = None
) -> bool:
    """
    Initialize AICostMonitor SDK.
    
    Args:
        api_key: Your AICostMonitor API key
        server: AICostMonitor server URL (default: https://aicostmonitor.com)
        debug: Enable debug logging
        auto_track: Automatically track OpenAI/Anthropic calls
        project_name: Project name for grouping
        tags: Additional tags for filtering
        
    Returns:
        True if initialization successful
        
    Example:
        import aicostmonitor
        aicostmonitor.init(
            api_key="ak_xxx",
            project_name="my-app",
            tags={"env": "production"}
        )
    """
    global _config, _stats, _buffer, _enabled
    
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    _config = Config(
        api_key=api_key,
        server=server.rstrip("/"),
        debug=debug,
        auto_track=auto_track,
        project_name=project_name,
        tags=tags or {}
    )
    
    _stats = Stats()
    _buffer = BatchBuffer(_config)
    _buffer.start_flush_timer()
    
    if auto_track:
        from .proxy import enable_tracking
        enable_tracking()
    
    _enabled = True
    logger.info(f"AICostMonitor initialized - Project: {project_name}")
    
    # Register shutdown handler
    import atexit
    atexit.register(shutdown)
    
    return True


def shutdown():
    """Shutdown SDK and flush remaining records"""
    global _enabled, _buffer
    
    if _buffer:
        _buffer.stop()
    
    _enabled = False
    logger.info("AICostMonitor shutdown complete")


def track(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float = None,
    metadata: Dict = None
) -> Dict[str, Any]:
    """
    Manually track an API call.
    
    Args:
        provider: Provider name (openai, anthropic, etc.)
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost_usd: Optional cost in USD (will be calculated if not provided)
        metadata: Additional metadata
        
    Returns:
        Tracking result with cost information
    """
    global _stats
    
    if not _config:
        logger.warning("SDK not initialized, call init() first")
        return {"error": "not_initialized"}
    
    # Calculate cost if not provided
    if cost_usd is None:
        cost_usd = _calculate_cost(provider, model, input_tokens, output_tokens)
    
    cost_cny = cost_usd * 7.24  # Approximate exchange rate
    
    # Update local stats
    _stats.total_calls += 1
    _stats.total_input_tokens += input_tokens
    _stats.total_output_tokens += output_tokens
    _stats.total_cost_usd += cost_usd
    _stats.total_cost_cny += cost_cny
    
    # Update provider stats
    if provider not in _stats.by_provider:
        _stats.by_provider[provider] = {"calls": 0, "cost_usd": 0.0, "tokens": 0}
    _stats.by_provider[provider]["calls"] += 1
    _stats.by_provider[provider]["cost_usd"] += cost_usd
    _stats.by_provider[provider]["tokens"] += input_tokens + output_tokens
    
    # Update model stats
    model_key = f"{provider}/{model}"
    if model_key not in _stats.by_model:
        _stats.by_model[model_key] = {"calls": 0, "cost_usd": 0.0, "tokens": 0}
    _stats.by_model[model_key]["calls"] += 1
    _stats.by_model[model_key]["cost_usd"] += cost_usd
    _stats.by_model[model_key]["tokens"] += input_tokens + output_tokens
    
    # Create record
    record = {
        "id": f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{provider}_{_stats.total_calls}",
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "cost_cny": cost_cny,
        "timestamp": datetime.now().isoformat(),
        "project": _config.project_name,
        "tags": _config.tags,
        "metadata": metadata or {}
    }
    
    # Add to batch buffer
    if _buffer:
        _buffer.add(record)
    
    # Check budgets
    _check_budgets(provider, cost_usd)
    
    logger.debug(f"Tracked: {provider}/{model} - ${cost_usd:.6f}")
    
    return {
        "tracked": True,
        "cost_usd": cost_usd,
        "cost_cny": cost_cny
    }


def get_stats() -> Dict[str, Any]:
    """Get current usage statistics"""
    if not _stats:
        return {"error": "not_initialized"}
    
    return {
        "total_calls": _stats.total_calls,
        "total_input_tokens": _stats.total_input_tokens,
        "total_output_tokens": _stats.total_output_tokens,
        "total_cost_usd": round(_stats.total_cost_usd, 6),
        "total_cost_cny": round(_stats.total_cost_cny, 4),
        "by_provider": _stats.by_provider,
        "by_model": _stats.by_model,
        "duration_seconds": (datetime.now() - _stats.start_time).total_seconds()
    }


def set_budget(
    limit: float,
    currency: str = "USD",
    period: str = "monthly",
    webhook: Optional[str] = None,
    alert_at: float = 0.8  # Alert at 80% of budget
) -> bool:
    """
    Set a budget limit.
    
    Args:
        limit: Budget limit
        currency: "USD" or "CNY"
        period: "daily", "weekly", "monthly"
        webhook: Webhook URL for alerts
        alert_at: Alert when usage reaches this percentage (0-1)
        
    Returns:
        True if budget set successfully
    """
    global _budgets
    
    budget_id = f"{period}_{currency}"
    _budgets[budget_id] = {
        "limit": limit,
        "currency": currency,
        "period": period,
        "webhook": webhook,
        "alert_at": alert_at,
        "alerted": False
    }
    
    logger.info(f"Budget set: {limit} {currency} ({period})")
    return True


def set_webhook(
    url: str,
    events: List[str] = None,
    headers: Dict[str, str] = None
) -> bool:
    """
    Set a webhook for notifications.
    
    Args:
        url: Webhook URL
        events: List of events to notify (default: all)
        headers: Custom headers
        
    Returns:
        True if webhook set successfully
    """
    global _webhooks
    
    _webhooks.append({
        "url": url,
        "events": events or ["budget_alert", "high_cost"],
        "headers": headers or {}
    })
    
    logger.info(f"Webhook set: {url}")
    return True


def _calculate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost based on provider pricing"""
    # Pricing per 1K tokens (USD)
    PRICING = {
        "openai": {
            "gpt-4o": (0.0025, 0.01),
            "gpt-4o-mini": (0.00015, 0.0006),
            "gpt-4-turbo": (0.01, 0.03),
            "gpt-4": (0.03, 0.06),
            "gpt-3.5-turbo": (0.0005, 0.0015),
        },
        "anthropic": {
            "claude-3.5-sonnet": (0.003, 0.015),
            "claude-3-opus": (0.015, 0.075),
            "claude-3-sonnet": (0.003, 0.015),
            "claude-3-haiku": (0.00025, 0.00125),
        },
        "google": {
            "gemini-1.5-pro": (0.00125, 0.005),
            "gemini-1.5-flash": (0.000075, 0.0003),
        },
        "deepseek": {
            "deepseek-v3": (0.001, 0.002),
            "deepseek-r1": (0.001, 0.002),
        },
    }
    
    provider_pricing = PRICING.get(provider, {})
    
    # Try exact match first, then partial match
    pricing = None
    for model_name, prices in provider_pricing.items():
        if model_name == model or model.startswith(model_name.split("-")[0]):
            pricing = prices
            break
    
    if not pricing:
        # Default pricing
        pricing = (0.001, 0.002)
    
    input_cost = (input_tokens / 1000) * pricing[0]
    output_cost = (output_tokens / 1000) * pricing[1]
    
    return round(input_cost + output_cost, 6)


def _check_budgets(provider: str, cost: float):
    """Check if budgets are exceeded"""
    for budget_id, budget in _budgets.items():
        current_cost = _stats.total_cost_usd if budget["currency"] == "USD" else _stats.total_cost_cny
        
        # Check if exceeded
        if current_cost >= budget["limit"]:
            if not budget.get("exceeded_alerted"):
                budget["exceeded_alerted"] = True
                _send_alert(budget, "exceeded", current_cost)
        
        # Check if approaching limit
        elif current_cost >= budget["limit"] * budget["alert_at"]:
            if not budget.get("alerted"):
                budget["alerted"] = True
                _send_alert(budget, "warning", current_cost)


def _send_alert(budget: Dict, alert_type: str, current_cost: float):
    """Send budget alert"""
    logger.warning(f"Budget {alert_type}: {current_cost:.2f} {budget['currency']}")
    
    # Send to webhooks
    for webhook in _webhooks:
        if "budget_alert" in webhook.get("events", []):
            try:
                requests.post(
                    webhook["url"],
                    json={
                        "event": "budget_alert",
                        "type": alert_type,
                        "budget": budget,
                        "current_cost": current_cost,
                        "timestamp": datetime.now().isoformat()
                    },
                    headers=webhook.get("headers", {}),
                    timeout=5
                )
            except Exception as e:
                logger.error(f"Failed to send webhook alert: {e}")
