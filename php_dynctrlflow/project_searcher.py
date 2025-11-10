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
from .settings import Settings


class ProjectSearcher:
    """Project searcher that coordinates all components to complete project search and filtering"""

    def _debug_print(self, message: str) -> None:
        """Print debug message if debug mode is enabled"""
        if self.debug:
            print(message)

    def __init__(
        self,
        github_token: str,
        cache_manager: Optional[CacheManager] = None,
        rate_limit_handler: Optional[RateLimitHandler] = None,
        semgrep_analyzer: Optional[SemgrepAnalyzer] = None,
        php_analyzer: Optional[PHPAnalyzer] = None,
        csv_exporter: Optional[CSVExporter] = None,
        debug: bool = False,
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
            debug: Enable debug output
        """
        # Initialize components
        self.cache_manager = cache_manager or CacheManager()
        self.rate_limit_handler = rate_limit_handler or RateLimitHandler()
        self.semgrep_analyzer = semgrep_analyzer or SemgrepAnalyzer()
        self.php_analyzer = php_analyzer or PHPAnalyzer(self.semgrep_analyzer)
        self.csv_exporter = csv_exporter or CSVExporter()
        self.debug = debug

        # Initialize GitHub client
        self.github_client = GitHubAPIClient(
            github_token, self.cache_manager, self.rate_limit_handler, debug=debug
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

        Note: GitHub Search API has a hard limit of 1000 results per query.
        This means for a single query, you can only get the first 1000 results.
        However, you CAN query different ranges to get different sets of results.
        
        Strategy:
        1. First, check total_count to see how many results exist
        2. If count <= 1000, use simple query
        3. If count > 1000, split by stars ranges to get different result sets
        4. Merge and deduplicate results, then sort by stars

        Args:
            count: Number of projects to get

        Returns:
            repositorySearch result list, sorted by stars (descending)

        Raises:
            GitHubAPIError: GitHub API request failed
        """
        # GitHub Search API hard limit: maximum 1000 results per query
        GITHUB_SEARCH_MAX_RESULTS = 1000
        
        try:
            # Use Repository Search API to search for PHP projects, sorted by stars
            base_query = "language:PHP"
            print(f"  📡 GitHub Repository Search API:")
            print(f"     Base Query: {base_query}")
            print(f"     Sort: stars (descending)")
            print(f"     Requested: {count} projects")

            # First, check total_count to see how many results exist
            _, total_count = self.github_client.search_repositories_optimized(
                query=base_query,
                per_page=1,
                page=1,
            )
            
            if total_count is not None:
                print(f"  📊 Total matching repositories: {total_count}")
                if total_count <= GITHUB_SEARCH_MAX_RESULTS:
                    print(f"  ℹ️  Total results ({total_count}) <= {GITHUB_SEARCH_MAX_RESULTS}, using simple query")
                else:
                    print(f"  ⚠️  Total results ({total_count}) > {GITHUB_SEARCH_MAX_RESULTS}, need to use multi-query strategy")
                    print(f"     Note: GitHub Search API can only return first {GITHUB_SEARCH_MAX_RESULTS} results per query")
                    print(f"     We'll query different stars ranges to get different result sets")

            # If count <= 1000, use simple query
            if count <= GITHUB_SEARCH_MAX_RESULTS:
                return self._search_single_query(base_query, count)
            
            # For count > 1000, split by stars ranges
            print(f"  🔄 Using multi-query strategy to bypass 1000 result limit")
            print(f"     Each query can return up to {GITHUB_SEARCH_MAX_RESULTS} results")
            
            return self._search_with_stars_ranges(base_query, count)

        except Exception as e:
            print(f"  ❌ GitHub search failed: {e}")
            import traceback

            print("  📋 Error details:")
            print(f"     {traceback.format_exc()}")
            raise GitHubAPIError(f"GitHub search failed: {e}") from e

    def _search_single_query(
        self, query: str, count: int
    ) -> List[Dict[str, Any]]:
        """
        Search with a single query (for count <= 1000).

        Args:
            query: Search query
            count: Number of results to get

        Returns:
            List of repository dictionaries
        """
        all_repos: List[Dict[str, Any]] = []
        per_page = 100  # GitHub maximum limit is 100 per page
        pages_needed = min((count + per_page - 1) // per_page, 10)

        # Track total_count from first query to know actual available results
        first_total_count = None
        
        for page in range(1, pages_needed + 1):
            if len(all_repos) >= count:
                break

            remaining = count - len(all_repos)
            current_per_page = min(remaining, per_page)

            print(f"  📄 Fetching page {page}/{pages_needed} (requesting {current_per_page} items)...")
            self._debug_print(f"  🔍 [DEBUG] Query: {query[:80]}...")
            self._debug_print(f"  🔍 [DEBUG] Requesting per_page={current_per_page}, page={page}")

            repos, total_count = self.github_client.search_repositories_optimized(
                query=query,
                per_page=current_per_page,
                page=page,
            )
            
            # Capture total_count from first query
            if first_total_count is None and total_count is not None:
                first_total_count = total_count
                self._debug_print(f"  🔍 [DEBUG] First query total_count: {first_total_count}")
            
            self._debug_print(f"  🔍 [DEBUG] Received {len(repos)} repos (expected {current_per_page})")
            self._debug_print(f"  🔍 [DEBUG] Total count from API: {total_count}")
            
            all_repos.extend(repos)

            print(f"  ✅ Page {page}: Retrieved {len(repos)} repositories")
            print(f"  📊 Total so far: {len(all_repos)}/{count}")

            # Check if we should continue pagination
            # If we got fewer results than requested, check if it's because:
            # 1. We've reached the end (no more results available)
            # 2. Cache returned incomplete data (old format with fewer items)
            if len(repos) < current_per_page:
                # If we have total_count, check if we've gotten all available results
                if first_total_count is not None:
                    if len(all_repos) >= first_total_count:
                        self._debug_print(f"  🔍 [DEBUG] Got all available results ({len(all_repos)} >= {first_total_count})")
                        print(f"  ⚠️  No more results available")
                        break
                    else:
                        print(f"  ⚠️  Got {len(repos)} < {current_per_page} results, but total_count={first_total_count} suggests more available")
                        self._debug_print(f"  🔍 [DEBUG] This might be incomplete cache data, but continuing anyway")
                        # Continue to next page to try getting more
                        continue
                else:
                    # No total_count available, assume we've reached the end
                    print(f"  ⚠️  No more results available (no total_count to verify)")
                    self._debug_print(f"  🔍 [DEBUG] Got {len(repos)} < {current_per_page} results, stopping pagination")
                    break

        if len(all_repos) > count:
            all_repos = all_repos[:count]

        print(f"\n  ✅ Successfully retrieved {len(all_repos)} PHP repositories")
        return all_repos

    def _search_with_stars_ranges(
        self, base_query: str, count: int
    ) -> List[Dict[str, Any]]:
        """
        Search by splitting queries into stars ranges to bypass 1000 result limit.

        Strategy:
        1. Start with high stars ranges (e.g., stars:>=10000)
        2. For each range, check total_count
        3. If a range has > 1000 results, dynamically subdivide it
        4. Continue until we have enough results or no more ranges available
        5. Merge and deduplicate results, then sort by stars

        Args:
            base_query: Base search query (e.g., "language:PHP")
            count: Number of results to get

        Returns:
            List of repository dictionaries, sorted by stars (descending)
        """
        GITHUB_SEARCH_MAX_RESULTS = 1000
        all_repos: List[Dict[str, Any]] = []
        seen_repo_ids: set = set()  # For deduplication

        # Define initial stars ranges (descending order)
        # These are starting points; ranges will be subdivided if needed
        initial_ranges = [
            (100000, None),  # Very popular (>=100k stars)
            (50000, 99999),
            (20000, 49999),
            (10000, 19999),
            (5000, 9999),
            (2000, 4999),
            (1000, 1999),
            (500, 999),
            (200, 499),
            (100, 199),
            (50, 99),
            (20, 49),
            (10, 19),
            (1, 9),
            (0, 0),  # No stars
        ]

        print(f"  📊 Strategy: Query multiple stars ranges and merge results")
        print(f"     Initial ranges: {len(initial_ranges)}")
        print(f"     Will dynamically subdivide ranges with > {GITHUB_SEARCH_MAX_RESULTS} results")

        # Process ranges as a queue, subdividing as needed
        ranges_to_process = [(min_stars, max_stars) for min_stars, max_stars in initial_ranges]
        range_idx = 0

        while ranges_to_process and len(all_repos) < count:
            range_idx += 1
            min_stars, max_stars = ranges_to_process.pop(0)

            # Build query with stars range
            if max_stars is None:
                stars_query = f"stars:>={min_stars}"
            else:
                stars_query = f"stars:{min_stars}..{max_stars}"
            
            query = f"{base_query} {stars_query}"
            
            print(f"\n  🔍 Range {range_idx}: {stars_query}")
            print(f"     Query: {query}")

            try:
                # First, check total_count for this range
                self._debug_print(f"  🔍 [DEBUG] Checking total_count for range: {stars_query}")
                self._debug_print(f"  🔍 [DEBUG] Query: {query}")
                check_results, total_count = self.github_client.search_repositories_optimized(
                    query=query,
                    per_page=1,
                    page=1,
                )
                
                self._debug_print(f"  🔍 [DEBUG] Check query returned {len(check_results)} results (expected 1)")
                
                if total_count is None:
                    print(f"  ⚠️  Could not get total_count for range, skipping")
                    continue
                
                print(f"  📊 Total results in range: {total_count}")

                # If this range has > 1000 results, subdivide it
                if total_count > GITHUB_SEARCH_MAX_RESULTS:
                    print(f"  ⚠️  Range has {total_count} results (>{GITHUB_SEARCH_MAX_RESULTS}), subdividing...")
                    
                    # Subdivide the range
                    sub_ranges = self._subdivide_stars_range(min_stars, max_stars)
                    print(f"  🔄 Subdivided into {len(sub_ranges)} sub-ranges")
                    
                    # Add sub-ranges to the front of the queue (process higher stars first)
                    ranges_to_process = sub_ranges + ranges_to_process
                    continue

                # Range has <= 1000 results, fetch all of them
                fetch_count = min(total_count, GITHUB_SEARCH_MAX_RESULTS)
                self._debug_print(f"  🔍 [DEBUG] Fetching {fetch_count} results for range (total_count={total_count})")
                range_repos = self._search_single_query(query, fetch_count)
                
                self._debug_print(f"  🔍 [DEBUG] _search_single_query returned {len(range_repos)} repos (expected {fetch_count})")
                
                # Deduplicate and add new repos
                new_repos = []
                for repo in range_repos:
                    # Validate repo format (should be dict)
                    if not isinstance(repo, dict):
                        self._debug_print(f"  ⚠️  [DEBUG] Invalid repo format (not dict): {type(repo)}, skipping")
                        continue
                    repo_id = repo.get("id")
                    if repo_id and repo_id not in seen_repo_ids:
                        seen_repo_ids.add(repo_id)
                        new_repos.append(repo)
                
                self._debug_print(f"  🔍 [DEBUG] After deduplication: {len(new_repos)} new repos (from {len(range_repos)} total)")
                
                all_repos.extend(new_repos)
                
                print(f"  ✅ Range {range_idx}: Retrieved {len(range_repos)} repos, {len(new_repos)} new")
                print(f"  📊 Total so far: {len(all_repos)}/{count}")

                # If this range returned less than requested, likely no more results in lower ranges
                if len(range_repos) < total_count:
                    print(f"  ℹ️  Range returned {len(range_repos)} results (less than total {total_count})")
                    self._debug_print(f"  🔍 [DEBUG] Missing {total_count - len(range_repos)} results from this range")

            except Exception as e:
                print(f"  ⚠️  Range {range_idx} failed: {e}")
                # Continue with next range
                continue

        # Sort by stars (descending) and limit to requested count
        all_repos.sort(key=lambda x: x.get("stargazers_count", 0), reverse=True)
        
        if len(all_repos) > count:
            all_repos = all_repos[:count]

        print(f"\n  ✅ Successfully retrieved {len(all_repos)} PHP repositories")
        print(f"     (from {range_idx} ranges, deduplicated)")
        
        if len(all_repos) < count:
            print(f"  ⚠️  Note: Only {len(all_repos)} results available (may have exhausted all matching repositories)")

        return all_repos

    def _subdivide_stars_range(
        self, min_stars: int, max_stars: int | None
    ) -> List[tuple[int, int | None]]:
        """
        Subdivide a stars range into smaller ranges.

        Strategy:
        - For ranges with max_stars, split into 2-4 sub-ranges
        - For ranges with max_stars=None (>=min_stars), use exponential backoff
        - Ensure each sub-range is small enough to potentially have <= 1000 results

        Args:
            min_stars: Minimum stars in range
            max_stars: Maximum stars in range (None means >=min_stars)

        Returns:
            List of (min_stars, max_stars) tuples for sub-ranges
        """
        if max_stars is None:
            # For open-ended ranges (>=min_stars), use exponential backoff
            # Start with smaller ranges at the top, larger at the bottom
            if min_stars >= 100000:
                # Very high stars: split into smaller chunks
                return [
                    (min_stars * 2, None),  # >= 2*min_stars
                    (min_stars, min_stars * 2 - 1),  # min_stars..2*min_stars-1
                ]
            elif min_stars >= 10000:
                # High stars: split into 2-3 chunks
                return [
                    (min_stars * 2, None),  # >= 2*min_stars
                    (int(min_stars * 1.5), min_stars * 2 - 1),  # 1.5*min_stars..2*min_stars-1
                    (min_stars, int(min_stars * 1.5) - 1),  # min_stars..1.5*min_stars-1
                ]
            else:
                # Lower stars: split into more chunks
                return [
                    (min_stars * 3, None),  # >= 3*min_stars
                    (min_stars * 2, min_stars * 3 - 1),  # 2*min_stars..3*min_stars-1
                    (int(min_stars * 1.5), min_stars * 2 - 1),  # 1.5*min_stars..2*min_stars-1
                    (min_stars, int(min_stars * 1.5) - 1),  # min_stars..1.5*min_stars-1
                ]
        else:
            # For bounded ranges, split into 2-4 sub-ranges
            range_size = max_stars - min_stars + 1
            
            if range_size <= 100:
                # Small range, don't subdivide further
                return [(min_stars, max_stars)]
            elif range_size <= 500:
                # Medium range, split into 2
                mid = (min_stars + max_stars) // 2
                return [
                    (mid + 1, max_stars),  # Upper half
                    (min_stars, mid),  # Lower half
                ]
            elif range_size <= 2000:
                # Large range, split into 3
                third = range_size // 3
                return [
                    (min_stars + 2 * third + 1, max_stars),  # Upper third
                    (min_stars + third + 1, min_stars + 2 * third),  # Middle third
                    (min_stars, min_stars + third),  # Lower third
                ]
            else:
                # Very large range, split into 4
                quarter = range_size // 4
                return [
                    (min_stars + 3 * quarter + 1, max_stars),  # Upper quarter
                    (min_stars + 2 * quarter + 1, min_stars + 3 * quarter),  # Third quarter
                    (min_stars + quarter + 1, min_stars + 2 * quarter),  # Second quarter
                    (min_stars, min_stars + quarter),  # Lower quarter
                ]

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
                try:
                    file_contents = self._get_project_files(result)
                except GitHubAPIError as e:
                    print(f"   ❌ Failed to get project files: {e}")
                    result.add_metadata("analysis_error", f"Failed to get files: {e}")
                    error_count += 1
                    continue

                if not file_contents:
                    # No files found with SuperGlobal patterns - this is a valid result
                    # The repository doesn't contain SuperGlobal usage, so it's rejected
                    print("   ℹ️  No SuperGlobal usage found")
                    result.add_metadata("rejection_reason", "No SuperGlobal usage found")
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
        Get PHP file content for the project using Code Search API
        
        This method uses GitHub Code Search API to find files containing SuperGlobal
        usage patterns, which is more efficient than scanning all files.

        Args:
            result: Search result

        Returns:
            Mapping of file path to content

        Raises:
            GitHubAPIError: API request failed
        """
        try:
            file_contents: Dict[str, str] = {}
            max_files = Settings.get_max_files_per_project()

            # Use Code Search API to find files containing SuperGlobal usage
            # This is more efficient than scanning all repository files
            superglobal_patterns = [
                "$_GET", "$_POST", "$_REQUEST", "$_COOKIE", 
                "$_SESSION", "$_SERVER", "$_FILES", "$_ENV"
            ]
            
            print(f"      📡 Searching for files with SuperGlobal usage patterns")
            print(f"         Repository: {result.owner}/{result.repo_name}")
            
            # Search for files containing any SuperGlobal pattern
            # GitHub Code Search API supports pattern matching
            search_query = " OR ".join([f'"{pattern}"' for pattern in superglobal_patterns[:3]])
            # Use first few patterns to find candidate files
            
            try:
                code_results = self.github_client.search_code_in_repository(
                    result.owner,
                    result.repo_name,
                    query=search_query,
                    language="PHP"
                )
                
                # Ensure code_results is a list, not None
                if code_results is None:
                    code_results = []
                
                print(f"      ✅ Found {len(code_results)} file(s) with SuperGlobal patterns")
                
                if not code_results:
                    # No files found with SuperGlobal patterns - this is a valid result
                    # The repository may not contain SuperGlobal usage
                    print(f"      ℹ️  No files found with SuperGlobal patterns in this repository")
                    return {}
                
                # Get unique file paths from search results
                # GitHub Code Search API already filtered by language and pattern,
                # so we can trust the results and don't need to filter by extension
                unique_paths = set()
                for item in code_results:
                    file_path = item.get("path", "")
                    if file_path:  # Only check if path exists
                        unique_paths.add(file_path)
                
                print(f"         Unique files found: {len(unique_paths)}")
                
                if not unique_paths:
                    # No unique paths found - this is a valid result
                    print(f"      ℹ️  No unique file paths found in search results")
                    return {}
                
                # Fetch file contents for matched files
                # Use all files returned by Code Search API (up to max_files limit)
                unique_paths_list = list(unique_paths)[:max_files]
                for i, file_path in enumerate(unique_paths_list, 1):
                    try:
                        print(f"         📄 [{i}/{len(unique_paths_list)}] Fetching file: {file_path}")

                        content = self.github_client.get_file_content(
                            result.owner, result.repo_name, file_path
                        )
                        file_contents[file_path] = content

                        file_size = len(content)
                        print(f"            ✅ File size: {file_size} characters")

                    except Exception as e:
                        print(f"         ❌ Failed to fetch file {file_path}: {e}")
                        continue

                print("      📊 File Fetching Summary:")
                print(f"         Code search results: {len(code_results)}")
                print(f"         Unique files: {len(unique_paths)}")
                print(f"         Successfully fetched: {len(file_contents)}")
                
            except Exception as e:
                # Code Search API failed - raise error
                print(f"      ❌ Code Search API failed: {e}")
                raise GitHubAPIError(
                    f"Code Search API failed for {result.owner}/{result.repo_name}: {e}"
                ) from e

            return file_contents

        except GitHubAPIError:
            # Re-raise GitHubAPIError without wrapping
            raise
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
