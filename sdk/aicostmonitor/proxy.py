"""
AICostMonitor SDK Proxy Module
Automatically intercepts OpenAI and Anthropic API calls
"""

import sys
import functools
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("aicostmonitor")

# Original modules
_original_openai = None
_original_anthropic = None
_tracking_enabled = False


def enable_tracking():
    """Enable automatic tracking of API calls"""
    global _tracking_enabled, _original_openai, _original_anthropic
    
    if _tracking_enabled:
        return
    
    # Patch OpenAI
    try:
        import openai
        _original_openai = openai
        
        # Patch the client
        if hasattr(openai, 'OpenAI'):
            _patch_openai_client(openai.OpenAI)
        
        # Patch legacy ChatCompletion (for older openai versions)
        if hasattr(openai, 'ChatCompletion'):
            _patch_openai_legacy(openai)
        
        logger.info("OpenAI tracking enabled")
    except ImportError:
        pass
    
    # Patch Anthropic
    try:
        import anthropic
        _original_anthropic = anthropic
        
        if hasattr(anthropic, 'Anthropic'):
            _patch_anthropic_client(anthropic.Anthropic)
        
        logger.info("Anthropic tracking enabled")
    except ImportError:
        pass
    
    # Patch LangChain if available
    try:
        _patch_langchain()
        logger.info("LangChain tracking enabled")
    except ImportError:
        pass
    
    _tracking_enabled = True


def disable_tracking():
    """Disable automatic tracking"""
    global _tracking_enabled
    
    # Restore original modules if needed
    _tracking_enabled = False
    logger.info("Tracking disabled")


def _patch_openai_client(cls):
    """Patch OpenAI client class"""
    original_init = cls.__init__
    original_chat_create = None
    
    # Store reference to chat.completions.create
    if hasattr(cls, 'chat') and hasattr(cls.chat, 'completions'):
        original_chat_create = cls.chat.completions.create
        
        class TrackedCompletions:
            def __init__(self, client):
                self._client = client
                self._original_create = None
            
            def create(self, *args, **kwargs):
                return _tracked_openai_create(self._client, args, kwargs, original_chat_create)
        
        # Wrap the chat.completions
        original_chat_property = type(cls.chat).completions
        
    # Patch the __init__ to set up tracking
    @functools.wraps(original_init)
    def tracked_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._aicm_tracked = True
    
    cls.__init__ = tracked_init
    
    # Patch chat.completions.create method
    if hasattr(cls, 'chat'):
        _patch_chat_completions(cls.chat)


def _patch_chat_completions(chat_obj):
    """Patch chat.completions.create"""
    if hasattr(chat_obj, 'completions') and hasattr(chat_obj.completions, 'create'):
        original_create = chat_obj.completions.create
        
        @functools.wraps(original_create)
        def tracked_create(*args, **kwargs):
            response = original_create(*args, **kwargs)
            return _track_openai_response(response, kwargs)
        
        chat_obj.completions.create = tracked_create


def _tracked_openai_create(client, args, kwargs, original_func):
    """Track OpenAI API call"""
    from .core import track
    
    response = original_func(*args, **kwargs) if original_func else client.chat.completions.create(*args, **kwargs)
    
    # Extract usage info
    model = kwargs.get('model', 'unknown')
    
    if hasattr(response, 'usage'):
        input_tokens = getattr(response.usage, 'prompt_tokens', 0)
        output_tokens = getattr(response.usage, 'completion_tokens', 0)
        
        track(
            provider="openai",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata={"stream": kwargs.get('stream', False)}
        )
    
    return response


def _track_openai_response(response, kwargs):
    """Track OpenAI response"""
    from .core import track
    
    model = kwargs.get('model', 'unknown')
    
    if hasattr(response, 'usage'):
        input_tokens = getattr(response.usage, 'prompt_tokens', 0)
        output_tokens = getattr(response.usage, 'completion_tokens', 0)
        
        track(
            provider="openai",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
    
    return response


def _patch_openai_legacy(openai_module):
    """Patch legacy OpenAI API (for backward compatibility)"""
    if not hasattr(openai_module, 'ChatCompletion'):
        return
    
    original_create = openai_module.ChatCompletion.create
    
    @functools.wraps(original_create)
    def tracked_create(*args, **kwargs):
        from .core import track
        
        response = original_create(*args, **kwargs)
        
        # Extract usage from response
        model = kwargs.get('model', 'unknown')
        
        if hasattr(response, 'usage'):
            input_tokens = getattr(response.usage, 'prompt_tokens', 0)
            output_tokens = getattr(response.usage, 'completion_tokens', 0)
            
            track(
                provider="openai",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
        
        return response
    
    openai_module.ChatCompletion.create = tracked_create


def _patch_anthropic_client(cls):
    """Patch Anthropic client class"""
    original_init = cls.__init__
    
    @functools.wraps(original_init)
    def tracked_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        
        # Patch messages.create
        if hasattr(self, 'messages') and hasattr(self.messages, 'create'):
            original_create = self.messages.create
            
            @functools.wraps(original_create)
            def tracked_create(*args, **kwargs):
                from .core import track
                
                response = original_create(*args, **kwargs)
                
                model = kwargs.get('model', 'unknown')
                
                if hasattr(response, 'usage'):
                    input_tokens = getattr(response.usage, 'input_tokens', 0)
                    output_tokens = getattr(response.usage, 'output_tokens', 0)
                    
                    track(
                        provider="anthropic",
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens
                    )
                
                return response
            
            self.messages.create = tracked_create
    
    cls.__init__ = tracked_init


def _patch_langchain():
    """Patch LangChain callbacks"""
    try:
        from langchain_core.callbacks import BaseCallbackHandler
        
        # Create a tracking callback handler
        class AICostMonitorCallback(BaseCallbackHandler):
            """LangChain callback handler for cost tracking"""
            
            def __init__(self):
                super().__init__()
                self.name = "AICostMonitor"
            
            def on_llm_end(self, response, **kwargs):
                """Track LLM call completion"""
                from .core import track
                
                try:
                    # Extract token usage
                    if hasattr(response, 'llm_output') and response.llm_output:
                        token_usage = response.llm_output.get('token_usage', {})
                        input_tokens = token_usage.get('prompt_tokens', 0)
                        output_tokens = token_usage.get('completion_tokens', 0)
                        
                        # Try to get model name
                        model = kwargs.get('invocation_params', {}).get('model', 'unknown')
                        
                        # Determine provider from model name
                        provider = self._get_provider(model)
                        
                        if input_tokens > 0 or output_tokens > 0:
                            track(
                                provider=provider,
                                model=model,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens
                            )
                except Exception as e:
                    logger.error(f"Error tracking LangChain call: {e}")
            
            def _get_provider(self, model: str) -> str:
                """Determine provider from model name"""
                model_lower = model.lower()
                if 'gpt' in model_lower or 'o1' in model_lower:
                    return "openai"
                elif 'claude' in model_lower:
                    return "anthropic"
                elif 'gemini' in model_lower:
                    return "google"
                elif 'deepseek' in model_lower:
                    return "deepseek"
                else:
                    return "unknown"
        
        # Register the callback handler globally
        # Users can also add it manually to their chains
        import langchain
        if hasattr(langchain, 'callbacks'):
            langchain.callbacks.AICostMonitorCallback = AICostMonitorCallback
        
        logger.info("LangChain callback registered")
        
    except ImportError:
        pass


# Auto-enable tracking when module is imported if configured
def _auto_enable():
    """Auto-enable tracking if AICOSTMONITOR_API_KEY is set"""
    import os
    
    api_key = os.environ.get('AICOSTMONITOR_API_KEY')
    server = os.environ.get('AICOSTMONITOR_SERVER', 'https://aicostmonitor.com')
    
    if api_key:
        from .core import init
        init(
            api_key=api_key,
            server=server,
            auto_track=True
        )
        logger.info("Auto-initialized from environment variables")


# Try auto-enable on import
try:
    _auto_enable()
except Exception:
    pass
