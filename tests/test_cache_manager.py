"""
Cache Manager Tests

Tests for CacheManager class.
"""

import tempfile
import time
import unittest
from pathlib import Path

from php_dynctrlflow.cache_manager import CacheManager
from php_dynctrlflow.exceptions import CacheError


class TestCacheManager(unittest.TestCase):
    """Test CacheManager class"""

    def setUp(self) -> None:
        """Test setup"""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_cache.db"
        self.cache_manager = CacheManager(db_path=str(self.db_path), expire_after=3600)

    def tearDown(self) -> None:
        """Test cleanup"""
        # Close connections and remove temp files
        if hasattr(self, "cache_manager"):
            self.cache_manager.clear()
        if self.db_path.exists():
            self.db_path.unlink()
        Path(self.temp_dir).rmdir()

    def test_set_and_get(self) -> None:
        """Test set and get methods"""
        key = "test_key"
        value = {"test": "data"}

        # Set value
        self.cache_manager.set(key, value)

        # Get value
        result = self.cache_manager.get(key)
        self.assertEqual(result, value)

    def test_get_nonexistent_key(self) -> None:
        """Test getting nonexistent key"""
        result = self.cache_manager.get("nonexistent_key")
        self.assertIsNone(result)

    def test_get_expired_key(self) -> None:
        """Test getting expired key"""
        key = "expired_key"
        value = {"test": "data"}

        # Set value with short expiration
        self.cache_manager.set(key, value, expire_after=1)

        # Wait for expiration
        time.sleep(2)

        # Get expired value
        result = self.cache_manager.get(key)
        self.assertIsNone(result)

    def test_delete(self) -> None:
        """Test delete method"""
        key = "test_key"
        value = {"test": "data"}

        # Set value
        self.cache_manager.set(key, value)

        # Delete value
        self.cache_manager.delete(key)

        # Get deleted value
        result = self.cache_manager.get(key)
        self.assertIsNone(result)

    def test_clear(self) -> None:
        """Test clear method"""
        # Set multiple values
        for i in range(5):
            self.cache_manager.set(f"key_{i}", {"value": i})

        # Clear all
        self.cache_manager.clear()

        # Check all values are gone
        for i in range(5):
            result = self.cache_manager.get(f"key_{i}")
            self.assertIsNone(result)

    def test_generate_cache_key(self) -> None:
        """Test generate_cache_key method"""
        url = "https://api.github.com/test"
        params = {"param1": "value1", "param2": "value2"}

        key1 = self.cache_manager.generate_cache_key(url, params)
        key2 = self.cache_manager.generate_cache_key(url, params)

        # Same inputs should generate same key
        self.assertEqual(key1, key2)

        # Different params should generate different key
        key3 = self.cache_manager.generate_cache_key(url, {"param1": "different"})
        self.assertNotEqual(key1, key3)

    def test_generate_cache_key_no_params(self) -> None:
        """Test generate_cache_key method without params"""
        url = "https://api.github.com/test"

        key1 = self.cache_manager.generate_cache_key(url)
        key2 = self.cache_manager.generate_cache_key(url)

        # Same URL should generate same key
        self.assertEqual(key1, key2)

    def test_cleanup_expired(self) -> None:
        """Test cleanup_expired method"""
        # Set values with different expiration times
        self.cache_manager.set("key1", "value1", expire_after=1)
        self.cache_manager.set("key2", "value2", expire_after=3600)

        # Wait for first to expire
        time.sleep(2)

        # Cleanup expired
        deleted_count = self.cache_manager.cleanup_expired()

        # Check that expired key is gone
        self.assertIsNone(self.cache_manager.get("key1"))
        # Check that non-expired key still exists
        self.assertEqual(self.cache_manager.get("key2"), "value2")
        self.assertGreater(deleted_count, 0)

    def test_get_stats(self) -> None:
        """Test get_stats method"""
        # Set some values
        self.cache_manager.set("key1", "value1")
        self.cache_manager.set("key2", "value2")

        stats = self.cache_manager.get_stats()

        self.assertIn("total_entries", stats)
        self.assertIn("active_entries", stats)
        self.assertIn("expired_entries", stats)
        self.assertIn("db_path", stats)
        self.assertGreaterEqual(stats["total_entries"], 2)
        self.assertGreaterEqual(stats["active_entries"], 2)

    def test_set_with_custom_expire(self) -> None:
        """Test set with custom expiration time"""
        key = "test_key"
        value = {"test": "data"}

        # Set with custom expiration
        self.cache_manager.set(key, value, expire_after=7200)

        # Get value
        result = self.cache_manager.get(key)
        self.assertEqual(result, value)


if __name__ == "__main__":
    unittest.main()

