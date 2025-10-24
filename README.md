# PHP Project Filtering System

An automated tool for searching and analyzing PHP projects on GitHub with specific security risk characteristics.

## Features

- **SuperGlobal Detection**: Detects whether projects use SuperGlobal parameters ($_GET, $_POST, etc.)
- **Dynamic Function Detection**: Identifies dynamic function calls like call_user_func, call_user_func_array
- **Dynamic Include Detection**: Uses Semgrep to detect dynamic file inclusion statements
- **Strict Filtering Logic**: Multi-layer filtering ensures result quality
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

1. Set GitHub API token:
```bash
export GITHUB_TOKEN=your_token_here
```

2. Create configuration file (if needed):
```bash
cp config/settings.py.example config/settings.py
```

## Usage

Run the project using uv:
```bash
uv run python main.py --token your_github_token --output results.csv
```

Or activate the virtual environment and run:
```bash
uv shell
python main.py --token your_github_token --output results.csv
```

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
