"""
Configuration Settings Loader

This module loads and formats configuration data from config.yml file.
All configuration values come from config.yml - this file only handles
loading, parsing, and formatting.

If config.yml does not exist, the user should copy config.yml.example to config.yml.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment, unused-ignore]


class Settings:
    """Configuration settings loader class"""

    # Configuration file paths (relative to project root)
    CONFIG_FILE_PATH = Path(__file__).parent.parent / "config.yml"
    CONFIG_FILE_EXAMPLE_PATH = Path(__file__).parent.parent / "config.yml.example"
    CONFIG_FILE_ENV = "PHP_DYNCTRLFLOW_CONFIG"

    # Project basic information (not configurable)
    PROJECT_NAME = "Dataset-PHPDynCtrlflow"
    PROJECT_VERSION = "1.0.0"
    PROJECT_DESCRIPTION = "PHP Project Dataset Generator - Generates downloadable datasets of PHP projects with dynamic control flow characteristics"


    # Configuration cache
    _config_cache: Optional[Dict[str, Any]] = None

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
    def _load_config_file(cls) -> Dict[str, Any]:
        """
        Load configuration from YAML file

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config.yml does not exist
            ImportError: If PyYAML is not installed
            ValueError: If config file is invalid
        """
        if cls._config_cache is not None:
            return cls._config_cache

        config_path = cls._get_config_file_path()
        
        # Check if config file exists
        if not config_path.exists():
            example_path = cls.CONFIG_FILE_EXAMPLE_PATH
            if example_path.exists():
                raise FileNotFoundError(
                    f"Configuration file {config_path} not found.\n"
                    f"Please copy {example_path} to {config_path} and configure it.\n"
                    f"Example: cp {example_path} {config_path}"
                )
            else:
                raise FileNotFoundError(
                    f"Configuration file {config_path} not found.\n"
                    f"Please create config.yml with your configuration."
                )

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
    def _get_config_value(cls, path: str) -> Any:
        """
        Get configuration value by path (e.g., "github.api_token")

        Args:
            path: Configuration path (dot-separated)

        Returns:
            Configuration value

        Raises:
            KeyError: If configuration path does not exist
        """
        config = cls._load_config_file()
        keys = path.split(".")
        value: Any = config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    raise KeyError(
                        f"Configuration path '{path}' not found in config.yml. "
                        f"Please add it to your configuration file."
                    )
            else:
                raise KeyError(
                    f"Configuration path '{path}' is invalid. "
                    f"Intermediate value is not a dictionary."
                )
        return value

    @classmethod
    def get_github_token(cls) -> str:
        """
        Get GitHub API token from config file

        Returns:
            GitHub API token

        Raises:
            ValueError: Token not found in config file
        """
        try:
            token = cls._get_config_value("github.api_token")
            if token:
                return str(token)
        except KeyError:
            pass

        raise ValueError(
            f"GitHub API token not found in config.yml (github.api_token). "
            f"Please set it in your configuration file."
        )

    @classmethod
    def get_github_base_url(cls) -> str:
        """
        Get GitHub API base URL

        Returns:
            GitHub API base URL
        """
        try:
            return str(cls._get_config_value("github.base_url"))
        except KeyError:
            return "https://api.github.com"

    @classmethod
    def get_cache_db_path(cls) -> str:
        """
        Get cache database path

        Returns:
            Cache database path
        """
        path_str = str(cls._get_config_value("cache.db_path"))
        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    @classmethod
    def get_cache_default_expire(cls) -> int:
        """
        Get cache default expiration time

        Returns:
            Cache expiration time in seconds
        """
        return int(cls._get_config_value("cache.default_expire"))

    @classmethod
    def get_cache_cleanup_interval(cls) -> int:
        """
        Get cache cleanup interval

        Returns:
            Cleanup interval in seconds
        """
        return int(cls._get_config_value("cache.cleanup_interval"))

    @classmethod
    def get_output_dir(cls) -> str:
        """
        Get output directory path

        Returns:
            Output directory path
        """
        path_str = str(cls._get_config_value("output.output_dir"))
        path = Path(path_str)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @classmethod
    def get_output_encoding(cls) -> str:
        """
        Get output encoding

        Returns:
            Output encoding
        """
        return str(cls._get_config_value("output.encoding"))

    @classmethod
    def get_output_delimiter(cls) -> str:
        """
        Get output delimiter

        Returns:
            Output delimiter
        """
        return str(cls._get_config_value("output.delimiter"))

    @classmethod
    def get_semgrep_rules_path(cls) -> str:
        """
        Get Semgrep rules file path

        Returns:
            Semgrep rules file path
        """
        return str(cls._get_config_value("semgrep.rules_file"))

    @classmethod
    def get_semgrep_timeout(cls) -> int:
        """
        Get Semgrep execution timeout

        Returns:
            Timeout in seconds
        """
        return int(cls._get_config_value("semgrep.timeout"))

    @classmethod
    def get_semgrep_validation_timeout(cls) -> int:
        """
        Get Semgrep validation timeout

        Returns:
            Timeout in seconds
        """
        return int(cls._get_config_value("semgrep.validation_timeout"))

    @classmethod
    def get_max_projects(cls) -> int:
        """
        Get maximum number of projects to search

        Returns:
            Maximum number of projects
        """
        return int(cls._get_config_value("search.max_projects"))

    @classmethod
    def get_max_files_per_project(cls) -> int:
        """
        Get maximum number of files per project

        Returns:
            Maximum number of files per project
        """
        return int(cls._get_config_value("search.max_files_per_project"))

    @classmethod
    def get_batch_size(cls) -> int:
        """
        Get batch size for streaming batch processing

        Returns:
            Batch size (default: 100)
        """
        try:
            return int(cls._get_config_value("search.batch_size"))
        except (KeyError, ValueError):
            # Default batch size if not configured
            return 100

    @classmethod
    def get_request_delay(cls) -> float:
        """
        Get request delay between API calls

        Returns:
            Request delay in seconds
        """
        return float(cls._get_config_value("rate_limit.request_delay"))

    @classmethod
    def get_rate_limit_wait_threshold(cls) -> int:
        """
        Get rate limit wait threshold

        Returns:
            Wait threshold in seconds
        """
        return int(cls._get_config_value("rate_limit.wait_threshold"))

    @classmethod
    def get_php_file_extensions(cls) -> List[str]:
        """
        Get PHP file extensions list

        Returns:
            PHP file extensions list
        """
        extensions = cls._get_config_value("php_analysis.file_extensions")
        if isinstance(extensions, list):
            return [str(ext) for ext in extensions]
        return []

    @classmethod
    def get_php_context_lines(cls) -> int:
        """
        Get PHP analysis context lines

        Returns:
            Number of context lines
        """
        return int(cls._get_config_value("php_analysis.context_lines"))

    @classmethod
    def is_php_file(cls, filename: str) -> bool:
        """
        Check if file is PHP file

        Args:
            filename: File name

        Returns:
            Whether file is PHP file
        """
        extensions = cls.get_php_file_extensions()
        return any(filename.endswith(ext) for ext in extensions)

    @classmethod
    def get_log_level(cls) -> str:
        """
        Get log level

        Returns:
            Log level
        """
        return str(cls._get_config_value("logging.log_level"))

    @classmethod
    def get_log_format(cls) -> str:
        """
        Get log format

        Returns:
            Log format string
        """
        return str(cls._get_config_value("logging.log_format"))

    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """
        Validate configuration

        Returns:
            Configuration validation results (dict with bool values and optional error messages)
        """
        results: Dict[str, Any] = {}

        # Check if config file exists
        try:
            cls._load_config_file()
            results["config_file"] = True
        except (FileNotFoundError, ValueError) as e:
            results["config_file"] = False
            results["config_file_error"] = str(e)

        # Check GitHub token
        try:
            cls.get_github_token()
            results["github_token"] = True
        except (ValueError, KeyError):
            results["github_token"] = False

        # Check cache directory
        try:
            cls.get_cache_db_path()
            results["cache_dir"] = True
        except (KeyError, Exception):
            results["cache_dir"] = False

        # Check output directory
        try:
            cls.get_output_dir()
            results["output_dir"] = True
        except (KeyError, Exception):
            results["output_dir"] = False

        # Check Semgrep rules file
        try:
            rules_path = Path(cls.get_semgrep_rules_path())
            results["semgrep_rules"] = rules_path.exists()
        except (KeyError, Exception):
            results["semgrep_rules"] = False

        return results

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

    # Legacy methods for backward compatibility (will be removed if not used)
    @classmethod
    def get_api_config(cls) -> Dict[str, Any]:
        """
        Get API configuration

        Returns:
            API configuration dictionary
        """
        return {
            "base_url": cls.get_github_base_url(),
            "max_projects": cls.get_max_projects(),
            "max_files_per_project": cls.get_max_files_per_project(),
        }

    @classmethod
    def get_cache_config(cls) -> Dict[str, Any]:
        """
        Get cache configuration

        Returns:
            Cache configuration dictionary
        """
        return {
            "db_path": cls.get_cache_db_path(),
            "default_expire": cls.get_cache_default_expire(),
            "cleanup_interval": cls.get_cache_cleanup_interval(),
        }

    @classmethod
    def get_rate_limit_config(cls) -> Dict[str, Any]:
        """
        Get rate limiting configuration

        Returns:
            Rate limiting configuration dictionary
        """
        return {
            "request_delay": cls.get_request_delay(),
            "wait_threshold": cls.get_rate_limit_wait_threshold(),
        }

    @classmethod
    def get_semgrep_config(cls) -> Dict[str, Any]:
        """
        Get Semgrep configuration

        Returns:
            Semgrep configuration dictionary
        """
        return {
            "rules_file": cls.get_semgrep_rules_path(),
            "timeout": cls.get_semgrep_timeout(),
            "validation_timeout": cls.get_semgrep_validation_timeout(),
        }

    @classmethod
    def get_analysis_config(cls) -> Dict[str, Any]:
        """
        Get analysis configuration

        Returns:
            Analysis configuration dictionary
        """
        return {
            "php_extensions": cls.get_php_file_extensions(),
            "context_lines": cls.get_php_context_lines(),
            "max_files_per_project": cls.get_max_files_per_project(),
        }

    @classmethod
    def get_export_config(cls) -> Dict[str, Any]:
        """
        Get export configuration

        Returns:
            Export configuration dictionary
        """
        return {
            "output_dir": cls.get_output_dir(),
            "encoding": cls.get_output_encoding(),
            "delimiter": cls.get_output_delimiter(),
        }
