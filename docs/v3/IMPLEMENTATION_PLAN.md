# v3 Implementation Plan

## Overview

This document outlines the implementation phases for JMeter Test Generator v3.0.0.

**Key Feature**: Interactive wizard command `jmeter-gen new scenario` for creating `pt_scenario.yaml` files.

**Implementation Steps**: 12 steps total (11 implementation + 1 documentation)

---

## Phase 1: v3.0.0 - Scenario Init Wizard

### Objectives

- Interactive CLI wizard for creating pt_scenario.yaml
- Auto-detect OpenAPI spec in project
- Endpoint selection with operationId display
- Smart capture suggestions from response schemas
- Support for loop and think time steps
- Live preview of current scenario
- YAML output generation

### Implementation Steps

#### Step 1: Add questionary Dependency

- Add `questionary>=2.0.0` to pyproject.toml dependencies
- Run `pip install -e ".[dev]"` to install
- Verify installation with simple test

#### Step 2: Create ScenarioWizard Class Structure

- Create `jmeter_gen/core/scenario_wizard.py`
- Define `WizardState` and `EndpointOption` dataclasses
- Implement `__init__` with OpenAPIParser
- Implement `run()` main flow skeleton
- Implement `save()` method

#### Step 3: Implement Metadata Prompts

- Implement `_prompt_metadata()` for name/description
- Implement `_prompt_settings()` for threads/rampup/duration/base_url
- Add input validation for numeric fields
- Handle user cancellation (Ctrl+C)

#### Step 4: Implement Endpoint Selection

- Implement `_prompt_action()` for action selection
- Implement `_prompt_endpoint()` with endpoint list
- Format endpoints as "METHOD /path (operationId)"
- Implement `_detect_variable_usage()` for suggestions
- Sort endpoints: suggested first, then alphabetically
- Implement `_prompt_step_name()` with smart defaults
- Implement `_prompt_path_params()` for static values when no variable matches
- Implement `_prompt_headers()` for Authorization with captured tokens

#### Step 5: Implement Capture Suggestions

- Implement `_suggest_captures()` algorithm
- Analyze response schema for id/token/key fields
- Implement `_generate_variable_name()` for naming
- Implement `_validate_variable_name()` for JMeter/YAML compatibility
- Implement `_prompt_captures()` with checkbox selection
- Track captured variables in WizardState

#### Step 6: Implement Assertions

- Implement `_prompt_assertions()` for status code
- Default status based on HTTP method
- Optional body field assertions

#### Step 7: Implement Loop Support

- Implement `_prompt_loop()` for loop configuration
- Support fixed count loops
- Support while condition loops
- Prompt for interval between iterations
- Prompt for endpoint within loop

#### Step 8: Implement Think Time

- Implement `_prompt_think_time()` for delays
- Validate milliseconds input
- Add as separate step in scenario

#### Step 9: Implement Preview and YAML Generation

- Implement `_render_preview()` using Rich Table
- Show step list with captures and variable usage
- Implement `_to_yaml()` for YAML serialization
- Ensure proper formatting (block style, no sorting)

#### Step 10: CLI Integration

- Add `new` command group to cli.py
- Add `scenario` subcommand with options
- Auto-detect OpenAPI spec if --spec not provided
- Confirm spec usage with user
- Run wizard and save output
- Display summary (steps, captures, loops)

#### Step 11: Testing

- Unit tests for ScenarioWizard methods
- Mock questionary prompts for testing
- Test capture suggestion algorithm
- Test variable name generation
- Test YAML output format
- CLI integration tests
- Test error handling (no spec, user cancel)

#### Step 12: Documentation Update

- Update main README.md with v3 features
- Update CLAUDE.md with v3 modules and commands
- Update CLI --help texts for new commands
- Add v3 to docs/BACKLOG.md (move Scenario Init Wizard to Completed)
- Update pyproject.toml description if needed
- Verify all docstrings are complete
- Update version references across all files

### Acceptance Criteria

- [ ] `jmeter-gen new scenario` starts interactive wizard
- [ ] Auto-detects OpenAPI spec in current directory
- [ ] Displays endpoint list with METHOD /path (operationId) format
- [ ] Suggests captures based on response schema analysis
- [ ] Highlights endpoints that use captured variables
- [ ] Prompts for path param values when no variable matches
- [ ] Suggests Authorization header when token captured
- [ ] Validates variable names for JMeter/YAML compatibility
- [ ] Supports fixed count and while loops (single endpoint only)
- [ ] Supports think time as separate step
- [ ] Shows live preview after each step
- [ ] Generates valid pt_scenario.yaml
- [ ] Handles user cancellation gracefully
- [ ] >80% test coverage for new module

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `jmeter_gen/core/scenario_wizard.py` | Create | Wizard logic |
| `jmeter_gen/cli.py` | Modify | Add `new` group + `scenario` command |
| `tests/core/test_scenario_wizard.py` | Create | Unit tests |
| `tests/test_cli_v3.py` | Create | CLI integration tests |
| `pyproject.toml` | Modify | Add questionary dependency, bump version |
| `jmeter_gen/__init__.py` | Modify | Update version to 3.0.0 |

---

## Test Strategy

### Unit Tests

```
tests/core/test_scenario_wizard.py
  - test_prompt_metadata_default_values
  - test_prompt_metadata_custom_values
  - test_prompt_settings_defaults
  - test_prompt_settings_validation
  - test_suggest_captures_id_fields
  - test_suggest_captures_token_fields
  - test_suggest_captures_no_schema
  - test_generate_variable_name_id_field
  - test_generate_variable_name_custom_field
  - test_detect_variable_usage
  - test_endpoint_sorting_suggested_first
  - test_to_yaml_format
  - test_save_creates_file
```

### CLI Tests

```
tests/test_cli_v3.py
  - test_new_scenario_no_spec_found
  - test_new_scenario_auto_detect_spec
  - test_new_scenario_custom_spec_path
  - test_new_scenario_custom_output
```

### Mocking Strategy

```python
from unittest.mock import patch, MagicMock

@patch('questionary.text')
@patch('questionary.select')
@patch('questionary.checkbox')
def test_wizard_flow(mock_checkbox, mock_select, mock_text):
    # Configure mock returns
    mock_text.return_value.ask.side_effect = [
        "Test Scenario",  # name
        "",               # description
        "5",              # threads
        "2",              # rampup
        "",               # duration
        "",               # base_url
    ]
    mock_select.return_value.ask.side_effect = [
        "Add endpoint",
        "Done - save scenario",
    ]
    # ... test wizard
```

---

## Dependencies

```
v3.0.0 (Current)
    |
    +-- ScenarioWizard (new module)
    +-- CLI extension (new group)
    +-- questionary (new dependency)
    |
    Depends on:
    +-- OpenAPIParser (existing)
    +-- ProjectAnalyzer (existing)
```

---

## Branch Strategy

All v3 development happens on `v3` branch:

```bash
# Current state
git checkout v3  # Already on v3 branch

# Create feature branch if needed
git checkout -b v3/wizard-implementation

# Merge back to v3
git checkout v3
git merge v3/wizard-implementation

# Release process
git checkout master
git merge v3
git tag v3.0.0
```

---

## Example Session

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

----------------------------------------

Step 1:
? Select action: Add endpoint

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
? Confirm captures: [Enter]

? Add assertions?
  [x] Status code: 201

----------------------------------------

Current scenario:
  1. Create User (POST /users) -> captures: userId

Step 2:
? Select action: Add endpoint

? Select endpoint:
  > GET /users/{id} (getUserById)  <- suggested (uses ${userId})
    ...

Auto-detected: This endpoint uses ${userId} from step 1

----------------------------------------

Step 3:
? Select action: Add think time

? Think time (ms): 2000

----------------------------------------

? Select action: Done - save scenario

Saved: pt_scenario.yaml

  3 steps created
  1 capture configured
```

---

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

  - name: "Think Time"
    think_time: 2000
```

---

## Error Scenarios

### No OpenAPI Spec Found

```
$ jmeter-gen new scenario

No OpenAPI spec found. Use --spec to specify path.
```

### User Cancels

```
$ jmeter-gen new scenario
? Scenario name: ^C

Wizard cancelled.
```

### Invalid Input

```
? Threads [1]: abc
Invalid input: must be a positive number
? Threads [1]: 10
```
