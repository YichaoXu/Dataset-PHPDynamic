# PHP项目筛选系统概念文档

## 1. Context

**Problem Statement**
在GitHub上存在大量PHP项目，其中一些项目可能包含安全风险特征，如使用动态函数调用或动态文件包含语句，同时允许用户通过SuperGlobal参数远程传入数据。当前缺乏系统化的方法来识别和筛选这类具有潜在安全风险的项目，需要构建一个自动化工具来发现这些项目并生成结构化的分析报告。

**System Role**
本系统作为GitHub项目安全分析工具链中的核心筛选模块，负责从海量PHP项目中识别具有特定安全风险特征的项目，为后续的安全研究和分析提供高质量的数据集。

**Data Flow**
- **Inputs:** GitHub API搜索查询、PHP代码内容、Semgrep规则配置
- **Outputs:** 符合条件的项目信息、CSV格式的分析报告、检测结果详情
- **Connections:** GitHub API → 项目筛选系统 → CSV报告生成器

**Scope Boundaries**
- **Owned:** PHP代码静态分析、项目筛选逻辑、结果导出、缓存管理
- **Not Owned:** GitHub API本身、Semgrep工具维护、最终安全评估

## 2. Concepts

**Conceptual Diagram**
```
GitHub API
    ↓ (repository data)
ProjectSearcher
    ↓ (filtered repositories)
PHPAnalyzer ← SemgrepAnalyzer
    ↓ (analysis results)
SearchResult
    ↓ (qualified projects)
CSVExporter
    ↓ (structured report)
CSV Output
```

**Core Concepts**

- **SuperGlobal Requirement**: 项目必须包含SuperGlobal参数使用的必要条件。这个概念定义了筛选的第一道门槛，确保只有允许用户远程传入数据的项目才会被进一步分析。范围包括$_GET、$_POST等所有SuperGlobal变量，排除纯静态或内部使用的项目。

- **Primary Function Detection**: 检测特殊动态函数调用的核心概念。这些函数（call_user_func、call_user_func_array等）代表代码中的动态执行能力，是安全风险的重要指标。概念范围包括函数存在性检测和使用详情分析，与SuperGlobal Requirement形成组合条件。

- **Fallback Include Detection**: 当主要函数不存在时的备选检测策略。这个概念扩展了检测范围，通过Semgrep静态分析识别动态文件包含语句。范围限定为非字符串字面量的表达式，包括变量、字符串拼接、函数调用等动态生成路径的情况。

- **Filtering Logic**: 严格的多层筛选逻辑概念。这个概念定义了从项目发现到最终记录的完整决策流程，确保只有同时满足SuperGlobal条件和函数/包含检测的项目才会被记录。逻辑流程具有明确的优先级和放弃条件。

- **Analysis Result**: 封装项目分析结果的数据概念。这个概念统一了不同类型检测结果的数据结构，支持主要检测和备选检测两种模式，为CSV导出提供标准化的数据格式。

## 3. Contracts & Flow

**Data Contracts**
- **With GitHub API:** 接收仓库元数据、代码内容、commit信息、star数量
- **With Semgrep:** 交换PHP代码内容和静态分析规则，接收检测结果
- **With CSV Output:** 提供标准化的项目信息字段和分析结果

**Internal Processing Flow**
1. **Repository Discovery** - 通过GitHub Code Search API搜索包含SuperGlobal使用的PHP项目
2. **SuperGlobal Validation** - 验证项目是否真正包含SuperGlobal参数使用
3. **Primary Function Analysis** - 检测call_user_func等动态函数的使用情况
4. **Fallback Analysis** - 当主要函数不存在时，使用Semgrep检测动态include语句
5. **Result Qualification** - 应用筛选逻辑，确定项目是否符合记录条件
6. **Data Export** - 将符合条件的项目信息导出为CSV格式

## 4. Scenarios

- **Typical:** 搜索发现一个PHP项目包含$_GET使用，检测到call_user_func函数调用，项目被标记为primary类型并记录到CSV文件中，包含完整的项目信息和函数使用详情。

- **Boundary:** 项目包含SuperGlobal使用但主要函数和动态include都不存在，系统按照筛选逻辑放弃该项目，不进行记录，确保输出质量。

- **Interaction:** 当Semgrep分析器检测到动态include语句时，PHPAnalyzer协调主要函数检测和备选检测的结果，ProjectSearcher应用完整的筛选逻辑决定项目命运，CSVExporter格式化所有相关信息输出到结构化报告中。
