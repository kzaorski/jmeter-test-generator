# Changelog

All notable changes to the JMeter Test Generator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
