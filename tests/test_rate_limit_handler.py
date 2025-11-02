"""
Rate Limit Handler Tests

Tests for RateLimitHandler class.
"""

import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock

from php_dynctrlflow.exceptions import RateLimitError
from php_dynctrlflow.rate_limit_handler import RateLimitHandler


class TestRateLimitHandler(unittest.TestCase):
    """Test RateLimitHandler class"""

    def setUp(self) -> None:
        """Test setup"""
        self.handler = RateLimitHandler(request_delay=0.1)

    def test_init(self) -> None:
        """Test initialization"""
        handler = RateLimitHandler(request_delay=1.0)
        self.assertEqual(handler.request_delay, 1.0)
        self.assertIsNone(handler.rate_limit_remaining)
        self.assertIsNone(handler.rate_limit_reset)

    def test_should_wait_initially_false(self) -> None:
        """Test should_wait initially returns False"""
        self.assertFalse(self.handler.should_wait())

    def test_should_wait_after_request(self) -> None:
        """Test should_wait returns True immediately after request"""
        self.handler.last_request_time = time.time()
        # Should wait if less than request_delay has passed
        self.assertTrue(self.handler.should_wait())

    def test_get_wait_time_initially_zero(self) -> None:
        """Test get_wait_time initially returns 0"""
        self.assertEqual(self.handler.get_wait_time(), 0.0)

    def test_get_wait_time_after_request(self) -> None:
        """Test get_wait_time returns correct wait time"""
        self.handler.last_request_time = time.time()
        wait_time = self.handler.get_wait_time()
        self.assertGreater(wait_time, 0)
        self.assertLessEqual(wait_time, self.handler.request_delay)

    def test_wait_if_needed_no_wait(self) -> None:
        """Test wait_if_needed doesn't wait when not needed"""
        start_time = time.time()
        self.handler.wait_if_needed()
        elapsed = time.time() - start_time
        # Should not wait (or wait very briefly)
        self.assertLess(elapsed, 0.05)

    def test_update_from_response(self) -> None:
        """Test update_from_response method"""
        mock_response = Mock()
        mock_response.headers = {
            "X-RateLimit-Remaining": "100",
            "X-RateLimit-Reset": str(int(time.time()) + 3600),
        }

        self.handler.update_from_response(mock_response)

        self.assertEqual(self.handler.rate_limit_remaining, 100)
        self.assertIsNotNone(self.handler.rate_limit_reset)

    def test_update_from_response_rate_limit_exceeded(self) -> None:
        """Test update_from_response when rate limit is exceeded"""
        mock_response = Mock()
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + 3600),
        }

        # Should raise RateLimitError when remaining is 0
        with self.assertRaises(RateLimitError):
            self.handler.update_from_response(mock_response)

    def test_get_status(self) -> None:
        """Test get_status method"""
        self.handler.rate_limit_remaining = 100
        self.handler.rate_limit_reset = datetime.now() + timedelta(hours=1)

        status = self.handler.get_status()

        self.assertIn("remaining", status)
        self.assertIn("reset_time", status)
        self.assertIn("request_delay", status)
        self.assertIn("should_wait", status)
        self.assertIn("wait_time", status)
        self.assertEqual(status["remaining"], 100)

    def test_get_header_int_valid(self) -> None:
        """Test _get_header_int with valid integer header"""
        mock_response = Mock()
        mock_response.headers = {"X-Test-Header": "123"}

        value = self.handler._get_header_int(mock_response, "X-Test-Header")
        self.assertEqual(value, 123)

    def test_get_header_int_missing(self) -> None:
        """Test _get_header_int with missing header"""
        mock_response = Mock()
        mock_response.headers = {}

        value = self.handler._get_header_int(mock_response, "X-Missing-Header")
        self.assertIsNone(value)

    def test_get_header_int_invalid(self) -> None:
        """Test _get_header_int with invalid integer header"""
        mock_response = Mock()
        mock_response.headers = {"X-Test-Header": "not_a_number"}

        value = self.handler._get_header_int(mock_response, "X-Test-Header")
        self.assertIsNone(value)


if __name__ == "__main__":
    unittest.main()

