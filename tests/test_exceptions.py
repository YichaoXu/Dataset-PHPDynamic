"""
Exception Tests

Tests for custom exception classes.
"""

import unittest

from php_dynctrlflow.exceptions import (
    AnalysisError,
    CacheError,
    GitHubAPIError,
    RateLimitError,
    SemgrepError,
)


class TestGitHubAPIError(unittest.TestCase):
    """Test GitHubAPIError exception"""

    def test_init_with_message_only(self) -> None:
        """Test exception initialization with message only"""
        error = GitHubAPIError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertIsNone(error.status_code)
        self.assertIsNone(error.response_data)

    def test_init_with_all_params(self) -> None:
        """Test exception initialization with all parameters"""
        error = GitHubAPIError("Test error", status_code=404, response_data="Not found")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.status_code, 404)
        self.assertEqual(error.response_data, "Not found")


class TestAnalysisError(unittest.TestCase):
    """Test AnalysisError exception"""

    def test_init_with_message_only(self) -> None:
        """Test exception initialization with message only"""
        error = AnalysisError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertIsNone(error.file_path)
        self.assertIsNone(error.line_number)

    def test_init_with_all_params(self) -> None:
        """Test exception initialization with all parameters"""
        error = AnalysisError("Test error", file_path="test.php", line_number=10)
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.file_path, "test.php")
        self.assertEqual(error.line_number, 10)


class TestSemgrepError(unittest.TestCase):
    """Test SemgrepError exception"""

    def test_init_with_message_only(self) -> None:
        """Test exception initialization with message only"""
        error = SemgrepError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertIsNone(error.command)
        self.assertIsNone(error.exit_code)

    def test_init_with_all_params(self) -> None:
        """Test exception initialization with all parameters"""
        error = SemgrepError("Test error", command="semgrep --config rules.yml", exit_code=1)
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.command, "semgrep --config rules.yml")
        self.assertEqual(error.exit_code, 1)


class TestCacheError(unittest.TestCase):
    """Test CacheError exception"""

    def test_init_with_message_only(self) -> None:
        """Test exception initialization with message only"""
        error = CacheError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertIsNone(error.operation)
        self.assertIsNone(error.key)

    def test_init_with_all_params(self) -> None:
        """Test exception initialization with all parameters"""
        error = CacheError("Test error", operation="get", key="test_key")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.operation, "get")
        self.assertEqual(error.key, "test_key")


class TestRateLimitError(unittest.TestCase):
    """Test RateLimitError exception"""

    def test_init_with_message_only(self) -> None:
        """Test exception initialization with message only"""
        error = RateLimitError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertIsNone(error.reset_time)
        self.assertIsNone(error.remaining)

    def test_init_with_all_params(self) -> None:
        """Test exception initialization with all parameters"""
        error = RateLimitError("Test error", reset_time=1234567890, remaining=0)
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.reset_time, 1234567890)
        self.assertEqual(error.remaining, 0)


if __name__ == "__main__":
    unittest.main()

