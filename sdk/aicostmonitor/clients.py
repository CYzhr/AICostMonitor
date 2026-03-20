"""
AICostMonitor SDK - Wrapped Clients
Drop-in replacements for OpenAI and Anthropic clients
"""

import logging
from typing import Any, Dict, Optional, List

logger = logging.getLogger("aicostmonitor")


class OpenAI:
    """
    Drop-in replacement for OpenAI client with automatic cost tracking.
    
    Usage:
        import aicostmonitor
        
        # Instead of: from openai import OpenAI
        client = aicostmonitor.OpenAI(api_key="sk-...")
        
        # Everything works exactly the same!
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        # Cost is automatically tracked!
    """
    
    def __init__(self, api_key: str = None, base_url: str = None, **kwargs):
        """
        Initialize OpenAI client with cost tracking.
        
        Args:
            api_key: OpenAI API key
            base_url: Optional base URL
            **kwargs: Additional arguments passed to OpenAI client
        """
        from openai import OpenAI as _OpenAI
        from .core import track
        
        self._client = _OpenAI(api_key=api_key, base_url=base_url, **kwargs)
        self._track = track
        
        # Wrap chat.completions
        self.chat = _TrackedChat(self._client.chat, "openai", track)
        
        # Wrap embeddings
        if hasattr(self._client, 'embeddings'):
            self.embeddings = _TrackedEmbeddings(self._client.embeddings, "openai", track)
        
        # Pass through other attributes
        self.models = self._client.models
        self.files = self._client.files
        self.fine_tuning = getattr(self._client, 'fine_tuning', None)
        self.images = getattr(self._client, 'images', None)
        self.audio = getattr(self._client, 'audio', None)
    
    def __getattr__(self, name):
        return getattr(self._client, name)


class Anthropic:
    """
    Drop-in replacement for Anthropic client with automatic cost tracking.
    
    Usage:
        import aicostmonitor
        
        # Instead of: from anthropic import Anthropic
        client = aicostmonitor.Anthropic(api_key="sk-ant-...")
        
        # Everything works exactly the same!
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": "Hello!"}]
        )
        # Cost is automatically tracked!
    """
    
    def __init__(self, api_key: str = None, base_url: str = None, **kwargs):
        """
        Initialize Anthropic client with cost tracking.
        
        Args:
            api_key: Anthropic API key
            base_url: Optional base URL
            **kwargs: Additional arguments passed to Anthropic client
        """
        from anthropic import Anthropic as _Anthropic
        from .core import track
        
        self._client = _Anthropic(api_key=api_key, base_url=base_url, **kwargs)
        self._track = track
        
        # Wrap messages
        self.messages = _TrackedMessages(self._client.messages, "anthropic", track)
    
    def __getattr__(self, name):
        return getattr(self._client, name)


class _TrackedChat:
    """Tracked chat completions"""
    
    def __init__(self, chat, provider: str, track_func):
        self._chat = chat
        self._provider = provider
        self._track = track_func
        self.completions = _TrackedCompletions(chat.completions, provider, track_func)
    
    def __getattr__(self, name):
        return getattr(self._chat, name)


class _TrackedCompletions:
    """Tracked completions"""
    
    def __init__(self, completions, provider: str, track_func):
        self._completions = completions
        self._provider = provider
        self._track = track_func
    
    def create(self, *args, **kwargs):
        """Create completion with tracking"""
        response = self._completions.create(*args, **kwargs)
        
        # Handle streaming
        if kwargs.get('stream', False):
            return _TrackedStream(response, kwargs, self._provider, self._track)
        
        # Track usage for non-streaming
        self._track_response(response, kwargs)
        
        return response
    
    def _track_response(self, response, kwargs):
        """Track response usage"""
        model = kwargs.get('model', 'unknown')
        
        if hasattr(response, 'usage'):
            input_tokens = getattr(response.usage, 'prompt_tokens', 0)
            output_tokens = getattr(response.usage, 'completion_tokens', 0)
            
            self._track(
                provider=self._provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
    
    def __getattr__(self, name):
        return getattr(self._completions, name)


class _TrackedStream:
    """Wrapper for streaming responses"""
    
    def __init__(self, stream, kwargs, provider, track_func):
        self._stream = stream
        self._kwargs = kwargs
        self._provider = provider
        self._track = track_func
        self._input_tokens = 0
        self._output_tokens = 0
        self._chunks = []
    
    def __iter__(self):
        for chunk in self._stream:
            self._chunks.append(chunk)
            
            # Try to extract usage from final chunk
            if hasattr(chunk, 'usage') and chunk.usage:
                self._input_tokens = getattr(chunk.usage, 'prompt_tokens', 0)
                self._output_tokens = getattr(chunk.usage, 'completion_tokens', 0)
            
            yield chunk
        
        # Track after stream completes
        if self._input_tokens > 0 or self._output_tokens > 0:
            self._track(
                provider=self._provider,
                model=self._kwargs.get('model', 'unknown'),
                input_tokens=self._input_tokens,
                output_tokens=self._output_tokens,
                metadata={"stream": True}
            )
    
    def __next__(self):
        return next(self._stream)
    
    def __getattr__(self, name):
        return getattr(self._stream, name)


class _TrackedMessages:
    """Tracked Anthropic messages"""
    
    def __init__(self, messages, provider: str, track_func):
        self._messages = messages
        self._provider = provider
        self._track = track_func
    
    def create(self, *args, **kwargs):
        """Create message with tracking"""
        response = self._messages.create(*args, **kwargs)
        
        # Handle streaming
        if kwargs.get('stream', False):
            return _TrackedAnthropicStream(response, kwargs, self._provider, self._track)
        
        # Track usage
        model = kwargs.get('model', 'unknown')
        
        if hasattr(response, 'usage'):
            input_tokens = getattr(response.usage, 'input_tokens', 0)
            output_tokens = getattr(response.usage, 'output_tokens', 0)
            
            self._track(
                provider=self._provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
        
        return response
    
    def __getattr__(self, name):
        return getattr(self._messages, name)


class _TrackedAnthropicStream:
    """Wrapper for Anthropic streaming responses"""
    
    def __init__(self, stream, kwargs, provider, track_func):
        self._stream = stream
        self._kwargs = kwargs
        self._provider = provider
        self._track = track_func
        self._input_tokens = 0
        self._output_tokens = 0
    
    def __iter__(self):
        for event in self._stream:
            # Extract usage from message_delta or message_start events
            if hasattr(event, 'type'):
                if event.type == 'message_start' and hasattr(event, 'message'):
                    if hasattr(event.message, 'usage'):
                        self._input_tokens = getattr(event.message.usage, 'input_tokens', 0)
                elif event.type == 'message_delta' and hasattr(event, 'usage'):
                    self._output_tokens = getattr(event.usage, 'output_tokens', 0)
            
            yield event
        
        # Track after stream completes
        if self._input_tokens > 0 or self._output_tokens > 0:
            self._track(
                provider=self._provider,
                model=self._kwargs.get('model', 'unknown'),
                input_tokens=self._input_tokens,
                output_tokens=self._output_tokens,
                metadata={"stream": True}
            )
    
    def __next__(self):
        return next(self._stream)
    
    def __getattr__(self, name):
        return getattr(self._stream, name)


class _TrackedEmbeddings:
    """Tracked embeddings"""
    
    def __init__(self, embeddings, provider: str, track_func):
        self._embeddings = embeddings
        self._provider = provider
        self._track = track_func
    
    def create(self, *args, **kwargs):
        """Create embedding with tracking"""
        response = self._embeddings.create(*args, **kwargs)
        
        model = kwargs.get('model', 'unknown')
        
        if hasattr(response, 'usage'):
            input_tokens = getattr(response.usage, 'prompt_tokens', 0)
            
            self._track(
                provider=self._provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=0,
                metadata={"type": "embedding"}
            )
        
        return response
    
    def __getattr__(self, name):
        return getattr(self._embeddings, name)
