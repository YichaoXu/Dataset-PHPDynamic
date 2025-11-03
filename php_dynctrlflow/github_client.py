"""
GitHub API Client

This module manages interactions with the GitHub API, searches for PHP projects,
and follows GitHub API best practices using PyGithub library.
"""

from typing import Any, Dict, List, Optional

from github import Github, GithubRetry
from github.GithubException import GithubException

from .cache_manager import CacheManager
from .exceptions import GitHubAPIError


class GitHubAPIClient:
    """Manages interactions with the GitHub API and searches for PHP projects"""

    def __init__(
        self,
        api_token: str,
        cache_manager: CacheManager,
        rate_limit_handler: Any,  # Keep for compatibility but PyGithub handles rate limiting
    ) -> None:
        """
        Initialize GitHub API client using PyGithub

        Args:
            api_token: GitHub API access token
            cache_manager: Cache manager
            rate_limit_handler: Rate limit handler (kept for compatibility, PyGithub handles rate limiting)

        Raises:
            GitHubAPIError: Invalid token
        """
        if not api_token:
            raise GitHubAPIError("GitHub API token is required")

        self.api_token = api_token
        self.cache_manager = cache_manager
        self.rate_limit_handler = rate_limit_handler

        # Initialize PyGithub client with automatic rate limiting and retry
        # Configure custom retry behavior: wait 1 hour (3600 seconds) for rate limit errors
        try:
            # Create custom GithubRetry with smart rate limit handling:
            # - For primary rate limits: Use X-RateLimit-Reset header (GitHub's recommended wait time)
            # - For secondary rate limits: Wait 1 hour (3600 seconds)
            # - Use reasonable backoff_factor to allow GitHub's recommended times to take precedence
            custom_retry = GithubRetry(
                total=3,  # Maximum number of retries
                backoff_factor=1,  # Exponential backoff factor (allows GitHub's recommended times to work)
                secondary_rate_wait=3600,  # Wait 1 hour (3600 seconds) for secondary rate limits only
            )
            
            self.github = Github(api_token, retry=custom_retry)
            
            # Log token setup (masked)
            token_preview = f"{api_token[:4]}...{api_token[-4:]}" if len(api_token) > 8 else "****"
            token_length = len(api_token)
            print(f"  🔑 PyGithub initialized: Bearer {token_preview} (length: {token_length})")
            print(f"  ⏱️  Rate limit retry configured: smart handling (primary=GitHub time, secondary=1 hour)")
            
            # Verify authentication by checking rate limit
            # Use rate_limiting property for simple access, or get_rate_limit() for detailed info
            remaining, limit = self.github.rate_limiting
            print(f"  ⏱️  Rate limit: {remaining}/{limit} remaining")
            
        except Exception as e:
            raise GitHubAPIError(f"Failed to initialize PyGithub: {e}") from e

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

        # Generate cache key
        url = f"https://api.github.com/search/code"
        params: Dict[str, Any] = {
            "q": search_query,
            "per_page": min(per_page, 100),
            "sort": "indexed",
            "order": "desc",
        }
        cache_key = self.cache_manager.generate_cache_key(url, params)

        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result and isinstance(cached_result, list):
            print(f"  ✅ Cache hit: Found {len(cached_result)} cached results")
            return list(cached_result)

        print("  🔄 Cache miss: Making API request...")
        print(f"  📡 GitHub API Request: {search_query}")

        try:
            # PyGithub search_code returns PaginatedList
            # Convert to list and limit to per_page
            results = []
            search_results = self.github.search_code(search_query, sort="indexed", order="desc")
            
            count = 0
            for file_content in search_results:
                if count >= per_page:
                    break
                
                # Convert ContentFile to dictionary format
                result_dict: Dict[str, Any] = {
                    "name": file_content.name,
                    "path": file_content.path,
                    "sha": file_content.sha,
                    "url": file_content.url,
                    "html_url": file_content.html_url,
                    "repository": {
                        "id": file_content.repository.id,
                        "name": file_content.repository.name,
                        "full_name": file_content.repository.full_name,
                        "owner": {
                            "login": file_content.repository.owner.login,
                            "id": file_content.repository.owner.id,
                        },
                        "html_url": file_content.repository.html_url,
                        "description": file_content.repository.description,
                        "stargazers_count": file_content.repository.stargazers_count,
                    },
                    "score": getattr(file_content, "score", None),
                }
                results.append(result_dict)
                count += 1

            print(f"  ✅ API Response successful: {len(results)} results")

            # Cache results (1 hour)
            self.cache_manager.set(cache_key, results, expire_after=3600)
            print("  💾 Results cached for 1 hour")

            return results

        except GithubException as e:
            error_msg = str(e)
            print(f"  ❌ API Error: {error_msg}")
            
            # Convert PyGithub exceptions to GitHubAPIError
            if e.status == 403:
                raise GitHubAPIError(
                    f"GitHub API returned 403 Forbidden. This may be due to rate limiting, permissions, or repository access restrictions. Error: {error_msg}",
                    e.status,
                    error_msg,
                ) from e
            else:
                raise GitHubAPIError(
                    f"GitHub API request failed: {error_msg}",
                    e.status if hasattr(e, "status") else 500,
                    error_msg,
                ) from e
        except Exception as e:
            raise GitHubAPIError(f"Unexpected error during GitHub API request: {e}") from e

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

        # Generate cache key
        url = f"https://api.github.com/search/code"
        params: Dict[str, Any] = {
            "q": search_query,
            "per_page": 100,
            "sort": "indexed",
            "order": "desc",
        }
        cache_key = self.cache_manager.generate_cache_key(url, params)

        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result and isinstance(cached_result, list):
            return list(cached_result)

        try:
            # PyGithub search_code returns PaginatedList
            results: List[Dict[str, Any]] = []
            search_results = self.github.search_code(search_query, sort="indexed", order="desc")
            
            # Handle case where search_results might be None
            if search_results is not None:
                for file_content in search_results:
                    # Convert ContentFile to dictionary format
                    try:
                        result_dict: Dict[str, Any] = {
                            "name": file_content.name,
                            "path": file_content.path,
                            "sha": file_content.sha,
                            "url": file_content.url,
                            "html_url": file_content.html_url,
                            "repository": {
                                "id": file_content.repository.id,
                                "name": file_content.repository.name,
                                "full_name": file_content.repository.full_name,
                                "owner": {
                                    "login": file_content.repository.owner.login,
                                    "id": file_content.repository.owner.id,
                                },
                                "html_url": file_content.repository.html_url,
                            },
                            "score": getattr(file_content, "score", None),
                        }
                        results.append(result_dict)
                    except Exception as item_error:
                        # Skip invalid items
                        continue

            # Cache successful response (1 hour)
            self.cache_manager.set(cache_key, results, expire_after=3600)

            return results

        except GithubException as e:
            error_msg = str(e)
            
            # Convert PyGithub exceptions to GitHubAPIError
            if e.status == 403:
                raise GitHubAPIError(
                    f"GitHub API returned 403 Forbidden for {owner}/{repo}. This may be due to rate limiting, permissions, or repository access restrictions. Error: {error_msg}",
                    e.status,
                    error_msg,
                ) from e
            else:
                raise GitHubAPIError(
                    f"GitHub API request failed for {owner}/{repo}: {error_msg}",
                    e.status if hasattr(e, "status") else 500,
                    error_msg,
                ) from e
        except Exception as e:
            raise GitHubAPIError(f"Unexpected error during GitHub API request for {owner}/{repo}: {e}") from e

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
        # Generate cache key
        url = f"https://api.github.com/search/repositories"
        params: Dict[str, Any] = {
            "q": query,
            "per_page": min(per_page, 100),
            "page": page,
            "sort": "stars",
            "order": "desc",
        }
        cache_key = self.cache_manager.generate_cache_key(url, params)

        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result and isinstance(cached_result, list):
            return list(cached_result)

        try:
            # PyGithub search_repositories returns PaginatedList
            results = []
            search_results = self.github.search_repositories(query, sort="stars", order="desc")
            
            # Handle pagination: PyGithub uses 1-based indexing for get_page()
            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            
            count = 0
            for repo in search_results:
                if count >= end_index:
                    break
                if count >= start_index:
                    # Convert Repository to dictionary format
                    result_dict: Dict[str, Any] = {
                        "id": repo.id,
                        "name": repo.name,
                        "full_name": repo.full_name,
                        "owner": {
                            "login": repo.owner.login,
                            "id": repo.owner.id,
                            "type": repo.owner.type,
                        },
                        "html_url": repo.html_url,
                        "description": repo.description,
                        "stargazers_count": repo.stargazers_count,
                        "language": repo.language,
                        "default_branch": repo.default_branch,
                        "created_at": repo.created_at.isoformat() if repo.created_at else None,
                        "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                        "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None,
                    }
                    results.append(result_dict)
                count += 1

                # Cache results (2 hours, repository info changes less)
                self.cache_manager.set(cache_key, results, expire_after=7200)

                return results

        except GithubException as e:
            error_msg = str(e)
            raise GitHubAPIError(
                f"GitHub API request failed: {error_msg}",
                e.status if hasattr(e, "status") else 500,
                error_msg,
            ) from e
        except Exception as e:
            raise GitHubAPIError(f"Unexpected error during GitHub API request: {e}") from e

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
        url = f"https://api.github.com/repos/{owner}/{repo}/contents"
        print(f"        📡 Repository Contents API: {url}")
        cache_key = self.cache_manager.generate_cache_key(url)

        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result and isinstance(cached_result, list):
            print(f"        ✅ Cache hit: Found {len(cached_result)} items")
            return list(cached_result)

        print("        🔄 Cache miss: Making API request...")

        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
            contents = repository.get_contents("")

            # Convert ContentFile(s) to dictionary format
            result_list: List[Dict[str, Any]] = []
            
            # get_contents returns a single ContentFile if path is a file, or a list if it's a directory
            if isinstance(contents, list):
                for content in contents:
                    content_dict: Dict[str, Any] = {
                        "name": content.name,
                        "path": content.path,
                        "sha": content.sha,
                        "size": content.size,
                        "url": content.url,
                        "html_url": content.html_url,
                        "git_url": content.git_url,
                        "download_url": content.download_url,
                        "type": content.type,
                    }
                    result_list.append(content_dict)
            else:
                # Single file
                content_dict: Dict[str, Any] = {
                    "name": contents.name,
                    "path": contents.path,
                    "sha": contents.sha,
                    "size": contents.size,
                    "url": contents.url,
                    "html_url": contents.html_url,
                    "git_url": contents.git_url,
                    "download_url": contents.download_url,
                    "type": contents.type,
                }
                result_list.append(content_dict)

            print(f"        ✅ Success: Retrieved {len(result_list)} items")

            # Cache results (30 minutes)
            self.cache_manager.set(cache_key, result_list, expire_after=1800)
            print("        💾 Results cached for 30 minutes")

            return result_list

        except GithubException as e:
            error_msg = str(e)
            print(f"        ❌ Error: Status {e.status if hasattr(e, 'status') else 'unknown'}")
            print(f"        📋 Error message: {error_msg[:200]}")
            raise GitHubAPIError(
                f"Failed to get repository contents: {error_msg}",
                e.status if hasattr(e, "status") else 500,
                error_msg,
            ) from e
        except Exception as e:
            raise GitHubAPIError(f"Unexpected error getting repository contents: {e}") from e

    def get_file_content(self, owner: str, repo: str, file_path: str) -> str:
        """
        Get content of specified file

        Args:
            owner: Repository owner
            repo: Repository name
            file_path: File path

        Returns:
            File content string

        Raises:
            GitHubAPIError: File not found or API request failed
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        print(f"            📡 File Content API: {file_path}")
        cache_key = self.cache_manager.generate_cache_key(url)

        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result and isinstance(cached_result, str):
            print(f"            ✅ Cache hit: Found cached file ({len(cached_result)} chars)")
            return str(cached_result)

        print("            🔄 Cache miss: Making API request...")

        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
            file_content = repository.get_contents(file_path)

            # PyGithub returns ContentFile, decode the content
            if hasattr(file_content, "decoded_content"):
                content = file_content.decoded_content
                if isinstance(content, bytes):
                    content_str = content.decode("utf-8")
                else:
                    content_str = str(content)
            else:
                # Fallback: decode base64 content
                import base64
                content_str = base64.b64decode(file_content.content).decode("utf-8")

            print(f"            ✅ Success: Retrieved file ({len(content_str)} chars)")

            # Cache results (30 minutes)
            self.cache_manager.set(cache_key, content_str, expire_after=1800)
            print("            💾 File cached for 30 minutes")

            return content_str

        except GithubException as e:
            error_msg = str(e)
            if hasattr(e, "status") and e.status == 404:
                print(f"            ❌ File not found: {file_path}")
                raise GitHubAPIError(f"File not found: {file_path}") from e
            else:
                print(f"            ❌ Error: Status {e.status if hasattr(e, 'status') else 'unknown'}")
                print(f"            📋 Error message: {error_msg[:200]}")
                raise GitHubAPIError(
                    f"Failed to get file content: {error_msg}",
                    e.status if hasattr(e, "status") else 500,
                    error_msg,
                ) from e
        except Exception as e:
            raise GitHubAPIError(f"Unexpected error getting file content: {e}") from e

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
        url = f"https://api.github.com/repos/{owner}/{repo}"
        cache_key = self.cache_manager.generate_cache_key(url)

        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result and isinstance(cached_result, dict):
            return dict(cached_result)

        try:
            repository = self.github.get_repo(f"{owner}/{repo}")

            # Convert Repository to dictionary format
            repo_info: Dict[str, Any] = {
                "id": repository.id,
                "name": repository.name,
                "full_name": repository.full_name,
                "owner": {
                    "login": repository.owner.login,
                    "id": repository.owner.id,
                    "type": repository.owner.type,
                },
                "html_url": repository.html_url,
                "description": repository.description,
                "stargazers_count": repository.stargazers_count,
                "language": repository.language,
                "default_branch": repository.default_branch,
                "created_at": repository.created_at.isoformat() if repository.created_at else None,
                "updated_at": repository.updated_at.isoformat() if repository.updated_at else None,
                "pushed_at": repository.pushed_at.isoformat() if repository.pushed_at else None,
            }

            # Cache results (1 hour)
            self.cache_manager.set(cache_key, repo_info, expire_after=3600)

            return repo_info

        except GithubException as e:
            error_msg = str(e)
            raise GitHubAPIError(
                f"Failed to get repository info: {error_msg}",
                e.status if hasattr(e, "status") else 500,
                error_msg,
            ) from e
        except Exception as e:
            raise GitHubAPIError(f"Unexpected error getting repository info: {e}") from e

    def get_branch_commit_sha(self, owner: str, repo: str, branch: str = "main") -> str:
        """
        Get latest commit SHA for specified branch

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name (default: main)

        Returns:
            Commit SHA string

        Raises:
            GitHubAPIError: If API request failed or branch does not exist
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
        cache_key = self.cache_manager.generate_cache_key(url)

        # Try to get from cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            if isinstance(cached_result, dict):
                sha = cached_result.get("sha")
                if sha:
                    return str(sha)
                else:
                    raise GitHubAPIError(f"Invalid commit data in cache for {owner}/{repo}/{branch}")
            elif isinstance(cached_result, str):
                return str(cached_result)

        try:
            repository = self.github.get_repo(f"{owner}/{repo}")
            branch_obj = repository.get_branch(branch)
            
            commit_sha = branch_obj.commit.sha
            
            if not commit_sha:
                raise GitHubAPIError(f"No SHA found for branch {branch} in {owner}/{repo}")

            # Cache results (30 minutes)
            commit_data = {"sha": commit_sha}
            self.cache_manager.set(cache_key, commit_data, expire_after=1800)

            return commit_sha

        except GithubException as e:
            error_msg = str(e)
            if hasattr(e, "status") and e.status == 404:
                raise GitHubAPIError(f"Branch '{branch}' does not exist in {owner}/{repo}") from e
            else:
                raise GitHubAPIError(
                    f"Failed to get commit SHA for {owner}/{repo}/{branch}: {error_msg}",
                    e.status if hasattr(e, "status") else 500,
                    error_msg,
                ) from e
        except Exception as e:
            raise GitHubAPIError(f"Unexpected error while getting commit SHA for {owner}/{repo}/{branch}: {e}") from e

    def make_authenticated_request(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Make authenticated API request

        Note: This method is kept for compatibility but PyGithub should be used directly.
        This is a placeholder that raises an error to encourage using PyGithub methods.

        Args:
            url: API URL
            params: Query parameters

        Raises:
            GitHubAPIError: This method should not be used with PyGithub
        """
        raise GitHubAPIError(
            "make_authenticated_request should not be used with PyGithub. Use PyGithub methods directly."
        )

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status

        Returns:
            Rate limit status information
        """
        try:
            # Use rate_limiting property for simple access
            remaining, limit = self.github.rate_limiting
            reset_time = None
            
            # Get detailed rate limit info if needed
            try:
                rate_limit_overview = self.github.get_rate_limit()
                if rate_limit_overview.resources.core.reset:
                    reset_time = rate_limit_overview.resources.core.reset.isoformat()
            except Exception:
                # Fallback: use rate_limiting_resettime if available
                try:
                    reset_timestamp = self.github.rate_limiting_resettime
                    if reset_timestamp:
                        from datetime import datetime
                        reset_time = datetime.fromtimestamp(reset_timestamp).isoformat()
                except Exception:
                    pass
            
            return {
                "remaining": remaining,
                "limit": limit,
                "reset_time": reset_time,
            }
        except Exception as e:
            return {
                "remaining": None,
                "limit": None,
                "reset_time": None,
                "error": str(e),
            }

    def close(self) -> None:
        """Close GitHub client connection"""
        try:
            self.github.close()
        except Exception:
            pass  # Ignore errors during cleanup
