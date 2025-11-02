# Dataset-PHPDynCtrlflow

An automated dataset generation tool that collects PHP projects from GitHub and generates downloadable datasets in CSV format. This tool identifies PHP projects with specific security risk characteristics and exports them as structured datasets for research and analysis purposes.

## Features

- **Top Stars Project Selection**: Discovers PHP repositories sorted by star count from GitHub Repository Search API, focusing on popular and well-maintained projects
- **SuperGlobal Requirement**: Filters projects that must use SuperGlobal parameters ($_GET, $_POST, $_REQUEST, $_COOKIE, $_SESSION, $_SERVER, $_FILES, $_ENV) as a necessary condition
- **Primary Function Detection**: Detects dynamic function calls like `call_user_func`, `call_user_func_array`, `forward_static_call`, `forward_static_call_array`, and variable function calls (`$var()` and `$$var()`)
- **Fallback Include Detection**: Uses Semgrep static analysis to detect dynamic file inclusion statements (non-string literal expressions) when primary functions are absent
- **Strict Multi-Layer Filtering**: Ensures dataset quality through systematic filtering: SuperGlobal validation → Primary function detection → Fallback include detection
- **CSV Dataset Export**: Generates downloadable CSV datasets containing qualified project information with metadata (project name, owner, URL, commit hash, star count, detection type)

## System Requirements

- Python 3.9+
- uv (modern Python package manager)
- GitHub API access token

## Installation

1. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone the repository:
```bash
git clone <repository-url>
cd php-dynctrlflow
```

3. Install dependencies:
```bash
uv sync
```

4. Install development dependencies (optional):
```bash
uv sync --extra dev
```

## Configuration

### Configuration File (Required)

1. Create configuration file from example:
```bash
cp config.yml.example config.yml
```

2. Edit `config.yml` and set your GitHub API token and dataset generation settings:
```yaml
github:
  api_token: "your_github_token_here"
  
search:
  max_projects: 1000          # Maximum number of repositories to analyze
  max_files_per_project: 10   # Maximum PHP files to analyze per repository

cache:
  db_path: "data/cache/github_cache.db"
  default_expire: 3600        # Cache expiration time in seconds (1 hour)

rate_limit:
  request_delay: 1.0          # Delay between API requests (seconds)

output:
  output_dir: "data/output"   # Directory where CSV datasets are saved
```

**Priority**: CLI parameter `--token` (highest) > Configuration file `config.yml` > Environment variable `GITHUB_TOKEN`

**Note**: GitHub API token is required. Generate one at [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens).

## Usage

### Basic Usage

Run the tool to generate a dataset:
```bash
# Using the entry point defined in pyproject.toml (recommended)
uv run php-dynctrlflow --token your_github_token --max-projects 1000
```

This will generate CSV dataset files in `data/output/` directory with timestamps:
- `php_projects_YYYYMMDD_HHMMSS.csv`: Basic dataset with qualified projects
- `php_projects_summary_YYYYMMDD_HHMMSS.csv`: Summary statistics
- `php_projects_detailed_YYYYMMDD_HHMMSS.csv`: Detailed analysis results

### Advanced Usage

Generate dataset with custom settings:
```bash
uv run php-dynctrlflow --token YOUR_TOKEN --max-projects 500 --verbose
```

Include unqualified projects in dataset:
```bash
uv run php-dynctrlflow --token YOUR_TOKEN --max-projects 2000 --include-unqualified
```

### Output Location

Generated datasets are saved in the `data/output/` directory (configured in `config.yml`). The CSV files contain all necessary information to download and analyze the identified PHP projects.

## How It Works

### Dataset Generation Workflow

The tool follows a structured workflow to discover, analyze, and export qualified PHP projects as downloadable datasets:

1. **Top Stars Discovery**: Retrieves specified number of top stars PHP repositories from GitHub Repository Search API, sorted by star count in descending order

2. **Repository Selection**: Limits total repositories to maximum project count (default: 1000) for analysis efficiency

3. **SearchResult Creation**: Converts repository items to SearchResult objects, automatically fetching commit SHA for each repository's default branch

4. **File Content Retrieval**: Scans repository root directories to fetch PHP file contents for analysis (limited to configurable max files per project, default: 10)

5. **SuperGlobal Validation**: Validates whether projects truly contain SuperGlobal parameter usage ($_GET, $_POST, $_REQUEST, $_COOKIE, $_SESSION, $_SERVER, $_FILES, $_ENV) as a necessary condition. Projects without SuperGlobal usage are abandoned.

6. **Primary Function Analysis**: Detects usage of dynamic functions like `call_user_func`, `call_user_func_array`, `forward_static_call`, `forward_static_call_array`, and variable function calls (`$var()` and `$$var()`). Projects with these functions are marked as qualified.

7. **Fallback Analysis**: When primary functions do not exist, uses Semgrep static analysis to detect dynamic include/require statements with non-string literal expressions (variables, string concatenation, function calls). Projects with dynamic includes are marked as qualified.

8. **Result Qualification**: Applies strict multi-layer filtering logic to determine if projects meet recording conditions

9. **Dataset Export**: Exports qualified project information to CSV format datasets with complete metadata (project name, owner, repo name, URL, commit hash, star count, detection type)

### Filtering Logic

The system applies strict multi-layer filtering:

1. **SuperGlobal Requirement** (Necessary Condition): Projects must contain SuperGlobal parameter usage. If not, the project is abandoned.

2. **Primary Function Detection** (Priority 1): If SuperGlobal is present, check for special dynamic function calls (`call_user_func`, `call_user_func_array`, `forward_static_call`, `forward_static_call_array`, variable function calls). If found, record the project.

3. **Fallback Include Detection** (Priority 2): If dynamic functions are not found, check for dynamic `include`/`require` statements with non-string literal expressions (variables, string concatenation, function calls). If found, record the project.

4. **Abandonment**: If neither primary functions nor dynamic includes are found, abandon the project.

### Dataset Size Configuration

Configure the number of projects to analyze and include in the generated dataset:

- **Default**: 1000 projects
- **Small-scale testing**: 100-500 projects (quick validation)
- **Production analysis**: 1000-2000 projects (balanced quality and quantity)
- **Large-scale research**: 5000+ projects (requires significant API usage and processing time)

**Note**: The `max_projects` parameter determines how many repositories are analyzed. Only qualified projects (passing all filtering criteria) are included in the final CSV dataset output.

## GitHub API Authentication

The tool requires a GitHub personal access token to access the GitHub API.

**Token Configuration**:
- **CLI Parameter**: `--token <TOKEN>` (highest priority)
- **Configuration File**: `config.yml` → `github.api_token` (fallback)

**Note**: Generate a GitHub personal access token at [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens).

## Project Structure

```
php-dynctrlflow/
├── php_dynctrlflow/        # Core source code package (dataset generator)
│   ├── cli.py              # CLI interface
│   ├── project_searcher.py # Project discovery and filtering orchestration
│   ├── php_analyzer.py     # PHP code analysis (SuperGlobal, dynamic functions)
│   ├── semgrep_analyzer.py # Semgrep static analysis integration
│   ├── github_client.py    # GitHub API client (Repository Search, Contents, File Content)
│   ├── cache_manager.py    # SQLite cache management
│   ├── rate_limit_handler.py # GitHub API rate limit handling
│   ├── search_result.py    # Search result data model
│   ├── csv_exporter.py     # CSV dataset export functionality
│   ├── settings.py         # Configuration loader
│   └── semgrep/
│       └── rules.yml       # Semgrep rules for dynamic include detection (internal)
├── config.yml              # User configuration file (git-ignored)
├── config.yml.example      # Configuration template
├── tests/                  # Test cases
├── docs/                   # Documentation
│   ├── idea.md             # Concept document
│   ├── design.md           # Technical design specification
│   └── todo.md             # Development task list
├── pyproject.toml          # Project configuration and dependencies
├── uv.lock                 # Locked dependency versions
└── .venv/                  # Virtual environment (managed by uv)

# Runtime-generated directories (not in version control)
├── data/                   # Runtime data
│   ├── cache/              # SQLite cache database (API responses)
│   ├── temp/               # Temporary files
│   └── output/             # Generated CSV datasets (downloadable datasets)
│       ├── php_projects_YYYYMMDD_HHMMSS.csv
│       ├── php_projects_summary_YYYYMMDD_HHMMSS.csv
│       └── php_projects_detailed_YYYYMMDD_HHMMSS.csv
├── .mypy_cache/           # MyPy type checking cache
├── .ruff_cache/           # Ruff code checking cache
└── .semgrep/              # Semgrep analysis cache
```

**Note**: The `data/output/` directory contains the generated CSV datasets. These CSV files are the downloadable datasets produced by this tool.

## Dataset Output Format

The generated CSV datasets contain the following fields for qualified projects:

### Basic Dataset (`php_projects_YYYYMMDD_HHMMSS.csv`)

Contains essential information needed to download and identify projects:

- `project_name`: Full repository name (owner/repo format)
- `owner`: Repository owner (used for Git clone: `git clone https://github.com/{owner}/{repo_name}.git`)
- `repo_name`: Repository name (used for Git clone)
- `url`: Repository GitHub URL (direct link to project)
- `commit_hash`: Latest commit SHA for the default branch (used to checkout specific version: `git checkout {commit_hash}`)
- `star_count`: Number of stars (project popularity indicator)
- `detection_type`: Detection type (`primary_functions` or `fallback_includes`)

### Additional Dataset Files

- `php_projects_summary_YYYYMMDD_HHMMSS.csv`: Summary statistics and aggregated data
- `php_projects_detailed_YYYYMMDD_HHMMSS.csv`: Detailed analysis results with full detection information

**Note**: Only qualified projects (meeting all filtering criteria: SuperGlobal usage + primary functions OR fallback includes) are included in the basic CSV dataset. Unqualified projects are filtered out unless `--include-unqualified` flag is used.

## Development

Run tests:
```bash
uv run pytest
```

Code formatting:
```bash
uv run black php_dynctrlflow/ tests/
uv run ruff check php_dynctrlflow/ tests/
```

Type checking:
```bash
uv run mypy php_dynctrlflow/
```

Install new dependencies:
```bash
uv add package-name
uv add --dev package-name  # Development dependencies
```

## uv Advantages

- **Fast**: 10-100x faster than pip
- **Reliable**: Automatically locks dependency versions
- **Modern**: Supports latest Python package management standards
- **Simple**: Unified command interface

## License

MIT License
