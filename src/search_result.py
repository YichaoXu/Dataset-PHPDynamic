"""
搜索结果数据模型

本模块定义了搜索结果的数据结构，用于存储项目信息和分析结果。
"""

from typing import Any, Dict, List, Optional


class SearchResult:
    """存储单个项目的搜索结果和分析数据"""

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
        初始化搜索结果

        Args:
            owner: 仓库所有者
            repo_name: 仓库名称
            url: 仓库URL
            commit_hash: 当前提交哈希
            star_count: 星标数量
            analysis_result: PHP分析结果
        """
        self.owner = owner
        self.repo_name = repo_name
        self.url = url
        self.commit_hash = commit_hash
        self.star_count = star_count
        self.analysis_result = analysis_result or {}

    @property
    def project_name(self) -> str:
        """获取完整项目名称"""
        return f"{self.owner}/{self.repo_name}"

    @property
    def detection_type(self) -> str:
        """获取检测类型"""
        summary = self.analysis_result.get("analysis_summary", {})
        return str(summary.get("detection_type", "unknown"))

    @property
    def superglobal_usage(self) -> List[str]:
        """获取SuperGlobal使用情况"""
        usage = self.analysis_result.get("superglobal_usage", [])
        return [item.get("pattern", "") for item in usage]

    @property
    def function_usage(self) -> List[str]:
        """获取动态函数使用情况"""
        usage = self.analysis_result.get("dynamic_function_usage", [])
        return [item.get("pattern", "") for item in usage]

    @property
    def dynamic_include_usage(self) -> List[str]:
        """获取动态include使用情况"""
        usage = self.analysis_result.get("dynamic_include_usage", [])
        return [item.get("rule_id", "") for item in usage]

    @property
    def is_qualified(self) -> bool:
        """判断项目是否符合要求"""
        summary = self.analysis_result.get("analysis_summary", {})
        return bool(summary.get("status") == "accepted")

    @property
    def priority(self) -> int:
        """获取项目优先级"""
        summary = self.analysis_result.get("analysis_summary", {})
        return int(summary.get("priority", 0))

    @property
    def rejection_reason(self) -> str:
        """获取拒绝原因"""
        summary = self.analysis_result.get("analysis_summary", {})
        return str(summary.get("reason", ""))

    def to_csv_row(self) -> Dict[str, Any]:
        """
        转换为CSV行数据

        Returns:
            CSV行数据字典
        """
        return {
            "project_name": self.project_name,
            "owner": self.owner,
            "repo_name": self.repo_name,
            "url": self.url,
            "commit_hash": self.commit_hash,
            "star_count": self.star_count,
            "detection_type": self.detection_type,
            "is_qualified": self.is_qualified,
            "priority": self.priority,
            "superglobal_usage": self._format_usage_list(self.superglobal_usage),
            "function_usage": self._format_usage_list(self.function_usage),
            "dynamic_include_usage": self._format_usage_list(
                self.dynamic_include_usage
            ),
            "rejection_reason": self.rejection_reason,
            "analysis_timestamp": self.analysis_result.get("timestamp", ""),
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式

        Returns:
            字典格式的数据
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
        格式化使用情况列表为字符串

        Args:
            usage_list: 使用情况列表

        Returns:
            格式化后的字符串
        """
        if not usage_list:
            return ""
        return "; ".join(usage_list)

    def get_detailed_analysis(self) -> Dict[str, Any]:
        """
        获取详细分析信息

        Returns:
            详细分析信息字典
        """
        return {
            "superglobal_details": self.analysis_result.get("superglobal_usage", []),
            "function_details": self.analysis_result.get("dynamic_function_usage", []),
            "include_details": self.analysis_result.get("dynamic_include_usage", []),
            "analysis_summary": self.analysis_result.get("analysis_summary", {}),
        }

    def update_analysis_result(self, analysis_result: Dict[str, Any]) -> None:
        """
        更新分析结果

        Args:
            analysis_result: 新的分析结果
        """
        self.analysis_result = analysis_result

    def add_metadata(self, key: str, value: Any) -> None:
        """
        添加元数据

        Args:
            key: 键名
            value: 值
        """
        if "metadata" not in self.analysis_result:
            self.analysis_result["metadata"] = {}
        self.analysis_result["metadata"][key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        获取元数据

        Args:
            key: 键名
            default: 默认值

        Returns:
            元数据值
        """
        metadata = self.analysis_result.get("metadata", {})
        return metadata.get(key, default)

    def __str__(self) -> str:
        """字符串表示"""
        status = "QUALIFIED" if self.is_qualified else "REJECTED"
        return f"SearchResult({self.project_name}, {status}, {self.detection_type})"

    def __repr__(self) -> str:
        """详细字符串表示"""
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
    ) -> "SearchResult":
        """
        从GitHub数据创建SearchResult实例

        Args:
            github_data: GitHub API返回的数据
            analysis_result: PHP分析结果

        Returns:
            SearchResult实例
        """
        # 从GitHub数据中提取信息
        full_name = github_data.get("full_name", "")
        owner, repo_name = full_name.split("/", 1) if "/" in full_name else ("", "")

        return cls(
            owner=owner,
            repo_name=repo_name,
            url=github_data.get("html_url", ""),
            commit_hash=github_data.get("default_branch", "main"),
            star_count=github_data.get("stargazers_count", 0),
            analysis_result=analysis_result,
        )

    @classmethod
    def from_search_item(
        cls,
        search_item: Dict[str, Any],
        repo_info: Optional[Dict[str, Any]] = None,
        analysis_result: Optional[Dict[str, Any]] = None,
    ) -> "SearchResult":
        """
        从GitHub搜索项创建SearchResult实例

        Args:
            search_item: GitHub搜索API返回的项
            repo_info: 仓库详细信息
            analysis_result: PHP分析结果

        Returns:
            SearchResult实例
        """
        repository = search_item.get("repository", {})
        full_name = repository.get("full_name", "")
        owner, repo_name = full_name.split("/", 1) if "/" in full_name else ("", "")

        # 使用repo_info中的信息（如果可用）
        if repo_info:
            star_count = repo_info.get("stargazers_count", 0)
            url = repo_info.get("html_url", "")
            commit_hash = repo_info.get("default_branch", "main")
        else:
            star_count = repository.get("stargazers_count", 0)
            url = repository.get("html_url", "")
            commit_hash = repository.get("default_branch", "main")

        return cls(
            owner=owner,
            repo_name=repo_name,
            url=url,
            commit_hash=commit_hash,
            star_count=star_count,
            analysis_result=analysis_result,
        )
