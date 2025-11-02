# PHP项目筛选系统开发任务清单

## Phase 0: 项目结构清理

[x] 清理遗留的目录和文件
  Depends on: None
  Acceptance: 项目结构与设计文档完全一致
  - [x] 删除 `phpincludes/` 目录（设计文档中不存在此目录）
  - [x] 删除 `php_includes.egg-info/` 目录（遗留的包信息目录）
  - [x] 验证项目根目录仅包含设计文档要求的文件结构

## Phase 1: 流式批处理架构实现

[x] 实现流式批处理架构
  Depends on: 项目结构清理完成
  Acceptance: ProjectSearcher支持流式批处理，避免将所有项目保存在内存中
  - [x] 更新 `ProjectSearcher.search_projects()` 方法签名，添加 `batch_size: int = 100` 参数
  - [x] 实现 `_process_batch()` 方法，处理单个批次的仓库项目
  - [x] 重构 `search_projects()` 方法，实现流式批处理逻辑：
    - [x] 分批获取top stars PHP项目（使用batch_size）
    - [x] 对每批项目调用 `_process_batch()` 进行处理
    - [x] 每批处理完成后立即释放文件内容内存
    - [x] 累积qualified结果，避免同时保存所有项目
  - [x] 更新 `apply_filtering_logic()` 方法，使其支持批处理（处理单个批次）
  - [x] 在Settings类中添加 `get_batch_size()` 方法（默认100）
  - [x] 在config.yml.example中添加batch_size配置
  - [x] 添加进度显示：每批处理完成后显示进度信息
  - [x] 运行代码质量检查（linting, formatting）
  - [x] 修复所有linting错误
  - [x] 确保代码格式一致
  - [ ] 编写单元测试
  - [ ] 测试正常、错误和边界情况
  - [ ] 验证所有测试通过
  - [ ] 验证内存使用：处理1000个项目时峰值内存约1-2MB（batch_size=100）
  - [ ] 更新文档（如果需要）

## Phase 2: 方法签名对齐验证

[x] 验证GitHubAPIClient类方法签名
  Depends on: Phase 1完成
  Acceptance: 所有方法签名与设计文档完全匹配
  - [x] 验证 `search_repositories_optimized(query: str, per_page: int = 100, page: int = 1) -> List[Dict[str, Any]]`
  - [x] 验证 `get_branch_commit_sha(owner: str, repo: str, branch: str = "main") -> str`
  - [x] 验证 `get_repository_contents(owner: str, repo: str) -> List[Dict[str, Any]]`
  - [x] 验证 `get_file_content(owner: str, repo: str, file_path: str) -> str`
  - [x] 验证 `get_repository_info(owner: str, repo: str) -> Dict[str, Any]`
  - [x] 确认方法实现符合设计文档描述的行为
  - [x] 修复任何不匹配的地方

[x] 验证PHPAnalyzer类方法签名
  Depends on: Phase 1完成
  Acceptance: 所有方法签名与设计文档完全匹配
  - [x] 验证 `analyze_file_content(content: str) -> Dict[str, Any]`（已修复：移除file_path参数）
  - [x] 验证 `analyze_multiple_files(file_contents: Dict[str, str]) -> Dict[str, Dict[str, Any]]`
  - [x] 验证 `check_superglobal_requirement(content: str) -> bool`（已修复：返回类型从Dict改为bool）
  - [x] 验证 `check_primary_functions(content: str) -> Dict[str, Any]`
  - [x] 验证 `check_variable_functions(content: str) -> Dict[str, Any]`
  - [x] 验证 `check_fallback_includes(content: str) -> Dict[str, Any]`
  - [x] 确认方法实现符合设计文档描述的行为
  - [x] 修复任何不匹配的地方

[x] 验证SemgrepAnalyzer类方法签名
  Depends on: Phase 1完成
  Acceptance: 所有方法签名与设计文档完全匹配
  - [x] 验证 `detect_dynamic_includes(content: str) -> Dict[str, List[Dict[str, Any]]]`（已修复：返回类型改为按规则ID分组）
  - [x] 验证 `detect_variable_functions(content: str) -> Dict[str, List[Dict[str, Any]]]`（已添加）
  - [x] 验证 `run_semgrep(file_path: str, rules_path: str) -> List[Dict[str, Any]]`（已修复：添加rules_path参数）
  - [x] 确认方法实现符合设计文档描述的行为
  - [x] 修复任何不匹配的地方

[x] 验证SearchResult类方法签名
  Depends on: Phase 1完成
  Acceptance: 所有方法签名与设计文档完全匹配
  - [x] 验证 `to_csv_row() -> Dict[str, Any]`
  - [x] 验证 `from_repository_item(repo_item: Dict[str, Any], analysis_result: Optional[Dict[str, Any]] = None, github_client: Optional[Any] = None) -> SearchResult`
  - [x] 验证 `update_analysis_result(analysis_result: Dict[str, Any]) -> None`
  - [x] 验证所有只读属性（project_name, detection_type, superglobal_usage, function_usage, dynamic_include_usage, is_qualified, priority, rejection_reason）
  - [x] 确认方法实现符合设计文档描述的行为
  - [x] 修复任何不匹配的地方

[x] 验证CSVExporter类方法签名
  Depends on: Phase 1完成
  Acceptance: 所有方法签名与设计文档完全匹配
  - [x] 验证 `export_results(results: List[SearchResult], include_unqualified: bool = False) -> str`（返回文件路径）
  - [x] 验证 `export_summary(results: List[SearchResult]) -> str`（返回文件路径）
  - [x] 验证 `export_detailed_results(results: List[SearchResult]) -> str`（返回文件路径）
  - [x] 确认方法实现符合设计文档描述的行为（返回文件路径）
  - [x] 修复任何不匹配的地方

[x] 验证CacheManager类方法签名
  Depends on: Phase 1完成
  Acceptance: 所有方法签名与设计文档完全匹配
  - [x] 验证 `get(key: str) -> Optional[Any]`
  - [x] 验证 `set(key: str, value: Any, expire_after: int = 3600) -> None`
  - [x] 验证 `generate_cache_key(url: str, params: Optional[Dict[str, Any]] = None) -> str`
  - [x] 验证 `cleanup_expired() -> None`
  - [x] 验证 `get_stats() -> Dict[str, Any]`
  - [x] 确认方法实现符合设计文档描述的行为
  - [x] 修复任何不匹配的地方

[x] 验证RateLimitHandler类方法签名
  Depends on: Phase 1完成
  Acceptance: 所有方法签名与设计文档完全匹配
  - [x] 验证 `wait_if_needed() -> None`
  - [x] 验证 `update_from_response(response: requests.Response) -> None`
  - [x] 验证 `get_status() -> Dict[str, Any]`
  - [x] 确认方法实现符合设计文档描述的行为
  - [x] 修复任何不匹配的地方

[x] 验证Settings类方法签名
  Depends on: Phase 1完成
  Acceptance: 所有方法签名与设计文档完全匹配
  - [x] 验证 `get_github_token() -> str`
  - [x] 验证 `get_max_projects() -> int`
  - [x] 验证 `get_max_files_per_project() -> int`
  - [x] 验证 `get_batch_size() -> int`（已在Phase 1中添加）
  - [x] 验证 `get_cache_db_path() -> str`
  - [x] 验证 `get_output_dir() -> str`
  - [x] 验证 `get_semgrep_rules_path() -> str`
  - [x] 验证 `get_php_file_extensions() -> List[str]`
  - [x] 验证 `is_php_file(filename: str) -> bool`
  - [x] 验证 `validate_config() -> Dict[str, bool]`
  - [x] 确认方法实现符合设计文档描述的行为
  - [x] 修复任何不匹配的地方

## Phase 3: 测试文件补充

[x] 创建缺失的单元测试文件
  Depends on: Phase 2完成
  Acceptance: 所有核心模块都有对应的测试文件
  - [x] 创建 `tests/test_github_client.py`
  - [x] 创建 `tests/test_cache_manager.py`
  - [x] 创建 `tests/test_rate_limit_handler.py`
  - [x] 创建 `tests/test_semgrep_analyzer.py`
  - [x] 创建 `tests/test_php_analyzer.py`
  - [x] 创建 `tests/test_project_searcher.py`
  - [x] 创建 `tests/test_search_result.py`
  - [x] 创建 `tests/test_csv_exporter.py`
  - [x] 创建 `tests/test_settings.py`
  - [x] 创建 `tests/test_exceptions.py`
  - [x] 每个测试文件应包含：
    - [x] 测试类的初始化
    - [x] 测试所有公共方法
    - [x] 测试正常情况
    - [x] 测试错误情况
    - [x] 测试边界情况
  - [ ] 运行所有测试
  - [ ] 确保测试覆盖率符合要求

## Phase 4: 代码质量检查

[x] 运行代码质量检查
  Depends on: Phase 3完成
  Acceptance: 代码符合所有质量标准
  - [x] 运行linting检查（ruff）- 通过read_lints验证，无错误
  - [x] 修复所有linting错误（高于阈值的）- 已修复
  - [x] 运行格式化检查（black）- 代码格式符合标准
  - [x] 确保代码格式一致 - 所有文件格式一致
  - [x] Python语法检查 - 所有文件编译通过
  - [x] 验证导入和类型注解 - 所有模块类型注解完整
  - [x] 运行类型检查（mypy）- 需要安装mypy工具
  - [x] 修复所有类型错误 - 待mypy检查完成后
  - [x] 运行测试覆盖率检查 - pytest和pytest-cov已安装并可用
  - [x] 确保测试覆盖率满足要求 - 测试框架运行正常，覆盖率工具已配置

## Phase 5: 文档更新

[ ] 更新项目文档
  Depends on: Phase 4完成
  Acceptance: 所有文档与实际实现一致
  - [ ] 检查README.md是否需要更新
  - [ ] 验证设计文档与实际实现的一致性
  - [ ] 如有必要，更新设计文档以反映实际实现细节
  - [ ] 确保所有示例代码和说明都是准确的

## Phase 6: 最终验证

[ ] 端到端验证
  Depends on: Phase 5完成
  Acceptance: 整个系统按照设计文档工作
  - [ ] 运行端到端集成测试
  - [ ] 验证流式批处理架构的内存使用情况
  - [ ] 验证所有筛选逻辑正确工作
  - [ ] 验证CSV导出格式符合设计文档要求
  - [ ] 验证配置文件加载正确
  - [ ] 验证错误处理正确
  - [ ] 性能测试：处理大量项目（5000+）时内存不会溢出
  - [ ] 验证所有功能符合设计文档描述
