"""Shared pytest fixtures for all tests."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """Create a temporary project directory for testing.

    Yields:
        Path object pointing to temporary directory

    Cleanup:
        Automatically removes directory after test
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def project_with_openapi_yaml(temp_project_dir: Path) -> Path:
    """Create a test project with openapi.yaml in root.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to project directory
    """
    spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
servers:
  - url: http://localhost:8000
paths:
  /users:
    get:
      summary: Get users
      responses:
        '200':
          description: Success
"""
    spec_path = temp_project_dir / "openapi.yaml"
    spec_path.write_text(spec_content)
    return temp_project_dir


@pytest.fixture
def project_with_swagger_json(temp_project_dir: Path) -> Path:
    """Create a test project with swagger.json in root.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to project directory
    """
    spec_content = """{
  "openapi": "3.0.0",
  "info": {
    "title": "Test API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "http://localhost:8000"
    }
  ],
  "paths": {
    "/users": {
      "get": {
        "summary": "Get users",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    }
  }
}
"""
    spec_path = temp_project_dir / "swagger.json"
    spec_path.write_text(spec_content)
    return temp_project_dir


@pytest.fixture
def project_with_nested_spec(temp_project_dir: Path) -> Path:
    """Create a test project with spec in subdirectory.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to project directory
    """
    # Create nested directory structure
    api_dir = temp_project_dir / "api" / "docs"
    api_dir.mkdir(parents=True)

    spec_content = """openapi: 3.0.0
info:
  title: Nested API
  version: 1.0.0
paths:
  /test:
    get:
      summary: Test endpoint
"""
    spec_path = api_dir / "openapi.yaml"
    spec_path.write_text(spec_content)
    return temp_project_dir


@pytest.fixture
def project_with_multiple_specs(temp_project_dir: Path) -> Path:
    """Create a test project with multiple spec files.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to project directory
    """
    # Create openapi.yaml in root
    openapi_content = """openapi: 3.0.0
info:
  title: OpenAPI Spec
  version: 1.0.0
paths:
  /test:
    get:
      operationId: testGet
      responses:
        '200':
          description: OK
"""
    (temp_project_dir / "openapi.yaml").write_text(openapi_content)

    # Create swagger.json in subdirectory
    swagger_content = """{
  "openapi": "3.0.0",
  "info": {
    "title": "Swagger Spec",
    "version": "1.0.0"
  },
  "paths": {
    "/swagger-test": {
      "get": {
        "operationId": "swaggerTestGet",
        "responses": {
          "200": {
            "description": "OK"
          }
        }
      }
    }
  }
}
"""
    docs_dir = temp_project_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "swagger.json").write_text(swagger_content)

    return temp_project_dir


@pytest.fixture
def empty_project(temp_project_dir: Path) -> Path:
    """Create an empty test project with no spec files.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to empty project directory
    """
    # Add a dummy file to make it a valid project
    (temp_project_dir / "README.md").write_text("# Test Project")
    return temp_project_dir


@pytest.fixture
def project_with_deep_nesting(temp_project_dir: Path) -> Path:
    """Create a project with spec beyond MAX_SEARCH_DEPTH.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to project directory
    """
    # Create directory 4 levels deep (beyond MAX_SEARCH_DEPTH of 3)
    deep_dir = temp_project_dir / "level1" / "level2" / "level3" / "level4"
    deep_dir.mkdir(parents=True)

    spec_content = """openapi: 3.0.0
info:
  title: Deep API
  version: 1.0.0
"""
    (deep_dir / "openapi.yaml").write_text(spec_content)

    # Also add one at level 2 (within depth limit)
    level2_dir = temp_project_dir / "level1" / "level2"
    (level2_dir / "api-spec.yaml").write_text(spec_content)

    return temp_project_dir


@pytest.fixture
def project_with_swagger2_yaml(temp_project_dir: Path) -> Path:
    """Create a test project with Swagger 2.0 YAML spec.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to project directory
    """
    spec_content = """swagger: '2.0'
info:
  title: Test API
  version: 1.0.0
host: localhost:8000
basePath: /api/v1
schemes:
  - https
  - http
paths:
  /users:
    get:
      summary: Get users
      operationId: getUsers
      responses:
        '200':
          description: Success
    post:
      summary: Create user
      operationId: createUser
      parameters:
        - in: body
          name: body
          description: User object
          required: true
          schema:
            type: object
      responses:
        '201':
          description: Created
  /users/{id}:
    get:
      summary: Get user by ID
      operationId: getUserById
      parameters:
        - in: path
          name: id
          type: integer
          required: true
      responses:
        '200':
          description: Success
"""
    spec_path = temp_project_dir / "swagger.yaml"
    spec_path.write_text(spec_content)
    return temp_project_dir


@pytest.fixture
def project_with_swagger2_json(temp_project_dir: Path) -> Path:
    """Create a test project with Swagger 2.0 JSON spec.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to project directory
    """
    spec_content = """{
  "swagger": "2.0",
  "info": {
    "title": "Test API",
    "version": "1.0.0"
  },
  "host": "api.example.com",
  "basePath": "/v2",
  "schemes": ["https"],
  "paths": {
    "/pets": {
      "get": {
        "summary": "List pets",
        "operationId": "listPets",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    }
  }
}
"""
    spec_path = temp_project_dir / "swagger.json"
    spec_path.write_text(spec_content)
    return temp_project_dir


@pytest.fixture
def spec_with_no_endpoints(temp_project_dir: Path) -> Path:
    """Create OpenAPI spec with empty paths object.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to spec file
    """
    spec_content = """openapi: 3.0.0
info:
  title: Empty API
  version: 1.0.0
servers:
  - url: http://localhost:8000
paths: {}
"""
    spec_path = temp_project_dir / "empty-spec.yaml"
    spec_path.write_text(spec_content)
    return spec_path


@pytest.fixture
def invalid_yaml_spec(temp_project_dir: Path) -> Path:
    """Create file with invalid YAML syntax.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to invalid YAML file
    """
    spec_content = """openapi: 3.0.0
info:
  title: Invalid YAML
  version: [this is: not valid yaml}
"""
    spec_path = temp_project_dir / "invalid.yaml"
    spec_path.write_text(spec_content)
    return spec_path


@pytest.fixture
def invalid_openapi_structure(temp_project_dir: Path) -> Path:
    """Create valid YAML but missing required OpenAPI fields.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to invalid OpenAPI spec
    """
    spec_content = """openapi: 3.0.0
info:
  title: Missing Paths
  version: 1.0.0
"""
    spec_path = temp_project_dir / "missing-paths.yaml"
    spec_path.write_text(spec_content)
    return spec_path


@pytest.fixture
def unsupported_openapi_version(temp_project_dir: Path) -> Path:
    """Create OpenAPI spec with unsupported version.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to spec with unsupported version
    """
    spec_content = """openapi: 4.0.0
info:
  title: Future Version API
  version: 1.0.0
paths:
  /test:
    get:
      summary: Test endpoint
"""
    spec_path = temp_project_dir / "unsupported-version.yaml"
    spec_path.write_text(spec_content)
    return spec_path


@pytest.fixture
def minimal_invalid_jmx(temp_project_dir: Path) -> Path:
    """Create minimal JMX file missing required elements.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to invalid JMX file
    """
    jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan" enabled="true">
      <stringProp name="TestPlan.comments"/>
      <boolProp name="TestPlan.functional_mode">false</boolProp>
    </TestPlan>
    <hashTree/>
  </hashTree>
</jmeterTestPlan>
"""
    jmx_path = temp_project_dir / "invalid.jmx"
    jmx_path.write_text(jmx_content)
    return jmx_path


@pytest.fixture
def malformed_xml_file(temp_project_dir: Path) -> Path:
    """Create file with invalid XML syntax.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to malformed XML file
    """
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan>
  <unclosed tag>
  <another tag without closing
"""
    xml_path = temp_project_dir / "malformed.jmx"
    xml_path.write_text(xml_content)
    return xml_path


@pytest.fixture
def spec_with_complex_refs(temp_project_dir: Path) -> Path:
    """Create OpenAPI spec with nested $ref resolution.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to spec with complex references
    """
    spec_content = """openapi: 3.0.0
info:
  title: Complex Refs API
  version: 1.0.0
servers:
  - url: http://localhost:8000
paths:
  /users:
    post:
      summary: Create user
      operationId: createUser
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/User'
      responses:
        '201':
          description: Created
components:
  schemas:
    User:
      type: object
      properties:
        name:
          type: string
        address:
          $ref: '#/components/schemas/Address'
    Address:
      type: object
      properties:
        street:
          type: string
        city:
          type: string
"""
    spec_path = temp_project_dir / "complex-refs.yaml"
    spec_path.write_text(spec_content)
    return spec_path


@pytest.fixture
def spec_with_special_characters(temp_project_dir: Path) -> Path:
    """Create OpenAPI spec with special characters in paths.

    Args:
        temp_project_dir: Temporary directory fixture

    Returns:
        Path to spec with special characters
    """
    spec_content = """openapi: 3.0.0
info:
  title: Special Chars API
  version: 1.0.0
servers:
  - url: http://localhost:8000
paths:
  /api/users/{id}/items-list_v2:
    get:
      summary: Get user items
      operationId: getUserItems
      parameters:
        - in: path
          name: id
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Success
"""
    spec_path = temp_project_dir / "special-chars.yaml"
    spec_path.write_text(spec_content)
    return spec_path
