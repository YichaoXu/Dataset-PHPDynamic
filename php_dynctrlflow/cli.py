#!/usr/bin/env python3
"""
Dataset-PHPDynCtrlflow - PHP Project Dataset Generator

CLI interface for collecting PHP projects from GitHub that meet specific criteria.
The goal is to obtain accurate datasets of projects with specific characteristics.
"""

import argparse
import sys
from pathlib import Path
from typing import List

from .settings import Settings
from .exceptions import AnalysisError, GitHubAPIError
from .project_searcher import ProjectSearcher


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create command-line argument parser

    Returns:
        Argument parser
    """
    parser = argparse.ArgumentParser(
        description="Dataset-PHPDynCtrlflow - PHP Project Dataset Generator for generating downloadable datasets of PHP projects with dynamic control flow characteristics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  uv run php-dynctrlflow --token YOUR_GITHUB_TOKEN
  uv run php-dynctrlflow --token YOUR_GITHUB_TOKEN --max-projects 50 --no-export
  uv run php-dynctrlflow --token YOUR_GITHUB_TOKEN --include-unqualified
        """,
    )

    # Required parameters
    parser.add_argument(
        "--token",
        type=str,
        help="GitHub API access token (default: from config.yml)",
    )

    # Optional parameters
    parser.add_argument(
        "--max-projects",
        type=int,
        default=None,
        help="Maximum number of projects (default: from config.yml)",
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
        default=None,
        help="Output directory (default: from config.yml)",
    )

    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        help="Cache directory (default: from config.yml)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show detailed error information (including tracebacks)",
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
    # Get values from config if not provided via command line
    max_projects = args.max_projects or Settings.get_max_projects()
    output_dir = args.output_dir or Settings.get_output_dir()
    cache_dir = args.cache_dir or Settings.get_cache_db_path()

    # Validate max_projects
    if max_projects <= 0:
        raise ValueError("max-projects must be greater than 0")

    if max_projects > 1000:
        print("⚠️ Warning: max-projects over 1000 may cause API rate limit issues")

    if max_projects > 5000:
        print(
            "⚠️ Warning: max-projects over 5000 may take a very long time and hit API limits"
        )

    # Validate output directory
    output_path = Path(output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(
            f"Cannot create output directory {output_dir}: {e}"
        ) from e

    # Validate cache directory
    cache_path = Path(cache_dir)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f"Cannot create cache directory {cache_dir}: {e}") from e


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
        return str(args.token)  # Type conversion for mypy

    try:
        return str(Settings.get_github_token())  # Type conversion for mypy
    except ValueError as e:
        raise ValueError(
            f"{e}\n"
            f"Please use --token parameter or set github.api_token in config.yml"
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
    max_projects = args.max_projects or Settings.get_max_projects()
    output_dir = args.output_dir or Settings.get_output_dir()
    cache_dir = args.cache_dir or Settings.get_cache_db_path()
    print(f"  • Maximum projects: {max_projects}")
    print(f"  • Output directory: {output_dir}")
    print(f"  • Cache directory: {cache_dir}")
    print(f"  • Export CSV: {'No' if args.no_export else 'Yes'}")
    print(f"  • Include unqualified: {'Yes' if args.include_unqualified else 'No'}")


def main() -> int:
    """
    Main function

    Returns:
        Exit code
    """
    # Parse command-line arguments first (before any operations)
    parser = create_argument_parser()
    try:
        args = parser.parse_args()
        debug_mode = args.debug
    except SystemExit:
        # argparse exits on --help or --version
        return 0
    except Exception:
        # If argument parsing fails, we can't use debug flag
        debug_mode = False

    try:
        # Print banner
        print_banner()

        # Validate arguments
        validate_arguments(args)

        # Get GitHub token
        github_token = get_github_token(args)

        # Print configuration summary
        print_config_summary(args)

        # Create project searcher
        print("\n🚀 Initializing project searcher...")
        searcher = ProjectSearcher(github_token)

        try:
            # Execute search
            print("\n🔍 Starting project search and analysis...")
            searcher.search_projects(
                max_projects=args.max_projects,  # None means use config.yml
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
        if debug_mode:
            print(f"\n❌ Parameter error: {e}")
            import traceback
            traceback.print_exc()
        else:
            print(f"\n❌ Parameter error: {e}")
        return 1

    except GitHubAPIError as e:
        if debug_mode:
            print(f"\n❌ GitHub API error: {e}")
            if hasattr(e, 'status_code'):
                print(f"   Status code: {e.status_code}")
            if hasattr(e, 'response_data'):
                print(f"   Response data: {e.response_data}")
            import traceback
            traceback.print_exc()
        else:
            print(f"\n❌ GitHub API error occurred")
            print("   Use --debug for detailed error information")
        return 2

    except AnalysisError as e:
        if debug_mode:
            print(f"\n❌ Analysis error: {e}")
            if hasattr(e, 'file_path'):
                print(f"   File path: {e.file_path}")
            if hasattr(e, 'line_number'):
                print(f"   Line number: {e.line_number}")
            import traceback
            traceback.print_exc()
        else:
            print(f"\n❌ Analysis error occurred")
            print("   Use --debug for detailed error information")
        return 3

    except Exception as e:
        if debug_mode:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        else:
            print(f"\n❌ An unexpected error occurred")
            print(f"   Error type: {type(e).__name__}")
            print("   Use --debug for detailed error information")
        return 4


