# PHP Project Dataset Collection Tool

An automated tool for collecting PHP projects from GitHub that meet specific criteria. The goal is to obtain accurate datasets for further analysis.

## Features

- **Dataset Collection**: Collects PHP projects from GitHub that meet specific criteria
- **SuperGlobal Requirement**: Projects must use SuperGlobal parameters ($_GET, $_POST, etc.)
- **Dynamic Function Detection**: Identifies dynamic function calls like call_user_func, call_user_func_array
- **Dynamic Include Detection**: Uses Semgrep to detect dynamic file inclusion statements
- **Strict Filtering Logic**: Multi-layer filtering ensures dataset quality
- **Language Filtering**: Automatically filters by PHP language using GitHub's `language:PHP` qualifier
- **Smart Project Limits**: Configurable project limits (default: 1000) to manage API usage
- **CSV Export**: Generates structured dataset reports

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
cp config.yml.example config.yml
```

2. Edit `config.yml` and set your GitHub API token:
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

Run the project using the defined entry point:
```bash
# Using the entry point defined in pyproject.toml (recommended)
uv run php-includes --token your_github_token --max-projects 1000
```

Or activate the virtual environment and run:
```bash
uv shell
php-includes --token your_github_token --max-projects 1000
```

### Advanced Usage

Search with custom settings:
```bash
uv run php-includes --token YOUR_TOKEN --max-projects 500 --verbose
```

Include unqualified projects in output:
```bash
uv run php-includes --token YOUR_TOKEN --max-projects 2000 --include-unqualified
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

## GitHub API Reference

The project uses the GitHub REST API v3 to search for PHP repositories, analyze code, and retrieve file contents.

**Base URL**: `https://api.github.com`

### Authentication

All API requests use personal access tokens for authentication:
- **Header**: `Authorization: token <GITHUB_TOKEN>`
- **CLI Parameter**: `--token <TOKEN>` (highest priority)
- **Configuration File**: `config.yml` → `github.api_token` (fallback)

### API Endpoints Used

#### 1. Code Search API

**Endpoint**: `GET /search/code`

**Purpose**: Primary method to discover PHP repositories containing specific code patterns.

**Query Format**:
```
{pattern} language:PHP
```

**Example**:
```
call_user_func language:PHP
include $_GET language:PHP
```

**Key Features**:
- Searches across all public repositories (global search)
- Returns file paths and repository information
- Results are deduplicated by repository name
- **Rate Limit**: 30 requests/minute (authenticated)

**Response Fields Used**:
- `items[].repository.full_name`: Repository identifier
- `items[].path`: File path containing the match
- `items[].repository.html_url`: Repository URL

#### 2. File Content API

**Endpoint**: `GET /repos/{owner}/{repo}/contents/{path}`

**Purpose**: Fetch complete PHP file contents for analysis.

**Features**:
- Returns base64-encoded file content (requires decoding)
- **Rate Limit**: 5000 requests/hour (authenticated)
- **Limit**: Maximum 10 files per repository

#### 3. Repository Contents API

**Endpoint**: `GET /repos/{owner}/{repo}/contents`

**Purpose**: Fallback method to list repository files when Code Search API doesn't provide file paths.

**Features**:
- Lists root directory contents
- Filtered to PHP files only
- **Rate Limit**: 5000 requests/hour (authenticated)

#### 4. Repository Info API

**Endpoint**: `GET /repos/{owner}/{repo}`

**Purpose**: Get repository metadata (stars, description, etc.).

**Rate Limit**: 5000 requests/hour (authenticated)

### API Request Flow

1. **Code Search API**: Search for code patterns (`call_user_func language:PHP`)
   - Returns: List of files containing the pattern from various repositories

2. **Extract Repository Information**: 
   - Extract unique repository identifiers from results
   - Collect matched file paths for each repository
   - Deduplicate repositories

3. **File Content API**: 
   - Fetch complete file contents for matched files
   - Uses file paths directly from Code Search results

4. **Analysis**: 
   - Use Semgrep and regex to analyze file contents locally
   - Detect security risk patterns

### Rate Limiting & Caching

**Rate Limits**:
- Code Search API: 30 requests/minute
- Repository APIs: 5000 requests/hour

**Caching**:
All API responses are cached using SQLite database:
- Code Search: 1 hour cache
- File Content: 30 minutes cache
- Repository Info: 1 hour cache

**Automatic Handling**:
- Pre-request rate limit checks
- Automatic wait if approaching limits
- Exponential backoff for errors

### Why Code Search API?

The project uses **Code Search API** (not Repository Search API) because:
- **Code content search**: Finds repositories containing specific code patterns
- **Combined filtering**: `language:PHP` + code pattern in one query
- **Efficiency**: Returns only relevant repositories, avoiding millions of irrelevant ones
- **Repository Search API limitation**: Searches by metadata (name, description), not code content

### Error Handling

Common HTTP status codes:
- `200`: Success
- `401`: Unauthorized (invalid token)
- `403`: Forbidden (rate limit exceeded)
- `404`: Not Found (file/repository doesn't exist)
- `422`: Unprocessable Entity (invalid query format)
- `429`: Too Many Requests (rate limit exceeded)

The system includes automatic error handling with retry logic.

### API Usage

**Estimated usage per 100 projects**:
- Code Search: 4-8 requests
- File Content: 100-1000 requests
- Total: ~104-1018 requests (within 5000/hour limit)

**Reference Links**:
- [GitHub REST API Documentation](https://docs.github.com/en/rest)
- [Code Search API](https://docs.github.com/en/rest/search/search#search-code)
- [Rate Limiting](https://docs.github.com/en/rest/rate-limit)

## Project Structure

```
PHPIncludes/
├── phpincludes/            # Core source code package
├── config.yml              # Configuration file (git-ignored)
├── config.yml.example      # Configuration template
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
uv run black phpincludes/ tests/
uv run ruff check phpincludes/ tests/
```

Type checking:
```bash
uv run mypy phpincludes/
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
