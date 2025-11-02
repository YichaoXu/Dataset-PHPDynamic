"""
Project Searcher

This module implements core project search and filtering logic,
coordinating all components to complete the full workflow.
"""

import time
from datetime import datetime, timedelta
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
    """Project searcher that coordinates all components to complete project search and filtering"""

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
        Initialize project searcher

        Args:
            github_token: GitHub API access token
            cache_manager: Cache manager
            rate_limit_handler: Rate limit handler
            semgrep_analyzer: Semgrep analyzer
            php_analyzer: PHP analyzer
            csv_exporter: CSV exporter
        """
        # Initialize components
        self.cache_manager = cache_manager or CacheManager()
        self.rate_limit_handler = rate_limit_handler or RateLimitHandler()
        self.semgrep_analyzer = semgrep_analyzer or SemgrepAnalyzer()
        self.php_analyzer = php_analyzer or PHPAnalyzer(self.semgrep_analyzer)
        self.csv_exporter = csv_exporter or CSVExporter()

        # Initialize GitHub client
        self.github_client = GitHubAPIClient(
            github_token, self.cache_manager, self.rate_limit_handler
        )

        # Search statistics
        self.search_stats: Dict[str, Any] = {
            "total_searched": 0,
            "qualified_projects": 0,
            "rejected_projects": 0,
            "error_projects": 0,
            "start_time": None,
            "end_time": None,
        }

    def search_projects(
        self,
        max_projects: Optional[int] = None,
        export_csv: bool = True,
        include_unqualified: bool = False,
        batch_size: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        Search and filter PHP projects using streaming batch processing

        Uses streaming batch processing to avoid keeping all projects in memory.
        Processes repositories in batches, analyzes each batch, and releases memory
        after processing each batch.

        Workflow:
        1. Use Repository Search API to get specified number of top stars PHP projects
        2. Split projects into batches (default: from config, typically 100 per batch)
        3. For each batch:
           a. Create SearchResult objects
           b. Fetch file contents
           c. Analyze and filter
           d. Release file content memory
           e. Accumulate qualified results
        4. Export CSV and return qualified results

        Args:
            max_projects: Maximum number of projects to search and analyze (default from config)
            export_csv: Whether to export CSV file
            include_unqualified: Whether to include unqualified projects
            batch_size: Number of repositories to process per batch (default from config)

        Returns:
            List of qualified search results

        Raises:
            GitHubAPIError: GitHub API request failed
            AnalysisError: Project analysis failed
        """
        from .settings import Settings

        self.search_stats["start_time"] = datetime.now()

        # Get default values from config
        if max_projects is None:
            max_projects = Settings.get_max_projects()
        if batch_size is None:
            batch_size = Settings.get_batch_size()

        try:
            # 1. Use Repository Search API to get top stars PHP projects
            print(f"\n{'='*60}")
            print("🚀 Starting PHP Project Search (Streaming Batch Processing)...")
            print(f"{'='*60}")
            print(f"📊 Configuration:")
            print(f"   Max projects: {max_projects} top stars PHP projects")
            print(f"   Batch size: {batch_size} repositories per batch")
            print(f"{'='*60}")

            print(f"\n🔍 Searching top {max_projects} stars PHP repositories...")
            repository_results = self._search_top_stars_php_projects(max_projects)
            print(f"✅ Found {len(repository_results)} PHP repositories")

            # Limit to max_projects
            if len(repository_results) > max_projects:
                repository_results = repository_results[:max_projects]

            # 2. Process in batches
            print(f"\n{'='*60}")
            print(f"📊 Starting Batch Processing: {len(repository_results)} repositories in batches of {batch_size}")
            print(f"{'='*60}")

            # Calculate total batches
            total_batches = (len(repository_results) + batch_size - 1) // batch_size
            print(f"   Total batches: {total_batches}")

            # Accumulate qualified results
            all_qualified_results: List[SearchResult] = []

            # Process each batch
            for batch_num in range(1, total_batches + 1):
                start_idx = (batch_num - 1) * batch_size
                end_idx = min(start_idx + batch_size, len(repository_results))
                batch_repos = repository_results[start_idx:end_idx]

                print(f"\n{'='*60}")
                print(f"📦 Processing Batch {batch_num}/{total_batches}")
                print(f"   Repositories: {start_idx + 1}-{end_idx} of {len(repository_results)}")
                print(f"{'='*60}")

                # Process this batch
                batch_results = self._process_batch(batch_repos, batch_num, total_batches)

                # Accumulate qualified results
                all_qualified_results.extend(batch_results)

                # Print batch summary
                print(f"\n✅ Batch {batch_num}/{total_batches} completed:")
                print(f"   Qualified projects in this batch: {len(batch_results)}")
                print(f"   Total qualified so far: {len(all_qualified_results)}")

            # 3. Update statistics
            self._update_search_stats(all_qualified_results)

            # 4. Export CSV (if needed)
            if export_csv:
                self._export_results(all_qualified_results, include_unqualified)

            self.search_stats["end_time"] = datetime.now()
            self._print_search_summary()

            return all_qualified_results

        except Exception as e:
            self.search_stats["end_time"] = datetime.now()
            raise GitHubAPIError(f"Project search failed: {e}") from e

    def _search_top_stars_php_projects(
        self, count: int
    ) -> List[Dict[str, Any]]:
        """
        Search for top stars PHP projects

        Args:
            count: Number of projects to get

        Returns:
            repositorySearch result list

        Raises:
            GitHubAPIError: GitHub API request failed
        """
        try:
            # Use Repository Search API to search for PHP projects, sorted by stars
            query = "language:PHP"
            print(f"  📡 GitHub Repository Search API:")
            print(f"     Query: {query}")
            print(f"     Sort: stars (descending)")
            print(f"     Count: {count}")

            # Since GitHub API returns at most 100 results per page, need to paginate
            all_repos: List[Dict[str, Any]] = []
            per_page = min(count, 100)  # GitHub maximum limit is 100 per page

            # Calculate required number of pages
            pages_needed = (count + per_page - 1) // per_page

            for page in range(1, pages_needed + 1):
                if len(all_repos) >= count:
                    break

                remaining = count - len(all_repos)
                current_per_page = min(remaining, per_page)

                print(f"  📄 Fetching page {page}/{pages_needed} (requesting {current_per_page} items)...")

                repos = self.github_client.search_repositories_optimized(
                    query=query,
                    per_page=current_per_page,
                    page=page,
                )
                all_repos.extend(repos)

                print(f"  ✅ Page {page}: Retrieved {len(repos)} repositories")
                print(f"  📊 Total so far: {len(all_repos)}/{count}")

                # If number of results returned is less than requested, no more results available
                if len(repos) < current_per_page:
                    print(f"  ⚠️  No more results available")
                    break

            # Limit to requested number
            if len(all_repos) > count:
                all_repos = all_repos[:count]

            print(f"\n  ✅ Successfully retrieved {len(all_repos)} PHP repositories")
            return all_repos

        except Exception as e:
            print(f"  ❌ GitHub search failed: {e}")
            import traceback

            print("  📋 Error details:")
            print(f"     {traceback.format_exc()}")
            raise GitHubAPIError(f"GitHub search failed: {e}") from e

    def _process_batch(
        self,
        repository_items: List[Dict[str, Any]],
        batch_num: int,
        total_batches: int,
    ) -> List[SearchResult]:
        """
        Process a single batch of repository items

        For each repository in the batch:
        1. Create SearchResult object
        2. Get file contents
        3. Analyze files
        4. Apply filtering logic
        5. Release file content memory

        Args:
            repository_items: List of repository metadata items
            batch_num: Current batch number
            total_batches: Total number of batches

        Returns:
            List of qualified SearchResult objects from this batch

        Raises:
            GitHubAPIError: GitHub API request failed
            AnalysisError: Project analysis failed
        """
        print(f"\n🔄 Processing batch {batch_num}/{total_batches}: {len(repository_items)} repositories")

        # 1. Create SearchResult objects
        batch_results: List[SearchResult] = []
        for i, repo_item in enumerate(repository_items, 1):
            try:
                result = SearchResult.from_repository_item(
                    repo_item, github_client=self.github_client
                )
                batch_results.append(result)
                print(f"   [{i}/{len(repository_items)}] {result.project_name}")
            except Exception as e:
                print(f"   ⚠️  Failed to convert repository {i}: {e}")
                continue

        # 2. Apply filtering logic (this handles file content fetching, analysis, and filtering)
        qualified_results = self.apply_filtering_logic(batch_results)

        # 3. File content memory is automatically released after apply_filtering_logic
        #   because file_contents dict goes out of scope after each project analysis

        return qualified_results

    def apply_filtering_logic(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Apply strict filtering logic to a batch of results

        Designed to process a single batch of results. After analysis completes,
        file contents are released from memory automatically.

        Filtering logic:
        1. SuperGlobal detection (required condition)
        2. Primary function detection (priority 1)
        3. Fallback include detection (priority 2)

        Args:
            results: Batch of search results to filter (typically from a single batch)

        Returns:
            List of qualified search results from this batch

        Raises:
            AnalysisError: Project analysis failed
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
                error_count = self.search_stats.get("error_projects", 0)
                self.search_stats["error_projects"] = error_count + 1

        print(f"\n{'='*60}")
        print("📊 Filtering Summary:")
        print(f"   Total projects: {len(results)}")
        print(f"   Qualified: {qualified_count}")
        print(f"   Rejected: {rejected_count}")
        print(f"   Analysis errors: {error_count}")
        print(f"{'='*60}")

        return filtered_results

    def _get_project_files(self, result: SearchResult) -> Dict[str, str]:
        """
        Get PHP file content for the project

        Args:
            result: Search result

        Returns:
            Mapping of file path to content

        Raises:
            GitHubAPIError: API request failed
        """
        try:
            # Scan repository root directory for PHP files
            print(
                f"      📡 Scanning repository root: {result.owner}/{result.repo_name}"
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
        Combine analysis results from multiple files

        Args:
            analysis_results: File analysis results

        Returns:
            Combined analysis result
        """
        combined: Dict[str, Any] = {
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
            # Merge usage information
            superglobal_usage = result.get("superglobal_usage", [])
            if isinstance(superglobal_usage, list) and isinstance(combined["superglobal_usage"], list):
                combined["superglobal_usage"].extend(superglobal_usage)
            
            dynamic_function_usage = result.get("dynamic_function_usage", [])
            if isinstance(dynamic_function_usage, list) and isinstance(combined["dynamic_function_usage"], list):
                combined["dynamic_function_usage"].extend(dynamic_function_usage)
            
            dynamic_include_usage = result.get("dynamic_include_usage", [])
            if isinstance(dynamic_include_usage, list) and isinstance(combined["dynamic_include_usage"], list):
                combined["dynamic_include_usage"].extend(dynamic_include_usage)

            # Merge flags
            combined["has_superglobal"] = combined["has_superglobal"] or result.get(
                "has_superglobal", False
            )
            combined["has_dynamic_functions"] = combined[
                "has_dynamic_functions"
            ] or result.get("has_dynamic_functions", False)
            combined["has_dynamic_includes"] = combined[
                "has_dynamic_includes"
            ] or result.get("has_dynamic_includes", False)

        # Generate analysis summary
        combined["analysis_summary"] = self._generate_combined_summary(combined)

        return combined

    def _generate_combined_summary(self, combined: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate combined analysis summary

        Args:
            combined: Combined analysis result

        Returns:
            Analysis summary
        """
        # 1. Check SuperGlobal usage
        if not combined["has_superglobal"]:
            return {
                "status": "rejected",
                "reason": "No SuperGlobal usage found",
                "priority": 0,
            }

        # 2. Check main dynamic functions
        if combined["has_dynamic_functions"]:
            return {
                "status": "accepted",
                "reason": "Dynamic functions detected",
                "priority": 1,
                "detection_type": "primary_functions",
            }

        # 3. Check fallback dynamic includes
        if combined["has_dynamic_includes"]:
            return {
                "status": "accepted",
                "reason": "Dynamic includes detected",
                "priority": 2,
                "detection_type": "fallback_includes",
            }

        # 4. None of the above match
        return {
            "status": "rejected",
            "reason": "No dynamic functions or includes found",
            "priority": 0,
        }

    def _meets_criteria(self, result: SearchResult) -> bool:
        """
        Check if project meets filtering criteria

        Args:
            result: Search result

        Returns:
            Whether it meets the criteria
        """
        return result.is_qualified

    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Deduplicate search results

        Args:
            results: Original result list

        Returns:
            Deduplicated result list
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
        Update search statistics

        Args:
            results: Search result list
        """
        total_searched = len(results)
        qualified_projects = sum(1 for r in results if r.is_qualified)
        self.search_stats["total_searched"] = total_searched
        self.search_stats["qualified_projects"] = qualified_projects
        self.search_stats["rejected_projects"] = total_searched - qualified_projects

    def _export_results(
        self, results: List[SearchResult], include_unqualified: bool
    ) -> None:
        """
        Export results to CSV

        Args:
            results: Search result list
            include_unqualified: Whether to include unqualified projects
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
        """Print search summary"""
        stats = self.search_stats
        start_time = stats.get("start_time")
        end_time = stats.get("end_time")
        duration: Optional[timedelta] = None
        if start_time and end_time and isinstance(start_time, datetime) and isinstance(end_time, datetime):
            duration = end_time - start_time

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
        Get search statistics

        Returns:
            Statistics dictionary
        """
        return self.search_stats.copy()

    def close(self) -> None:
        """Close all resources"""
        self.github_client.close()
        self.cache_manager.cleanup_expired()
