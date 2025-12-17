# Testing Strategy

This document describes the testing architecture and guidelines for the JMeter Test Generator project.

## Overview

The project uses pytest as the testing framework with comprehensive coverage across unit, integration, and CLI tests.

**Key Statistics:**
- 677+ tests
- 21 test files
- 82% code coverage

## Directory Structure

```
tests/
├── conftest.py                    # Shared fixtures (22 fixtures)
├── core/                          # Unit tests for core modules
│   ├── test_jmx_generator.py      # JMX generation
│   ├── test_openapi_parser.py     # OpenAPI/Swagger parsing
│   ├── test_jmx_validator.py      # JMX validation
│   ├── test_project_analyzer.py   # Project scanning
│   ├── test_spec_comparator.py    # Spec comparison
│   ├── test_snapshot_manager.py   # Snapshot handling
│   ├── test_jmx_updater.py        # JMX updates
│   └── *_v2.py                    # v2 scenario-based tests
├── fixtures/                      # Test data files
│   └── scenarios/                 # YAML scenario fixtures
├── test_cli.py                    # CLI unit tests (with mocks)
├── test_cli_integration.py        # CLI integration tests (no mocks)
├── test_edge_cases.py             # Boundary condition tests
├── test_error_handling.py         # Error scenario tests
└── test_mcp_server.py             # MCP server async tests
```

## Test Categories

### Custom Pytest Markers

The project uses custom markers to categorize tests:

```python
@pytest.mark.unit          # Unit tests
@pytest.mark.integration   # Integration tests (real I/O)
@pytest.mark.v2            # v2 scenario-based tests
@pytest.mark.slow          # Slow-running tests
```

**Running specific categories:**

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only v2 tests
pytest -m v2

# Exclude slow tests
pytest -m "not slow"

# Exclude integration tests for quick feedback
pytest -m "not integration"
```

### Unit Tests (tests/core/)

Unit tests verify individual module behavior in isolation:

- Use mocks for external dependencies
- Focus on business logic correctness
- High coverage per module (80%+ target)

Example:
```python
class TestJMXGenerator:
    @pytest.fixture
    def generator(self):
        return JMXGenerator()

    def test_generate_creates_valid_xml(self, generator, sample_spec):
        result = generator.generate(sample_spec, "test.jmx")
        assert result["success"] is True
```

### Integration Tests (test_cli_integration.py)

Integration tests verify end-to-end workflows:

- NO mocks for core modules
- Real file system operations
- Real XML generation and parsing
- Marked with `@pytest.mark.integration`

Example:
```python
@pytest.mark.integration
class TestAnalyzeCommandIntegration:
    def test_analyze_real_openapi_yaml_project(self, project_with_openapi_yaml):
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--path", str(project_with_openapi_yaml)])
        assert result.exit_code == 0
```

### CLI Tests (test_cli.py)

CLI tests verify command-line interface behavior:

- Mock core modules to test CLI logic in isolation
- Use Click's CliRunner for command invocation
- Test argument parsing, output formatting, error handling

Example:
```python
@patch("jmeter_gen.cli.ProjectAnalyzer")
def test_analyze_spec_found(self, mock_analyzer_class, runner):
    mock_analyzer = Mock()
    mock_analyzer_class.return_value = mock_analyzer
    mock_analyzer.analyze_with_change_detection.return_value = {...}

    result = runner.invoke(analyze, ["--path", "."])

    assert result.exit_code == 0
    mock_analyzer.analyze_with_change_detection.assert_called_once_with(".", None)
```

### Async Tests (test_mcp_server.py)

MCP server tests use pytest-asyncio:

```python
@pytest.mark.asyncio
async def test_analyze_project_with_spec_found(self, project_with_openapi_yaml):
    arguments = {"project_path": str(project_with_openapi_yaml)}
    result = await _analyze_project(arguments)

    response = json.loads(result[0].text)
    assert response["success"] is True
```

## Fixtures

### Shared Fixtures (conftest.py)

Common fixtures available to all tests:

| Fixture | Description |
|---------|-------------|
| `project_with_openapi_yaml` | OpenAPI 3.0 YAML spec |
| `project_with_swagger_json` | OpenAPI 3.0 JSON spec |
| `project_with_swagger2_yaml` | Swagger 2.0 YAML spec |
| `project_with_swagger2_json` | Swagger 2.0 JSON spec |
| `project_with_nested_spec` | Spec in subdirectory |
| `project_with_multiple_specs` | Multiple spec files |
| `empty_project` | No spec files |
| `temp_project_dir` | Clean temp directory |
| `invalid_yaml_spec` | Malformed YAML |
| `spec_with_no_endpoints` | Empty paths object |

### v2 Scenario Fixtures

YAML fixtures in `tests/fixtures/scenarios/`:

- `valid_basic.yaml` - Minimal valid scenario
- `valid_full.yaml` - All features enabled
- `valid_with_captures.yaml` - All 3 capture syntaxes
- `invalid_*.yaml` - Error case scenarios

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=jmeter_gen --cov-report=html

# Run specific file
pytest tests/core/test_jmx_generator.py

# Run specific test
pytest tests/test_cli.py::TestGenerateCommand::test_generate_with_spec_and_base_url_flag

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Coverage Reports

```bash
# Terminal report
pytest --cov=jmeter_gen --cov-report=term-missing

# HTML report (opens in browser)
pytest --cov=jmeter_gen --cov-report=html
open htmlcov/index.html
```

## Writing New Tests

### Guidelines

1. **Test file naming**: `test_<module>.py`
2. **Test class naming**: `Test<ComponentName>`
3. **Test method naming**: `test_<subject>_<condition>_<expected>`
4. **Use fixtures**: Prefer shared fixtures over inline data
5. **Mock assertions**: Always verify mock call arguments

### Mock Assertion Best Practices

```python
# Good - verify arguments
mock_analyzer.analyze_project.assert_called_once_with(".")
call_args = mock_generator.generate.call_args[1]
assert call_args["base_url"] == "http://test.com"

# Avoid - no argument verification
mock_analyzer.analyze_project.assert_called_once()  # Missing arguments
```

### Adding a New Unit Test

```python
# tests/core/test_my_module.py
import pytest
from jmeter_gen.core.my_module import MyModule

class TestMyModule:
    @pytest.fixture
    def module(self):
        return MyModule()

    def test_method_returns_expected_result(self, module):
        """Test that method returns correct value for valid input."""
        result = module.method("input")
        assert result == "expected"

    def test_method_raises_on_invalid_input(self, module):
        """Test that method raises ValueError for invalid input."""
        with pytest.raises(ValueError, match="Invalid input"):
            module.method(None)
```

### Adding a New Integration Test

```python
# Add to tests/test_cli_integration.py
@pytest.mark.integration
class TestNewFeatureIntegration:
    def test_feature_end_to_end(self, project_with_openapi_yaml, tmp_path):
        """Test complete workflow for new feature."""
        runner = CliRunner()
        result = runner.invoke(cli, ["command", "--option", str(tmp_path)])

        assert result.exit_code == 0
        assert (tmp_path / "output.file").exists()
```

## Dual Testing Approach

The project uses a dual testing approach:

1. **CLI Tests (test_cli.py)**: Mock core modules
   - Tests CLI argument parsing
   - Tests output formatting
   - Tests error message display
   - Fast execution

2. **Integration Tests (test_cli_integration.py)**: No mocks
   - Tests real file operations
   - Tests actual JMX generation
   - Tests XML structure correctness
   - Catches integration issues

Both test files should be kept in sync - new CLI features need tests in both files.

## v2 Tests

Tests for v2 scenario-based features are marked with `@pytest.mark.v2`:

```python
# tests/core/test_scenario_parser.py
pytestmark = pytest.mark.v2

class TestScenarioParser:
    def test_parse_valid_scenario(self, parser, fixtures_dir):
        result = parser.parse(fixtures_dir / "valid_basic.yaml")
        assert result.name is not None
```

To run only v2 tests:
```bash
pytest -m v2
```

To exclude v2 tests:
```bash
pytest -m "not v2"
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure package is installed in dev mode (`pip install -e ".[dev]"`)

2. **Fixture not found**: Check fixture is in conftest.py or imported correctly

3. **Async test not running**: Ensure `@pytest.mark.asyncio` decorator is present

4. **Mock not working**: Verify patch path matches import path in tested module

### Debug Mode

```bash
# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Show local variables on failure
pytest -l
```
