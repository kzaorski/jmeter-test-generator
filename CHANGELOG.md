# Changelog

All notable changes to the JMeter Test Generator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.4.0] - 2025-12-17

### Added
- **CI/CD Integration Features** - New options for pipeline usage (Azure DevOps, GitHub Actions, etc.)
  - `--scenario PATH` flag for explicit scenario file path (overrides auto-discovery)
  - `--spec URL` support to download OpenAPI spec from HTTP/HTTPS URLs
  - `--insecure` flag to skip SSL verification when downloading spec from URL
  - Auto-detect CI environment (CI, TF_BUILD, GITHUB_ACTIONS, GITLAB_CI, etc.)
  - Plain text output without colors when CI environment detected
- New helper functions in CLI module
  - `_is_ci_environment()` - Detect CI environment variables
  - `_resolve_spec_path()` - Download spec from URL if needed
- 9 new tests for CI integration features

### Changed
- `--spec` option now accepts both file paths and URLs
- Console output automatically adapts to CI environment (no colors, no interactive prompts)

### Documentation
- Added "CI/CD Integration" section to README.md with pipeline examples
- Added "CI/CD Integration" section to CLAUDE.md
- New `docs/PIPELINE_INTEGRATION_PLAN.md` with implementation details

---

## [3.3.0] - 2025-12-16

### Added
- **`--no-scenario` Flag** - New option for `generate` command
  - Skips scenario file detection
  - Forces OpenAPI-based generation even when pt_scenario.yaml exists
- **Generation Options Menu** - When scenario file is found during `analyze`
  - Option 1: Generate from scenario (recommended)
  - Option 2: Generate from OpenAPI spec only (uses `--no-scenario`)
  - Option 3: Don't generate now

### Changed
- `analyze` output now shows relative paths instead of full paths for better readability
- Improved snapshot path comparison to handle macOS symlinks (`/var` -> `/private/var`)

### Fixed
- Path truncation issues in Rich tables when displaying long file paths

---

## [3.2.2] - 2025-12-03

### Added
- **Interactive "Run Generate" Prompt** - After `analyze` and `new scenario` commands
  - Prompts "Run generate now? [Y/n]" instead of just showing suggestion
  - If yes: runs `generate` command automatically
  - If no: shows the traditional "Next step: jmeter-gen generate" suggestion

### Changed
- Removed next step suggestion when scenario parsing fails (user must fix scenario first)

---

## [3.2.1] - 2025-12-03

### Added
- **Automatic Validation** - All generation operations now automatically validate output
  - CLI `generate` (OpenAPI) - JMX validation after generation
  - CLI `generate --scenario` - JMX validation after generation
  - MCP `generate_scenario_jmx` - JMX validation result included in response
  - MCP `build_scenario` - Scenario validation result included in response
- Validation results displayed in CLI output (PASSED / issue count)
- MCP responses include structured `validation` object with issues

### Changed
- Consistent validation behavior across all generation paths

---

## [3.2.0] - 2025-12-03

### Added
- **Scenario Validator Tool** - Dedicated validation for pt_scenario.yaml before generation
  - `jmeter-gen validate scenario` command for CLI validation
  - `validate_scenario` MCP tool for AI agent integration
  - ScenarioValidator module with structured ValidationResult
  - Error vs warning distinction (errors block generation)
  - Checks: YAML syntax, required fields, endpoint existence, variable lifecycle
- Scenario validation in development workflow to catch errors early

### Changed
- `jmeter-gen validate` command now requires target type: `script` or `scenario`
  - Old: `jmeter-gen validate test.jmx`
  - New: `jmeter-gen validate script test.jmx`
- MCP Server now provides 9 tools (was 8)
- Updated existing tool descriptions to suggest validation workflow

---

## [3.1.0] - 2025-12-01

### Added
- **MCP Scenario Builder Tools** - 3 new tools for scenario creation via MCP
  - `list_endpoints`: List all endpoints from OpenAPI spec with details
  - `suggest_captures`: Suggest capturable variables from endpoint response schema
  - `build_scenario`: Build pt_scenario.yaml from step definitions

### Changed
- MCP Server now provides 8 tools (was 5)
- Test count increased to 677 tests
- Code coverage at 82%

---

## [3.0.0] - 2025-12-01

### Added
- **Scenario Init Wizard** - Interactive CLI wizard for creating pt_scenario.yaml files
  - `jmeter-gen new scenario` command
  - Auto-detect OpenAPI spec in project
  - Endpoint selection with "METHOD /path (operationId)" format
  - Smart capture suggestions (id, token fields from response schema)
  - Variable usage detection for endpoint suggestions
  - Loop (count/while) and think time support
  - Live preview after each step
- `questionary` dependency for interactive prompts

### Changed
- Test count increased to 624 tests
- Code coverage at 85%

---

## [2.0.0] - 2025-11-28

### Added
- **Scenario-Based Testing** - Define realistic user flows with pt_scenario.yaml
  - PtScenarioParser for YAML parsing and validation
  - CorrelationAnalyzer for auto-detecting JSONPath captures
  - ScenarioJMXGenerator for sequential JMX generation
  - ScenarioVisualizer for terminal flow visualization
  - ScenarioMermaid for diagram generation
- **MCP Server Tools** - 5 tools for GitHub Copilot integration
- **Variable Capture & Correlation** - Extract response values for subsequent steps
- **Endpoint Formats** - Support operationId and METHOD /path formats
- **Multi-step Loops** - Loop with count, while condition, interval settings

### Changed
- `analyze` command detects pt_scenario.yaml files
- `generate` command uses scenario-based flow when pt_scenario.yaml present

---

## [1.1.0] - 2025-11-25

### Added

- **Multi-spec selection support** - When multiple OpenAPI specs are found in a project:
  - CLI `analyze` displays table with all found specs
  - CLI `generate` prompts user to select which spec to use
  - MCP Server returns `available_specs` list for Copilot integration
- New `find_all_openapi_specs()` method in ProjectAnalyzer
- `analyze_project()` now returns `available_specs` and `multiple_specs_found` fields

### Changed

- Test count increased from 326 to 372 tests
- Code coverage improved from 85% to 92%

### Fixed

- `generate` command now uses `recommended_jmx_name` from `analyze` for consistent naming

---

## [1.0.0] - 2025-11-25

### Overview

Initial release of JMeter Test Generator - a tool that generates JMeter JMX test plans from OpenAPI/Swagger specifications. Features dual-mode architecture (CLI + MCP Server), OpenAPI change detection, and comprehensive JMX generation.

### Features

#### Core Functionality
- **Automatic spec detection** - Finds OpenAPI/Swagger specs in project directories
- **OpenAPI 3.x and Swagger 2.0 support** - Full parsing and validation
- **JMX generation** - HTTP Request Defaults pattern, thread groups, assertions
- **JMX validation** - Structure validation with improvement recommendations
- **Smart default output filename** - Generated from API title (e.g., "My API" -> `my-api-test.jmx`)

#### OpenAPI Change Detection
- **SpecComparator** - Detect added, removed, modified endpoints
- **SnapshotManager** - Save/load spec snapshots with sensitive data filtering
- **JMXUpdater** - Update existing JMX files, preserve customizations

#### CLI Commands
- `jmeter-gen analyze` - Scan project for OpenAPI specs
- `jmeter-gen generate` - Generate JMX files (auto-discovers spec)
- `jmeter-gen validate` - Validate existing JMX files
- `jmeter-gen mcp` - Start MCP Server for GitHub Copilot

#### MCP Server
- `analyze_project_for_jmeter` - Project analysis via MCP protocol
- `generate_jmx_from_openapi` - JMX generation with change detection support

### CLI Options

**analyze:**
- `--no-detect-changes` - Disable change detection (enabled by default)
- `--show-details` - Show detailed change breakdown
- `--export-diff PATH` - Export diff to JSON

**generate:**
- `--output PATH` - Custom output path (default: based on API title)
- `--threads N` - Number of virtual users (default: 1)
- `--rampup N` - Ramp-up period in seconds (default: 0)
- `--duration N` - Test duration in seconds
- `--base-url URL` - Override base URL from spec
- `--auto-update` - Update existing JMX when changes detected
- `--force-new` - Force regeneration (skip update)
- `--no-snapshot` - Skip snapshot saving

### Technical Details

- **Testing**: 326 tests passing, 85% code coverage
- **Performance**: <5 seconds end-to-end for typical projects
- **Dependencies**: Python 3.9+, PyYAML, Click, Rich, MCP SDK

### Known Limitations

- No built-in authentication support (Bearer, API keys, Basic Auth)
- Minimal sample data for request bodies
- No correlation/variable extraction
- No CSV Data Set Config generation
- Status code assertions only (200/201)

### Documentation

- README.md - Installation and usage
- QUICKSTART.md - 5-minute getting started guide
- docs/ARCHITECTURE.md - System design
- docs/CORE_MODULES.md - Module specifications
- docs/DEVELOPMENT.md - Development guide
- docs/JMX_FORMAT_REFERENCE.md - JMX structure reference

### Examples

- **Petstore API** (Swagger 2.0) - 20 endpoints
- **Simple CRUD API** (OpenAPI 3.0.3) - 7 endpoints

---

## [Unreleased]

### Planned Features

- CSV Data Set Config support
- Request body data generation with faker
- Authentication support (Bearer, Basic, API Key)
- Correlation (JSON/Regex extractors, variable usage)
- Advanced assertions (response time, JSON path)
- Custom JMX templates

## Links

- Documentation: [docs/](docs/)
- Examples: [examples/](examples/)
