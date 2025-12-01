# Quick Start Guide

Get started with JMeter Test Generator in 5 minutes.

## Installation

```bash
cd app
pip install -e .
```

## Verify Installation

```bash
jmeter-gen --version
# Output: jmeter-gen, version 3.0.0
```

## Basic Usage

### 1. Analyze Your Project

Navigate to your project directory:

```bash
cd /path/to/your/api/project
jmeter-gen analyze
```

Expected output:
```
Analyzing project: /path/to/your/api/project

OpenAPI Specification Found!

Location: /path/to/your/api/project/openapi.yaml
API Title: My API
Base URL: http://localhost:8080
Endpoints: 5

Available Endpoints:
Method | Path              | Operation ID
POST   | /api/users        | createUser
GET    | /api/users/{id}   | getUser
PUT    | /api/users/{id}   | updateUser
DELETE | /api/users/{id}   | deleteUser
GET    | /api/users        | listUsers

Recommended JMX name: my-api-test.jmx

To generate test:
  jmeter-gen generate
```

### 2. Generate JMX File

```bash
jmeter-gen generate
```

Expected output:
```
No spec provided, scanning project...
Found spec: ./openapi.yaml
Parsing OpenAPI spec...
API: My API v1.0.0
Base URL: http://localhost:8080
Endpoints: 5

Generating JMX file...

SUCCESS! JMeter test plan generated
Output: my-api-test.jmx
HTTP Samplers: 5
Assertions: 5

Configuration:
  Threads: 1
  Ramp-up: 0s
  Iterations: 1

To run the test:
  jmeter -n -t my-api-test.jmx -l results.jtl
```

### 3. Customize Configuration

Generate with custom load profile:

```bash
jmeter-gen generate \
  --threads 50 \
  --rampup 10 \
  --duration 300 \
  --output performance-test.jmx
```

Default values (for single-run testing):
- Threads: 1
- Ramp-up: 0 seconds
- Duration: None (uses 1 iteration per thread)

### 4. Validate Generated JMX

```bash
jmeter-gen validate performance-test.jmx
```

Expected output:
```
Validating JMX file: performance-test.jmx

VALID! JMX file is correct

Recommendations:
  • Consider adding CSV Data Set Config for test data
  • Add Response Time assertion for performance validation
```

### 5. Run Test in JMeter

```bash
# Headless mode
jmeter -n -t performance-test.jmx -l results.jtl

# GUI mode (for debugging)
jmeter
# Then: File → Open → performance-test.jmx
```

## Example: API Load Testing

```bash
# Navigate to your API project
cd /path/to/your/api/project

# Analyze
jmeter-gen analyze

# Generate with load test configuration
jmeter-gen generate \
  --spec openapi.yaml \
  --threads 50 \
  --rampup 10 \
  --duration 300 \
  --output api-load-test.jmx

# Validate
jmeter-gen validate api-load-test.jmx

# Run in JMeter
jmeter -n -t api-load-test.jmx -l results.jtl
```

## Scenario-Based Testing

For realistic user flows with variable correlation, create a `pt_scenario.yaml` file.

### Create Scenario with Wizard

```bash
jmeter-gen new scenario
```

The wizard guides you through:
1. Scenario name and description
2. Thread/ramp-up/duration settings
3. Endpoint selection from OpenAPI spec
4. Capture suggestions from response schema
5. Loop and think time configuration

### Example pt_scenario.yaml

```yaml
name: "User CRUD Flow"
description: "Create, read, update, delete user"

settings:
  threads: 10
  rampup: 5
  duration: 60

scenario:
  - name: "Create User"
    endpoint: "POST /users"
    payload:
      email: "test@example.com"
      password: "secret123"
    capture:
      - userId
    assert:
      status: 201

  - name: "Get User"
    endpoint: "GET /users/{userId}"
    params:
      userId: "${userId}"
    assert:
      status: 200

  - name: "Update User"
    endpoint: "PUT /users/{userId}"
    params:
      userId: "${userId}"
    payload:
      firstName: "Updated"
    assert:
      status: 200

  - name: "Delete User"
    endpoint: "DELETE /users/{userId}"
    params:
      userId: "${userId}"
    assert:
      status: 200
```

### Generate from Scenario

```bash
# Auto-detects pt_scenario.yaml in project
jmeter-gen generate

# Or specify explicitly
jmeter-gen generate --scenario pt_scenario.yaml
```

Output includes variable flow visualization:
```
Scenario: User CRUD Flow
========================

[1] Create User (POST /users)
    capture: userId
    assert: 201

[2] Get User (GET /users/{userId})
    uses: ${userId}
    assert: 200

Variable Flow:
  userId: [1] --> [2,3,4]
```

## MCP Server Mode (GitHub Copilot)

### 1. Configure VS Code

Add to `.vscode/settings.json`:

```json
{
  "github.copilot.chat.mcp.servers": {
    "jmeter-test-generator": {
      "command": "jmeter-gen",
      "args": ["mcp"]
    }
  }
}
```

### 2. Reload VS Code

Press `Ctrl+Shift+P` → "Developer: Reload Window"

### 3. Use in Copilot Chat

Open Copilot Chat and try:

```
"Generate JMeter test for this project"
"Create a performance test with 50 users for 5 minutes"
"Analyze this API and create JMeter test plan"
```

Copilot will:
1. Scan your project for OpenAPI spec
2. Generate JMX file with appropriate configuration
3. Provide instructions for running the test

## CLI Commands Reference

```bash
# Analyze project
jmeter-gen analyze [--project-path PATH]

# Generate JMX
jmeter-gen generate [OPTIONS]
  --spec PATH           Path to OpenAPI spec
  --scenario PATH       Path to pt_scenario.yaml file
  --output, -o PATH     Output JMX file
  --threads, -t INT     Number of threads (default: 1)
  --rampup, -r INT      Ramp-up period in seconds (default: 0)
  --duration, -d INT    Test duration in seconds (default: None - iteration-based)
  --endpoints, -e TEXT  Specific endpoints to include (can be repeated)
  --base-url URL        Override base URL from spec

# Create new scenario (interactive wizard)
jmeter-gen new scenario [OPTIONS]
  --spec PATH           Path to OpenAPI spec (auto-detected if not provided)
  --output, -o NAME     Output filename (default: pt_scenario.yaml)

# Validate JMX
jmeter-gen validate JMX_PATH

# Start MCP Server
jmeter-gen mcp

# Show help
jmeter-gen --help
jmeter-gen COMMAND --help
```

## Common Issues

### Issue: "No OpenAPI spec found"

**Solution**: Make sure your project has one of these files:
- openapi.yaml / openapi.yml
- openapi.json
- swagger.yaml / swagger.yml
- swagger.json
- api.yaml / api.json

The tool searches recursively up to 3 levels deep. Alternatively, specify the path explicitly:
```bash
jmeter-gen generate --spec path/to/your/spec.yaml
```

### Issue: "Unsupported OpenAPI version"

**Solution**: Currently supported versions:
- OpenAPI 3.x (3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.1.0, etc.)
- Swagger 2.0

Older versions are not supported.

### Issue: "JMeter can't load the JMX file"

**Solution**: Validate the JMX first:
```bash
jmeter-gen validate your-test.jmx
```

Common causes:
- Invalid XML structure
- Missing required elements
- Encoding issues (ensure UTF-8)

### Issue: "MCP Server not found in Copilot"

**Solution**:
1. Make sure jmeter-gen is installed: `which jmeter-gen` or `jmeter-gen --version`
2. Check VS Code settings.json has correct MCP configuration
3. Reload VS Code: Ctrl+Shift+P → "Developer: Reload Window"
4. Check Copilot extension is up to date

### Issue: "Base URL incorrect in generated JMX"

**Solution**: Override the base URL during generation:
```bash
jmeter-gen generate --spec openapi.yaml --base-url https://api.production.com
```

Or update the HTTP Request Defaults element in the generated JMX file.

## Current Capabilities

**Supported:**
- OpenAPI 3.x and Swagger 2.0 specifications
- Scenario-based sequential test flows
- Variable capture and correlation
- Loop constructs (count-based and while-condition)
- Think time between steps
- Custom payloads and assertions
- Interactive scenario wizard

**Limitations:**
- No built-in authentication helpers (Bearer, API keys, Basic Auth)
- No CSV Data Set Config for external test data
- No Faker/random data generation
- Status code and body assertions only (no response time assertions)

## Next Steps

1. Read [Scenario Specification](docs/v2/PT_SCENARIO_SPEC.md) for pt_scenario.yaml format
2. Check [examples/](examples/) for working examples
3. Review [CHANGELOG.md](CHANGELOG.md) for version history

## Getting Help

- Check the [examples/](examples/) directory for working examples
- Read the [Development Guide](docs/DEVELOPMENT.md) for detailed documentation
- Review [CHANGELOG.md](CHANGELOG.md) for version history and roadmap

## License

MIT License - see LICENSE file for details
