# Alternatives Considered

This document records design alternatives that were evaluated and rejected, along with the reasoning.

---

## 1. Manual JSONPath (Rejected)

### Description
Require users to specify explicit JSONPath expressions for variable extraction.

### Example
```yaml
capture:
  - name: userId
    jsonpath: "$.data.user.id"
  - name: token
    jsonpath: "$.auth.accessToken"
```

### Why Rejected
- **Worse UX**: Requires users to know JSONPath syntax
- **Error-prone**: Easy to make typos in paths
- **Maintenance burden**: Paths break when API changes
- **Redundant**: OpenAPI spec already contains response schemas

### What We Chose Instead
Automatic correlation detection. Users write `capture: [userId]` and the tool determines the JSONPath from the OpenAPI response schema.

---

## 2. Custom DSL Instead of YAML (Rejected)

### Description
Create a custom domain-specific language for scenario definitions.

### Example
```
scenario "User CRUD"
  step "Create User"
    POST /users
    body { email: "test@example.com" }
    capture userId from response.id
  end

  step "Get User"
    GET /users/{userId}
    expect status 200
  end
end
```

### Why Rejected
- **Learning curve**: Users need to learn new syntax
- **Tooling**: No IDE support, syntax highlighting, validation
- **Standard deviation**: YAML is widely understood
- **Maintenance**: Custom parser more complex than YAML

### What We Chose Instead
YAML format with clear schema. YAML is:
- Well-known and documented
- Has IDE support (syntax highlighting, validation)
- Easy to parse with standard libraries
- Human-readable

---

## 3. Sequence Only Without Correlations (Rejected)

### Description
Implement only sequential step execution without automatic variable correlation.

### Example
```yaml
scenario:
  - endpoint: "createUser"
  - endpoint: "getUser"
  - endpoint: "deleteUser"
```

### Why Rejected
- **Too limited**: Most real scenarios need data from previous steps
- **Not differentiated**: Other tools already do simple sequencing
- **Core value**: Automatic correlation is the main innovation

### What We Chose Instead
Full correlation support with automatic JSONPath detection.

---

## 4. Session Recording / Proxy (Rejected - Out of Scope)

### Description
Implement a proxy server that records HTTP traffic and generates scenarios.

### Why Rejected
- **Separate tool scope**: Significantly different architecture
- **Complexity**: Proxy implementation, HTTPS interception, certificate handling
- **Maintenance**: Browser compatibility, mobile app support
- **Existing tools**: Fiddler, Charles, mitmproxy already do this well

### Recommendation
Use existing proxy tools for recording, then import captured traffic. This could be a future extension (import HAR files).

---

## 5. GUI Configuration Tool (Rejected for v2)

### Description
Build a visual editor for creating scenarios instead of YAML.

### Why Rejected for v2
- **Scope creep**: Would significantly delay v2 release
- **Separate project**: GUI is a different product category
- **CLI focus**: Current users prefer command-line tools
- **YAML works**: Text-based config integrates with version control

### Future Possibility
Could be a separate companion tool or VS Code extension in the future.

---

## 6. Full JMeter Feature Parity (Rejected)

### Description
Support all JMeter elements and configurations in pt_scenario.yaml.

### Example
```yaml
scenario:
  - name: "Step"
    jmeter:
      timers:
        - type: "GaussianRandomTimer"
          deviation: 100
          offset: 300
      preprocessors:
        - type: "JSR223PreProcessor"
          script: "..."
```

### Why Rejected
- **Complexity explosion**: JMeter has hundreds of elements
- **Diminishing returns**: Most users need only HTTP samplers
- **Maintenance burden**: Keep up with JMeter versions
- **Against philosophy**: We want simplicity, not full parity

### What We Chose Instead
Support common patterns well:
- HTTP samplers with variables
- JSON extraction
- Basic assertions
- Loops and conditions

For advanced cases, users can manually edit the generated JMX.

---

## 7. Real-Time Test Execution (Rejected)

### Description
Execute scenarios directly without JMeter, showing results in real-time.

### Why Rejected
- **Reinventing JMeter**: JMeter already does execution well
- **Feature scope**: Load testing execution is complex
- **Integration**: Users want JMeter compatibility for existing workflows
- **Reporting**: JMeter has mature reporting infrastructure

### What We Chose Instead
Generate high-quality JMX files that run in JMeter. Our value is in simplifying test creation, not execution.

---

## 8. OpenAPI-First Approach Only (Rejected)

### Description
Require OpenAPI spec for all scenarios, no standalone mode.

### Why Rejected
- **Flexibility**: Some users may want to define scenarios without OpenAPI
- **Legacy APIs**: Not all APIs have OpenAPI specs
- **Prototyping**: Quick tests before spec is finalized

### What We Chose Instead
OpenAPI is optional but recommended. When provided:
- Validates endpoint references
- Enables automatic correlation detection
- Provides request/response schema info

Without OpenAPI:
- Manual endpoint definitions
- Explicit JSONPath for captures
- Less validation
