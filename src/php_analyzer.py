"""
PHP代码分析器

本模块分析PHP代码，检测SuperGlobal使用、动态函数调用和动态include语句。
"""

import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from .exceptions import AnalysisError
from .semgrep_analyzer import SemgrepAnalyzer


class PHPAnalyzer:
    """PHP代码分析器，检测安全风险特征"""

    def __init__(self, semgrep_analyzer: Optional[SemgrepAnalyzer] = None) -> None:
        """
        初始化PHP分析器

        Args:
            semgrep_analyzer: Semgrep分析器实例
        """
        self.semgrep_analyzer = semgrep_analyzer or SemgrepAnalyzer()

        # 定义要检测的模式
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

    def analyze_file_content(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        分析PHP文件内容

        Args:
            file_path: 文件路径
            content: 文件内容

        Returns:
            分析结果字典

        Raises:
            AnalysisError: 分析失败
        """
        try:
            result = {
                "file_path": file_path,
                "has_superglobal": False,
                "has_dynamic_functions": False,
                "has_dynamic_includes": False,
                "superglobal_usage": [],
                "dynamic_function_usage": [],
                "dynamic_include_usage": [],
                "analysis_summary": {},
            }

            # 1. 检查SuperGlobal使用
            superglobal_result = self.check_superglobal_requirement(content)
            result["has_superglobal"] = superglobal_result["found"]
            result["superglobal_usage"] = superglobal_result["usage"]

            # 如果SuperGlobal不存在，直接返回
            if not result["has_superglobal"]:
                result["analysis_summary"] = {
                    "status": "rejected",
                    "reason": "No SuperGlobal usage found",
                }
                return result

            # 2. 检查主要动态函数（call_user_func等）
            function_result = self.check_primary_functions(content)
            result["has_dynamic_functions"] = function_result["found"]
            result["dynamic_function_usage"] = function_result["usage"]

            # 2b. 检查变量函数调用（$var() 和 $$var()）
            variable_function_result = self.check_variable_functions(content)
            if variable_function_result["found"]:
                result["has_dynamic_functions"] = True
                result["dynamic_function_usage"].extend(variable_function_result["usage"])

            # 3. 如果主要函数不存在，检查fallback includes
            if not result["has_dynamic_functions"]:
                include_result = self.check_fallback_includes(content)
                result["has_dynamic_includes"] = include_result["found"]
                result["dynamic_include_usage"] = include_result["usage"]

            # 4. 生成分析摘要
            result["analysis_summary"] = self._generate_analysis_summary(result)

            return result

        except Exception as e:
            raise AnalysisError(
                f"Failed to analyze file {file_path}: {e}", file_path=file_path
            ) from e

    def check_superglobal_requirement(self, content: str) -> Dict[str, Any]:
        """
        检查SuperGlobal使用要求

        Args:
            content: PHP代码内容

        Returns:
            检查结果字典
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
        检查主要动态函数调用（call_user_func等）

        Args:
            content: PHP代码内容

        Returns:
            检查结果字典
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
        检查变量函数调用（$var() 和 $$var()）
        使用Semgrep进行精确检测，类似于AST分析中的ast_call节点检查
        在AST分析中，我们会检查ast_call节点的func是expr类型（变量表达式）
        Semgrep内部使用AST分析，可以精确匹配 $VAR(...) 和 $$VAR(...) 模式

        Args:
            content: PHP代码内容

        Returns:
            检查结果字典
        """
        temp_file_path = None
        try:
            # 使用Semgrep检测变量函数调用
            # 创建临时文件用于Semgrep分析
            temp_file_path = self._create_temp_file(content)
            semgrep_results = self.semgrep_analyzer.run_semgrep(temp_file_path)

            usage = []
            for result in semgrep_results:
                # 只提取变量函数调用的检测结果（rule_id: variable-function-call）
                if result.get("rule_id") == "variable-function-call":
                    usage.append(
                        {
                            "rule_id": result["rule_id"],
                            "pattern": "variable-function-call",
                            "line_number": result["line_number"],
                            "message": result["message"],
                            "severity": result["severity"],
                            "code_snippet": result.get("code_snippet", ""),
                            "context": self._get_context_by_line(
                                content, result["line_number"]
                            ),
                        }
                    )

            return {
                "found": len(usage) > 0,
                "usage": usage,
                "semgrep_results": [
                    r
                    for r in semgrep_results
                    if r.get("rule_id") == "variable-function-call"
                ],
            }

        except Exception:
            # 如果Semgrep失败，使用正则表达式fallback
            return self._fallback_variable_function_detection(content)
        finally:
            # 清理临时文件
            if temp_file_path:
                Path(temp_file_path).unlink(missing_ok=True)

    def _fallback_variable_function_detection(self, content: str) -> Dict[str, Any]:
        """
        使用正则表达式的fallback变量函数检测

        Args:
            content: PHP代码内容

        Returns:
            检测结果字典
        """
        # 匹配 $var() 和 $$var() 形式的变量函数调用
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
        创建临时文件用于Semgrep分析

        Args:
            content: PHP代码内容

        Returns:
            临时文件路径
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
        检查fallback动态include语句

        Args:
            content: PHP代码内容

        Returns:
            检查结果字典
        """
        try:
            # 使用Semgrep进行更精确的分析
            semgrep_results = self.semgrep_analyzer.detect_dynamic_includes(content)

            usage = []
            for result in semgrep_results:
                usage.append(
                    {
                        "rule_id": result["rule_id"],
                        "line_number": result["line_number"],
                        "message": result["message"],
                        "severity": result["severity"],
                        "code_snippet": result["code_snippet"],
                        "context": self._get_context_by_line(
                            content, result["line_number"]
                        ),
                    }
                )

            return {
                "found": len(usage) > 0,
                "usage": usage,
                "semgrep_results": semgrep_results,
            }

        except Exception:
            # 如果Semgrep失败，使用正则表达式fallback
            return self._fallback_include_detection(content)

    def _fallback_include_detection(self, content: str) -> Dict[str, Any]:
        """
        使用正则表达式的fallback include检测

        Args:
            content: PHP代码内容

        Returns:
            检测结果字典
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
        获取指定位置的上下文

        Args:
            content: 文件内容
            position: 位置
            context_lines: 上下文行数

        Returns:
            上下文字符串
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
        根据行号获取上下文

        Args:
            content: 文件内容
            line_number: 行号（1-based）
            context_lines: 上下文行数

        Returns:
            上下文字符串
        """
        lines = content.split("\n")
        actual_line = line_number - 1  # 转换为0-based

        start_line = max(0, actual_line - context_lines)
        end_line = min(len(lines), actual_line + context_lines + 1)

        context_lines_list = []
        for i in range(start_line, end_line):
            prefix = ">>> " if i == actual_line else "    "
            context_lines_list.append(f"{prefix}{i+1:4d}: {lines[i]}")

        return "\n".join(context_lines_list)

    def _generate_analysis_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成分析摘要

        Args:
            result: 分析结果

        Returns:
            分析摘要
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
        分析多个PHP文件

        Args:
            file_contents: 文件路径到内容的映射

        Returns:
            每个文件的分析结果
        """
        results = {}

        for file_path, content in file_contents.items():
            try:
                results[file_path] = self.analyze_file_content(file_path, content)
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
        获取分析统计信息

        Args:
            results: 分析结果字典

        Returns:
            统计信息
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
