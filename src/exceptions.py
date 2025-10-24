"""
异常类定义

本模块定义了项目中使用的所有自定义异常类。
"""

from typing import Optional


class GitHubAPIError(Exception):
    """GitHub API请求失败或返回错误时抛出"""

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
    """PHP代码分析过程中出现错误时抛出"""

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
    """Semgrep静态分析失败时抛出"""

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
    """缓存操作失败时抛出"""

    def __init__(
        self, message: str, operation: Optional[str] = None, key: Optional[str] = None
    ) -> None:
        super().__init__(message)
        self.operation = operation
        self.key = key


class RateLimitError(Exception):
    """GitHub API速率限制被触发时抛出"""

    def __init__(
        self,
        message: str,
        reset_time: Optional[int] = None,
        remaining: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.reset_time = reset_time
        self.remaining = remaining
