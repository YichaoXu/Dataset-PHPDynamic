"""
项目搜索器

本模块实现了核心的项目搜索和筛选逻辑，协调所有组件完成完整的工作流程。
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .cache_manager import CacheManager
from .csv_exporter import CSVExporter
from .exceptions import GitHubAPIError
from .github_client import GitHubAPIClient
from .php_analyzer import PHPAnalyzer
from .rate_limit_handler import RateLimitHandler
from .search_result import SearchResult
from .semgrep_analyzer import SemgrepAnalyzer


class ProjectSearcher:
    """项目搜索器，协调所有组件完成项目搜索和筛选"""

    def __init__(
        self,
        github_token: str,
        cache_manager: Optional[CacheManager] = None,
        rate_limit_handler: Optional[RateLimitHandler] = None,
        semgrep_analyzer: Optional[SemgrepAnalyzer] = None,
        php_analyzer: Optional[PHPAnalyzer] = None,
        csv_exporter: Optional[CSVExporter] = None,
    ) -> None:
        """
        初始化项目搜索器

        Args:
            github_token: GitHub API访问令牌
            cache_manager: 缓存管理器
            rate_limit_handler: 速率限制处理器
            semgrep_analyzer: Semgrep分析器
            php_analyzer: PHP分析器
            csv_exporter: CSV导出器
        """
        # 初始化组件
        self.cache_manager = cache_manager or CacheManager()
        self.rate_limit_handler = rate_limit_handler or RateLimitHandler()
        self.semgrep_analyzer = semgrep_analyzer or SemgrepAnalyzer()
        self.php_analyzer = php_analyzer or PHPAnalyzer(self.semgrep_analyzer)
        self.csv_exporter = csv_exporter or CSVExporter()

        # 初始化GitHub客户端
        self.github_client = GitHubAPIClient(
            github_token, self.cache_manager, self.rate_limit_handler
        )

        # 搜索统计
        self.search_stats = {
            "total_searched": 0,
            "qualified_projects": 0,
            "rejected_projects": 0,
            "error_projects": 0,
            "start_time": None,
            "end_time": None,
        }

    def search_projects(
        self,
        search_queries: List[str],
        max_projects: int = 100,
        export_csv: bool = True,
        include_unqualified: bool = False,
    ) -> List[SearchResult]:
        """
        搜索并筛选PHP项目

        Args:
            search_queries: 搜索查询列表
            max_projects: 最大项目数量
            export_csv: 是否导出CSV文件
            include_unqualified: 是否包含不符合条件的项目

        Returns:
            搜索结果列表

        Raises:
            GitHubAPIError: GitHub API请求失败
            AnalysisError: 项目分析失败
        """
        self.search_stats["start_time"] = datetime.now()

        try:
            all_results: List[SearchResult] = []

            # 1. 搜索项目
            for query in search_queries:
                print(f"🔍 搜索查询: {query}")
                search_results = self._search_github_projects(query, max_projects)
                all_results.extend(search_results)

            # 2. 去重
            unique_results = self._deduplicate_results(all_results)

            # 3. 应用筛选逻辑
            print(f"📊 开始分析 {len(unique_results)} 个项目...")
            filtered_results = self.apply_filtering_logic(unique_results)

            # 4. 更新统计信息
            self._update_search_stats(filtered_results)

            # 5. 导出CSV（如果需要）
            if export_csv:
                self._export_results(filtered_results, include_unqualified)

            self.search_stats["end_time"] = datetime.now()
            self._print_search_summary()

            return filtered_results

        except Exception as e:
            self.search_stats["end_time"] = datetime.now()
            raise GitHubAPIError(f"Project search failed: {e}") from e

    def apply_filtering_logic(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        应用严格的筛选逻辑

        Args:
            results: 原始搜索结果列表

        Returns:
            筛选后的结果列表

        Raises:
            AnalysisError: 项目分析失败
        """
        filtered_results: List[SearchResult] = []

        for i, result in enumerate(results, 1):
            try:
                print(f"🔬 分析项目 {i}/{len(results)}: {result.project_name}")

                # 获取项目文件内容
                file_contents = self._get_project_files(result)

                if not file_contents:
                    print("   ❌ 未找到PHP文件")
                    result.add_metadata("analysis_error", "No PHP files found")
                    continue

                # 分析项目
                analysis_results = self.php_analyzer.analyze_multiple_files(
                    file_contents
                )

                # 合并分析结果
                combined_analysis = self._combine_analysis_results(analysis_results)

                # 更新结果
                result.update_analysis_result(combined_analysis)

                # 应用筛选规则
                if self._meets_criteria(result):
                    filtered_results.append(result)
                    print(f"   ✅ 符合条件: {result.detection_type}")
                else:
                    print(f"   ❌ 不符合条件: {result.rejection_reason}")

                # 添加延迟避免API限制
                time.sleep(0.5)

            except Exception as e:
                print(f"   ⚠️ 分析失败: {e}")
                result.add_metadata("analysis_error", str(e))
                self.search_stats["error_projects"] += 1

        return filtered_results

    def _search_github_projects(
        self, query: str, max_projects: int
    ) -> List[SearchResult]:
        """
        搜索GitHub项目

        Args:
            query: 搜索查询
            max_projects: 最大项目数量

        Returns:
            搜索结果列表

        Raises:
            GitHubAPIError: GitHub API请求失败
        """
        try:
            # 搜索代码
            search_results = self.github_client.search_code_content(
                query, language="PHP", per_page=min(max_projects, 100)
            )

            results: List[SearchResult] = []

            for item in search_results:
                try:
                    # 获取仓库信息
                    repo_info = self._get_repository_info(item)

                    # 创建SearchResult
                    result = SearchResult.from_search_item(item, repo_info)
                    results.append(result)

                except Exception as e:
                    print(f"   ⚠️ 获取仓库信息失败: {e}")
                    continue

            return results

        except Exception as e:
            raise GitHubAPIError(f"GitHub search failed: {e}") from e

    def _get_repository_info(self, search_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取仓库详细信息

        Args:
            search_item: 搜索项

        Returns:
            仓库信息

        Raises:
            GitHubAPIError: API请求失败
        """
        repository = search_item.get("repository", {})
        owner = repository.get("owner", {}).get("login", "")
        repo_name = repository.get("name", "")

        if not owner or not repo_name:
            raise GitHubAPIError("Invalid repository information")

        return self.github_client.get_repository_info(owner, repo_name)

    def _get_project_files(self, result: SearchResult) -> Dict[str, str]:
        """
        获取项目的PHP文件内容

        Args:
            result: 搜索结果

        Returns:
            文件路径到内容的映射

        Raises:
            GitHubAPIError: API请求失败
        """
        try:
            # 获取仓库文件列表
            contents = self.github_client.get_repository_contents(
                result.owner, result.repo_name
            )

            file_contents: Dict[str, str] = {}

            for item in contents:
                if item.get("type") == "file" and item.get("name", "").endswith(".php"):
                    try:
                        file_path = item.get("path", "")
                        content = self.github_client.get_file_content(
                            result.owner, result.repo_name, file_path
                        )
                        file_contents[file_path] = content

                        # 限制文件数量避免过多请求
                        if len(file_contents) >= 10:
                            break

                    except Exception as e:
                        print(f"   ⚠️ 获取文件失败 {item.get('name', '')}: {e}")
                        continue

            return file_contents

        except Exception as e:
            raise GitHubAPIError(f"Failed to get project files: {e}") from e

    def _combine_analysis_results(
        self, analysis_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        合并多个文件的分析结果

        Args:
            analysis_results: 文件分析结果

        Returns:
            合并后的分析结果
        """
        combined = {
            "has_superglobal": False,
            "has_dynamic_functions": False,
            "has_dynamic_includes": False,
            "superglobal_usage": [],
            "dynamic_function_usage": [],
            "dynamic_include_usage": [],
            "analysis_summary": {},
            "timestamp": datetime.now().isoformat(),
        }

        for _file_path, result in analysis_results.items():
            # 合并使用情况
            combined["superglobal_usage"].extend(result.get("superglobal_usage", []))
            combined["dynamic_function_usage"].extend(
                result.get("dynamic_function_usage", [])
            )
            combined["dynamic_include_usage"].extend(
                result.get("dynamic_include_usage", [])
            )

            # 合并标志
            combined["has_superglobal"] = combined["has_superglobal"] or result.get(
                "has_superglobal", False
            )
            combined["has_dynamic_functions"] = combined[
                "has_dynamic_functions"
            ] or result.get("has_dynamic_functions", False)
            combined["has_dynamic_includes"] = combined[
                "has_dynamic_includes"
            ] or result.get("has_dynamic_includes", False)

        # 生成分析摘要
        combined["analysis_summary"] = self._generate_combined_summary(combined)

        return combined

    def _generate_combined_summary(self, combined: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成合并后的分析摘要

        Args:
            combined: 合并的分析结果

        Returns:
            分析摘要
        """
        # 1. 检查SuperGlobal使用
        if not combined["has_superglobal"]:
            return {
                "status": "rejected",
                "reason": "No SuperGlobal usage found",
                "priority": 0,
            }

        # 2. 检查主要动态函数
        if combined["has_dynamic_functions"]:
            return {
                "status": "accepted",
                "reason": "Dynamic functions detected",
                "priority": 1,
                "detection_type": "primary_functions",
            }

        # 3. 检查fallback动态includes
        if combined["has_dynamic_includes"]:
            return {
                "status": "accepted",
                "reason": "Dynamic includes detected",
                "priority": 2,
                "detection_type": "fallback_includes",
            }

        # 4. 都不符合
        return {
            "status": "rejected",
            "reason": "No dynamic functions or includes found",
            "priority": 0,
        }

    def _meets_criteria(self, result: SearchResult) -> bool:
        """
        检查项目是否符合筛选标准

        Args:
            result: 搜索结果

        Returns:
            是否符合标准
        """
        return result.is_qualified

    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        去重搜索结果

        Args:
            results: 原始结果列表

        Returns:
            去重后的结果列表
        """
        seen = set()
        unique_results: List[SearchResult] = []

        for result in results:
            project_key = f"{result.owner}/{result.repo_name}"
            if project_key not in seen:
                seen.add(project_key)
                unique_results.append(result)

        return unique_results

    def _update_search_stats(self, results: List[SearchResult]) -> None:
        """
        更新搜索统计信息

        Args:
            results: 搜索结果列表
        """
        self.search_stats["total_searched"] = len(results)
        self.search_stats["qualified_projects"] = sum(
            1 for r in results if r.is_qualified
        )
        self.search_stats["rejected_projects"] = (
            self.search_stats["total_searched"]
            - self.search_stats["qualified_projects"]
        )

    def _export_results(
        self, results: List[SearchResult], include_unqualified: bool
    ) -> None:
        """
        导出结果到CSV

        Args:
            results: 搜索结果列表
            include_unqualified: 是否包含不符合条件的项目
        """
        try:
            # 导出基本结果
            csv_path = self.csv_exporter.export_results(
                results, include_unqualified=include_unqualified
            )
            print(f"📄 结果已导出到: {csv_path}")

            # 导出摘要
            summary_path = self.csv_exporter.export_summary(results)
            print(f"📊 摘要已导出到: {summary_path}")

            # 导出详细结果
            detailed_path = self.csv_exporter.export_detailed_results(results)
            print(f"📋 详细结果已导出到: {detailed_path}")

        except Exception as e:
            print(f"⚠️ 导出失败: {e}")

    def _print_search_summary(self) -> None:
        """打印搜索摘要"""
        stats = self.search_stats
        duration = (
            stats["end_time"] - stats["start_time"]
            if stats["start_time"] and stats["end_time"]
            else None
        )

        print("\n" + "=" * 50)
        print("🔍 搜索摘要")
        print("=" * 50)
        print(f"总搜索项目数: {stats['total_searched']}")
        print(f"符合条件项目: {stats['qualified_projects']}")
        print(f"不符合条件项目: {stats['rejected_projects']}")
        print(f"分析错误项目: {stats['error_projects']}")
        if duration:
            print(f"总耗时: {duration.total_seconds():.2f} 秒")
        print("=" * 50)

    def get_search_statistics(self) -> Dict[str, Any]:
        """
        获取搜索统计信息

        Returns:
            统计信息字典
        """
        return self.search_stats.copy()

    def close(self) -> None:
        """关闭所有资源"""
        self.github_client.close()
        self.cache_manager.cleanup_expired()
