# pt_scenario.yaml Specification

## Overview

The `pt_scenario.yaml` file defines performance test scenarios with sequential steps, variable correlations, and assertions. This format enables creating realistic user flows instead of random endpoint calls.

---

## File Structure

```yaml
version: "1.0"              # Required: Specification version
name: "Scenario Name"       # Required: Display name
description: "..."          # Optional: Scenario description

settings:                   # Optional: Test settings
  threads: 10
  rampup: 5
  duration: 60
  base_url: "http://localhost:8080"

variables:                  # Optional: Global variables
  api_key: "test-key"
  default_password: "Test123!"

scenario:                   # Required: List of steps
  - name: "Step Name"
    endpoint: "operationId"       # operationId format
    # OR
    endpoint: "POST /users"       # METHOD /path format
    # ... step configuration
```

Note: The OpenAPI specification is auto-detected by `jmeter-gen generate` command (same as v1 behavior). The scenario file should be placed in the same directory as your OpenAPI spec.

---

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Specification version (currently "1.0") |
| `name` | string | Yes | Scenario display name |
| `description` | string | No | Scenario description |
| `settings` | object | No | Test execution settings |
| `variables` | object | No | Global variables (constants) |
| `scenario` | array | Yes | Ordered list of test steps |

---

## Settings Object

```yaml
settings:
  threads: 10                    # Number of concurrent threads
  rampup: 5                      # Ramp-up period in seconds
  duration: 60                   # Test duration in seconds (optional)
  base_url: "http://localhost"   # Override base URL from spec
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `threads` | integer | 1 | Number of concurrent virtual users |
| `rampup` | integer | 0 | Time to start all threads (seconds) |
| `duration` | integer | null | Test duration (seconds), null = single iteration |
| `base_url` | string | from spec | Override API base URL |

---

## Variables Object

Global variables available throughout the scenario. Use `${variable_name}` syntax to reference.

```yaml
variables:
  api_version: "v1"
  default_password: "SecurePass123!"
  admin_email: "admin@example.com"
```

---

## Scenario Step Structure

Each step in the `scenario` array has the following structure:

```yaml
- name: "Create User"           # Required: Step display name
  endpoint: "createUser"        # Required: operationId OR "METHOD /path"
  enabled: true                 # Optional: Enable/disable step (default: true)

  params:                       # Optional: Path and query parameters
    userId: "${userId}"

  headers:                      # Optional: Additional HTTP headers
    X-Custom-Header: "value"

  payload:                      # Optional: Request body (JSON)
    email: "test@example.com"
    password: "${default_password}"

  capture:                      # Optional: Variables to extract from response
    - userId
    - email

  assert:                       # Optional: Response assertions
    status: 201
    body:
      firstName: "Test"
```

### Step Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Step display name in JMeter |
| `endpoint` | string | Yes | operationId OR "METHOD /path" format (see below) |
| `enabled` | boolean | No | Enable/disable step (default: true) |
| `params` | object | No | Path and query parameters |
| `headers` | object | No | Additional HTTP headers |
| `payload` | object | No | Request body (JSON object) |
| `capture` | array | No | Variables to extract from response |
| `assert` | object | No | Response assertions |
| `condition` | object | No | Conditional execution (planned) |
| `loop` | object | No | Loop control (count, while) |

### Endpoint Format

The `endpoint` field supports two formats:

**1. operationId format** (recommended when available):
```yaml
endpoint: "createUser"
endpoint: "getUserById"
endpoint: "deleteUser"
```

**2. METHOD /path format** (when operationId is not defined):
```yaml
endpoint: "POST /users"
endpoint: "GET /users/{userId}"
endpoint: "DELETE /users/{userId}"
endpoint: "PUT /api/v1/products/{id}"
```

The parser automatically detects the format:
- If the value contains a space and starts with an HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS), it's treated as METHOD /path
- Otherwise, it's treated as operationId

### Endpoint Validation

All endpoints are validated against the OpenAPI specification:
- **operationId format**: Must match an existing operationId in spec
- **METHOD /path format**: Must match an existing path+method combination

If endpoint not found in spec: **ScenarioValidationException** is raised.
This is strict validation - unknown endpoints are NOT allowed.

### Short Path Mapping

For convenience, you can use shortened paths in scenarios. The tool will automatically
map them to full paths from the OpenAPI spec.

**Example**:
```yaml
# Instead of full path:
- endpoint: "POST /api/v2/users/trigger"

# You can write:
- endpoint: "POST /trigger"
```

**Matching Rules**:
1. **Exact match first**: If path exists exactly in spec, use it
2. **Suffix match**: Find paths that END with the short path
   - `/trigger` matches `/api/v2/trigger` but NOT `/trigger/history`
3. **Path parameters preserved**: `/users/{id}` matches `/api/v1/users/{id}`

**Multiple Matches**:
When multiple paths match (e.g., `/users` matches both `/api/v1/users` and `/api/v2/users`):
- **CLI**: Interactive prompt listing all candidates, user selects one
- **MCP**: Return error with candidates list, user must provide full path in next request

Example CLI prompt:
```
Multiple paths match '/users':
  [1] /api/v1/users
  [2] /api/v2/users
  [3] /admin/users
Select path [1-3]:
```

**Generated JMX**: Always contains the FULL resolved path from OpenAPI spec.

---

## Capture Syntax

The `capture` field defines variables to extract from the response. The tool **automatically detects** the JSONPath by analyzing the OpenAPI response schema.

### Auto-Detection Algorithm

When you write `capture: [userId]`, the tool:
1. Gets the response schema for the endpoint from OpenAPI spec
2. Builds an index of all field names to JSONPaths
3. Matches using priority order:
   - **Exact match**: `userId` matches field `userId`
   - **Case-insensitive**: `userid` matches field `userId`
   - **ID suffix**: `userId` matches field `id` or `user.id`
   - **Nested search**: `userId` matches `$.data.userId`, `$.user.id`

### Simple Capture

```yaml
capture:
  - userId      # Auto-detect: $.userId, $.id, $.data.user.id, etc.
  - email       # Auto-detect: $.email
```

### Mapped Capture (when names differ)

```yaml
capture:
  - userId: "id"              # Extract $.id, store as ${userId}
  - userName: "user.name"     # Extract $.user.name, store as ${userName}
```

### Explicit JSONPath (fallback)

```yaml
capture:
  - firstPetId:
      path: "$.pets[0].id"
  - allPetIds:
      path: "$.pets[*].id"
      match: "all"            # Extract all matches
```

### Capture in Loops

```yaml
capture:
  - userId: "userIds"         # In loop context, stores as userIds_1, userIds_2, etc.
```

---

## Assert Syntax

The `assert` field defines expected response characteristics.

### Status Code Assertion

```yaml
assert:
  status: 201                 # Expected HTTP status code
```

### Body Assertions

```yaml
assert:
  status: 200
  body:
    firstName: "Test"         # Assert exact field value
    email: "test@example.com"
```

### Header Assertions

```yaml
assert:
  status: 200
  headers:
    Content-Type: "application/json"
```

---

## Condition Syntax (planned)

Conditional step execution based on previous results.

### Simple Condition

```yaml
condition:
  if: "${response_status} == 200"
```

### With Else Action

```yaml
condition:
  if: "${userId} != null"
  else: "skip"                # skip, fail, or continue
```

### Multiple Conditions (AND)

```yaml
condition:
  if:
    - "${response_status} == 200"
    - "${userId} != null"
```

---

## Loop Syntax

Loop control allows repeating a step multiple times.

### Fixed Count Loop

```yaml
loop:
  count: 5                    # Repeat step 5 times
  interval: 1000              # Optional: delay between iterations (ms)
```

### While Loop (condition-based)

```yaml
loop:
  while: "$.status != 'finished'"   # JSONPath condition
  max_iterations: 100               # Safety limit (default: 100)
  interval: 5000                    # Optional: delay between iterations (ms)
```

The while loop continues until the condition evaluates to false or max_iterations is reached.
The condition uses JSONPath syntax to check values from the response.

### Foreach Loop (planned)

```yaml
loop:
  foreach: "petIds"           # Iterate over petIds_1, petIds_2, etc.
  variable: "currentPetId"    # ${currentPetId} = current value
```

Note: Foreach loops are not yet implemented.

---

## Variable Lifecycle

### Scope
- Variables defined in `variables:` are global (available in all steps)
- Variables from `capture:` are available in subsequent steps only
- Variable names are case-sensitive

### Capture Behavior
- Simple capture `[varName]` -> looks for `$.varName` in response
- Mapped capture `[varName: "fieldName"]` -> looks for `$.fieldName` in response
- If field not found: WARNING logged, variable set to placeholder `${varName_NOT_FOUND}`
- Variables can be overwritten by subsequent captures

### Error Handling
- Missing capture field: Warning + placeholder (test continues)
- Undefined variable in substitution: Warning + keep literal `${varName}`

---

## Variable Reference Syntax

Use `${variable_name}` to reference variables:

```yaml
params:
  userId: "${userId}"

payload:
  email: "user${i}@example.com"    # In loop context
  password: "${default_password}"

headers:
  Authorization: "Bearer ${token}"
```

---

## Complete Example

```yaml
version: "1.0"
name: "User CRUD Flow"
description: "Complete user lifecycle: create, read, update, delete"

settings:
  threads: 10
  rampup: 5
  duration: 60
  base_url: "http://localhost:8080"

variables:
  api_version: "v1"
  default_password: "TestPass123!"

scenario:
  # Using operationId format
  - name: "Create User"
    endpoint: "createUser"
    payload:
      email: "test.user@example.com"
      firstName: "Test"
      lastName: "User"
      password: "${default_password}"
    capture:
      - userId
      - email
    assert:
      status: 201

  # Using METHOD /path format (alternative)
  - name: "Get Created User"
    endpoint: "GET /users/{userId}"
    params:
      userId: "${userId}"
    assert:
      status: 200
      body:
        firstName: "Test"

  - name: "Update User"
    endpoint: "PUT /users/{userId}"
    params:
      userId: "${userId}"
    payload:
      firstName: "Updated"
      lastName: "Name"
    capture:
      - updatedAt
    assert:
      status: 200

  - name: "Delete User"
    endpoint: "DELETE /users/{userId}"
    params:
      userId: "${userId}"
    assert:
      status: 200

  - name: "Verify Deletion"
    endpoint: "GET /users/{userId}"
    params:
      userId: "${userId}"
    assert:
      status: 404
```

---

## Validation Rules

The parser validates the following:

1. **Required fields**: `version`, `name`, `scenario`
2. **Endpoint existence**: All `endpoint` values must match either:
   - An operationId in the OpenAPI spec, OR
   - A valid METHOD /path combination that exists in the spec
3. **Variable definitions**: Variables must be defined before use (in `variables` or `capture`)
4. **Type consistency**: `params` and `payload` types should match OpenAPI schema (warning only)

### Error Messages

| Error | Description |
|-------|-------------|
| `EndpointNotFound` | operationId or METHOD /path not found in OpenAPI spec |
| `UndefinedVariable` | Variable used before definition |
| `InvalidYAML` | YAML syntax error |
| `MissingRequiredField` | Required field not provided |
| `InvalidEndpointFormat` | Endpoint format is neither valid operationId nor METHOD /path |

---

## File Naming Convention

Recommended file names:
- `pt_scenario.yaml` - default name (auto-discovered)
- `{name}_scenario.yaml` - named scenarios
- `scenarios/*.yaml` - multiple scenarios in folder
