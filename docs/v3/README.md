# v3.0.0 - Scenario Init Wizard

## Overview

Version 3.0.0 introduces an interactive wizard for creating `pt_scenario.yaml` files. The wizard guides users through step-by-step scenario building with endpoint selection, auto-capture suggestions, and special functions (loop, timer).

## New Command

```bash
jmeter-gen new scenario [--spec PATH] [--output NAME]
```

## Features

1. **Auto-detect OpenAPI spec** - automatically finds openapi.yaml in project
2. **Endpoint list with operationId** - displays "METHOD /path (operationId)"
3. **Smart capture suggestions** - analyzes response schema, suggests id/token fields
4. **Variable usage detection** - highlights endpoints that use captured variables
5. **Special actions**: loop (count/while), think time as separate steps
6. **Live preview** - shows current scenario after each step
7. **YAML output** - generates valid pt_scenario.yaml

## User Flow Example

```
$ jmeter-gen new scenario

Scenario Wizard
==================

? Scenario name: User Registration Flow
? Description (optional): Complete user registration and verification

? OpenAPI spec found: ./openapi.yaml
  Use this spec? [Y/n]: Y

Found 15 endpoints in spec

? Settings:
  Threads [1]: 10
  Ramp-up (seconds) [0]: 5
  Duration (seconds, empty=single iteration): 60
  Base URL override (empty=from spec):

--------------------------------------------

Step 1:
? Select action:
  > Add endpoint
    Add loop
    Add think time
    Done - save scenario

? Select endpoint:
  > POST /users (createUser)
    GET /users (getUsers)
    GET /users/{id} (getUserById)
    ...

? Step name [Create User]:

Suggested captures from response schema:
  [x] id -> ${userId}
  [ ] email
  [ ] createdAt

? Add assertions?
  [x] Status code: 201

--------------------------------------------

Current scenario:
  1. Create User (POST /users) -> captures: userId

Step 2:
? Select action: Add endpoint

? Select endpoint:
  > GET /users/{id} (getUserById)  <- suggested (uses ${userId})

Auto-detected: This endpoint uses ${userId} from step 1

--------------------------------------------

Step 3:
? Select action: Add loop

? Loop type: Fixed count
? Count: 5
? Interval between iterations (ms) [0]: 1000

? Select endpoint for loop:
  > GET /status (getStatus)

--------------------------------------------

Step 4:
? Select action: Add think time

? Think time (ms): 2000

--------------------------------------------

? Select action: Done - save scenario

Saved: pt_scenario.yaml

  4 steps created
  2 captures configured
  1 loop configured
```

## Generated Output

```yaml
version: "1.0"
name: "User Registration Flow"
description: "Complete user registration and verification"

settings:
  threads: 10
  rampup: 5
  duration: 60

scenario:
  - name: "Create User"
    endpoint: "POST /users"
    capture:
      - userId: "id"
    assert:
      status: 201

  - name: "Get User"
    endpoint: "GET /users/${userId}"
    assert:
      status: 200

  - name: "Poll Status"
    endpoint: "GET /status"
    loop:
      count: 5
      interval: 1000

  - name: "Think Time"
    think_time: 2000
```

## Dependencies

- `questionary` - interactive prompts with checkboxes and lists

## Files

| File | Purpose |
|------|---------|
| `jmeter_gen/core/scenario_wizard.py` | Wizard logic |
| `jmeter_gen/cli.py` | CLI command `new scenario` |
| `tests/core/test_scenario_wizard.py` | Unit tests |

## Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Overview, features, user flow example |
| [CORE_MODULES.md](CORE_MODULES.md) | ScenarioWizard class specification |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Step-by-step implementation plan |

## Related Documentation

- [v2/PT_SCENARIO_SPEC.md](../v2/PT_SCENARIO_SPEC.md) - pt_scenario.yaml format specification
- [BACKLOG.md](../BACKLOG.md) - Extensions backlog
