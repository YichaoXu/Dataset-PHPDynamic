"""
GitHub API Client Tests

Tests for GitHubAPIClient class.
"""

import unittest
from unittest.mock import Mock, patch

from php_dynctrlflow.cache_manager import CacheManager
from php_dynctrlflow.exceptions import GitHubAPIError, RateLimitError
from php_dynctrlflow.github_client import GitHubAPIClient
from php_dynctrlflow.rate_limit_handler import RateLimitHandler


class TestGitHubAPIClient(unittest.TestCase):
    """Test GitHubAPIClient class"""

    def setUp(self) -> None:
        """Test setup"""
        self.api_token = "test_token_123"
        self.cache_manager = CacheManager(db_path=":memory:")
        self.rate_limit_handler = RateLimitHandler()
        self.client = GitHubAPIClient(
            self.api_token, self.cache_manager, self.rate_limit_handler
        )

    def tearDown(self) -> None:
        """Test cleanup"""
        self.client.close()

    def test_init(self) -> None:
        """Test initialization"""
        client = GitHubAPIClient(
            "test_token", self.cache_manager, self.rate_limit_handler
        )
        self.assertEqual(client.api_token, "test_token")
        self.assertEqual(client.cache_manager, self.cache_manager)
        self.assertEqual(client.rate_limit_handler, self.rate_limit_handler)
        client.close()

    def test_init_empty_token(self) -> None:
        """Test initialization with empty token raises error"""
        with self.assertRaises(GitHubAPIError):
            GitHubAPIClient("", self.cache_manager, self.rate_limit_handler)

    @patch("php_dynctrlflow.github_client.requests.Session.get")
    def test_search_repositories_optimized(self, mock_get: Mock) -> None:
        """Test search_repositories_optimized method"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "full_name": "owner/repo",
                    "stargazers_count": 100,
                    "html_url": "https://github.com/owner/repo",
                }
            ]
        }
        mock_response.headers = {"X-RateLimit-Remaining": "100"}
        mock_get.return_value = mock_response

        results = self.client.search_repositories_optimized("language:PHP")

        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)

    @patch("php_dynctrlflow.github_client.requests.Session.get")
    def test_get_repository_contents(self, mock_get: Mock) -> None:
        """Test get_repository_contents method"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "file1.php", "type": "file"},
            {"name": "dir1", "type": "dir"},
        ]
        mock_response.headers = {"X-RateLimit-Remaining": "100"}
        mock_get.return_value = mock_response

        contents = self.client.get_repository_contents("owner", "repo")

        self.assertIsInstance(contents, list)
        self.assertEqual(len(contents), 2)

    @patch("php_dynctrlflow.github_client.requests.Session.get")
    def test_get_file_content(self, mock_get: Mock) -> None:
        """Test get_file_content method"""
        import base64

        mock_response = Mock()
        mock_response.status_code = 200
        content = "<?php echo 'test'; ?>"
        encoded_content = base64.b64encode(content.encode()).decode()
        mock_response.json.return_value = {"content": encoded_content}
        mock_response.headers = {"X-RateLimit-Remaining": "100"}
        mock_get.return_value = mock_response

        file_content = self.client.get_file_content("owner", "repo", "test.php")

        self.assertEqual(file_content, content)

    @patch("php_dynctrlflow.github_client.requests.Session.get")
    def test_get_repository_info(self, mock_get: Mock) -> None:
        """Test get_repository_info method"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "full_name": "owner/repo",
            "stargazers_count": 200,
            "default_branch": "main",
        }
        mock_response.headers = {"X-RateLimit-Remaining": "100"}
        mock_get.return_value = mock_response

        info = self.client.get_repository_info("owner", "repo")

        self.assertIsInstance(info, dict)
        self.assertEqual(info["full_name"], "owner/repo")

    @patch("php_dynctrlflow.github_client.requests.Session.get")
    def test_get_branch_commit_sha(self, mock_get: Mock) -> None:
        """Test get_branch_commit_sha method"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sha": "commit123"}
        mock_response.headers = {"X-RateLimit-Remaining": "100"}
        mock_get.return_value = mock_response

        sha = self.client.get_branch_commit_sha("owner", "repo", "main")

        self.assertEqual(sha, "commit123")

    @patch("php_dynctrlflow.github_client.requests.Session.get")
    def test_get_branch_commit_sha_404(self, mock_get: Mock) -> None:
        """Test get_branch_commit_sha with 404 response"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Should return branch name as fallback
        sha = self.client.get_branch_commit_sha("owner", "repo", "main")

        self.assertEqual(sha, "main")

    @patch("php_dynctrlflow.github_client.requests.Session.get")
    def test_api_error_handling(self, mock_get: Mock) -> None:
        """Test API error handling"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with self.assertRaises(GitHubAPIError):
            self.client.get_repository_info("owner", "repo")

    def test_generate_cache_key_consistency(self) -> None:
        """Test that cache key generation is consistent"""
        url = "https://api.github.com/test"
        params = {"param1": "value1"}

        key1 = self.cache_manager.generate_cache_key(url, params)
        key2 = self.cache_manager.generate_cache_key(url, params)

        self.assertEqual(key1, key2)


if __name__ == "__main__":
    unittest.main()

