"""
Exception Classes

This module defines all custom exception classes used in the project.
"""

from typing import Optional


class GitHubAPIError(Exception):
    """Raised when GitHub API request fails or returns an error"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class AnalysisError(Exception):
    """Raised when an error occurs during PHP code analysis"""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.file_path = file_path
        self.line_number = line_number


class SemgrepError(Exception):
    """Raised when Semgrep static analysis fails"""

    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.command = command
        self.exit_code = exit_code


class CacheError(Exception):
    """Raised when cache operation fails"""

    def __init__(
        self, message: str, operation: Optional[str] = None, key: Optional[str] = None
    ) -> None:
        super().__init__(message)
        self.operation = operation
        self.key = key


class RateLimitError(Exception):
    """Raised when GitHub API rate limit is triggered"""

    def __init__(
        self,
        message: str,
        reset_time: Optional[int] = None,
        remaining: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.reset_time = reset_time
        self.remaining = remaining
