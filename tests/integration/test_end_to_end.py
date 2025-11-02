"""
端到端集成测试

本模块测试完整的项目搜索和分析工作流程。
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from phpincludes.settings import Settings
from phpincludes.cache_manager import CacheManager
from phpincludes.csv_exporter import CSVExporter
from phpincludes.exceptions import AnalysisError, GitHubAPIError
from phpincludes.project_searcher import ProjectSearcher
from phpincludes.rate_limit_handler import RateLimitHandler
from phpincludes.search_result import SearchResult
from phpincludes.semgrep_analyzer import SemgrepAnalyzer


class TestEndToEndWorkflow(unittest.TestCase):
    """端到端工作流程测试"""

    def setUp(self) -> None:
        """测试前准备"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # 模拟GitHub令牌
        self.mock_token = "test_token_12345"

        # 创建测试用的Semgrep规则文件
        self.semgrep_rules_path = self.temp_path / "test_rules.yml"
        self._create_test_semgrep_rules()

    def tearDown(self) -> None:
        """测试后清理"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_semgrep_rules(self) -> None:
        """创建测试用的Semgrep规则文件"""
        rules_content = r"""
rules:
  - id: test-dynamic-include
    message: "Test dynamic include detected"
    languages: [php]
    severity: WARNING
    patterns:
      - pattern-either:
          - pattern: include $EXPR;
          - pattern: include($EXPR);
        metavariable-regex:
          metavariable: $EXPR
          regex: '.*\$.*'
"""
        self.semgrep_rules_path.write_text(rules_content)

    def _create_mock_github_client(self) -> Mock:
        """创建模拟的GitHub客户端"""
        mock_client = Mock()

        # 模拟搜索代码结果（修复后的方法）
        mock_client.search_code_content.return_value = [
            {
                "repository": {
                    "full_name": "test/php-project",
                    "owner": {"login": "test"},
                    "name": "php-project",
                    "html_url": "https://github.com/test/php-project",
                    "stargazers_count": 100,
                },
                "path": "index.php",
            }
        ]

        # 模拟优化的仓库搜索结果（保留兼容性）
        mock_client.search_repositories_optimized.return_value = [
            {
                "full_name": "test/php-project",
                "owner": {"login": "test"},
                "name": "php-project",
                "html_url": "https://github.com/test/php-project",
                "stargazers_count": 100,
                "default_branch": "main",
            }
        ]

        # 模拟仓库信息
        mock_client.get_repository_info.return_value = {
            "full_name": "test/php-project",
            "html_url": "https://github.com/test/php-project",
            "stargazers_count": 100,
            "default_branch": "main",
        }

        # 模拟仓库内容
        mock_client.get_repository_contents.return_value = [
            {
                "type": "file",
                "name": "index.php",
                "path": "index.php",
            }
        ]

        # 模拟文件内容
        mock_client.get_file_content.return_value = """
<?php
// 测试PHP文件
if (isset($_GET['page'])) {
    include $_GET['page'] . '.php';
}

if (isset($_POST['action'])) {
    call_user_func($_POST['action']);
}
?>
"""

        return mock_client

    def _create_mock_semgrep_analyzer(self) -> Mock:
        """创建模拟的Semgrep分析器"""
        mock_analyzer = Mock()
        mock_analyzer.detect_dynamic_includes.return_value = [
            {
                "rule_id": "test-dynamic-include",
                "line_number": 3,
                "message": "Test dynamic include detected",
                "severity": "WARNING",
                "code_snippet": "include $_GET['page'] . '.php';",
            }
        ]
        return mock_analyzer

    @patch("phpincludes.project_searcher.GitHubAPIClient")
    def test_complete_filtering_workflow(self, mock_github_client_class) -> None:
        """测试完整的筛选工作流程"""
        # 设置模拟
        mock_github_client = self._create_mock_github_client()
        mock_github_client_class.return_value = mock_github_client

        # 创建项目搜索器
        searcher = ProjectSearcher(
            github_token=self.mock_token,
            cache_manager=CacheManager(db_path=str(self.temp_path / "test_cache.db")),
            rate_limit_handler=RateLimitHandler(),
            csv_exporter=CSVExporter(output_dir=str(self.temp_path / "output")),
        )

        try:
            # 执行搜索
            results = searcher.search_projects(
                max_projects=1,
                export_csv=True,
                include_unqualified=False,
            )

            # 验证结果
            self.assertIsInstance(results, list)
            self.assertEqual(len(results), 1)

            result = results[0]
            self.assertIsInstance(result, SearchResult)
            self.assertEqual(result.project_name, "test/php-project")
            self.assertTrue(result.is_qualified)

            # 验证统计信息
            stats = searcher.get_search_statistics()
            self.assertEqual(stats["total_searched"], 1)
            self.assertEqual(stats["qualified_projects"], 1)
            self.assertEqual(stats["rejected_projects"], 0)

        finally:
            searcher.close()

    def test_error_handling_scenarios(self) -> None:
        """测试错误处理场景"""
        # 测试GitHub API错误
        with patch("phpincludes.project_searcher.GitHubAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client.search_code_content.side_effect = GitHubAPIError(
                "API request failed", status_code=403
            )
            mock_client_class.return_value = mock_client

            searcher = ProjectSearcher(
                github_token=self.mock_token,
                cache_manager=CacheManager(
                    db_path=str(self.temp_path / "test_cache.db")
                ),
            )

            try:
                with self.assertRaises(GitHubAPIError):
                    searcher.search_projects(max_projects=1)
            finally:
                searcher.close()

        # 测试分析错误
        with patch("phpincludes.project_searcher.GitHubAPIClient") as mock_client_class:
            mock_client = self._create_mock_github_client()
            mock_client.get_file_content.side_effect = AnalysisError(
                "File analysis failed", file_path="test.php"
            )
            mock_client_class.return_value = mock_client

            searcher = ProjectSearcher(
                github_token=self.mock_token,
                cache_manager=CacheManager(
                    db_path=str(self.temp_path / "test_cache.db")
                ),
            )

            try:
                results = searcher.search_projects(max_projects=1)
                # 应该返回空结果而不是抛出异常
                self.assertEqual(len(results), 0)
            finally:
                searcher.close()

    def test_csv_output_format(self) -> None:
        """测试CSV输出格式"""
        # 创建测试结果
        test_result = SearchResult(
            owner="test",
            repo_name="php-project",
            url="https://github.com/test/php-project",
            commit_hash="abc123",
            star_count=100,
            analysis_result={
                "has_superglobal": True,
                "has_dynamic_functions": True,
                "has_dynamic_includes": False,
                "superglobal_usage": [{"pattern": r"\$_GET\s*\[", "line_number": 3}],
                "dynamic_function_usage": [
                    {"pattern": r"call_user_func\s*\(", "line_number": 7}
                ],
                "dynamic_include_usage": [],
                "analysis_summary": {
                    "status": "accepted",
                    "reason": "Dynamic functions detected",
                    "priority": 1,
                    "detection_type": "primary_functions",
                },
            },
        )

        # 创建CSV导出器
        csv_exporter = CSVExporter(output_dir=str(self.temp_path / "output"))

        # 导出CSV
        csv_path = csv_exporter.export_results([test_result])

        # 验证文件存在
        self.assertTrue(Path(csv_path).exists())

        # 验证CSV内容
        csv_content = Path(csv_path).read_text()
        self.assertIn("test/php-project", csv_content)
        self.assertIn("Yes", csv_content)  # is_qualified
        self.assertIn("primary_functions", csv_content)

        # 测试摘要导出
        summary_path = csv_exporter.export_summary([test_result])
        self.assertTrue(Path(summary_path).exists())

        # 测试详细结果导出
        detailed_path = csv_exporter.export_detailed_results([test_result])
        self.assertTrue(Path(detailed_path).exists())

    def test_search_result_data_model(self) -> None:
        """测试搜索结果数据模型"""
        # 创建测试结果
        result = SearchResult(
            owner="test",
            repo_name="php-project",
            url="https://github.com/test/php-project",
            commit_hash="abc123",
            star_count=100,
            analysis_result={
                "has_superglobal": True,
                "has_dynamic_functions": True,
                "has_dynamic_includes": False,
                "superglobal_usage": [{"pattern": r"\$_GET\s*\[", "line_number": 3}],
                "dynamic_function_usage": [
                    {"pattern": r"call_user_func\s*\(", "line_number": 7}
                ],
                "dynamic_include_usage": [],
                "analysis_summary": {
                    "status": "accepted",
                    "reason": "Dynamic functions detected",
                    "priority": 1,
                    "detection_type": "primary_functions",
                },
            },
        )

        # 测试属性访问
        self.assertEqual(result.project_name, "test/php-project")
        self.assertEqual(result.owner, "test")
        self.assertEqual(result.repo_name, "php-project")
        self.assertTrue(result.is_qualified)
        self.assertEqual(result.detection_type, "primary_functions")
        self.assertEqual(result.priority, 1)

        # 测试CSV转换
        csv_row = result.to_csv_row()
        self.assertIn("project_name", csv_row)
        self.assertIn("is_qualified", csv_row)
        self.assertIn("detection_type", csv_row)

        # 测试字典转换
        result_dict = result.to_dict()
        self.assertIn("project_name", result_dict)
        self.assertIn("analysis_result", result_dict)

    def test_configuration_validation(self) -> None:
        """测试配置验证"""
        # 测试有效配置
        validation_results = Settings.validate_config()
        self.assertIsInstance(validation_results, dict)

        # 测试配置获取方法
        project_info = Settings.get_project_info()
        self.assertIn("name", project_info)
        self.assertIn("version", project_info)

        api_config = Settings.get_api_config()
        self.assertIn("base_url", api_config)
        self.assertIn("max_projects", api_config)

        cache_config = Settings.get_cache_config()
        self.assertIn("db_path", cache_config)
        self.assertIn("default_expire", cache_config)

    def test_rate_limiting_and_caching(self) -> None:
        """测试速率限制和缓存"""
        # 创建缓存管理器
        cache_manager = CacheManager(
            db_path=str(self.temp_path / "test_cache.db"),
            expire_after=60,
        )

        # 测试缓存操作
        test_key = "test_key"
        test_value = {"test": "data"}

        # 设置缓存
        cache_manager.set(test_key, test_value)

        # 获取缓存
        cached_value = cache_manager.get(test_key)
        self.assertEqual(cached_value, test_value)

        # 删除缓存
        cache_manager.delete(test_key)
        cached_value = cache_manager.get(test_key)
        self.assertIsNone(cached_value)

        # 测试速率限制处理器
        rate_handler = RateLimitHandler(request_delay=0.1)

        # 测试等待逻辑
        self.assertFalse(rate_handler.should_wait())
        self.assertEqual(rate_handler.get_wait_time(), 0.0)

        # 测试状态获取
        status = rate_handler.get_status()
        self.assertIsInstance(status, dict)

    def test_semgrep_integration(self) -> None:
        """测试Semgrep集成"""
        # 创建Semgrep分析器
        semgrep_analyzer = SemgrepAnalyzer(rules_file=str(self.semgrep_rules_path))

        # 测试规则验证
        try:
            is_valid = semgrep_analyzer.validate_rules()
            # 如果Semgrep未安装，跳过测试
            if not is_valid:
                self.skipTest("Semgrep not installed")
        except Exception:
            self.skipTest("Semgrep not available")

        # 测试规则信息获取
        rule_info = semgrep_analyzer.get_rule_info()
        self.assertIn("rules_file", rule_info)
        self.assertIn("file_exists", rule_info)

    def test_edge_cases(self) -> None:
        """测试边界情况"""
        # 测试空搜索结果
        with patch("phpincludes.project_searcher.GitHubAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client.search_code_content.return_value = []
            mock_client_class.return_value = mock_client

            searcher = ProjectSearcher(
                github_token=self.mock_token,
                cache_manager=CacheManager(
                    db_path=str(self.temp_path / "test_cache.db")
                ),
            )

            try:
                results = searcher.search_projects(max_projects=1)
                self.assertEqual(len(results), 0)
            finally:
                searcher.close()

        # 测试无效的搜索结果
        result = SearchResult(
            owner="",
            repo_name="",
            url="",
            commit_hash="",
            star_count=0,
        )

        self.assertEqual(result.project_name, "/")
        self.assertFalse(result.is_qualified)
        self.assertEqual(result.detection_type, "unknown")


if __name__ == "__main__":
    unittest.main()
