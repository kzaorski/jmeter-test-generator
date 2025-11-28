# JMX File Format Reference

This document provides a comprehensive analysis of the JMeter JMX file format based on official Apache JMeter documentation and current implementation practices (2025).

## Overview

A JMX file is a saved JMeter test plan in XML format. JMeter uses XStream for serialization, creating an XML structure that represents the entire test configuration. The mapping between XML node names (like `<hashTree>` or `<TestPlan>`) and the actual Java class names is managed through `saveservice.properties`.

**Key Characteristics:**
- XML-encoded format
- Hierarchical structure using `<hashTree>` elements
- Multiple property types for different data types
- Can be created programmatically using any XML API
- Version-dependent format (current modern format differs from legacy versions)

## Root Structure

Every JMX file starts with the `<jmeterTestPlan>` root element:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6">
  <hashTree>
    <!-- Test plan contents -->
  </hashTree>
</jmeterTestPlan>
```

**Attributes:**
- `version`: JMX format version (typically "1.2")
- `properties`: Properties version (e.g., "5.0")
- `jmeter`: JMeter version that created the file (e.g., "5.6")

## HashTree Structure

The `<hashTree>` element is fundamental to JMX organization. It represents parent-child relationships and creates the hierarchical test plan structure.

**Pattern:**
```xml
<TestElement>
  <!-- Element properties -->
</TestElement>
<hashTree>
  <!-- Child elements -->
  <ChildElement>
    <!-- Child properties -->
  </ChildElement>
  <hashTree>
    <!-- Grandchild elements -->
  </hashTree>
</hashTree>
```

**Hierarchy Example:**
```
<jmeterTestPlan>
  <hashTree>
    <TestPlan>          → Test Plan configuration
    <hashTree>
      <ThreadGroup>     → Thread Group configuration
      <hashTree>
        <HTTPSampler>   → HTTP Request sampler
        <hashTree>
          <ResponseAssertion>  → Assertion for the sampler
          <hashTree/>          → Empty (no children)
        </hashTree>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
```

**Key Rules:**
- Every test element is followed by a `<hashTree>` containing its children
- Leaf elements (with no children) have an empty `<hashTree/>`
- The structure is both hierarchical and ordered

## Test Element Structure

All test elements (TestPlan, ThreadGroup, HTTPSampler, etc.) share a common attribute pattern:

```xml
<ElementName
  guiclass="GUIClassName"
  testclass="TestClassName"
  testname="Display Name"
  enabled="true">
  <!-- Properties -->
</ElementName>
```

**Common Attributes:**
- `guiclass`: GUI class for the JMeter UI (e.g., "TestPlanGui", "ThreadGroupGui")
- `testclass`: Test element class name (e.g., "TestPlan", "ThreadGroup")
- `testname`: Display name shown in JMeter GUI
- `enabled`: Boolean indicating if element is enabled ("true" or "false")

## Property Types

JMX uses multiple property element types to store different data types:

### 1. stringProp
Stores string values.

```xml
<stringProp name="PropertyName">value</stringProp>
```

**Examples:**
```xml
<stringProp name="HTTPSampler.domain">localhost</stringProp>
<stringProp name="HTTPSampler.port">8080</stringProp>
<stringProp name="HTTPSampler.protocol">http</stringProp>
<stringProp name="HTTPSampler.path">/api/users</stringProp>
<stringProp name="HTTPSampler.method">POST</stringProp>
<stringProp name="ThreadGroup.num_threads">10</stringProp>
<stringProp name="ThreadGroup.ramp_time">5</stringProp>
```

### 2. boolProp
Stores boolean values ("true" or "false").

```xml
<boolProp name="PropertyName">true</boolProp>
```

**Examples:**
```xml
<boolProp name="TestPlan.functional_mode">false</boolProp>
<boolProp name="TestPlan.serialize_threadgroups">false</boolProp>
<boolProp name="HTTPSampler.follow_redirects">true</boolProp>
<boolProp name="HTTPSampler.use_keepalive">true</boolProp>
<boolProp name="ThreadGroup.scheduler">true</boolProp>
<boolProp name="LoopController.continue_forever">false</boolProp>
```

### 3. intProp
Stores integer values.

```xml
<intProp name="PropertyName">42</intProp>
```

**Examples:**
```xml
<intProp name="LoopController.loops">1</intProp>
<intProp name="Assertion.test_type">8</intProp>
```

### 4. longProp
Stores long integer values (for large numbers or timestamps).

```xml
<longProp name="PropertyName">1234567890</longProp>
```

### 5. elementProp
Stores complex nested properties (like Arguments, Headers, etc.).

```xml
<elementProp name="PropertyName" elementType="ElementType">
  <!-- Nested properties -->
</elementProp>
```

**Example - Arguments:**
```xml
<elementProp name="HTTPsampler.Arguments" elementType="Arguments">
  <collectionProp name="Arguments.arguments">
    <elementProp name="userId" elementType="HTTPArgument">
      <boolProp name="HTTPArgument.always_encode">false</boolProp>
      <stringProp name="Argument.name">userId</stringProp>
      <stringProp name="Argument.value">123</stringProp>
      <stringProp name="Argument.metadata">=</stringProp>
      <boolProp name="HTTPArgument.use_equals">true</boolProp>
    </elementProp>
  </collectionProp>
</elementProp>
```

**Example - Loop Controller:**
```xml
<elementProp name="ThreadGroup.main_controller" elementType="LoopController">
  <boolProp name="LoopController.continue_forever">false</boolProp>
  <stringProp name="LoopController.loops">1</stringProp>
</elementProp>
```

### 6. collectionProp
Stores collections of properties (arrays/lists).

```xml
<collectionProp name="PropertyName">
  <stringProp name="item1">value1</stringProp>
  <stringProp name="item2">value2</stringProp>
</collectionProp>
```

**Example - Assertion Test Strings:**
```xml
<collectionProp name="Asserion.test_strings">
  <stringProp name="49586">200</stringProp>
  <stringProp name="49587">201</stringProp>
</collectionProp>
```

## Core Test Elements

### TestPlan

The root test element containing global test configuration.

```xml
<TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="My Test Plan" enabled="true">
  <stringProp name="TestPlan.comments">Test plan description</stringProp>
  <boolProp name="TestPlan.functional_mode">false</boolProp>
  <boolProp name="TestPlan.serialize_threadgroups">false</boolProp>
  <elementProp name="TestPlan.user_defined_variables" elementType="Arguments">
    <collectionProp name="Arguments.arguments"/>
  </elementProp>
  <stringProp name="TestPlan.user_define_classpath"></stringProp>
</TestPlan>
```

**Key Properties:**
- `TestPlan.comments`: Comments/description
- `TestPlan.functional_mode`: If true, saves response data (not for load testing)
- `TestPlan.serialize_threadgroups`: Run thread groups sequentially
- `TestPlan.user_defined_variables`: User-defined variables

### ThreadGroup

Defines the load profile (number of users, ramp-up, duration).

```xml
<ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group" enabled="true">
  <stringProp name="ThreadGroup.on_sample_error">continue</stringProp>
  <elementProp name="ThreadGroup.main_controller" elementType="LoopController">
    <boolProp name="LoopController.continue_forever">false</boolProp>
    <stringProp name="LoopController.loops">1</stringProp>
  </elementProp>
  <stringProp name="ThreadGroup.num_threads">10</stringProp>
  <stringProp name="ThreadGroup.ramp_time">5</stringProp>
  <boolProp name="ThreadGroup.scheduler">true</boolProp>
  <stringProp name="ThreadGroup.duration">60</stringProp>
  <stringProp name="ThreadGroup.delay">0</stringProp>
</ThreadGroup>
```

**Key Properties:**
- `ThreadGroup.num_threads`: Number of virtual users/threads
- `ThreadGroup.ramp_time`: Time (seconds) to reach full thread count
- `ThreadGroup.scheduler`: Enable scheduler for duration-based tests
- `ThreadGroup.duration`: Test duration in seconds (when scheduler enabled)
- `ThreadGroup.delay`: Startup delay in seconds
- `ThreadGroup.on_sample_error`: Action on sampler error (continue/startnextloop/stopthread/stoptest)
- `ThreadGroup.main_controller`: Loop controller configuration

**Thread Group Parameters Explained:**
- **num_threads**: Simulates concurrent users or connections (e.g., 100 users)
- **ramp_time**: Gradual increase period (e.g., 100 seconds to add all 100 threads)
- **scheduler**: When enabled, allows duration-based testing
- **duration**: Total test execution time (e.g., 60 seconds)

### ConfigTestElement (HTTP Request Defaults)

**IMPORTANT**: Use HTTP Request Defaults to centralize server configuration. This allows users to override the base URL for different environments (dev/staging/prod) without modifying individual samplers.

```xml
<ConfigTestElement guiclass="HttpDefaultsGui" testclass="ConfigTestElement" testname="HTTP Request Defaults" enabled="true">
  <elementProp name="HTTPsampler.Arguments" elementType="Arguments" guiclass="HTTPArgumentsPanel" testclass="Arguments" enabled="true">
    <collectionProp name="Arguments.arguments"/>
  </elementProp>
  <stringProp name="HTTPSampler.domain">localhost</stringProp>
  <stringProp name="HTTPSampler.port">8080</stringProp>
  <stringProp name="HTTPSampler.protocol">http</stringProp>
  <stringProp name="HTTPSampler.contentEncoding">UTF-8</stringProp>
  <stringProp name="HTTPSampler.path"></stringProp>
  <stringProp name="HTTPSampler.concurrentPool">6</stringProp>
  <stringProp name="HTTPSampler.connect_timeout"></stringProp>
  <stringProp name="HTTPSampler.response_timeout"></stringProp>
</ConfigTestElement>
```

**Key Properties:**
- `HTTPSampler.domain`: Default server hostname or IP (applied to all samplers)
- `HTTPSampler.port`: Default port number (e.g., 80, 443, 8080)
- `HTTPSampler.protocol`: Default protocol (http or https)
- `HTTPSampler.contentEncoding`: Default character encoding (e.g., UTF-8)
- `HTTPSampler.path`: Base path prefix (usually empty)
- `HTTPSampler.concurrentPool`: Connection pool size (default: 6)

**Hierarchy:** HTTP Request Defaults should be added as a child of TestPlan, BEFORE ThreadGroups. This allows configuration to apply globally to all ThreadGroups in the test plan, enabling environment-specific testing without modifying individual ThreadGroups.

**TestPlan vs ThreadGroup Level:**
- **TestPlan Level (Recommended):** HTTP Request Defaults applies to ALL ThreadGroups in the test plan. Use this for multi-threaded scenarios or when you want to override the base URL for the entire test plan without editing individual ThreadGroups.
- **ThreadGroup Level:** HTTP Request Defaults applies only to samplers within that specific ThreadGroup. Use this only when different ThreadGroups need different server configurations.

**User Interaction Required:**
- Before generating JMX, prompt user for custom base URL
- If user provides URL, parse it and use in HTTP Request Defaults
- If user skips (empty input), use base URL from OpenAPI spec
- Individual HTTP Samplers will inherit domain/port/protocol from defaults
- Individual HTTP Samplers should only specify the path (not domain/port/protocol)

### HTTPSamplerProxy (HTTP Request)

Defines an HTTP request. When using HTTP Request Defaults (recommended), individual samplers only need to specify the path.

**With HTTP Request Defaults (Recommended):**
```xml
<HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="POST /api/users" enabled="true">
  <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
    <collectionProp name="Arguments.arguments"/>
  </elementProp>
  <stringProp name="HTTPSampler.domain"></stringProp>
  <stringProp name="HTTPSampler.port"></stringProp>
  <stringProp name="HTTPSampler.protocol"></stringProp>
  <stringProp name="HTTPSampler.contentEncoding"></stringProp>
  <stringProp name="HTTPSampler.path">/api/users</stringProp>
  <stringProp name="HTTPSampler.method">POST</stringProp>
  <boolProp name="HTTPSampler.follow_redirects">true</boolProp>
  <boolProp name="HTTPSampler.auto_redirects">false</boolProp>
  <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
  <boolProp name="HTTPSampler.DO_MULTIPART_POST">false</boolProp>
  <stringProp name="HTTPSampler.embedded_url_re"></stringProp>
  <stringProp name="HTTPSampler.connect_timeout"></stringProp>
  <stringProp name="HTTPSampler.response_timeout"></stringProp>
</HTTPSamplerProxy>
```

**Without HTTP Request Defaults (Legacy):**
```xml
<HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="POST /api/users" enabled="true">
  <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
    <collectionProp name="Arguments.arguments"/>
  </elementProp>
  <stringProp name="HTTPSampler.domain">localhost</stringProp>
  <stringProp name="HTTPSampler.port">8080</stringProp>
  <stringProp name="HTTPSampler.protocol">http</stringProp>
  <stringProp name="HTTPSampler.contentEncoding">UTF-8</stringProp>
  <stringProp name="HTTPSampler.path">/api/users</stringProp>
  <stringProp name="HTTPSampler.method">POST</stringProp>
  <boolProp name="HTTPSampler.follow_redirects">true</boolProp>
  <boolProp name="HTTPSampler.auto_redirects">false</boolProp>
  <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
  <boolProp name="HTTPSampler.DO_MULTIPART_POST">false</boolProp>
  <stringProp name="HTTPSampler.embedded_url_re"></stringProp>
  <stringProp name="HTTPSampler.connect_timeout"></stringProp>
  <stringProp name="HTTPSampler.response_timeout"></stringProp>
</HTTPSamplerProxy>
```

**Key Properties:**
- `HTTPSampler.domain`: Server hostname or IP
- `HTTPSampler.port`: Port number (e.g., 80, 443, 8080)
- `HTTPSampler.protocol`: Protocol (http or https)
- `HTTPSampler.path`: Request path/endpoint
- `HTTPSampler.method`: HTTP method (GET, POST, PUT, DELETE, PATCH, etc.)
- `HTTPSampler.contentEncoding`: Character encoding (e.g., UTF-8)
- `HTTPSampler.follow_redirects`: Follow HTTP redirects
- `HTTPSampler.use_keepalive`: Use HTTP keep-alive
- `HTTPSampler.DO_MULTIPART_POST`: Use multipart/form-data for POST
- `HTTPsampler.Arguments`: Request parameters/body

**URL Parsing for JMX:**
When converting a full URL to JMX properties:

```python
# URL: http://localhost:8080/api/users?id=123
from urllib.parse import urlparse

parsed = urlparse("http://localhost:8080/api/users")
# domain: localhost
# port: 8080
# protocol: http
# path: /api/users
```

### HTTP Request Body Data

For POST/PUT requests with JSON or XML body:

```xml
<HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="POST with JSON">
  <boolProp name="HTTPSampler.postBodyRaw">true</boolProp>
  <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
    <collectionProp name="Arguments.arguments">
      <elementProp name="" elementType="HTTPArgument">
        <boolProp name="HTTPArgument.always_encode">false</boolProp>
        <stringProp name="Argument.value">{"userId": 123, "name": "John"}</stringProp>
        <stringProp name="Argument.metadata">=</stringProp>
      </elementProp>
    </collectionProp>
  </elementProp>
  <!-- Other properties -->
</HTTPSamplerProxy>
```

**Important Notes:**
- Set `HTTPSampler.postBodyRaw` to `true` for body data
- Place JSON/XML content in `Argument.value`
- Add Content-Type header via HeaderManager (not shown above)
- Do NOT check `DO_MULTIPART_POST` for JSON/XML

### ResponseAssertion

Validates HTTP responses.

```xml
<ResponseAssertion guiclass="AssertionGui" testclass="ResponseAssertion" testname="Assert 200 OK" enabled="true">
  <collectionProp name="Asserion.test_strings">
    <stringProp name="49586">200</stringProp>
  </collectionProp>
  <stringProp name="Assertion.custom_message"></stringProp>
  <stringProp name="Assertion.test_field">Assertion.response_code</stringProp>
  <boolProp name="Assertion.assume_success">false</boolProp>
  <intProp name="Assertion.test_type">8</intProp>
  <stringProp name="Assertion.scope">all</stringProp>
</ResponseAssertion>
```

**Key Properties:**
- `Asserion.test_strings`: Collection of patterns to test (note: typo in JMeter property name)
- `Assertion.test_field`: What to test
  - `Assertion.response_code`: HTTP response code
  - `Assertion.response_data`: Response body
  - `Assertion.response_headers`: Response headers
  - `Assertion.response_message`: Response message
- `Assertion.test_type`: Pattern matching rule (integer)
  - `1`: Contains
  - `2`: Matches (regex)
  - `8`: Equals
  - `16`: Substring
  - `32`: Not
  - `48`: Not Contains
- `Assertion.assume_success`: Ignore response code (useful for testing non-200 codes)
- `Assertion.scope`: Scope (all, parent, children, variable)

**Response Code Assertion Examples:**

Assert 200:
```xml
<intProp name="Assertion.test_type">8</intProp>  <!-- Equals -->
<stringProp name="Assertion.test_field">Assertion.response_code</stringProp>
<collectionProp name="Asserion.test_strings">
  <stringProp name="49586">200</stringProp>
</collectionProp>
```

Assert 201:
```xml
<intProp name="Assertion.test_type">8</intProp>  <!-- Equals -->
<stringProp name="Assertion.test_field">Assertion.response_code</stringProp>
<collectionProp name="Asserion.test_strings">
  <stringProp name="49587">201</stringProp>
</collectionProp>
```

Assert 200 or 201:
```xml
<intProp name="Assertion.test_type">1</intProp>  <!-- Contains -->
<stringProp name="Assertion.test_field">Assertion.response_code</stringProp>
<collectionProp name="Asserion.test_strings">
  <stringProp name="49586">200</stringProp>
  <stringProp name="49587">201</stringProp>
</collectionProp>
```

## Complete Example

A minimal but complete JMX file:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="API Test" enabled="true">
      <stringProp name="TestPlan.comments"></stringProp>
      <boolProp name="TestPlan.functional_mode">false</boolProp>
      <boolProp name="TestPlan.serialize_threadgroups">false</boolProp>
      <elementProp name="TestPlan.user_defined_variables" elementType="Arguments">
        <collectionProp name="Arguments.arguments"/>
      </elementProp>
    </TestPlan>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Users" enabled="true">
        <stringProp name="ThreadGroup.on_sample_error">continue</stringProp>
        <elementProp name="ThreadGroup.main_controller" elementType="LoopController">
          <boolProp name="LoopController.continue_forever">false</boolProp>
          <stringProp name="LoopController.loops">1</stringProp>
        </elementProp>
        <stringProp name="ThreadGroup.num_threads">10</stringProp>
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
        <stringProp name="ThreadGroup.duration">60</stringProp>
        <stringProp name="ThreadGroup.delay">0</stringProp>
      </ThreadGroup>
      <hashTree>
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="GET /api/users" enabled="true">
          <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
            <collectionProp name="Arguments.arguments"/>
          </elementProp>
          <stringProp name="HTTPSampler.domain">localhost</stringProp>
          <stringProp name="HTTPSampler.port">8080</stringProp>
          <stringProp name="HTTPSampler.protocol">http</stringProp>
          <stringProp name="HTTPSampler.path">/api/users</stringProp>
          <stringProp name="HTTPSampler.method">GET</stringProp>
          <boolProp name="HTTPSampler.follow_redirects">true</boolProp>
          <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
        </HTTPSamplerProxy>
        <hashTree>
          <ResponseAssertion guiclass="AssertionGui" testclass="ResponseAssertion" testname="Assert 200" enabled="true">
            <collectionProp name="Asserion.test_strings">
              <stringProp name="49586">200</stringProp>
            </collectionProp>
            <stringProp name="Assertion.test_field">Assertion.response_code</stringProp>
            <boolProp name="Assertion.assume_success">false</boolProp>
            <intProp name="Assertion.test_type">8</intProp>
          </ResponseAssertion>
          <hashTree/>
        </hashTree>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
```

## XML Formatting

JMeter JMX files should be formatted with proper indentation for readability:

- Use 2-space indentation
- Each nested level adds 2 spaces
- Self-closing tags (`<hashTree/>`) on single line
- Properties on separate lines

**Python Example (using xml.etree.ElementTree):**

```python
import xml.etree.ElementTree as ET
from xml.dom import minidom

def prettify_xml(elem):
    """Return pretty-printed XML string."""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")
```

## Implementation Guidelines

### 1. Building XML Structure

Use xml.etree.ElementTree for building JMX files:

```python
import xml.etree.ElementTree as ET

# Create root
root = ET.Element('jmeterTestPlan',
                  version="1.2",
                  properties="5.0",
                  jmeter="5.6")

# Add hashTree
main_tree = ET.SubElement(root, 'hashTree')

# Add TestPlan
test_plan = ET.SubElement(main_tree, 'TestPlan',
                         guiclass="TestPlanGui",
                         testclass="TestPlan",
                         testname="My Test",
                         enabled="true")

# Add properties
ET.SubElement(test_plan, 'stringProp',
              name="TestPlan.comments").text = ""
ET.SubElement(test_plan, 'boolProp',
              name="TestPlan.functional_mode").text = "false"
```

### 2. URL Parsing

Parse base URLs to extract JMX properties:

```python
from urllib.parse import urlparse

def parse_url_for_jmx(url):
    """Parse URL into JMX HTTPSampler properties."""
    parsed = urlparse(url)

    return {
        'domain': parsed.hostname,
        'port': str(parsed.port) if parsed.port else ('443' if parsed.scheme == 'https' else '80'),
        'protocol': parsed.scheme,
        'path': parsed.path or '/'
    }

# Example
result = parse_url_for_jmx("http://localhost:8080/api/users")
# {'domain': 'localhost', 'port': '8080', 'protocol': 'http', 'path': '/api/users'}
```

### 3. Response Code Assertions

Map HTTP methods to expected response codes:

```python
def get_expected_code(method):
    """Get expected response code for HTTP method."""
    return '201' if method.upper() == 'POST' else '200'

def create_assertion(expected_code):
    """Create ResponseAssertion element."""
    assertion = ET.Element('ResponseAssertion',
                          guiclass="AssertionGui",
                          testclass="ResponseAssertion",
                          testname=f"Assert {expected_code}",
                          enabled="true")

    # Test strings collection
    coll = ET.SubElement(assertion, 'collectionProp',
                        name="Asserion.test_strings")
    ET.SubElement(coll, 'stringProp',
                 name=str(hash(expected_code))).text = expected_code

    # Test field
    ET.SubElement(assertion, 'stringProp',
                 name="Assertion.test_field").text = "Assertion.response_code"

    # Test type (8 = equals)
    ET.SubElement(assertion, 'intProp',
                 name="Assertion.test_type").text = "8"

    return assertion
```

### 4. HashTree Management

Always pair elements with hashTree:

```python
def add_element_with_tree(parent_tree, element):
    """Add element and its hashTree to parent."""
    parent_tree.append(element)
    child_tree = ET.SubElement(parent_tree, 'hashTree')
    return child_tree

# Usage
test_plan_tree = add_element_with_tree(main_tree, test_plan)
thread_group_tree = add_element_with_tree(test_plan_tree, thread_group)
sampler_tree = add_element_with_tree(thread_group_tree, http_sampler)
add_element_with_tree(sampler_tree, assertion)  # Returns empty tree
```

## Common Pitfalls

1. **Missing hashTree**: Every element must be followed by a `<hashTree>`, even if empty
2. **Wrong property type**: Using `stringProp` for booleans or integers
3. **Typo in property names**: e.g., "Asserion.test_strings" (JMeter's actual typo)
4. **Wrong test_type**: Using wrong integer for assertion type
5. **Port as string**: Port must be stringProp, not intProp
6. **Missing encoding**: Always specify UTF-8 for contentEncoding
7. **Multipart for JSON**: Don't use multipart for JSON/XML POST

## Validation

### JMeter Load Test
```bash
# Load in GUI mode to validate structure
jmeter -t test-plan.jmx

# Run in non-GUI mode
jmeter -n -t test-plan.jmx -l results.jtl
```

### XML Schema Validation
```bash
# Check XML well-formedness
xmllint --noout test-plan.jmx
```

## References

This document is based on the following sources:

- [JmxTestPlan - Apache JMeter Wiki](https://cwiki.apache.org/confluence/display/JMETER/JmxTestPlan)
- [Apache JMeter - User guide: Customizable templates](https://jmeter.apache.org/creating-templates.html)
- [Apache JMeter - User's Manual: Building a Test Plan Programmatically](https://jmeter.apache.org/usermanual/build-programmatic-test-plan.html)
- [Apache JMeter - User's Manual: Component Reference](https://jmeter.apache.org/usermanual/component_reference.html)
- [ThreadGroup API Documentation](https://jmeter.apache.org/api/org/apache/jmeter/threads/ThreadGroup.html)
- [HTTPSampler API Documentation](https://jmeter.apache.org/api/org/apache/jmeter/protocol/http/sampler/HTTPSampler.html)
- [Updating JMeter Performance Tests with an XML parser - OctoPerf](https://octoperf.com/blog/2022/11/08/update-jmeter-script-xml-parser)
- [JMeter Assertions: The Ultimate Guide - OctoPerf](https://octoperf.com/blog/2018/04/19/jmeter-assertions/)
- [Create a jmx file with code - Stack Overflow](https://stackoverflow.com/questions/22188640/create-a-jmx-file-with-code)

---

**Last Updated**: 2025-11-23
**JMeter Version**: 5.6+
**Document Version**: 1.0
