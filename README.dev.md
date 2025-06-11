# Developer Environment Setup

## Package Management

**This project uses `uv`, NOT `pip`.**

### Essential Commands
```bash
# Install dependencies
uv add <package>              # Runtime dependency
uv add --dev <package>        # Development dependency

# Run tools
uv run pytest                 # Run tests
uv run mypy src/              # Type checking
uv run ruff check             # Linting
uv run ruff check --fix       # Auto-fix linting issues

# Install project
uv pip install -e .           # Development install
```

### Project Structure
- Uses `pyproject.toml` for configuration
- Uses `uv.lock` for dependency locking
- Source code in `src/paise2/`
- Tests in `tests/`

### Never Use These Commands
- ❌ `pip install <package>`
- ❌ `python -m pytest`
- ❌ `mypy src/`
- ❌ `ruff check`

Always prefix with `uv run` or use `uv add` for dependencies.
