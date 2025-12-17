# Architecture - JMeter Test Generator

## System Overview

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                            User Interfaces                                    │
│                                                                               │
│  ┌──────────────────────┐                 ┌──────────────────────┐           │
│  │     CLI Mode         │                 │     MCP Mode         │           │
│  │    (Terminal)        │                 │    (Copilot)         │           │
│  └──────────┬───────────┘                 └──────────┬───────────┘           │
│             │                                        │                        │
│             └────────────────┬───────────────────────┘                        │
│                              │                                                │
└──────────────────────────────┼────────────────────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                          Core Logic (Shared)                                  │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                      Base Modules (v1.0)                                │ │
│  │                                                                         │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐           │ │
│  │  │ Project        │  │ OpenAPI        │  │ JMX            │           │ │
│  │  │ Analyzer       │→ │ Parser         │→ │ Generator      │           │ │
│  │  └────────────────┘  └────────────────┘  └───────┬────────┘           │ │
│  │                                                   │                    │ │
│  │                                         ┌─────────▼────────┐           │ │
│  │                                         │ JMX Validator    │           │ │
│  │                                         └──────────────────┘           │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                   Change Detection Modules (v1.1)                       │ │
│  │                                                                         │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐           │ │
│  │  │ Spec           │  │ Snapshot       │  │ JMX            │           │ │
│  │  │ Comparator     │→ │ Manager        │→ │ Updater        │           │ │
│  │  └────────────────┘  └────────────────┘  └────────────────┘           │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    Scenario Modules (v2.0/v3.0)                         │ │
│  │                                                                         │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐           │ │
│  │  │ PtScenario     │  │ Correlation    │  │ Scenario JMX   │           │ │
│  │  │ Parser         │→ │ Analyzer       │→ │ Generator      │           │ │
│  │  └───────┬────────┘  └────────────────┘  └────────────────┘           │ │
│  │          │                                                             │ │
│  │          ▼                                                             │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐           │ │
│  │  │ Scenario       │  │ Scenario       │  │ Scenario       │           │ │
│  │  │ Validator      │  │ Visualizer     │  │ Mermaid        │           │ │
│  │  └────────────────┘  └────────────────┘  └────────────────┘           │ │
│  │                                                                        │ │
│  │  ┌────────────────┐                                                   │ │
│  │  │ Scenario       │  (v3.0 - Interactive Wizard)                      │ │
│  │  │ Wizard         │                                                   │ │
│  │  └────────────────┘                                                   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Design Principles

1. **Separation of Concerns**: Core logic separated from interfaces
2. **DRY (Don't Repeat Yourself)**: CLI and MCP share the same core
3. **Single Responsibility**: Each module has one clear purpose
4. **Open/Closed**: Easy to extend (new features) without modifying core
5. **Dependency Inversion**: Depend on abstractions, not implementations

## Component Architecture

### Layer 1: User Interfaces

#### CLI Interface (jmeter_gen/cli.py)

**Responsibilities**:
- Parse command-line arguments
- Validate user input
- Format output for terminal
- Handle errors and display messages
- Delegate to core logic

**Technology**:
- Click: CLI framework
- Rich: Terminal formatting and tables

**Commands**:
1. `analyze` - Scan project for OpenAPI specs
2. `generate` - Generate JMX from spec
3. `validate` - Validate JMX file
4. `mcp` - Start MCP Server mode

**Example Flow**:
```
User runs: jmeter-gen generate --threads 50

CLI:
  1. Parse args (threads=50)
  2. Call ProjectAnalyzer.analyze_project()
  3. Call OpenAPIParser.parse()
  4. Call JMXGenerator.generate()
  5. Display success message with Rich
```

#### MCP Server Interface (jmeter_gen/mcp_server.py)

**Responsibilities**:
- Implement MCP protocol
- Expose tools for AI assistants
- Translate MCP calls to core logic
- Format responses for Copilot

**Technology**:
- MCP Python SDK
- stdio transport

**Tools** (9 total):
1. `analyze_project_for_jmeter` - Project analysis with change detection
2. `generate_jmx_from_openapi` - JMX generation from OpenAPI spec
3. `generate_scenario_jmx` - JMX generation from pt_scenario.yaml
4. `validate_jmx` - Validate JMX file structure
5. `validate_scenario` - Validate pt_scenario.yaml before generation
6. `visualize_scenario` - Visualize scenario with Mermaid diagram
7. `list_endpoints` - List all endpoints from OpenAPI spec
8. `suggest_captures` - Suggest capturable variables for endpoint
9. `build_scenario` - Build pt_scenario.yaml from step definitions

**Example Flow**:
```
Copilot: "Generate JMeter test"

MCP Server:
  1. Receive MCP tool call
  2. Parse arguments
  3. Call ProjectAnalyzer.analyze_project()
  4. Call OpenAPIParser.parse()
  5. Call JMXGenerator.generate()
  6. Return formatted text response
```

### Layer 2: Core Logic (Shared)

All core modules are in `jmeter_gen/core/` and are shared between CLI and MCP.

#### Project Analyzer (core/project_analyzer.py)

**Purpose**: Find OpenAPI specifications in project directory

**Class**: `ProjectAnalyzer`

**Key Methods**:
```python
class ProjectAnalyzer:
    def find_openapi_spec(self, project_path: str) -> Optional[Dict]:
        """Find OpenAPI spec in project"""

    def analyze_project(self, project_path: str) -> Dict:
        """Complete project analysis with endpoints overview"""
```

**Algorithm**:
1. Check common file names (openapi.yaml, swagger.json, etc.)
2. If not found, recursive search (max 3 levels deep)
3. Return spec path, format, and metadata
4. If multiple specs found, prefer openapi.yaml

**Input**:
```python
project_path = "/workspace/my-api-project"
```

**Output**:
```python
{
    "openapi_spec_found": True,
    "spec_path": "/workspace/.../openapi.yaml",
    "spec_format": "yaml",
    "endpoints_count": 5,
    "endpoints": [...],
    "base_url": "http://localhost:8080",
    "api_title": "User Management API",
    "recommended_jmx_name": "user-management-api-test.jmx"
}
```

#### OpenAPI Parser (core/openapi_parser.py)

**Purpose**: Parse OpenAPI 3.0.x specifications

**Class**: `OpenAPIParser`

**Key Methods**:
```python
class OpenAPIParser:
    def parse(self, spec_path: str) -> Dict:
        """Parse OpenAPI spec file"""

    def _parse_endpoints(self, paths: Dict) -> List[Dict]:
        """Extract endpoints from paths"""

    def _get_base_url(self, servers: List[Dict]) -> str:
        """Extract base URL, prefer localhost"""
```

**Algorithm**:
1. Load YAML or JSON file
2. Extract info (title, version)
3. Extract servers (prefer localhost)
4. Parse paths and operations
5. Return structured data

**Input**:
```python
spec_path = "/workspace/.../openapi.yaml"
```

**Output**:
```python
{
    "title": "User Management API",
    "version": "1.0.0",
    "base_url": "http://localhost:3000",
    "endpoints": [
        {
            "path": "/api/v1/users",
            "method": "POST",
            "operationId": "createUser",
            "summary": "Create a new user",
            "requestBody": True,
            "parameters": []
        },
        ...
    ],
    "spec": {...}  # Full spec for reference
}
```

#### JMX Generator (core/jmx_generator.py)

**Purpose**: Generate JMeter JMX files from OpenAPI data

**Class**: `JMXGenerator`

**Key Methods**:
```python
class JMXGenerator:
    def generate(
        self,
        spec_data: Dict,
        output_path: str,
        endpoints: List[str] = None,
        threads: int = 10,
        rampup: int = 5,
        duration: int = 60
    ) -> Dict:
        """Generate JMX file"""

    def _create_test_plan(self, title: str, ...) -> ET.Element:
        """Create Test Plan XML element"""

    def _create_thread_group(self, threads: int, ...) -> ET.Element:
        """Create Thread Group XML element"""

    def _create_http_sampler(self, endpoint: Dict, base_url: str) -> ET.Element:
        """Create HTTP Request Sampler"""

    def _create_assertions(self, endpoint: Dict) -> List[ET.Element]:
        """Create Response Assertions"""

    def _prettify_xml(self, elem: ET.Element) -> str:
        """Format XML with indentation"""
```

**Algorithm**:
1. Create Test Plan element
2. Add Thread Group with configuration
3. For each endpoint:
   - Create HTTP Request Sampler
   - Parse base URL to domain, port, protocol
   - Set method, path, parameters
   - Add Response Assertion (200/201)
4. Build XML tree structure
5. Pretty-print and save to file

**JMX Structure**:
```xml
<jmeterTestPlan>
  <hashTree>
    <TestPlan testname="API Performance Test">
      <boolProp name="TestPlan.functional_mode">false</boolProp>
    </TestPlan>
    <hashTree>
      <ThreadGroup testname="Thread Group">
        <stringProp name="ThreadGroup.num_threads">10</stringProp>
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
        <stringProp name="ThreadGroup.duration">60</stringProp>
      </ThreadGroup>
      <hashTree>
        <HTTPSamplerProxy testname="POST /api/trigger">
          <stringProp name="HTTPSampler.domain">localhost</stringProp>
          <stringProp name="HTTPSampler.port">3300</stringProp>
          <stringProp name="HTTPSampler.protocol">http</stringProp>
          <stringProp name="HTTPSampler.path">/service/.../trigger</stringProp>
          <stringProp name="HTTPSampler.method">POST</stringProp>
        </HTTPSamplerProxy>
        <hashTree>
          <ResponseAssertion testname="Assert 201">
            <stringProp name="Assertion.test_field">Assertion.response_code</stringProp>
            <stringProp name="Assertion.test_string">201</stringProp>
          </ResponseAssertion>
          <hashTree/>
        </hashTree>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
```

**Input**:
```python
spec_data = {
    "title": "Service CF Agent API",
    "base_url": "http://localhost:3300",
    "endpoints": [...]
}
output_path = "performance-test.jmx"
threads = 50
rampup = 10
duration = 300
```

**Output**:
```python
{
    "success": True,
    "jmx_path": "performance-test.jmx",
    "samplers_created": 5,
    "assertions_added": 5,
    "threads": 50,
    "rampup": 10,
    "duration": 300,
    "summary": "Created JMX with 5 HTTP samplers, 50 threads, 10s ramp-up, 300s duration"
}
```

#### JMX Validator (core/jmx_validator.py)

**Purpose**: Validate JMX file structure and provide recommendations

**Class**: `JMXValidator`

**Key Methods**:
```python
class JMXValidator:
    def validate(self, jmx_path: str) -> Dict:
        """Validate JMX file"""

    def _check_structure(self, root: ET.Element) -> List[str]:
        """Check for required elements"""

    def _check_configuration(self, root: ET.Element) -> List[str]:
        """Check configuration best practices"""

    def _generate_recommendations(self, root: ET.Element) -> List[str]:
        """Generate improvement recommendations"""
```

**Validation Checks**:
1. Valid XML structure
2. Required elements present (TestPlan, ThreadGroup)
3. At least one sampler exists
4. Thread Group has valid configuration
5. Samplers have domain and path set

**Recommendations**:
1. Add CSV Data Set Config for test data
2. Add timers for realistic load
3. Add listeners for results collection
4. Configure assertions for validation

**Input**:
```python
jmx_path = "performance-test.jmx"
```

**Output**:
```python
{
    "valid": True,
    "issues": [],
    "recommendations": [
        "Consider adding CSV Data Set Config for test data",
        "Add Response Time assertion for performance validation",
        "Add View Results Tree listener for debugging"
    ]
}
```

## Data Flow

### End-to-End Flow: Generate JMX

```
1. User Input
   CLI: jmeter-gen generate --threads 50
   MCP: "Generate JMeter test with 50 users"

2. Interface Layer (CLI or MCP)
   - Parse input
   - Validate arguments

3. Project Analyzer
   - Scan project directory
   - Find openapi.yaml
   - Return spec location

4. OpenAPI Parser
   - Load openapi.yaml
   - Parse endpoints
   - Extract base_url from spec
   - Return structured data

5. Interface Layer
   - Prompt user: "Enter base URL (press Enter for default: http://localhost:8080):"
   - User input: custom URL or empty (use default)
   - Pass base_url override to JMX Generator (if provided)

6. JMX Generator
   - Determine final base_url (user override or spec default)
   - Parse base_url to domain/port/protocol
   - Create XML structure
   - Add Test Plan
   - Add Thread Group (50 threads)
   - Add HTTP Request Defaults (ConfigTestElement) with domain/port/protocol
   - Add HTTP Samplers (5 endpoints) with ONLY path (inherit from defaults)
   - Add Assertions
   - Save to file

7. Interface Layer
   - Format success message
   - Display to user

8. User Output
   CLI: "SUCCESS! Generated performance-test.jmx with 5 samplers"
   MCP: "Created performance-test.jmx with 5 endpoints, 50 users"
```

## Module Dependencies

```
                              ┌─────────────────────────────────────────────────────────┐
                              │                    Core Modules                         │
                              │                                                         │
CLI ────────┐                 │  Base Flow (v1.0):                                     │
            │                 │  ProjectAnalyzer → OpenAPIParser → JMXGenerator        │
            │                 │                                          ↓              │
            │                 │                                    JMXValidator         │
            ├──→──────────────┤                                                         │
            │                 │  Change Detection (v1.1):                              │
            │                 │  SpecComparator → SnapshotManager → JMXUpdater         │
            │                 │                                                         │
MCP Server ─┘                 │  Scenario Flow (v2.0/v3.0):                            │
                              │  PtScenarioParser ──┬──→ ScenarioValidator             │
                              │         ↓           │                                   │
                              │  CorrelationAnalyzer│                                   │
                              │         ↓           │                                   │
                              │  ScenarioJMXGenerator                                   │
                              │                     │                                   │
                              │  ScenarioVisualizer ←──┘                               │
                              │         ↓                                               │
                              │  ScenarioMermaid                                        │
                              │                                                         │
                              │  ScenarioWizard (v3.0) - standalone, uses OpenAPIParser │
                              └─────────────────────────────────────────────────────────┘

Legend:
→  depends on / data flows to
```

**All Core Modules** (14 total):

| Module | File | Purpose | Version |
|--------|------|---------|---------|
| ProjectAnalyzer | `project_analyzer.py` | Find OpenAPI specs in project | v1.0 |
| OpenAPIParser | `openapi_parser.py` | Parse OpenAPI/Swagger specs | v1.0 |
| JMXGenerator | `jmx_generator.py` | Generate JMX from spec | v1.0 |
| JMXValidator | `jmx_validator.py` | Validate JMX structure | v1.0 |
| SpecComparator | `spec_comparator.py` | Compare OpenAPI specs | v1.1 |
| SnapshotManager | `snapshot_manager.py` | Manage spec snapshots | v1.1 |
| JMXUpdater | `jmx_updater.py` | Update existing JMX files | v1.1 |
| PtScenarioParser | `ptscenario_parser.py` | Parse pt_scenario.yaml | v2.0 |
| CorrelationAnalyzer | `correlation_analyzer.py` | Auto-detect JSONPath for captures | v2.0 |
| ScenarioJMXGenerator | `scenario_jmx_generator.py` | Generate JMX from scenarios | v2.0 |
| ScenarioValidator | `scenario_validator.py` | Validate scenarios against spec | v2.0 |
| ScenarioVisualizer | `scenario_visualizer.py` | Rich terminal visualization | v2.0 |
| ScenarioMermaid | `scenario_mermaid.py` | Generate Mermaid diagrams | v2.0 |
| ScenarioWizard | `scenario_wizard.py` | Interactive scenario creation | v3.0 |

**Dependency Rules**:
1. CLI and MCP do NOT depend on each other
2. Core modules do NOT depend on CLI or MCP
3. Core modules have minimal dependencies between them
4. Each module can be tested independently
5. Scenario modules depend on OpenAPIParser for spec data
6. Change detection modules work independently of scenario modules

## Technology Stack

### Core
- Python 3.9+
- xml.etree.ElementTree (XML generation)
- PyYAML (YAML parsing)
- pathlib (File operations)

### CLI Interface
- Click 8.1+ (CLI framework)
- Rich 13.0+ (Terminal formatting)

### MCP Interface
- MCP Python SDK 1.0+ (MCP protocol)

### Development
- pytest (Testing)
- ruff (Linting and formatting)
- mypy (Type checking)

### Optional
- lxml (Alternative XML library, if needed)
- pydantic (Data validation, if needed)

## File Structure

```
jmeter-test-generator/
├── jmeter_gen/
│   ├── __init__.py               # Package initialization
│   ├── cli.py                    # CLI interface (Click)
│   ├── mcp_server.py             # MCP Server interface
│   ├── exceptions.py             # Custom exceptions
│   └── core/
│       ├── __init__.py
│       ├── project_analyzer.py   # Find OpenAPI specs
│       ├── openapi_parser.py     # Parse OpenAPI
│       ├── jmx_generator.py      # Generate JMX
│       ├── jmx_validator.py      # Validate JMX
│       ├── ptscenario_parser.py  # Parse pt_scenario.yaml
│       ├── scenario_jmx_generator.py  # Generate JMX from scenarios
│       ├── scenario_validator.py # Validate scenarios
│       ├── scenario_wizard.py    # Interactive wizard
│       ├── spec_comparator.py    # Compare OpenAPI specs
│       ├── snapshot_manager.py   # Manage spec snapshots
│       └── jmx_updater.py        # Update existing JMX
├── tests/
│   ├── conftest.py               # Shared fixtures
│   ├── core/                     # Core module tests
│   ├── fixtures/                 # Test data files
│   ├── test_cli.py
│   ├── test_cli_integration.py
│   ├── test_mcp_server.py
│   ├── test_error_handling.py
│   └── test_edge_cases.py
├── examples/
│   ├── petstore/
│   │   ├── swagger.json
│   │   └── petstore-test.jmx
│   └── simple-crud/
│       ├── openapi.yaml
│       └── simple-crud-test.jmx
├── docs/
│   ├── PT_SCENARIO_SPEC.md
│   ├── PT_SCENARIO_CHEATSHEET.md
│   ├── BACKLOG.md
│   ├── TESTING.md
│   └── dev/
│       ├── ARCHITECTURE.md       # This file
│       ├── CORE_MODULES.md
│       ├── DEVELOPMENT.md
│       └── JMX_FORMAT_REFERENCE.md
├── .vscode/
│   └── settings.json             # MCP configuration
├── pyproject.toml                # Project config
├── README.md
├── QUICKSTART.md
├── CHANGELOG.md
├── CLAUDE.md
└── TODO.md
```

## Extension Points

The architecture allows for easy extension:

### 1. New Commands (CLI)
Add new commands to `cli.py` without modifying core.

Example:
```python
@cli.command()
def optimize(jmx_path):
    """Optimize existing JMX file"""
    # New command, uses core modules
```

### 2. New MCP Tools
Add new tools to `mcp_server.py`.

Example:
```python
@server.list_tools()
async def list_tools():
    return [
        # Existing tools...
        Tool(
            name="optimize_jmx",
            description="Optimize JMX configuration"
        )
    ]
```

### 3. New Core Modules
Add new modules to `core/` for new features.

Example:
```
core/csv_generator.py  # Generate CSV test data
core/auth_handler.py   # Handle authentication
```

### 4. New Output Formats
Extend JMXGenerator to support other formats.

Example:
```python
class K6Generator:
    """Generate k6 scripts instead of JMX"""
```

## Design Patterns Used

### 1. Facade Pattern
- CLI and MCP Server act as facades to core logic
- Simplifies complex core interactions

### 2. Strategy Pattern
- Different data generation strategies (future)
- Different assertion strategies

### 3. Builder Pattern
- JMXGenerator builds complex XML structures step by step

### 4. Template Method Pattern
- Templates for common JMX elements

## Error Handling Strategy

### Layers of Error Handling

1. **Input Validation** (CLI/MCP layer)
   - Validate user input
   - Check file paths exist
   - Return user-friendly errors

2. **Core Logic** (Core layer)
   - Raise specific exceptions
   - Provide error context
   - Don't catch exceptions (let them bubble up)

3. **Interface Layer** (CLI/MCP layer)
   - Catch core exceptions
   - Format for user
   - Log errors

### Exception Hierarchy

```python
class JMeterGenException(Exception):
    """Base exception"""

class SpecNotFoundException(JMeterGenException):
    """OpenAPI spec not found"""

class InvalidSpecException(JMeterGenException):
    """Invalid OpenAPI spec"""

class JMXGenerationException(JMeterGenException):
    """JMX generation failed"""

class JMXValidationException(JMeterGenException):
    """JMX validation failed"""
```

## Performance Considerations

### Target Performance

- Project analysis: <1 second
- OpenAPI parsing: <0.5 seconds
- JMX generation: <2 seconds (for 50 endpoints)
- Total end-to-end: <5 seconds

### Optimization Strategies

1. **Lazy Loading**: Only parse spec when needed
2. **Caching**: Cache parsed specs (future)
3. **Streaming**: Stream XML output for large JMX files
4. **Parallel Processing**: Parse multiple specs in parallel (future)

## Security Considerations

1. **Path Traversal**: Validate file paths, prevent directory traversal
2. **XML Injection**: Sanitize user input before XML generation
3. **Command Injection**: Avoid shell execution
4. **Sensitive Data**: Don't log sensitive information (API keys, passwords)

## Testing Strategy

### Unit Tests
- Test each core module independently
- Mock dependencies
- Test edge cases

### Integration Tests
- Test CLI with real OpenAPI specs
- Test MCP Server with real requests
- Test end-to-end flow

### Test Data
- Use real-world OpenAPI specs
- Create minimal test specs
- Test error cases (invalid YAML, missing fields)

## Deployment

### CLI Deployment
```bash
pip install jmeter-test-generator
jmeter-gen --version
```

### MCP Server Deployment
- No separate deployment needed
- Configured in VS Code settings
- Runs via `jmeter-gen mcp` command

## Future Architecture Enhancements

### v1.1
- Plugin system for custom generators
- Configuration file support (.jmetergenrc)

### v1.2
- Web UI for configuration
- REST API for remote generation

## Conclusion

This architecture provides:
- Clear separation of concerns
- Reusable core logic
- Easy testing
- Simple extension
- Multiple interfaces (CLI, MCP)
- Production-ready structure

The key design decision is to share core logic between CLI and MCP, avoiding code duplication while providing multiple user interfaces.
