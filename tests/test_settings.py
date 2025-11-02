"""
Settings Tests

Tests for Settings configuration loader class.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from php_dynctrlflow.settings import Settings


class TestSettings(unittest.TestCase):
    """Test Settings class"""

    def setUp(self) -> None:
        """Test setup"""
        # Clear config cache
        Settings._config_cache = None

    def tearDown(self) -> None:
        """Test cleanup"""
        # Clear config cache after each test
        Settings._config_cache = None

    @patch("php_dynctrlflow.settings.Settings.CONFIG_FILE_PATH")
    def test_get_github_token(self, mock_path: Path) -> None:
        """Test get_github_token method"""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("github:\n  api_token: test_token_123\n")
            temp_path = Path(f.name)

        mock_path.return_value = temp_path

        try:
            token = Settings.get_github_token()
            self.assertEqual(token, "test_token_123")
        finally:
            temp_path.unlink()

    @patch("php_dynctrlflow.settings.Settings.CONFIG_FILE_PATH")
    def test_get_max_projects(self, mock_path: Path) -> None:
        """Test get_max_projects method"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("search:\n  max_projects: 500\n")
            temp_path = Path(f.name)

        mock_path.return_value = temp_path

        try:
            max_projects = Settings.get_max_projects()
            self.assertEqual(max_projects, 500)
        finally:
            temp_path.unlink()

    @patch("php_dynctrlflow.settings.Settings.CONFIG_FILE_PATH")
    def test_get_max_files_per_project(self, mock_path: Path) -> None:
        """Test get_max_files_per_project method"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("search:\n  max_files_per_project: 20\n")
            temp_path = Path(f.name)

        mock_path.return_value = temp_path

        try:
            max_files = Settings.get_max_files_per_project()
            self.assertEqual(max_files, 20)
        finally:
            temp_path.unlink()

    @patch("php_dynctrlflow.settings.Settings.CONFIG_FILE_PATH")
    def test_get_batch_size_default(self, mock_path: Path) -> None:
        """Test get_batch_size method with default value"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("search:\n  max_projects: 200\n")
            temp_path = Path(f.name)

        mock_path.return_value = temp_path

        try:
            batch_size = Settings.get_batch_size()
            self.assertEqual(batch_size, 100)  # Default value
        finally:
            temp_path.unlink()

    @patch("php_dynctrlflow.settings.Settings.CONFIG_FILE_PATH")
    def test_get_batch_size_from_config(self, mock_path: Path) -> None:
        """Test get_batch_size method from config"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("search:\n  batch_size: 50\n")
            temp_path = Path(f.name)

        mock_path.return_value = temp_path

        try:
            batch_size = Settings.get_batch_size()
            self.assertEqual(batch_size, 50)
        finally:
            temp_path.unlink()

    @patch("php_dynctrlflow.settings.Settings.CONFIG_FILE_PATH")
    def test_get_output_dir(self, mock_path: Path) -> None:
        """Test get_output_dir method"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("output:\n  output_dir: test_output\n")
            temp_path = Path(f.name)

        mock_path.return_value = temp_path

        try:
            output_dir = Settings.get_output_dir()
            self.assertEqual(output_dir, "test_output")
            # Check that directory was created
            self.assertTrue(Path("test_output").exists())
            # Cleanup
            Path("test_output").rmdir()
        finally:
            temp_path.unlink()

    @patch("php_dynctrlflow.settings.Settings.CONFIG_FILE_PATH")
    def test_get_semgrep_rules_path(self, mock_path: Path) -> None:
        """Test get_semgrep_rules_path method"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("semgrep:\n  rules_file: test_rules.yml\n")
            temp_path = Path(f.name)

        mock_path.return_value = temp_path

        try:
            rules_path = Settings.get_semgrep_rules_path()
            self.assertEqual(rules_path, "test_rules.yml")
        finally:
            temp_path.unlink()

    @patch("php_dynctrlflow.settings.Settings.CONFIG_FILE_PATH")
    def test_get_php_file_extensions(self, mock_path: Path) -> None:
        """Test get_php_file_extensions method"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("php_analysis:\n  file_extensions:\n    - .php\n    - .phtml\n")
            temp_path = Path(f.name)

        mock_path.return_value = temp_path

        try:
            extensions = Settings.get_php_file_extensions()
            self.assertIn(".php", extensions)
            self.assertIn(".phtml", extensions)
        finally:
            temp_path.unlink()

    @patch("php_dynctrlflow.settings.Settings.CONFIG_FILE_PATH")
    def test_is_php_file(self, mock_path: Path) -> None:
        """Test is_php_file method"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("php_analysis:\n  file_extensions:\n    - .php\n    - .phtml\n")
            temp_path = Path(f.name)

        mock_path.return_value = temp_path

        try:
            Settings._config_cache = None
            self.assertTrue(Settings.is_php_file("test.php"))
            self.assertTrue(Settings.is_php_file("test.phtml"))
            self.assertFalse(Settings.is_php_file("test.txt"))
        finally:
            temp_path.unlink()

    @patch("php_dynctrlflow.settings.Settings.CONFIG_FILE_PATH")
    def test_validate_config(self, mock_path: Path) -> None:
        """Test validate_config method"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(
                "github:\n  api_token: test_token\n"
                "cache:\n  db_path: test.db\n"
                "output:\n  output_dir: test_output\n"
            )
            temp_path = Path(f.name)

        mock_path.return_value = temp_path

        try:
            results = Settings.validate_config()
            self.assertIn("config_file", results)
            self.assertTrue(results["config_file"])
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    unittest.main()

