"""
Simple in-memory rate limiter for API endpoints.
"""

import time
from collections import defaultdict
from typing import Dict, Tuple


class RateLimiter:
    """
    Simple token bucket rate limiter.
    Tracks request counts per client IP address.
    """

    def __init__(self, requests_per_minute: int = 10):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute per client
        """
        self.requests_per_minute = requests_per_minute
        self.window_size = 60.0  # 1 minute in seconds

        # Store: client_ip -> list of timestamps
        self.requests: Dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        """
        Check if request is allowed for this client.

        Args:
            client_ip: Client IP address

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        current_time = time.time()

        # Clean up old requests outside the window
        self.requests[client_ip] = [
            ts
            for ts in self.requests[client_ip]
            if current_time - ts < self.window_size
        ]

        request_count = len(self.requests[client_ip])

        if request_count >= self.requests_per_minute:
            return False, 0

        # Allow request and record timestamp
        self.requests[client_ip].append(current_time)
        remaining = self.requests_per_minute - request_count - 1

        return True, remaining

    def reset(self, client_ip: str):
        """Reset rate limit for a specific client."""
        if client_ip in self.requests:
            del self.requests[client_ip]

    def cleanup_old_entries(self, max_age: float = 3600.0):
        """
        Clean up entries older than max_age seconds.
        Call this periodically to prevent memory buildup.
        """
        current_time = time.time()

        clients_to_remove = []
        for client_ip, timestamps in self.requests.items():
            # Remove old timestamps
            timestamps[:] = [ts for ts in timestamps if current_time - ts < max_age]

            # Mark for removal if no recent requests
            if not timestamps:
                clients_to_remove.append(client_ip)

        for client_ip in clients_to_remove:
            del self.requests[client_ip]
