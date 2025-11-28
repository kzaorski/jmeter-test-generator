# JMeter Test Generator v2

## What's New in v2

Version 2 introduces **scenario-based test generation** - define realistic user flows with automatic variable correlation.

### Key Features

- **pt_scenario.yaml**: Define sequential test steps in YAML
- **Variable Capture & Correlation**: Extract response values and use them in subsequent steps
- **Scenario Visualization**: See your test flow before generating JMX
- **User-Defined Payloads**: Full control over request data
- **Seamless Integration**: Existing commands extended, no new commands to learn
- **Short Path Mapping**: Use `/trigger` instead of `/api/v2/trigger` for convenience

---

## Quick Start

### 1. Create a Scenario File

Create `pt_scenario.yaml` in your project (same directory as your OpenAPI spec):

```yaml
version: "1.0"
name: "User Flow"

scenario:
  - name: "Create User"
    endpoint: "createUser"              # operationId format
    payload:
      email: "test@example.com"
      password: "secret123"
    capture:
      - userId
    assert:
      status: 201

  - name: "Get User"
    endpoint: "GET /users/{userId}"     # METHOD /path format (alternative)
    params:
      userId: "${userId}"
    assert:
      status: 200
```

Note: The OpenAPI spec is auto-detected (no need to specify it in the scenario file).

### 2. Analyze Project

```bash
jmeter-gen analyze
```

Output:
```
Project Analysis
================
OpenAPI spec: ./openapi.yaml (OpenAPI 3.0.3)
Scenario file: ./pt_scenario.yaml
  Name: User Flow
  Steps: 2
```

### 3. Generate JMX

```bash
jmeter-gen generate
```

When `pt_scenario.yaml` is present, the command automatically:
1. Parses the scenario file
2. Visualizes the flow in terminal
3. Validates endpoints against OpenAPI spec
4. Generates scenario-based JMX

Output:
```
Scenario: User Flow
===================

[1] Create User (POST /users)
    capture: userId
    assert: 201

[2] Get User (GET /users/{userId})
    uses: ${userId}
    assert: 200

Variable Flow:
  userId: [1] --> [2]

Generating JMX...
Generated: performance-test.jmx (2 samplers)
```

---

## File Relationships

```
project/
  openapi.yaml       # Required - API specification
  pt_scenario.yaml   # Optional - test scenario definition
```

- `openapi.yaml` (or swagger.json): **Required** - defines API endpoints
- `pt_scenario.yaml`: **Optional** - defines test scenarios using endpoints from spec

The scenario file REFERENCES the OpenAPI spec - it does not replace it.
When `pt_scenario.yaml` is present, `jmeter-gen generate` uses it for sequential test generation.
When absent, v1 behavior (endpoint catalog) is used.

---

## Endpoint Formats

The `endpoint` field supports two formats:

**operationId** (when defined in OpenAPI spec):
```yaml
endpoint: "createUser"
endpoint: "getUserById"
```

**METHOD /path** (when operationId is not available):
```yaml
endpoint: "POST /users"
endpoint: "GET /users/{userId}"
endpoint: "DELETE /api/v1/items/{id}"
```

---

## Backward Compatibility

All v1 commands continue to work exactly as before:

```bash
# These still work in v2
jmeter-gen analyze
jmeter-gen generate
jmeter-gen validate test.jmx
jmeter-gen mcp
```

**Key difference**: When `pt_scenario.yaml` is present in the project:
- `analyze` also reports the scenario file
- `generate` uses scenario-based flow instead of endpoint catalog

When no scenario file exists, v1 behavior is unchanged.

---

## Documentation

| Document | Description |
|----------|-------------|
| [VISION.md](VISION.md) | Product vision and goals |
| [PT_SCENARIO_SPEC.md](PT_SCENARIO_SPEC.md) | Full pt_scenario.yaml specification |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture |
| [CORE_MODULES.md](CORE_MODULES.md) | New module specifications |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Development roadmap |
| [FEASIBILITY_ANALYSIS.md](FEASIBILITY_ANALYSIS.md) | Technical feasibility assessment |

---

## MCP Server Tools

The MCP Server provides 5 tools for integration with GitHub Copilot and other MCP clients:

| Tool | Description |
|------|-------------|
| `analyze_project_for_jmeter` | Discover OpenAPI specs and scenario files in project |
| `generate_jmx_from_openapi` | Generate JMX from OpenAPI spec (v1 endpoint catalog) |
| `generate_scenario_jmx` | Generate JMX from pt_scenario.yaml with correlations |
| `validate_jmx` | Validate JMX file structure with recommendations |
| `visualize_scenario` | Visualize scenario with JSON, text, and Mermaid output |

---

## Roadmap

**v2.0.0** (current): Scenario parsing, visualization, JMX generation

**Completed P1 Extensions**:
- [x] Automatic correlations from OpenAPI response schemas
- [x] Mermaid diagram export (`scenario_mermaid.py`)
- [x] Full MCP integration (5 tools with scenario support)

**Planned Extensions** (prioritized, not version-assigned):
- P2: Scenario wizard, loops, conditionals, think time
- P3: Postman import, CSV data, auth helpers, Faker, GraphQL

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for full backlog with details.

---

## Migration from v1

No migration required. v2 is additive:

1. Keep using existing commands - they work exactly as before
2. Add `pt_scenario.yaml` when you need realistic user flows
3. Both approaches coexist - remove the scenario file to get v1 behavior

---

## Requirements

- Python 3.9+
- OpenAPI 3.0.x or Swagger 2.0 specification
- Rich library (included in dependencies)
