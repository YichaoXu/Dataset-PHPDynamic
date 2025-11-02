"""
PHP Code Analyzer

This module analyzes PHP code, detecting SuperGlobal usage, dynamic function calls, and dynamic include statements.
"""

import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from .exceptions import AnalysisError
from .semgrep_analyzer import SemgrepAnalyzer


class PHPAnalyzer:
    """PHP code analyzer that detects security risk characteristics"""

    def __init__(self, semgrep_analyzer: Optional[SemgrepAnalyzer] = None) -> None:
        """
        Initialize PHP analyzer

        Args:
            semgrep_analyzer: Semgrep analyzer instance
        """
        self.semgrep_analyzer = semgrep_analyzer or SemgrepAnalyzer()

        # Define patterns to detect
        self.superglobal_patterns = [
            r"\$_GET\s*\[",
            r"\$_POST\s*\[",
            r"\$_REQUEST\s*\[",
            r"\$_COOKIE\s*\[",
            r"\$_SESSION\s*\[",
            r"\$_SERVER\s*\[",
            r"\$_ENV\s*\[",
            r"\$_FILES\s*\[",
        ]

        self.dynamic_function_patterns = [
            r"call_user_func\s*\(",
            r"call_user_func_array\s*\(",
            r"forward_static_call\s*\(",
            r"forward_static_call_array\s*\(",
        ]

    def analyze_file_content(self, content: str) -> Dict[str, Any]:
        """
        Analyze PHP file content, detecting all target features

        Args:
            content: PHP code content

        Returns:
            Analysis result dictionary

        Raises:
            AnalysisError: Analysis failed
        """
        try:
            result = {
                "has_superglobal": False,
                "has_dynamic_functions": False,
                "has_dynamic_includes": False,
                "superglobal_usage": [],
                "dynamic_function_usage": [],
                "dynamic_include_usage": [],
                "analysis_summary": {},
            }

            # 1. Check SuperGlobal usage (required condition)
            has_superglobal = self.check_superglobal_requirement(content)
            result["has_superglobal"] = has_superglobal
            # Get usage details
            superglobal_result = self._check_superglobal_usage(content)
            result["superglobal_usage"] = superglobal_result["usage"]

            # If SuperGlobal does not exist, return directly
            if not result["has_superglobal"]:
                result["analysis_summary"] = {
                    "status": "rejected",
                    "reason": "No SuperGlobal usage found",
                }
                return result

            # 2. Check main dynamic functions (call_user_func, etc.)
            function_result = self.check_primary_functions(content)
            result["has_dynamic_functions"] = function_result["found"]
            result["dynamic_function_usage"] = function_result["usage"]

            # 2b. Check variable function calls ($var() and $$var())
            variable_function_result = self.check_variable_functions(content)
            if variable_function_result["found"]:
                result["has_dynamic_functions"] = True
                usage_list = variable_function_result.get("usage", [])
                if isinstance(usage_list, list) and isinstance(result["dynamic_function_usage"], list):
                    result["dynamic_function_usage"].extend(usage_list)

            # 3. If main functions do not exist, check fallback includes
            if not result["has_dynamic_functions"]:
                include_result = self.check_fallback_includes(content)
                result["has_dynamic_includes"] = include_result["found"]
                result["dynamic_include_usage"] = include_result["usage"]

            # 4. Generate analysis summary
            result["analysis_summary"] = self._generate_analysis_summary(result)

            return result

        except Exception as e:
            raise AnalysisError(f"Failed to analyze content: {e}") from e

    def check_superglobal_requirement(self, content: str) -> bool:
        """
        Check SuperGlobal usage requirement

        Args:
            content: PHP code content

        Returns:
            Whether SuperGlobal usage is found

        Raises:
            AnalysisError: Analysis failed
        """
        try:
            for pattern in self.superglobal_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
            return False
        except Exception as e:
            raise AnalysisError(f"Failed to check SuperGlobal requirement: {e}") from e

    def _check_superglobal_usage(self, content: str) -> Dict[str, Any]:
        """
        Check SuperGlobal usage and return detailed results

        Args:
            content: PHP code content

        Returns:
            Usage check result dictionary
        """
        usage = []
        found_patterns = set()

        for pattern in self.superglobal_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_number = content[: match.start()].count("\n") + 1
                usage.append(
                    {
                        "pattern": pattern,
                        "line_number": line_number,
                        "match": match.group(),
                        "context": self._get_context(content, match.start()),
                    }
                )
                found_patterns.add(pattern)

        return {
            "found": len(usage) > 0,
            "usage": usage,
            "patterns_found": list(found_patterns),
        }

    def check_primary_functions(self, content: str) -> Dict[str, Any]:
        """
        Check main dynamic function calls (call_user_func, etc.)

        Args:
            content: PHP code content

        Returns:
            Check result dictionary
        """
        usage = []
        found_patterns = set()

        for pattern in self.dynamic_function_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_number = content[: match.start()].count("\n") + 1
                usage.append(
                    {
                        "pattern": pattern,
                        "line_number": line_number,
                        "match": match.group(),
                        "context": self._get_context(content, match.start()),
                    }
                )
                found_patterns.add(pattern)

        return {
            "found": len(usage) > 0,
            "usage": usage,
            "patterns_found": list(found_patterns),
        }

    def check_variable_functions(self, content: str) -> Dict[str, Any]:
        """
        Check variable function calls ($var() and $$var())
        Uses Semgrep for precise detection, similar to ast_call node checking in AST analysis
        In AST analysis, we check if ast_call node's func is expr type (variable expression)
        Semgrep internally uses AST analysis and can precisely match $VAR(...) and $$VAR(...) patterns

        Args:
            content: PHP code content

        Returns:
            Check result dictionary
        """
        try:
            # Use Semgrep to detect variable function calls
            semgrep_results = self.semgrep_analyzer.detect_variable_functions(content)

            usage = []
            # semgrep_results is Dict[str, List[Dict[str, Any]]] grouped by rule_id
            for rule_id, results_list in semgrep_results.items():
                for result in results_list:
                    usage.append(
                        {
                            "rule_id": result.get("rule_id", rule_id),
                            "pattern": "variable-function-call",
                            "line_number": result.get("line_number", 0),
                            "message": result.get("message", ""),
                            "severity": result.get("severity", ""),
                            "code_snippet": result.get("code_snippet", ""),
                            "context": self._get_context_by_line(
                                content, result.get("line_number", 0)
                            ),
                        }
                    )

            return {
                "found": len(usage) > 0,
                "usage": usage,
            }

        except Exception:
            # If Semgrep failed, use regex fallback
            return self._fallback_variable_function_detection(content)

    def _fallback_variable_function_detection(self, content: str) -> Dict[str, Any]:
        """
        Fallback variable function detection using regex

        Args:
            content: PHP code content

        Returns:
            Detection result dictionary
        """
        # Match variable function calls in the form $var() and $$var()
        variable_function_patterns = [
            r"\$\w+\s*\(",  # $var(
            r"\$\$\w+\s*\(",  # $$var(
        ]

        usage = []
        for pattern in variable_function_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_number = content[: match.start()].count("\n") + 1
                usage.append(
                    {
                        "pattern": pattern,
                        "line_number": line_number,
                        "match": match.group(),
                        "context": self._get_context(content, match.start()),
                    }
                )

        return {
            "found": len(usage) > 0,
            "usage": usage,
        }

    def _create_temp_file(self, content: str) -> str:
        """
        Create temporary file for Semgrep analysis

        Args:
            content: PHP code content

        Returns:
            Temporary file path
        """

        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".php", delete=False
        )
        temp_file.write(content)
        temp_file_path = temp_file.name
        temp_file.close()
        return temp_file_path

    def check_fallback_includes(self, content: str) -> Dict[str, Any]:
        """
        Check fallback dynamic include statements

        Args:
            content: PHP code content

        Returns:
            Check result dictionary
        """
        try:
            # Use Semgrep for more precise analysis
            semgrep_results = self.semgrep_analyzer.detect_dynamic_includes(content)

            usage = []
            # semgrep_results is Dict[str, List[Dict[str, Any]]] grouped by rule_id
            for rule_id, results_list in semgrep_results.items():
                for result in results_list:
                    usage.append(
                        {
                            "rule_id": result.get("rule_id", rule_id),
                            "line_number": result.get("line_number", 0),
                            "message": result.get("message", ""),
                            "severity": result.get("severity", ""),
                            "code_snippet": result.get("code_snippet", ""),
                            "context": self._get_context_by_line(
                                content, result.get("line_number", 0)
                            ),
                        }
                    )

            return {
                "found": len(usage) > 0,
                "usage": usage,
                "semgrep_results": semgrep_results,
            }

        except Exception:
            # If Semgrep failed, use regex fallback
            return self._fallback_include_detection(content)

    def _fallback_include_detection(self, content: str) -> Dict[str, Any]:
        """
        Fallback include detection using regex

        Args:
            content: PHP code content

        Returns:
            Detection result dictionary
        """
        include_patterns = [
            r"(include|include_once|require|require_once)\s*\(\s*\$[^)]+\s*\)",
            r"(include|include_once|require|require_once)\s+\$[^;]+;",
            r"(include|include_once|require|require_once)\s*\(\s*[^)]*\$[^)]*\s*\)",
        ]

        usage = []
        for pattern in include_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_number = content[: match.start()].count("\n") + 1
                usage.append(
                    {
                        "pattern": pattern,
                        "line_number": line_number,
                        "match": match.group(),
                        "context": self._get_context(content, match.start()),
                    }
                )

        return {"found": len(usage) > 0, "usage": usage, "method": "regex_fallback"}

    def _get_context(self, content: str, position: int, context_lines: int = 3) -> str:
        """
        Get context at specified position

        Args:
            content: File content
            position: Position
            context_lines: Number of context lines

        Returns:
            Context string
        """
        lines = content.split("\n")
        line_number = content[:position].count("\n")

        start_line = max(0, line_number - context_lines)
        end_line = min(len(lines), line_number + context_lines + 1)

        context_lines_list = []
        for i in range(start_line, end_line):
            prefix = ">>> " if i == line_number else "    "
            context_lines_list.append(f"{prefix}{i+1:4d}: {lines[i]}")

        return "\n".join(context_lines_list)

    def _get_context_by_line(
        self, content: str, line_number: int, context_lines: int = 3
    ) -> str:
        """
        Get context by line number

        Args:
            content: File content
            line_number: Line number (1-based)
            context_lines: Number of context lines

        Returns:
            Context string
        """
        lines = content.split("\n")
        actual_line = line_number - 1  # Convert to 0-based

        start_line = max(0, actual_line - context_lines)
        end_line = min(len(lines), actual_line + context_lines + 1)

        context_lines_list = []
        for i in range(start_line, end_line):
            prefix = ">>> " if i == actual_line else "    "
            context_lines_list.append(f"{prefix}{i+1:4d}: {lines[i]}")

        return "\n".join(context_lines_list)

    def _generate_analysis_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate analysis summary

        Args:
            result: Analysis result

        Returns:
            Analysis summary
        """
        if not result["has_superglobal"]:
            return {
                "status": "rejected",
                "reason": "No SuperGlobal usage found",
                "priority": 0,
            }

        if result["has_dynamic_functions"]:
            return {
                "status": "accepted",
                "reason": "Dynamic functions detected",
                "priority": 1,
                "detection_type": "primary_functions",
            }

        if result["has_dynamic_includes"]:
            return {
                "status": "accepted",
                "reason": "Dynamic includes detected",
                "priority": 2,
                "detection_type": "fallback_includes",
            }

        return {
            "status": "rejected",
            "reason": "No dynamic functions or includes found",
            "priority": 0,
        }

    def analyze_multiple_files(
        self, file_contents: Dict[str, str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze multiple PHP files

        Args:
            file_contents: Mapping of file path to content

        Returns:
            Analysis result for each file
        """
        results = {}

        for file_path, content in file_contents.items():
            try:
                result = self.analyze_file_content(content)
                result["file_path"] = file_path
                results[file_path] = result
            except AnalysisError as e:
                results[file_path] = {
                    "file_path": file_path,
                    "error": str(e),
                    "analysis_summary": {
                        "status": "error",
                        "reason": f"Analysis failed: {e}",
                    },
                }

        return results

    def get_analysis_statistics(
        self, results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get analysis statistics

        Args:
            results: Analysis result dictionary

        Returns:
            Statistics
        """
        total_files = len(results)
        accepted_files = 0
        rejected_files = 0
        error_files = 0

        detection_types = {"primary_functions": 0, "fallback_includes": 0}

        for result in results.values():
            summary = result.get("analysis_summary", {})
            status = summary.get("status", "unknown")

            if status == "accepted":
                accepted_files += 1
                detection_type = summary.get("detection_type")
                if detection_type in detection_types:
                    detection_types[detection_type] += 1
            elif status == "rejected":
                rejected_files += 1
            elif status == "error":
                error_files += 1

        return {
            "total_files": total_files,
            "accepted_files": accepted_files,
            "rejected_files": rejected_files,
            "error_files": error_files,
            "acceptance_rate": accepted_files / total_files if total_files > 0 else 0,
            "detection_types": detection_types,
        }
