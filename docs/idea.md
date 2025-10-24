# PHP Project Filtering System Concept Document

## 1. Context

**Problem Statement**
GitHub hosts numerous PHP projects, some of which may contain security risk characteristics such as dynamic function calls or dynamic file inclusion statements while allowing users to remotely input data through SuperGlobal parameters. There is currently a lack of systematic methods to identify and filter such projects with potential security risks, requiring an automated tool to discover these projects and generate structured analysis reports.

**System Role**
This system serves as the core filtering module in the GitHub project security analysis toolchain, responsible for identifying projects with specific security risk characteristics from massive PHP projects, providing high-quality datasets for subsequent security research and analysis.

**Data Flow**
- **Inputs:** GitHub API search queries, PHP code content, Semgrep rule configurations
- **Outputs:** Qualified project information, CSV format analysis reports, detection result details
- **Connections:** GitHub API → Project Filtering System → CSV Report Generator

**Scope Boundaries**
- **Owned:** PHP code static analysis, project filtering logic, result export, cache management
- **Not Owned:** GitHub API itself, Semgrep tool maintenance, final security assessment

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

- **SuperGlobal Requirement**: The necessary condition that projects must contain SuperGlobal parameter usage. This concept defines the first screening threshold, ensuring that only projects allowing users to remotely input data will be further analyzed. Scope includes all SuperGlobal variables such as $_GET, $_POST, excluding purely static or internally used projects.

- **Primary Function Detection**: The core concept for detecting special dynamic function calls. These functions ("call_user_func", "call_user_func_array", "forward_static_call", "forward_static_call_array", etc.) represent dynamic execution capabilities in code and are important indicators of security risks. Concept scope includes function existence detection and usage detail analysis, forming combined conditions with SuperGlobal Requirement.

- **Fallback Include Detection**: The alternative detection strategy when primary functions do not exist. This concept extends the detection scope by using Semgrep static analysis to identify dynamic file inclusion statements. Scope is limited to non-string literal expressions, including variables, string concatenation, function calls, and other dynamically generated path situations.

- **Filtering Logic**: The strict multi-layer filtering logic concept. This concept defines the complete decision process from project discovery to final recording, ensuring that only projects meeting both SuperGlobal conditions and function/include detection will be recorded. The logic flow has clear priorities and abandonment conditions.

- **Analysis Result**: The data concept encapsulating project analysis results. This concept unifies the data structure of different types of detection results, supporting both primary detection and alternative detection modes, providing standardized data format for CSV export.

## 3. Contracts & Flow

**Data Contracts**
- **With GitHub API:** Receives repository metadata, code content, commit information, star counts
- **With Semgrep:** Exchanges PHP code content and static analysis rules, receives detection results
- **With CSV Output:** Provides standardized project information fields and analysis results

**Internal Processing Flow**
1. **Repository Discovery** - Searches for PHP projects containing SuperGlobal usage through GitHub Code Search API
2. **SuperGlobal Validation** - Validates whether projects truly contain SuperGlobal parameter usage
3. **Primary Function Analysis** - Detects usage of dynamic functions like call_user_func
4. **Fallback Analysis** - When primary functions do not exist, uses Semgrep to detect dynamic include statements
5. **Result Qualification** - Applies filtering logic to determine if projects meet recording conditions
6. **Data Export** - Exports qualified project information to CSV format

## 4. Scenarios

- **Typical:** A search discovers a PHP project containing $_GET usage, detects call_user_func function calls, the project is marked as primary type and recorded in CSV file with complete project information and function usage details.

- **Boundary:** A project contains SuperGlobal usage but neither primary functions nor dynamic includes exist, the system abandons the project according to filtering logic without recording, ensuring output quality.

- **Interaction:** When Semgrep analyzer detects dynamic include statements, PHPAnalyzer coordinates results from primary function detection and alternative detection, ProjectSearcher applies complete filtering logic to decide project fate, CSVExporter formats all relevant information for output to structured reports.
