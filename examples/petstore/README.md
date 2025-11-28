# Petstore API Example

This example demonstrates JMeter Test Generator with the classic Swagger Petstore API (Swagger 2.0).

## Overview

- **API**: Swagger Petstore v1.0.7
- **Spec Type**: Swagger 2.0
- **Base URL**: https://petstore.swagger.io
- **Endpoints**: 20 HTTP endpoints
- **Operations**: Pet, Store, and User management

## Files

- `swagger.json` - Swagger 2.0 specification
- `petstore-test.jmx` - Generated JMeter test plan
- `README.md` - This file

## Endpoints Included

### Pet Operations (10 endpoints)
- POST /pet - Add a new pet
- PUT /pet - Update existing pet
- GET /pet/findByStatus - Find pets by status
- GET /pet/findByTags - Find pets by tags
- GET /pet/{petId} - Find pet by ID
- POST /pet/{petId} - Update pet with form data
- DELETE /pet/{petId} - Delete pet
- POST /pet/{petId}/uploadImage - Upload pet image

### Store Operations (4 endpoints)
- GET /store/inventory - Get inventory
- POST /store/order - Place order
- GET /store/order/{orderId} - Get order by ID
- DELETE /store/order/{orderId} - Delete order

### User Operations (6 endpoints)
- POST /user - Create user
- POST /user/createWithList - Create users with list
- GET /user/login - Login user
- GET /user/logout - Logout user
- GET /user/{username} - Get user by name
- PUT /user/{username} - Update user
- DELETE /user/{username} - Delete user

## Generate JMX File

### Basic Generation

From the examples/petstore directory:

```bash
# Simple - auto-detects spec, generates swagger-petstore-test.jmx
jmeter-gen generate --base-url https://petstore.swagger.io

# Or with explicit spec path
jmeter-gen generate --spec swagger.json --base-url https://petstore.swagger.io
```

### Custom Load Profile

Generate with custom thread configuration:

```bash
jmeter-gen generate \
  --spec swagger.json \
  --output petstore-load-test.jmx \
  --threads 10 \
  --rampup 5 \
  --duration 60 \
  --base-url https://petstore.swagger.io
```

### Filter Specific Endpoints

Generate only specific operations:

```bash
jmeter-gen generate \
  --spec swagger.json \
  --output petstore-pets-only.jmx \
  --endpoints addPet \
  --endpoints getPetById \
  --endpoints updatePet \
  --base-url https://petstore.swagger.io
```

## Run Tests in JMeter

### GUI Mode (for development)

```bash
jmeter -t petstore-test.jmx
```

Or:
1. Open JMeter GUI: `jmeter`
2. File -> Open -> `petstore-test.jmx`
3. Click the green "Start" button

### Headless Mode (for CI/CD)

```bash
jmeter -n -t petstore-test.jmx -l results.jtl
```

Generate HTML report:

```bash
jmeter -n -t petstore-test.jmx -l results.jtl -e -o report/
```

## Validate Generated JMX

```bash
jmeter-gen validate petstore-test.jmx
```

Expected output:
```
Validating JMX file: petstore-test.jmx

VALID! JMX file structure is correct

Recommendations:
  • Consider adding Response Time assertions
  • Add CSV Data Set Config for test data
```

## Test Plan Structure

The generated JMX file includes:

1. **Test Plan** - Root element with metadata
2. **HTTP Request Defaults** - Base URL configuration (https://petstore.swagger.io)
3. **View Results Tree** - Listener for response inspection
4. **Aggregate Report** - Listener for performance metrics
5. **Thread Group** - Load configuration (1 thread, 0s ramp-up, 1 iteration)
6. **HTTP Samplers** - 20 samplers (one per endpoint)
   - GET /pet/findByStatus
   - POST /pet
   - PUT /pet
   - DELETE /pet/{petId}
   - etc.
7. **Header Managers** - Content-Type headers for POST/PUT requests
8. **Response Assertions** - Status code validation (200/201)

## Notes

- **Authentication**: Petstore API doesn't require authentication
- **Request Bodies**: POST/PUT requests use minimal sample data
- **Path Parameters**: Static values (e.g., petId=123)
- **Query Parameters**: Default values from spec
- **Base URL**: Uses HTTPS (https://petstore.swagger.io)

## Expected Results

When running the test, you should see:

- 20 HTTP requests executed
- Most requests return 200/201 status codes
- Some requests may fail with 404 (e.g., GET /pet/{petId} with non-existent ID)
- Total execution time: ~5-10 seconds (depends on network)

## Customization

To customize the test:

1. **Change base URL**: Update HTTP Request Defaults in JMeter GUI
2. **Add test data**: Create CSV file and add CSV Data Set Config
3. **Add assertions**: Right-click sampler -> Add -> Assertions
4. **Add timers**: Add Constant Timer or Gaussian Random Timer
5. **Add authentication**: Add HTTP Header Manager with API key

## Resources

- Petstore API Docs: https://petstore.swagger.io
- Swagger Spec: https://github.com/swagger-api/swagger-petstore
- JMeter Docs: https://jmeter.apache.org/usermanual/index.html
