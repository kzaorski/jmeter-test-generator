# Plan: CI/CD Integration v3.4.0

**Status:** Implemented

## Summary

Added CI/CD integration features to jmeter-gen for use in Azure DevOps, GitHub Actions, and other pipelines.

## New Features

### 1. `--scenario PATH` flag
Explicit path to pt_scenario.yaml file, overriding auto-discovery.

```bash
jmeter-gen generate \
  --spec ./api/openapi.yaml \
  --scenario ./scenarios/login-flow.yaml \
  --output test.jmx
```

### 2. `--spec URL` support
Download OpenAPI spec from HTTP/HTTPS URL.

```bash
jmeter-gen generate \
  --spec https://api.example.com/swagger.json \
  --output test.jmx
```

### 3. `--insecure` flag
Skip SSL verification when downloading spec from URL.

```bash
jmeter-gen generate \
  --spec https://self-signed.example.com/swagger.json \
  --output test.jmx \
  --insecure
```

### 4. CI environment auto-detection
Automatically detects CI environment and disables colors/prompts.

Detected variables:
- `CI`
- `GITHUB_ACTIONS`
- `GITLAB_CI`
- `JENKINS_URL`
- `TF_BUILD` (Azure DevOps)
- `BUILDKITE`
- `CIRCLECI`
- `TRAVIS`

## Usage in Azure DevOps

```yaml
- script: |
    pip install jmeter-test-generator
    jmeter-gen generate \
      --spec $(SWAGGER_URL) \
      --scenario pipeline/loadtest/pt_scenario.yaml \
      --output $(Build.ArtifactStagingDirectory)/test.jmx \
      --base-url $(API_BASE_URL) \
      --insecure
  displayName: 'Generate JMeter test plan'
```

## Usage in GitHub Actions

```yaml
- name: Generate JMeter test
  run: |
    pip install jmeter-test-generator
    jmeter-gen generate \
      --spec ${{ secrets.SWAGGER_URL }} \
      --scenario ./scenarios/performance.yaml \
      --output ./test.jmx \
      --base-url ${{ vars.API_URL }}
```

## Implementation Details

### Files Modified
- `jmeter_gen/cli.py` - New flags and CI detection
- `tests/test_cli.py` - 9 new tests
- `pyproject.toml` - Version bump to 3.4.0
- `README.md` - CI/CD Integration section
- `CLAUDE.md` - CI/CD Integration section

### Functions Added
- `_is_ci_environment()` - Detect CI environment
- `_resolve_spec_path()` - Download spec from URL if needed

### Backward Compatibility
All changes are additive. Existing usage without new flags works unchanged.
