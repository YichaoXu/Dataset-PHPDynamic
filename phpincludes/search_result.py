"""
Search Result Data Model

This module defines the data structure for search results, used to store project information and analysis results.
"""

import re
from typing import Any, Dict, List, Optional


class SearchResult:
    """Stores search results and analysis data for a single project"""

    def __init__(
        self,
        owner: str,
        repo_name: str,
        url: str,
        commit_hash: str,
        star_count: int,
        analysis_result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize search result

        Args:
            owner: Repository owner
            repo_name: Repository name
            url: Repository URL
            commit_hash: Current commit hash
            star_count: Star count
            analysis_result: PHP analysis result
        """
        self.owner = owner
        self.repo_name = repo_name
        self.url = url
        self.commit_hash = commit_hash
        self.star_count = star_count
        self.analysis_result = analysis_result or {}

    @property
    def project_name(self) -> str:
        """Get full project name"""
        return f"{self.owner}/{self.repo_name}"

    @property
    def detection_type(self) -> str:
        """Get detection type"""
        summary = self.analysis_result.get("analysis_summary", {})
        return str(summary.get("detection_type", "unknown"))

    @property
    def superglobal_usage(self) -> List[str]:
        """Get SuperGlobal usage (deduplicated SuperGlobal types)"""
        usage = self.analysis_result.get("superglobal_usage", [])
        # Extract actual SuperGlobal variable names (from pattern or match)
        superglobals = set()
        for item in usage:
            match = item.get("match", "")
            pattern = item.get("pattern", "")
            # Extract SuperGlobal type from matched content or pattern
            if match:
                # Extract $_VAR format
                matches = re.findall(
                    r"\$_(GET|POST|REQUEST|COOKIE|SESSION|SERVER|FILES|ENV)",
                    match,
                    re.IGNORECASE,
                )
                superglobals.update(m.upper() for m in matches)
            elif pattern:
                matches = re.findall(
                    r"\$_(GET|POST|REQUEST|COOKIE|SESSION|SERVER|FILES|ENV)",
                    pattern,
                    re.IGNORECASE,
                )
                superglobals.update(m.upper() for m in matches)
        return sorted(superglobals)

    @property
    def function_usage(self) -> List[str]:
        """Get dynamic function usage (deduplicated function names)"""
        usage = self.analysis_result.get("dynamic_function_usage", [])
        # Extract function names
        functions = set()
        for item in usage:
            match = item.get("match", "")
            pattern = item.get("pattern", "")
            rule_id = item.get("rule_id", "")

            # If it is a variable function call detected by Semgrep
            if rule_id == "variable-function-call":
                functions.add("variable_function_call")
            elif match:
                # Extract function names: call_user_func, call_user_func_array, forward_static_call, forward_static_call_array
                func_matches = re.findall(
                    r"(call_user_func(?:_array)?|forward_static_call(?:_array)?)",
                    match,
                    re.IGNORECASE,
                )
                functions.update(m.lower() for m in func_matches)
            elif pattern:
                func_matches = re.findall(
                    r"(call_user_func(?:_array)?|forward_static_call(?:_array)?)",
                    pattern,
                    re.IGNORECASE,
                )
                functions.update(m.lower() for m in func_matches)
        return sorted(functions)

    @property
    def dynamic_include_usage(self) -> List[str]:
        """Get dynamic include usage (deduplicated types)"""
        usage = self.analysis_result.get("dynamic_include_usage", [])
        # Extract include types
        include_types = set()
        for item in usage:
            rule_id = item.get("rule_id", "")
            if rule_id:
                # Extract type from rule_id: dynamic-include-detection -> include
                if "include" in rule_id:
                    include_types.add("include")
                elif "require" in rule_id:
                    include_types.add("require")
            else:
                # Extract from pattern
                pattern = item.get("pattern", "")
                if pattern:
                    matches = re.findall(
                        r"(include|require)(?:_once)?", pattern, re.IGNORECASE
                    )
                    include_types.update(m.lower() for m in matches)
        return sorted(include_types)

    @property
    def is_qualified(self) -> bool:
        """Check if project meets requirements"""
        summary = self.analysis_result.get("analysis_summary", {})
        return bool(summary.get("status") == "accepted")

    @property
    def priority(self) -> int:
        """Get project priority"""
        summary = self.analysis_result.get("analysis_summary", {})
        return int(summary.get("priority", 0))

    @property
    def rejection_reason(self) -> str:
        """Get rejection reason"""
        summary = self.analysis_result.get("analysis_summary", {})
        return str(summary.get("reason", ""))

    def to_csv_row(self) -> Dict[str, Any]:
        """
        Convert to CSV row data

        Returns:
            CSV row data dictionary (only basic information needed for download and analysis)
        """
        return {
            "project_name": self.project_name,
            "owner": self.owner,
            "repo_name": self.repo_name,
            "url": self.url,
            "commit_hash": self.commit_hash,
            "star_count": self.star_count,
            "detection_type": self.detection_type,
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format

        Returns:
            Dictionary format data
        """
        return {
            "project_name": self.project_name,
            "owner": self.owner,
            "repo_name": self.repo_name,
            "url": self.url,
            "commit_hash": self.commit_hash,
            "star_count": self.star_count,
            "analysis_result": self.analysis_result,
            "is_qualified": self.is_qualified,
            "detection_type": self.detection_type,
            "priority": self.priority,
        }

    def _format_usage_list(self, usage_list: List[str]) -> str:
        """
        Format usage list as string (deduplicated and formatted)

        Args:
            usage_list: Usage list (already deduplicated)

        Returns:
            Formatted string
        """
        if not usage_list:
            return ""
        # Use comma separator for better readability
        return ", ".join(usage_list)

    def get_detailed_analysis(self) -> Dict[str, Any]:
        """
        Get detailed analysis information

        Returns:
            Detailed analysis information dictionary
        """
        return {
            "superglobal_details": self.analysis_result.get("superglobal_usage", []),
            "function_details": self.analysis_result.get("dynamic_function_usage", []),
            "include_details": self.analysis_result.get("dynamic_include_usage", []),
            "analysis_summary": self.analysis_result.get("analysis_summary", {}),
        }

    def update_analysis_result(self, analysis_result: Dict[str, Any]) -> None:
        """
        Update analysis result

        Args:
            analysis_result: New analysis result
        """
        self.analysis_result = analysis_result

    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata

        Args:
            key: Key name
            value: Value
        """
        if "metadata" not in self.analysis_result:
            self.analysis_result["metadata"] = {}
        self.analysis_result["metadata"][key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata

        Args:
            key: Key name
            default: Default value

        Returns:
            Metadata value
        """
        metadata = self.analysis_result.get("metadata", {})
        return metadata.get(key, default)

    def __str__(self) -> str:
        """String representation"""
        status = "QUALIFIED" if self.is_qualified else "REJECTED"
        return f"SearchResult({self.project_name}, {status}, {self.detection_type})"

    def __repr__(self) -> str:
        """Detailed string representation"""
        return (
            f"SearchResult(owner='{self.owner}', repo_name='{self.repo_name}', "
            f"url='{self.url}', commit_hash='{self.commit_hash}', "
            f"star_count={self.star_count}, is_qualified={self.is_qualified})"
        )

    @classmethod
    def from_github_data(
        cls,
        github_data: Dict[str, Any],
        analysis_result: Optional[Dict[str, Any]] = None,
        github_client: Optional[Any] = None,
    ) -> "SearchResult":
        """
        Create SearchResult instance from GitHub data

        Args:
            github_data: GitHub API returned data
            analysis_result: PHP analysis result
            github_client: GitHub API client (for getting commit SHA)

        Returns:
            SearchResult instance
        """
        # Extract information from GitHub data
        full_name = github_data.get("full_name", "")
        owner, repo_name = full_name.split("/", 1) if "/" in full_name else ("", "")
        default_branch = github_data.get("default_branch", "main")

        # Get actual commit SHA (if possible)
        commit_hash = default_branch  # Default to use branch name
        if github_client and owner and repo_name:
            try:
                commit_hash = github_client.get_branch_commit_sha(
                    owner, repo_name, default_branch
                )
            except Exception:
                # If get failed, use branch name as fallback
                commit_hash = default_branch

        return cls(
            owner=owner,
            repo_name=repo_name,
            url=github_data.get("html_url", ""),
            commit_hash=commit_hash,
            star_count=github_data.get("stargazers_count", 0),
            analysis_result=analysis_result,
        )

    @classmethod
    def from_repository_item(
        cls,
        repo_item: Dict[str, Any],
        analysis_result: Optional[Dict[str, Any]] = None,
        github_client: Optional[Any] = None,
    ) -> "SearchResult":
        """
        Create SearchResult instance from GitHub repository search result

        Args:
            repo_item: GitHub repository search API returned item
            analysis_result: PHP analysis result
            github_client: GitHub API client (for getting commit SHA)

        Returns:
            SearchResult instance
        """
        # Extract data from repository information
        full_name = repo_item.get("full_name", "")
        owner, repo_name = full_name.split("/", 1) if "/" in full_name else ("", "")
        default_branch = repo_item.get("default_branch", "main")

        # Get actual commit SHA (if possible)
        commit_hash = default_branch  # Default to use branch name
        if github_client and owner and repo_name:
            try:
                commit_hash = github_client.get_branch_commit_sha(
                    owner, repo_name, default_branch
                )
            except Exception:
                # If get failed, use branch name as fallback
                commit_hash = default_branch

        return cls(
            owner=owner,
            repo_name=repo_name,
            url=repo_item.get("html_url", ""),
            commit_hash=commit_hash,
            star_count=repo_item.get("stargazers_count", 0),
            analysis_result=analysis_result,
        )

    @classmethod
    def from_search_item(
        cls,
        search_item: Dict[str, Any],
        repo_info: Optional[Dict[str, Any]] = None,
        analysis_result: Optional[Dict[str, Any]] = None,
        github_client: Optional[Any] = None,
    ) -> "SearchResult":
        """
        Create SearchResult instance from GitHub search item

        Args:
            search_item: GitHub search API returned item
            repo_info: Repository detailed information
            analysis_result: PHP analysis result
            github_client: GitHub API client (for getting commit SHA)

        Returns:
            SearchResult instance
        """
        repository = search_item.get("repository", {})
        full_name = repository.get("full_name", "")
        owner, repo_name = full_name.split("/", 1) if "/" in full_name else ("", "")

        # Use information from repo_info (if available)
        if repo_info:
            star_count = repo_info.get("stargazers_count", 0)
            url = repo_info.get("html_url", "")
            default_branch = repo_info.get("default_branch", "main")
        else:
            star_count = repository.get("stargazers_count", 0)
            url = repository.get("html_url", "")
            default_branch = repository.get("default_branch", "main")

        # Get actual commit SHA (if possible)
        commit_hash = default_branch  # Default to use branch name
        if github_client and owner and repo_name:
            try:
                commit_hash = github_client.get_branch_commit_sha(
                    owner, repo_name, default_branch
                )
            except Exception:
                # If get failed, use branch name as fallback
                commit_hash = default_branch

        return cls(
            owner=owner,
            repo_name=repo_name,
            url=url,
            commit_hash=commit_hash,
            star_count=star_count,
            analysis_result=analysis_result,
        )
