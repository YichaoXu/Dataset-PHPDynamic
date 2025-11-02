"""
Semgrep Analyzer Tests

Tests for SemgrepAnalyzer class.
"""

import tempfile
import unittest
from pathlib import Path

from php_dynctrlflow.exceptions import SemgrepError
from php_dynctrlflow.semgrep_analyzer import SemgrepAnalyzer


class TestSemgrepAnalyzer(unittest.TestCase):
    """Test SemgrepAnalyzer class"""

    def setUp(self) -> None:
        """Test setup"""
        # Create temporary Semgrep rules file
        self.temp_dir = tempfile.mkdtemp()
        self.rules_file = Path(self.temp_dir) / "test_rules.yml"
        self._create_test_rules_file()
        self.analyzer = SemgrepAnalyzer(rules_file=str(self.rules_file))

    def tearDown(self) -> None:
        """Test cleanup"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_rules_file(self) -> None:
        """Create test Semgrep rules file"""
        rules_content = """
rules:
  - id: test-dynamic-include
    message: "Test dynamic include detected"
    languages: [php]
    pattern: |
      include $EXPR;
    severity: WARNING
"""
        self.rules_file.write_text(rules_content)

    def test_init(self) -> None:
        """Test initialization"""
        analyzer = SemgrepAnalyzer(rules_file=str(self.rules_file))
        self.assertEqual(analyzer.rules_file, self.rules_file)

    def test_init_nonexistent_file(self) -> None:
        """Test initialization with nonexistent rules file"""
        with self.assertRaises(SemgrepError):
            SemgrepAnalyzer(rules_file="nonexistent.yml")

    def test_detect_dynamic_includes(self) -> None:
        """Test detect_dynamic_includes method"""
        php_content = '<?php\n$file = $_GET["page"];\ninclude $file;\n?>'

        try:
            results = self.analyzer.detect_dynamic_includes(php_content)
            # Results should be Dict[str, List[Dict[str, Any]]]
            self.assertIsInstance(results, dict)
        except SemgrepError:
            # Semgrep may not be installed, skip this test
            self.skipTest("Semgrep not installed or not available")

    def test_detect_variable_functions(self) -> None:
        """Test detect_variable_functions method"""
        php_content = '<?php\n$func = "strlen";\n$result = $func($str);\n?>'

        try:
            results = self.analyzer.detect_variable_functions(php_content)
            # Results should be Dict[str, List[Dict[str, Any]]]
            self.assertIsInstance(results, dict)
        except SemgrepError:
            # Semgrep may not be installed, skip this test
            self.skipTest("Semgrep not installed or not available")

    def test_run_semgrep(self) -> None:
        """Test run_semgrep method"""
        # Create temporary PHP file
        temp_php = Path(self.temp_dir) / "test.php"
        temp_php.write_text('<?php\n$file = $_GET["page"];\ninclude $file;\n?>')

        try:
            results = self.analyzer.run_semgrep(str(temp_php), str(self.rules_file))
            # Results should be List[Dict[str, Any]]
            self.assertIsInstance(results, list)
        except SemgrepError:
            # Semgrep may not be installed, skip this test
            self.skipTest("Semgrep not installed or not available")

    def test_parse_semgrep_output(self) -> None:
        """Test parse_semgrep_output method"""
        json_output = """
{
  "results": [
    {
      "check_id": "test-rule",
      "path": "test.php",
      "start": {"line": 1, "col": 1},
      "end": {"line": 1, "col": 10},
      "extra": {
        "message": "Test message",
        "severity": "WARNING",
        "lines": "test code"
      }
    }
  ]
}
"""
        results = self.analyzer.parse_semgrep_output(json_output)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["rule_id"], "test-rule")

    def test_parse_semgrep_output_invalid_json(self) -> None:
        """Test parse_semgrep_output with invalid JSON"""
        with self.assertRaises(SemgrepError):
            self.analyzer.parse_semgrep_output("invalid json")


if __name__ == "__main__":
    unittest.main()

