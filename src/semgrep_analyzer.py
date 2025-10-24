"""
Semgrep静态分析器

本模块使用Semgrep进行PHP代码的静态分析，检测动态include/require语句。
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from .exceptions import SemgrepError


class SemgrepAnalyzer:
    """使用Semgrep进行PHP代码静态分析"""

    def __init__(self, rules_file: str = "config/semgrep_rules.yml") -> None:
        """
        初始化Semgrep分析器

        Args:
            rules_file: Semgrep规则文件路径
        """
        self.rules_file = Path(rules_file)
        if not self.rules_file.exists():
            raise SemgrepError(f"Semgrep rules file not found: {rules_file}")

    def detect_dynamic_includes(self, php_content: str) -> List[Dict[str, Any]]:
        """
        检测PHP代码中的动态include/require语句

        Args:
            php_content: PHP代码内容

        Returns:
            检测结果列表，每个结果包含文件路径、行号、规则ID等信息

        Raises:
            SemgrepError: Semgrep分析失败
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".php", delete=False
        ) as temp_file:
            temp_file.write(php_content)
            temp_file_path = temp_file.name

        try:
            # 运行Semgrep分析
            results = self.run_semgrep(temp_file_path)
            return results
        finally:
            # 清理临时文件
            Path(temp_file_path).unlink(missing_ok=True)

    def run_semgrep(self, file_path: str) -> List[Dict[str, Any]]:
        """
        运行Semgrep分析指定文件

        Args:
            file_path: 要分析的文件路径

        Returns:
            Semgrep分析结果列表

        Raises:
            SemgrepError: Semgrep执行失败
        """
        try:
            # 构建Semgrep命令
            cmd = [
                "semgrep",
                "--config",
                str(self.rules_file),
                "--json",
                "--no-git-ignore",
                file_path,
            ]

            # 执行命令
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, check=False
            )

            if result.returncode != 0:
                raise SemgrepError(
                    f"Semgrep execution failed: {result.stderr}",
                    command=" ".join(cmd),
                    exit_code=result.returncode,
                )

            # 解析JSON输出
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
        解析Semgrep的JSON输出

        Args:
            json_output: Semgrep的JSON输出字符串

        Returns:
            解析后的结果列表

        Raises:
            SemgrepError: JSON解析失败
        """
        try:
            data = json.loads(json_output)
            results = []

            # 提取结果
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
        分析多个PHP文件

        Args:
            file_contents: 文件路径到内容的映射

        Returns:
            每个文件的分析结果

        Raises:
            SemgrepError: 分析失败
        """
        results: Dict[str, List[Dict[str, Any]]] = {}
        temp_files: List[str] = []

        try:
            # 创建临时文件
            for file_path, content in file_contents.items():
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".php", delete=False
                )
                temp_file.write(content)
                temp_file.close()
                temp_files.append(str(temp_file.name))

            # 运行Semgrep分析所有文件
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

            # 解析结果并按文件分组
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
            # 清理临时文件
            for temp_file in temp_files:
                Path(temp_file).unlink(missing_ok=True)

    def get_rule_info(self) -> Dict[str, Any]:
        """
        获取规则文件信息

        Returns:
            规则文件的基本信息

        Raises:
            SemgrepError: 获取规则信息失败
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
        验证规则文件是否有效

        Returns:
            规则文件是否有效

        Raises:
            SemgrepError: 验证失败
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
