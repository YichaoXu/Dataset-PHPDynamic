"""
项目配置设置

本模块定义了项目的所有配置常量和设置。
"""

import os
from pathlib import Path
from typing import Dict, List, Optional


class Settings:
    """项目配置设置类"""

    # 项目基本信息
    PROJECT_NAME = "PHPIncludes"
    PROJECT_VERSION = "1.0.0"
    PROJECT_DESCRIPTION = "PHP项目动态include/require检测工具"

    # GitHub API配置
    GITHUB_API_BASE_URL = "https://api.github.com"
    GITHUB_API_TOKEN_ENV = "GITHUB_TOKEN"
    GITHUB_API_DEFAULT_TOKEN = ""  # 从环境变量获取

    # 搜索配置
    DEFAULT_MAX_PROJECTS = 100
    DEFAULT_MAX_FILES_PER_PROJECT = 10
    DEFAULT_SEARCH_DELAY = 0.5  # 秒

    # 缓存配置
    CACHE_DB_PATH = "data/cache/github_cache.db"
    CACHE_DEFAULT_EXPIRE = 3600  # 1小时
    CACHE_CLEANUP_INTERVAL = 86400  # 24小时

    # 速率限制配置
    DEFAULT_REQUEST_DELAY = 1.0  # 秒
    RATE_LIMIT_WAIT_THRESHOLD = 3600  # 1小时

    # Semgrep配置
    SEMGREP_RULES_FILE = "config/semgrep_rules.yml"
    SEMGREP_TIMEOUT = 30  # 秒
    SEMGREP_VALIDATION_TIMEOUT = 10  # 秒

    # PHP分析配置
    PHP_FILE_EXTENSIONS = [".php", ".phtml", ".php3", ".php4", ".php5"]
    CONTEXT_LINES = 3  # 代码上下文行数

    # CSV导出配置
    OUTPUT_DIR = "data/output"
    CSV_ENCODING = "utf-8"
    CSV_DELIMITER = ","

    # 日志配置
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 默认搜索查询
    DEFAULT_SEARCH_QUERIES = [
        "call_user_func",
        "call_user_func_array",
        "forward_static_call",
        "forward_static_call_array",
        "include $_GET",
        "include $_POST",
        "require $_GET",
        "require $_POST",
    ]

    @classmethod
    def get_github_token(cls) -> str:
        """
        获取GitHub API令牌

        Returns:
            GitHub API令牌
        """
        token = os.getenv(cls.GITHUB_API_TOKEN_ENV)
        if not token:
            raise ValueError(
                f"GitHub API token not found. Please set {cls.GITHUB_API_TOKEN_ENV} environment variable."
            )
        return token

    @classmethod
    def get_cache_db_path(cls) -> str:
        """
        获取缓存数据库路径

        Returns:
            缓存数据库路径
        """
        path = Path(cls.CACHE_DB_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    @classmethod
    def get_output_dir(cls) -> str:
        """
        获取输出目录路径

        Returns:
            输出目录路径
        """
        path = Path(cls.OUTPUT_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @classmethod
    def get_semgrep_rules_path(cls) -> str:
        """
        获取Semgrep规则文件路径

        Returns:
            Semgrep规则文件路径
        """
        return cls.SEMGREP_RULES_FILE

    @classmethod
    def validate_config(cls) -> Dict[str, bool]:
        """
        验证配置

        Returns:
            配置验证结果
        """
        results = {}

        # 检查GitHub令牌
        try:
            cls.get_github_token()
            results["github_token"] = True
        except ValueError:
            results["github_token"] = False

        # 检查缓存目录
        try:
            cls.get_cache_db_path()
            results["cache_dir"] = True
        except Exception:
            results["cache_dir"] = False

        # 检查输出目录
        try:
            cls.get_output_dir()
            results["output_dir"] = True
        except Exception:
            results["output_dir"] = False

        # 检查Semgrep规则文件
        rules_path = Path(cls.get_semgrep_rules_path())
        results["semgrep_rules"] = rules_path.exists()

        return results

    @classmethod
    def get_search_queries(
        cls, custom_queries: Optional[List[str]] = None
    ) -> List[str]:
        """
        获取搜索查询列表

        Args:
            custom_queries: 自定义查询列表

        Returns:
            搜索查询列表
        """
        if custom_queries:
            return custom_queries
        return cls.DEFAULT_SEARCH_QUERIES.copy()

    @classmethod
    def get_php_file_extensions(cls) -> List[str]:
        """
        获取PHP文件扩展名列表

        Returns:
            PHP文件扩展名列表
        """
        return cls.PHP_FILE_EXTENSIONS.copy()

    @classmethod
    def is_php_file(cls, filename: str) -> bool:
        """
        判断是否为PHP文件

        Args:
            filename: 文件名

        Returns:
            是否为PHP文件
        """
        return any(filename.endswith(ext) for ext in cls.PHP_FILE_EXTENSIONS)

    @classmethod
    def get_project_info(cls) -> Dict[str, str]:
        """
        获取项目信息

        Returns:
            项目信息字典
        """
        return {
            "name": cls.PROJECT_NAME,
            "version": cls.PROJECT_VERSION,
            "description": cls.PROJECT_DESCRIPTION,
        }

    @classmethod
    def get_api_config(cls) -> Dict[str, any]:
        """
        获取API配置

        Returns:
            API配置字典
        """
        return {
            "base_url": cls.GITHUB_API_BASE_URL,
            "token_env": cls.GITHUB_API_TOKEN_ENV,
            "max_projects": cls.DEFAULT_MAX_PROJECTS,
            "max_files_per_project": cls.DEFAULT_MAX_FILES_PER_PROJECT,
            "search_delay": cls.DEFAULT_SEARCH_DELAY,
        }

    @classmethod
    def get_cache_config(cls) -> Dict[str, any]:
        """
        获取缓存配置

        Returns:
            缓存配置字典
        """
        return {
            "db_path": cls.get_cache_db_path(),
            "default_expire": cls.CACHE_DEFAULT_EXPIRE,
            "cleanup_interval": cls.CACHE_CLEANUP_INTERVAL,
        }

    @classmethod
    def get_rate_limit_config(cls) -> Dict[str, any]:
        """
        获取速率限制配置

        Returns:
            速率限制配置字典
        """
        return {
            "request_delay": cls.DEFAULT_REQUEST_DELAY,
            "wait_threshold": cls.RATE_LIMIT_WAIT_THRESHOLD,
        }

    @classmethod
    def get_semgrep_config(cls) -> Dict[str, any]:
        """
        获取Semgrep配置

        Returns:
            Semgrep配置字典
        """
        return {
            "rules_file": cls.get_semgrep_rules_path(),
            "timeout": cls.SEMGREP_TIMEOUT,
            "validation_timeout": cls.SEMGREP_VALIDATION_TIMEOUT,
        }

    @classmethod
    def get_analysis_config(cls) -> Dict[str, any]:
        """
        获取分析配置

        Returns:
            分析配置字典
        """
        return {
            "php_extensions": cls.get_php_file_extensions(),
            "context_lines": cls.CONTEXT_LINES,
            "max_files_per_project": cls.DEFAULT_MAX_FILES_PER_PROJECT,
        }

    @classmethod
    def get_export_config(cls) -> Dict[str, any]:
        """
        获取导出配置

        Returns:
            导出配置字典
        """
        return {
            "output_dir": cls.get_output_dir(),
            "encoding": cls.CSV_ENCODING,
            "delimiter": cls.CSV_DELIMITER,
        }
