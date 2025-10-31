# PHP Project Filtering System

An automated tool for searching and analyzing PHP projects on GitHub with specific security risk characteristics.

## Features

- **SuperGlobal Detection**: Detects whether projects use SuperGlobal parameters ($_GET, $_POST, etc.)
- **Dynamic Function Detection**: Identifies dynamic function calls like call_user_func, call_user_func_array
- **Dynamic Include Detection**: Uses Semgrep to detect dynamic file inclusion statements
- **Strict Filtering Logic**: Multi-layer filtering ensures result quality
- **Language Filtering**: Automatically filters by PHP language using GitHub's `language:PHP` qualifier
- **Smart Project Limits**: Configurable project limits (default: 1000) to manage API usage
- **CSV Export**: Generates structured analysis reports

## System Requirements

- Python 3.9+
- uv (modern Python package manager)
- Semgrep
- GitHub API access token

## Installation

1. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone the repository:
```bash
git clone <repository-url>
cd PHPIncludes
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

### Method 1: Configuration File (Recommended)

1. Create configuration file from example:
```bash
cp config/config.yml.example config/config.yml
```

2. Edit `config/config.yml` and set your GitHub API token:
```yaml
github:
  api_token: "your_github_token_here"
  
search:
  max_projects: 1000
  max_files_per_project: 10
  search_delay: 0.5
  default_language: "PHP"
  
  # Custom search queries (optional)
  custom_queries:
    - "call_user_func language:PHP"
    - "include $_GET language:PHP"

cache:
  db_path: "data/cache/github_cache.db"
  default_expire: 3600

rate_limit:
  request_delay: 1.0

output:
  output_dir: "data/output"
```

**Priority**: Configuration file > Environment variable > Default value

### Method 2: Environment Variable

Alternatively, you can set the GitHub API token via environment variable:
```bash
export GITHUB_TOKEN=your_token_here
```

**Note**: Configuration file settings take precedence over environment variables.

## Usage

Run the project using uv:
```bash
uv run python main.py --token your_github_token --max-projects 1000 --language PHP
```

Or activate the virtual environment and run:
```bash
uv shell
python main.py --token your_github_token --max-projects 1000 --language PHP
```

### Advanced Usage

Search with custom queries and language filtering:
```bash
python main.py --token YOUR_TOKEN --queries "call_user_func" "include $_GET" --language PHP --max-projects 500
```

Search with different language variants:
```bash
python main.py --token YOUR_TOKEN --language php --max-projects 2000
```

## Project Limits and Filtering Strategy

### Why We Need Limits

GitHub hosts millions of repositories, making it impossible to analyze all projects. Our system implements smart filtering to focus on relevant PHP projects:

1. **Language Filtering**: Uses GitHub's `language:PHP` qualifier to only search PHP repositories
2. **Project Limits**: Default limit of 1000 projects to manage API usage and processing time
3. **Smart Queries**: Pre-defined queries target specific security patterns

### Recommended Limits

- **Small-scale testing**: 100-500 projects
- **Production analysis**: 1000-2000 projects  
- **Large-scale research**: 5000+ projects (with caution)

### API Rate Limiting

GitHub API has rate limits:
- **Authenticated requests**: 5000 requests/hour
- **Search API**: 30 requests/minute
- **Repository API**: 5000 requests/hour

Our system includes automatic rate limiting and caching to respect these limits.

## Project Structure

```
PHPIncludes/
├── src/                    # Core source code
├── config/                 # Configuration files
├── tests/                  # Test cases
├── scripts/                # Script files
├── docs/                   # Documentation
├── pyproject.toml          # Project configuration and dependencies
├── uv.lock                 # Locked dependency versions
└── .venv/                  # Virtual environment (managed by uv)

# Runtime-generated directories (not in version control)
├── data/                   # Runtime data (cache, temp files, output)
├── .mypy_cache/           # MyPy type checking cache
├── .ruff_cache/           # Ruff code checking cache
└── .semgrep/              # Semgrep cache
```

## Development

Run tests:
```bash
uv run pytest
```

Code formatting:
```bash
uv run black src/ tests/
uv run ruff check src/ tests/
```

Type checking:
```bash
uv run mypy src/
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
