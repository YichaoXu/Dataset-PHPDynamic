# PHP项目筛选系统设计文档

## Design Overview

**Classes**: `ProjectSearcher`, `PHPAnalyzer`, `SemgrepAnalyzer`, `SearchResult`, `CSVExporter`, `GitHubAPIClient`, `CacheManager`, `RateLimitHandler`, `Settings`
**Relationships**: `ProjectSearcher` orchestrates `GitHubAPIClient`, `PHPAnalyzer`, `SemgrepAnalyzer`, and `CSVExporter`, `PHPAnalyzer` uses `SemgrepAnalyzer` for fallback detection, `GitHubAPIClient` uses `CacheManager` and `RateLimitHandler`, `ProjectSearcher` creates `SearchResult` objects, all classes use `Settings` for configuration loading
**Abstract**: None
**Exceptions**: `GitHubAPIError`, `AnalysisError`, `SemgrepError`, `CacheError`, `RateLimitError`

## Core Design Principles

### Top Stars Project Selection
系统首先从GitHub Repository Search API获取指定数量的top stars PHP项目，按star数量降序排列。这确保了分析聚焦在流行且维护良好的项目上，提高结果质量。

### SuperGlobal Requirement
项目必须包含SuperGlobal参数使用（$_GET, $_POST, $_REQUEST, $_COOKIE, $_SESSION, $_SERVER, $_FILES, $_ENV）作为筛选的必要条件。只有在仓库发现后才进行此验证。

### Primary Function Detection
检测特殊动态函数调用：`call_user_func`, `call_user_func_array`, `forward_static_call`, `forward_static_call_array`，以及变量函数调用（`$var()`和`$$var()`）。

### Fallback Include Detection
当主要函数不存在时，使用Semgrep检测动态include/require语句，参数必须是非字符串字面量的表达式（排除纯字符串字面量，但包括包含变量的格式字符串）。

### Filtering Logic
严格的多层筛选：仓库选择和限制 → SuperGlobal检测（必要条件）→ 主要函数检测（优先级1）→ 备选检测（优先级2）。

### Streaming Batch Processing
采用流式批处理架构，分批获取和分析项目，每批处理完成后立即释放内存。默认批次大小为100个项目，可通过batch_size参数配置。这种设计避免了将所有项目同时保存在内存中，支持处理大量项目而不会导致内存溢出。

**内存使用模式**：
- 单批内存峰值：仓库元数据（`batch_size × ~2KB`） + SearchResult对象（`batch_size × ~5KB`） + 单个项目文件内容峰值（`max_files_per_project × ~30KB`） ≈ 1-2MB（batch_size=100）
- 内存释放策略：每个项目分析完成后立即释放文件内容，每批处理完成后未qualified项目对象可被GC回收，仅qualified项目的SearchResult对象保留在最终结果列表中
- 内存占用对比：处理1000个项目时，流式批处理峰值内存约1-2MB，而原有架构需要50-100MB（所有项目同时保存在内存中）

## Class Specifications

### ProjectSearcher Class
- **Responsibility**: 协调整个项目筛选流程，实现严格的筛选逻辑
- **Properties**: 
  - `github_client: GitHubAPIClient` - GitHub API客户端
  - `php_analyzer: PHPAnalyzer` - PHP代码分析器
  - `csv_exporter: CSVExporter` - CSV导出器
  - `semgrep_analyzer: SemgrepAnalyzer` - Semgrep分析器
  - `cache_manager: CacheManager` - 缓存管理器
  - `rate_limit_handler: RateLimitHandler` - 速率限制处理器

- **`search_projects(max_projects: int = None, export_csv: bool = True, include_unqualified: bool = False, batch_size: int = 100) -> List[SearchResult]`**
  - **Behavior**: 使用流式批处理方式执行完整的项目搜索和筛选流程。分批获取top stars PHP项目，对每批项目立即进行分析和筛选，避免将所有项目保存在内存中。流程：获取一批仓库 → 创建SearchResult对象 → 文件内容获取 → 分析 → 筛选 → 保存结果 → 释放内存 → 处理下一批
  - **Input**: max_projects（要搜索和分析的项目数量上限，默认从配置获取）, export_csv（是否导出CSV）, include_unqualified（是否包含不合格项目）, batch_size（每批处理的仓库数量，默认100）
  - **Output**: 符合条件的搜索结果列表（仅包含qualified项目）
  - **Raises**: `GitHubAPIError`, `AnalysisError`

- **`apply_filtering_logic(results: List[SearchResult]) -> List[SearchResult]`**
  - **Behavior**: 对一批搜索结果应用筛选逻辑：SuperGlobal检测（必要条件）→ 主要函数检测（优先级1）→ 备选检测（优先级2）。设计为处理单个批次，分析完成后立即返回结果，不保留文件内容在内存中。
  - **Input**: 一批搜索结果列表（通常来自单个批处理批次）
  - **Output**: 筛选后的搜索结果列表（仅qualified项目）
  - **Raises**: `AnalysisError`

- **`_process_batch(repository_items: List[Dict[str, Any]], batch_num: int, total_batches: int) -> List[SearchResult]`**
  - **Behavior**: 处理单个批次的仓库项目。创建SearchResult对象，获取文件内容，执行分析，应用筛选逻辑，返回qualified项目。处理完成后释放文件内容内存。
  - **Input**: repository_items（一批仓库元数据列表）, batch_num（当前批次编号）, total_batches（总批次数）
  - **Output**: 该批次中符合条件的搜索结果列表
  - **Raises**: `GitHubAPIError`, `AnalysisError`

### PHPAnalyzer Class
- **Responsibility**: 分析PHP代码，检测SuperGlobal、主要函数和动态include使用
- **Properties**: 
  - `semgrep_analyzer: SemgrepAnalyzer` - Semgrep分析器
  - `target_functions: List[str]` - 目标函数列表
  - `superglobals: List[str]` - SuperGlobal参数列表

- **`analyze_file_content(content: str) -> Dict[str, Any]`**
  - **Behavior**: 分析PHP文件内容，检测所有目标特征（SuperGlobal、主要函数、变量函数、动态include）
  - **Input**: PHP代码内容
  - **Output**: 分析结果字典
  - **Raises**: `AnalysisError`

- **`analyze_multiple_files(file_contents: Dict[str, str]) -> Dict[str, Dict[str, Any]]`**
  - **Behavior**: 分析多个PHP文件，返回每个文件的分析结果
  - **Input**: 文件路径到内容的映射
  - **Output**: 文件路径到分析结果的映射
  - **Raises**: `AnalysisError`

- **`check_superglobal_requirement(content: str) -> bool`**
  - **Behavior**: 检查SuperGlobal使用（必要条件）
  - **Input**: PHP代码内容
  - **Output**: 是否通过SuperGlobal检测
  - **Raises**: `AnalysisError`

- **`check_primary_functions(content: str) -> Dict[str, Any]`**
  - **Behavior**: 检查主要函数使用情况，包括call_user_func系列函数和变量函数调用（$var()和$$var()）
  - **Input**: PHP代码内容
  - **Output**: 主要函数检测结果
  - **Raises**: `AnalysisError`

- **`check_variable_functions(content: str) -> Dict[str, Any]`**
  - **Behavior**: 使用Semgrep检测变量函数调用
  - **Input**: PHP代码内容
  - **Output**: 变量函数检测结果
  - **Raises**: `SemgrepError`

- **`check_fallback_includes(content: str) -> Dict[str, Any]`**
  - **Behavior**: 使用Semgrep检查动态include语句（备选检测）
  - **Input**: PHP代码内容
  - **Output**: 动态include检测结果
  - **Raises**: `SemgrepError`

### SemgrepAnalyzer Class
- **Responsibility**: 使用Semgrep进行PHP静态分析，检测动态include/require语句和变量函数调用
- **Properties**: 
  - `semgrep_rules_path: str` - Semgrep规则文件路径
  - `semgrep_executable: str` - Semgrep可执行文件路径

- **`detect_dynamic_includes(content: str) -> Dict[str, List[Dict[str, Any]]]`**
  - **Behavior**: 检测动态include/require语句（参数为非字符串字面量，但包括包含变量的格式字符串）
  - **Input**: PHP代码内容
  - **Output**: 动态include检测结果（按规则ID分组）
  - **Raises**: `SemgrepError`

- **`detect_variable_functions(content: str) -> Dict[str, List[Dict[str, Any]]]`**
  - **Behavior**: 检测变量函数调用（$var()和$$var()）
  - **Input**: PHP代码内容
  - **Output**: 变量函数检测结果
  - **Raises**: `SemgrepError`

- **`run_semgrep(file_path: str, rules_path: str) -> List[Dict[str, Any]]`**
  - **Behavior**: 运行Semgrep分析指定文件，使用指定规则文件
  - **Input**: 文件路径、规则文件路径
  - **Output**: Semgrep结果列表
  - **Raises**: `SemgrepError`

### SearchResult Class
- **Responsibility**: 封装项目分析结果，支持CSV输出
- **Properties**: 
  - `owner: str` - 仓库所有者
  - `repo_name: str` - 仓库名称
  - `url: str` - 仓库URL
  - `commit_hash: str` - Commit哈希（SHA值）
  - `star_count: int` - Star数量
  - `analysis_result: Dict[str, Any]` - 分析结果字典

- **Properties (read-only):**
  - `project_name: str` - 完整项目名称（owner/repo_name）
  - `detection_type: str` - 检测类型（primary_functions/fallback_includes/none）
  - `superglobal_usage: List[str]` - SuperGlobal使用列表（去重后的类型）
  - `function_usage: List[str]` - 动态函数使用列表（去重后的函数名）
  - `dynamic_include_usage: List[str]` - 动态include使用列表（去重后的类型）
  - `is_qualified: bool` - 是否符合筛选条件
  - `priority: int` - 优先级（0=rejected, 1=fallback, 2=primary）
  - `rejection_reason: str` - 拒绝原因（如果不合格）

- **`to_csv_row() -> Dict[str, Any]`**
  - **Behavior**: 转换为CSV行格式
  - **Input**: None
  - **Output**: CSV行数据字典
  - **Raises**: None

- **`from_repository_item(repo_item: Dict[str, Any], analysis_result: Optional[Dict[str, Any]] = None, github_client: Optional[Any] = None) -> SearchResult`**
  - **Behavior**: 从GitHub仓库搜索结果创建SearchResult实例，自动获取commit SHA
  - **Input**: 仓库搜索结果项、分析结果、GitHub客户端（用于获取commit SHA）
  - **Output**: SearchResult实例
  - **Raises**: None

- **`update_analysis_result(analysis_result: Dict[str, Any]) -> None`**
  - **Behavior**: 更新分析结果
  - **Input**: 分析结果字典
  - **Output**: None
  - **Raises**: None

### CSVExporter Class
- **Responsibility**: 将搜索结果导出为CSV格式
- **Properties**: 
  - `output_dir: Path` - 输出目录路径

- **`export_results(results: List[SearchResult], include_unqualified: bool = False) -> str`**
  - **Behavior**: 导出搜索结果到CSV文件（基本格式）
  - **Input**: 搜索结果列表、是否包含不合格项目
  - **Output**: 输出文件路径
  - **Raises**: `IOError`, `ValueError`

- **`export_summary(results: List[SearchResult]) -> str`**
  - **Behavior**: 导出摘要信息到CSV文件（汇总统计）
  - **Input**: 搜索结果列表
  - **Output**: 输出文件路径
  - **Raises**: `IOError`, `ValueError`

- **`export_detailed_results(results: List[SearchResult]) -> str`**
  - **Behavior**: 导出详细结果到CSV文件（包含完整分析信息）
  - **Input**: 搜索结果列表
  - **Output**: 输出文件路径
  - **Raises**: `IOError`, `ValueError`

### GitHubAPIClient Class
- **Responsibility**: 管理与GitHub API的交互，遵循最佳实践
- **Properties**: 
  - `api_token: str` - GitHub API访问令牌
  - `cache_manager: CacheManager` - 缓存管理器
  - `rate_limit_handler: RateLimitHandler` - 速率限制处理器

- **`search_repositories_optimized(query: str, per_page: int = 100, page: int = 1) -> List[Dict[str, Any]]`**
  - **Behavior**: 使用GitHub Repository Search API搜索仓库，按star数量降序排列，支持分页
  - **Input**: 搜索查询、每页结果数量、页码
  - **Output**: 仓库搜索结果列表
  - **Raises**: `GitHubAPIError`

- **`get_branch_commit_sha(owner: str, repo: str, branch: str = "main") -> str`**
  - **Behavior**: 获取指定分支的commit SHA
  - **Input**: 仓库所有者、仓库名、分支名
  - **Output**: Commit SHA字符串
  - **Raises**: None

- **`get_repository_contents(owner: str, repo: str) -> List[Dict[str, Any]]`**
  - **Behavior**: 获取仓库根目录的文件和目录列表
  - **Input**: 仓库所有者、仓库名
  - **Output**: 文件/目录列表
  - **Raises**: `GitHubAPIError`

- **`get_file_content(owner: str, repo: str, file_path: str) -> str`**
  - **Behavior**: 获取指定文件的内容，使用缓存
  - **Input**: 仓库所有者、仓库名和文件路径
  - **Output**: 文件内容字符串
  - **Raises**: `GitHubAPIError`

- **`get_repository_info(owner: str, repo: str) -> Dict[str, Any]`**
  - **Behavior**: 获取仓库基本信息，包括star数量、默认分支等
  - **Input**: 仓库所有者、仓库名
  - **Output**: 仓库信息字典
  - **Raises**: `GitHubAPIError`

### CacheManager Class
- **Responsibility**: 管理API请求的缓存，避免重复查询
- **Properties**: 
  - `db_path: Path` - SQLite缓存数据库路径
  - `connection: sqlite3.Connection` - 数据库连接

- **`get(key: str) -> Optional[Any]`**
  - **Behavior**: 从缓存中获取数据，检查是否过期
  - **Input**: 缓存键
  - **Output**: 缓存的数据或None（如果不存在或已过期）
  - **Raises**: `CacheError`

- **`set(key: str, value: Any, expire_after: int = 3600) -> None`**
  - **Behavior**: 将数据存储到缓存，设置过期时间
  - **Input**: 缓存键、数据和过期时间（秒）
  - **Output**: None
  - **Raises**: `CacheError`

- **`generate_cache_key(url: str, params: Optional[Dict[str, Any]] = None) -> str`**
  - **Behavior**: 生成缓存键（基于URL和参数）
  - **Input**: URL和可选参数字典
  - **Output**: 缓存键字符串
  - **Raises**: None

- **`cleanup_expired() -> None`**
  - **Behavior**: 清理过期的缓存条目
  - **Input**: None
  - **Output**: None
  - **Raises**: `CacheError`

- **`get_stats() -> Dict[str, Any]`**
  - **Behavior**: 获取缓存统计信息
  - **Input**: None
  - **Output**: 统计信息字典
  - **Raises**: None

### RateLimitHandler Class
- **Responsibility**: 处理GitHub API速率限制
- **Properties**: 
  - `rate_limit_remaining: int` - 剩余请求次数
  - `rate_limit_reset: datetime` - 速率限制重置时间
  - `request_delay: float` - 请求间隔时间

- **`wait_if_needed() -> None`**
  - **Behavior**: 检查是否需要等待以遵守速率限制，如果需要则等待
  - **Input**: None
  - **Output**: None
  - **Raises**: `RateLimitError`

- **`update_from_response(response: requests.Response) -> None`**
  - **Behavior**: 从HTTP响应中更新速率限制信息
  - **Input**: HTTP响应对象
  - **Output**: None
  - **Raises**: None

- **`get_status() -> Dict[str, Any]`**
  - **Behavior**: 获取速率限制状态
  - **Input**: None
  - **Output**: 速率限制状态字典
  - **Raises**: None

### Settings Class
- **Responsibility**: 加载和格式化`config.yml`配置文件数据
- **Properties**: 
  - `CONFIG_FILE_PATH: Path` - 配置文件路径（`config.yml`）
  - `CONFIG_FILE_EXAMPLE_PATH: Path` - 配置模板文件路径（`config.yml.example`）
  - `CONFIG_FILE_ENV: str` - 配置文件路径环境变量名（`PHP_DYNCTRLFLOW_CONFIG`）
  - `PROJECT_NAME: str` - 项目名称
  - `PROJECT_VERSION: str` - 项目版本
  - `PROJECT_DESCRIPTION: str` - 项目描述
- **`get_github_token() -> str`**
  - **Behavior**: 从config.yml获取GitHub API令牌
  - **Input**: None
  - **Output**: GitHub API令牌
  - **Raises**: `ValueError`（如果令牌未找到）

- **`get_max_projects() -> int`**
  - **Behavior**: 获取最大项目数量
  - **Input**: None
  - **Output**: 最大项目数量
  - **Raises**: `KeyError`（如果配置不存在）

- **`get_max_files_per_project() -> int`**
  - **Behavior**: 获取每个项目的最大文件数
  - **Input**: None
  - **Output**: 最大文件数
  - **Raises**: `KeyError`（如果配置不存在）

- **`get_batch_size() -> int`**
  - **Behavior**: 获取流式处理的批次大小（每批处理的仓库数量）
  - **Input**: None
  - **Output**: 批次大小（默认100）
  - **Raises**: `KeyError`（如果配置不存在）

- **`get_cache_db_path() -> str`**
  - **Behavior**: 获取缓存数据库路径，自动创建父目录
  - **Input**: None
  - **Output**: 缓存数据库路径
  - **Raises**: `KeyError`（如果配置不存在）

- **`get_output_dir() -> str`**
  - **Behavior**: 获取输出目录路径，自动创建目录
  - **Input**: None
  - **Output**: 输出目录路径
  - **Raises**: `KeyError`（如果配置不存在）

- **`get_semgrep_rules_path() -> str`**
  - **Behavior**: 获取Semgrep规则文件路径
  - **Input**: None
  - **Output**: Semgrep规则文件路径
  - **Raises**: `KeyError`（如果配置不存在）

- **`get_php_file_extensions() -> List[str]`**
  - **Behavior**: 获取PHP文件扩展名列表
  - **Input**: None
  - **Output**: PHP文件扩展名列表
  - **Raises**: `KeyError`（如果配置不存在）

- **`is_php_file(filename: str) -> bool`**
  - **Behavior**: 检查文件是否为PHP文件
  - **Input**: 文件名
  - **Output**: 是否为PHP文件
  - **Raises**: None

- **`validate_config() -> Dict[str, bool]`**
  - **Behavior**: 验证配置文件，检查必需配置是否存在
  - **Input**: None
  - **Output**: 配置验证结果字典
  - **Raises**: None

## Exception Classes

### GitHubAPIError
当GitHub API请求失败或返回错误时抛出

### AnalysisError
当PHP代码分析过程中出现错误时抛出

### SemgrepError
当Semgrep静态分析失败时抛出

### CacheError
当缓存操作失败时抛出

### RateLimitError
当GitHub API速率限制被触发时抛出

## Semgrep Rules Configuration

Semgrep规则配置文件位于`php_dynctrlflow/semgrep/rules.yml`（内部实现细节），包含以下规则：

### Dynamic Include/Require Detection Rules

检测动态include/require语句，参数必须是非字符串字面量的表达式。使用`metavariable-regex`排除纯字符串字面量，但保留包含变量的格式字符串（如`"base_$var.php"`）。

**规则ID及检测模式**:

- **`dynamic-include-detection`**
  - **Pattern**: `include $EXPR;` 或 `include($EXPR);`
  - **Metavariable**: `$EXPR` 匹配非纯字符串字面量的表达式
  - **会匹配**: `include $file;`, `include $_GET['page'];`, `include $base . $path;`, `include getFile();`, `include "base_$var.php";`
  - **不匹配**: `include "file.php";`, `include 'file.php';`
  - **Confidence**: MEDIUM

- **`dynamic-include-once-detection`**
  - **Pattern**: `include_once $EXPR;` 或 `include_once($EXPR);`
  - **Metavariable**: `$EXPR` 匹配非纯字符串字面量的表达式
  - **Confidence**: MEDIUM

- **`dynamic-require-detection`**
  - **Pattern**: `require $EXPR;` 或 `require($EXPR);`
  - **Metavariable**: `$EXPR` 匹配非纯字符串字面量的表达式
  - **Confidence**: MEDIUM

- **`dynamic-require-once-detection`**
  - **Pattern**: `require_once $EXPR;` 或 `require_once($EXPR);`
  - **Metavariable**: `$EXPR` 匹配非纯字符串字面量的表达式
  - **Confidence**: MEDIUM

### String Concatenation Include Detection Rules

检测字符串拼接的include/require语句，具有更高的置信度。

- **`string-concatenation-include`**
  - **Pattern**: `include $VAR . $EXPR;`, `include($VAR . $EXPR);`, `include_once $VAR . $EXPR;`, `include_once($VAR . $EXPR);`, `require $VAR . $EXPR;`, `require($VAR . $EXPR);`, `require_once $VAR . $EXPR;`, `require_once($VAR . $EXPR);`
  - **检测**: 包含字符串拼接操作符（`.`)的include/require语句
  - **Confidence**: HIGH

### Function Call Include Detection Rules

检测函数调用的include/require语句，具有更高的置信度。

- **`function-call-include`**
  - **Pattern**: `include $FUNC(...);`, `include($FUNC(...));`, `include_once $FUNC(...);`, `include_once($FUNC(...));`, `require $FUNC(...);`, `require($FUNC(...));`, `require_once $FUNC(...);`, `require_once($FUNC(...));`
  - **检测**: 参数为函数调用结果的include/require语句
  - **Confidence**: HIGH

### Variable Function Call Detection Rules

检测变量函数调用，包括`$var()`和`$$var()`格式。

- **`variable-function-call`**
  - **Pattern**: `$VAR(...)` 或 `$$VAR(...)`
  - **检测**: 函数名为变量的动态函数调用
  - **会匹配**: `$func(...)`, `$$func(...)`
  - **不匹配**: 字符串字面量函数调用或直接函数调用（如`strlen()`）
  - **Confidence**: MEDIUM

### SuperGlobal Usage Detection Rules

检测SuperGlobal变量的使用。

- **`superglobal-usage`**
  - **Pattern**: `$_GET[...]`, `$_POST[...]`, `$_REQUEST[...]`, `$_COOKIE[...]`, `$_SESSION[...]`, `$_SERVER[...]`, `$_ENV[...]`, `$_FILES[...]`
  - **检测**: SuperGlobal变量的数组访问
  - **Confidence**: HIGH

### Dynamic Function Call Detection Rules

检测动态函数调用，使用`call_user_func`系列函数。

- **`dynamic-function-call`**
  - **Pattern**: `call_user_func(...)`, `call_user_func_array(...)`, `forward_static_call(...)`, `forward_static_call_array(...)`
  - **检测**: 动态函数调用，函数名通过参数传递
  - **Confidence**: HIGH

## Processing Flow

流式批处理架构，避免将所有项目保存在内存中：

```
1. Top Stars Discovery (Batch-based)
   ↓ (GitHub Repository Search API, sorted by stars, paginated)
2. Batch Iteration (Loop for each batch)
   ↓ (Process batch_size repositories at a time, default: 100)
   
   For each batch:
   ├─ 2.1. Repository Items Retrieval
   │     ↓ (Get batch_size repository metadata items)
   ├─ 2.2. SearchResult Creation (Per Item)
   │     ↓ (Convert to SearchResult object, get commit SHA)
   ├─ 2.3. File Content Retrieval (Per Item)
   │     ↓ (Scan repository root, fetch PHP files, limited to max_files_per_project)
   ├─ 2.4. Analysis (Per Item)
   │     ├─ 2.4.1. SuperGlobal Validation
   │     │     ↓ (必要条件检查)
   │     ├─ 2.4.2. Primary Function Analysis
   │     │     ↓ (call_user_func, variable functions等检测)
   │     └─ 2.4.3. Fallback Analysis (if needed)
   │           ↓ (Semgrep动态include检测)
   ├─ 2.5. Result Qualification (Per Item)
   │     ↓ (筛选逻辑应用，判断是否qualified)
   ├─ 2.6. Memory Release
   │     ↓ (释放文件内容内存，保留分析结果摘要)
   └─ 2.7. Accumulate Qualified Results
         ↓ (将qualified结果添加到结果列表)

3. Final Result Aggregation
   ↓ (合并所有批次的qualified结果)
4. Data Export
   ↓ (CSV格式输出，包含所有qualified项目)
```

**流式处理的优势**：
- **内存效率**：每批处理完后立即释放文件内容，避免大量数据同时占用内存
- **可扩展性**：支持处理大量项目（5000+）而不会导致内存溢出
- **即时反馈**：每批处理完成后可显示进度，用户可以了解处理状态
- **错误隔离**：单个批次的错误不会影响其他批次的处理

## Output Format

CSV文件仅包含下载和分析项目所需的基本信息：

- `project_name`: 项目名称（owner/repo_name格式），用于识别项目
- `owner`: 仓库所有者，用于Git克隆和下载
- `repo_name`: 仓库名称，用于Git克隆和下载
- `url`: 项目GitHub链接，用于访问和下载
- `commit_hash`: Commit哈希（SHA值），用于下载特定版本的代码
- `star_count`: Star数量，项目流行度指标
- `detection_type`: 检测类型（primary_functions/fallback_includes），表明项目是通过主要函数检测还是备选include检测发现的

## Target System File Structure

```
php-dynctrlflow/
├── php_dynctrlflow/
│   ├── __init__.py
│   ├── github_client.py          # GitHubAPIClient class
│   ├── cache_manager.py          # CacheManager class
│   ├── rate_limit_handler.py     # RateLimitHandler class
│   ├── semgrep_analyzer.py       # SemgrepAnalyzer class
│   ├── php_analyzer.py           # PHPAnalyzer class
│   ├── project_searcher.py       # ProjectSearcher class
│   ├── search_result.py          # SearchResult class
│   ├── csv_exporter.py           # CSVExporter class
│   ├── settings.py               # Settings class (configuration loader)
│   ├── cli.py                     # CLI interface (command-line argument parsing and main logic)
│   ├── __main__.py               # Package entry point (allows python -m php_dynctrlflow)
│   ├── semgrep/                  # Semgrep rules module (internal implementation)
│   │   ├── __init__.py
│   │   └── rules.yml              # Semgrep rules configuration (internal)
│   └── exceptions.py              # All exception classes
├── config.yml.example            # Configuration template with all default values
├── config.yml                    # User configuration file (git-ignored)
├── tests/
│   ├── __init__.py
│   ├── test_github_client.py
│   ├── test_cache_manager.py
│   ├── test_rate_limit_handler.py
│   ├── test_semgrep_analyzer.py
│   ├── test_php_analyzer.py
│   ├── test_project_searcher.py
│   ├── test_search_result.py
│   ├── test_csv_exporter.py
│   ├── test_exceptions.py
│   └── integration/
│       ├── __init__.py
│       └── test_end_to_end.py
├── docs/
│   ├── idea.md                   # Conceptual documentation
│   ├── design.md                 # Technical design specification
│   └── todo.md                   # Development task list
├── pyproject.toml                # Project configuration and dependencies
├── uv.lock                       # Locked dependency versions (managed by uv)
├── .gitignore                    # Git ignore rules
└── README.md                      # Project documentation

# Runtime directories (not in version control)
├── data/
│   ├── cache/                    # Cache storage directory
│   │   └── github_cache.db       # SQLite cache database
│   ├── temp/                     # Temporary files directory
│   └── output/                    # CSV output directory
│       └── php_projects.csv      # Generated results
├── .mypy_cache/                  # MyPy type checking cache
├── .ruff_cache/                  # Ruff linting cache
└── .semgrep/                     # Semgrep analysis cache
```

### File Structure Description

**Core Source Files (`php_dynctrlflow/`)**
- `github_client.py`: GitHub API交互和认证，包含Repository Search API、Repository Contents API、File Content API、Repository Info API和Commit SHA获取
- `cache_manager.py`: SQLite缓存管理功能，用于存储API响应
- `rate_limit_handler.py`: API速率限制处理，自动等待和限制请求频率
- `semgrep_analyzer.py`: Semgrep静态分析集成，检测动态include和变量函数调用
- `php_analyzer.py`: PHP代码分析协调器，整合Semgrep和正则表达式检测
- `project_searcher.py`: 主要协调逻辑，实现top stars项目发现、文件获取、分析和筛选流程
- `search_result.py`: 搜索结果数据模型，封装项目信息和分析结果
- `csv_exporter.py`: CSV导出功能，支持基本、摘要和详细三种格式
- `exceptions.py`: 所有异常类定义

**Configuration Files (Project Root)**
- `config.yml.example`: 配置文件模板，包含所有默认配置值（实际配置文件`config.yml`被Git忽略）
- `config.yml`: 用户配置文件（Git忽略）

**Core Source Files (`php_dynctrlflow/`) - Configuration & Internal Modules**
- `settings.py`: 配置加载和格式化处理类，从项目根目录的`config.yml`读取所有配置值
- `semgrep/rules.yml`: Semgrep规则配置文件（内部实现细节，不暴露给用户）
- `semgrep/__init__.py`: Semgrep模块初始化文件

**Testing (`tests/`)**
- 每个核心模块都有对应的测试文件
- `integration/`: 端到端集成测试

**Data Storage (`data/`)**
- `cache/`: 缓存数据存储（SQLite数据库）
- `temp/`: 临时文件存储
- `output/`: CSV结果输出（运行时生成，Git忽略）


**Project Root**
- `pyproject.toml`: 项目配置和元数据，使用uv进行依赖管理，定义入口点 `php-dynctrlflow = "php_dynctrlflow.cli:main"`
- `uv.lock`: 锁定的依赖版本（由uv管理）

**Entry Point (`php_dynctrlflow/`)**
- `cli.py`: CLI 接口（命令行参数解析和主要逻辑）
- `__main__.py`: 包入口点（允许 `python -m php_dynctrlflow` 运行，备选方式）
- 通过 `uv run php-dynctrlflow` 执行（推荐方式，使用 pyproject.toml 中定义的入口点 `php_dynctrlflow.cli:main`）