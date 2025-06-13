# Developer Environment Setup

## Package Management

**This project uses `uv`, NOT `pip`.**

### Essential Commands
```bash
# Install dependencies
uv add <package>              # Runtime dependency
uv add --dev <package>        # Development dependency
```

When needed, the following MUST be run through vscode tasks, without waiting for confirmation:

- `Run Tests`
- `Run MyPy`, for type checking
- `Run Ruff Check`, for linting
- `Run Ruff Format`, for formatting

The output for each of these is available after the tool has run, in the file called `output.log.txt`.

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
