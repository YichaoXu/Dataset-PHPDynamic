"""
Project Configuration Settings

This module defines all configuration constants and settings for the project.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


class Settings:
    """Project configuration settings class"""

    # Configuration file path
    CONFIG_FILE_PATH = Path("config/config.yml")
    CONFIG_FILE_ENV = "PHPINCLUDES_CONFIG"

    # Project basic information
    PROJECT_NAME = "PHPIncludes"
    PROJECT_VERSION = "1.0.0"
    PROJECT_DESCRIPTION = "PHP Project Dynamic Include/Require Detection Tool"

    # Configuration cache
    _config_cache: Optional[Dict[str, Any]] = None

    # GitHub API configuration
    GITHUB_API_BASE_URL = "https://api.github.com"
    GITHUB_API_TOKEN_ENV = "GITHUB_TOKEN"
    GITHUB_API_DEFAULT_TOKEN = ""  # Get from environment variable or config file

    # Search configuration
    DEFAULT_MAX_PROJECTS = 1000  # Increased to 1000 as suggested
    DEFAULT_MAX_FILES_PER_PROJECT = 10
    DEFAULT_SEARCH_DELAY = 0.5  # seconds

    # Language filtering
    DEFAULT_LANGUAGE = "PHP"  # Filter by PHP language
    LANGUAGE_ALIASES = ["PHP", "php", "Php"]  # Support different cases

    # Cache configuration
    CACHE_DB_PATH = "data/cache/github_cache.db"
    CACHE_DEFAULT_EXPIRE = 3600  # 1 hour
    CACHE_CLEANUP_INTERVAL = 86400  # 24 hours

    # Rate limiting configuration
    DEFAULT_REQUEST_DELAY = 1.0  # seconds
    RATE_LIMIT_WAIT_THRESHOLD = 3600  # 1 hour

    # Semgrep configuration
    SEMGREP_RULES_FILE = "config/semgrep_rules.yml"
    SEMGREP_TIMEOUT = 30  # seconds
    SEMGREP_VALIDATION_TIMEOUT = 10  # seconds

    # PHP analysis configuration
    PHP_FILE_EXTENSIONS = [".php", ".phtml", ".php3", ".php4", ".php5"]
    CONTEXT_LINES = 3  # Code context lines

    # CSV export configuration
    OUTPUT_DIR = "data/output"
    CSV_ENCODING = "utf-8"
    CSV_DELIMITER = ","

    # Logging configuration
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Default search queries with language filtering
    DEFAULT_SEARCH_QUERIES = [
        "call_user_func language:PHP",
        "call_user_func_array language:PHP",
        "forward_static_call language:PHP",
        "forward_static_call_array language:PHP",
        "include $_GET language:PHP",
        "include $_POST language:PHP",
        "require $_GET language:PHP",
        "require $_POST language:PHP",
    ]

    @classmethod
    def _load_config_file(cls) -> Dict[str, Any]:
        """
        Load configuration from YAML file

        Returns:
            Configuration dictionary
        """
        if cls._config_cache is not None:
            return cls._config_cache

        config_path = cls._get_config_file_path()
        if not config_path.exists():
            cls._config_cache = {}
            return cls._config_cache

        if yaml is None:
            raise ImportError(
                "PyYAML is required to load configuration files. "
                "Install it with: uv add pyyaml"
            )

        try:
            with open(config_path, encoding="utf-8") as f:
                cls._config_cache = yaml.safe_load(f) or {}
            return cls._config_cache
        except Exception as e:
            raise ValueError(
                f"Failed to load configuration file {config_path}: {e}"
            ) from e

    @classmethod
    def _get_config_file_path(cls) -> Path:
        """
        Get configuration file path

        Returns:
            Configuration file path
        """
        # Check environment variable first
        env_path = os.getenv(cls.CONFIG_FILE_ENV)
        if env_path:
            return Path(env_path)

        # Use default path
        return cls.CONFIG_FILE_PATH

    @classmethod
    def _get_config_value(cls, path: str, default: Any = None) -> Any:
        """
        Get configuration value by path (e.g., "github.api_token")

        Args:
            path: Configuration path (dot-separated)
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        try:
            config = cls._load_config_file()
            keys = path.split(".")
            value = config
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                    if value is None:
                        return default
                else:
                    return default
            return value if value is not None else default
        except Exception:
            return default

    @classmethod
    def get_github_token(cls) -> str:
        """
        Get GitHub API token
        Priority: config file > environment variable

        Returns:
            GitHub API token

        Raises:
            ValueError: Token not found
        """
        # 1. Try config file first
        token = cls._get_config_value("github.api_token")
        if token:
            return str(token)

        # 2. Try environment variable
        token = os.getenv(cls.GITHUB_API_TOKEN_ENV)
        if token:
            return token

        # 3. Raise error if not found
        raise ValueError(
            f"GitHub API token not found. "
            f"Please set it in config/config.yml (github.api_token) or "
            f"set {cls.GITHUB_API_TOKEN_ENV} environment variable."
        )

    @classmethod
    def get_cache_db_path(cls) -> str:
        """
        Get cache database path
        Priority: config file > default

        Returns:
            Cache database path
        """
        path_str = cls._get_config_value("cache.db_path", cls.CACHE_DB_PATH)
        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    @classmethod
    def get_output_dir(cls) -> str:
        """
        Get output directory path
        Priority: config file > default

        Returns:
            Output directory path
        """
        path_str = cls._get_config_value("output.output_dir", cls.OUTPUT_DIR)
        path = Path(path_str)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @classmethod
    def get_semgrep_rules_path(cls) -> str:
        """
        Get Semgrep rules file path
        Priority: config file > default

        Returns:
            Semgrep rules file path
        """
        return str(cls._get_config_value("semgrep.rules_file", cls.SEMGREP_RULES_FILE))

    @classmethod
    def validate_config(cls) -> Dict[str, bool]:
        """
        Validate configuration

        Returns:
            Configuration validation results
        """
        results = {}

        # Check GitHub token
        try:
            cls.get_github_token()
            results["github_token"] = True
        except ValueError:
            results["github_token"] = False

        # Check cache directory
        try:
            cls.get_cache_db_path()
            results["cache_dir"] = True
        except Exception:
            results["cache_dir"] = False

        # Check output directory
        try:
            cls.get_output_dir()
            results["output_dir"] = True
        except Exception:
            results["output_dir"] = False

        # Check Semgrep rules file
        rules_path = Path(cls.get_semgrep_rules_path())
        results["semgrep_rules"] = rules_path.exists()

        return results

    @classmethod
    def get_max_projects(cls) -> int:
        """
        Get maximum number of projects to search
        Priority: config file > default

        Returns:
            Maximum number of projects
        """
        return int(
            cls._get_config_value("search.max_projects", cls.DEFAULT_MAX_PROJECTS)
        )

    @classmethod
    def get_max_files_per_project(cls) -> int:
        """
        Get maximum number of files per project
        Priority: config file > default

        Returns:
            Maximum number of files per project
        """
        return int(
            cls._get_config_value(
                "search.max_files_per_project", cls.DEFAULT_MAX_FILES_PER_PROJECT
            )
        )

    @classmethod
    def get_search_delay(cls) -> float:
        """
        Get search delay between requests
        Priority: config file > default

        Returns:
            Search delay in seconds
        """
        return float(
            cls._get_config_value("search.search_delay", cls.DEFAULT_SEARCH_DELAY)
        )

    @classmethod
    def get_request_delay(cls) -> float:
        """
        Get request delay between API calls
        Priority: config file > default

        Returns:
            Request delay in seconds
        """
        return float(
            cls._get_config_value("rate_limit.request_delay", cls.DEFAULT_REQUEST_DELAY)
        )

    @classmethod
    def get_language_filter(cls) -> str:
        """
        Get language filter for GitHub search
        Priority: config file > default

        Returns:
            Language filter string
        """
        return str(
            cls._get_config_value("search.default_language", cls.DEFAULT_LANGUAGE)
        )

    @classmethod
    def get_search_queries(
        cls, custom_queries: Optional[List[str]] = None, language: Optional[str] = None
    ) -> List[str]:
        """
        Get search query list with optional language filtering
        Priority: custom_queries > config file > default

        Args:
            custom_queries: Custom query list
            language: Language filter (e.g., "PHP", "php")

        Returns:
            Search query list with language filtering
        """
        # 1. Use custom queries if provided
        if custom_queries:
            lang_filter = language or cls.get_language_filter()
            filtered_queries = []
            for query in custom_queries:
                if "language:" not in query.lower():
                    filtered_queries.append(f"{query} language:{lang_filter}")
                else:
                    filtered_queries.append(query)
            return filtered_queries

        # 2. Try config file
        config_queries = cls._get_config_value("search.custom_queries")
        if config_queries and isinstance(config_queries, list):
            lang_filter = language or cls.get_language_filter()
            filtered_queries = []
            for query in config_queries:
                query_str = str(query)
                if "language:" not in query_str.lower():
                    filtered_queries.append(f"{query_str} language:{lang_filter}")
                else:
                    filtered_queries.append(query_str)
            return filtered_queries

        # 3. Use default queries with language filtering
        lang_filter = language or cls.get_language_filter()
        return [
            query.replace("language:PHP", f"language:{lang_filter}")
            for query in cls.DEFAULT_SEARCH_QUERIES
        ]

    @classmethod
    def get_php_file_extensions(cls) -> List[str]:
        """
        Get PHP file extensions list

        Returns:
            PHP file extensions list
        """
        return cls.PHP_FILE_EXTENSIONS.copy()

    @classmethod
    def is_php_file(cls, filename: str) -> bool:
        """
        Check if file is PHP file

        Args:
            filename: File name

        Returns:
            Whether file is PHP file
        """
        return any(filename.endswith(ext) for ext in cls.PHP_FILE_EXTENSIONS)

    @classmethod
    def get_project_info(cls) -> Dict[str, str]:
        """
        Get project information

        Returns:
            Project information dictionary
        """
        return {
            "name": cls.PROJECT_NAME,
            "version": cls.PROJECT_VERSION,
            "description": cls.PROJECT_DESCRIPTION,
        }

    @classmethod
    def get_api_config(cls) -> Dict[str, any]:
        """
        Get API configuration

        Returns:
            API configuration dictionary
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
        Get cache configuration

        Returns:
            Cache configuration dictionary
        """
        return {
            "db_path": cls.get_cache_db_path(),
            "default_expire": cls.CACHE_DEFAULT_EXPIRE,
            "cleanup_interval": cls.CACHE_CLEANUP_INTERVAL,
        }

    @classmethod
    def get_rate_limit_config(cls) -> Dict[str, any]:
        """
        Get rate limiting configuration

        Returns:
            Rate limiting configuration dictionary
        """
        return {
            "request_delay": cls.DEFAULT_REQUEST_DELAY,
            "wait_threshold": cls.RATE_LIMIT_WAIT_THRESHOLD,
        }

    @classmethod
    def get_semgrep_config(cls) -> Dict[str, any]:
        """
        Get Semgrep configuration

        Returns:
            Semgrep configuration dictionary
        """
        return {
            "rules_file": cls.get_semgrep_rules_path(),
            "timeout": cls.SEMGREP_TIMEOUT,
            "validation_timeout": cls.SEMGREP_VALIDATION_TIMEOUT,
        }

    @classmethod
    def get_analysis_config(cls) -> Dict[str, any]:
        """
        Get analysis configuration

        Returns:
            Analysis configuration dictionary
        """
        return {
            "php_extensions": cls.get_php_file_extensions(),
            "context_lines": cls.CONTEXT_LINES,
            "max_files_per_project": cls.DEFAULT_MAX_FILES_PER_PROJECT,
        }

    @classmethod
    def get_export_config(cls) -> Dict[str, any]:
        """
        Get export configuration

        Returns:
            Export configuration dictionary
        """
        return {
            "output_dir": cls.get_output_dir(),
            "encoding": cls.CSV_ENCODING,
            "delimiter": cls.CSV_DELIMITER,
        }
