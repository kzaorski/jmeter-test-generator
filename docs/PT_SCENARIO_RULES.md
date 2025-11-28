# pt_scenario.yaml - Complete Guide

A standalone guide for creating valid `pt_scenario.yaml` test scenario files.

**File location**: Place `pt_scenario.yaml` in the same directory as your OpenAPI spec.
**Command**: Run `jmeter-gen generate` to generate JMX from the scenario.

---

## Quick Start

### Minimal Example

```yaml
version: "1.0"
name: "My API Test"

scenario:
  - name: "Create item"
    endpoint: "POST /items"
    payload:
      name: "Test Item"
    capture:
      - itemId: "id"
    assert:
      status: 201

  - name: "Get item"
    endpoint: "GET /items/${itemId}"
    assert:
      status: 200
```

### CRUD Flow Template

```yaml
version: "1.0"
name: "CRUD Flow"

variables:
  test_email: "test@example.com"

scenario:
  - name: "Create"
    endpoint: "POST /users"
    payload:
      email: "${test_email}"
      name: "Test User"
    capture:
      - userId: "id"
    assert:
      status: 201

  - name: "Read"
    endpoint: "GET /users/${userId}"
    assert:
      status: 200

  - name: "Update"
    endpoint: "PUT /users/${userId}"
    payload:
      name: "Updated User"
    assert:
      status: 200

  - name: "Delete"
    endpoint: "DELETE /users/${userId}"
    assert:
      status: 204
```

### Login + API Call Template

```yaml
version: "1.0"
name: "Authenticated Flow"

scenario:
  - name: "Login"
    endpoint: "POST /auth/login"
    payload:
      username: "testuser"
      password: "secret123"
    capture:
      - token: "accessToken"
    assert:
      status: 200

  - name: "Get profile"
    endpoint: "GET /users/me"
    headers:
      Authorization: "Bearer ${token}"
    assert:
      status: 200
```

### Async Job Polling Template (While Loop)

```yaml
version: "1.0"
name: "Async Job Flow"

scenario:
  - name: "Trigger job"
    endpoint: "POST /trigger"
    payload:
      action: "process-data"
    capture:
      - jobId: "id"
    assert:
      status: 202

  - name: "Poll status until completed"
    endpoint: "GET /status/${jobId}"
    loop:
      while: "${jobStatus} != 'completed'"
      max: 30                    # Max 30 attempts
      interval: 30000            # Wait 30 seconds between polls
    capture:
      - jobStatus: "status"
    assert:
      status: 200

  - name: "Get result"
    endpoint: "GET /result/${jobId}"
    assert:
      status: 200
      body:
        status: "completed"
```

---

## Quick Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `version` | string | Yes | - | Spec version, use `"1.0"` |
| `name` | string | Yes | - | Scenario display name |
| `description` | string | No | - | Scenario description |
| `settings` | object | No | - | Thread/timing config |
| `variables` | object | No | - | Global variables |
| `scenario` | array | Yes | - | List of test steps |

### Step Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Step name in JMeter |
| `endpoint` | string | Yes | - | operationId or `"METHOD /path"` |
| `enabled` | boolean | No | true | Enable/disable step |
| `params` | object | No | - | Path and query parameters |
| `headers` | object | No | - | HTTP headers |
| `payload` | object | No | - | Request body (JSON) |
| `capture` | array | No | - | Variables to extract |
| `assert` | object | No | - | Response assertions |
| `loop` | object | No | - | Loop control (planned) |

### Settings Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `threads` | integer | 1 | Concurrent virtual users |
| `rampup` | integer | 0 | Ramp-up time (seconds) |
| `duration` | integer | null | Test duration (seconds) |
| `base_url` | string | from spec | Override API base URL |

---

## Endpoint Formats

Two formats supported - use whichever matches your OpenAPI spec:

### 1. operationId (preferred)

```yaml
endpoint: "createUser"
endpoint: "getUserById"
endpoint: "deleteUser"
```

**How to find operationId in OpenAPI spec:**
```yaml
# In your openapi.yaml:
paths:
  /users:
    post:
      operationId: createUser    # <-- Use this value
      summary: "Create a new user"
```

### 2. METHOD /path (when operationId unavailable)

```yaml
endpoint: "POST /users"
endpoint: "GET /users/{userId}"
endpoint: "DELETE /api/v1/items/{id}"
```

**Method must be uppercase**: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS

### Short Path Mapping

For convenience, you can use shortened paths:

```yaml
# Instead of:
endpoint: "POST /api/v2/users/trigger"

# You can write:
endpoint: "POST /trigger"
```

The tool automatically maps to the full path from your OpenAPI spec.

---

## Variable Capture

Extract values from API responses for use in subsequent steps.

### Simple Capture (auto-detect JSONPath)

```yaml
capture:
  - userId      # Auto-detects $.userId, $.id, $.data.userId, etc.
  - email       # Auto-detects $.email
```

### Mapped Capture (different field name)

```yaml
capture:
  - userId: "id"              # Extract $.id, store as ${userId}
  - userName: "user.name"     # Extract $.user.name, store as ${userName}
```

### Explicit JSONPath (full control)

```yaml
capture:
  - firstItemId:
      path: "$.items[0].id"
  - allItemIds:
      path: "$.items[*].id"
      match: "all"            # Extract all matches
```

### Using Variables

Reference captured variables with `${varName}`:

```yaml
params:
  userId: "${userId}"

payload:
  parentId: "${parentId}"
  email: "user${i}@example.com"

headers:
  Authorization: "Bearer ${token}"
```

---

## Assertions

### Status Code

```yaml
assert:
  status: 201
```

### Body Fields

```yaml
assert:
  status: 200
  body:
    firstName: "Test"
    email: "test@example.com"
```

### Headers

```yaml
assert:
  status: 200
  headers:
    Content-Type: "application/json"
```

---

## Loops (Planned Feature)

### Count Loop - Fixed Iterations

```yaml
- name: "Create multiple items"
  endpoint: "POST /items"
  loop:
    count: 5
    variable: "i"           # ${i} = 1, 2, 3, 4, 5
  payload:
    name: "Item ${i}"
  capture:
    - itemId: "id"          # Stores as itemId_1, itemId_2, etc.
```

### Foreach Loop - Iterate Over Array

```yaml
- name: "Delete each item"
  endpoint: "DELETE /items/${currentItemId}"
  loop:
    foreach: "itemIds"       # Iterates itemIds_1, itemIds_2, etc.
    variable: "currentItemId"
```

### While Loop - Condition-Based

```yaml
# Pagination example - fetch all pages
- name: "Fetch page"
  endpoint: "GET /items"
  params:
    page: "${pageNum}"
  loop:
    while: "${hasMore} == true"
    max: 100                # Safety limit
  capture:
    - hasMore: "meta.hasNextPage"
    - pageNum: "meta.nextPage"
```

---

## OpenAPI Mapping Examples

### Example 1: Petstore API

**OpenAPI spec:**
```yaml
paths:
  /pet:
    post:
      operationId: addPet
      requestBody:
        content:
          application/json:
            schema:
              properties:
                id: { type: integer }
                name: { type: string }
                status: { type: string }
      responses:
        '200':
          content:
            application/json:
              schema:
                properties:
                  id: { type: integer }
                  name: { type: string }
```

**Scenario step:**
```yaml
- name: "Add Pet"
  endpoint: "addPet"           # Use operationId
  payload:
    name: "TestDog"
    status: "available"
  capture:
    - petId: "id"              # Maps to $.id in response
  assert:
    status: 200
```

### Example 2: User API (no operationId)

**OpenAPI spec:**
```yaml
paths:
  /users:
    post:
      summary: "Create user"
      # No operationId defined
      requestBody:
        content:
          application/json:
            schema:
              properties:
                email: { type: string }
                password: { type: string }
  /users/{id}:
    get:
      summary: "Get user by ID"
      parameters:
        - name: id
          in: path
          required: true
```

**Scenario steps:**
```yaml
- name: "Create User"
  endpoint: "POST /users"      # Use METHOD /path format
  payload:
    email: "test@example.com"
    password: "secret123"
  capture:
    - userId: "id"
  assert:
    status: 201

- name: "Get User"
  endpoint: "GET /users/${userId}"
  assert:
    status: 200
```

### Example 3: Nested Response

**OpenAPI response schema:**
```yaml
responses:
  '200':
    content:
      application/json:
        schema:
          properties:
            data:
              properties:
                user:
                  properties:
                    id: { type: integer }
                    profile:
                      properties:
                        name: { type: string }
```

**Capture from nested response:**
```yaml
capture:
  - userId:
      path: "$.data.user.id"
  - userName:
      path: "$.data.user.profile.name"
```

---

## Settings Configuration

```yaml
settings:
  threads: 10              # 10 concurrent users
  rampup: 5                # Start all threads over 5 seconds
  duration: 60             # Run for 60 seconds
  base_url: "http://localhost:8080"  # Override spec URL
```

---

## Complete Field Reference

### Top-Level Structure

```yaml
version: "1.0"              # Required: Always "1.0"
name: "Scenario Name"       # Required: Display name
description: "..."          # Optional: Description

settings:                   # Optional
  threads: 10
  rampup: 5
  duration: 60
  base_url: "http://..."

variables:                  # Optional: Global constants
  key: "value"

scenario:                   # Required: Array of steps
  - name: "Step 1"
    endpoint: "..."
    # ... step fields
```

### Step Structure

```yaml
- name: "Step Name"         # Required: Display name
  endpoint: "..."           # Required: operationId or "METHOD /path"
  enabled: true             # Optional: Default true

  params:                   # Optional: Path/query params
    userId: "${userId}"
    page: 1

  headers:                  # Optional: HTTP headers
    Authorization: "Bearer ${token}"
    X-Custom: "value"

  payload:                  # Optional: Request body
    field: "value"
    nested:
      child: "value"

  capture:                  # Optional: Extract variables
    - varName               # Simple
    - varName: "field"      # Mapped
    - varName:              # Explicit
        path: "$.path"
        match: "first"      # or "all"

  assert:                   # Optional: Assertions
    status: 200
    body:
      field: "expected"
    headers:
      Content-Type: "application/json"

  loop:                     # Optional: Loop control (planned)
    count: 5                # Fixed count
    # OR
    foreach: "varName"      # Iterate array
    # OR
    while: "condition"      # Condition
    max: 100                # Safety limit
    variable: "i"           # Loop variable
```

---

## Validation Rules

### Required Fields

| Level | Required Fields |
|-------|-----------------|
| Root | `version`, `name`, `scenario` |
| Step | `name`, `endpoint` |

### Endpoint Validation

- **operationId**: Must exist in OpenAPI spec
- **METHOD /path**: Must match existing path + method in spec
- Invalid endpoints cause `EndpointNotFoundException`

### Variable Scope

1. Variables in `variables:` are global (available in all steps)
2. Variables from `capture:` are available in subsequent steps only
3. Variable names are case-sensitive
4. Undefined variable: Warning logged, literal `${varName}` kept

### Error Messages

| Error | Cause |
|-------|-------|
| `EndpointNotFound` | operationId or METHOD /path not in spec |
| `UndefinedVariable` | Variable used before capture/definition |
| `InvalidYAML` | YAML syntax error |
| `MissingRequiredField` | Required field not provided |
| `InvalidEndpointFormat` | Not valid operationId or METHOD /path |

---

## Common Mistakes

### 1. Using `steps:` instead of `scenario:`

```yaml
# WRONG
steps:
  - name: "..."

# CORRECT
scenario:
  - name: "..."
```

### 2. Missing variable capture before use

```yaml
# WRONG - userId not captured yet
scenario:
  - name: "Get User"
    endpoint: "GET /users/${userId}"   # Error: undefined variable

# CORRECT - capture first, then use
scenario:
  - name: "Create User"
    endpoint: "POST /users"
    capture:
      - userId: "id"                   # Capture here

  - name: "Get User"
    endpoint: "GET /users/${userId}"   # Now it works
```

### 3. Wrong endpoint format

```yaml
# WRONG - lowercase method
endpoint: "get /users"

# WRONG - missing space
endpoint: "GET/users"

# CORRECT
endpoint: "GET /users"
```

### 4. Wrong capture syntax

```yaml
# WRONG - not an array
capture:
  userId: "id"

# CORRECT - array with mapping
capture:
  - userId: "id"
```

### 5. Forgetting path parameters

```yaml
# WRONG - using literal value in path
endpoint: "GET /users/123"

# CORRECT - use variable substitution
endpoint: "GET /users/${userId}"
params:
  userId: "${userId}"
```

---

## File Naming

- **Default**: `pt_scenario.yaml` (auto-discovered)
- **Named**: `user-flow_scenario.yaml`
- **Multiple**: `scenarios/login.yaml`, `scenarios/checkout.yaml`
