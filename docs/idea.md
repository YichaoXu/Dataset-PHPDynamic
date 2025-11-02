# PHP Project Filtering System Concept Document

## 1. Context

**Problem Statement**
GitHub hosts numerous PHP projects, some of which may contain security risk characteristics such as dynamic function calls or dynamic file inclusion statements while allowing users to remotely input data through SuperGlobal parameters. There is currently a lack of systematic methods to identify and filter such projects with potential security risks from top-ranked repositories, requiring an automated tool to discover these projects by star ranking and generate structured analysis reports.

**System Role**
This system serves as the core filtering module in the GitHub project security analysis toolchain, responsible for identifying projects with specific security risk characteristics from top stars PHP projects, providing high-quality datasets for subsequent security research and analysis.

**Data Flow**
- **Inputs:** Top stars PHP repository list, PHP code content, Semgrep rule configurations
- **Outputs:** Qualified project information, CSV format analysis reports, detection result details
- **Connections:** GitHub Repository Search API → Project Filtering System → CSV Report Generator

**Scope Boundaries**
- **Owned:** PHP code static analysis, project filtering logic, result export, cache management, repository selection by star ranking
- **Not Owned:** GitHub API itself, Semgrep tool maintenance, final security assessment, repository ranking algorithm

## 2. Concepts

**Conceptual Diagram**
```
GitHub Repository Search API
    ↓ (top stars PHP repositories)
ProjectSearcher
    ↓ (selected repositories)
Repository Contents API
    ↓ (PHP file content)
PHPAnalyzer ← SemgrepAnalyzer
    ↓ (analysis results)
SearchResult
    ↓ (qualified projects)
CSVExporter
    ↓ (structured report)
CSV Output
```

**Core Concepts**

- **Top Stars Project Selection**: The initial discovery strategy that retrieves PHP repositories sorted by star count from GitHub. This concept defines the starting point for analysis by focusing on popular and well-maintained projects. Scope includes repository metadata retrieval, star count sorting, and quantity limitation to ensure manageable analysis scope while maintaining quality.

- **SuperGlobal Requirement**: The necessary condition that projects must contain SuperGlobal parameter usage. This concept defines the first screening threshold after repository discovery, ensuring that only projects allowing users to remotely input data will be further analyzed. Scope includes all SuperGlobal variables such as $_GET, $_POST, excluding purely static or internally used projects.

- **Primary Function Detection**: The core concept for detecting special dynamic function calls. These functions ("call_user_func", "call_user_func_array", "forward_static_call", "forward_static_call_array", variable function calls, etc.) represent dynamic execution capabilities in code and are important indicators of security risks. Concept scope includes function existence detection and usage detail analysis, forming combined conditions with SuperGlobal Requirement.

- **Fallback Include Detection**: The alternative detection strategy when primary functions do not exist. This concept extends the detection scope by using Semgrep static analysis to identify dynamic file inclusion statements. Scope is limited to non-string literal expressions, including variables, string concatenation, function calls, and other dynamically generated path situations.

- **Filtering Logic**: The strict multi-layer filtering logic concept. This concept defines the complete decision process from project discovery to final recording, ensuring that only projects meeting both SuperGlobal conditions and function/include detection will be recorded. The logic flow has clear priorities: first validate SuperGlobal usage, then check for primary functions, finally apply fallback include detection.

- **Analysis Result**: The data concept encapsulating project analysis results. This concept unifies the data structure of different types of detection results, supporting both primary detection and alternative detection modes, providing standardized data format for CSV export.

## 3. Contracts & Flow

**Data Contracts**
- **With GitHub Repository Search API:** Receives top stars PHP repository metadata including repository name, owner, URL, star count, default branch, and commit hash
- **With GitHub Repository Contents API:** Receives PHP file listings and contents from repository root directories
- **With Semgrep:** Exchanges PHP code content and static analysis rules, receives detection results for dynamic includes and variable functions
- **With CSV Output:** Provides standardized project information fields including project name, detection type, SuperGlobal usage, function usage, and dynamic include usage

**Internal Processing Flow**
1. **Top Stars Discovery** - Retrieves specified number of top stars PHP repositories from GitHub Repository Search API, sorted by star count in descending order
2. **Repository Selection** - Limits total repositories to maximum project count for analysis efficiency
3. **File Content Retrieval** - Scans repository root directories to fetch PHP file contents for analysis
4. **SuperGlobal Validation** - Validates whether projects truly contain SuperGlobal parameter usage
5. **Primary Function Analysis** - Detects usage of dynamic functions like call_user_func and variable function calls
6. **Fallback Analysis** - When primary functions do not exist, uses Semgrep to detect dynamic include statements
7. **Result Qualification** - Applies filtering logic to determine if projects meet recording conditions
8. **Data Export** - Exports qualified project information to CSV format with complete metadata and analysis results

## 4. Scenarios

- **Typical:** System retrieves top 100 stars PHP repositories from GitHub, discovers a project containing $_GET usage, detects call_user_func function calls through code analysis, the project is marked as primary type and recorded in CSV file with complete project information including commit hash, star count, and function usage details.

- **Boundary:** A top stars PHP project contains SuperGlobal usage but neither primary functions nor dynamic includes exist, the system abandons the project according to filtering logic without recording, ensuring output quality. Another boundary case occurs when repository limit is reached before analyzing all discovered repositories.

- **Interaction:** System retrieves repository list from GitHub Repository Search API, ProjectSearcher coordinates repository selection and file retrieval, PHPAnalyzer uses Semgrep analyzer to detect dynamic include statements when primary functions are absent, SearchResult encapsulates combined analysis results from primary function detection and alternative detection, ProjectSearcher applies complete filtering logic to decide project fate, CSVExporter formats all relevant information including commit hash and star count for output to structured reports.
