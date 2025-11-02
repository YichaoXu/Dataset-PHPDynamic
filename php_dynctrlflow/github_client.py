"""
GitHub API Client

This module manages interactions with the GitHub API, searches for PHP projects,
and follows GitHub API best practices.
"""

from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from .cache_manager import CacheManager
from .exceptions import GitHubAPIError, RateLimitError
from .rate_limit_handler import RateLimitHandler


class GitHubAPIClient:
    """Manages interactions with the GitHub API and searches for PHP projects"""

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        api_token: str,
        cache_manager: CacheManager,
        rate_limit_handler: RateLimitHandler,
    ) -> None:
        """
        Initialize GitHub API client

        Args:
            api_token: GitHub API access token
            cache_manager: Cache manager
            rate_limit_handler: Rate limit handler

        Raises:
            GitHubAPIError: Invalid token
        """
        if not api_token:
            raise GitHubAPIError("GitHub API token is required")

        self.api_token = api_token
        self.cache_manager = cache_manager
        self.rate_limit_handler = rate_limit_handler

        # Create HTTP session
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {api_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Dataset-PHPDynCtrlflow/1.0.0",
            }
        )

    def search_code_content(
        self, query: str, language: str = "PHP", per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search for repositories containing specific code using GitHub Code Search API

        Args:
            query: Search query string
            language: Programming language
            per_page: Number of results per page

        Returns:
            List of code search results

        Raises:
            GitHubAPIError: API request failed
        """
        search_query = f"{query} language:{language}"
        url = urljoin(self.BASE_URL, "/search/code")

        params: Dict[str, Any] = {
            "q": search_query,
            "per_page": min(per_page, 100),  # GitHub maximum limit is 100
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

        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result and isinstance(cached_result, list):
            print(f"  ✅ Cache hit: Found {len(cached_result)} cached results")
            return list(cached_result)  # Type conversion for mypy

        print("  🔄 Cache miss: Making API request...")

        try:
            # Wait for rate limit
            self.rate_limit_handler.wait_if_needed()
            rate_status = self.rate_limit_handler.get_status()
            print(
                f"  ⏱️  Rate limit status: {rate_status.get('remaining', 'N/A')} requests remaining, reset at {rate_status.get('reset_time', 'N/A')}"
            )

            response = self.session.get(url, params=params, timeout=30)

            # Check rate limit
            self.rate_limit_handler.update_from_response(response)
            rate_status = self.rate_limit_handler.get_status()
            print(
                f"  ⏱️  Rate limit after request: {rate_status.get('remaining', 'N/A')} requests remaining"
            )

            print(f"  📥 Response status: {response.status_code}")

            if response.status_code == 200:
                data: Dict[str, Any] = response.json()
                total_count = data.get("total_count", 0)
                results: List[Dict[str, Any]] = data.get("items", [])
                incomplete_results = data.get("incomplete_results", False)

                print("  ✅ API Response successful:")
                print(f"     Total matches: {total_count}")
                print(f"     Results returned: {len(results)}")
                print(f"     Incomplete results: {incomplete_results}")

                # Count result types
                repos = set()
                for item in results:
                    repo = item.get("repository", {}).get("full_name", "unknown")
                    repos.add(repo)
                print(f"     Unique repositories: {len(repos)}")

                # Cache results (1 hour)
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
            raise  # Re-raise rate limit error

    def search_code_in_repository(
        self, owner: str, repo: str, query: str, language: str = "PHP"
    ) -> List[Dict[str, Any]]:
        """
        Search code content within a specific repository

        Args:
            owner: Repository owner
            repo: Repository name
            query: Search query string
            language: Programming language

        Returns:
            List of code search results

        Raises:
            GitHubAPIError: API request failed
        """
        search_query = f"{query} language:{language} repo:{owner}/{repo}"
        url = urljoin(self.BASE_URL, "/search/code")

        params: Dict[str, Any] = {
            "q": search_query,
            "per_page": 100,  # GitHub maximum limit is 100
            "sort": "indexed",
            "order": "desc",
        }

        cache_key = self.cache_manager.generate_cache_key(url, params)

        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result and isinstance(cached_result, list):
            return list(cached_result)  # Type conversion for mypy

        try:
            # Wait for rate limit
            self.rate_limit_handler.wait_if_needed()

            response = self.session.get(url, params=params, timeout=30)

            # Check rate limit
            self.rate_limit_handler.update_from_response(response)

            if response.status_code == 200:
                data = response.json()
                results = data.get("items", [])

                # Cache results (1 hour)
                self.cache_manager.set(cache_key, results, expire_after=3600)

                return list(results)  # Type conversion for mypy
            else:
                raise GitHubAPIError(
                    f"GitHub API request failed: {response.status_code}",
                    response.status_code,
                    response.text,
                )

        except requests.RequestException as e:
            raise GitHubAPIError(f"Network error during GitHub API request: {e}") from e
        except RateLimitError:
            raise  # Re-raise rate limit error

    def search_repositories_optimized(
        self, query: str, per_page: int = 100, page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Optimized repository search using Repository Search API

        Args:
            query: Search query
            per_page: Number of results per page
            page: Page number (starting from 1)

        Returns:
            repositorySearch result list

        Raises:
            GitHubAPIError: API request failed
        """
        url = urljoin(self.BASE_URL, "/search/repositories")

        params: Dict[str, Any] = {
            "q": query,
            "per_page": min(per_page, 100),  # GitHub maximum limit is 100
            "page": page,
            "sort": "stars",
            "order": "desc",
        }

        cache_key = self.cache_manager.generate_cache_key(url, params)

        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result and isinstance(cached_result, list):
            return list(cached_result)  # Type conversion for mypy

        try:
            # Wait for rate limit
            self.rate_limit_handler.wait_if_needed()

            response = self.session.get(url, params=params, timeout=30)

            # Check rate limit
            self.rate_limit_handler.update_from_response(response)

            if response.status_code == 200:
                data: Dict[str, Any] = response.json()
                results: List[Dict[str, Any]] = data.get("items", [])

                # Cache results (2 hours, repository info changes less)
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
            raise  # Re-raise rate limit error

    def get_repository_contents(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """
        Get repository file content list

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            File content information list

        Raises:
            GitHubAPIError: API request failed
        """
        url = urljoin(self.BASE_URL, f"/repos/{owner}/{repo}/contents")
        print(f"        📡 Repository Contents API: {url}")
        cache_key = self.cache_manager.generate_cache_key(url)

        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result and isinstance(cached_result, list):
            print(f"        ✅ Cache hit: Found {len(cached_result)} items")
            return list(cached_result)  # Type conversion for mypy

        print("        🔄 Cache miss: Making API request...")

        try:
            self.rate_limit_handler.wait_if_needed()

            response = self.session.get(url, timeout=30)
            self.rate_limit_handler.update_from_response(response)

            print(f"        📥 Response status: {response.status_code}")

            if response.status_code == 200:
                contents: List[Dict[str, Any]] = response.json()
                print(f"        ✅ Success: Retrieved {len(contents)} items")

                # Cache results (30 minutes)
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
        Get content of specified file

        Args:
            owner: Repository owner
            repo: Repository name
            file_path: File path

        Returns:
            File contentstring

        Raises:
            GitHubAPIError: File not found or API request failed
        """
        url = urljoin(self.BASE_URL, f"/repos/{owner}/{repo}/contents/{file_path}")
        print(f"            📡 File Content API: {file_path}")
        cache_key = self.cache_manager.generate_cache_key(url)

        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result and isinstance(cached_result, str):
            print(
                f"            ✅ Cache hit: Found cached file ({len(cached_result)} chars)"
            )
            return str(cached_result)  # Type conversion for mypy

        print("            🔄 Cache miss: Making API request...")

        try:
            self.rate_limit_handler.wait_if_needed()

            response = self.session.get(url, timeout=30)
            self.rate_limit_handler.update_from_response(response)

            print(f"            📥 Response status: {response.status_code}")

            if response.status_code == 200:
                file_data: Dict[str, Any] = response.json()

                # GitHub API returns base64-encoded content
                import base64

                content: str = base64.b64decode(file_data["content"]).decode("utf-8")
                print(f"            ✅ Success: Retrieved file ({len(content)} chars)")

                # Cache results (30 minutes)
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
        Get basic repository information

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Repository information dictionary

        Raises:
            GitHubAPIError: API request failed
        """
        url = urljoin(self.BASE_URL, f"/repos/{owner}/{repo}")
        cache_key = self.cache_manager.generate_cache_key(url)

        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result and isinstance(cached_result, dict):
            return dict(cached_result)  # Type conversion for mypy

        try:
            self.rate_limit_handler.wait_if_needed()

            response = self.session.get(url, timeout=30)
            self.rate_limit_handler.update_from_response(response)

            if response.status_code == 200:
                repo_info: Dict[str, Any] = response.json()

                # Cache results (1 hour)
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

    def get_branch_commit_sha(self, owner: str, repo: str, branch: str = "main") -> str:
        """
        Get latest commit SHA for specified branch

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name (default: main)

        Returns:
            Commit SHA string (returns branch name as fallback if get failed)
        """
        # Use /repos/{owner}/{repo}/commits/{branch} to get latest commit
        # Note: This endpoint returns a single commit object, not a list
        url = urljoin(self.BASE_URL, f"/repos/{owner}/{repo}/commits/{branch}")
        cache_key = self.cache_manager.generate_cache_key(url)

        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            if isinstance(cached_result, dict):
                sha = cached_result.get("sha", branch)
                return str(sha) if sha else branch  # Type conversion for mypy
            elif isinstance(cached_result, str):
                return str(cached_result)  # Type conversion for mypy
            return branch

        try:
            self.rate_limit_handler.wait_if_needed()

            response = self.session.get(url, timeout=30)
            self.rate_limit_handler.update_from_response(response)

            if response.status_code == 200:
                commit_data: Dict[str, Any] = response.json()
                # API returns a single commit object containing sha field
                commit_sha: str = commit_data.get("sha", branch) or branch

                # Cache results (30 minutes)
                self.cache_manager.set(cache_key, commit_data, expire_after=1800)

                return commit_sha
            elif response.status_code == 404:
                # Branch does not exist, return branch name as fallback
                return branch
            else:
                # Other error, return branch name as fallback
                return branch

        except requests.RequestException:
            # If request fails, return branch name as fallback
            return branch

    def make_authenticated_request(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """
        Make authenticated API request

        Args:
            url: API URL
            params: Query parameters

        Returns:
            HTTP response object

        Raises:
            RateLimitError: Rate limit triggered
            GitHubAPIError: Request failed
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
        Get current rate limit status

        Returns:
            Rate limit status information
        """
        return self.rate_limit_handler.get_status()

    def close(self) -> None:
        """Close HTTP session"""
        self.session.close()
