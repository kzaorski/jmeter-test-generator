# Feasibility Analysis: pt_scenario.yaml

## Scope Clarification

This analysis covers the full v2.0.0 scope including **automatic correlation detection**.
All features described in this document are included in v2.0.0 release.

---

## Executive Summary

**Concept**: A `pt_scenario.yaml` file that defines sequential test scenarios with automatic variable correlation.

**Feasibility Assessment**: **YES, fully feasible** - existing architecture supports this feature.

---

## 1. Problem Statement

### Current State
- JMX generated from OpenAPI = "endpoint catalog"
- No sequence (e.g., login -> operations)
- No correlation (token from response -> Authorization header)
- No realistic payloads

### Solution
- YAML defining step order and payloads
- Tool automatically detects correlations from OpenAPI response schemas
- Generates JMX with JSONPostProcessor extractors and `${...}` variables

---

## 2. Key Technical Challenges

### 2.1 Automatic Correlation Detection (MOST CHALLENGING)

**Problem**: User writes `capture: userId`, tool must find the JSONPath automatically.

**Solution**: Analyze response schemas from OpenAPI spec.

```yaml
# User writes:
capture:
  - userId

# Tool analyzes OpenAPI response schema for this endpoint:
# responses.200.content.application/json.schema.properties
# Finds: { "id": { "type": "integer" } }
# Generates: JSONPath = "$.id" (matching userId -> id)
```

**Matching Algorithm**:
1. Exact match: `userId` == `userId`
2. ID suffix: `userId` -> search for `id`
3. Case insensitive: `userid` -> `userId`
4. Nested search: `userId` -> `$.user.id`, `$.data.userId`

**Confidence scoring**: When multiple matches found, choose best or warn.

**Assessment**: Feasible. OpenAPIParser already parses spec, just need to add response schema extraction.

### 2.2 JMX Elements to Generate

| JMX Element | Purpose | Complexity |
|-------------|---------|------------|
| JSONPostProcessor | Response extraction | Low |
| IfController | Conditions | Medium |
| LoopController | Count loops | Low |
| ForeachController | Array iteration | Medium |
| JSONPathAssertion | Body assertions | Low |

**Assessment**: Feasible. JMXGenerator already uses xml.etree.ElementTree, adding new elements is an extension of existing code.

### 2.3 pt_scenario.yaml Validation

**Problem**: Verify that:
- Endpoint references (operationId) exist in OpenAPI
- Variables `${...}` are defined before use
- Payloads match request body schema

**Assessment**: Feasible - standard YAML validation + business logic.

---

## 3. Solution Architecture

### New Modules

```
jmeter_gen/core/
  ptscenario_parser.py      # Parse pt_scenario.yaml
  correlation_analyzer.py    # Automatic correlation detection
  scenario_jmx_generator.py  # Generate JMX from scenario
  scenario_visualizer.py     # Visualize scenario flow
```

### Extensions to Existing Modules

```python
# openapi_parser.py - new method:
def extract_response_schema(operation_id: str) -> dict:
    """Get response schema for endpoint."""

# jmx_generator.py - new methods:
def _create_json_post_processor(...) -> ET.Element
def _create_if_controller(...) -> ET.Element
def _create_loop_controller(...) -> ET.Element
```

### Data Flow

```
pt_scenario.yaml
       |
       v
PtScenarioParser.parse()
       |
       v
CorrelationAnalyzer.analyze()  <-- OpenAPI response schemas
       |
       v
ScenarioVisualizer.visualize()
       |
       v
ScenarioJMXGenerator.generate()
       |
       v
output.jmx (with correlations)
```

---

## 4. Example pt_scenario.yaml

```yaml
name: "User CRUD Flow"
spec: "./openapi.yaml"

settings:
  threads: 10
  rampup: 5
  base_url: "http://localhost:8080"

variables:
  default_password: "Test123!"

scenario:
  - name: "Create User"
    endpoint: "createUser"        # operationId from OpenAPI
    payload:
      email: "test@example.com"
      password: "${default_password}"
    capture:
      - userId                    # Tool: $.id -> ${userId}
    assert:
      status: 201

  - name: "Get User"
    endpoint: "getUser"
    params:
      userId: "${userId}"         # Variable usage
    assert:
      status: 200

  - name: "Delete User"
    endpoint: "deleteUser"
    params:
      userId: "${userId}"
    assert:
      status: 200
```

---

## 5. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Ambiguous correlation matching | Medium | Medium | Warning + placeholder in JMX |
| Complex nested response schemas | Low | Low | Recursive search with depth limit |
| Different OpenAPI formats (2.0 vs 3.0) | Medium | Medium | Already supported in parser |
| Payload vs schema validation | Low | Low | Optional validation |

---

## 6. First Feature: Scenario Visualization

After parsing pt_scenario.yaml, display a graphical representation showing:
- Step sequence (flow)
- Data flow between steps (especially correlations)
- Variable capture and usage

### Implementation
1. **Rich library** - colored boxes and lines in terminal (default)
2. **Mermaid export** - `--export-diagram` flag generates .md with flowchart

### CLI Command
```bash
jmeter-gen scenario visualize pt_scenario.yaml
jmeter-gen scenario visualize pt_scenario.yaml --export-diagram flow.md
```

---

## 7. Conclusion

**YES, worth implementing.** This feature solves a real problem - current JMX files are "dead" without sequences and correlations. Automatic correlation detection is a differentiating feature compared to competitors.

### v2.0.0 Scope (Implemented)
- Scenario parsing and validation
- Automatic correlation detection from OpenAPI schemas
- Rich terminal visualization
- JMX generation with JSONPostProcessor extractors

### Prioritized Extensions (Future)
- P1: Mermaid export, MCP integration
- P2: Loops, conditionals, think time, scenario wizard
- P3: Postman/Insomnia import, CSV data, auth helpers
