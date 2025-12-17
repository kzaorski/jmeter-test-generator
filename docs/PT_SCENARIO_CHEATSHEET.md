# pt_scenario.yaml Cheatsheet

Quick reference for creating test scenarios.

---

## Minimal Example

```yaml
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

---

## Structure

```yaml
name: "Scenario Name"           # Required
description: "..."              # Optional

settings:                       # Optional
  threads: 10
  rampup: 5
  duration: 60
  base_url: "http://localhost:8080"

variables:                      # Optional - global constants
  api_key: "test-key"

scenario:                       # Required - list of steps
  - name: "Step Name"
    endpoint: "..."
    # ... step config
```

---

## Step Fields

```yaml
- name: "Step Name"             # Required
  endpoint: "createUser"        # Required - operationId or "METHOD /path"
  enabled: true                 # Optional (default: true)
  params:                       # Optional - path/query params
    userId: "${userId}"
  headers:                      # Optional
    Authorization: "Bearer ${token}"
  payload:                      # Optional - request body
    email: "test@example.com"
  capture:                      # Optional - extract from response
    - userId: "id"
  assert:                       # Optional
    status: 201
  loop:                         # Optional
    count: 5
  think_time: 1000              # Optional - delay in ms
```

---

## Endpoint Formats

```yaml
# operationId (preferred)
endpoint: "createUser"
endpoint: "getUserById"

# METHOD /path (when no operationId)
endpoint: "POST /users"
endpoint: "GET /users/{userId}"
endpoint: "DELETE /api/v1/items/{id}"

# Short path (auto-mapped to full path)
endpoint: "POST /trigger"       # Maps to /api/v2/trigger
```

---

## Capture Syntax

```yaml
capture:
  # Simple - auto-detect JSONPath
  - userId

  # Mapped - different field name
  - userId: "id"
  - userName: "user.name"

  # Explicit JSONPath
  - firstItemId:
      path: "$.items[0].id"
  - allIds:
      path: "$.items[*].id"
      match: "all"
```

Use captured variables: `${userId}`, `${token}`

---

## Assertions

```yaml
assert:
  status: 200
  body:
    firstName: "Test"
  headers:
    Content-Type: "application/json"
  body_contains: "Success"      # For non-JSON responses
```

---

## Loops

```yaml
# Fixed count
loop:
  count: 5
  interval: 1000                # Delay between iterations (ms)

# While condition
loop:
  while: "${status} != 'completed'"
  max: 30                       # Safety limit
  interval: 5000

# Multi-step loop
- loop:
    count: 3
  steps:
    - name: "Step A"
      endpoint: "GET /a"
    - think_time: 500
```

---

## Common Mistakes

| Wrong | Correct |
|-------|---------|
| `steps:` | `scenario:` |
| `endpoint: "get /users"` | `endpoint: "GET /users"` |
| `capture: userId: "id"` | `capture: - userId: "id"` |
| Using `${var}` before capture | Capture first, then use |

---

## Commands

```bash
# Validate scenario
jmeter-gen validate scenario pt_scenario.yaml --spec openapi.yaml

# Generate JMX
jmeter-gen generate

# Create new scenario (wizard)
jmeter-gen new scenario
```

---

Full specification: [PT_SCENARIO_SPEC.md](PT_SCENARIO_SPEC.md)
