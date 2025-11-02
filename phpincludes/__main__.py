"""
PHPIncludes Package Entry Point

This module allows the package to be run as a module using:
    uv run python -m phpincludes
    or
    python -m phpincludes

When Python runs a package with `-m`, it looks for `__main__.py` and executes it.
This is the standard way to support `python -m package_name` execution.
"""

from .cli import main

if __name__ == "__main__":
    import sys
    sys.exit(main())

