# Dataset-PHPDynCtrlflow

An automated dataset generation tool that collects PHP projects from GitHub and generates downloadable datasets in CSV format. This tool identifies PHP projects with specific security risk characteristics (dynamic control flow patterns) and exports them as structured datasets for research and analysis purposes.

## What It Does

This tool:
1. Searches GitHub for top-starred PHP repositories
2. Analyzes code to find projects with:
   - SuperGlobal parameter usage ($_GET, $_POST, etc.)
   - Dynamic function calls (`call_user_func`, variable functions, etc.)
   - Dynamic file inclusion statements
3. Exports qualified projects to CSV datasets with metadata (project name, owner, URL, commit hash, star count, detection type)

## Installation

1. **Install uv** (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Clone the repository**:
```bash
git clone <repository-url>
cd php-dynctrlflow
```

3. **Install dependencies**:
```bash
uv sync
```

## Configuration

1. **Create configuration file**:
```bash
cp config.yml.example config.yml
```

2. **Edit `config.yml`** and set your GitHub API token:
```yaml
github:
  api_token: "your_github_token_here"
  
search:
  max_projects: 1000
  max_files_per_project: 10
```

**Get GitHub Token**: Generate one at [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)

## Usage

**Basic usage**:
```bash
uv run php-dynctrlflow
```

**Advanced usage**:
```bash
# Custom settings
uv run php-dynctrlflow --token YOUR_TOKEN --max-projects 500 --verbose

# Include unqualified projects
uv run php-dynctrlflow --token YOUR_TOKEN --max-projects 2000 --include-unqualified
```

**Output**: CSV datasets are saved in `data/output/` directory:
- `php_projects_YYYYMMDD_HHMMSS.csv`: Basic dataset with qualified projects
- `php_projects_summary_YYYYMMDD_HHMMSS.csv`: Summary statistics
- `php_projects_detailed_YYYYMMDD_HHMMSS.csv`: Detailed analysis results

## Dataset Output

The CSV datasets contain:
- `project_name`: Repository name (owner/repo)
- `owner`, `repo_name`: For Git clone
- `url`: GitHub repository URL
- `commit_hash`: Commit SHA for specific version checkout
- `star_count`: Project popularity
- `detection_type`: `primary_functions` or `fallback_includes`

## Requirements

- Python 3.9+
- uv package manager
- GitHub API access token
- Semgrep (for static analysis)

## Documentation

For detailed information:
- **[Concept & Ideas](docs/idea.md)**: Project context, concepts, and design goals
- **[Technical Design](docs/design.md)**: Complete technical specification and architecture

## Development

```bash
# Run tests
uv run pytest

# Format code
uv run black php_dynctrlflow/ tests/
uv run ruff check php_dynctrlflow/ tests/

# Type checking
uv run mypy php_dynctrlflow/
```

## License

MIT License
