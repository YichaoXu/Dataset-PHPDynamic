"""
Rate Limit Handler

This module handles GitHub API rate limiting, ensuring requests follow best practices.
"""

import time
from datetime import datetime, timedelta
from typing import Any, Optional

from .exceptions import RateLimitError


class RateLimitHandler:
    """Handles GitHub API rate limiting"""

    def __init__(self, request_delay: float = 1.0) -> None:
        """
        Initialize rate limit handler

        Args:
            request_delay: Request delay in seconds
        """
        self.request_delay = request_delay
        self.rate_limit_remaining: Optional[int] = None
        self.rate_limit_reset: Optional[datetime] = None
        self.last_request_time: Optional[float] = None

    def check_rate_limit(self, response: Any) -> None:
        """
        Check rate limit information in response

        Args:
            response: HTTP response object

        Raises:
            RateLimitError: Rate limit triggered
        """
        # Get rate limit information from response headers
        self.rate_limit_remaining = self._get_header_int(
            response, "X-RateLimit-Remaining"
        )
        reset_timestamp = self._get_header_int(response, "X-RateLimit-Reset")

        if reset_timestamp:
            self.rate_limit_reset = datetime.fromtimestamp(reset_timestamp)

        # Check if rate limit is triggered
        if self.rate_limit_remaining == 0:
            reset_time = self.rate_limit_reset or datetime.now() + timedelta(hours=1)
            raise RateLimitError(
                "GitHub API rate limit exceeded",
                reset_time=int(reset_time.timestamp()),
                remaining=0,
            )

    def wait_for_rate_limit_reset(self) -> None:
        """
        Wait for rate limit reset

        Raises:
            RateLimitError: Wait time too long
        """
        if not self.rate_limit_reset:
            raise RateLimitError("No rate limit reset time available")

        wait_time = (self.rate_limit_reset - datetime.now()).total_seconds()

        if wait_time > 0:
            if wait_time > 3600:  # Exceeds 1 hour
                raise RateLimitError(
                    f"Rate limit reset time too far in future: {wait_time} seconds"
                )

            time.sleep(wait_time)

    def should_wait(self) -> bool:
        """
        Determine if waiting is needed

        Returns:
            Whether waiting is needed
        """
        if self.last_request_time is None:
            return False

        elapsed = time.time() - (self.last_request_time or 0)
        return elapsed < self.request_delay

    def get_wait_time(self) -> float:
        """
        Get required wait time

        Returns:
            Wait time in seconds
        """
        if not self.should_wait():
            return 0.0

        elapsed = time.time() - (self.last_request_time or 0)
        return max(0.0, self.request_delay - elapsed)

    def wait_if_needed(self) -> None:
        """Wait if needed"""
        if self.should_wait():
            wait_time = self.get_wait_time()
            if wait_time > 0:
                time.sleep(wait_time)

        self.last_request_time = time.time()

    def update_from_response(self, response: Any) -> None:
        """
        Update rate limit information from response

        Args:
            response: HTTP response object
        """
        try:
            self.check_rate_limit(response)
        except RateLimitError:
            # If rate limit triggered, try to wait for reset
            try:
                self.wait_for_rate_limit_reset()
            except RateLimitError as e:
                # If wait failed, re-raise original error
                raise RateLimitError(
                    f"Rate limit exceeded and cannot wait for reset: {e}",
                    (
                        int(self.rate_limit_reset.timestamp())
                        if self.rate_limit_reset
                        else None
                    ),
                    self.rate_limit_remaining or 0,
                )

    def get_status(self) -> dict:
        """
        Get current rate limit status

        Returns:
            Dictionary containing rate limit status
        """
        return {
            "remaining": self.rate_limit_remaining,
            "reset_time": (
                self.rate_limit_reset.isoformat() if self.rate_limit_reset else None
            ),
            "request_delay": self.request_delay,
            "last_request_time": self.last_request_time,
            "should_wait": self.should_wait(),
            "wait_time": self.get_wait_time(),
        }

    def _get_header_int(self, response: Any, header_name: str) -> Optional[int]:
        """
        Get integer value from response header

        Args:
            response: HTTP response object
            header_name: Header name

        Returns:
            Integer value or None
        """
        try:
            value = response.headers.get(header_name)
            return int(value) if value else None
        except (ValueError, AttributeError):
            return None
