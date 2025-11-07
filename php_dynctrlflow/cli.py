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
from .downloader import ProjectDownloader
from .loc_counter import LOCCounter


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create command-line argument parser with subcommands

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
  uv run php-dynctrlflow download path/to/projects.csv
        """,
    )

    # Global arguments
    parser.add_argument(
        "--version",
        action="version",
        version=f"{Settings.PROJECT_NAME} {Settings.PROJECT_VERSION}",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show detailed error information (including tracebacks)",
    )

    # Search command arguments (for backward compatibility, keep in main parser)
    parser.add_argument(
        "--token",
        type=str,
        help="GitHub API access token (default: from config.yml)",
    )
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

    # Create subparsers for download command
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=False)

    # Download command
    download_parser = subparsers.add_parser(
        "download",
        help="Download projects from CSV file",
        description="Download GitHub repositories from CSV file using archive links",
    )
    download_parser.add_argument(
        "csv_path",
        type=str,
        help="Path to CSV file containing project information",
    )
    download_parser.add_argument(
        "--output-dir",
        type=str,
        default="data/repos",
        help="Output directory for downloaded projects (default: data/repos)",
    )
    download_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    # LOC command
    loc_parser = subparsers.add_parser(
        "loc",
        help="Count lines of code in repositories",
        description="Count lines of code (LOC) in repositories",
    )
    loc_parser.add_argument(
        "--repos-dir",
        type=str,
        default="data/repos",
        help="Directory containing repositories (default: data/repos)",
    )
    loc_parser.add_argument(
        "--output-csv",
        type=str,
        default=None,
        help="Path to output CSV file (optional)",
    )
    loc_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
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


def handle_search_command(args: argparse.Namespace, debug_mode: bool) -> int:
    """
    Handle search command.

    Args:
        args: Parsed arguments
        debug_mode: Enable debug mode

    Returns:
        Exit code
    """
    try:
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


def handle_loc_command(args: argparse.Namespace, debug_mode: bool) -> int:
    """
    Handle LOC counting command.

    Args:
        args: Parsed arguments
        debug_mode: Enable debug mode

    Returns:
        Exit code
    """
    try:
        # Print banner
        print_banner()

        # Create LOC counter
        counter = LOCCounter(
            repos_dir=args.repos_dir,
            verbose=args.verbose,
        )

        # Count LOC in all repositories
        results = counter.count_all_repositories(output_csv=args.output_csv)

        if results:
            print(f"\n✅ Successfully counted LOC in {len(results)} repositories!")
        else:
            print("\n⚠️  No repositories found")

        return 0

    except ValueError as e:
        if debug_mode:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        else:
            print(f"\n❌ Error: {e}")
            print("   Use --debug for detailed error information")
        return 1

    except Exception as e:
        if debug_mode:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        else:
            print(f"\n❌ An unexpected error occurred")
            print(f"   Error type: {type(e).__name__}")
            print("   Use --debug for detailed error information")
        return 2


def handle_download_command(args: argparse.Namespace, debug_mode: bool) -> int:
    """
    Handle download command.

    Args:
        args: Parsed arguments
        debug_mode: Enable debug mode

    Returns:
        Exit code
    """
    try:
        # Print banner
        print_banner()

        # Create downloader
        downloader = ProjectDownloader(
            output_dir=args.output_dir,
            verbose=args.verbose,
        )

        # Download projects from CSV
        stats = downloader.download_from_csv(args.csv_path)

        # Print summary
        print("\n" + "=" * 60)
        print("📊 Download Summary")
        print("=" * 60)
        print(f"  • Total projects: {stats['total']}")
        print(f"  • Successfully downloaded: {stats['success']}")
        print(f"  • Failed: {stats['failed']}")
        print(f"  • Skipped: {stats['skipped']}")
        print(f"  • Output directory: {args.output_dir}")
        print("=" * 60)

        if stats["success"] > 0:
            print(f"\n✅ Successfully downloaded {stats['success']} projects!")
        if stats["failed"] > 0:
            print(f"\n⚠️  {stats['failed']} projects failed to download")
        if stats["skipped"] > 0:
            print(f"\n⏭️  {stats['skipped']} projects were skipped")

        return 0 if stats["failed"] == 0 else 1

    except AnalysisError as e:
        if debug_mode:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        else:
            print(f"\n❌ Error: {e}")
            print("   Use --debug for detailed error information")
        return 1

    except Exception as e:
        if debug_mode:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        else:
            print(f"\n❌ An unexpected error occurred")
            print(f"   Error type: {type(e).__name__}")
            print("   Use --debug for detailed error information")
        return 2


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
        debug_mode = args.debug if hasattr(args, "debug") else False
    except SystemExit:
        # argparse exits on --help or --version
        return 0
    except Exception:
        # If argument parsing fails, we can't use debug flag
        debug_mode = False

    try:
        # Handle subcommands
        command = getattr(args, "command", None)

        # Default to search command if no command specified (backward compatibility)
        if command == "download":
            return handle_download_command(args, debug_mode)
        elif command == "loc":
            return handle_loc_command(args, debug_mode)
        else:
            # Default to search command (backward compatible with old argument format)
            # Print banner
            print_banner()
            return handle_search_command(args, debug_mode)

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


