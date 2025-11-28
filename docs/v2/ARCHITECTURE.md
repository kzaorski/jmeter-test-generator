# v2 Architecture

## Overview

v2 extends the existing architecture with new modules for scenario-based test generation while maintaining full backward compatibility with v1.

---

## Module Diagram

```
                           CLI (cli.py)
                               |
          +--------------------+--------------------+
          |                                         |
     Commands (Extended)                       MCP Server
    (analyze, generate,                      (mcp_server.py)
     validate, mcp)                                |
          |                                        |
          v                                        v
    +--------------------------------------------------+
    |                   Core Modules                   |
    |                                                  |
    | v1 Modules:              v2 Modules:             |
    | - ProjectAnalyzer        - PtScenarioParser      |
    | - OpenAPIParser    <---> - CorrelationAnalyzer   |
    | - JMXGenerator           - ScenarioVisualizer    |
    | - JMXValidator           - ScenarioJMXGenerator  |
    | - SpecComparator                                 |
    | - SnapshotManager        P1 Planned:             |
    | - JMXUpdater             - Mermaid export        |
    |                          - MCP integration       |
    +--------------------------------------------------+
```

Note: v2 does NOT introduce new CLI commands. Instead, existing `analyze` and `generate` commands are extended to detect and use `pt_scenario.yaml` when present.

---

## New v2 Modules

### 1. PtScenarioParser (`jmeter_gen/core/ptscenario_parser.py`)

**Purpose**: Parse and validate pt_scenario.yaml files.

**Responsibilities**:
- Load YAML file
- Validate schema structure
- Parse steps into data structures
- Validate endpoint references against OpenAPI spec

**Dependencies**:
- PyYAML
- OpenAPIParser (for endpoint validation)

### 2. CorrelationAnalyzer (`jmeter_gen/core/correlation_analyzer.py`)

**Purpose**: Automatically detect variable correlations from OpenAPI response schemas.

**Responsibilities**:
- Extract response schemas from OpenAPI spec
- Build field index mapping field names to JSONPaths
- Match capture variables to schema fields using priority-based algorithm
- Generate CorrelationMapping objects with confidence scores
- Track variable usage across scenario steps

**Dependencies**:
- OpenAPIParser (for schema extraction)

### 3. ScenarioVisualizer (`jmeter_gen/core/scenario_visualizer.py`)

**Purpose**: Visualize scenario flow in terminal.

**Responsibilities**:
- Render Rich terminal visualization
- Show variable flow between steps
- (planned) Generate Mermaid flowchart syntax

**Dependencies**:
- Rich library
- PtScenarioParser

### 4. ScenarioJMXGenerator (`jmeter_gen/core/scenario_jmx_generator.py`)

**Purpose**: Generate JMX from parsed scenario with correlations.

**Responsibilities**:
- Create sequential HTTP samplers
- Add JSONPostProcessor extractors
- Apply variable substitutions
- Generate assertions

**Dependencies**:
- JMXGenerator (base functionality)
- CorrelationAnalyzer

---

## Data Flow

### Extended `generate` Command

```
jmeter-gen generate
       |
       v
ProjectAnalyzer.analyze_project()
       |
       +---> Find OpenAPI spec (existing v1 behavior)
       +---> Find pt_scenario.yaml (NEW)
       |
       v
[pt_scenario.yaml found?]
       |
       +-- NO --> v1 flow: JMXGenerator.generate()
       |
       +-- YES --> v2 flow:
                    |
                    v
             PtScenarioParser.parse()
                    |
                    +---> OpenAPIParser (validate endpoints)
                    |
                    v
             CorrelationAnalyzer.analyze()
                    |
                    +---> OpenAPIParser.extract_response_schema()
                    +---> Build field index, match captures
                    +---> Generate CorrelationResult
                    |
                    v
             ScenarioVisualizer.visualize()
                    |
                    +---> Rich terminal output
                    +---> Show correlation info
                    |
                    v
             ScenarioJMXGenerator.generate()
                    |
                    +---> HTTP samplers
                    +---> JSONPostProcessor extractors
                    +---> Response assertions
                    |
                    v
             output.jmx (with auto-correlations)
```

### Extended `analyze` Command

```
jmeter-gen analyze
       |
       v
ProjectAnalyzer.analyze_project()
       |
       +---> Find OpenAPI spec (existing v1 behavior)
       +---> Find pt_scenario.yaml (NEW)
       |
       v
Report findings:
  - OpenAPI spec location
  - pt_scenario.yaml location (if found)
  - Scenario summary (name, steps count)
```

---

## Data Structures

### ParsedScenario

```python
@dataclass
class ParsedScenario:
    version: str
    name: str
    description: Optional[str]
    settings: ScenarioSettings
    variables: dict[str, Any]
    steps: list[ScenarioStep]
```

### ScenarioStep

```python
@dataclass
class ScenarioStep:
    name: str
    endpoint: str  # operationId OR "METHOD /path"
    endpoint_type: str  # "operation_id" or "method_path"
    method: Optional[str]  # Parsed method (for method_path type)
    path: Optional[str]  # Parsed path (for method_path type)
    enabled: bool
    params: dict[str, Any]
    headers: dict[str, str]
    payload: Optional[dict[str, Any]]
    captures: list[CaptureConfig]
    assertions: Optional[AssertConfig]
```

### CorrelationMapping

```python
@dataclass
class CorrelationMapping:
    variable_name: str          # Variable name to store
    jsonpath: str               # JSONPath expression
    source_step: int            # Step index where captured (1-based)
    source_endpoint: str        # Endpoint identifier
    target_steps: list[int]     # Steps using this variable
    confidence: float           # Match confidence 0.0-1.0
    match_type: str             # "explicit", "exact", "suffix", "nested"
```

---

## Extension Points

### Adding New Capture Sources

The CorrelationAnalyzer is designed to be extensible:

```python
class CorrelationAnalyzer:
    def register_source(self, source: CaptureSource):
        """Register additional capture sources (headers, cookies, etc.)"""
```

### Custom Visualizers

ScenarioVisualizer supports pluggable renderers:

```python
class ScenarioVisualizer:
    def add_renderer(self, renderer: Renderer):
        """Add custom output format (SVG, PlantUML, etc.)"""
```

---

## Integration with v1

v2 modules reuse v1 components where possible:

| v1 Component | v2 Usage |
|--------------|----------|
| OpenAPIParser | Endpoint validation, response schema extraction |
| JMXGenerator | Base sampler creation, XML utilities |
| JMXValidator | Optional output validation |

This ensures consistency and reduces code duplication.

---

## CLI Command Structure

v2 extends existing commands rather than adding new ones:

```
jmeter-gen
  |
  +-- analyze          # Extended: also detects pt_scenario.yaml
  |     |
  |     +-- Reports OpenAPI spec location
  |     +-- Reports pt_scenario.yaml if found (NEW)
  |
  +-- generate         # Extended: uses pt_scenario.yaml if present
  |     |
  |     +-- [no pt_scenario.yaml] -> v1 behavior (endpoint catalog)
  |     +-- [pt_scenario.yaml found] -> v2 behavior:
  |           +-- Parse scenario
  |           +-- Visualize flow (Rich output)
  |           +-- Generate scenario-based JMX
  |
  +-- validate         # Unchanged (validates JMX structure)
  |
  +-- mcp              # Unchanged (MCP Server)
```

### Planned Commands

```
jmeter-gen
  |
  +-- scenario init    # Interactive wizard to create pt_scenario.yaml (planned)
```

---

## Error Handling

v2 introduces new exception types:

```python
class PtScenarioException(JMeterGenException):
    """Base for scenario errors"""

class ScenarioParseException(PtScenarioException):
    """YAML parsing failed"""

class EndpointNotFoundException(PtScenarioException):
    """operationId or METHOD /path not in OpenAPI spec"""

class InvalidEndpointFormatException(PtScenarioException):
    """Endpoint format is neither valid operationId nor METHOD /path"""

class UndefinedVariableException(PtScenarioException):
    """Variable used before definition"""

class CorrelationException(PtScenarioException):
    """Correlation analysis failed"""

class SchemaNotFoundException(CorrelationException):
    """Response schema not found for endpoint"""

class FieldNotFoundException(CorrelationException):
    """Capture field not found in schema"""
```
