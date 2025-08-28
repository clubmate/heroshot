# Heroshot - Python Project

**ALWAYS** follow these instructions first and only fallback to additional search and context gathering if the information here is incomplete or found to be in error.

## Current State
This repository is currently in early development with minimal code. It contains:
- A Python-focused `.gitignore` file 
- Basic README.md
- No source code or project configuration files yet

## Working Effectively

### Initial Setup & Environment
Run these commands to set up your development environment:

```bash
# Set up Python virtual environment (takes ~3 seconds)
python3 -m venv .venv

# Activate virtual environment (always do this before any Python work)
source .venv/bin/activate

# Upgrade pip (takes ~2 seconds)
pip install --upgrade pip

# Install common development tools (takes 10-60+ seconds, NEVER CANCEL)
# NOTE: May fail due to network connectivity issues in sandboxed environments
pip install pytest black flake8
```

**CRITICAL TIMING NOTE**: Package installation takes 10-60+ seconds depending on network. Set timeout to 300+ seconds for pip install commands. **NEVER CANCEL** pip operations - they may appear to hang but are often still downloading.

**KNOWN ISSUE**: `pip install` commands may fail with `ReadTimeoutError` due to network connectivity limitations in sandboxed environments. This is a known infrastructure limitation, not a code issue.

### Available Development Tools
- **Python**: 3.12.3 (system installation at `/usr/bin/python3`)
- **pip**: Available for package management
- **git**: Available for version control
- **make**: Available for build scripts (when added)
- **node/npm**: Available if JavaScript components are added

### Development Workflow

#### Testing
```bash
# Always activate virtual environment first
source .venv/bin/activate

# Run tests (typically takes <1 second for small test suites)
pytest -v

# Run tests with coverage (when coverage is installed)
pytest --cov=src tests/
```

#### Code Quality & Linting
```bash
# Always activate virtual environment first
source .venv/bin/activate

# Format code with black (takes ~0.1 seconds per file)
black .

# Check formatting without applying changes
black --check .

# Lint code with flake8 (takes ~0.1 seconds per file)
flake8 .

# Run all quality checks together
black --check . && flake8 .
```

**ALWAYS** run `black .` and `flake8 .` before committing changes to ensure code quality.

### Validation Scenarios

When making changes to the codebase, **ALWAYS** validate using these scenarios:

1. **Basic Python Execution**: 
   ```bash
   source .venv/bin/activate
   python3 -c "print('Heroshot is working')"
   ```

2. **Test Suite Execution**:
   ```bash
   source .venv/bin/activate
   pytest -v
   ```

3. **Code Quality Validation**:
   ```bash
   source .venv/bin/activate
   black --check .
   flake8 .
   ```

4. **Full Development Cycle** (run this sequence after any changes):
   ```bash
   source .venv/bin/activate
   black .
   flake8 .
   pytest -v
   ```

### Timeout Guidelines

**NEVER CANCEL** these operations - wait for completion:
- Virtual environment creation: 5+ seconds (use 30+ second timeout)
- Pip package installation: 10-60+ seconds (use 300+ second timeout for safety)
- Black formatting: <1 second per file (use 10+ second timeout)
- Flake8 linting: <1 second per file (use 10+ second timeout)
- Pytest execution: <1 second for small test suites (use 30+ second timeout)

**IMPORTANT**: Network operations (pip install) may fail with timeout errors in sandboxed environments due to connectivity restrictions.

### Common Workflows

#### Adding New Dependencies
```bash
source .venv/bin/activate
pip install <package-name>
# NOTE: May fail due to network timeouts in sandboxed environments
# Always test after installing new packages
pytest -v
```

#### Creating New Python Modules
1. Create the `.py` file in appropriate directory
2. Add corresponding test file with `test_` prefix
3. Run the full validation cycle:
   ```bash
   source .venv/bin/activate
   black .
   flake8 .
   pytest -v
   ```

## Repository Structure

```
/home/runner/work/heroshot/heroshot/
├── .git/                    # Git repository data
├── .github/                 # GitHub configuration (workflows, etc.)
│   └── copilot-instructions.md
├── .gitignore               # Python-focused ignore patterns
├── README.md                # Project documentation
├── .venv/                   # Python virtual environment (created by setup)
└── *.py                     # Python source files (to be added)
```

## Validation Requirements

Before completing any task:

1. **Environment Check**: Ensure virtual environment is activated
2. **Code Quality**: Run `black .` and `flake8 .`
3. **Testing**: Run `pytest -v` 
4. **Manual Verification**: Test any new functionality manually

## Known Working Commands

These commands have been validated and work correctly:

```bash
# Environment setup (tested: works in ~3 seconds)
python3 -m venv .venv

# Package installation (tested: may timeout due to network issues)
source .venv/bin/activate && pip install pytest black flake8

# Basic Python execution (tested: works instantly)
source .venv/bin/activate && python3 -c "print('Heroshot is working')"

# Testing (when pytest is available: works in ~0.2 seconds)
source .venv/bin/activate && pytest -v

# Formatting (when black is available: works in ~0.1 seconds)
source .venv/bin/activate && black .

# Linting (when flake8 is available: works in ~0.1 seconds)
source .venv/bin/activate && flake8 .
```

## Future Development Notes

When code is added to this repository:
- Follow Python best practices for project structure
- Add `requirements.txt` or `pyproject.toml` for dependency management
- Consider adding CI/CD workflows in `.github/workflows/`
- Add comprehensive test coverage
- Update this documentation as the project evolves

## Emergency Troubleshooting

If virtual environment becomes corrupted:
```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install pytest black flake8
```

**Remember**: Always activate the virtual environment with `source .venv/bin/activate` before any Python-related commands.