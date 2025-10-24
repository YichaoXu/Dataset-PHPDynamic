#!/usr/bin/env python3
"""
PHPIncludes - PHP项目动态include/require检测工具

主程序入口点，提供命令行接口来搜索和分析PHP项目。
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
    创建命令行参数解析器

    Returns:
        参数解析器
    """
    parser = argparse.ArgumentParser(
        description="PHPIncludes - PHP项目动态include/require检测工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py --token YOUR_GITHUB_TOKEN
  python main.py --token YOUR_GITHUB_TOKEN --queries "call_user_func" "include $_GET"
  python main.py --token YOUR_GITHUB_TOKEN --max-projects 50 --no-export
  python main.py --token YOUR_GITHUB_TOKEN --include-unqualified
        """,
    )

    # 必需参数
    parser.add_argument(
        "--token",
        type=str,
        help="GitHub API访问令牌 (或设置GITHUB_TOKEN环境变量)",
    )

    # 可选参数
    parser.add_argument(
        "--queries",
        nargs="+",
        help="搜索查询列表 (默认使用预定义查询)",
    )

    parser.add_argument(
        "--max-projects",
        type=int,
        default=Settings.DEFAULT_MAX_PROJECTS,
        help=f"最大项目数量 (默认: {Settings.DEFAULT_MAX_PROJECTS})",
    )

    parser.add_argument(
        "--no-export",
        action="store_true",
        help="不导出CSV文件",
    )

    parser.add_argument(
        "--include-unqualified",
        action="store_true",
        help="在CSV中包含不符合条件的项目",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=Settings.OUTPUT_DIR,
        help=f"输出目录 (默认: {Settings.OUTPUT_DIR})",
    )

    parser.add_argument(
        "--cache-dir",
        type=str,
        default=Settings.CACHE_DB_PATH,
        help=f"缓存目录 (默认: {Settings.CACHE_DB_PATH})",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="详细输出",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"{Settings.PROJECT_NAME} {Settings.PROJECT_VERSION}",
    )

    return parser


def validate_arguments(args: argparse.Namespace) -> None:
    """
    验证命令行参数

    Args:
        args: 解析后的参数

    Raises:
        ValueError: 参数验证失败
    """
    if args.max_projects <= 0:
        raise ValueError("max-projects must be greater than 0")

    if args.max_projects > 1000:
        print("⚠️ 警告: max-projects超过1000可能导致API限制问题")

    # 验证输出目录
    output_path = Path(args.output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f"无法创建输出目录 {args.output_dir}: {e}") from e

    # 验证缓存目录
    cache_path = Path(args.cache_dir)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f"无法创建缓存目录 {args.cache_dir}: {e}") from e


def get_github_token(args: argparse.Namespace) -> str:
    """
    获取GitHub API令牌

    Args:
        args: 命令行参数

    Returns:
        GitHub API令牌

    Raises:
        ValueError: 令牌未找到
    """
    if args.token:
        return args.token

    try:
        return Settings.get_github_token()
    except ValueError as e:
        raise ValueError(
            f"{e}\n"
            f"请使用 --token 参数或设置 {Settings.GITHUB_API_TOKEN_ENV} 环境变量"
        ) from e


def print_banner() -> None:
    """打印程序横幅"""
    info = Settings.get_project_info()
    print("=" * 60)
    print(f"🔍 {info['name']} v{info['version']}")
    print(f"📝 {info['description']}")
    print("=" * 60)


def print_config_summary(args: argparse.Namespace) -> None:
    """
    打印配置摘要

    Args:
        args: 命令行参数
    """
    print("\n📋 配置摘要:")
    print(f"  • 最大项目数: {args.max_projects}")
    print(f"  • 输出目录: {args.output_dir}")
    print(f"  • 缓存目录: {args.cache_dir}")
    print(f"  • 导出CSV: {'否' if args.no_export else '是'}")
    print(f"  • 包含不符合条件项目: {'是' if args.include_unqualified else '否'}")


def print_search_queries(queries: List[str]) -> None:
    """
    打印搜索查询

    Args:
        queries: 搜索查询列表
    """
    print(f"\n🔍 搜索查询 ({len(queries)}个):")
    for i, query in enumerate(queries, 1):
        print(f"  {i}. {query}")


def main() -> int:
    """
    主函数

    Returns:
        退出码
    """
    try:
        # 解析命令行参数
        parser = create_argument_parser()
        args = parser.parse_args()

        # 打印横幅
        print_banner()

        # 验证参数
        validate_arguments(args)

        # 获取GitHub令牌
        github_token = get_github_token(args)

        # 获取搜索查询
        search_queries = Settings.get_search_queries(args.queries)

        # 打印配置摘要
        print_config_summary(args)
        print_search_queries(search_queries)

        # 创建项目搜索器
        print("\n🚀 初始化项目搜索器...")
        searcher = ProjectSearcher(github_token)

        try:
            # 执行搜索
            print("\n🔍 开始搜索和分析项目...")
            searcher.search_projects(
                search_queries=search_queries,
                max_projects=args.max_projects,
                export_csv=not args.no_export,
                include_unqualified=args.include_unqualified,
            )

            # 打印结果摘要
            stats = searcher.get_search_statistics()
            print("\n✅ 搜索完成!")
            print(f"  • 总项目数: {stats['total_searched']}")
            print(f"  • 符合条件: {stats['qualified_projects']}")
            print(f"  • 不符合条件: {stats['rejected_projects']}")
            print(f"  • 分析错误: {stats['error_projects']}")

            if stats["qualified_projects"] > 0:
                print(f"\n🎉 找到 {stats['qualified_projects']} 个符合条件的项目!")
            else:
                print("\n😔 未找到符合条件的项目")

            return 0

        finally:
            # 清理资源
            searcher.close()

    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断操作")
        return 130

    except ValueError as e:
        print(f"\n❌ 参数错误: {e}")
        return 1

    except GitHubAPIError as e:
        print(f"\n❌ GitHub API错误: {e}")
        if args.verbose:
            print(f"   状态码: {e.status_code}")
            print(f"   响应数据: {e.response_data}")
        return 2

    except AnalysisError as e:
        print(f"\n❌ 分析错误: {e}")
        if args.verbose:
            print(f"   文件路径: {e.file_path}")
            print(f"   行号: {e.line_number}")
        return 3

    except Exception as e:
        print(f"\n❌ 未预期的错误: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 4


if __name__ == "__main__":
    sys.exit(main())
