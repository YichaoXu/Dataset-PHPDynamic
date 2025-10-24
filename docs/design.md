# PHP项目查询脚本设计文档

## 项目筛选规则

### 筛选逻辑流程

1. **SuperGlobal检测（必要条件）**
   - 项目必须包含SuperGlobal参数使用（`$_GET`, `$_POST`, `$_REQUEST`, `$_COOKIE`, `$_SESSION`, `$_SERVER`, `$_FILES`, `$_ENV`）
   - 如果SuperGlobal检测失败，直接放弃该项目

2. **主要函数检测（优先级1）**
   - 检测特殊动态函数调用：`call_user_func`, `call_user_func_array`, `forward_static_call`, `forward_static_call_array`
   - 如果检测到任一函数，记录项目并输出

3. **备选检测（优先级2）**
   - 当主要函数不存在时，检测动态include/require语句
   - 检测`include`, `include_once`, `require`, `require_once`
   - 参数必须是非AST_STRING格式的表达式（字符串拼接、函数调用等）

4. **项目记录条件**
   - SuperGlobal检测通过 + （主要函数检测通过 或 备选检测通过）
   - 如果主要函数和备选检测都失败，放弃该项目

### 输出格式

符合条件的项目将输出到CSV文件，包含以下字段：
- `project_name`: 项目名称
- `owner`: 项目管理者/组织
- `url`: 项目链接
- `current_commit`: 当前commit哈希
- `stars_count`: Star数量
- `detection_type`: 检测类型（primary/fallback）
- `superglobal_usage`: 使用的SuperGlobal参数
- `function_usage`: 检测到的函数使用情况
- `dynamic_include_usage`: 动态include使用情况（如果适用）

## Design Overview

**Classes**: `GitHubAPIClient`, `PHPAnalyzer`, `ProjectSearcher`, `SearchResult`, `SearchCriteria`, `CacheManager`, `RateLimitHandler`, `SemgrepAnalyzer`, `CSVExporter`
**Relationships**: `ProjectSearcher` uses `GitHubAPIClient`, `PHPAnalyzer`, `SemgrepAnalyzer`, `CacheManager`, `RateLimitHandler`, and `CSVExporter`, `ProjectSearcher` creates `SearchResult`, `SearchCriteria` configures `ProjectSearcher`, `GitHubAPIClient` uses `CacheManager` and `RateLimitHandler`, `SemgrepAnalyzer` provides static analysis capabilities to `PHPAnalyzer`, `CSVExporter` exports `SearchResult` objects to CSV files
**Abstract**: None
**Exceptions**: `GitHubAPIError` extends `Exception`, `AnalysisError` extends `Exception`, `CacheError` extends `Exception`, `RateLimitError` extends `Exception`, `SemgrepError` extends `Exception`, raised by respective classes

## Class Specifications

### GitHubAPIClient Class
- **Responsibility**: 管理与GitHub API的交互，搜索PHP项目，遵循GitHub API最佳实践
- **Properties**: 
  - `api_token: str` - GitHub API访问令牌
  - `base_url: str` - GitHub API基础URL
  - `session: requests.Session` - HTTP会话对象
  - `cache_manager: CacheManager` - 缓存管理器
  - `rate_limit_handler: RateLimitHandler` - 速率限制处理器

- **`__init__(api_token: str, cache_manager: CacheManager, rate_limit_handler: RateLimitHandler) -> None`**
  - **Behavior**: 初始化GitHub API客户端，设置认证头和缓存
  - **Input**: GitHub API访问令牌、缓存管理器和速率限制处理器
  - **Output**: None
  - **Raises**: `GitHubAPIError` if token is invalid

- **`search_code_content(query: str, language: str = "PHP") -> List[Dict[str, Any]]`**
  - **Behavior**: 使用GitHub Code Search API搜索包含特定代码的仓库
  - **Input**: 搜索查询字符串和编程语言
  - **Output**: 代码搜索结果列表
  - **Raises**: `GitHubAPIError` if API request fails
  - **Note**: 优先使用Code Search API而非Repository Search API以减少请求次数

- **`get_repository_contents(owner: str, repo: str) -> List[Dict[str, Any]]`**
  - **Behavior**: 获取仓库的文件内容列表，使用缓存避免重复请求
  - **Input**: 仓库所有者和仓库名
  - **Output**: 文件内容信息列表
  - **Raises**: `GitHubAPIError` if API request fails

- **`get_file_content(owner: str, repo: str, file_path: str) -> str`**
  - **Behavior**: 获取指定文件的内容，使用条件请求和缓存
  - **Input**: 仓库所有者、仓库名和文件路径
  - **Output**: 文件内容字符串
  - **Raises**: `GitHubAPIError` if file not found or API request fails

- **`make_authenticated_request(url: str, params: Dict[str, Any] = None) -> requests.Response`**
  - **Behavior**: 发起经过身份验证的API请求，处理速率限制
  - **Input**: API URL和查询参数
  - **Output**: HTTP响应对象
  - **Raises**: `RateLimitError` if rate limit exceeded

- **Example Usage**:
```python
cache_manager = CacheManager()
rate_handler = RateLimitHandler()
client = GitHubAPIClient("your_token", cache_manager, rate_handler)
results = client.search_code_content("call_user_func language:PHP")
```

### CacheManager Class
- **Responsibility**: 管理API请求的缓存，避免重复查询，提高效率
- **Properties**: 
  - `cache_backend: str` - 缓存后端类型（sqlite, memory, redis）
  - `expire_after: int` - 缓存过期时间（秒）
  - `cache_db_path: str` - SQLite缓存数据库路径

- **`__init__(backend: str = "sqlite", expire_after: int = 3600, db_path: str = "github_cache.db") -> None`**
  - **Behavior**: 初始化缓存管理器
  - **Input**: 缓存后端类型、过期时间和数据库路径
  - **Output**: None
  - **Raises**: `CacheError` if cache initialization fails

- **`get(key: str) -> Optional[Any]`**
  - **Behavior**: 从缓存中获取数据
  - **Input**: 缓存键
  - **Output**: 缓存的数据或None
  - **Raises**: `CacheError` if cache read fails

- **`set(key: str, value: Any, expire_after: Optional[int] = None) -> None`**
  - **Behavior**: 将数据存储到缓存
  - **Input**: 缓存键、数据和过期时间
  - **Output**: None
  - **Raises**: `CacheError` if cache write fails

- **`delete(key: str) -> None`**
  - **Behavior**: 从缓存中删除数据
  - **Input**: 缓存键
  - **Output**: None
  - **Raises**: `CacheError` if cache delete fails

- **`clear() -> None`**
  - **Behavior**: 清空所有缓存
  - **Input**: None
  - **Output**: None
  - **Raises**: `CacheError` if cache clear fails

- **`generate_cache_key(url: str, params: Dict[str, Any] = None) -> str`**
  - **Behavior**: 生成缓存键
  - **Input**: URL和查询参数
  - **Output**: 缓存键字符串
  - **Raises**: None

- **Example Usage**:
```python
cache = CacheManager(backend="sqlite", expire_after=7200)
cached_data = cache.get("search_call_user_func")
```

### RateLimitHandler Class
- **Responsibility**: 处理GitHub API速率限制，确保请求符合最佳实践
- **Properties**: 
  - `rate_limit_remaining: int` - 剩余请求次数
  - `rate_limit_reset: datetime` - 速率限制重置时间
  - `retry_after: int` - 重试等待时间
  - `request_delay: float` - 请求间隔时间

- **`__init__(request_delay: float = 1.0) -> None`**
  - **Behavior**: 初始化速率限制处理器
  - **Input**: 请求间隔时间
  - **Output**: None
  - **Raises**: None

- **`check_rate_limit(response: requests.Response) -> None`**
  - **Behavior**: 检查响应中的速率限制信息
  - **Input**: HTTP响应对象
  - **Output**: None
  - **Raises**: `RateLimitError` if rate limit exceeded

- **`wait_for_rate_limit_reset() -> None`**
  - **Behavior**: 等待速率限制重置
  - **Input**: None
  - **Output**: None
  - **Raises**: `RateLimitError` if wait time exceeds maximum

- **`should_wait() -> bool`**
  - **Behavior**: 判断是否需要等待
  - **Input**: None
  - **Output**: 布尔值表示是否需要等待
  - **Raises**: None

- **`get_wait_time() -> float`**
  - **Behavior**: 获取需要等待的时间
  - **Input**: None
  - **Output**: 等待时间（秒）
  - **Raises**: None

- **Example Usage**:
```python
rate_handler = RateLimitHandler(request_delay=1.5)
rate_handler.check_rate_limit(response)
```

### SemgrepAnalyzer Class
- **Responsibility**: 使用Semgrep进行PHP静态分析，检测动态include/require语句
- **Properties**: 
  - `semgrep_rules_path: str` - Semgrep规则文件路径
  - `semgrep_executable: str` - Semgrep可执行文件路径
  - `temp_dir: str` - 临时文件目录

- **`__init__(rules_path: str = "semgrep_rules.yml", semgrep_path: str = "semgrep") -> None`**
  - **Behavior**: 初始化Semgrep分析器
  - **Input**: 规则文件路径和Semgrep可执行文件路径
  - **Output**: None
  - **Raises**: `SemgrepError` if semgrep not found or rules invalid

- **`analyze_code_content(content: str, file_path: str = "temp.php") -> List[Dict[str, Any]]`**
  - **Behavior**: 分析PHP代码内容，检测动态include/require语句
  - **Input**: PHP代码内容和文件路径
  - **Output**: Semgrep分析结果列表
  - **Raises**: `SemgrepError` if analysis fails

- **`detect_dynamic_includes(content: str) -> Dict[str, List[Dict[str, Any]]]`**
  - **Behavior**: 检测动态include/require语句（参数为非字符串字面量）
  - **Input**: PHP代码内容
  - **Output**: 动态include检测结果字典
  - **Raises**: `SemgrepError` if detection fails

- **`create_temp_file(content: str, filename: str = "temp.php") -> str`**
  - **Behavior**: 创建临时PHP文件用于Semgrep分析
  - **Input**: PHP代码内容和文件名
  - **Output**: 临时文件路径
  - **Raises**: `SemgrepError` if file creation fails

- **`run_semgrep(file_path: str) -> List[Dict[str, Any]]`**
  - **Behavior**: 运行Semgrep分析指定文件
  - **Input**: 文件路径
  - **Output**: Semgrep结果列表
  - **Raises**: `SemgrepError` if semgrep execution fails

- **`parse_semgrep_output(output: str) -> List[Dict[str, Any]]`**
  - **Behavior**: 解析Semgrep输出结果
  - **Input**: Semgrep输出字符串
  - **Output**: 解析后的结果列表
  - **Raises**: `SemgrepError` if parsing fails

- **`cleanup_temp_files() -> None`**
  - **Behavior**: 清理临时文件
  - **Input**: None
  - **Output**: None
  - **Raises**: None

- **Example Usage**:
```python
semgrep_analyzer = SemgrepAnalyzer("rules.yml")
results = semgrep_analyzer.detect_dynamic_includes(php_code)
```

### PHPAnalyzer Class
- **Responsibility**: 分析PHP代码，检测特定函数、SuperGlobal参数和动态include/require语句的使用
- **Properties**: 
  - `target_functions: List[str]` - 要检测的PHP函数列表
  - `superglobals: List[str]` - SuperGlobal参数列表
  - `semgrep_analyzer: SemgrepAnalyzer` - Semgrep分析器实例
  - `enable_dynamic_include_detection: bool` - 是否启用动态include检测

- **`__init__(target_functions: List[str] = None, superglobals: List[str] = None, enable_dynamic_include_detection: bool = True) -> None`**
  - **Behavior**: 初始化PHP分析器，设置检测目标和Semgrep分析器
  - **Input**: 目标函数列表、SuperGlobal参数列表和动态include检测开关
  - **Output**: None
  - **Raises**: `SemgrepError` if semgrep analyzer initialization fails

- **`analyze_file_content(content: str) -> Dict[str, Any]`**
  - **Behavior**: 分析PHP文件内容，检测目标函数、SuperGlobal和动态include的使用
  - **Input**: PHP文件内容字符串
  - **Output**: 分析结果字典
  - **Raises**: `AnalysisError` if content parsing fails

- **`contains_target_functions(content: str) -> bool`**
  - **Behavior**: 检查文件是否包含目标函数
  - **Input**: PHP文件内容
  - **Output**: 布尔值表示是否包含目标函数
  - **Raises**: `AnalysisError` if parsing fails

- **`contains_superglobals(content: str) -> bool`**
  - **Behavior**: 检查文件是否使用SuperGlobal参数
  - **Input**: PHP文件内容
  - **Output**: 布尔值表示是否使用SuperGlobal参数
  - **Raises**: `AnalysisError` if parsing fails

- **`contains_dynamic_includes(content: str) -> bool`**
  - **Behavior**: 检查文件是否包含动态include/require语句
  - **Input**: PHP文件内容
  - **Output**: 布尔值表示是否包含动态include语句
  - **Raises**: `AnalysisError` if analysis fails

- **`get_function_usage_details(content: str) -> Dict[str, List[str]]`**
  - **Behavior**: 获取函数使用的详细信息
  - **Input**: PHP文件内容
  - **Output**: 函数使用详情字典
  - **Raises**: `AnalysisError` if parsing fails

- **`get_dynamic_include_details(content: str) -> Dict[str, List[Dict[str, Any]]]`**
  - **Behavior**: 获取动态include/require语句的详细信息
  - **Input**: PHP文件内容
  - **Output**: 动态include使用详情字典
  - **Raises**: `AnalysisError` if analysis fails

- **`should_use_fallback_detection(function_results: Dict[str, Any]) -> bool`**
  - **Behavior**: 判断是否应该使用备选检测策略（动态include检测）
  - **Input**: 主要函数检测结果
  - **Output**: 布尔值表示是否使用备选检测
  - **Raises**: None

- **Example Usage**:
```python
analyzer = PHPAnalyzer(enable_dynamic_include_detection=True)
result = analyzer.analyze_file_content(php_code)
dynamic_includes = analyzer.get_dynamic_include_details(php_code)
```

### ProjectSearcher Class
- **Responsibility**: 协调GitHub API客户端和PHP分析器，执行完整的项目搜索流程，实现严格的筛选逻辑
- **Properties**: 
  - `github_client: GitHubAPIClient` - GitHub API客户端实例
  - `php_analyzer: PHPAnalyzer` - PHP分析器实例
  - `semgrep_analyzer: SemgrepAnalyzer` - Semgrep分析器实例
  - `search_criteria: SearchCriteria` - 搜索条件
  - `cache_manager: CacheManager` - 缓存管理器
  - `rate_limit_handler: RateLimitHandler` - 速率限制处理器
  - `csv_exporter: CSVExporter` - CSV输出处理器

- **`__init__(api_token: str, search_criteria: SearchCriteria) -> None`**
  - **Behavior**: 初始化项目搜索器，创建所有必要的组件
  - **Input**: GitHub API令牌和搜索条件
  - **Output**: None
  - **Raises**: `GitHubAPIError` if client initialization fails

- **`search_projects() -> List[SearchResult]`**
  - **Behavior**: 执行完整的项目搜索流程，按照筛选规则严格筛选项目
  - **Input**: None
  - **Output**: 符合条件的搜索结果列表
  - **Raises**: `GitHubAPIError`, `AnalysisError` if search or analysis fails

- **`apply_filtering_logic(repo_data: Dict[str, Any]) -> Optional[SearchResult]`**
  - **Behavior**: 应用筛选逻辑：SuperGlobal检测 -> 主要函数检测 -> 备选检测
  - **Input**: 仓库数据
  - **Output**: 搜索结果对象或None（如果不符合条件）
  - **Raises**: `AnalysisError` if analysis fails

- **`check_superglobal_requirement(content: str) -> bool`**
  - **Behavior**: 检查项目是否包含SuperGlobal使用（必要条件）
  - **Input**: PHP代码内容
  - **Output**: 布尔值表示是否通过SuperGlobal检测
  - **Raises**: `AnalysisError` if analysis fails

- **`check_primary_functions(content: str) -> Dict[str, Any]`**
  - **Behavior**: 检查主要函数使用情况
  - **Input**: PHP代码内容
  - **Output**: 主要函数检测结果字典
  - **Raises**: `AnalysisError` if analysis fails

- **`check_fallback_includes(content: str) -> Dict[str, Any]`**
  - **Behavior**: 检查备选动态include语句
  - **Input**: PHP代码内容
  - **Output**: 动态include检测结果字典
  - **Raises**: `AnalysisError` if analysis fails

- **`build_optimized_search_queries() -> List[str]`**
  - **Behavior**: 构建优化的搜索查询，优先搜索SuperGlobal使用
  - **Input**: None
  - **Output**: 搜索查询列表
  - **Raises**: None
  - **Note**: 使用Code Search API的组合查询，优先搜索SuperGlobal使用

- **`filter_repositories_by_criteria(repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]`**
  - **Behavior**: 根据搜索条件过滤仓库，使用缓存避免重复分析
  - **Input**: 仓库信息列表
  - **Output**: 过滤后的仓库列表
  - **Raises**: None

- **`analyze_repository_batch(repositories: List[Dict[str, Any]]) -> List[SearchResult]`**
  - **Behavior**: 批量分析多个仓库，应用严格筛选逻辑
  - **Input**: 仓库信息列表
  - **Output**: 符合条件的搜索结果列表
  - **Raises**: `AnalysisError` if analysis fails

- **`deduplicate_repositories(repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]`**
  - **Behavior**: 去重仓库列表，避免重复分析
  - **Input**: 仓库信息列表
  - **Output**: 去重后的仓库列表
  - **Raises**: None

- **`export_results_to_csv(results: List[SearchResult], output_file: str) -> None`**
  - **Behavior**: 将搜索结果导出到CSV文件
  - **Input**: 搜索结果列表和输出文件路径
  - **Output**: None
  - **Raises**: `IOError` if file write fails

- **Example Usage**:
```python
criteria = SearchCriteria()
searcher = ProjectSearcher("token", criteria)
results = searcher.search_projects()
searcher.export_results_to_csv(results, "php_projects.csv")
```

### SearchResult Class
- **Responsibility**: 封装单个项目的搜索结果，包括主要和备选检测结果，支持CSV输出
- **Properties**: 
  - `repository_name: str` - 仓库名称
  - `owner: str` - 仓库所有者
  - `url: str` - 仓库URL
  - `current_commit: str` - 当前commit哈希
  - `stars_count: int` - Star数量
  - `matches_criteria: bool` - 是否匹配搜索条件
  - `function_usage: Dict[str, List[str]]` - 函数使用详情
  - `dynamic_include_usage: Dict[str, List[Dict[str, Any]]]` - 动态include使用详情
  - `superglobal_usage: List[str]` - SuperGlobal使用列表
  - `analysis_summary: str` - 分析摘要
  - `detection_type: str` - 检测类型（primary/fallback）

- **`__init__(repository_name: str, owner: str, url: str, current_commit: str = "", stars_count: int = 0) -> None`**
  - **Behavior**: 初始化搜索结果
  - **Input**: 仓库名称、所有者、URL、当前commit和star数量
  - **Output**: None
  - **Raises**: None

- **`add_analysis_result(function_usage: Dict[str, List[str]], superglobal_usage: List[str], dynamic_include_usage: Dict[str, List[Dict[str, Any]]] = None, detection_type: str = "primary") -> None`**
  - **Behavior**: 添加分析结果到搜索结果
  - **Input**: 函数使用详情、SuperGlobal使用列表、动态include使用详情和检测类型
  - **Output**: None
  - **Raises**: None

- **`to_dict() -> Dict[str, Any]`**
  - **Behavior**: 将搜索结果转换为字典格式
  - **Input**: None
  - **Output**: 字典格式的搜索结果
  - **Raises**: None

- **`to_csv_row() -> Dict[str, Any]`**
  - **Behavior**: 将搜索结果转换为CSV行格式
  - **Input**: None
  - **Output**: CSV行数据字典
  - **Raises**: None

- **`has_primary_targets() -> bool`**
  - **Behavior**: 检查是否包含主要检测目标
  - **Input**: None
  - **Output**: 布尔值表示是否包含主要目标
  - **Raises**: None

- **`has_fallback_targets() -> bool`**
  - **Behavior**: 检查是否包含备选检测目标
  - **Input**: None
  - **Output**: 布尔值表示是否包含备选目标
  - **Raises**: None

- **`is_qualified() -> bool`**
  - **Behavior**: 检查项目是否符合筛选条件
  - **Input**: None
  - **Output**: 布尔值表示是否符合条件
  - **Raises**: None

- **Example Usage**:
```python
result = SearchResult("repo", "owner", "https://github.com/owner/repo", "abc123", 100)
result.add_analysis_result(func_usage, superglobal_usage, dynamic_include_usage, "fallback")
csv_row = result.to_csv_row()
```

### CSVExporter Class
- **Responsibility**: 处理CSV文件输出，将搜索结果导出为CSV格式
- **Properties**: 
  - `output_file: str` - 输出文件路径
  - `csv_headers: List[str]` - CSV文件头部字段
  - `encoding: str` - 文件编码格式

- **`__init__(output_file: str = "php_projects.csv", encoding: str = "utf-8") -> None`**
  - **Behavior**: 初始化CSV导出器
  - **Input**: 输出文件路径和编码格式
  - **Output**: None
  - **Raises**: None

- **`export_results(results: List[SearchResult]) -> None`**
  - **Behavior**: 导出搜索结果到CSV文件
  - **Input**: 搜索结果列表
  - **Output**: None
  - **Raises**: `IOError` if file write fails

- **`write_header() -> None`**
  - **Behavior**: 写入CSV文件头部
  - **Input**: None
  - **Output**: None
  - **Raises**: `IOError` if file write fails

- **`write_result_row(result: SearchResult) -> None`**
  - **Behavior**: 写入单个搜索结果的CSV行
  - **Input**: 搜索结果对象
  - **Output**: None
  - **Raises**: `IOError` if file write fails

- **`format_superglobal_usage(superglobal_usage: List[str]) -> str`**
  - **Behavior**: 格式化SuperGlobal使用信息为字符串
  - **Input**: SuperGlobal使用列表
  - **Output**: 格式化后的字符串
  - **Raises**: None

- **`format_function_usage(function_usage: Dict[str, List[str]]) -> str`**
  - **Behavior**: 格式化函数使用信息为字符串
  - **Input**: 函数使用字典
  - **Output**: 格式化后的字符串
  - **Raises**: None

- **`format_dynamic_include_usage(dynamic_include_usage: Dict[str, List[Dict[str, Any]]]) -> str`**
  - **Behavior**: 格式化动态include使用信息为字符串
  - **Input**: 动态include使用字典
  - **Output**: 格式化后的字符串
  - **Raises**: None

- **Example Usage**:
```python
exporter = CSVExporter("results.csv")
exporter.export_results(search_results)
```

### SearchCriteria Class
- **Responsibility**: 定义搜索条件和配置参数，包括主要和备选检测目标
- **Properties**: 
  - `target_functions: List[str]` - 目标PHP函数列表
  - `superglobals: List[str]` - SuperGlobal参数列表
  - `dynamic_includes: List[str]` - 动态include/require语句列表
  - `max_repositories: int` - 最大搜索仓库数量
  - `min_stars: int` - 最小星数要求
  - `language: str` - 编程语言过滤
  - `fallback_to_includes: bool` - 是否在主要函数不存在时使用备选检测

- **`__init__(target_functions: List[str] = None, superglobals: List[str] = None, dynamic_includes: List[str] = None, max_repositories: int = 100, fallback_to_includes: bool = True) -> None`**
  - **Behavior**: 初始化搜索条件
  - **Input**: 目标函数、SuperGlobal参数、动态include语句、最大仓库数量和备选检测开关
  - **Output**: None
  - **Raises**: None

- **`get_default_target_functions() -> List[str]`**
  - **Behavior**: 获取默认的目标函数列表
  - **Input**: None
  - **Output**: 默认函数列表
  - **Raises**: None

- **`get_default_superglobals() -> List[str]`**
  - **Behavior**: 获取默认的SuperGlobal参数列表
  - **Input**: None
  - **Output**: 默认SuperGlobal列表
  - **Raises**: None

- **`get_default_dynamic_includes() -> List[str]`**
  - **Behavior**: 获取默认的动态include/require语句列表
  - **Input**: None
  - **Output**: 默认动态include列表
  - **Raises**: None

- **`validate() -> bool`**
  - **Behavior**: 验证搜索条件的有效性
  - **Input**: None
  - **Output**: 布尔值表示条件是否有效
  - **Raises**: None

- **`should_use_fallback() -> bool`**
  - **Behavior**: 判断是否应该使用备选检测策略
  - **Input**: None
  - **Output**: 布尔值表示是否使用备选检测
  - **Raises**: None

- **Example Usage**:
```python
criteria = SearchCriteria()
criteria.target_functions = ["call_user_func", "call_user_func_array"]
criteria.dynamic_includes = ["include", "require"]
criteria.fallback_to_includes = True
```

## Exception Classes

### GitHubAPIError
当GitHub API请求失败或返回错误时抛出

### AnalysisError
当PHP代码分析过程中出现错误时抛出

### CacheError
当缓存操作失败时抛出

### RateLimitError
当GitHub API速率限制被触发时抛出

### SemgrepError
当Semgrep静态分析失败时抛出

## GitHub API Best Practices

### Authentication
- 使用个人访问令牌(PAT)进行身份验证，提高速率限制阈值
- 令牌应具有适当的权限范围（repo, read:user等）

### Rate Limiting
- 遵循GitHub API速率限制：认证用户5000请求/小时，未认证用户60请求/小时
- 实现指数退避重试机制
- 监控`X-RateLimit-Remaining`和`X-RateLimit-Reset`头部
- 在可变请求之间至少间隔1秒

### Query Optimization
- 优先使用Code Search API而非Repository Search API
- 使用精确的搜索查询减少结果集大小
- 实现分页处理，避免单次请求过大
- 使用条件请求（ETag, Last-Modified）避免重复获取未更改的数据

### Caching Strategy
- 实现多层缓存：内存缓存用于频繁访问的数据，持久化缓存用于长期存储
- 设置合理的缓存过期时间：搜索结果1-2小时，文件内容30分钟
- 使用缓存键包含查询参数，确保缓存准确性

### Error Handling
- 实现完整的错误处理机制
- 区分不同类型的错误（网络错误、API错误、解析错误）
- 提供有意义的错误消息和恢复建议

## Validation Rules

### SearchCriteria Validation
- target_functions列表不能为空（除非启用备选检测）
- superglobals列表不能为空
- dynamic_includes列表不能为空（当启用备选检测时）
- max_repositories必须大于0
- min_stars必须大于等于0
- fallback_to_includes必须是布尔值

### GitHubAPIClient Validation
- API token不能为空
- API token必须是有效的GitHub token格式
- 缓存管理器必须正确初始化

### CacheManager Validation
- 缓存后端类型必须是支持的类型（sqlite, memory, redis）
- 缓存过期时间必须大于0
- 数据库路径必须有效

### RateLimitHandler Validation
- 请求间隔时间必须大于0
- 速率限制信息必须有效

### SemgrepAnalyzer Validation
- Semgrep可执行文件必须存在
- 规则文件必须有效且格式正确
- 临时目录必须可写

### PHPAnalyzer Validation
- 文件内容必须是有效的PHP代码
- 目标函数列表必须包含有效的PHP函数名
- 动态include列表必须包含有效的PHP语句名
- Semgrep分析器必须正确初始化（如果使用）

## Semgrep Rules Configuration

### Dynamic Include/Require Detection Rules

以下Semgrep规则用于检测PHP代码中的动态include/require语句（参数为非字符串字面量）：

```yaml
rules:
  - id: dynamic-include-detection
    languages: [php]
    message: "Detected dynamic include statement with non-string literal argument"
    severity: WARNING
    patterns:
      - pattern: include($ARG);
      - metavariable-pattern:
          metavariable: $ARG
          pattern-not: "'...'"
          pattern-not: '"..."'

  - id: dynamic-include-once-detection
    languages: [php]
    message: "Detected dynamic include_once statement with non-string literal argument"
    severity: WARNING
    patterns:
      - pattern: include_once($ARG);
      - metavariable-pattern:
          metavariable: $ARG
          pattern-not: "'...'"
          pattern-not: '"..."'

  - id: dynamic-require-detection
    languages: [php]
    message: "Detected dynamic require statement with non-string literal argument"
    severity: WARNING
    patterns:
      - pattern: require($ARG);
      - metavariable-pattern:
          metavariable: $ARG
          pattern-not: "'...'"
          pattern-not: '"..."'

  - id: dynamic-require-once-detection
    languages: [php]
    message: "Detected dynamic require_once statement with non-string literal argument"
    severity: WARNING
    patterns:
      - pattern: require_once($ARG);
      - metavariable-pattern:
          metavariable: $ARG
          pattern-not: "'...'"
          pattern-not: '"..."'

  - id: string-concatenation-include
    languages: [php]
    message: "Detected include with string concatenation"
    severity: WARNING
    patterns:
      - pattern: include($VAR . $STR);
      - pattern: include($STR . $VAR);
      - pattern: include($VAR . $VAR);

  - id: function-call-include
    languages: [php]
    message: "Detected include with function call argument"
    severity: WARNING
    patterns:
      - pattern: include($FUNC(...));
      - pattern: include_once($FUNC(...));
      - pattern: require($FUNC(...));
      - pattern: require_once($FUNC(...));
```

### Rule Usage Notes

- **Metavariable Patterns**: 使用`pattern-not`排除字符串字面量，确保只检测动态表达式
- **String Concatenation**: 检测字符串拼接操作（如`$base . '/config.php'`）
- **Function Calls**: 检测函数调用作为参数（如`get_template() . '.php'`）
- **Variable Usage**: 检测变量作为参数（如`include $template`）

### Integration with PHPAnalyzer

这些规则将被`SemgrepAnalyzer`类使用，通过以下方式集成：

1. **规则文件管理**: 规则保存在`semgrep_rules.yml`文件中
2. **动态分析**: `detect_dynamic_includes()`方法使用这些规则
3. **结果解析**: `parse_semgrep_output()`方法解析Semgrep输出
4. **缓存优化**: 分析结果可以被缓存以提高性能

## 筛选逻辑流程图

```
开始搜索项目
    ↓
搜索GitHub仓库（优先搜索SuperGlobal使用）
    ↓
对每个仓库应用筛选逻辑：
    ↓
1. SuperGlobal检测
    ↓
   [SuperGlobal存在？]
    ↓ 否
   放弃项目
    ↓ 是
2. 主要函数检测
    ↓
   [主要函数存在？]
    ↓ 是                    ↓ 否
   记录项目（primary）     3. 备选检测
    ↓                      ↓
   输出到CSV              [动态include存在？]
                           ↓ 是        ↓ 否
                          记录项目    放弃项目
                          (fallback)
                           ↓
                          输出到CSV
    ↓
继续下一个项目
    ↓
完成搜索，生成CSV报告
```
