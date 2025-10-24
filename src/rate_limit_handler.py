"""
速率限制处理器

本模块处理GitHub API的速率限制，确保请求符合最佳实践。
"""

import time
from datetime import datetime, timedelta
from typing import Any, Optional

from .exceptions import RateLimitError


class RateLimitHandler:
    """处理GitHub API速率限制"""

    def __init__(self, request_delay: float = 1.0) -> None:
        """
        初始化速率限制处理器

        Args:
            request_delay: 请求间隔时间（秒）
        """
        self.request_delay = request_delay
        self.rate_limit_remaining: Optional[int] = None
        self.rate_limit_reset: Optional[datetime] = None
        self.last_request_time: Optional[float] = None

    def check_rate_limit(self, response: Any) -> None:
        """
        检查响应中的速率限制信息

        Args:
            response: HTTP响应对象

        Raises:
            RateLimitError: 速率限制被触发
        """
        # 从响应头获取速率限制信息
        self.rate_limit_remaining = self._get_header_int(
            response, "X-RateLimit-Remaining"
        )
        reset_timestamp = self._get_header_int(response, "X-RateLimit-Reset")

        if reset_timestamp:
            self.rate_limit_reset = datetime.fromtimestamp(reset_timestamp)

        # 检查是否触发速率限制
        if self.rate_limit_remaining == 0:
            reset_time = self.rate_limit_reset or datetime.now() + timedelta(hours=1)
            raise RateLimitError(
                "GitHub API rate limit exceeded",
                reset_time=int(reset_time.timestamp()),
                remaining=0,
            )

    def wait_for_rate_limit_reset(self) -> None:
        """
        等待速率限制重置

        Raises:
            RateLimitError: 等待时间过长
        """
        if not self.rate_limit_reset:
            raise RateLimitError("No rate limit reset time available")

        wait_time = (self.rate_limit_reset - datetime.now()).total_seconds()

        if wait_time > 0:
            if wait_time > 3600:  # 超过1小时
                raise RateLimitError(
                    f"Rate limit reset time too far in future: {wait_time} seconds"
                )

            time.sleep(wait_time)

    def should_wait(self) -> bool:
        """
        判断是否需要等待

        Returns:
            是否需要等待
        """
        if self.last_request_time is None:
            return False

        elapsed = time.time() - (self.last_request_time or 0)
        return elapsed < self.request_delay

    def get_wait_time(self) -> float:
        """
        获取需要等待的时间

        Returns:
            等待时间（秒）
        """
        if not self.should_wait():
            return 0.0

        elapsed = time.time() - (self.last_request_time or 0)
        return max(0.0, self.request_delay - elapsed)

    def wait_if_needed(self) -> None:
        """如果需要则等待"""
        if self.should_wait():
            wait_time = self.get_wait_time()
            if wait_time > 0:
                time.sleep(wait_time)

        self.last_request_time = time.time()

    def update_from_response(self, response: Any) -> None:
        """
        从响应更新速率限制信息

        Args:
            response: HTTP响应对象
        """
        try:
            self.check_rate_limit(response)
        except RateLimitError:
            # 如果触发速率限制，尝试等待重置
            try:
                self.wait_for_rate_limit_reset()
            except RateLimitError as e:
                # 如果等待失败，重新抛出原始错误
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
        获取当前速率限制状态

        Returns:
            包含速率限制状态的字典
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
        从响应头获取整数值

        Args:
            response: HTTP响应对象
            header_name: 头部名称

        Returns:
            整数值或None
        """
        try:
            value = response.headers.get(header_name)
            return int(value) if value else None
        except (ValueError, AttributeError):
            return None
