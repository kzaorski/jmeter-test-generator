# v2 Implementation Plan

## Overview

This document outlines the implementation phases for JMeter Test Generator v2.

**Key Design Decision**: v2 extends existing CLI commands (`analyze`, `generate`) rather than adding new `scenario` subcommands. This maintains backward compatibility while adding scenario-based functionality.

---

## Phase 1: v2.0.0 - Scenario-Based Test Generation (Current)

### Objectives
- Parse pt_scenario.yaml files
- Validate against OpenAPI spec
- **Automatic correlation detection from OpenAPI response schemas**
- Visualize scenario flow in terminal (Rich)
- Generate scenario-based JMX files with JSONPostProcessor extractors
- Extend existing CLI commands (no new commands)

### Implementation Steps

#### Step 1: Data Structures and Exceptions
- Create dataclasses in `jmeter_gen/core/scenario_data.py`:
  - ScenarioSettings, CaptureConfig, AssertConfig
  - ScenarioStep (with endpoint_type, method, path fields)
  - ParsedScenario
  - CorrelationMapping, CorrelationResult
- Add new exceptions to `jmeter_gen/exceptions.py`:
  - PtScenarioException (base)
  - ScenarioParseException
  - ScenarioValidationException
  - EndpointNotFoundException
  - InvalidEndpointFormatException
  - UndefinedVariableException
  - CorrelationException, SchemaNotFoundException, FieldNotFoundException

#### Step 2: PtScenarioParser
- Implement YAML loading and schema validation
- Parse all scenario fields into dataclasses
- Implement endpoint format detection:
  - operationId format: `"createUser"`
  - METHOD /path format: `"POST /users"`
- Basic validation (required fields, types)
- Variable usage tracking

#### Step 3: OpenAPI Parser Extensions
- Add `get_endpoint_by_operation_id()` method
- Add `get_endpoint_by_method_path()` method
- Add `get_all_operation_ids()` method
- Add `get_all_paths()` method
- Add `extract_response_schema()` method for correlation detection
- Add `resolve_short_path()` for abbreviated path support

#### Step 4: CorrelationAnalyzer
- Implement `analyze()` method for full scenario analysis
- Implement `analyze_step()` for single step processing
- Build field index from response schemas (`_build_field_index()`)
- Implement matching algorithm with priority levels:
  - Explicit JSONPath (user-provided)
  - Source field mapping
  - Exact match, case-insensitive, ID suffix, nested search
- Calculate confidence scores for matches
- Track variable usage across steps (`_find_variable_usage()`)

#### Step 5: ProjectAnalyzer Extensions
- Add `find_scenario_file()` method
- Search for pt_scenario.yaml, pt_scenario.yml
- Update `analyze_project()` return value to include scenario_path

#### Step 6: ScenarioVisualizer
- Implement Rich terminal visualization
- Create step panels with endpoint info (method, path)
- Show variable capture and usage (with resolved JSONPaths)
- Display variable flow table
- Show correlation confidence indicators
- Show validation status and warnings

#### Step 7: ScenarioJMXGenerator
- Generate sequential HTTP samplers from scenario steps
- Resolve endpoints (operationId or METHOD /path)
- Apply variable substitutions in params, headers, payload
- **Generate JSONPostProcessor elements for captures**
- Generate response assertions (status code, body fields)
- Generate JSONPathAssertion for body field assertions
- Use HTTP Request Defaults for base URL

#### Step 8: CLI Integration - Extend `analyze`
- Detect pt_scenario.yaml in project
- Report scenario file location if found
- Display scenario summary (name, steps count)

#### Step 9: CLI Integration - Extend `generate`
- Check for pt_scenario.yaml presence
- If NOT found: existing v1 behavior (endpoint catalog)
- If found:
  - Parse scenario
  - Run correlation analysis
  - Visualize flow with correlation info (Rich output)
  - Validate endpoints against OpenAPI
  - Generate scenario-based JMX with extractors

#### Step 10: Testing
- Unit tests for PtScenarioParser
- Unit tests for CorrelationAnalyzer
- Unit tests for ScenarioVisualizer
- Unit tests for ScenarioJMXGenerator
- Unit tests for OpenAPIParser extensions
- Unit tests for ProjectAnalyzer extensions
- Integration tests with example scenarios
- CLI tests for extended commands

### Acceptance Criteria
- [ ] Parse valid pt_scenario.yaml files (both endpoint formats)
- [ ] Detect invalid YAML syntax and report clear errors
- [ ] Validate endpoint references against OpenAPI spec
- [ ] **Auto-detect JSONPath from OpenAPI response schemas**
- [ ] **Generate JSONPostProcessor elements for variable extraction**
- [ ] Display Rich visualization in terminal during generate
- [ ] Generate valid JMX files that run in JMeter
- [ ] `analyze` reports pt_scenario.yaml if found
- [ ] `generate` uses scenario-based flow when pt_scenario.yaml exists
- [ ] Full backward compatibility (v1 behavior when no scenario file)
- [ ] >80% test coverage for new modules

---

## Error Handling Strategy

### Validation Errors (before generation)
- **ScenarioParseException**: Invalid YAML syntax -> show line number, exit 1
- **ScenarioValidationException**: Invalid scenario structure -> show field path, exit 1
- **EndpointNotFoundException**: Endpoint not in spec -> show endpoint, list available, exit 1
- **AmbiguousPathException**: Multiple paths match short path -> prompt user to select (CLI) or use highest version (MCP)

### Runtime Warnings (during generation)
- **Capture field not found**: Warning message, use placeholder `${var_NOT_FOUND}`
- **Undefined variable**: Warning message, keep literal `${varName}`

### CLI Output Format
- Errors: Red text with [ERROR] prefix
- Warnings: Yellow text with [WARNING] prefix
- Warnings do not cause non-zero exit code

---

## Extensions Backlog

See [../BACKLOG.md](../BACKLOG.md) for the consolidated prioritized backlog.

---

## Dependencies

```
v2.0.0 (Current)
    |
    +-- PtScenarioParser
    +-- CorrelationAnalyzer (auto-detect JSONPath)
    +-- ScenarioVisualizer (Rich only)
    +-- ScenarioJMXGenerator (with JSONPostProcessor)
    +-- OpenAPIParser extensions (including extract_response_schema)
    +-- ProjectAnalyzer extensions
    +-- CLI extensions (analyze, generate)
    |
    v
P1 Extensions
    |
    +-- Mermaid export (requires: ScenarioVisualizer)
    +-- MCP integration (requires: all core modules)
    |
    v
P2 Extensions
    |
    +-- Scenario Wizard (standalone)
    +-- Loop/Condition support (requires: Parser, JMXGenerator)
    +-- Think time (requires: JMXGenerator)
    |
    v
P3 Extensions
    |
    +-- Data generation (requires: Parser)
    +-- Advanced features
```

---

## Test Strategy

### Unit Tests
- Each new module has dedicated test file
- Mock dependencies (OpenAPIParser, file system)
- Test error cases and edge cases
- Test both endpoint formats (operationId, METHOD /path)

### Integration Tests
- End-to-end scenario parsing and visualization
- JMX generation with real OpenAPI specs
- Use example projects (petstore, simple-crud)
- Test CLI command extensions

### Test Files
```
tests/core/
  test_ptscenario_parser.py
  test_correlation_analyzer.py
  test_scenario_visualizer.py
  test_scenario_jmx_generator.py
  test_openapi_parser_v2.py       # New methods tests
  test_project_analyzer_v2.py     # New methods tests
tests/
  test_cli_v2.py                  # Extended commands tests
tests/fixtures/scenarios/
  valid_basic.yaml
  valid_full.yaml
  valid_with_captures.yaml
  invalid_*.yaml
```

---

## Branch Strategy

All v2 development happens on `v2` branch:

```bash
# Start work
git checkout v2

# Create feature branch
git checkout -b v2/feature-name

# Merge back to v2
git checkout v2
git merge v2/feature-name

# Never merge v2 to master until release
```

Release process:
1. Complete extension implementation on v2 branch
2. Update version in pyproject.toml
3. Update CHANGELOG
4. Merge v2 to master
5. Tag release

---

## Example Scenario for Testing

```yaml
name: "Test Scenario"

settings:
  threads: 5
  rampup: 2

variables:
  test_email: "test@example.com"

scenario:
  # Using operationId format
  - name: "Create User"
    endpoint: "createUser"
    payload:
      email: "${test_email}"
      firstName: "Test"
      lastName: "User"
      password: "secret123"
    capture:
      - userId
    assert:
      status: 201

  # Using METHOD /path format
  - name: "Get User"
    endpoint: "GET /users/{userId}"
    params:
      userId: "${userId}"
    assert:
      status: 200

  - name: "Update User"
    endpoint: "PUT /users/{userId}"
    params:
      userId: "${userId}"
    payload:
      firstName: "Updated"
    assert:
      status: 200

  - name: "Delete User"
    endpoint: "DELETE /users/{userId}"
    params:
      userId: "${userId}"
    assert:
      status: 200
```
