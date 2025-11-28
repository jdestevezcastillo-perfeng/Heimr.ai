"""Global chaos state management with thread-safe access."""
import asyncio
import time
from datetime import datetime
from typing import Optional

from app.models import ChaosConfig
from app.chaos.scenarios import get_scenario


class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    def __init__(self, rate: float, capacity: int):
        """Initialize token bucket.
        
        Args:
            rate: Tokens added per second
            capacity: Maximum bucket size
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were available and consumed, False otherwise
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Add tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            # Try to consume
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def update_rate(self, rate: float, capacity: int):
        """Update rate limiting parameters.
        
        Args:
            rate: New tokens per second
            capacity: New bucket capacity
        """
        async with self._lock:
            self.rate = rate
            self.capacity = capacity
            self.tokens = min(capacity, self.tokens)


class ChaosState:
    """Thread-safe global chaos state manager."""
    
    def __init__(self):
        """Initialize chaos state with default configuration."""
        self._config = ChaosConfig()
        self._lock = asyncio.Lock()
        self._active_scenario: Optional[str] = "healthy"
        self._token_bucket: Optional[TokenBucket] = None
        self._request_timestamps: list[float] = []  # For RPS calculation
        self._request_window_seconds = 1.0
    
    async def get_config(self) -> ChaosConfig:
        """Get current chaos configuration.
        
        Returns:
            Current ChaosConfig
        """
        async with self._lock:
            return self._config.model_copy(deep=True)
    
    async def update_config(self, config: ChaosConfig):
        """Update chaos configuration.
        
        Args:
            config: New chaos configuration
        """
        async with self._lock:
            self._config = config.model_copy(deep=True)
            self._active_scenario = None  # Custom config
            
            # Update token bucket if rate limiting is enabled
            if config.errors.rate_limit.enabled:
                if self._token_bucket is None:
                    self._token_bucket = TokenBucket(
                        rate=config.errors.rate_limit.requests_per_second,
                        capacity=config.errors.rate_limit.bucket_size
                    )
                else:
                    await self._token_bucket.update_rate(
                        rate=config.errors.rate_limit.requests_per_second,
                        capacity=config.errors.rate_limit.bucket_size
                    )
            else:
                self._token_bucket = None
    
    async def activate_scenario(self, name: str):
        """Activate a predefined chaos scenario.
        
        Args:
            name: Scenario name
            
        Raises:
            ValueError: If scenario name is invalid
        """
        config = get_scenario(name)
        await self.update_config(config)
        async with self._lock:
            self._active_scenario = name
    
    async def reset(self):
        """Reset to healthy baseline."""
        await self.activate_scenario("healthy")
    
    async def get_active_scenario(self) -> Optional[str]:
        """Get name of currently active scenario.
        
        Returns:
            Scenario name or None if using custom config
        """
        async with self._lock:
            return self._active_scenario
    
    async def increment_concurrent(self) -> int:
        """Increment concurrent request counter.
        
        Returns:
            New concurrent request count
        """
        async with self._lock:
            self._config.resources.current_concurrent += 1
            return self._config.resources.current_concurrent
    
    async def decrement_concurrent(self) -> int:
        """Decrement concurrent request counter.
        
        Returns:
            New concurrent request count
        """
        async with self._lock:
            self._config.resources.current_concurrent = max(
                0, self._config.resources.current_concurrent - 1
            )
            return self._config.resources.current_concurrent
    
    async def check_rate_limit(self) -> bool:
        """Check if request should be rate limited.
        
        Returns:
            True if request is allowed, False if rate limited
        """
        config = await self.get_config()
        
        if not config.errors.rate_limit.enabled:
            return True
        
        if self._token_bucket is None:
            # Initialize token bucket
            self._token_bucket = TokenBucket(
                rate=config.errors.rate_limit.requests_per_second,
                capacity=config.errors.rate_limit.bucket_size
            )
        
        return await self._token_bucket.consume(1)
    
    async def record_request(self):
        """Record a request timestamp for RPS calculation."""
        async with self._lock:
            now = time.time()
            # Remove old timestamps outside the window
            cutoff = now - self._request_window_seconds
            self._request_timestamps = [ts for ts in self._request_timestamps if ts > cutoff]
            self._request_timestamps.append(now)
    
    async def get_current_rps(self) -> float:
        """Get current requests per second.
        
        Returns:
            Current RPS
        """
        async with self._lock:
            now = time.time()
            cutoff = now - self._request_window_seconds
            recent_requests = [ts for ts in self._request_timestamps if ts > cutoff]
            return len(recent_requests) / self._request_window_seconds


# Global singleton instance
chaos_state = ChaosState()
