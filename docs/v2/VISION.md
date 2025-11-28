# JMeter Test Generator v2 - Vision

## The Problem

JMeter Test Generator v1 generates JMX files from OpenAPI specifications. While useful, the generated tests are essentially a **"dead endpoint catalog"** - a flat list of HTTP samplers that execute in no particular order with no data dependencies.

### What's Missing in v1

1. **No Sequence**: Real user flows have order - login first, then operations
2. **No Correlations**: Token from login should flow to subsequent requests
3. **No Realistic Data**: Payloads are empty or contain placeholder values
4. **No User Journey**: Tests don't represent actual user behavior

### The Result

Generated JMX files require significant manual work to be useful for performance testing.

---

## The Solution: pt_scenario.yaml

Version 2 introduces **scenario-based test generation**:

```yaml
scenario:
  - name: "Login"
    endpoint: "loginUser"
    payload:
      email: "test@example.com"
      password: "secret"
    capture:
      - token

  - name: "Get Profile"
    endpoint: "getUserProfile"
    headers:
      Authorization: "Bearer ${token}"
```

### Key Capabilities

1. **Sequential Steps**: Define ordered test flows
2. **Automatic Correlation**: Tool detects and creates variable extractors
3. **User-Defined Payloads**: Full control over request data
4. **Visual Feedback**: See your scenario flow before generating JMX

---

## Unique Selling Point: Automatic Correlation Detection

Most tools require users to manually specify JSONPath expressions:

```yaml
# Other tools - manual JSONPath
capture:
  - name: userId
    jsonpath: "$.data.user.id"
```

JMeter Test Generator v2 **automatically detects** the correct JSONPath:

```yaml
# JMeter Test Generator v2 - automatic
capture:
  - userId    # Tool figures out $.id from OpenAPI response schema
```

### How It Works

1. Parse OpenAPI response schema for the endpoint
2. Build index of all response fields with their paths
3. Match capture variable name to schema fields
4. Generate JSONPath automatically

This significantly reduces manual effort and error-prone JSONPath writing.

---

## Target Users

### Primary: QA Engineers
- Need to create performance tests quickly
- Have OpenAPI specs available
- Want realistic user flow testing

### Secondary: Developers
- Testing API performance during development
- CI/CD pipeline integration
- Quick smoke tests

### Use Cases

1. **API Performance Testing**: Load test REST APIs with realistic flows
2. **Integration Testing**: Verify API sequences work correctly
3. **Regression Testing**: Automated performance baseline checks
4. **Load Testing**: Simulate real user behavior at scale

---

## Roadmap

### v2.0.0 - Scenario-Based Test Generation (Current)
- Parse pt_scenario.yaml (support both operationId and METHOD /path formats)
- Validate against OpenAPI spec
- Visualize scenario flow (Rich terminal output)
- Generate scenario-based JMX files
- Extend existing CLI commands (analyze, generate)
- Full backward compatibility with v1

### Future Extensions

See [../BACKLOG.md](../BACKLOG.md) for the consolidated prioritized backlog.

---

## Backward Compatibility

v2 is fully backward compatible with v1:

- All v1 commands continue to work exactly as before
- Existing workflows are unchanged
- v2 features are additive - existing commands are extended, not replaced
- When no `pt_scenario.yaml` exists, v1 behavior is preserved

Users can adopt v2 features incrementally by simply adding a scenario file to their project.

---

## Success Metrics

1. **Reduced Manual Work**: 80% less time to create realistic test scenarios
2. **Correlation Accuracy**: >80% auto-detection success rate
3. **User Adoption**: Positive feedback on scenario visualization
4. **JMX Quality**: Generated tests run without modification in JMeter
