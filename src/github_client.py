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

        print("  📡 GitHub API Request:")
        print(f"     URL: {url}")
        print(f"     Query: {search_query}")
        print(
            f"     Params: per_page={params['per_page']}, sort={params['sort']}, order={params['order']}"
        )

        cache_key = self.cache_manager.generate_cache_key(url, params)

        # 尝试从缓存获取
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            print(f"  ✅ Cache hit: Found {len(cached_result)} cached results")
            return cached_result

        print("  🔄 Cache miss: Making API request...")

        try:
            # 等待速率限制
            self.rate_limit_handler.wait_if_needed()
            rate_status = self.rate_limit_handler.get_status()
            print(
                f"  ⏱️  Rate limit status: {rate_status.get('remaining', 'N/A')} requests remaining, reset at {rate_status.get('reset_time', 'N/A')}"
            )

            response = self.session.get(url, params=params, timeout=30)

            # 检查速率限制
            self.rate_limit_handler.update_from_response(response)
            rate_status = self.rate_limit_handler.get_status()
            print(
                f"  ⏱️  Rate limit after request: {rate_status.get('remaining', 'N/A')} requests remaining"
            )

            print(f"  📥 Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                total_count = data.get("total_count", 0)
                results = data.get("items", [])
                incomplete_results = data.get("incomplete_results", False)

                print("  ✅ API Response successful:")
                print(f"     Total matches: {total_count}")
                print(f"     Results returned: {len(results)}")
                print(f"     Incomplete results: {incomplete_results}")

                # 统计结果类型
                repos = set()
                for item in results:
                    repo = item.get("repository", {}).get("full_name", "unknown")
                    repos.add(repo)
                print(f"     Unique repositories: {len(repos)}")

                # 缓存结果（1小时）
                self.cache_manager.set(cache_key, results, expire_after=3600)
                print("  💾 Results cached for 1 hour")

                return results
            else:
                error_text = (
                    response.text[:500] if response.text else "No error message"
                )
                print("  ❌ API Error:")
                print(f"     Status code: {response.status_code}")
                print(f"     Error message: {error_text}")
                raise GitHubAPIError(
                    f"GitHub API request failed: {response.status_code}",
                    response.status_code,
                    response.text,
                )

        except requests.RequestException as e:
            print(f"  ❌ Network error: {e}")
            raise GitHubAPIError(f"Network error during GitHub API request: {e}") from e
        except RateLimitError:
            print("  ⚠️  Rate limit exceeded")
            raise  # 重新抛出速率限制错误

    def search_code_in_repository(
        self, owner: str, repo: str, query: str, language: str = "PHP"
    ) -> List[Dict[str, Any]]:
        """
        在特定仓库内搜索代码内容

        Args:
            owner: 仓库所有者
            repo: 仓库名
            query: 搜索查询字符串
            language: 编程语言

        Returns:
            代码搜索结果列表

        Raises:
            GitHubAPIError: API请求失败
        """
        search_query = f"{query} language:{language} repo:{owner}/{repo}"
        url = urljoin(self.BASE_URL, "/search/code")

        params: Dict[str, Any] = {
            "q": search_query,
            "per_page": 100,  # GitHub限制最大100
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
            raise GitHubAPIError(f"Network error during GitHub API request: {e}") from e
        except RateLimitError:
            raise  # 重新抛出速率限制错误

    def search_repositories_optimized(
        self, query: str, per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """
        优化的仓库搜索，使用Repository Search API

        Args:
            query: 搜索查询
            per_page: 每页结果数量

        Returns:
            仓库搜索结果列表

        Raises:
            GitHubAPIError: API请求失败
        """
        url = urljoin(self.BASE_URL, "/search/repositories")

        params: Dict[str, Any] = {
            "q": query,
            "per_page": min(per_page, 100),  # GitHub限制最大100
            "sort": "stars",
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

                # 缓存结果（2小时，仓库信息变化较少）
                self.cache_manager.set(cache_key, results, expire_after=7200)

                return results
            else:
                raise GitHubAPIError(
                    f"GitHub API request failed: {response.status_code}",
                    response.status_code,
                    response.text,
                )

        except requests.RequestException as e:
            raise GitHubAPIError(f"Network error during GitHub API request: {e}") from e
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
        print(f"        📡 Repository Contents API: {url}")
        cache_key = self.cache_manager.generate_cache_key(url)

        # 尝试从缓存获取
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            print(f"        ✅ Cache hit: Found {len(cached_result)} items")
            return cached_result

        print("        🔄 Cache miss: Making API request...")

        try:
            self.rate_limit_handler.wait_if_needed()

            response = self.session.get(url, timeout=30)
            self.rate_limit_handler.update_from_response(response)

            print(f"        📥 Response status: {response.status_code}")

            if response.status_code == 200:
                contents = response.json()
                print(f"        ✅ Success: Retrieved {len(contents)} items")

                # 缓存结果（30分钟）
                self.cache_manager.set(cache_key, contents, expire_after=1800)
                print("        💾 Results cached for 30 minutes")

                return contents
            else:
                print(f"        ❌ Error: Status {response.status_code}")
                print(f"        📋 Error message: {response.text[:200]}")
                raise GitHubAPIError(
                    f"Failed to get repository contents: {response.status_code}",
                    response.status_code,
                    response.text,
                )

        except requests.RequestException as e:
            print(f"        ❌ Network error: {e}")
            raise GitHubAPIError(
                f"Network error getting repository contents: {e}"
            ) from e

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
        print(f"            📡 File Content API: {file_path}")
        cache_key = self.cache_manager.generate_cache_key(url)

        # 尝试从缓存获取
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            print(
                f"            ✅ Cache hit: Found cached file ({len(cached_result)} chars)"
            )
            return cached_result

        print("            🔄 Cache miss: Making API request...")

        try:
            self.rate_limit_handler.wait_if_needed()

            response = self.session.get(url, timeout=30)
            self.rate_limit_handler.update_from_response(response)

            print(f"            📥 Response status: {response.status_code}")

            if response.status_code == 200:
                file_data = response.json()

                # GitHub API返回base64编码的内容
                import base64

                content = base64.b64decode(file_data["content"]).decode("utf-8")
                print(f"            ✅ Success: Retrieved file ({len(content)} chars)")

                # 缓存结果（30分钟）
                self.cache_manager.set(cache_key, content, expire_after=1800)
                print("            💾 File cached for 30 minutes")

                return content
            elif response.status_code == 404:
                print(f"            ❌ File not found: {file_path}")
                raise GitHubAPIError(f"File not found: {file_path}")
            else:
                print(f"            ❌ Error: Status {response.status_code}")
                print(f"            📋 Error message: {response.text[:200]}")
                raise GitHubAPIError(
                    f"Failed to get file content: {response.status_code}",
                    response.status_code,
                    response.text,
                )

        except requests.RequestException as e:
            print(f"            ❌ Network error: {e}")
            raise GitHubAPIError(f"Network error getting file content: {e}") from e

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
            raise GitHubAPIError(f"Network error getting repository info: {e}") from e

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
            raise GitHubAPIError(
                f"Network error during authenticated request: {e}"
            ) from e

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
