# Development Guide

This guide helps you set up your development environment and start contributing to the JMeter Test Generator.

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git
- VS Code (recommended) or any text editor
- JMeter 5.6+ (for testing generated files)

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/jmeter-test-generator.git
cd jmeter-test-generator/app
```

### 2. Create Virtual Environment

```bash
# Create venv
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

This installs:
- Core dependencies (PyYAML, Click, Rich, MCP SDK)
- Development tools (pytest, ruff, mypy)
- The package in editable mode

### 4. Verify Installation

```bash
# Check CLI works
jmeter-gen --version

# Run tests
pytest

# Check linting
ruff check .
```

## Global Installation (User-wide)

If you want to use `jmeter-gen` from any directory without activating a virtual environment:

### Option 1: User Installation (Recommended)

```bash
cd /path/to/jmeter-test-generator/app
pip install --user -e ".[dev]"
```

This installs the package for your user only, without requiring admin privileges.

### Windows PATH Configuration

1. Find your Python Scripts directory:
   ```cmd
   python -c "import site; print(site.getusersitepackages().replace('site-packages', 'Scripts'))"
   ```

2. Add to PATH:
   - Press `Win + R`, type `sysdm.cpl`, press Enter
   - Go to "Advanced" tab -> "Environment Variables"
   - Under "User variables", find `Path` and click "Edit"
   - Add the Scripts directory path
   - Click OK -> OK -> OK

3. Restart terminal and verify:
   ```cmd
   jmeter-gen --version
   ```

### Linux/Mac PATH Configuration

The user bin directory (`~/.local/bin`) is typically already in PATH. If not, add to `~/.bashrc` or `~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then reload: `source ~/.bashrc`

### Option 2: System-wide Installation (requires admin)

```bash
cd /path/to/jmeter-test-generator/app
sudo pip install -e ".[dev]"  # Linux/Mac
pip install -e ".[dev]"       # Windows (run as Administrator)
```

### Usage from Any Directory

After global installation, you can run from any project:

```bash
cd /path/to/your/api/project
jmeter-gen analyze
jmeter-gen generate
```

## Project Structure

```
app/
├── jmeter_gen/              # Main package
│   ├── __init__.py
│   ├── cli.py               # CLI interface
│   ├── mcp_server.py        # MCP Server
│   └── core/                # Core logic
│       ├── __init__.py
│       ├── project_analyzer.py
│       ├── openapi_parser.py
│       ├── jmx_generator.py
│       └── jmx_validator.py
├── templates/               # JMX XML templates
├── tests/                   # Test suite
│   ├── core/
│   ├── integration/
│   └── fixtures/
├── examples/                # Example projects
├── docs/                    # Documentation
└── pyproject.toml           # Project config
```

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow the implementation plan in `docs/IMPLEMENTATION_PLAN.md`.

### 3. Write Tests

Every new feature must have tests:

```python
# tests/core/test_project_analyzer.py
import pytest
from jmeter_gen.core.project_analyzer import ProjectAnalyzer

def test_find_openapi_spec():
    analyzer = ProjectAnalyzer()
    result = analyzer.find_openapi_spec("tests/fixtures/sample-project")

    assert result["found"] is True
    assert result["spec_path"].endswith("openapi.yaml")
```

### 4. Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/core/test_project_analyzer.py

# Run with coverage
pytest --cov=jmeter_gen --cov-report=html

# View coverage report
open htmlcov/index.html
```

### 5. Lint and Format

```bash
# Check linting
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Type checking
mypy jmeter_gen/
```

### 6. Manual Testing

```bash
# Test with real project
cd /path/to/your/api/project

# Analyze project
jmeter-gen analyze

# Generate JMX
jmeter-gen generate --threads 50

# Validate generated JMX
jmeter-gen validate performance-test.jmx

# Test in JMeter
jmeter -n -t performance-test.jmx -l results.jtl
```

### 7. Commit Changes

```bash
git add .
git commit -m "feat: add feature description"
git push origin feature/your-feature-name
```

Follow conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `test:` - Adding tests
- `refactor:` - Code refactoring

## Testing Guide

### Unit Tests

Test individual functions in isolation:

```python
# tests/core/test_openapi_parser.py
def test_parse_endpoints():
    parser = OpenAPIParser()
    paths = {
        "/users": {
            "get": {"operationId": "listUsers"},
            "post": {"operationId": "createUser"}
        }
    }

    endpoints = parser._parse_endpoints(paths)

    assert len(endpoints) == 2
    assert endpoints[0]["method"] == "GET"
    assert endpoints[1]["method"] == "POST"
```

### Integration Tests

Test multiple components together:

```python
# tests/integration/test_end_to_end.py
def test_full_generation_flow():
    # Analyze project
    analyzer = ProjectAnalyzer()
    analysis = analyzer.analyze_project("tests/fixtures/sample-api")

    # Parse spec
    parser = OpenAPIParser()
    spec_data = parser.parse(analysis["spec_path"])

    # Generate JMX
    generator = JMXGenerator()
    result = generator.generate(
        spec_data=spec_data,
        output_path="/tmp/test.jmx",
        threads=10
    )

    assert result["success"] is True
    assert Path("/tmp/test.jmx").exists()
```

### Test Fixtures

Use fixtures for test data:

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def sample_openapi_spec():
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "servers": [{"url": "http://localhost:8080"}],
        "paths": {
            "/users": {
                "get": {"operationId": "listUsers"}
            }
        }
    }

# Usage in tests
def test_parser(sample_openapi_spec):
    parser = OpenAPIParser()
    # Use sample_openapi_spec
```

## Debugging

### VS Code Debug Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: CLI Generate",
      "type": "debugpy",
      "request": "launch",
      "module": "jmeter_gen.cli",
      "args": ["generate", "--spec", "/path/to/openapi.yaml"],
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Current Test",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

### Print Debugging

Use Rich for formatted debug output:

```python
from rich import print as rprint
from rich.pretty import pprint

# Print formatted data
rprint("[blue]Debug:[/blue] Processing endpoint", endpoint)

# Pretty-print complex objects
pprint(spec_data)
```

### Logging

Use logging module:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Parsing spec: %s", spec_path)
logger.info("Generated JMX with %d samplers", count)
logger.warning("No base URL found, using default")
logger.error("Failed to parse spec: %s", error)
```

## Code Style Guidelines

### Type Hints

Always use type hints:

```python
from typing import Dict, List, Optional

def parse_endpoints(paths: Dict) -> List[Dict]:
    """Parse endpoints from OpenAPI paths"""
    endpoints: List[Dict] = []
    # ...
    return endpoints

def find_spec(path: str) -> Optional[Dict]:
    """Find OpenAPI spec, returns None if not found"""
    # ...
```

### Docstrings

Use Google-style docstrings:

```python
def generate(self, spec_data: Dict, output_path: str) -> Dict:
    """Generate JMeter JMX file from OpenAPI spec.

    Args:
        spec_data: Parsed OpenAPI specification
        output_path: Path where to save JMX file

    Returns:
        Generation result with success status and metadata

    Raises:
        JMXGenerationException: If generation fails
    """
```

### Error Handling

Raise specific exceptions:

```python
class JMeterGenException(Exception):
    """Base exception for JMeter Generator"""

class SpecNotFoundException(JMeterGenException):
    """OpenAPI spec not found in project"""

# Usage
if not spec_path.exists():
    raise SpecNotFoundException(f"No spec found in {project_path}")
```

### Constants

Use UPPERCASE for constants:

```python
class ProjectAnalyzer:
    COMMON_SPEC_NAMES = [
        "openapi.yaml",
        "swagger.json"
    ]
    MAX_SEARCH_DEPTH = 3
```

## Common Tasks

### Adding a New CLI Command

1. Edit `jmeter_gen/cli.py`:

```python
@cli.command()
@click.option("--jmx", required=True)
def optimize(jmx):
    """Optimize JMX file configuration"""
    console.print(f"[blue]Optimizing:[/blue] {jmx}")
    # Implementation
```

2. Test manually:

```bash
jmeter-gen optimize --jmx test.jmx
```

3. Add tests in `tests/test_cli.py`

### Adding a New Core Module

1. Create file: `jmeter_gen/core/new_module.py`
2. Implement class and methods
3. Add to `jmeter_gen/core/__init__.py`:

```python
from .new_module import NewModule

__all__ = ["ProjectAnalyzer", "OpenAPIParser", "JMXGenerator", "NewModule"]
```

4. Add tests: `tests/core/test_new_module.py`

### Adding Dependencies

1. Edit `pyproject.toml`:

```toml
[project]
dependencies = [
    "click>=8.1.0",
    "rich>=13.0.0",
    "new-package>=1.0.0"
]
```

2. Reinstall:

```bash
pip install -e ".[dev]"
```

## MCP Server Development

### Testing MCP Server Locally

1. Start MCP Server:

```bash
jmeter-gen mcp
```

2. In another terminal, use MCP client to test:

```python
# test_mcp_client.py
import asyncio
from mcp.client.stdio import stdio_client

async def test():
    async with stdio_client("jmeter-gen", ["mcp"]) as client:
        # List tools
        tools = await client.list_tools()
        print("Available tools:", tools)

        # Call tool
        result = await client.call_tool(
            "analyze_project_for_jmeter",
            {"project_path": "/workspace/my-api"}
        )
        print("Result:", result)

asyncio.run(test())
```

### Testing with GitHub Copilot

1. Configure in VS Code `settings.json`:

```json
{
  "github.copilot.chat.mcp.servers": {
    "jmeter-test-generator": {
      "command": "jmeter-gen",
      "args": ["mcp"]
    }
  }
}
```

2. Reload VS Code

3. Open project with OpenAPI spec

4. Ask Copilot: "Generate JMeter test for this project"

## Troubleshooting

### Import Errors

```bash
# Reinstall in editable mode
pip install -e .

# Or reinstall with dev dependencies
pip install -e ".[dev]"
```

### Tests Not Found

```bash
# Make sure you're in the right directory
cd app/

# Run with verbose output
pytest -v
```

### MCP Server Not Starting

```bash
# Check dependencies
pip list | grep mcp

# Reinstall MCP SDK
pip install --upgrade mcp
```

### JMeter Can't Load Generated JMX

```bash
# Validate JMX
jmeter-gen validate performance-test.jmx

# Check XML structure
xmllint performance-test.jmx

# Test in JMeter GUI mode
jmeter
# Then: File → Open → performance-test.jmx
```

## CI/CD (Future)

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -e ".[dev]"
      - run: pytest --cov=jmeter_gen
      - run: ruff check .
```

## Release Process (Future)

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create git tag: `git tag v1.0.0`
4. Push tag: `git push --tags`
5. Build package: `python -m build`
6. Publish to PyPI: `twine upload dist/*`

## Getting Help

- Check documentation in `docs/`
- Review examples in `examples/`
- Look at existing tests for patterns
- Ask in team chat or create GitHub issue

## Contributing

1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Ensure all tests pass
5. Submit pull request

## Useful Commands Cheat Sheet

```bash
# Development
pip install -e ".[dev]"           # Install in dev mode
pytest                            # Run tests
pytest --cov                      # Run with coverage
ruff check .                      # Lint code
ruff format .                     # Format code
mypy jmeter_gen/                  # Type check

# Testing
jmeter-gen analyze                # Test analyze command
jmeter-gen generate               # Test generate command
jmeter-gen validate test.jmx      # Test validate command
jmeter-gen mcp                    # Start MCP server

# JMeter
jmeter -n -t test.jmx -l results.jtl    # Run test headless
jmeter                                   # Open GUI

# Git
git checkout -b feature/name      # Create branch
git commit -m "feat: description" # Commit
git push origin feature/name      # Push

# Cleanup
rm -rf venv                       # Remove venv
find . -type d -name __pycache__ -exec rm -rf {} +  # Clean cache
```

## Next Steps

1. Read `IMPLEMENTATION_PLAN.md` for roadmap
2. Read `ARCHITECTURE.md` for system design
3. Read `CORE_MODULES.md` for module specs
4. Pick a task from Phase 1 and start coding
5. Test frequently with real-world API projects

Happy coding!
