"""
Lines of Code (LOC) counter for repositories.

Counts lines of code in repositories, supporting multiple file types.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict


class LOCCounter:
    """
    Counts lines of code in repositories.
    """

    # Common file extensions to count
    PHP_EXTENSIONS = {".php", ".php3", ".php4", ".php5", ".phtml"}
    CODE_EXTENSIONS = {
        ".php", ".php3", ".php4", ".php5", ".phtml",
        ".js", ".jsx", ".ts", ".tsx",
        ".py", ".java", ".cpp", ".c", ".h", ".hpp",
        ".cs", ".go", ".rs", ".rb", ".swift", ".kt",
        ".html", ".htm", ".css", ".scss", ".sass",
        ".xml", ".json", ".yaml", ".yml",
        ".sql", ".sh", ".bash", ".zsh",
    }

    # Directories to ignore
    IGNORE_DIRS = {
        ".git", ".svn", ".hg", ".bzr",
        "node_modules", "vendor", "bower_components",
        "__pycache__", ".pytest_cache", ".mypy_cache",
        "build", "dist", "target", "out",
        ".idea", ".vscode", ".vs",
        "cache", "tmp", "temp", "logs",
    }

    def __init__(self, repos_dir: str, verbose: bool = False) -> None:
        """
        Initialize the LOC counter.

        Args:
            repos_dir: Directory containing repositories
            verbose: Enable verbose output
        """
        self.repos_dir = Path(repos_dir)
        self.verbose = verbose

        if not self.repos_dir.exists():
            raise ValueError(f"Repository directory does not exist: {repos_dir}")

    def count_lines_in_file(self, file_path: Path) -> int:
        """
        Count lines in a single file.

        Args:
            file_path: Path to file

        Returns:
            Number of lines in file
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f)
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Error reading {file_path}: {e}")
            return 0

    def count_repository(
        self, repo_path: Path
    ) -> Dict[str, int]:
        """
        Count lines of code in a repository.

        Args:
            repo_path: Path to repository directory

        Returns:
            Dictionary with LOC statistics
        """
        stats: Dict[str, int] = {
            "total_files": 0,
            "php_files": 0,
            "code_files": 0,
            "total_lines": 0,
            "php_lines": 0,
            "code_lines": 0,
        }

        if not repo_path.is_dir():
            return stats

        for root, dirs, files in os.walk(repo_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]

            for file in files:
                file_path = Path(root) / file
                file_ext = file_path.suffix.lower()

                # Count all files
                stats["total_files"] += 1

                # Count PHP files specifically
                if file_ext in self.PHP_EXTENSIONS:
                    stats["php_files"] += 1
                    lines = self.count_lines_in_file(file_path)
                    stats["php_lines"] += lines

                # Count code files
                if file_ext in self.CODE_EXTENSIONS:
                    stats["code_files"] += 1
                    lines = self.count_lines_in_file(file_path)
                    stats["code_lines"] += lines
                    stats["total_lines"] += lines

        return stats

    def count_all_repositories(
        self, output_csv: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """
        Count lines of code in all repositories.

        Args:
            output_csv: Optional path to output CSV file

        Returns:
            List of dictionaries with statistics for each repository
        """
        results: List[Dict[str, any]] = []

        # Get all subdirectories (repositories)
        repos = [
            d
            for d in self.repos_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

        if not repos:
            print(f"⚠️  No repositories found in {self.repos_dir}")
            return results

        print(f"\n📊 Counting LOC in {len(repos)} repositories...")
        print(f"📁 Directory: {self.repos_dir}")

        total_stats = {
            "total_files": 0,
            "php_files": 0,
            "code_files": 0,
            "total_lines": 0,
            "php_lines": 0,
            "code_lines": 0,
        }

        for idx, repo_path in enumerate(sorted(repos), 1):
            repo_name = repo_path.name
            print(f"\n[{idx}/{len(repos)}] 📦 {repo_name}")

            stats = self.count_repository(repo_path)

            # Add repository name to stats
            result = {
                "repository": repo_name,
                **stats,
            }
            results.append(result)

            # Accumulate totals
            for key in total_stats:
                total_stats[key] += stats[key]

            # Print summary
            print(f"  📄 Files: {stats['total_files']} total, {stats['code_files']} code, {stats['php_files']} PHP")
            print(f"  📝 Lines: {stats['total_lines']} total, {stats['code_lines']} code, {stats['php_lines']} PHP")

        # Print overall summary
        print("\n" + "=" * 60)
        print("📊 Overall Summary")
        print("=" * 60)
        print(f"  📦 Repositories: {len(repos)}")
        print(f"  📄 Files: {total_stats['total_files']} total, {total_stats['code_files']} code, {total_stats['php_files']} PHP")
        print(f"  📝 Lines: {total_stats['total_lines']} total, {total_stats['code_lines']} code, {total_stats['php_lines']} PHP")
        print("=" * 60)

        # Export to CSV if requested
        if output_csv:
            self._export_to_csv(results, output_csv)

        return results

    def _export_to_csv(self, results: List[Dict[str, any]], csv_path: str) -> None:
        """
        Export results to CSV file.

        Args:
            results: List of statistics dictionaries
            csv_path: Path to output CSV file
        """
        import csv

        csv_file = Path(csv_path)
        csv_file.parent.mkdir(parents=True, exist_ok=True)

        if not results:
            return

        fieldnames = [
            "repository",
            "total_files",
            "code_files",
            "php_files",
            "total_lines",
            "code_lines",
            "php_lines",
        ]

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        print(f"\n✅ Results exported to: {csv_path}")

