# JMeter Test Generator

Generate JMeter JMX test plans from OpenAPI specifications.

## Features

- Automatic OpenAPI/Swagger spec detection in projects
- **Multi-spec selection** - Choose which spec to use when multiple are found
- Support for OpenAPI 3.x (3.0.0 - 3.1.x) and Swagger 2.0
- **Scenario-based testing** - Define sequential user flows with pt_scenario.yaml
- **Variable capture & correlation** - Extract response values for subsequent steps
- **Interactive wizard** - `jmeter-gen new scenario` for guided scenario creation
- **Scenario visualization** - Terminal and Mermaid diagram output
- Generate JMX files with HTTP samplers, assertions, and listeners
- Dual mode: CLI and MCP Server (GitHub Copilot integration)
- Rich terminal output with tables and formatting
- JMX validation and recommendations
- Configurable thread groups (threads, ramp-up, duration/iterations)
- HTTP Request Defaults for centralized server configuration

## Requirements

- Python 3.9+
- Dependencies (automatically installed):
  - click >= 8.1.0
  - rich >= 13.0.0
  - pyyaml >= 6.0
  - mcp >= 1.0.0 (MCP SDK for GitHub Copilot integration)
  - pydantic >= 2.7.0
  - anyio >= 4.5
  - httpx >= 0.27

## Installation

### Development Mode (from source directory)

```bash
# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### User-wide Installation (run from any directory)

To use `jmeter-gen` from any directory without activating a virtual environment:

```bash
cd /path/to/jmeter-test-generator/app
pip install --user -e ".[dev]"
```

**Windows:** Ensure Python Scripts directory is in PATH:
```cmd
# Find your Scripts directory
python -c "import site; print(site.getusersitepackages().replace('site-packages', 'Scripts'))"

# Typical path: C:\Users\USERNAME\AppData\Roaming\Python\Python3XX\Scripts
```

Add this path to your system PATH environment variable, then restart your terminal.

**Linux/Mac:** The user bin directory (`~/.local/bin`) is usually already in PATH.

### Verify Installation

```bash
jmeter-gen --version
jmeter-gen --help
```

## Quick Start

### CLI Mode

```bash
# Analyze project for OpenAPI specs
jmeter-gen analyze

# Generate JMX file
jmeter-gen generate

# Generate with custom configuration
jmeter-gen generate --threads 50 --rampup 10 --duration 300 --output load-test.jmx

# Validate JMX script
jmeter-gen validate script performance-test.jmx

# Validate scenario file
jmeter-gen validate scenario pt_scenario.yaml --spec openapi.yaml

# Create scenario interactively (wizard)
jmeter-gen new scenario
```

### MCP Server Mode (GitHub Copilot)

Configure in VS Code settings.json:
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

The MCP Server provides 9 tools for Copilot integration:

| Tool | Description |
|------|-------------|
| `analyze_project_for_jmeter` | Discover OpenAPI specs and scenario files |
| `generate_jmx_from_openapi` | Generate JMX from OpenAPI spec |
| `generate_scenario_jmx` | Generate JMX from pt_scenario.yaml |
| `validate_jmx` | Validate JMX file structure |
| `validate_scenario` | Validate pt_scenario.yaml before generation |
| `visualize_scenario` | Visualize scenario with Mermaid diagram |
| `list_endpoints` | List all endpoints from OpenAPI spec |
| `suggest_captures` | Suggest capturable variables for endpoint |
| `build_scenario` | Build pt_scenario.yaml from step definitions |

Example prompts in Copilot:
```
"Analyze this project for JMeter testing"
"List all endpoints from the OpenAPI spec"
"Suggest captures for the createUser endpoint"
"Build a scenario with login, create item, and logout steps"
```

### CI/CD Integration

Use jmeter-gen in pipelines (Azure DevOps, GitHub Actions, etc.):

```bash
# Generate JMX from URL with explicit scenario file
jmeter-gen generate \
  --spec https://api.example.com/swagger.json \
  --scenario ./scenarios/login-flow.yaml \
  --output ./tests/performance.jmx \
  --base-url https://api.example.com \
  --insecure  # skip SSL verification if needed
```

**CI-friendly features (v3.4.0+):**
- `--spec URL` - Download spec from HTTP/HTTPS URL
- `--scenario PATH` - Explicit scenario file (no auto-discovery)
- `--insecure` - Skip SSL verification for spec download
- Auto-detect CI environment (CI, TF_BUILD, GITHUB_ACTIONS, etc.)
- Plain text output without colors when CI detected

**Azure DevOps example:**
```yaml
- script: |
    pip install jmeter-test-generator
    jmeter-gen generate \
      --spec $(SWAGGER_URL) \
      --scenario pipeline/loadtest/pt_scenario.yaml \
      --output $(Build.ArtifactStagingDirectory)/test.jmx \
      --base-url $(API_BASE_URL)
  displayName: 'Generate JMeter test plan'
```

## Architecture

```
jmeter-gen (core logic)
    |
    +-- CLI Mode (terminal commands)
    +-- MCP Mode (Copilot integration)
```

Both modes share the same core logic.

## Documentation

- [Quick Start Guide](QUICKSTART.md) - 5-minute getting started
- [Changelog](CHANGELOG.md) - Version history

### Feature Documentation
- [Scenario Wizard](docs/v3/README.md) - Interactive wizard for creating scenarios
- [Scenario Specification](docs/v2/PT_SCENARIO_SPEC.md) - pt_scenario.yaml format
- [Scenario Testing](docs/v2/README.md) - Scenario-based test generation

### Developer Documentation
- [Architecture](docs/v1/ARCHITECTURE.md)
- [Development Guide](docs/v1/DEVELOPMENT.md)
- [Core Modules](docs/v2/CORE_MODULES.md)

## Project Structure

```
app/
├── jmeter_gen/              # Main package
│   ├── core/                # Core logic (shared)
│   │   ├── project_analyzer.py
│   │   ├── openapi_parser.py
│   │   ├── jmx_generator.py
│   │   ├── jmx_validator.py
│   │   ├── spec_comparator.py      # Change detection
│   │   ├── snapshot_manager.py     # Snapshot management
│   │   ├── jmx_updater.py          # JMX updates
│   │   ├── ptscenario_parser.py    # Scenario parsing
│   │   ├── correlation_analyzer.py # Auto-correlation
│   │   ├── scenario_jmx_generator.py # Scenario JMX
│   │   ├── scenario_visualizer.py  # Terminal visualization
│   │   ├── scenario_mermaid.py     # Mermaid diagrams
│   │   └── scenario_wizard.py      # Interactive wizard
│   ├── cli.py               # CLI interface
│   └── mcp_server.py        # MCP Server interface
├── tests/                   # Unit and integration tests
├── docs/                    # Documentation
└── pyproject.toml           # Project configuration
```

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .

# Format code
ruff format .
```

## Examples

See [examples/](examples/) directory for:
- Petstore API example (Swagger 2.0)
- Simple CRUD API example (OpenAPI 3.0)
- Multi-endpoint API scenarios

## License

MIT License
