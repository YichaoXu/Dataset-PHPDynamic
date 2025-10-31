#!/usr/bin/env python3
"""
PHPIncludes - PHP Project Dynamic Include/Require Detection Tool

Main program entry point providing command-line interface for searching and analyzing PHP projects.
"""

import argparse
import sys
from pathlib import Path
from typing import List

from config.settings import Settings
from src.exceptions import AnalysisError, GitHubAPIError
from src.project_searcher import ProjectSearcher


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create command-line argument parser

    Returns:
        Argument parser
    """
    parser = argparse.ArgumentParser(
        description="PHPIncludes - PHP Project Dynamic Include/Require Detection Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python main.py --token YOUR_GITHUB_TOKEN
  python main.py --token YOUR_GITHUB_TOKEN --queries "call_user_func" "include $_GET"
  python main.py --token YOUR_GITHUB_TOKEN --max-projects 50 --no-export
  python main.py --token YOUR_GITHUB_TOKEN --include-unqualified
        """,
    )

    # Required parameters
    parser.add_argument(
        "--token",
        type=str,
        help="GitHub API access token (or set GITHUB_TOKEN environment variable)",
    )

    # Optional parameters
    parser.add_argument(
        "--queries",
        nargs="+",
        help="Search query list (default uses predefined queries)",
    )

    parser.add_argument(
        "--max-projects",
        type=int,
        default=Settings.DEFAULT_MAX_PROJECTS,
        help=f"Maximum number of projects (default: {Settings.DEFAULT_MAX_PROJECTS})",
    )

    parser.add_argument(
        "--language",
        type=str,
        default=Settings.DEFAULT_LANGUAGE,
        help=f"Programming language filter (default: {Settings.DEFAULT_LANGUAGE})",
    )

    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Do not export CSV files",
    )

    parser.add_argument(
        "--include-unqualified",
        action="store_true",
        help="Include unqualified projects in CSV",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=Settings.OUTPUT_DIR,
        help=f"Output directory (default: {Settings.OUTPUT_DIR})",
    )

    parser.add_argument(
        "--cache-dir",
        type=str,
        default=Settings.CACHE_DB_PATH,
        help=f"Cache directory (default: {Settings.CACHE_DB_PATH})",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"{Settings.PROJECT_NAME} {Settings.PROJECT_VERSION}",
    )

    return parser


def validate_arguments(args: argparse.Namespace) -> None:
    """
    Validate command-line arguments

    Args:
        args: Parsed arguments

    Raises:
        ValueError: Argument validation failed
    """
    if args.max_projects <= 0:
        raise ValueError("max-projects must be greater than 0")

    if args.max_projects > 1000:
        print("⚠️ Warning: max-projects over 1000 may cause API rate limit issues")

    if args.max_projects > 5000:
        print(
            "⚠️ Warning: max-projects over 5000 may take a very long time and hit API limits"
        )

    # Validate output directory
    output_path = Path(args.output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(
            f"Cannot create output directory {args.output_dir}: {e}"
        ) from e

    # Validate cache directory
    cache_path = Path(args.cache_dir)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f"Cannot create cache directory {args.cache_dir}: {e}") from e


def get_github_token(args: argparse.Namespace) -> str:
    """
    Get GitHub API token

    Args:
        args: Command-line arguments

    Returns:
        GitHub API token

    Raises:
        ValueError: Token not found
    """
    if args.token:
        return args.token

    try:
        return Settings.get_github_token()
    except ValueError as e:
        raise ValueError(
            f"{e}\n"
            f"Please use --token parameter or set {Settings.GITHUB_API_TOKEN_ENV} environment variable"
        ) from e


def print_banner() -> None:
    """Print program banner"""
    info = Settings.get_project_info()
    print("=" * 60)
    print(f"🔍 {info['name']} v{info['version']}")
    print(f"📝 {info['description']}")
    print("=" * 60)


def print_config_summary(args: argparse.Namespace) -> None:
    """
    Print configuration summary

    Args:
        args: Command-line arguments
    """
    print("\n📋 Configuration Summary:")
    print(f"  • Maximum projects: {args.max_projects}")
    print(f"  • Language filter: {args.language}")
    print(f"  • Output directory: {args.output_dir}")
    print(f"  • Cache directory: {args.cache_dir}")
    print(f"  • Export CSV: {'No' if args.no_export else 'Yes'}")
    print(f"  • Include unqualified: {'Yes' if args.include_unqualified else 'No'}")


def print_search_queries(queries: List[str]) -> None:
    """
    Print search queries

    Args:
        queries: Search query list
    """
    print(f"\n🔍 Search Queries ({len(queries)}):")
    for i, query in enumerate(queries, 1):
        print(f"  {i}. {query}")


def main() -> int:
    """
    Main function

    Returns:
        Exit code
    """
    try:
        # Parse command-line arguments
        parser = create_argument_parser()
        args = parser.parse_args()

        # Print banner
        print_banner()

        # Validate arguments
        validate_arguments(args)

        # Get GitHub token
        github_token = get_github_token(args)

        # Get search queries with language filtering
        search_queries = Settings.get_search_queries(args.queries, args.language)

        # Print configuration summary
        print_config_summary(args)
        print_search_queries(search_queries)

        # Create project searcher
        print("\n🚀 Initializing project searcher...")
        searcher = ProjectSearcher(github_token)

        try:
            # Execute search
            print("\n🔍 Starting project search and analysis...")
            searcher.search_projects(
                search_queries=search_queries,
                max_projects=args.max_projects,
                export_csv=not args.no_export,
                include_unqualified=args.include_unqualified,
            )

            # Print result summary
            stats = searcher.get_search_statistics()
            print("\n✅ Search completed!")
            print(f"  • Total projects: {stats['total_searched']}")
            print(f"  • Qualified: {stats['qualified_projects']}")
            print(f"  • Rejected: {stats['rejected_projects']}")
            print(f"  • Analysis errors: {stats['error_projects']}")

            if stats["qualified_projects"] > 0:
                print(f"\n🎉 Found {stats['qualified_projects']} qualified projects!")
            else:
                print("\n😔 No qualified projects found")

            return 0

        finally:
            # Cleanup resources
            searcher.close()

    except KeyboardInterrupt:
        print("\n\n⏹️ User interrupted operation")
        return 130

    except ValueError as e:
        print(f"\n❌ Parameter error: {e}")
        return 1

    except GitHubAPIError as e:
        print(f"\n❌ GitHub API error: {e}")
        if args.verbose:
            print(f"   Status code: {e.status_code}")
            print(f"   Response data: {e.response_data}")
        return 2

    except AnalysisError as e:
        print(f"\n❌ Analysis error: {e}")
        if args.verbose:
            print(f"   File path: {e.file_path}")
            print(f"   Line number: {e.line_number}")
        return 3

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 4


if __name__ == "__main__":
    sys.exit(main())
