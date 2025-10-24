"""
缓存管理器

本模块提供基于SQLite的缓存功能，用于存储GitHub API请求结果。
"""

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .exceptions import CacheError


class CacheManager:
    """管理API请求的缓存，避免重复查询"""

    def __init__(
        self, db_path: str = "data/cache/github_cache.db", expire_after: int = 3600
    ) -> None:
        """
        初始化缓存管理器

        Args:
            db_path: SQLite数据库文件路径
            expire_after: 缓存过期时间（秒）
        """
        self.db_path = Path(db_path)
        self.expire_after = expire_after

        # 确保缓存目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

    def _init_database(self) -> None:
        """初始化数据库表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        expires_at REAL NOT NULL
                    )
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_expires_at 
                    ON cache(expires_at)
                """
                )
        except sqlite3.Error as e:
            raise CacheError(f"Failed to initialize cache database: {e}")

    def get(self, key: str) -> Optional[Any]:
        """
        从缓存中获取数据

        Args:
            key: 缓存键

        Returns:
            缓存的数据或None（如果不存在或已过期）

        Raises:
            CacheError: 缓存读取失败
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
                )
                row = cursor.fetchone()

                if row is None:
                    return None

                value, expires_at = row

                # 检查是否过期
                if time.time() > expires_at:
                    self.delete(key)
                    return None

                return json.loads(value)

        except (sqlite3.Error, json.JSONDecodeError) as e:
            raise CacheError(
                f"Failed to get cache value for key '{key}': {e}", "get", key
            )

    def set(self, key: str, value: Any, expire_after: Optional[int] = None) -> None:
        """
        将数据存储到缓存

        Args:
            key: 缓存键
            value: 要缓存的数据
            expire_after: 过期时间（秒），None使用默认值

        Raises:
            CacheError: 缓存写入失败
        """
        try:
            expire_time = expire_after or self.expire_after
            expires_at = time.time() + expire_time

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cache (key, value, created_at, expires_at)
                    VALUES (?, ?, ?, ?)
                """,
                    (key, json.dumps(value), time.time(), expires_at),
                )

        except (sqlite3.Error, json.JSONDecodeError) as e:
            raise CacheError(
                f"Failed to set cache value for key '{key}': {e}", "set", key
            )

    def delete(self, key: str) -> None:
        """
        从缓存中删除数据

        Args:
            key: 缓存键

        Raises:
            CacheError: 缓存删除失败
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        except sqlite3.Error as e:
            raise CacheError(
                f"Failed to delete cache value for key '{key}': {e}", "delete", key
            )

    def clear(self) -> None:
        """
        清空所有缓存

        Raises:
            CacheError: 缓存清空失败
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache")
        except sqlite3.Error as e:
            raise CacheError(f"Failed to clear cache: {e}", "clear")

    def cleanup_expired(self) -> int:
        """
        清理过期的缓存条目

        Returns:
            删除的条目数量

        Raises:
            CacheError: 清理失败
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM cache WHERE expires_at < ?", (time.time(),)
                )
                return cursor.rowcount
        except sqlite3.Error as e:
            raise CacheError(f"Failed to cleanup expired cache: {e}", "cleanup")

    def generate_cache_key(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成缓存键

        Args:
            url: API URL
            params: 查询参数

        Returns:
            缓存键字符串
        """
        key_data: Dict[str, Any] = {"url": url}
        if params:
            key_data["params"] = sorted(params.items())

        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get_stats(self) -> dict:
        """
        获取缓存统计信息

        Returns:
            包含缓存统计信息的字典
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM cache")
                total_count = cursor.fetchone()[0]

                cursor = conn.execute(
                    "SELECT COUNT(*) FROM cache WHERE expires_at > ?", (time.time(),)
                )
                active_count = cursor.fetchone()[0]

                return {
                    "total_entries": total_count,
                    "active_entries": active_count,
                    "expired_entries": total_count - active_count,
                    "db_path": str(self.db_path),
                }
        except sqlite3.Error as e:
            raise CacheError(f"Failed to get cache stats: {e}", "stats")
