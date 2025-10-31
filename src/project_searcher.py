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
            # 1. Optimize search strategy: group queries to reduce API calls
            print(f"\n{'='*60}")
            print(
                f"🔍 Optimizing Search Strategy: Processing {len(search_queries)} queries..."
            )
            print(f"{'='*60}")
            print("📝 Original Query List:")
            for i, q in enumerate(search_queries, 1):
                print(f"   {i}. {q}")

            optimized_queries = self._create_optimized_queries(search_queries)

            print(f"\n📦 Optimized Query List ({len(optimized_queries)} query groups):")
            for i, q in enumerate(optimized_queries, 1):
                print(f"   {i}. {q}")

            # 2. Execute grouped searches
            print(f"\n{'='*60}")
            print("🚀 Starting GitHub API Search...")
            print(f"{'='*60}")
            all_results: List[SearchResult] = []
            for i, query in enumerate(optimized_queries, 1):
                print(f"\n🔍 Executing Search [{i}/{len(optimized_queries)}]:")
                print(f"   Query: {query}")
                try:
                    search_results = self._search_github_projects_optimized(
                        query, max_projects
                    )
                    print(
                        f"   ✅ Search successful: Found {len(search_results)} results"
                    )
                    all_results.extend(search_results)
                except Exception as e:
                    print(f"   ❌ Search failed: {e}")
                    print("   ⚠️  Continuing with next query...")
                    continue

            print(f"\n{'='*60}")
            print("📊 Search Summary:")
            print(f"   Total results: {len(all_results)}")
            print(f"{'='*60}")

            # 3. Deduplicate results
            print("\n🔄 Deduplicating results...")
            before_dedup = len(all_results)
            unique_results = self._deduplicate_results(all_results)
            after_dedup = len(unique_results)
            print(f"   Before deduplication: {before_dedup} results")
            print(f"   After deduplication: {after_dedup} results")
            print(f"   Duplicates removed: {before_dedup - after_dedup}")

            # 3.5. Limit to max_projects
            if len(unique_results) > max_projects:
                print(
                    f"\n⚠️  Limiting results to max_projects={max_projects} (had {len(unique_results)} unique repositories)"
                )
                unique_results = unique_results[:max_projects]
                print(f"   Limited to: {len(unique_results)} repositories")

            # 4. Apply filtering logic
            print(f"\n{'='*60}")
            print(f"📊 Starting Analysis: {len(unique_results)} projects...")
            print(f"{'='*60}")
            filtered_results = self.apply_filtering_logic(unique_results)

            # 5. 更新统计信息
            self._update_search_stats(filtered_results)

            # 6. 导出CSV（如果需要）
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
        qualified_count = 0
        rejected_count = 0
        error_count = 0

        for i, result in enumerate(results, 1):
            try:
                print(
                    f"\n🔬 Analyzing Project {i}/{len(results)}: {result.project_name}"
                )
                print(f"   URL: {result.url}")

                # Get project file contents
                print("   📁 Fetching project files...")
                file_contents = self._get_project_files(result)

                if not file_contents:
                    print("   ❌ No PHP files found")
                    result.add_metadata("analysis_error", "No PHP files found")
                    rejected_count += 1
                    continue

                print(f"   ✅ Found {len(file_contents)} PHP file(s):")
                for file_path in list(file_contents.keys())[:5]:  # Show first 5 files
                    print(f"      - {file_path}")
                if len(file_contents) > 5:
                    print(f"      ... and {len(file_contents) - 5} more file(s)")

                # Analyze project
                print("   🔍 Starting code analysis...")
                analysis_results = self.php_analyzer.analyze_multiple_files(
                    file_contents
                )

                # Combine analysis results
                combined_analysis = self._combine_analysis_results(analysis_results)

                # Display analysis summary
                print("   📊 Analysis Summary:")
                print(
                    f"      SuperGlobal usage: {combined_analysis.get('has_superglobal', False)}"
                )
                print(
                    f"      Dynamic functions: {combined_analysis.get('has_dynamic_functions', False)}"
                )
                print(
                    f"      Dynamic includes: {combined_analysis.get('has_dynamic_includes', False)}"
                )

                # Update result
                result.update_analysis_result(combined_analysis)

                # Apply filtering rules
                print("   🎯 Applying filtering rules...")
                if self._meets_criteria(result):
                    filtered_results.append(result)
                    qualified_count += 1
                    print("   ✅ ✅ ✅ QUALIFIED!")
                    print(f"      Detection type: {result.detection_type}")
                    print(f"      Priority: {result.priority}")
                    if result.superglobal_usage:
                        print(
                            f"      SuperGlobal usage count: {len(result.superglobal_usage)}"
                        )
                    if result.function_usage:
                        print(
                            f"      Dynamic function usage count: {len(result.function_usage)}"
                        )
                    if result.dynamic_include_usage:
                        print(
                            f"      Dynamic include usage count: {len(result.dynamic_include_usage)}"
                        )
                else:
                    rejected_count += 1
                    print("   ❌ NOT QUALIFIED")
                    print(f"      Rejection reason: {result.rejection_reason}")

                # Add delay to avoid API limits
                time.sleep(0.5)

            except Exception as e:
                error_count += 1
                print(f"   ⚠️ ⚠️ ⚠️ Analysis failed: {e}")
                import traceback

                print("   📋 Error details:")
                print(f"      {traceback.format_exc()}")
                result.add_metadata("analysis_error", str(e))
                self.search_stats["error_projects"] += 1

        print(f"\n{'='*60}")
        print("📊 Filtering Summary:")
        print(f"   Total projects: {len(results)}")
        print(f"   Qualified: {qualified_count}")
        print(f"   Rejected: {rejected_count}")
        print(f"   Analysis errors: {error_count}")
        print(f"{'='*60}")

        return filtered_results

    def _create_optimized_queries(self, search_queries: List[str]) -> List[str]:
        """
        创建优化的搜索查询列表
        GitHub Code Search API对OR查询有格式要求，我们将相关查询分组

        Args:
            search_queries: 原始搜索查询列表

        Returns:
            优化后的搜索查询列表
        """
        # 清理查询，移除language:PHP限定符
        cleaned_queries = []
        for query in search_queries:
            clean_query = (
                query.replace(" language:PHP", "").replace(" language:php", "").strip()
            )
            # GitHub Code Search API对查询格式要求：
            # - 简单字符串：直接使用
            # - 包含特殊字符的：保持原样，API会自动处理
            # 不需要手动添加引号，这可能导致422错误
            cleaned_queries.append(clean_query)

        # 分组：函数相关查询和include相关查询
        function_queries = []
        include_queries = []

        for query in cleaned_queries:
            # 判断查询类型
            query_lower = query.lower()
            if any(
                func in query_lower
                for func in ["call_user_func", "forward_static_call"]
            ):
                function_queries.append(query)
            elif any(inc in query_lower for inc in ["include", "require"]):
                include_queries.append(query)

        # 构建优化后的查询列表
        optimized_queries = []

        # 函数查询：每组最多2个用OR连接（避免查询过长）
        if function_queries:
            for i in range(0, len(function_queries), 2):
                group = function_queries[i : i + 2]
                if len(group) == 1:
                    optimized_queries.append(group[0])
                else:
                    # GitHub API要求OR查询格式：query1 OR query2
                    optimized_queries.append(" OR ".join(group))

        # Include查询：每组最多2个用OR连接（避免查询过长）
        if include_queries:
            for i in range(0, len(include_queries), 2):
                group = include_queries[i : i + 2]
                if len(group) == 1:
                    optimized_queries.append(group[0])
                else:
                    optimized_queries.append(" OR ".join(group))

        # 如果没有分组，使用原始清理后的查询
        if not optimized_queries:
            optimized_queries = cleaned_queries

        # 为每个查询添加language:PHP
        return [f"{query} language:PHP" for query in optimized_queries]

    def _search_github_projects_optimized(
        self, query: str, max_projects: int
    ) -> List[SearchResult]:
        """
        优化的GitHub项目搜索 - 修复版本：先找仓库，再搜索内部代码

        Args:
            query: 搜索查询
            max_projects: 最大项目数量

        Returns:
            搜索结果列表

        Raises:
            GitHubAPIError: GitHub API请求失败
        """
        try:
            # 1. Use Code Search API to find repositories containing specific code
            print("  🔍 Searching repositories with Code Search API...")
            # Note: max_projects is the limit for total repositories, not per-page results
            # We use per_page=100 (GitHub's max) to get more results, then limit later
            code_search_results = self.github_client.search_code_content(
                query, language="PHP", per_page=100  # Use max per_page to get more results
            )

            print(f"  📥 Received {len(code_search_results)} code search results")

            results: List[SearchResult] = []
            # Collect matched file paths for each repository: repo_full_name -> [file_paths]
            repo_file_paths: Dict[str, List[str]] = {}
            processed_repos = set()  # Avoid processing duplicate repositories
            skipped_repos = 0
            error_repos = 0

            print("  🔄 Processing search results...")
            for idx, item in enumerate(code_search_results, 1):
                try:
                    # Extract repository information
                    repository = item.get("repository", {})
                    full_name = repository.get("full_name", "")
                    file_path = item.get("path", "")
                    html_url = item.get("html_url", "")
                    name = repository.get("name", "")
                    owner = repository.get("owner", {}).get("login", "unknown")

                    if not full_name:
                        print(
                            f"     ⚠️  [{idx}] Skipping invalid repository (no full_name)"
                        )
                        skipped_repos += 1
                        continue

                    # Collect file paths (even if repository is duplicate, collect all matched files)
                    if full_name not in repo_file_paths:
                        repo_file_paths[full_name] = []
                    if file_path and file_path not in repo_file_paths[full_name]:
                        repo_file_paths[full_name].append(file_path)

                    # Create SearchResult only when first encountering this repository
                    if full_name not in processed_repos:
                        processed_repos.add(full_name)

                        # Create SearchResult
                        result = SearchResult.from_search_item(item)
                        # Store file path list in metadata
                        result.add_metadata(
                            "matched_file_paths", repo_file_paths[full_name]
                        )
                        results.append(result)

                        print(f"     ✅ [{idx}] Repository: {full_name}")
                        print(f"         Owner: {owner}, Repository: {name}")
                        print(f"         URL: {html_url}")
                        print(
                            f"         Matched files: {len(repo_file_paths[full_name])}"
                        )
                    else:
                        # Update file path list for existing SearchResult
                        for result in results:
                            if result.project_name == full_name:
                                result.add_metadata(
                                    "matched_file_paths", repo_file_paths[full_name]
                                )
                                break

                    print(
                        f"         📄 File [{len(repo_file_paths[full_name])}]: {file_path}"
                    )

                except Exception as e:
                    print(f"     ❌ [{idx}] Failed to process repository: {e}")
                    error_repos += 1
                    continue

            print("  📊 Processing Summary:")
            print(f"     Total results: {len(code_search_results)}")
            print(f"     Successfully processed: {len(results)}")
            print(f"     Skipped duplicates: {skipped_repos}")
            print(f"     Processing errors: {error_repos}")
            print(f"     Unique repositories: {len(processed_repos)}")

            return results

        except Exception as e:
            print(f"  ❌ GitHub search failed: {e}")
            import traceback

            print("  📋 Error details:")
            print(f"     {traceback.format_exc()}")
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
        优化：直接使用Code Search API返回的文件路径，而不是重新扫描仓库根目录

        Args:
            result: 搜索结果

        Returns:
            文件路径到内容的映射

        Raises:
            GitHubAPIError: API请求失败
        """
        try:
            # 1. Try to get file paths from Code Search API results in metadata
            matched_file_paths = result.get_metadata("matched_file_paths")
            if matched_file_paths and isinstance(matched_file_paths, list):
                print(
                    f"      📡 Using Code Search API file paths: {result.owner}/{result.repo_name}"
                )
                print(f"      ✅ Found {len(matched_file_paths)} matched file(s)")

                file_contents: Dict[str, str] = {}
                success_count = 0
                error_count = 0

                # Limit file count to avoid too many requests
                max_files = min(len(matched_file_paths), 10)

                for idx, file_path in enumerate(matched_file_paths[:max_files], 1):
                    try:
                        print(
                            f"         📄 [{idx}/{max_files}] Fetching file: {file_path}"
                        )

                        content = self.github_client.get_file_content(
                            result.owner, result.repo_name, file_path
                        )
                        file_contents[file_path] = content

                        file_size = len(content)
                        print(f"            ✅ File size: {file_size} characters")
                        success_count += 1

                    except Exception as e:
                        error_count += 1
                        print(f"            ❌ Failed to fetch file: {e}")
                        continue

                print("      📊 File Fetching Summary:")
                print(f"         Matched files: {len(matched_file_paths)}")
                print(f"         Processed files: {max_files}")
                print(f"         Successfully fetched: {success_count}")
                print(f"         Fetch errors: {error_count}")

                return file_contents

            # 2. Fallback: scan repository root directory if no Code Search file paths (backward compatibility)
            print(
                f"      📡 Fallback: Scanning repository root: {result.owner}/{result.repo_name}"
            )
            contents = self.github_client.get_repository_contents(
                result.owner, result.repo_name
            )
            print(f"      ✅ Retrieved {len(contents)} file/directory item(s)")

            file_contents: Dict[str, str] = {}
            php_file_count = 0
            skipped_files = 0
            error_files = 0

            for item in contents:
                if item.get("type") == "file" and item.get("name", "").endswith(".php"):
                    php_file_count += 1
                    try:
                        file_path = item.get("path", "")
                        print(
                            f"         📄 [{php_file_count}] Fetching file: {file_path}"
                        )

                        content = self.github_client.get_file_content(
                            result.owner, result.repo_name, file_path
                        )
                        file_contents[file_path] = content

                        file_size = len(content)
                        print(f"            ✅ File size: {file_size} characters")

                        # Limit file count to avoid too many requests
                        if len(file_contents) >= 10:
                            print(
                                "         ⚠️  Reached max file limit (10), stopping..."
                            )
                            break

                    except Exception as e:
                        error_files += 1
                        print(
                            f"         ❌ Failed to fetch file {item.get('name', '')}: {e}"
                        )
                        continue
                else:
                    skipped_files += 1

            print("      📊 File Fetching Summary:")
            print(f"         Total items: {len(contents)}")
            print(f"         PHP files: {php_file_count}")
            print(f"         Successfully fetched: {len(file_contents)}")
            print(f"         Skipped non-PHP: {skipped_files}")
            print(f"         Fetch errors: {error_files}")

            return file_contents

        except Exception as e:
            print(f"      ❌ Failed to get repository files: {e}")
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
            # Export basic results
            csv_path = self.csv_exporter.export_results(
                results, include_unqualified=include_unqualified
            )
            print(f"📄 Results exported to: {csv_path}")

            # Export summary
            summary_path = self.csv_exporter.export_summary(results)
            print(f"📊 Summary exported to: {summary_path}")

            # Export detailed results
            detailed_path = self.csv_exporter.export_detailed_results(results)
            print(f"📋 Detailed results exported to: {detailed_path}")

        except Exception as e:
            print(f"⚠️  Export failed: {e}")

    def _print_search_summary(self) -> None:
        """打印搜索摘要"""
        stats = self.search_stats
        duration = (
            stats["end_time"] - stats["start_time"]
            if stats["start_time"] and stats["end_time"]
            else None
        )

        print("\n" + "=" * 50)
        print("\n🔍 Search Summary")
        print("=" * 50)
        print(f"Total projects searched: {stats['total_searched']}")
        print(f"Qualified projects: {stats['qualified_projects']}")
        print(f"Rejected projects: {stats['rejected_projects']}")
        print(f"Analysis errors: {stats['error_projects']}")
        if duration:
            print(f"Total duration: {duration.total_seconds():.2f} seconds")
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
