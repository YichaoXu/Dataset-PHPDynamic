"""
GitHub API客户端

本模块管理与GitHub API的交互，搜索PHP项目，遵循GitHub API最佳实践。
"""

from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from .cache_manager import CacheManager
from .exceptions import GitHubAPIError, RateLimitError
from .rate_limit_handler import RateLimitHandler


class GitHubAPIClient:
    """管理与GitHub API的交互，搜索PHP项目"""

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        api_token: str,
        cache_manager: CacheManager,
        rate_limit_handler: RateLimitHandler,
    ) -> None:
        """
        初始化GitHub API客户端

        Args:
            api_token: GitHub API访问令牌
            cache_manager: 缓存管理器
            rate_limit_handler: 速率限制处理器

        Raises:
            GitHubAPIError: 令牌无效
        """
        if not api_token:
            raise GitHubAPIError("GitHub API token is required")

        self.api_token = api_token
        self.cache_manager = cache_manager
        self.rate_limit_handler = rate_limit_handler

        # 创建HTTP会话
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {api_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "PHPIncludes/1.0.0",
            }
        )

    def search_code_content(
        self, query: str, language: str = "PHP", per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """
        使用GitHub Code Search API搜索包含特定代码的仓库

        Args:
            query: 搜索查询字符串
            language: 编程语言
            per_page: 每页结果数量

        Returns:
            代码搜索结果列表

        Raises:
            GitHubAPIError: API请求失败
        """
        search_query = f"{query} language:{language}"
        url = urljoin(self.BASE_URL, "/search/code")

        params: Dict[str, Any] = {
            "q": search_query,
            "per_page": min(per_page, 100),  # GitHub限制最大100
            "sort": "indexed",
            "order": "desc",
        }

        cache_key = self.cache_manager.generate_cache_key(url, params)

        # 尝试从缓存获取
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            return cached_result

        try:
            # 等待速率限制
            self.rate_limit_handler.wait_if_needed()

            response = self.session.get(url, params=params, timeout=30)

            # 检查速率限制
            self.rate_limit_handler.update_from_response(response)

            if response.status_code == 200:
                data = response.json()
                results = data.get("items", [])

                # 缓存结果（1小时）
                self.cache_manager.set(cache_key, results, expire_after=3600)

                return results
            else:
                raise GitHubAPIError(
                    f"GitHub API request failed: {response.status_code}",
                    response.status_code,
                    response.text,
                )

        except requests.RequestException as e:
            raise GitHubAPIError(f"Network error during GitHub API request: {e}")
        except RateLimitError:
            raise  # 重新抛出速率限制错误

    def get_repository_contents(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """
        获取仓库的文件内容列表

        Args:
            owner: 仓库所有者
            repo: 仓库名

        Returns:
            文件内容信息列表

        Raises:
            GitHubAPIError: API请求失败
        """
        url = urljoin(self.BASE_URL, f"/repos/{owner}/{repo}/contents")
        cache_key = self.cache_manager.generate_cache_key(url)

        # 尝试从缓存获取
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            return cached_result

        try:
            self.rate_limit_handler.wait_if_needed()

            response = self.session.get(url, timeout=30)
            self.rate_limit_handler.update_from_response(response)

            if response.status_code == 200:
                contents = response.json()

                # 缓存结果（30分钟）
                self.cache_manager.set(cache_key, contents, expire_after=1800)

                return contents
            else:
                raise GitHubAPIError(
                    f"Failed to get repository contents: {response.status_code}",
                    response.status_code,
                    response.text,
                )

        except requests.RequestException as e:
            raise GitHubAPIError(f"Network error getting repository contents: {e}")

    def get_file_content(self, owner: str, repo: str, file_path: str) -> str:
        """
        获取指定文件的内容

        Args:
            owner: 仓库所有者
            repo: 仓库名
            file_path: 文件路径

        Returns:
            文件内容字符串

        Raises:
            GitHubAPIError: 文件未找到或API请求失败
        """
        url = urljoin(self.BASE_URL, f"/repos/{owner}/{repo}/contents/{file_path}")
        cache_key = self.cache_manager.generate_cache_key(url)

        # 尝试从缓存获取
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            return cached_result

        try:
            self.rate_limit_handler.wait_if_needed()

            response = self.session.get(url, timeout=30)
            self.rate_limit_handler.update_from_response(response)

            if response.status_code == 200:
                file_data = response.json()

                # GitHub API返回base64编码的内容
                import base64

                content = base64.b64decode(file_data["content"]).decode("utf-8")

                # 缓存结果（30分钟）
                self.cache_manager.set(cache_key, content, expire_after=1800)

                return content
            elif response.status_code == 404:
                raise GitHubAPIError(f"File not found: {file_path}")
            else:
                raise GitHubAPIError(
                    f"Failed to get file content: {response.status_code}",
                    response.status_code,
                    response.text,
                )

        except requests.RequestException as e:
            raise GitHubAPIError(f"Network error getting file content: {e}")

    def get_repository_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        获取仓库基本信息

        Args:
            owner: 仓库所有者
            repo: 仓库名

        Returns:
            仓库信息字典

        Raises:
            GitHubAPIError: API请求失败
        """
        url = urljoin(self.BASE_URL, f"/repos/{owner}/{repo}")
        cache_key = self.cache_manager.generate_cache_key(url)

        # 尝试从缓存获取
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            return cached_result

        try:
            self.rate_limit_handler.wait_if_needed()

            response = self.session.get(url, timeout=30)
            self.rate_limit_handler.update_from_response(response)

            if response.status_code == 200:
                repo_info = response.json()

                # 缓存结果（1小时）
                self.cache_manager.set(cache_key, repo_info, expire_after=3600)

                return repo_info
            else:
                raise GitHubAPIError(
                    f"Failed to get repository info: {response.status_code}",
                    response.status_code,
                    response.text,
                )

        except requests.RequestException as e:
            raise GitHubAPIError(f"Network error getting repository info: {e}")

    def make_authenticated_request(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """
        发起经过身份验证的API请求

        Args:
            url: API URL
            params: 查询参数

        Returns:
            HTTP响应对象

        Raises:
            RateLimitError: 速率限制被触发
            GitHubAPIError: 请求失败
        """
        try:
            self.rate_limit_handler.wait_if_needed()

            response = self.session.get(url, params=params, timeout=30)
            self.rate_limit_handler.update_from_response(response)

            return response

        except requests.RequestException as e:
            raise GitHubAPIError(f"Network error during authenticated request: {e}")

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        获取当前速率限制状态

        Returns:
            速率限制状态信息
        """
        return self.rate_limit_handler.get_status()

    def close(self) -> None:
        """关闭HTTP会话"""
        self.session.close()
