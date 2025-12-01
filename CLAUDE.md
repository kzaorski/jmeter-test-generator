# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JMeter Test Generator - A Python CLI tool and MCP Server that generates JMeter JMX test plans from OpenAPI specifications. The project uses a dual-mode architecture where both CLI and MCP Server share the same core logic.

## Common Commands

### Development Setup
```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
jmeter-gen --version
```

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=jmeter_gen --cov-report=html

# Run specific test file
pytest tests/core/test_project_analyzer.py -v

# View coverage report
open htmlcov/index.html
```

### Linting and Formatting
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

### Running the Tool
```bash
# Analyze project for OpenAPI specs
jmeter-gen analyze

# Generate JMX file (from current directory)
jmeter-gen generate

# Generate with custom configuration
jmeter-gen generate --threads 50 --rampup 10 --duration 300 --output performance-test.jmx

# Validate existing JMX file
jmeter-gen validate performance-test.jmx

# Start MCP Server
jmeter-gen mcp

# Create new scenario file (interactive wizard)
jmeter-gen new scenario
jmeter-gen new scenario --spec openapi.yaml --output my_scenario.yaml
```

### Testing with Example Projects
```bash
# Example test project (Petstore API)
cd examples/petstore

# Run analysis
jmeter-gen analyze

# Generate test plan
jmeter-gen generate
```

## Architecture

### Dual-Mode Design
The codebase uses a **shared core logic** pattern:
- **CLI Mode** (`jmeter_gen/cli.py`): Terminal interface using Click and Rich
- **MCP Server Mode** (`jmeter_gen/mcp_server.py`): MCP protocol for GitHub Copilot integration
- **Core Logic** (`jmeter_gen/core/`): Shared business logic used by both interfaces

### Core Modules (in jmeter_gen/core/)
All core modules are shared between CLI and MCP. They must NOT import from CLI or MCP layers.

1. **ProjectAnalyzer** (`project_analyzer.py`): Scans project directories for OpenAPI specs
   - Searches for common spec names (openapi.yaml, swagger.json, etc.)
   - Recursively searches subdirectories (max 3 levels)
   - Returns spec location and metadata
   - `analyze_with_change_detection()` for change detection

2. **OpenAPIParser** (`openapi_parser.py`): Parses OpenAPI 3.0.x specifications
   - Supports YAML and JSON formats
   - Extracts endpoints, base URLs, and metadata
   - Validates OpenAPI version and structure

3. **JMXGenerator** (`jmx_generator.py`): Generates JMeter JMX files
   - Creates XML structure using xml.etree.ElementTree
   - Builds Test Plan, Thread Group, HTTP Samplers, and Assertions
   - Handles URL parsing for domain/port/protocol extraction

4. **JMXValidator** (`jmx_validator.py`): Validates JMX structure
   - Checks for required XML elements
   - Validates ThreadGroup configuration
   - Generates improvement recommendations

5. **SpecComparator** (`spec_comparator.py`): Compare OpenAPI specs
   - Detect added, removed, and modified endpoints
   - Calculate SHA256 endpoint fingerprints
   - Generate SpecDiff reports

6. **SnapshotManager** (`snapshot_manager.py`): Manage spec snapshots
   - Save/load snapshots in `.jmeter-gen/snapshots/`
   - Filter sensitive data (tokens, keys, passwords)
   - Git metadata extraction

7. **JMXUpdater** (`jmx_updater.py`): Update existing JMX files
   - Add new samplers, disable removed ones
   - Preserve user customizations
   - Create timestamped backups

### Data Flow
```
User Input (CLI/MCP)
  ↓
ProjectAnalyzer.analyze_project()
  ↓
OpenAPIParser.parse()
  ↓
JMXGenerator.generate()
  ↓
JMXValidator.validate() (optional)
  ↓
Output (formatted response)
```

### Module Dependencies
- CLI and MCP do NOT depend on each other
- Core modules do NOT depend on CLI or MCP
- Core modules have minimal dependencies between them
- This ensures independent testing and reusability

## Implementation Status

### Completed
- **Phase 1: Core Logic** ✅ COMPLETED
  - ProjectAnalyzer (90% coverage)
  - OpenAPIParser (100% coverage, Swagger 2.0 + OpenAPI 3.0.x)
  - JMXGenerator (98% coverage, HTTP Request Defaults pattern)
  - JMXValidator (100% coverage)
- **Phase 2: CLI Interface** ✅ COMPLETED
  - CLI commands: analyze, generate, validate, mcp (94% coverage)
  - Rich formatting, error handling, interactive prompts
- **Phase 3: MCP Server** ✅ COMPLETED
  - MCP Server with 8 tools (78% coverage)
  - `analyze_project_for_jmeter`: project_path, detect_changes, jmx_path, **scenario detection**
  - `generate_jmx_from_openapi`: spec_path, output_path, threads, rampup, duration, base_url, detect_changes, auto_update, export_diff_path
  - `generate_scenario_jmx`: scenario_path, spec_path, output_path, base_url_override, **auto-filename**
  - `validate_jmx`: jmx_path - validates JMX structure with recommendations
  - `visualize_scenario`: scenario_path, spec_path - returns JSON, text, and Mermaid diagram
  - `list_endpoints`: spec_path - list all endpoints from OpenAPI spec
  - `suggest_captures`: spec_path, endpoint - suggest capturable variables from response
  - `build_scenario`: spec_path, steps, name, settings - build pt_scenario.yaml from steps
  - Full async/await implementation
  - Integrated validation workflow
- **Change Detection Modules** ✅ COMPLETED
  - SpecComparator (96% coverage) - Compare specs, detect changes
  - SnapshotManager (93% coverage) - Save/load snapshots, filter sensitive data
  - JMXUpdater (82% coverage) - Update existing JMX files
  - CLI extensions: change detection (default), --auto-update, --export-diff
- **v1.1.0 Multi-Spec Support** - find_all_openapi_specs(), interactive selection
- **v2.0.0 Scenario-Based Testing** ✅ COMPLETED
  - PtScenarioParser, CorrelationAnalyzer, ScenarioJMXGenerator, ScenarioVisualizer
  - ScenarioMermaid module for diagram generation
  - Full MCP integration with 5 tools
- **v3.0.0 Scenario Init Wizard** ✅ COMPLETED
  - ScenarioWizard interactive CLI wizard
  - `jmeter-gen new scenario` command
  - Auto-detect OpenAPI spec, smart capture suggestions
  - Loop and think time support
- **Overall**: 677 tests passing, 82% code coverage
- Project structure and configuration (pyproject.toml)
- Package initialization files
- Comprehensive documentation (8 docs)
- VS Code configuration with MCP setup

### Implementation Order (Step-by-Step)

**Phase 1: Core Logic**
1. **Step 1:** `jmeter_gen/core/project_analyzer.py` - File discovery
   - Implement ProjectAnalyzer class
   - Add find_openapi_spec() method
   - Add analyze_project() method
   - Write unit tests

2. **Step 2:** `jmeter_gen/core/openapi_parser.py` - Spec parsing
   - Implement OpenAPIParser class
   - Add parse() method
   - Add _parse_endpoints() helper
   - Add _get_base_url() helper
   - Write unit tests

3. **Step 3:** `jmeter_gen/core/jmx_generator.py` - JMX generation (most complex)
   - Implement JMXGenerator class
   - Add generate() method
   - Add _create_test_plan() helper
   - Add _create_thread_group() helper
   - Add _create_http_sampler() helper
   - Add _create_assertions() helper
   - Add _prettify_xml() helper
   - Write unit tests
   - Test with JMeter

4. **Step 4:** `jmeter_gen/core/jmx_validator.py` - Validation
   - Implement JMXValidator class
   - Add validate() method
   - Add structure checking helpers
   - Write unit tests

**Phase 2: CLI Interface**
5. **Step 5:** `jmeter_gen/cli.py` - CLI implementation
   - Set up Click framework
   - Implement analyze command
   - Implement generate command
   - Implement validate command
   - Implement mcp command
   - Add Rich formatting
   - Write CLI tests

**Phase 3: MCP Server**
6. **Step 6:** `jmeter_gen/mcp_server.py` - MCP Server
   - Set up MCP Server
   - Implement list_tools() handler
   - Implement call_tool() handler
   - Add analyze_project_for_jmeter tool
   - Add generate_jmx_from_openapi tool
   - Write MCP tests

**Phase 4: Testing & Integration**
7. **Step 7:** Unit tests completion
   - Ensure >80% coverage for all modules
   - Test error cases
   - Test edge cases

8. **Step 8:** Integration tests
   - End-to-end workflow tests
   - Test with Petstore API example
   - Test CLI integration
   - Test MCP integration

## Development Workflow

### Documentation Updates Required
**CRITICAL:** After completing each implementation step, you MUST update the documentation to reflect the current state:

1. **After each step completion:**
   - Update TODO.md - Mark completed tasks with [x]
   - Update implementation status in relevant docs
   - Document any design decisions or deviations from the plan
   - Update CLAUDE.md if new patterns or conventions emerge

2. **What to update:**
   - Mark checkboxes in TODO.md as tasks are completed
   - Update "Current Status" section in TODO.md
   - If implementation differs from specs, update CORE_MODULES.md
   - If new architectural decisions made, update ARCHITECTURE.md
   - Add any new commands or usage patterns to relevant docs

3. **When to update:**
   - Immediately after completing each step
   - Before moving to the next step
   - After discovering any issues that required design changes

**Never proceed to the next step without updating documentation first.** This ensures documentation stays synchronized with implementation and provides accurate guidance for future work.

## Code Standards

### Writing Style
- **No Emojis in Documentation**: Do not use emojis in any documentation files (.md, docstrings, comments). Technical documentation must be professional and emoji-free.
- **English Only**: All documentation, code comments, docstrings, commit messages, and technical writing must be in English. No Polish or other languages.
- Exception: Emojis in CLI output or user-facing messages are acceptable for better user experience.

### Type Hints Required
All public methods must have complete type hints. Use Python 3.9+ style (lowercase `dict`, `list`):
```python
from typing import Any, Optional

def parse_endpoints(paths: dict) -> list[dict]:
    """Parse endpoints from OpenAPI paths"""
    endpoints: list[dict] = []
    return endpoints
```

### Docstrings Required
Use Google-style docstrings for all public methods:
```python
def generate(
    self,
    spec_data: dict,
    output_path: str,
    base_url: Optional[str] = None,
    endpoints: Optional[list[str]] = None,
    threads: int = 1,
    rampup: int = 0,
    duration: Optional[int] = None,
) -> dict:
    """Generate JMeter JMX file from OpenAPI spec.

    Args:
        spec_data: Parsed OpenAPI specification
        output_path: Path where to save JMX file
        base_url: Override base URL (optional)
        endpoints: Filter specific endpoints (optional)
        threads: Number of threads (default: 1)
        rampup: Ramp-up period in seconds (default: 0)
        duration: Test duration in seconds (optional)

    Returns:
        Generation result with success status and metadata

    Raises:
        JMXGenerationException: If generation fails
    """
```

### Error Handling
- Raise specific exceptions, not generic `Exception`
- Use custom exception hierarchy (all inherit from `JMeterGenException`)
- Core modules raise exceptions; CLI/MCP layers catch and format them
- Provide context in error messages (which file, what failed, why)

### Testing Requirements
- Minimum 80% code coverage
- Every core module must have unit tests
- Test error cases and edge cases
- Use fixtures in `tests/conftest.py` for shared test data
- Mock dependencies in unit tests

## Important Constraints

### Dependencies
- Python 3.9+ required
- Minimize external dependencies
- Use standard library where possible (xml.etree.ElementTree, pathlib)
- Core dependencies: PyYAML, Click, Rich, MCP SDK

### OpenAPI Support
- MVP supports OpenAPI 3.0.x AND Swagger 2.0
- OpenAPI 3.0: Extract base URL from servers array (prefer localhost)
- Swagger 2.0: Construct base URL from host + basePath + schemes (prefer HTTPS)
- Request body detection:
  - OpenAPI 3.0: Check for `requestBody` field
  - Swagger 2.0: Check for parameters with `in: "body"` or `in: "formData"`

### JMX Generation
- **CRITICAL**: Use HTTP Request Defaults (ConfigTestElement) to centralize server configuration
- HTTP Request Defaults must be added to TestPlan level BEFORE ThreadGroups
- Individual HTTP Samplers should have EMPTY domain/port/protocol (inherited from defaults)
- Individual HTTP Samplers should ONLY specify path and method
- **User Interaction Required**: Before JMX generation, prompt user for base URL override
  - Prompt: "Enter base URL (press Enter for default: {spec_base_url}):"
  - If user provides URL, use it in HTTP Request Defaults
  - If user presses Enter (empty), use base_url from OpenAPI spec
- Use xml.etree.ElementTree (not lxml)
- Pretty-print XML with 2-space indentation
- POST requests default to 201 assertion
- Other requests default to 200 assertion
- Parse base_url to extract domain, port, protocol

### File Search
- Check common spec names first (COMMON_SPEC_NAMES array)
- Recursive search max 3 levels deep (MAX_SEARCH_DEPTH)
- Prefer openapi.yaml over swagger.json if multiple found

## Key Design Patterns

### Facade Pattern
CLI and MCP act as facades to core logic, simplifying complex interactions

### Builder Pattern
JMXGenerator builds complex XML structures step by step using helper methods like `_create_test_plan()`, `_create_thread_group()`, `_create_http_defaults()`, `_create_http_sampler()`

### Separation of Concerns
Clear boundaries: UI layer (CLI/MCP) → Core Logic → External Systems (file system, XML generation)

## Test Data Locations

### Primary Test Projects
Example projects in `examples/` directory:
- **Petstore API** (`examples/petstore/`): Swagger 2.0 example with 20 endpoints
- **Simple CRUD API** (`examples/simple-crud/`): OpenAPI 3.0.3 example with 7 endpoints
- Use these for integration testing and manual verification

### Test Fixtures
Test fixtures are defined as pytest fixtures in `tests/conftest.py`:
- `project_with_openapi_yaml` - Minimal OpenAPI 3.0 spec
- `project_with_swagger_json` - Swagger 2.0 spec
- `project_with_nested_spec` - Spec in subdirectory
- Various mock specs for error and edge case testing

## MCP Server Configuration

VS Code settings for GitHub Copilot integration:
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

After configuration changes, reload VS Code to apply.

## Project Scope

This is a small internal tool for a few users, NOT an enterprise application.
Do NOT add:
- Performance targets or benchmarks
- Enterprise features (logging frameworks, metrics, APM)
- Over-engineered error handling
- Unnecessary abstractions

Keep it simple and functional.

## Development Philosophy

### Spec-First Approach
This project follows a **spec-first** development methodology:

1. **Documentation before implementation** - Always create or update specifications and documentation before writing code. The docs/ folder contains the source of truth for how the system should behave.

2. **Implementation is replaceable** - The implementation (Python, libraries, frameworks) can always be changed. What matters is the specification. If we decide to rewrite in Go, Rust, or any other language, the specifications remain valid.

3. **Specs drive development** - When implementing a feature:
   - First: Write/update the specification in docs/
   - Then: Implement according to the spec
   - Finally: Update docs if implementation revealed spec issues

4. **Benefits**:
   - Clear requirements before coding
   - Easier onboarding (read specs, understand the system)
   - Language/framework agnostic design
   - Better long-term maintainability

## Common Data Structures

### Endpoint Structure (used throughout all modules)
```python
{
    "path": str,                    # "/api/users/{id}"
    "method": str,                  # "GET", "POST" (uppercase)
    "operationId": str,             # "getUser"
    "summary": str,                 # "Retrieve user by ID"
    "requestBody": bool,            # True if has request body
    "request_body_schema": dict,    # Schema for request body (if any)
    "parameters": list[dict]        # Path/query/header parameters
}
```

### Spec Data Structure (returned by OpenAPIParser)
```python
{
    "title": str,             # API title
    "version": str,           # API version
    "base_url": str,          # Selected base URL
    "endpoints": list[dict],  # List of endpoint structures
    "spec": dict              # Full spec for reference
}
```
Note: `spec_type` and `spec_version` are NOT returned by the parser. Use the raw spec to determine these if needed.

## v2.0.0 Scenario-Based Testing

Version 2 introduces scenario-based test generation using `pt_scenario.yaml` files. This enables sequential test flows with variable capture and correlation.

### v2 Documentation
All v2 specifications are in `docs/v2/`:
- **README.md**: Overview and quick start
- **VISION.md**: Product vision and goals
- **PT_SCENARIO_SPEC.md**: Complete pt_scenario.yaml specification
- **CORE_MODULES.md**: Module specifications including CorrelationAnalyzer
- **ARCHITECTURE.md**: v2 system architecture
- **IMPLEMENTATION_PLAN.md**: 10-step implementation plan
- **FEASIBILITY_ANALYSIS.md**: Technical feasibility assessment

### v2 Core Modules (new in v2.0.0)
1. **PtScenarioParser** (`ptscenario_parser.py`): Parse and validate pt_scenario.yaml
   - YAML schema validation
   - Endpoint format detection (operationId vs METHOD /path)
   - Variable reference validation

2. **CorrelationAnalyzer** (`correlation_analyzer.py`): Auto-detect JSONPath for captures
   - Analyze OpenAPI response schemas
   - Match capture names to response fields
   - Confidence-based matching algorithm

3. **ScenarioJMXGenerator** (`scenario_jmx_generator.py`): Generate JMX from scenarios
   - Sequential HTTP samplers (not parallel ThreadGroup)
   - JSONPostProcessor for variable extraction
   - Variable substitution in subsequent requests

4. **ScenarioVisualizer** (`scenario_visualizer.py`): Rich terminal visualization
   - Display scenario flow with step panels
   - Show variable captures and usage
   - Correlation confidence indicators

5. **ScenarioMermaid** (`scenario_mermaid.py`): Diagram generation
   - `generate_mermaid_diagram()` - Flowchart with variable flows
   - `generate_text_visualization()` - ASCII text visualization
   - Used by MCP `visualize_scenario` tool

### v2 Test Fixtures
Test fixtures for scenario parser in `tests/fixtures/scenarios/`:
- `valid_basic.yaml` - Minimal valid scenario
- `valid_full.yaml` - All features (captures, settings, variables)
- `valid_with_captures.yaml` - All 3 capture syntaxes
- `valid_operationid.yaml` - operationId format only
- `valid_method_path.yaml` - METHOD /path format only
- `valid_mixed_endpoints.yaml` - Both formats combined
- `invalid_*.yaml` - Various error cases for testing

### v2 Capture Syntax
Three capture syntaxes supported:
```yaml
capture:
  # Simple - auto-detect JSONPath from schema
  - userId

  # Mapped - different field name in response
  - localVar: "responseField"

  # Explicit JSONPath
  - itemId:
      path: "$.items[0].id"
      match: "first"  # or "all"
```

### v2 Endpoint Formats
Two endpoint formats supported (can be mixed):
```yaml
# operationId format
endpoint: "createUser"

# METHOD /path format
endpoint: "GET /users/{userId}"
```

### v1 Documentation
Legacy v1 documentation moved to `docs/v1/`.

## v3.0.0 Scenario Init Wizard

Version 3 introduces an interactive wizard for creating `pt_scenario.yaml` files.

### v3 Command
```bash
jmeter-gen new scenario [--spec PATH] [--output NAME]
```

### v3 Core Module
**ScenarioWizard** (`scenario_wizard.py`): Interactive CLI wizard
- Auto-detect OpenAPI spec in project
- Endpoint selection with "METHOD /path (operationId)" format
- Smart capture suggestions (id, token fields)
- Variable usage detection for endpoint suggestions
- Loop (count/while) and think time support
- Live preview after each step
- YAML output generation

### v3 Documentation
All v3 specifications in `docs/v3/`:
- **README.md**: Overview, features, user flow
- **CORE_MODULES.md**: ScenarioWizard class specification
- **IMPLEMENTATION_PLAN.md**: 12-step implementation plan

## Documentation References

All detailed specifications in `docs/v1/` (v1), `docs/v2/` (v2), and `docs/v3/` (v3):
- **IMPLEMENTATION_PLAN.md**: Timeline, phases, deliverables, success criteria
- **ARCHITECTURE.md**: System design, component architecture, data flow
- **CORE_MODULES.md**: Detailed specifications for all 4 core modules
- **DEVELOPMENT.md**: Environment setup, workflows, debugging, troubleshooting
- **JMX_FORMAT_REFERENCE.md**: Comprehensive JMX file format specification - **MUST USE for Step 3 (JMX Generator implementation)**

Always consult CORE_MODULES.md when implementing core logic for method signatures, algorithms, and expected behavior.

**CRITICAL for Step 3:** When implementing the JMX Generator, you MUST reference `docs/JMX_FORMAT_REFERENCE.md` for:
- Complete JMX XML structure and hierarchy
- All property types (stringProp, boolProp, intProp, elementProp, collectionProp)
- HTTPSampler configuration with all required properties
- ThreadGroup configuration details
- ResponseAssertion structure and test_type values
- HashTree organization patterns
- URL parsing for domain/port/protocol extraction
- Python implementation examples using xml.etree.ElementTree
- Common pitfalls to avoid
