"""
Search Result Tests

Tests for SearchResult class.
"""

import unittest
from typing import Any, Dict
from unittest.mock import Mock

from php_dynctrlflow.search_result import SearchResult


class TestSearchResult(unittest.TestCase):
    """Test SearchResult class"""

    def setUp(self) -> None:
        """Test setup"""
        self.result = SearchResult(
            owner="test_owner",
            repo_name="test_repo",
            url="https://github.com/test_owner/test_repo",
            commit_hash="abc123",
            star_count=100,
            analysis_result={
                "has_superglobal": True,
                "has_dynamic_functions": True,
                "superglobal_usage": [
                    {"match": "$_GET['key']", "pattern": r"\$_GET\s*\["},
                    {"match": "$_POST['key']", "pattern": r"\$_POST\s*\["},
                ],
                "dynamic_function_usage": [
                    {"match": "call_user_func(...)", "pattern": r"call_user_func\s*\("},
                ],
                "analysis_summary": {
                    "status": "accepted",
                    "detection_type": "primary_functions",
                    "priority": 1,
                    "reason": "Dynamic functions detected",
                },
            },
        )

    def test_init(self) -> None:
        """Test initialization"""
        result = SearchResult(
            owner="owner",
            repo_name="repo",
            url="https://github.com/owner/repo",
            commit_hash="hash123",
            star_count=50,
        )
        self.assertEqual(result.owner, "owner")
        self.assertEqual(result.repo_name, "repo")
        self.assertEqual(result.url, "https://github.com/owner/repo")
        self.assertEqual(result.commit_hash, "hash123")
        self.assertEqual(result.star_count, 50)

    def test_project_name(self) -> None:
        """Test project_name property"""
        self.assertEqual(self.result.project_name, "test_owner/test_repo")

    def test_detection_type(self) -> None:
        """Test detection_type property"""
        self.assertEqual(self.result.detection_type, "primary_functions")

    def test_superglobal_usage(self) -> None:
        """Test superglobal_usage property"""
        usage = self.result.superglobal_usage
        self.assertIsInstance(usage, list)
        self.assertIn("GET", usage)
        self.assertIn("POST", usage)

    def test_function_usage(self) -> None:
        """Test function_usage property"""
        usage = self.result.function_usage
        self.assertIsInstance(usage, list)
        self.assertGreater(len(usage), 0)

    def test_dynamic_include_usage(self) -> None:
        """Test dynamic_include_usage property"""
        usage = self.result.dynamic_include_usage
        self.assertIsInstance(usage, list)

    def test_is_qualified(self) -> None:
        """Test is_qualified property"""
        self.assertTrue(self.result.is_qualified)

    def test_is_qualified_false(self) -> None:
        """Test is_qualified property when not qualified"""
        result = SearchResult(
            owner="owner",
            repo_name="repo",
            url="https://github.com/owner/repo",
            commit_hash="hash",
            star_count=10,
            analysis_result={
                "analysis_summary": {
                    "status": "rejected",
                    "priority": 0,
                    "reason": "No SuperGlobal usage found",
                },
            },
        )
        self.assertFalse(result.is_qualified)

    def test_priority(self) -> None:
        """Test priority property"""
        self.assertEqual(self.result.priority, 1)

    def test_rejection_reason(self) -> None:
        """Test rejection_reason property"""
        result = SearchResult(
            owner="owner",
            repo_name="repo",
            url="https://github.com/owner/repo",
            commit_hash="hash",
            star_count=10,
            analysis_result={
                "analysis_summary": {
                    "status": "rejected",
                    "priority": 0,
                    "reason": "No SuperGlobal usage found",
                },
            },
        )
        self.assertEqual(result.rejection_reason, "No SuperGlobal usage found")

    def test_to_csv_row(self) -> None:
        """Test to_csv_row method"""
        row = self.result.to_csv_row()
        self.assertIsInstance(row, dict)
        self.assertEqual(row["project_name"], "test_owner/test_repo")
        self.assertEqual(row["owner"], "test_owner")
        self.assertEqual(row["repo_name"], "test_repo")
        self.assertEqual(row["url"], "https://github.com/test_owner/test_repo")
        self.assertEqual(row["commit_hash"], "abc123")
        self.assertEqual(row["star_count"], 100)
        self.assertEqual(row["detection_type"], "primary_functions")

    def test_update_analysis_result(self) -> None:
        """Test update_analysis_result method"""
        new_analysis: Dict[str, Any] = {
            "has_superglobal": False,
            "analysis_summary": {"status": "rejected", "priority": 0},
        }
        self.result.update_analysis_result(new_analysis)
        self.assertEqual(self.result.analysis_result, new_analysis)
        self.assertFalse(self.result.is_qualified)

    def test_from_repository_item(self) -> None:
        """Test from_repository_item class method"""
        repo_item = {
            "full_name": "owner/repo",
            "html_url": "https://github.com/owner/repo",
            "stargazers_count": 200,
            "default_branch": "main",
        }

        mock_github_client = Mock()
        mock_github_client.get_branch_commit_sha.return_value = "commit123"

        result = SearchResult.from_repository_item(
            repo_item, github_client=mock_github_client
        )

        self.assertEqual(result.owner, "owner")
        self.assertEqual(result.repo_name, "repo")
        self.assertEqual(result.star_count, 200)
        self.assertEqual(result.commit_hash, "commit123")

    def test_from_repository_item_no_client(self) -> None:
        """Test from_repository_item without github_client"""
        repo_item = {
            "full_name": "owner/repo",
            "html_url": "https://github.com/owner/repo",
            "stargazers_count": 200,
            "default_branch": "main",
        }

        result = SearchResult.from_repository_item(repo_item)

        self.assertEqual(result.owner, "owner")
        self.assertEqual(result.repo_name, "repo")
        self.assertEqual(result.commit_hash, "main")  # Falls back to branch name


if __name__ == "__main__":
    unittest.main()

