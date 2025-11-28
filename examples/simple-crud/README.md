# Simple CRUD API Example

This example demonstrates JMeter Test Generator with a simple REST API using OpenAPI 3.0.

## Overview

- **API**: Simple CRUD API v1.0.0
- **Spec Type**: OpenAPI 3.0.3
- **Base URL**: http://localhost:8080 (default)
- **Endpoints**: 7 HTTP endpoints
- **Operations**: User management with CRUD operations

## Files

- `openapi.yaml` - OpenAPI 3.0.3 specification
- `simple-crud-test.jmx` - Generated JMeter test plan
- `README.md` - This file

## Endpoints Included

### User Operations (7 endpoints)

1. **GET /users** - List all users
   - Query parameters: page, limit
   - Returns paginated user list

2. **POST /users** - Create a new user
   - Request body: UserCreate (email, firstName, lastName, password)
   - Returns created user with ID

3. **GET /users/{userId}** - Get user by ID
   - Path parameter: userId
   - Returns detailed user information

4. **PUT /users/{userId}** - Update user
   - Path parameter: userId
   - Request body: UserUpdate (email, firstName, lastName)
   - Returns updated user

5. **DELETE /users/{userId}** - Delete user
   - Path parameter: userId
   - Returns success confirmation

6. **GET /users/{userId}/profile** - Get user profile
   - Path parameter: userId
   - Returns profile information (bio, avatar, website)

7. **PATCH /users/{userId}/profile** - Update user profile
   - Path parameter: userId
   - Request body: Profile fields (bio, avatar, website)
   - Returns updated profile

## Generate JMX File

### Basic Generation

From the examples/simple-crud directory:

```bash
# Simple - auto-detects spec, generates simple-crud-api-test.jmx
jmeter-gen generate

# Or with explicit base URL
jmeter-gen generate --base-url http://localhost:8080
```

### Production Environment

Generate for production API:

```bash
jmeter-gen generate \
  --spec openapi.yaml \
  --output simple-crud-production.jmx \
  --base-url https://api.example.com
```

### Load Testing Configuration

Generate with load testing profile:

```bash
jmeter-gen generate \
  --spec openapi.yaml \
  --output simple-crud-load-test.jmx \
  --threads 20 \
  --rampup 10 \
  --duration 120 \
  --base-url http://localhost:8080
```

### Filter Specific Operations

Generate only specific endpoints:

```bash
jmeter-gen generate \
  --spec openapi.yaml \
  --output simple-crud-read-only.jmx \
  --endpoints listUsers \
  --endpoints getUser \
  --endpoints getUserProfile \
  --base-url http://localhost:8080
```

## Run Tests in JMeter

### Prerequisites

Before running the test, ensure your API server is running:

```bash
# Start your API server on localhost:8080
# Example with a typical Node.js/Express app:
npm start

# Or Python Flask:
python app.py

# Or any other framework
```

### GUI Mode (for development)

```bash
jmeter -t simple-crud-test.jmx
```

Or:
1. Open JMeter GUI: `jmeter`
2. File -> Open -> `simple-crud-test.jmx`
3. Click the green "Start" button
4. View results in "View Results Tree" or "Aggregate Report"

### Headless Mode (for CI/CD)

```bash
jmeter -n -t simple-crud-test.jmx -l results.jtl
```

Generate HTML report:

```bash
jmeter -n -t simple-crud-test.jmx -l results.jtl -e -o report/
open report/index.html
```

## Validate Generated JMX

```bash
jmeter-gen validate simple-crud-test.jmx
```

Expected output:
```
Validating JMX file: simple-crud-test.jmx

VALID! JMX file structure is correct

Recommendations:
  • Consider adding Response Time assertions
  • Add CSV Data Set Config for test data
```

## Test Plan Structure

The generated JMX file includes:

1. **Test Plan** - Root element with metadata
2. **HTTP Request Defaults**
   - Domain: localhost
   - Port: 8080
   - Protocol: http
3. **View Results Tree** - Listener for response inspection
4. **Aggregate Report** - Listener for performance metrics
5. **Thread Group** - Load configuration
   - 1 thread (virtual user)
   - 0s ramp-up
   - 1 iteration
6. **HTTP Samplers** - 7 samplers (one per endpoint)
   - GET /users
   - POST /users
   - GET /users/{userId}
   - PUT /users/{userId}
   - DELETE /users/{userId}
   - GET /users/{userId}/profile
   - PATCH /users/{userId}/profile
7. **Header Managers** - Content-Type: application/json for POST/PUT/PATCH
8. **Response Assertions** - Status code validation (200/201)

## Sample Request Bodies

The generated test uses minimal sample data:

### POST /users (Create User)
```json
{
  "email": "user@example.com",
  "firstName": "Sample",
  "lastName": "User",
  "password": "password123"
}
```

### PUT /users/{userId} (Update User)
```json
{
  "email": "user@example.com",
  "firstName": "Sample",
  "lastName": "User"
}
```

### PATCH /users/{userId}/profile (Update Profile)
```json
{
  "bio": "Sample bio text",
  "avatar": "https://example.com/avatar.jpg",
  "website": "https://example.com"
}
```

## Customization

### Add Test Data

Create a CSV file `users.csv`:
```csv
userId,email,firstName,lastName
1,john@example.com,John,Doe
2,jane@example.com,Jane,Smith
3,bob@example.com,Bob,Johnson
```

In JMeter GUI:
1. Right-click Thread Group -> Add -> Config Element -> CSV Data Set Config
2. Set filename: `users.csv`
3. Set variable names: `userId,email,firstName,lastName`
4. Update HTTP Samplers to use `${userId}`, `${email}`, etc.

### Add Response Time Assertions

1. Right-click HTTP Sampler -> Add -> Assertions -> Duration Assertion
2. Set duration: 1000 (milliseconds)
3. This will fail if response takes longer than 1 second

### Add Timers

Simulate real user behavior with delays:

1. Right-click Thread Group -> Add -> Timer -> Constant Timer
2. Set delay: 1000 (milliseconds between requests)

### Environment Variables

Switch between environments without regenerating JMX:

1. Open JMX in JMeter GUI
2. Find "HTTP Request Defaults"
3. Change domain/port/protocol
4. Save the file

Or use User Defined Variables for dynamic configuration.

## Expected Results

When running against a mock server:

- **Success scenario**: All 7 requests return 200/201
- **Partial success**: Some 404s for non-existent users (e.g., userId=123)
- **Total execution time**: <1 second for single iteration

When running load test (20 threads, 2 minutes):

- **Throughput**: 100-500 req/sec (depends on server)
- **Response time**: <100ms (localhost), <500ms (production)
- **Error rate**: Should be <1%

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Load Test

on:
  push:
    branches: [main]

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Start API server
        run: |
          npm install
          npm start &
          sleep 5

      - name: Install JMeter
        run: |
          wget https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-5.6.2.tgz
          tar -xzf apache-jmeter-5.6.2.tgz

      - name: Run load test
        run: |
          apache-jmeter-5.6.2/bin/jmeter -n \
            -t examples/simple-crud/simple-crud-test.jmx \
            -l results.jtl \
            -e -o report/

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: jmeter-results
          path: report/
```

## Troubleshooting

### Connection Refused

**Problem**: JMeter shows "Connection refused" errors

**Solution**:
- Verify API server is running: `curl http://localhost:8080/users`
- Check port number matches (8080)
- Update HTTP Request Defaults if using different port

### 404 Not Found

**Problem**: All requests return 404

**Solution**:
- Verify API endpoints match the spec
- Check base path (some APIs use /api/v1 prefix)
- Update paths in JMeter if needed

### Invalid JSON

**Problem**: Server returns 400 Bad Request

**Solution**:
- Check request body format in HTTP Sampler
- Verify Content-Type header is set to application/json
- Update sample data to match your API's validation rules

## Resources

- OpenAPI Specification: https://swagger.io/specification/
- JMeter Documentation: https://jmeter.apache.org/usermanual/index.html
- REST API Testing: https://www.blazemeter.com/blog/rest-api-testing-jmeter
