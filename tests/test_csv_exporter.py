"""
CSV Exporter Tests

Tests for CSVExporter class.
"""

import tempfile
import unittest
from pathlib import Path

from php_dynctrlflow.csv_exporter import CSVExporter
from php_dynctrlflow.search_result import SearchResult


class TestCSVExporter(unittest.TestCase):
    """Test CSVExporter class"""

    def setUp(self) -> None:
        """Test setup"""
        # Create temporary output directory
        self.temp_dir = tempfile.mkdtemp()
        self.exporter = CSVExporter(output_dir=str(Path(self.temp_dir) / "output"))

        # Create test results
        self.test_results = [
            SearchResult(
                owner="owner1",
                repo_name="repo1",
                url="https://github.com/owner1/repo1",
                commit_hash="hash1",
                star_count=100,
                analysis_result={
                    "analysis_summary": {
                        "status": "accepted",
                        "detection_type": "primary_functions",
                        "priority": 1,
                    },
                },
            ),
            SearchResult(
                owner="owner2",
                repo_name="repo2",
                url="https://github.com/owner2/repo2",
                commit_hash="hash2",
                star_count=200,
                analysis_result={
                    "analysis_summary": {
                        "status": "rejected",
                        "priority": 0,
                        "reason": "No SuperGlobal usage found",
                    },
                },
            ),
        ]

    def tearDown(self) -> None:
        """Test cleanup"""
        # Clean up temporary directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self) -> None:
        """Test initialization"""
        exporter = CSVExporter(output_dir="test_output")
        self.assertEqual(str(exporter.output_dir), "test_output")

    def test_export_results(self) -> None:
        """Test export_results method"""
        path = self.exporter.export_results(self.test_results)
        self.assertTrue(Path(path).exists())

        # Read and check file content
        with open(path, "r") as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 1)  # Header + at least one row

    def test_export_results_include_unqualified(self) -> None:
        """Test export_results with include_unqualified=True"""
        path = self.exporter.export_results(self.test_results, include_unqualified=True)
        self.assertTrue(Path(path).exists())

        # Check that both qualified and unqualified are included
        with open(path, "r") as f:
            lines = f.readlines()
            self.assertGreaterEqual(len(lines), 3)  # Header + 2 rows

    def test_export_summary(self) -> None:
        """Test export_summary method"""
        path = self.exporter.export_summary(self.test_results)
        self.assertTrue(Path(path).exists())

        # Read and check file content
        with open(path, "r") as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 1)  # Header + summary rows

    def test_export_detailed_results(self) -> None:
        """Test export_detailed_results method"""
        path = self.exporter.export_detailed_results(self.test_results)
        self.assertTrue(Path(path).exists())

        # Read and check file content
        with open(path, "r") as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 1)  # Header + detail rows

    def test_export_results_with_filename(self) -> None:
        """Test export_results with custom filename"""
        filename = "custom_output.csv"
        path = self.exporter.export_results(self.test_results, filename=filename)
        self.assertTrue(Path(path).exists())
        self.assertTrue(path.endswith(filename))

    def test_export_results_empty_list(self) -> None:
        """Test export_results with empty results list"""
        path = self.exporter.export_results([])
        self.assertTrue(Path(path).exists())

        # Check file has header only
        with open(path, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)  # Header only


if __name__ == "__main__":
    unittest.main()

