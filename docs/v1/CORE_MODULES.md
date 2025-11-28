# Core Modules Specification

This document provides detailed specifications for all core modules in the JMeter Test Generator.

## Module Overview

All core modules are in `jmeter_gen/core/` and implement the business logic shared between CLI and MCP interfaces.

## 1. Project Analyzer

**File**: `jmeter_gen/core/project_analyzer.py`

**Purpose**: Scan project directory for OpenAPI/Swagger specifications

### Class: ProjectAnalyzer

```python
class ProjectAnalyzer:
    """Analyze project structure for JMeter test generation"""

    COMMON_SPEC_NAMES = [
        "openapi.yaml",
        "openapi.yml",
        "openapi.json",
        "swagger.yaml",
        "swagger.yml",
        "swagger.json",
        "api-spec.yaml",
        "api.yaml"
    ]

    MAX_SEARCH_DEPTH = 3
```

### Methods

#### find_openapi_spec(project_path: str) -> Optional[Dict]

Find OpenAPI specification file in project.

**Parameters**:
- `project_path`: Path to project root directory

**Returns**:
```python
{
    "spec_path": str,        # Absolute path to spec file
    "format": str,           # "yaml" or "json"
    "found": bool            # True if found
}
# or None if not found
```

**Algorithm**:
1. Check for common spec names in project root
2. If not found, recursively search subdirectories (max 3 levels)
3. Return first match (best priority)
4. If multiple matches, prefer openapi.yaml over swagger.json

**Example**:
```python
analyzer = ProjectAnalyzer()
result = analyzer.find_openapi_spec("/workspace/my-api")

# Result:
{
    "spec_path": "/workspace/my-api/openapi.yaml",
    "format": "yaml",
    "found": True
}
```

#### find_all_openapi_specs(project_path: str) -> List[Dict]

Find all OpenAPI specification files in project (v1.1.0+).

**Parameters**:
- `project_path`: Path to project root directory

**Returns**:
```python
[
    {
        "spec_path": str,        # Absolute path to spec file
        "format": str,           # "yaml" or "json"
        "found": bool,           # True
        "in_root": bool          # True if in project root
    },
    ...
]
# Sorted by priority: root > subdirs, openapi > swagger, yaml > json
```

**Example**:
```python
analyzer = ProjectAnalyzer()
result = analyzer.find_all_openapi_specs("/workspace/my-api")

# Result (multiple specs found):
[
    {"spec_path": "/workspace/my-api/openapi.yaml", "format": "yaml", "found": True, "in_root": True},
    {"spec_path": "/workspace/my-api/docs/swagger.json", "format": "json", "found": True, "in_root": False}
]
```

#### analyze_project(project_path: str) -> Dict

Complete project analysis with endpoint overview.

**Parameters**:
- `project_path`: Path to project root directory

**Returns**:
```python
{
    "openapi_spec_found": bool,
    "spec_path": str,                    # If found (best match)
    "spec_format": str,                  # If found
    "endpoints_count": int,              # If found
    "endpoints": List[Dict],             # If found
    "base_url": str,                     # If found
    "api_title": str,                    # If found
    "recommended_jmx_name": str,         # If found
    "available_specs": List[Dict],       # All found specs (v1.1.0+)
    "multiple_specs_found": bool,        # True if >1 spec (v1.1.0+)
    "message": str                       # If not found
}
```

**Algorithm**:
1. Call `find_all_openapi_specs()` to get all specs
2. If empty, return error message
3. Use first (best priority) spec for analysis
4. Parse spec using OpenAPIParser
5. Extract endpoint summary
6. Generate recommended JMX filename
7. Include all found specs in `available_specs`

**Example**:
```python
analyzer = ProjectAnalyzer()
result = analyzer.analyze_project("/workspace/my-api-project")

# Result:
{
    "openapi_spec_found": True,
    "spec_path": "/workspace/my-api-project/openapi.yaml",
    "spec_format": "yaml",
    "endpoints_count": 5,
    "endpoints": [
        {
            "path": "/api/v1/users",
            "method": "POST",
            "operationId": "createUser",
            "summary": "Create a new user"
        },
        # ... more endpoints
    ],
    "base_url": "http://localhost:3000",
    "api_title": "User Management API",
    "recommended_jmx_name": "user-management-api-test.jmx"
}
```

### Private Methods

#### _generate_jmx_name(api_title: str) -> str

Generate JMX filename from API title.

**Logic**:
- Convert to lowercase
- Replace spaces with hyphens
- Append "-test.jmx"

**Example**:
```python
_generate_jmx_name("My Sample API")
# Returns: "my-sample-api-test.jmx"
```

### Error Handling

**Exceptions**:
- `FileNotFoundError`: Project path doesn't exist
- `PermissionError`: No read access to directory

**Return Values**:
- Returns `None` or error dict instead of raising exceptions
- Caller handles error display

---

## 2. OpenAPI Parser

**File**: `jmeter_gen/core/openapi_parser.py`

**Purpose**: Parse OpenAPI 3.0.x and Swagger 2.0 specifications

### Class: OpenAPIParser

```python
class OpenAPIParser:
    """Parse OpenAPI 3.0.x and Swagger 2.0 specifications"""

    SUPPORTED_OPENAPI_VERSIONS = ["3.0.0", "3.0.1", "3.0.2", "3.0.3"]
    SUPPORTED_SWAGGER_VERSIONS = ["2.0"]
    SUPPORTED_METHODS = ["get", "post", "put", "delete", "patch"]
```

### Methods

#### parse(spec_path: str) -> Dict

Parse OpenAPI specification file.

**Parameters**:
- `spec_path`: Path to OpenAPI spec file (YAML or JSON)

**Returns**:
```python
{
    "title": str,                 # API title from info.title
    "version": str,               # API version from info.version
    "base_url": str,              # Base URL (from servers or host+basePath)
    "endpoints": List[Dict],      # Parsed endpoints
    "spec": Dict,                 # Full spec for reference
    "spec_type": str,             # "openapi" or "swagger"
    "spec_version": str           # "3.0.0" or "2.0"
}
```

**Algorithm**:
1. Detect format (YAML or JSON) from file extension
2. Load and parse file
3. Detect specification type (OpenAPI 3.0.x or Swagger 2.0)
4. Validate version against SUPPORTED_OPENAPI_VERSIONS or SUPPORTED_SWAGGER_VERSIONS
5. Extract info (title, version)
6. Parse base URL:
   - OpenAPI 3.0: Extract from servers array (prefer localhost)
   - Swagger 2.0: Construct from host + basePath + schemes (prefer HTTPS)
7. Parse paths and operations
8. Return structured data

**Example**:
```python
parser = OpenAPIParser()
result = parser.parse("/workspace/api/openapi.yaml")

# Result:
{
    "title": "Service CF Agent API",
    "version": "1.0.0",
    "base_url": "http://localhost:3300",
    "endpoints": [...],
    "spec": {...}
}
```

#### _parse_endpoints(paths: Dict) -> List[Dict]

Extract endpoints from OpenAPI paths.

**Parameters**:
- `paths`: OpenAPI paths object

**Returns**:
```python
[
    {
        "path": str,              # Path template (e.g., "/users/{id}")
        "method": str,            # HTTP method (uppercase)
        "operationId": str,       # Operation ID
        "summary": str,           # Operation summary
        "description": str,       # Operation description
        "requestBody": bool,      # Has request body?
        "parameters": List[Dict]  # Path/query/header parameters
    },
    # ... more endpoints
]
```

**Algorithm**:
1. Iterate through paths
2. For each path, iterate through HTTP methods
3. Extract operation details
4. Check for request body:
   - OpenAPI 3.0: Check for `requestBody` field
   - Swagger 2.0: Check for parameters with `in: "body"` or `in: "formData"`
5. Extract parameters
6. Return list of endpoints

**Example**:
```python
endpoints = parser._parse_endpoints({
    "/users": {
        "get": {
            "operationId": "listUsers",
            "summary": "List all users"
        },
        "post": {
            "operationId": "createUser",
            "summary": "Create a new user",
            "requestBody": {...}
        }
    }
})

# Result:
[
    {
        "path": "/users",
        "method": "GET",
        "operationId": "listUsers",
        "summary": "List all users",
        "requestBody": False,
        "parameters": []
    },
    {
        "path": "/users",
        "method": "POST",
        "operationId": "createUser",
        "summary": "Create a new user",
        "requestBody": True,
        "parameters": []
    }
]
```

#### _get_base_url(servers: List[Dict]) -> str

Extract base URL from servers, prefer localhost.

**Parameters**:
- `servers`: OpenAPI servers array

**Returns**:
- Base URL string

**Algorithm**:
1. If no servers, return "http://localhost:8080"
2. Check for server with "localhost" in URL
3. If found, return that URL
4. Otherwise, return first server URL

**Example**:
```python
servers = [
    {"url": "https://api.production.com"},
    {"url": "http://localhost:3300"},
    {"url": "https://api.staging.com"}
]

base_url = parser._get_base_url(servers)
# Returns: "http://localhost:3300" (localhost preferred)
```

#### _get_base_url_from_swagger(host, base_path, schemes) -> str

Construct base URL from Swagger 2.0 fields.

**Parameters**:
- `host`: Server hostname (e.g., "petstore.swagger.io")
- `base_path`: Path prefix (e.g., "/v2")
- `schemes`: List of protocols (e.g., ["https", "http"])

**Returns**:
- Base URL string

**Algorithm**:
1. Use defaults if parameters are None: host="localhost:8080", base_path="", schemes=["http"]
2. Select scheme: prefer "https" if available, otherwise use first in list
3. Remove leading slash from base_path if present
4. Construct URL: `{scheme}://{host}/{base_path}` or `{scheme}://{host}` if base_path is empty

**Example**:
```python
base_url = parser._get_base_url_from_swagger(
    host="petstore.swagger.io",
    base_path="/v2",
    schemes=["https", "http"]
)
# Returns: "https://petstore.swagger.io/v2" (HTTPS preferred)
```

### Error Handling

**Exceptions**:
- `FileNotFoundError`: Spec file doesn't exist
- `yaml.YAMLError`: Invalid YAML syntax
- `json.JSONDecodeError`: Invalid JSON syntax
- `InvalidSpecException`: Invalid spec structure or missing required fields
- `UnsupportedVersionException`: OpenAPI/Swagger version not supported

---

## 3. JMX Generator

**File**: `jmeter_gen/core/jmx_generator.py`

**Purpose**: Generate JMeter JMX test plans from OpenAPI data

**CRITICAL REFERENCE**: See `docs/JMX_FORMAT_REFERENCE.md` for complete JMX file format specification, XML structure, property types, and implementation examples. This document is MANDATORY for implementing this module correctly.

### Class: JMXGenerator

```python
class JMXGenerator:
    """Generate JMeter test plans from OpenAPI specifications"""

    DEFAULT_THREADS = 10
    DEFAULT_RAMPUP = 5
    DEFAULT_DURATION = 60
```

### Methods

#### generate(...) -> Dict

Generate JMeter JMX file.

**Parameters**:
```python
def generate(
    self,
    spec_data: Dict,              # Parsed OpenAPI data
    output_path: str,             # Where to save JMX
    base_url: str = None,         # Override base URL (if None, use from spec_data)
    endpoints: List[str] = None,  # Filter by operationId (None = all)
    threads: int = 10,            # Number of virtual users
    rampup: int = 5,              # Ramp-up period (seconds)
    duration: int = 60            # Test duration (seconds)
) -> Dict
```

**Returns**:
```python
{
    "success": bool,
    "jmx_path": str,
    "samplers_created": int,
    "assertions_added": int,
    "threads": int,
    "rampup": int,
    "duration": int,
    "summary": str
}
```

**Algorithm**:
1. Determine final base_url (use parameter if provided, else use spec_data["base_url"])
2. Parse base_url to extract domain, port, protocol
3. Filter endpoints if specific operationIds provided
4. Create Test Plan XML element
5. Create Thread Group with configuration
6. **Create HTTP Request Defaults (ConfigTestElement)** with domain/port/protocol
7. For each endpoint:
   - Create HTTP Request Sampler with ONLY path (domain/port/protocol inherited from defaults)
   - Set method, path, parameters
   - Add to thread group
   - Create Response Assertion
   - Add to sampler
8. Build complete XML tree (ensure HTTP Request Defaults is BEFORE all samplers)
9. Pretty-print XML
10. Write to output file
11. Return generation summary

**Example**:
```python
generator = JMXGenerator()
result = generator.generate(
    spec_data={
        "title": "My API",
        "base_url": "http://localhost:8080",
        "endpoints": [...]
    },
    output_path="test.jmx",
    threads=50,
    rampup=10,
    duration=300
)

# Result:
{
    "success": True,
    "jmx_path": "/workspace/test.jmx",
    "samplers_created": 5,
    "assertions_added": 5,
    "threads": 50,
    "rampup": 10,
    "duration": 300,
    "summary": "Created JMX with 5 HTTP samplers, 50 threads, 10s ramp-up, 300s duration"
}
```

### Private Methods

#### _create_test_plan(title: str, ...) -> ET.Element

Create Test Plan XML element.

**Returns**: `xml.etree.ElementTree.Element`

**Structure**:
```xml
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="{title}">
      <boolProp name="TestPlan.functional_mode">false</boolProp>
      <boolProp name="TestPlan.serialize_threadgroups">false</boolProp>
    </TestPlan>
  </hashTree>
</jmeterTestPlan>
```

#### _create_thread_group(threads, rampup, duration) -> ET.Element

Create Thread Group XML element.

**Returns**: `xml.etree.ElementTree.Element`

**Structure**:
```xml
<ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
  <stringProp name="ThreadGroup.num_threads">{threads}</stringProp>
  <stringProp name="ThreadGroup.ramp_time">{rampup}</stringProp>
  <stringProp name="ThreadGroup.duration">{duration}</stringProp>
  <boolProp name="ThreadGroup.scheduler">true</boolProp>
</ThreadGroup>
```

#### _create_http_defaults(domain: str, port: str, protocol: str) -> ET.Element

Create HTTP Request Defaults (ConfigTestElement).

**Parameters**:
- `domain`: Server hostname or IP (e.g., "localhost")
- `port`: Port number as string (e.g., "8080", "" for default)
- `protocol`: Protocol (e.g., "http", "https")

**Returns**: `xml.etree.ElementTree.Element`

**Structure**:
```xml
<ConfigTestElement guiclass="HttpDefaultsGui" testclass="ConfigTestElement" testname="HTTP Request Defaults" enabled="true">
  <elementProp name="HTTPsampler.Arguments" elementType="Arguments" guiclass="HTTPArgumentsPanel" testclass="Arguments" enabled="true">
    <collectionProp name="Arguments.arguments"/>
  </elementProp>
  <stringProp name="HTTPSampler.domain">{domain}</stringProp>
  <stringProp name="HTTPSampler.port">{port}</stringProp>
  <stringProp name="HTTPSampler.protocol">{protocol}</stringProp>
  <stringProp name="HTTPSampler.contentEncoding">UTF-8</stringProp>
  <stringProp name="HTTPSampler.path"></stringProp>
  <stringProp name="HTTPSampler.concurrentPool">6</stringProp>
</ConfigTestElement>
```

**Important**: This element must be added to ThreadGroup BEFORE any HTTP Samplers.

#### _create_http_sampler(endpoint: Dict) -> ET.Element

Create HTTP Request Sampler (inherits domain/port/protocol from HTTP Request Defaults).

**Parameters**:
- `endpoint`: Endpoint data (path, method, operationId)

**Returns**: `xml.etree.ElementTree.Element`

**Logic**:
1. Create HTTPSamplerProxy element
2. Set ONLY path and method (domain/port/protocol are EMPTY - inherited from defaults)
3. Leave domain, port, protocol as empty stringProp elements

**Structure**:
```xml
<HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="POST /api/endpoint">
  <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
    <collectionProp name="Arguments.arguments"/>
  </elementProp>
  <stringProp name="HTTPSampler.domain"></stringProp>
  <stringProp name="HTTPSampler.port"></stringProp>
  <stringProp name="HTTPSampler.protocol"></stringProp>
  <stringProp name="HTTPSampler.contentEncoding"></stringProp>
  <stringProp name="HTTPSampler.path">/api/endpoint</stringProp>
  <stringProp name="HTTPSampler.method">POST</stringProp>
  <boolProp name="HTTPSampler.follow_redirects">true</boolProp>
  <boolProp name="HTTPSampler.auto_redirects">false</boolProp>
  <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
  <boolProp name="HTTPSampler.DO_MULTIPART_POST">false</boolProp>
</HTTPSamplerProxy>
```

**Note**: Empty domain/port/protocol properties cause JMeter to inherit values from HTTP Request Defaults.

#### _create_assertions(endpoint: Dict) -> List[ET.Element]

Create Response Assertions for endpoint.

**Parameters**:
- `endpoint`: Endpoint data

**Returns**: List of assertion elements

**Logic**:
- POST requests: expect 201
- Other requests: expect 200

**Structure**:
```xml
<ResponseAssertion guiclass="AssertionGui" testclass="ResponseAssertion" testname="Assert 200">
  <stringProp name="Assertion.test_field">Assertion.response_code</stringProp>
  <stringProp name="Assertion.test_string">200</stringProp>
  <intProp name="Assertion.test_type">8</intProp>
</ResponseAssertion>
```

#### _prettify_xml(elem: ET.Element) -> str

Format XML with proper indentation.

**Parameters**:
- `elem`: Root XML element

**Returns**: Pretty-printed XML string

**Logic**:
1. Convert to string using `ET.tostring`
2. Parse with `minidom`
3. Pretty-print with 2-space indentation
4. Return formatted string

### Error Handling

**Exceptions**:
- `JMXGenerationException`: General generation error
- `IOError`: Cannot write output file

---

## 4. JMX Validator

**File**: `jmeter_gen/core/jmx_validator.py`

**Purpose**: Validate JMX file structure and provide recommendations

### Class: JMXValidator

```python
class JMXValidator:
    """Validate JMeter JMX test plans"""

    REQUIRED_ELEMENTS = [
        "jmeterTestPlan",
        "TestPlan",
        "ThreadGroup"
    ]
```

### Methods

#### validate(jmx_path: str) -> Dict

Validate JMX file.

**Parameters**:
- `jmx_path`: Path to JMX file

**Returns**:
```python
{
    "valid": bool,
    "issues": List[str],           # List of problems found
    "recommendations": List[str]   # List of improvement suggestions
}
```

**Algorithm**:
1. Load and parse XML file
2. Check structure (required elements)
3. Check configuration (thread group settings)
4. Check samplers (at least one exists)
5. Generate recommendations
6. Return validation results

**Example**:
```python
validator = JMXValidator()
result = validator.validate("/workspace/test.jmx")

# Result (valid file):
{
    "valid": True,
    "issues": [],
    "recommendations": [
        "Consider adding CSV Data Set Config for test data",
        "Add Response Time assertion for performance validation"
    ]
}

# Result (invalid file):
{
    "valid": False,
    "issues": [
        "Missing ThreadGroup element",
        "No HTTP samplers found"
    ],
    "recommendations": []
}
```

### Private Methods

#### _check_structure(root: ET.Element) -> List[str]

Check for required XML elements.

**Returns**: List of issues (empty if valid)

**Checks**:
- jmeterTestPlan element exists
- TestPlan element exists
- ThreadGroup element exists

#### _check_configuration(root: ET.Element) -> List[str]

Check ThreadGroup configuration.

**Returns**: List of issues (empty if valid)

**Checks**:
- num_threads is set and > 0
- ramp_time is set
- At least one of: loops, duration, scheduler

#### _check_samplers(root: ET.Element) -> List[str]

Check for samplers in test plan.

**Returns**: List of issues (empty if valid)

**Checks**:
- At least one HTTPSamplerProxy exists
- Samplers have domain and path set

#### _generate_recommendations(root: ET.Element) -> List[str]

Generate improvement suggestions.

**Returns**: List of recommendations

**Recommendations**:
- Add CSV Data Set Config (if missing)
- Add listeners (if missing)
- Add timers (if missing)
- Add response time assertions (if only status code assertions)

### Error Handling

**Exceptions**:
- `FileNotFoundError`: JMX file doesn't exist
- `xml.etree.ElementTree.ParseError`: Invalid XML
- `JMXValidationException`: Validation failed

---

## Common Data Structures

### Endpoint Data Structure

Used throughout all modules:

```python
{
    "path": str,              # "/api/users/{id}"
    "method": str,            # "GET", "POST", etc. (uppercase)
    "operationId": str,       # "getUser"
    "summary": str,           # "Retrieve user by ID"
    "description": str,       # Longer description
    "requestBody": bool,      # True if has request body
    "parameters": [
        {
            "name": str,      # "id"
            "in": str,        # "path", "query", "header"
            "required": bool,
            "schema": {...}
        }
    ]
}
```

### Spec Data Structure

Returned by OpenAPIParser:

```python
{
    "title": str,             # "My API"
    "version": str,           # "1.0.0"
    "base_url": str,          # "http://localhost:8080"
    "endpoints": [...],       # List of endpoint dicts
    "spec": {...}             # Full OpenAPI spec
}
```

---

## Testing Requirements

Each core module must have:

1. **Unit Tests**:
   - Test each public method
   - Test error cases
   - Test edge cases (empty input, invalid data)
   - Mock dependencies

2. **Integration Tests**:
   - Test with real OpenAPI specs
   - Test end-to-end flow
   - Verify generated files are valid

3. **Test Coverage**:
   - Minimum 80% code coverage
   - 100% coverage for critical paths

---

## Implementation Notes

### Python Version
- Minimum: Python 3.9
- Use type hints for all public methods
- Use dataclasses for complex data structures (future enhancement)

### Dependencies
- Minimize external dependencies
- Use standard library where possible
- Core modules should have NO dependencies on CLI or MCP

### Code Style
- Follow PEP 8
- Use descriptive variable names
- Add docstrings to all public methods
- Keep functions focused and small (<50 lines)

### Error Handling
- Raise specific exceptions, not generic Exception
- Provide error context (which file, what went wrong)
- Don't catch exceptions in core modules (let them bubble up)

---

## Future Enhancements

### v1.1
- Add CSV Data Set Config generation
- Add request body data generation with faker
- Support more assertion types

### v1.2
- Add authentication support (Bearer, Basic)
- Add correlation and extractors

### OpenAPI Change Detection Modules

#### Module 5: SpecComparator

**File**: `jmeter_gen/core/spec_comparator.py`

**Purpose**: Compare two OpenAPI/Swagger specifications and detect changes

**Key Methods**:
```python
def compare(old_spec: Dict, new_spec: Dict) -> SpecDiff
def _normalize_endpoint(endpoint: Dict) -> Dict
def _calculate_fingerprint(endpoint: Dict) -> str
def _match_endpoints(old_endpoints, new_endpoints) -> Tuple
def _detect_modifications(old_endpoint, new_endpoint) -> Optional[Dict]
```

**Data Structures** (in `jmeter_gen/core/data_structures.py`):
- `EndpointChange`: Represents a single endpoint change (added/removed/modified)
- `SpecDiff`: Structured difference between two specs with summary

#### Module 6: JMXUpdater

**File**: `jmeter_gen/core/jmx_updater.py`

**Purpose**: Update existing JMX files based on OpenAPI spec changes

**Key Methods**:
```python
def update_jmx(jmx_path: str, diff: SpecDiff, spec_data: Dict) -> UpdateResult
def parse_jmx(jmx_path: str) -> ET.ElementTree
def _add_new_sampler(thread_group, endpoint, spec_data) -> ET.Element
def _disable_sampler(sampler: ET.Element) -> None
```

**Features**:
- Parses existing JMX files
- Matches HTTP Samplers to endpoints
- Preserves user customizations (timers, custom assertions)
- Creates timestamped backups
- Rolls back on failure

#### Module 7: SnapshotManager

**File**: `jmeter_gen/core/snapshot_manager.py`

**Purpose**: Manage OpenAPI specification snapshots for change detection

**Key Methods**:
```python
def save_snapshot(spec_path: str, jmx_path: str, spec_data: Dict) -> str
def load_snapshot(jmx_path: str) -> Optional[Dict]
def calculate_spec_hash(spec_data: Dict) -> str
def filter_sensitive_data(spec_data: Dict) -> Dict
```

**Features**:
- Filters sensitive data (tokens, passwords, keys)
- Stores snapshots in `.jmeter-gen/snapshots/` (committed to git)
- Manages backups in `.jmeter-gen/backups/` (gitignored)
- Extracts git metadata (commit, branch, author)

#### Extended CLI Options

**analyze command**:
- `--no-detect-changes` - Disable change detection (enabled by default)
- `--show-details` - Show detailed change breakdown
- `--export-diff` - Export diff to JSON file

**generate command**:
- `--auto-update` - Update existing JMX if changes detected
- `--force-new` - Force regeneration (skip update)
- `--no-snapshot` - Don't save snapshot

---

## Conclusion

These core modules form the foundation of the JMeter Test Generator. They are:
- Independent and testable
- Reusable across interfaces (CLI, MCP)
- Well-documented and maintainable
- Designed for extension

Refer to this document during implementation to ensure consistency and completeness.
