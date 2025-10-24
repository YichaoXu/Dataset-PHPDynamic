# PHP项目筛选系统设计文档

## Design Overview

**Classes**: `ProjectSearcher`, `PHPAnalyzer`, `SemgrepAnalyzer`, `SearchResult`, `CSVExporter`, `GitHubAPIClient`, `CacheManager`, `RateLimitHandler`
**Relationships**: `ProjectSearcher` orchestrates `GitHubAPIClient`, `PHPAnalyzer`, `SemgrepAnalyzer`, and `CSVExporter`, `PHPAnalyzer` uses `SemgrepAnalyzer` for fallback detection, `GitHubAPIClient` uses `CacheManager` and `RateLimitHandler`, `ProjectSearcher` creates `SearchResult` objects
**Abstract**: None
**Exceptions**: `GitHubAPIError`, `AnalysisError`, `SemgrepError`, `CacheError`, `RateLimitError`

## Core Design Principles

### SuperGlobal Requirement
项目必须包含SuperGlobal参数使用（$_GET, $_POST, $_REQUEST, $_COOKIE, $_SESSION, $_SERVER, $_FILES, $_ENV）作为筛选的必要条件。

### Primary Function Detection
检测特殊动态函数调用：`call_user_func`, `call_user_func_array`, `forward_static_call`, `forward_static_call_array`。

### Fallback Include Detection
当主要函数不存在时，使用Semgrep检测动态include/require语句，参数必须是非字符串字面量的表达式。

### Filtering Logic
严格的多层筛选：SuperGlobal检测（必要条件）→ 主要函数检测（优先级1）→ 备选检测（优先级2）。

## Class Specifications

### ProjectSearcher Class
- **Responsibility**: 协调整个项目筛选流程，实现严格的筛选逻辑
- **Properties**: 
  - `github_client: GitHubAPIClient` - GitHub API客户端
  - `php_analyzer: PHPAnalyzer` - PHP代码分析器
  - `csv_exporter: CSVExporter` - CSV导出器

- **`search_projects() -> List[SearchResult]`**
  - **Behavior**: 执行完整的项目搜索和筛选流程
  - **Input**: None
  - **Output**: 符合条件的搜索结果列表
  - **Raises**: `GitHubAPIError`, `AnalysisError`

- **`apply_filtering_logic(repo_data: Dict[str, Any]) -> Optional[SearchResult]`**
  - **Behavior**: 应用筛选逻辑：SuperGlobal → 主要函数 → 备选检测
  - **Input**: 仓库数据
  - **Output**: 搜索结果或None
  - **Raises**: `AnalysisError`

### PHPAnalyzer Class
- **Responsibility**: 分析PHP代码，检测SuperGlobal、主要函数和动态include使用
- **Properties**: 
  - `semgrep_analyzer: SemgrepAnalyzer` - Semgrep分析器
  - `target_functions: List[str]` - 目标函数列表
  - `superglobals: List[str]` - SuperGlobal参数列表

- **`analyze_file_content(content: str) -> Dict[str, Any]`**
  - **Behavior**: 分析PHP文件内容，检测所有目标特征
  - **Input**: PHP代码内容
  - **Output**: 分析结果字典
  - **Raises**: `AnalysisError`

- **`check_superglobal_requirement(content: str) -> bool`**
  - **Behavior**: 检查SuperGlobal使用（必要条件）
  - **Input**: PHP代码内容
  - **Output**: 是否通过SuperGlobal检测
  - **Raises**: `AnalysisError`

- **`check_primary_functions(content: str) -> Dict[str, Any]`**
  - **Behavior**: 检查主要函数使用情况
  - **Input**: PHP代码内容
  - **Output**: 主要函数检测结果
  - **Raises**: `AnalysisError`

- **`check_fallback_includes(content: str) -> Dict[str, Any]`**
  - **Behavior**: 检查动态include语句（备选检测）
  - **Input**: PHP代码内容
  - **Output**: 动态include检测结果
  - **Raises**: `AnalysisError`

### SemgrepAnalyzer Class
- **Responsibility**: 使用Semgrep进行PHP静态分析，检测动态include/require语句
- **Properties**: 
  - `semgrep_rules_path: str` - Semgrep规则文件路径
  - `semgrep_executable: str` - Semgrep可执行文件路径

- **`detect_dynamic_includes(content: str) -> Dict[str, List[Dict[str, Any]]]`**
  - **Behavior**: 检测动态include/require语句（参数为非字符串字面量）
  - **Input**: PHP代码内容
  - **Output**: 动态include检测结果
  - **Raises**: `SemgrepError`

- **`run_semgrep(file_path: str) -> List[Dict[str, Any]]`**
  - **Behavior**: 运行Semgrep分析指定文件
  - **Input**: 文件路径
  - **Output**: Semgrep结果列表
  - **Raises**: `SemgrepError`

### SearchResult Class
- **Responsibility**: 封装项目分析结果，支持CSV输出
- **Properties**: 
  - `repository_name: str` - 仓库名称
  - `owner: str` - 仓库所有者
  - `url: str` - 仓库URL
  - `current_commit: str` - 当前commit哈希
  - `stars_count: int` - Star数量
  - `detection_type: str` - 检测类型（primary/fallback）
  - `superglobal_usage: List[str]` - SuperGlobal使用列表
  - `function_usage: Dict[str, List[str]]` - 函数使用详情
  - `dynamic_include_usage: Dict[str, List[Dict[str, Any]]]` - 动态include使用详情

- **`to_csv_row() -> Dict[str, Any]`**
  - **Behavior**: 转换为CSV行格式
  - **Input**: None
  - **Output**: CSV行数据字典
  - **Raises**: None

- **`is_qualified() -> bool`**
  - **Behavior**: 检查项目是否符合筛选条件
  - **Input**: None
  - **Output**: 是否符合条件
  - **Raises**: None

### CSVExporter Class
- **Responsibility**: 将搜索结果导出为CSV格式
- **Properties**: 
  - `output_file: str` - 输出文件路径
  - `csv_headers: List[str]` - CSV文件头部字段

- **`export_results(results: List[SearchResult]) -> None`**
  - **Behavior**: 导出搜索结果到CSV文件
  - **Input**: 搜索结果列表
  - **Output**: None
  - **Raises**: `IOError`

### GitHubAPIClient Class
- **Responsibility**: 管理与GitHub API的交互，遵循最佳实践
- **Properties**: 
  - `api_token: str` - GitHub API访问令牌
  - `cache_manager: CacheManager` - 缓存管理器
  - `rate_limit_handler: RateLimitHandler` - 速率限制处理器

- **`search_code_content(query: str, language: str = "PHP") -> List[Dict[str, Any]]`**
  - **Behavior**: 使用GitHub Code Search API搜索包含特定代码的仓库
  - **Input**: 搜索查询和编程语言
  - **Output**: 代码搜索结果列表
  - **Raises**: `GitHubAPIError`

- **`get_file_content(owner: str, repo: str, file_path: str) -> str`**
  - **Behavior**: 获取指定文件的内容，使用缓存
  - **Input**: 仓库所有者、仓库名和文件路径
  - **Output**: 文件内容字符串
  - **Raises**: `GitHubAPIError`

### CacheManager Class
- **Responsibility**: 管理API请求的缓存，避免重复查询
- **Properties**: 
  - `cache_backend: str` - 缓存后端类型
  - `expire_after: int` - 缓存过期时间

- **`get(key: str) -> Optional[Any]`**
  - **Behavior**: 从缓存中获取数据
  - **Input**: 缓存键
  - **Output**: 缓存的数据或None
  - **Raises**: `CacheError`

- **`set(key: str, value: Any, expire_after: Optional[int] = None) -> None`**
  - **Behavior**: 将数据存储到缓存
  - **Input**: 缓存键、数据和过期时间
  - **Output**: None
  - **Raises**: `CacheError`

### RateLimitHandler Class
- **Responsibility**: 处理GitHub API速率限制
- **Properties**: 
  - `rate_limit_remaining: int` - 剩余请求次数
  - `rate_limit_reset: datetime` - 速率限制重置时间
  - `request_delay: float` - 请求间隔时间

- **`check_rate_limit(response: requests.Response) -> None`**
  - **Behavior**: 检查响应中的速率限制信息
  - **Input**: HTTP响应对象
  - **Output**: None
  - **Raises**: `RateLimitError`

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

### Dynamic Include/Require Detection Rules

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

## Processing Flow

```
1. Repository Discovery
   ↓ (GitHub Code Search API)
2. SuperGlobal Validation
   ↓ (必要条件检查)
3. Primary Function Analysis
   ↓ (call_user_func等检测)
4. Fallback Analysis (if needed)
   ↓ (Semgrep动态include检测)
5. Result Qualification
   ↓ (筛选逻辑应用)
6. Data Export
   ↓ (CSV格式输出)
```

## Output Format

CSV文件包含以下字段：
- `project_name`: 项目名称
- `owner`: 项目管理者/组织
- `url`: 项目链接
- `current_commit`: 当前commit哈希
- `stars_count`: Star数量
- `detection_type`: 检测类型（primary/fallback）
- `superglobal_usage`: 使用的SuperGlobal参数
- `function_usage`: 检测到的函数使用情况
- `dynamic_include_usage`: 动态include使用情况（如果适用）

## Target System File Structure

```
PHPIncludes/
├── src/
│   ├── __init__.py
│   ├── github_client.py          # GitHubAPIClient class
│   ├── cache_manager.py          # CacheManager class
│   ├── rate_limit_handler.py     # RateLimitHandler class
│   ├── semgrep_analyzer.py       # SemgrepAnalyzer class
│   ├── php_analyzer.py           # PHPAnalyzer class
│   ├── project_searcher.py       # ProjectSearcher class
│   ├── search_result.py          # SearchResult class
│   ├── csv_exporter.py           # CSVExporter class
│   └── exceptions.py              # All exception classes
├── config/
│   ├── semgrep_rules.yml         # Semgrep rules configuration
│   └── settings.py               # Configuration settings
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
├── scripts/
│   ├── setup.py                  # Project setup script
│   └── run_analysis.py           # Main execution script
├── requirements.txt               # Python dependencies
├── pyproject.toml                # Project configuration
├── .gitignore                    # Git ignore rules
├── README.md                      # Project documentation
└── main.py                       # Entry point

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

**Core Source Files (`src/`)**
- `github_client.py`: GitHub API交互和认证
- `cache_manager.py`: 缓存管理功能
- `rate_limit_handler.py`: API速率限制处理
- `semgrep_analyzer.py`: Semgrep静态分析集成
- `php_analyzer.py`: PHP代码分析协调器
- `project_searcher.py`: 主要协调逻辑
- `search_result.py`: 搜索结果数据模型
- `csv_exporter.py`: CSV导出功能
- `exceptions.py`: 所有异常类定义

**Configuration (`config/`)**
- `semgrep_rules.yml`: Semgrep规则配置文件
- `settings.py`: 项目配置和常量定义

**Testing (`tests/`)**
- 每个核心模块都有对应的测试文件
- `integration/`: 端到端集成测试

**Data Storage (`data/`)**
- `cache/`: 缓存数据存储
- `temp/`: 临时文件存储
- `output/`: CSV结果输出

**Scripts (`scripts/`)**
- `setup.py`: 项目环境设置
- `run_analysis.py`: 主要分析执行脚本

**Project Root**
- `requirements.txt`: Python依赖列表
- `pyproject.toml`: 项目配置和元数据
- `main.py`: 程序入口点