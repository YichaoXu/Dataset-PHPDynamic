"""
PHP Analyzer Tests

Tests for PHPAnalyzer class.
"""

import unittest
from unittest.mock import Mock, patch

from php_dynctrlflow.exceptions import AnalysisError
from php_dynctrlflow.php_analyzer import PHPAnalyzer


class TestPHPAnalyzer(unittest.TestCase):
    """Test PHPAnalyzer class"""

    def setUp(self) -> None:
        """Test setup"""
        self.analyzer = PHPAnalyzer()

    def test_init(self) -> None:
        """Test initialization"""
        analyzer = PHPAnalyzer()
        self.assertIsNotNone(analyzer.semgrep_analyzer)

    def test_check_superglobal_requirement_true(self) -> None:
        """Test check_superglobal_requirement returns True when SuperGlobal is found"""
        content = '<?php\n$value = $_GET["key"];\n?>'
        result = self.analyzer.check_superglobal_requirement(content)
        self.assertTrue(result)

    def test_check_superglobal_requirement_false(self) -> None:
        """Test check_superglobal_requirement returns False when no SuperGlobal"""
        content = '<?php\n$value = "test";\n?>'
        result = self.analyzer.check_superglobal_requirement(content)
        self.assertFalse(result)

    def test_check_primary_functions(self) -> None:
        """Test check_primary_functions method"""
        content = '<?php\ncall_user_func($func, $args);\n?>'
        result = self.analyzer.check_primary_functions(content)

        self.assertIsInstance(result, dict)
        self.assertIn("found", result)
        self.assertIn("usage", result)
        self.assertTrue(result["found"])

    def test_check_primary_functions_not_found(self) -> None:
        """Test check_primary_functions when not found"""
        content = '<?php\n$value = "test";\n?>'
        result = self.analyzer.check_primary_functions(content)

        self.assertIsInstance(result, dict)
        self.assertFalse(result["found"])

    def test_check_variable_functions(self) -> None:
        """Test check_variable_functions method"""
        content = '<?php\n$func = "strlen";\n$result = $func($str);\n?>'

        with patch.object(self.analyzer.semgrep_analyzer, "detect_variable_functions") as mock_detect:
            mock_detect.return_value = {
                "variable-function-call": [
                    {
                        "rule_id": "variable-function-call",
                        "line_number": 2,
                        "message": "Variable function call detected",
                    }
                ]
            }

            result = self.analyzer.check_variable_functions(content)
            self.assertIsInstance(result, dict)
            self.assertIn("found", result)
            self.assertIn("usage", result)

    def test_check_fallback_includes(self) -> None:
        """Test check_fallback_includes method"""
        content = '<?php\n$file = $_GET["page"];\ninclude $file;\n?>'

        with patch.object(
            self.analyzer.semgrep_analyzer, "detect_dynamic_includes"
        ) as mock_detect:
            mock_detect.return_value = {
                "dynamic-include-detection": [
                    {
                        "rule_id": "dynamic-include-detection",
                        "line_number": 2,
                        "message": "Dynamic include detected",
                    }
                ]
            }

            result = self.analyzer.check_fallback_includes(content)
            self.assertIsInstance(result, dict)
            self.assertIn("found", result)
            self.assertIn("usage", result)

    def test_analyze_file_content(self) -> None:
        """Test analyze_file_content method"""
        content = '<?php\n$value = $_GET["key"];\ncall_user_func($func);\n?>'

        result = self.analyzer.analyze_file_content(content)

        self.assertIsInstance(result, dict)
        self.assertIn("has_superglobal", result)
        self.assertIn("has_dynamic_functions", result)
        self.assertIn("analysis_summary", result)

    def test_analyze_file_content_no_superglobal(self) -> None:
        """Test analyze_file_content when no SuperGlobal"""
        content = '<?php\n$value = "test";\n?>'

        result = self.analyzer.analyze_file_content(content)

        self.assertIsInstance(result, dict)
        self.assertFalse(result["has_superglobal"])
        self.assertEqual(result["analysis_summary"]["status"], "rejected")

    def test_analyze_multiple_files(self) -> None:
        """Test analyze_multiple_files method"""
        file_contents = {
            "file1.php": '<?php\n$value = $_GET["key"];\n?>',
            "file2.php": '<?php\ncall_user_func($func);\n?>',
        }

        results = self.analyzer.analyze_multiple_files(file_contents)

        self.assertIsInstance(results, dict)
        self.assertEqual(len(results), 2)
        self.assertIn("file1.php", results)
        self.assertIn("file2.php", results)


if __name__ == "__main__":
    unittest.main()

