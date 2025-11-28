# Implementation Plan - JMeter Test Generator

## Overview

This document outlines the step-by-step implementation plan for the JMeter Test Generator application.

## Project Goals

1. Create a tool that generates JMeter JMX files from OpenAPI specifications
2. Support both CLI and MCP Server modes
3. Provide automatic project scanning for OpenAPI specs
4. Generate production-ready JMX files with proper configuration

## Implementation Overview

The implementation follows a step-by-step approach with 4 phases:

- Phase 1: Core Logic (4 steps)
- Phase 2: CLI Interface (1 step)
- Phase 3: MCP Server (1 step)
- Phase 4: Testing & Documentation (2 steps)

## Implementation Phases

### Phase 1: Core Logic

#### Step 1: Project Analyzer

**File**: `jmeter_gen/core/project_analyzer.py`

**Responsibilities**:
- Scan project directory for OpenAPI specs
- Support common file names (openapi.yaml, swagger.json, etc.)
- Recursive search with depth limit
- Return spec location and metadata

**Deliverables**:
- ProjectAnalyzer class
- Unit tests
- Support for YAML and JSON formats

**Success Criteria**:
- Can find openapi.yaml in real-world projects
- Returns proper metadata (path, format, found status)
- Handles missing specs gracefully

#### Step 2: OpenAPI Parser

**File**: `jmeter_gen/core/openapi_parser.py`

**Responsibilities**:
- Parse OpenAPI 3.0.x specifications
- Extract endpoints (paths, methods, operations)
- Extract base URL from servers
- Handle request/response schemas

**Deliverables**:
- OpenAPIParser class
- Support for OpenAPI 3.0.x
- Endpoint extraction with metadata
- Unit tests with sample specs

**Success Criteria**:
- Parses real-world OpenAPI specs correctly
- Extracts all endpoints
- Returns structured endpoint data

#### Step 3: JMX Generator

**File**: `jmeter_gen/core/jmx_generator.py`

**CRITICAL**: This step MUST use `docs/JMX_FORMAT_REFERENCE.md` as the primary reference for all JMX structure, property types, and implementation details.

**Responsibilities**:
- Generate JMX XML structure
- Create Test Plan, Thread Group
- Create HTTP Request Samplers
- Add Response Assertions
- Save formatted XML

**Deliverables**:
- JMXGenerator class
- XML generation using ElementTree
- Templates for common elements
- Pretty-print XML output
- Unit tests

**Success Criteria**:
- Generates valid JMX file
- JMeter can load and run the file
- Proper XML formatting
- Configurable threads, rampup, duration

**MVP Features**:
- Test Plan with basic settings
- Thread Group (threads, rampup, duration)
- HTTP Request Samplers (GET, POST)
- Response Code Assertions (200, 201)

**Phase 1 Limitations** (defer to v1.1+):
- No CSV Data Set Config
- No request body generation
- No correlation/extractors
- No authentication
- Only basic assertions

#### Step 4: JMX Validator

**File**: `jmeter_gen/core/jmx_validator.py`

**Responsibilities**:
- Validate JMX XML structure
- Check for required elements
- Provide recommendations

**Deliverables**:
- JMXValidator class
- XML schema validation
- Best practices checker
- Unit tests

**Success Criteria**:
- Validates generated JMX files
- Detects missing elements
- Provides actionable recommendations

### Phase 2: CLI Interface

#### Step 5: CLI Commands

**File**: `jmeter_gen/cli.py`

**Commands to implement**:
1. `jmeter-gen analyze` - Analyze project
2. `jmeter-gen generate` - Generate JMX
3. `jmeter-gen validate` - Validate JMX

**Technology**:
- Click for CLI framework
- Rich for formatted output

**Deliverables**:
- CLI entry point
- All three commands
- Help text and documentation
- Rich table output for analyze

**Success Criteria**:
- `jmeter-gen --help` works
- All commands execute successfully
- Proper error handling
- User-friendly output

**CLI Integration Testing:**

Additional deliverables:
- Integration tests with real OpenAPI specs
- End-to-end test with real-world projects
- Error handling tests
- Edge cases (missing spec, invalid JMX)

**Success Criteria**:
- All integration tests pass
- CLI works with real-world projects
- Helpful error messages

### Phase 3: MCP Server

#### Step 6: MCP Server Implementation

**File**: `jmeter_gen/mcp_server.py`

**Tools to implement**:
1. `analyze_project_for_jmeter`
2. `generate_jmx_from_openapi`

**Technology**:
- MCP Python SDK
- stdio transport

**Deliverables**:
- MCP Server class
- Tool definitions
- Tool handlers (delegate to core logic)
- Entry point via `jmeter-gen mcp`

**Success Criteria**:
- MCP Server starts successfully
- Lists tools correctly
- Handles tool calls
- Returns formatted responses

**MCP Integration:**

Additional deliverables:
- VS Code configuration template
- MCP Server tests
- Documentation for Copilot usage

**Success Criteria**:
- Works with GitHub Copilot in VS Code
- Natural language queries work
- Same results as CLI mode

### Phase 4: Testing & Documentation

#### Step 7: Comprehensive Testing

**Deliverables**:
- Unit tests for all core modules (>80% coverage)
- Integration tests for CLI
- MCP Server tests
- End-to-end tests with real projects

**Test Cases**:
1. Real-world API projects
2. Petstore API (sample)
3. Error cases (missing spec, invalid YAML)
4. Edge cases (empty spec, no endpoints)

**Success Criteria**:
- All tests pass
- >80% code coverage
- No critical bugs

#### Step 8: Documentation

**Deliverables**:
- README.md (main documentation)
- ARCHITECTURE.md (technical architecture)
- CORE_MODULES.md (module specifications)
- DEVELOPMENT.md (developer guide)
- Examples directory with real-world cases

**Success Criteria**:
- Complete user documentation
- Clear architecture diagrams
- Working examples
- Development setup guide

## Deliverables Checklist

### Code

- [ ] jmeter_gen/core/project_analyzer.py
- [ ] jmeter_gen/core/openapi_parser.py
- [ ] jmeter_gen/core/jmx_generator.py
- [ ] jmeter_gen/core/jmx_validator.py
- [ ] jmeter_gen/cli.py
- [ ] jmeter_gen/mcp_server.py
- [ ] jmeter_gen/__init__.py
- [ ] pyproject.toml
- [ ] All __init__.py files

### Templates

- [ ] templates/test_plan_base.xml
- [ ] templates/thread_group.xml
- [ ] templates/http_sampler.xml
- [ ] templates/assertion.xml

### Tests

- [ ] tests/core/test_project_analyzer.py
- [ ] tests/core/test_openapi_parser.py
- [ ] tests/core/test_jmx_generator.py
- [ ] tests/core/test_jmx_validator.py
- [ ] tests/test_cli.py
- [ ] tests/test_mcp_server.py
- [ ] tests/integration/test_end_to_end.py

### Documentation

- [ ] README.md
- [ ] docs/IMPLEMENTATION_PLAN.md (this file)
- [ ] docs/ARCHITECTURE.md
- [ ] docs/CORE_MODULES.md
- [ ] docs/DEVELOPMENT.md
- [x] examples/petstore/ (Swagger 2.0)
- [x] examples/simple-crud/ (OpenAPI 3.0.3)

### Configuration

- [ ] pyproject.toml
- [ ] .vscode/settings.json (MCP config)
- [ ] .gitignore
- [ ] LICENSE

## MVP Scope

### Included in MVP

1. OpenAPI 3.0.x support (YAML and JSON)
2. Auto-detection of specs in project
3. HTTP samplers (GET, POST, PUT, DELETE)
4. Basic response assertions (status code)
5. Thread Group configuration (threads, rampup, duration)
6. CLI interface (analyze, generate, validate)
7. MCP Server interface
8. Rich terminal output
9. JMX validation

### Excluded from MVP (Future Versions)

1. CSV Data Set Config generation
2. Request body data generation (faker)
3. Correlation and extractors
4. Authentication (Bearer, Basic, OAuth2)
5. Cookie Manager
6. Advanced assertions (JSON, regex)
7. Timers and think time
8. Swagger 2.0 support
9. Interactive mode
10. JMX modification (adding samplers to existing JMX)

## Success Metrics

### Functionality

- Generates valid JMX files that JMeter can execute
- Works with real-world OpenAPI specs
- Both CLI and MCP modes produce identical results

### Quality

- >80% test coverage
- No critical bugs
- All integration tests pass
- Clean code (passes linting)

### Usability

- Clear error messages
- User-friendly CLI output
- Complete documentation
- Working examples

### Performance

- Analyzes project in <1 second
- Generates JMX in <2 seconds
- No memory leaks

## Risk Mitigation

### Risk 1: JMX XML Complexity

**Mitigation**:
- Start with minimal valid JMX
- Use templates for common elements
- Test with JMeter GUI early and often
- Validate against JMeter XSD schema

### Risk 2: OpenAPI Spec Variations

**Mitigation**:
- Test with multiple real-world specs
- Handle missing fields gracefully
- Validate spec before parsing
- Document supported OpenAPI versions clearly

### Risk 3: MCP Integration Issues

**Mitigation**:
- Keep MCP Server as thin wrapper
- Reuse CLI logic completely
- Test MCP Server independently
- Provide fallback to CLI mode

### Risk 4: Scope Creep

**Mitigation**:
- Stick to MVP scope strictly
- Document future features separately
- Reject feature requests until MVP is stable
- Use versioning (v1.0 MVP, v1.1 enhancements)

## Definition of Done

A feature is "done" when:

1. Code is written and follows style guide
2. Unit tests written and passing
3. Integration tests passing (if applicable)
4. Documentation updated
5. Code reviewed
6. No critical bugs
7. Tested with real-world examples

## Extensions Backlog

See [../BACKLOG.md](../BACKLOG.md) for the consolidated prioritized backlog.

---

## OpenAPI Change Detection (Implemented)

#### Overview
Automatic detection of API changes in team environment using committed snapshots for collaboration and git-based audit trail.

#### Architecture

**New Core Modules:**

1. **SpecComparator** (`jmeter_gen/core/spec_comparator.py`)
   - Compare two OpenAPI/Swagger specifications
   - Detect added endpoints (path + method not in old spec)
   - Detect removed endpoints (path + method not in new spec)
   - Detect modified endpoints (same path+method, different definition)
   - Calculate endpoint fingerprints (SHA256 hash of normalized endpoint)
   - Generate SpecDiff dataclass with structured changes

2. **JMXUpdater** (`jmeter_gen/core/jmx_updater.py`)
   - Parse existing JMX files (xml.etree.ElementTree)
   - Add new HTTP Samplers for added endpoints
   - Disable (enabled="false") obsolete samplers (never delete)
   - Update modified samplers (path, method, request body)
   - Preserve user customizations:
     - Assertions (beyond default status code)
     - Timers (Constant Timer, Gaussian Timer, etc.)
     - Pre/Post Processors
     - Config elements (CSV Data Set, User Variables, etc.)
   - Create timestamped backups before any modification

3. **SnapshotManager** (`jmeter_gen/core/snapshot_manager.py`)
   - Save spec snapshots with sensitive data filtering
   - Load snapshots from `.jmeter-gen/snapshots/`
   - Calculate spec hash (SHA256 of normalized JSON)
   - Filter sensitive fields (tokens, passwords, API keys, secrets)
   - Manage backup rotation (keep last N backups)
   - Create .gitignore for backups (not snapshots)
   - Store git metadata (commit hash, branch, author)

**Extended Modules:**

4. **ProjectAnalyzer** (extended)
   - Add `auto_detect_changes` parameter (default: True)
   - Load snapshot on analyze
   - Compare current spec hash with snapshot hash
   - If different: run SpecComparator and include diff in result
   - Display change summary in CLI output

#### Data Structures

```python
@dataclass
class EndpointChange:
    path: str
    method: str
    operation_id: str
    change_type: str  # "added", "removed", "modified"
    changes: Dict[str, Any]  # Specific changes (request_body, parameters, etc.)
    fingerprint: str  # SHA256 hash

@dataclass
class SpecDiff:
    old_version: str
    new_version: str
    old_hash: str
    new_hash: str
    added_endpoints: List[EndpointChange]
    removed_endpoints: List[EndpointChange]
    modified_endpoints: List[EndpointChange]
    summary: Dict[str, int]  # {"added": 3, "removed": 1, "modified": 2}
    timestamp: str
    has_changes: bool
```

#### Snapshot Storage Strategy (Opcja B: Committed Snapshots)

**Directory Structure:**
```
project/
├── openapi.yaml                    # API spec (committed)
├── tests/jmeter/
│   ├── my-api-test.jmx            # JMX file (committed)
│   └── .jmeter-gen/
│       ├── snapshots/
│       │   └── my-api-test.spec.json  # ✅ COMMITTED (team collaboration)
│       ├── backups/                    # ❌ GITIGNORED (local only)
│       │   └── *.jmx.backup.*
│       └── .gitignore              # Auto-created
```

**Snapshot Format (my-api-test.spec.json):**
```json
{
  "version": "1.0",
  "format": "jmeter-gen-snapshot",
  "captured_at": "2025-11-24T10:00:00Z",
  "captured_by": "user@example.com",
  "git_commit": "abc123def456",
  "git_branch": "main",
  "spec": {
    "path": "openapi.yaml",
    "hash": "sha256:abc123...",
    "api_version": "1.0.0",
    "api_title": "My API",
    "base_url": "http://localhost:8080",
    "endpoints_count": 20
  },
  "jmx": {
    "path": "tests/jmeter/my-api-test.jmx",
    "hash": "sha256:def456...",
    "samplers_count": 20
  },
  "endpoints": [
    {
      "path": "/users",
      "method": "GET",
      "operation_id": "listUsers",
      "fingerprint": "sha256:xyz789...",
      "request_body": false,
      "parameters": [
        {"name": "page", "in": "query", "type": "integer"}
      ]
    }
  ],
  "security": {
    "filtered": true,
    "note": "Sensitive data removed for git storage"
  }
}
```

**Security: Sensitive Data Filtering**

Filtered fields (not stored in snapshot):
- `api_key`, `apiKey`, `token`, `access_token`, `auth_token`
- `password`, `passwd`, `secret`, `client_secret`
- `bearer`, `authorization`, `credit_card`, `ssn`
- Example data values (emails, phones, real data)

Stored (safe for git):
- Field names and types
- Endpoint paths and methods
- Parameter names and types (no defaults/examples)
- Schema structure (no example values)
- Operation IDs and summaries

#### CLI Commands

**Extended `analyze` command:**
```bash
jmeter-gen analyze [OPTIONS]

Options:
  --project-path PATH       Project directory (default: current)
  --no-detect-changes       Disable change detection (enabled by default)
  --show-details            Show detailed change breakdown
  --export-diff PATH        Export diff to JSON file
```

**Extended `generate` command:**
```bash
jmeter-gen generate [OPTIONS]

Options:
  --spec PATH               OpenAPI spec path
  --output PATH             Output JMX file
  --auto-update             Auto-update JMX if changes detected (no prompt)
  --force-new               Force new JMX (skip update)
  --no-snapshot             Don't save snapshot (one-time generation)
  ... (existing options)
```

#### Workflows

**Team Workflow (Git-based):**

1. **Developer changes API:**
   ```bash
   git checkout -b feature/new-endpoint
   vim openapi.yaml  # Add endpoint
   jmeter-gen generate --spec openapi.yaml
   # → Updates JMX, creates/updates snapshot
   git add openapi.yaml tests/jmeter/
   git commit -m "Add new endpoint"
   git push
   ```

2. **Code Review:**
   ```bash
   # Reviewer sees changes in PR:
   # - openapi.yaml diff
   # - my-api-test.jmx diff
   # - my-api-test.spec.json diff (shows what changed)

   git checkout feature/new-endpoint
   jmeter-gen analyze --show-details
   # → Shows exactly what changed
   ```

3. **After merge to main:**
   ```bash
   git checkout main
   git pull origin main
   jmeter-gen analyze
   # → Shows: "Snapshot up to date (no changes)"
   # All team members have same state
   ```

**CI/CD Integration:**
```yaml
# .github/workflows/api-changes.yml
- name: Detect API changes
  run: jmeter-gen analyze --export-diff changes.json

- name: Validate snapshot consistency
  run: |
    if git diff --name-only main | grep -q "openapi.yaml"; then
      # API changed - snapshot must be updated too
      git diff --name-only main | grep -q ".spec.json" || exit 1
    fi

- name: Auto-update JMX
  run: jmeter-gen generate --auto-update
```

#### Implementation Phases

**Phase 1: Core Comparison**
- Implement SpecComparator class
- Endpoint fingerprint calculation
- Detect added/removed/modified endpoints
- Generate SpecDiff structure
- Unit tests (80%+ coverage)

**Phase 2: Snapshot Management**
- Implement SnapshotManager class
- Sensitive data filtering
- Hash calculation
- Git metadata extraction
- .gitignore creation
- Unit tests

**Phase 3: JMX Update**
- Implement JMXUpdater class
- Parse existing JMX files
- Add/disable/update samplers
- Preserve user customizations
- Backup creation
- Unit tests

**Phase 4: CLI Integration**
- Extend ProjectAnalyzer with auto-detect
- Extend analyze command
- Extend generate command with --auto-update
- Implement resolve-snapshot-conflict command
- Rich formatting for change display

**Phase 5: MCP Integration**
- Update analyze_project_for_jmeter tool
- Update generate_jmx_from_openapi tool
- Add change detection to MCP responses

**Phase 6: Testing & Documentation**
- Integration tests (full workflow)
- User documentation
- Team workflow guide
- CI/CD examples

#### Success Criteria

- Automatic change detection on every `analyze`
- Zero-prompt auto-update with `--auto-update` flag
- Snapshots safe for git commit (no sensitive data)
- Team collaboration without local state conflicts
- 80%+ test coverage for all new modules
- Comprehensive documentation with examples

#### Performance Targets

- Spec comparison: <500ms (for 50 endpoints)
- Snapshot save: <200ms
- Snapshot load: <100ms
- JMX update: <1s (for 50 samplers)

#### Implementation Details

**Snapshot Naming Convention**: `{jmx_basename}.spec.json`
- Example: `my-api-test.jmx` → `.jmeter-gen/snapshots/my-api-test.spec.json`

**Non-Git Environment Behavior**: Graceful degradation
- Snapshots still created and work
- Git metadata fields set to null
- Change detection fully functional
- Log warning: "Not a git repository, snapshots will not include git metadata"

**Configuration**: No configuration file currently
- Future: Add `.jmetergenrc` for custom sensitive patterns, backup retention

#### Technical Specifications

See `docs/CORE_MODULES.md` for module specifications.

## Getting Started

To begin implementation:

1. Review ARCHITECTURE.md
2. Review CORE_MODULES.md
3. Set up development environment (see DEVELOPMENT.md)
4. Start with Step 1: Project Analyzer (Phase 1)
5. Follow test-driven development approach
6. Test with real-world OpenAPI projects frequently

## Questions to Resolve

1. XML library: ElementTree (stdlib) vs lxml?
   - Recommendation: ElementTree for MVP (no dependencies)

2. MCP SDK version requirements?
   - Check latest stable version

3. Minimum Python version?
   - Recommendation: Python 3.9+

4. JMeter version target?
   - Recommendation: JMeter 5.6+

5. OpenAPI validation library?
   - Recommendation: Basic YAML parsing for MVP, defer validation to v1.1

## Notes

- Keep it simple for MVP
- Prioritize working code over perfect code
- Test with real projects early and often
- Document as you go
- Ask for feedback frequently
