#!/usr/bin/env python3
"""
分析运行脚本

本脚本提供高级的分析运行功能，包括配置加载、进度报告、错误处理和日志记录。
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config.settings import Settings
from src.project_searcher import ProjectSearcher


class AnalysisRunner:
    """分析运行器"""

    def __init__(self, config_file: Optional[str] = None) -> None:
        """
        初始化分析运行器

        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config()
        self.logger = self._setup_logging()
        self.start_time = None
        self.end_time = None

    def _load_config(self) -> Dict:
        """
        加载配置文件

        Returns:
            配置字典
        """
        if self.config_file and Path(self.config_file).exists():
            try:
                with open(self.config_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 配置文件加载失败: {e}")
                return {}
        return {}

    def _setup_logging(self) -> logging.Logger:
        """
        设置日志记录

        Returns:
            日志记录器
        """
        logger = logging.getLogger("PHPIncludes")
        logger.setLevel(logging.INFO)

        # 创建文件处理器
        log_file = (
            Path("data/output")
            / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 设置格式
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加处理器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def run_analysis(
        self,
        queries: Optional[List[str]] = None,
        max_projects: Optional[int] = None,
        output_dir: Optional[str] = None,
        include_unqualified: bool = False,
        verbose: bool = False,
    ) -> bool:
        """
        运行分析

        Args:
            queries: 搜索查询列表
            max_projects: 最大项目数量
            output_dir: 输出目录
            include_unqualified: 是否包含不符合条件的项目
            verbose: 详细输出

        Returns:
            分析是否成功
        """
        self.start_time = datetime.now()
        self.logger.info("开始PHP项目分析")

        try:
            # 获取配置
            github_token = self._get_github_token()
            search_queries = queries or self.config.get(
                "queries", Settings.DEFAULT_SEARCH_QUERIES
            )
            max_proj = max_projects or self.config.get(
                "max_projects", Settings.DEFAULT_MAX_PROJECTS
            )
            output_path = output_dir or self.config.get(
                "output_dir", Settings.OUTPUT_DIR
            )

            # 记录配置
            self.logger.info("配置信息:")
            self.logger.info(f"  • 搜索查询: {len(search_queries)} 个")
            self.logger.info(f"  • 最大项目数: {max_proj}")
            self.logger.info(f"  • 输出目录: {output_path}")
            self.logger.info(f"  • 包含不符合条件项目: {include_unqualified}")

            # 创建项目搜索器
            searcher = ProjectSearcher(github_token)

            try:
                # 执行搜索
                self.logger.info("开始搜索和分析项目...")
                results = searcher.search_projects(
                    search_queries=search_queries,
                    max_projects=max_proj,
                    export_csv=True,
                    include_unqualified=include_unqualified,
                )

                # 记录结果
                stats = searcher.get_search_statistics()
                self.logger.info("分析完成:")
                self.logger.info(f"  • 总项目数: {stats['total_searched']}")
                self.logger.info(f"  • 符合条件: {stats['qualified_projects']}")
                self.logger.info(f"  • 不符合条件: {stats['rejected_projects']}")
                self.logger.info(f"  • 分析错误: {stats['error_projects']}")

                # 详细结果记录
                if verbose and results:
                    self.logger.info("详细结果:")
                    for i, result in enumerate(results[:10], 1):  # 只记录前10个
                        self.logger.info(
                            f"  {i}. {result.project_name} - {result.detection_type}"
                        )

                # 保存分析报告
                self._save_analysis_report(stats, results)

                return True

            finally:
                searcher.close()

        except Exception as e:
            self.logger.error(f"分析失败: {e}")
            if verbose:
                import traceback

                self.logger.error(traceback.format_exc())
            return False

        finally:
            self.end_time = datetime.now()
            if self.start_time:
                duration = self.end_time - self.start_time
                self.logger.info(f"总耗时: {duration.total_seconds():.2f} 秒")

    def _get_github_token(self) -> str:
        """
        获取GitHub令牌

        Returns:
            GitHub API令牌

        Raises:
            ValueError: 令牌未找到
        """
        # 从配置文件获取
        token = self.config.get("github_token")
        if token:
            return token

        # 从环境变量获取
        try:
            return Settings.get_github_token()
        except ValueError as e:
            raise ValueError(
                f"{e}\n"
                f"请在配置文件中设置 'github_token' 或设置 {Settings.GITHUB_API_TOKEN_ENV} 环境变量"
            ) from e

    def _save_analysis_report(self, stats: Dict, results: List) -> None:
        """
        保存分析报告

        Args:
            stats: 统计信息
            results: 搜索结果
        """
        try:
            report_file = (
                Path("data/output")
                / f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

            report = {
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": (
                    (self.end_time - self.start_time).total_seconds()
                    if self.start_time and self.end_time
                    else None
                ),
                "statistics": stats,
                "results_summary": [
                    {
                        "project_name": result.project_name,
                        "detection_type": result.detection_type,
                        "is_qualified": result.is_qualified,
                        "priority": result.priority,
                    }
                    for result in results
                ],
                "configuration": {
                    "queries": self.config.get(
                        "queries", Settings.DEFAULT_SEARCH_QUERIES
                    ),
                    "max_projects": self.config.get(
                        "max_projects", Settings.DEFAULT_MAX_PROJECTS
                    ),
                    "output_dir": self.config.get("output_dir", Settings.OUTPUT_DIR),
                },
            }

            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            self.logger.info(f"分析报告已保存: {report_file}")

        except Exception as e:
            self.logger.warning(f"保存分析报告失败: {e}")

    def create_sample_config(self, output_file: str = "analysis_config.json") -> None:
        """
        创建示例配置文件

        Args:
            output_file: 输出文件路径
        """
        sample_config = {
            "github_token": "your_github_token_here",
            "queries": [
                "call_user_func",
                "call_user_func_array",
                "forward_static_call",
                "forward_static_call_array",
                "include $_GET",
                "include $_POST",
                "require $_GET",
                "require $_POST",
            ],
            "max_projects": 100,
            "output_dir": "data/output",
            "include_unqualified": False,
            "verbose": False,
        }

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(sample_config, f, indent=2, ensure_ascii=False)

            print(f"✅ 示例配置文件已创建: {output_file}")
            print("请编辑配置文件并设置您的GitHub令牌")

        except Exception as e:
            print(f"❌ 创建配置文件失败: {e}")


def create_argument_parser() -> argparse.ArgumentParser:
    """
    创建命令行参数解析器

    Returns:
        参数解析器
    """
    parser = argparse.ArgumentParser(
        description="PHPIncludes 高级分析运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python scripts/run_analysis.py --config analysis_config.json
  python scripts/run_analysis.py --queries "call_user_func" "include $_GET" --max-projects 50
  python scripts/run_analysis.py --create-config
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径",
    )

    parser.add_argument(
        "--queries",
        nargs="+",
        help="搜索查询列表",
    )

    parser.add_argument(
        "--max-projects",
        type=int,
        help="最大项目数量",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        help="输出目录",
    )

    parser.add_argument(
        "--include-unqualified",
        action="store_true",
        help="包含不符合条件的项目",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="详细输出",
    )

    parser.add_argument(
        "--create-config",
        action="store_true",
        help="创建示例配置文件",
    )

    return parser


def main() -> int:
    """
    主函数

    Returns:
        退出码
    """
    parser = create_argument_parser()
    args = parser.parse_args()

    # 创建示例配置文件
    if args.create_config:
        runner = AnalysisRunner()
        runner.create_sample_config()
        return 0

    try:
        # 创建分析运行器
        runner = AnalysisRunner(config_file=args.config)

        # 运行分析
        success = runner.run_analysis(
            queries=args.queries,
            max_projects=args.max_projects,
            output_dir=args.output_dir,
            include_unqualified=args.include_unqualified,
            verbose=args.verbose,
        )

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n⏹️ 用户中断操作")
        return 130

    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        return 1

    except Exception as e:
        print(f"❌ 未预期的错误: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 4


if __name__ == "__main__":
    sys.exit(main())
