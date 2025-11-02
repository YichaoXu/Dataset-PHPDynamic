"""
Cache Manager

This module provides SQLite-based caching functionality for storing GitHub API request results.
"""

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .exceptions import CacheError


class CacheManager:
    """Manages caching of API requests to avoid duplicate queries"""

    def __init__(
        self, db_path: str = "data/cache/github_cache.db", expire_after: int = 3600
    ) -> None:
        """
        Initialize cache manager

        Args:
            db_path: SQLite database file path
            expire_after: Cache expiration time in seconds
        """
        self.db_path = Path(db_path)
        self.expire_after = expire_after

        # Ensure cache directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

    def _init_database(self) -> None:
        """Initialize database table"""
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
        Get data from cache

        Args:
            key: Cache key

        Returns:
            Cache data or None (if not exists or expired)

        Raises:
            CacheError: Cache read failed
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

                # Check if expired
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
        Store data to cache

        Args:
            key: Cache key
            value: Data to cache
            expire_after: Expiration time in seconds, None uses default

        Raises:
            CacheError: Cache write failed
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
        Delete data from cache

        Args:
            key: Cache key

        Raises:
            CacheError: Cache delete failed
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
        Clear all cache

        Raises:
            CacheError: Cache clear failed
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache")
        except sqlite3.Error as e:
            raise CacheError(f"Failed to clear cache: {e}", "clear")

    def cleanup_expired(self) -> int:
        """
        Clean up expired cache entries

        Returns:
            Number of deleted entries

        Raises:
            CacheError: Clean up failed
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
        Generate cache key

        Args:
            url: API URL
            params: Query parameters

        Returns:
            Cache key string
        """
        key_data: Dict[str, Any] = {"url": url}
        if params:
            key_data["params"] = sorted(params.items())

        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get_stats(self) -> dict:
        """
        Get cache statistics

        Returns:
            Dictionary containing cache statistics
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
