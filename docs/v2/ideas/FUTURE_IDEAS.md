# Future Ideas

This document contains detailed specifications for planned extensions. See [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) for the prioritized backlog.

---

## P3 Extensions - Detailed Specifications

### Postman/Insomnia Import

**Priority**: P3 - Lower

**Description**: Import existing Postman collections or Insomnia workspaces and convert them to pt_scenario.yaml format.

**Use Cases**:
- Teams with existing Postman collections
- Migration from manual API testing to performance testing
- Reuse of existing request definitions

**Technical Approach**:
- Parse Postman Collection v2.1 JSON format
- Parse Insomnia export format
- Map requests to scenario steps
- Convert environment variables to scenario variables
- Detect potential correlations from collection structure

**CLI**:
```bash
jmeter-gen scenario import postman collection.json --output scenario.yaml
jmeter-gen scenario import insomnia workspace.json --output scenario.yaml
```

---

### Data-Driven Testing (CSV Integration)

**Priority**: P3 - Lower

**Description**: Support CSV data files for parameterized testing.

**Example**:
```yaml
scenario:
  - name: "Create Users"
    endpoint: "createUser"
    data_source: "users.csv"  # CSV with email, firstName, lastName columns
    payload:
      email: "${__CSV_email}"
      firstName: "${__CSV_firstName}"
      lastName: "${__CSV_lastName}"
```

**JMX Output**: Generate CSV Data Set Config element.

---

### Multiple Scenarios (Thread Groups)

**Priority**: P3 - Lower

**Description**: Support multiple independent scenarios in one file, each becoming a separate Thread Group.

**Example**:
```yaml
version: "1.0"
name: "Full API Test"

scenarios:
  - name: "User Flow"
    threads: 10
    scenario:
      - name: "Create User"
        # ...

  - name: "Product Flow"
    threads: 5
    scenario:
      - name: "List Products"
        # ...
```

---

### Authentication Helpers

**Priority**: P3 - Lower

**Description**: Built-in support for common authentication patterns.

**Concepts**:
```yaml
auth:
  type: "bearer"
  token_endpoint: "loginUser"
  token_path: "$.token"
  refresh_on: 401
  header: "Authorization"
  prefix: "Bearer "
```

This would automatically:
1. Call token endpoint at start
2. Extract token to variable
3. Add header to all subsequent requests
4. Refresh token on 401 responses

---

### Data Generation (Faker Integration)

**Priority**: P3 - Lower

**Description**: Generate realistic test data using Faker library.

**Example**:
```yaml
payload:
  email: "${__faker:email}"
  firstName: "${__faker:firstName}"
  phone: "${__faker:phoneNumber}"
  address:
    street: "${__faker:streetAddress}"
    city: "${__faker:city}"
```

---

### Assertions Library

**Priority**: P3 - Lower

**Description**: More assertion types beyond status code and body fields.

**Concepts**:
```yaml
assert:
  status: 200
  response_time: "<2000ms"
  body:
    items:
      length: ">0"
      contains: "expected-id"
    total:
      type: "number"
      range: [0, 1000]
  headers:
    Content-Type: "application/json"
```

---

### Scenario Composition

**Priority**: P3 - Lower

**Description**: Reuse common step sequences across scenarios.

**Example**:
```yaml
# common/login.yaml
steps:
  - name: "Login"
    endpoint: "loginUser"
    payload:
      email: "${email}"
      password: "${password}"
    capture:
      - token

# main scenario
scenario:
  - include: "common/login.yaml"
    variables:
      email: "admin@example.com"
      password: "secret"

  - name: "Admin Operation"
    endpoint: "adminAction"
    # ...
```

---

### GraphQL Support

**Priority**: P3 - Lower

**Description**: Extend beyond REST to support GraphQL APIs.

**Considerations**:
- GraphQL introspection instead of OpenAPI
- Query/mutation definitions in scenarios
- Variable extraction from GraphQL responses

---

## Rejected Ideas

See [ALTERNATIVES_CONSIDERED.md](ALTERNATIVES_CONSIDERED.md) for ideas that were evaluated and rejected.
