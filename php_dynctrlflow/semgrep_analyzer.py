"""
Semgrep Static Analyzer

This module uses Semgrep for static analysis of PHP code,
detecting dynamic include/require statements.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from .exceptions import SemgrepError


class SemgrepAnalyzer:
    """Performs static analysis of PHP code using Semgrep"""

    def __init__(self, rules_file: str = "php_dynctrlflow/semgrep/rules.yml") -> None:
        """
        Initialize Semgrep analyzer

        Args:
            rules_file: Semgrep rules file path
        """
        self.rules_file = Path(rules_file)
        if not self.rules_file.exists():
            raise SemgrepError(f"Semgrep rules file not found: {rules_file}")

    def detect_dynamic_includes(self, content: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect dynamic include/require statements in PHP code

        Args:
            content: PHP code content

        Returns:
            Detection results grouped by rule ID

        Raises:
            SemgrepError: Semgrep analysis failed
        """
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".php", delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Run Semgrep analysis
            results = self.run_semgrep(temp_file_path, str(self.rules_file))
            
            # Group results by rule_id
            grouped_results: Dict[str, List[Dict[str, Any]]] = {}
            for result in results:
                rule_id = result.get("rule_id", "unknown")
                if rule_id not in grouped_results:
                    grouped_results[rule_id] = []
                grouped_results[rule_id].append(result)
            
            return grouped_results
        finally:
            # Clean up temporary file
            Path(temp_file_path).unlink(missing_ok=True)

    def detect_variable_functions(self, content: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect variable function calls ($var() and $$var())

        Args:
            content: PHP code content

        Returns:
            Variable function detection results grouped by rule ID

        Raises:
            SemgrepError: Semgrep analysis failed
        """
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".php", delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Run Semgrep analysis
            results = self.run_semgrep(temp_file_path, str(self.rules_file))
            
            # Filter for variable function call results only
            variable_function_results = [
                r for r in results if r.get("rule_id") == "variable-function-call"
            ]
            
            # Group results by rule_id
            grouped_results: Dict[str, List[Dict[str, Any]]] = {}
            for result in variable_function_results:
                rule_id = result.get("rule_id", "variable-function-call")
                if rule_id not in grouped_results:
                    grouped_results[rule_id] = []
                grouped_results[rule_id].append(result)
            
            return grouped_results
        finally:
            # Clean up temporary file
            Path(temp_file_path).unlink(missing_ok=True)

    def run_semgrep(self, file_path: str, rules_path: str) -> List[Dict[str, Any]]:
        """
        Run Semgrep analysis on specified file using specified rules file

        Args:
            file_path: File path to analyze
            rules_path: Semgrep rules file path

        Returns:
            List of Semgrep analysis results

        Raises:
            SemgrepError: Semgrep execution failed
        """
        try:
            # Build Semgrep command
            cmd = [
                "semgrep",
                "--config",
                str(rules_path),
                "--json",
                "--no-git-ignore",
                file_path,
            ]

            # Execute command
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, check=False
            )

            if result.returncode != 0:
                raise SemgrepError(
                    f"Semgrep execution failed: {result.stderr}",
                    command=" ".join(cmd),
                    exit_code=result.returncode,
                )

            # Parse JSON output
            return self.parse_semgrep_output(result.stdout)

        except subprocess.TimeoutExpired as e:
            raise SemgrepError(f"Semgrep execution timeout: {e}", command=" ".join(cmd))
        except FileNotFoundError:
            raise SemgrepError(
                "Semgrep not found. Please install semgrep: pip install semgrep",
                command="semgrep",
            )

    def parse_semgrep_output(self, json_output: str) -> List[Dict[str, Any]]:
        """
        Parse Semgrep JSON output

        Args:
            json_output: Semgrep JSON output string

        Returns:
            Parsed result list

        Raises:
            SemgrepError: JSON parsing failed
        """
        try:
            data = json.loads(json_output)
            results = []

            # Extract results
            for result in data.get("results", []):
                parsed_result = {
                    "rule_id": result.get("check_id"),
                    "file_path": result.get("path"),
                    "line_number": result.get("start", {}).get("line"),
                    "column_number": result.get("start", {}).get("col"),
                    "end_line": result.get("end", {}).get("line"),
                    "end_column": result.get("end", {}).get("col"),
                    "message": result.get("extra", {}).get("message"),
                    "severity": result.get("extra", {}).get("severity"),
                    "code_snippet": result.get("extra", {}).get("lines"),
                    "metadata": result.get("extra", {}).get("metadata", {}),
                }
                results.append(parsed_result)

            return results

        except json.JSONDecodeError as e:
            raise SemgrepError(f"Failed to parse Semgrep JSON output: {e}")

    def analyze_multiple_files(
        self, file_contents: Dict[str, str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Analyze multiple PHP files

        Args:
            file_contents: Mapping of file paths to content

        Returns:
            Analysis results for each file

        Raises:
            SemgrepError: Analysis failed
        """
        results: Dict[str, List[Dict[str, Any]]] = {}
        temp_files: List[str] = []

        try:
            # Create temporary files
            for file_path, content in file_contents.items():
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".php", delete=False
                )
                temp_file.write(content)
                temp_file_path = str(temp_file.name)
                temp_file.close()
                temp_files.append(temp_file_path)

            # Run Semgrep analysis on all files
            cmd = [
                "semgrep",
                "--config",
                str(self.rules_file),
                "--json",
                "--no-git-ignore",
            ] + temp_files

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, check=False
            )

            if result.returncode != 0:
                raise SemgrepError(
                    f"Semgrep execution failed: {result.stderr}",
                    command=" ".join(cmd),
                    exit_code=result.returncode,
                )

            # Parse results and group by file
            all_results = self.parse_semgrep_output(result.stdout)
            for result_item in all_results:
                file_path = result_item["file_path"]
                if file_path not in results:
                    results[file_path] = []
                results[file_path].append(result_item)

            return results

        except subprocess.TimeoutExpired as e:
            raise SemgrepError(f"Semgrep execution timeout: {e}", command=" ".join(cmd))
        finally:
            # Clean up temporary file
            for temp_file_path in temp_files:
                Path(temp_file_path).unlink(missing_ok=True)

    def get_rule_info(self) -> Dict[str, Any]:
        """
        Get rule file information

        Returns:
            Basic information about the rule file

        Raises:
            SemgrepError: Get rule information failed
        """
        try:
            cmd = ["semgrep", "--config", str(self.rules_file), "--dump-config"]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10, check=False
            )

            if result.returncode != 0:
                raise SemgrepError(
                    f"Failed to get rule info: {result.stderr}",
                    command=" ".join(cmd),
                    exit_code=result.returncode,
                )

            return {
                "rules_file": str(self.rules_file),
                "config_content": result.stdout,
                "file_exists": self.rules_file.exists(),
                "file_size": (
                    self.rules_file.stat().st_size if self.rules_file.exists() else 0
                ),
            }

        except subprocess.TimeoutExpired as e:
            raise SemgrepError(f"Timeout getting rule info: {e}", command=" ".join(cmd))

    def validate_rules(self) -> bool:
        """
        Validate if rule file is valid

        Returns:
            Whether the rule file is valid

        Raises:
            SemgrepError: Validation failed
        """
        try:
            cmd = ["semgrep", "--config", str(self.rules_file), "--validate"]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10, check=False
            )

            if result.returncode != 0:
                raise SemgrepError(
                    f"Rule validation failed: {result.stderr}",
                    command=" ".join(cmd),
                    exit_code=result.returncode,
                )

            return True

        except subprocess.TimeoutExpired as e:
            raise SemgrepError(f"Timeout validating rules: {e}", command=" ".join(cmd))
