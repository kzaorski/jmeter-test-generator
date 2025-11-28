"""Unit tests for OpenAPIParser v2 methods."""

import pytest

from jmeter_gen.core.openapi_parser import OpenAPIParser
from jmeter_gen.exceptions import AmbiguousPathException, EndpointNotFoundException

# Mark all tests in this module as v2 tests
pytestmark = pytest.mark.v2


class TestOpenAPIParserV2Methods:
    """Tests for v2 methods added to OpenAPIParser."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return OpenAPIParser()

    @pytest.fixture
    def spec_path(self, parser, tmp_path):
        """Create and parse a sample OpenAPI spec, return the path."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
servers:
  - url: http://localhost:8000
paths:
  /users:
    get:
      operationId: getUsers
      summary: List all users
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'
    post:
      operationId: createUser
      summary: Create a user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserInput'
      responses:
        '201':
          description: Created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
  /users/{id}:
    get:
      operationId: getUserById
      summary: Get user by ID
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
    put:
      operationId: updateUser
      summary: Update a user
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserInput'
      responses:
        '200':
          description: Updated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
    delete:
      operationId: deleteUser
      summary: Delete a user
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        '204':
          description: Deleted
  /users/{userId}/orders:
    get:
      operationId: getUserOrders
      summary: Get user orders
      parameters:
        - name: userId
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: Success
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
        email:
          type: string
        name:
          type: string
        created_at:
          type: string
          format: date-time
    UserInput:
      type: object
      properties:
        email:
          type: string
        name:
          type: string
"""
        spec_file = tmp_path / "openapi.yaml"
        spec_file.write_text(spec_content)
        parser.parse(str(spec_file))
        return spec_file

    # get_endpoint_by_operation_id tests

    def test_get_endpoint_by_operation_id_found(self, parser, spec_path):
        """Test finding endpoint by valid operation ID."""
        endpoint = parser.get_endpoint_by_operation_id("createUser")

        assert endpoint is not None
        assert endpoint["path"] == "/users"
        assert endpoint["method"] == "POST"
        assert endpoint["operationId"] == "createUser"

    def test_get_endpoint_by_operation_id_not_found(self, parser, spec_path):
        """Test that None is returned for invalid operation ID."""
        endpoint = parser.get_endpoint_by_operation_id("nonexistent")
        assert endpoint is None

    def test_get_endpoint_by_operation_id_all_operations(self, parser, spec_path):
        """Test finding various operation IDs."""
        operations = ["getUsers", "createUser", "getUserById", "updateUser", "deleteUser"]

        for op_id in operations:
            endpoint = parser.get_endpoint_by_operation_id(op_id)
            assert endpoint is not None
            assert endpoint["operationId"] == op_id

    # get_endpoint_by_method_path tests

    def test_get_endpoint_by_method_path_found(self, parser, spec_path):
        """Test finding endpoint by method and path."""
        endpoint = parser.get_endpoint_by_method_path("GET", "/users")

        assert endpoint is not None
        assert endpoint["method"] == "GET"
        assert endpoint["path"] == "/users"
        assert endpoint["operationId"] == "getUsers"

    def test_get_endpoint_by_method_path_with_param(self, parser, spec_path):
        """Test finding endpoint with path parameter."""
        endpoint = parser.get_endpoint_by_method_path("GET", "/users/{id}")

        assert endpoint is not None
        assert endpoint["operationId"] == "getUserById"

    def test_get_endpoint_by_method_path_not_found(self, parser, spec_path):
        """Test that None is returned for invalid path."""
        endpoint = parser.get_endpoint_by_method_path("GET", "/nonexistent")
        assert endpoint is None

    def test_get_endpoint_by_method_path_wrong_method(self, parser, spec_path):
        """Test that None is returned for wrong method."""
        endpoint = parser.get_endpoint_by_method_path("PATCH", "/users")
        assert endpoint is None

    def test_get_endpoint_by_method_path_case_insensitive(self, parser, spec_path):
        """Test that method matching is case-insensitive."""
        endpoint = parser.get_endpoint_by_method_path("get", "/users")
        assert endpoint is not None
        assert endpoint["operationId"] == "getUsers"

    # get_all_operation_ids tests

    def test_get_all_operation_ids(self, parser, spec_path):
        """Test getting all operation IDs from spec."""
        op_ids = parser.get_all_operation_ids()

        assert isinstance(op_ids, list)
        assert "getUsers" in op_ids
        assert "createUser" in op_ids
        assert "getUserById" in op_ids
        assert "updateUser" in op_ids
        assert "deleteUser" in op_ids
        assert "getUserOrders" in op_ids
        assert len(op_ids) == 6

    # get_all_paths tests

    def test_get_all_paths(self, parser, spec_path):
        """Test getting all paths from spec."""
        paths = parser.get_all_paths()

        assert isinstance(paths, dict)
        assert "/users" in paths
        assert "/users/{id}" in paths
        assert "/users/{userId}/orders" in paths
        # Check methods
        assert "GET" in paths["/users"]
        assert "POST" in paths["/users"]

    # extract_response_schema tests

    def test_extract_response_schema_200(self, parser, spec_path):
        """Test extracting response schema for 200 status."""
        schema = parser.extract_response_schema(operation_id="getUserById")

        assert schema is not None
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "id" in schema["properties"]
        assert "email" in schema["properties"]

    def test_extract_response_schema_201(self, parser, spec_path):
        """Test extracting response schema for 201 status."""
        schema = parser.extract_response_schema(operation_id="createUser")

        assert schema is not None
        assert schema["type"] == "object"

    def test_extract_response_schema_no_content(self, parser, spec_path):
        """Test extracting response schema when no content (204)."""
        schema = parser.extract_response_schema(operation_id="deleteUser")

        # 204 has no content, should return None
        assert schema is None

    def test_extract_response_schema_not_found(self, parser, spec_path):
        """Test extracting response schema for nonexistent operation."""
        schema = parser.extract_response_schema(operation_id="nonexistent")

        assert schema is None

    def test_extract_response_schema_by_method_path(self, parser, spec_path):
        """Test extracting response schema by method and path."""
        schema = parser.extract_response_schema(method="GET", path="/users/{id}")

        assert schema is not None
        assert "properties" in schema

    # resolve_short_path tests

    def test_resolve_short_path_exact_match(self, parser, spec_path):
        """Test that exact match takes precedence."""
        resolved = parser.resolve_short_path("GET", "/users")

        assert resolved is not None
        assert resolved.full_path == "/users"
        assert resolved.match_type == "exact"

    def test_resolve_short_path_suffix(self, parser, spec_path):
        """Test resolving by suffix."""
        resolved = parser.resolve_short_path("GET", "/orders")

        # Should find /users/{userId}/orders
        assert resolved is not None
        assert "orders" in resolved.full_path
        assert resolved.method == "GET"

    def test_resolve_short_path_not_found(self, parser, spec_path):
        """Test resolving non-existent path."""
        with pytest.raises(EndpointNotFoundException):
            parser.resolve_short_path("GET", "/nonexistent")

    def test_resolve_short_path_ambiguous(self, parser, tmp_path):
        """Test that AmbiguousPathException is raised for ambiguous paths."""
        # Create spec with ambiguous paths
        spec_content = """openapi: 3.0.0
info:
  title: Ambiguous API
  version: 1.0.0
paths:
  /api/v1/users:
    get:
      operationId: getV1Users
      responses:
        '200':
          description: Success
  /api/v2/users:
    get:
      operationId: getV2Users
      responses:
        '200':
          description: Success
"""
        spec_file = tmp_path / "ambiguous.yaml"
        spec_file.write_text(spec_content)

        parser = OpenAPIParser()
        parser.parse(str(spec_file))

        with pytest.raises(AmbiguousPathException) as exc_info:
            parser.resolve_short_path("GET", "/users")

        # Should contain candidates
        assert exc_info.value.candidates is not None
        assert len(exc_info.value.candidates) == 2

    # find_suffix_matches tests

    def test_find_suffix_matches(self, parser, spec_path):
        """Test finding paths by suffix."""
        matches = parser.find_suffix_matches("GET", "/users")

        assert isinstance(matches, list)
        assert len(matches) >= 1
        assert "/users" in matches

    def test_find_suffix_matches_multiple(self, parser, spec_path):
        """Test finding multiple suffix matches."""
        matches = parser.find_suffix_matches("GET", "/orders")

        # Should find /users/{userId}/orders
        assert len(matches) >= 1
        assert any("orders" in p for p in matches)


class TestOpenAPIParserV2WithSwagger:
    """Tests for v2 methods with Swagger 2.0 specs."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return OpenAPIParser()

    @pytest.fixture
    def swagger_spec_path(self, parser, tmp_path):
        """Create and parse a Swagger 2.0 spec, return the path."""
        spec_content = """{
  "swagger": "2.0",
  "info": {
    "title": "Pet Store",
    "version": "1.0.0"
  },
  "host": "petstore.example.com",
  "basePath": "/api",
  "schemes": ["https"],
  "paths": {
    "/pets": {
      "get": {
        "operationId": "listPets",
        "summary": "List pets",
        "responses": {
          "200": {
            "description": "Success",
            "schema": {
              "type": "array",
              "items": {
                "$ref": "#/definitions/Pet"
              }
            }
          }
        }
      },
      "post": {
        "operationId": "createPet",
        "summary": "Create pet",
        "parameters": [
          {
            "in": "body",
            "name": "pet",
            "schema": {
              "$ref": "#/definitions/PetInput"
            }
          }
        ],
        "responses": {
          "201": {
            "description": "Created",
            "schema": {
              "$ref": "#/definitions/Pet"
            }
          }
        }
      }
    },
    "/pets/{petId}": {
      "get": {
        "operationId": "getPet",
        "summary": "Get pet",
        "parameters": [
          {
            "in": "path",
            "name": "petId",
            "type": "integer",
            "required": true
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "schema": {
              "$ref": "#/definitions/Pet"
            }
          }
        }
      }
    }
  },
  "definitions": {
    "Pet": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer"
        },
        "name": {
          "type": "string"
        },
        "status": {
          "type": "string"
        }
      }
    },
    "PetInput": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string"
        }
      }
    }
  }
}
"""
        spec_file = tmp_path / "swagger.json"
        spec_file.write_text(spec_content)
        parser.parse(str(spec_file))
        return spec_file

    def test_get_endpoint_by_operation_id_swagger(self, parser, swagger_spec_path):
        """Test operation ID lookup with Swagger 2.0."""
        endpoint = parser.get_endpoint_by_operation_id("createPet")

        assert endpoint is not None
        assert endpoint["path"] == "/pets"
        assert endpoint["method"] == "POST"

    def test_get_all_operation_ids_swagger(self, parser, swagger_spec_path):
        """Test getting all operation IDs from Swagger 2.0."""
        op_ids = parser.get_all_operation_ids()

        assert "listPets" in op_ids
        assert "createPet" in op_ids
        assert "getPet" in op_ids

    def test_extract_response_schema_swagger(self, parser, swagger_spec_path):
        """Test extracting response schema from Swagger 2.0."""
        schema = parser.extract_response_schema(operation_id="getPet")

        # Swagger 2.0 uses #/definitions/ which is not resolved by _resolve_schema_ref
        # The schema is returned with $ref unresolved
        assert schema is not None
        # Schema contains $ref to #/definitions/Pet
        assert "$ref" in schema or "type" in schema


class TestOpenAPIParserV2NoSpec:
    """Tests for v2 methods when no spec is loaded."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance without loading a spec."""
        return OpenAPIParser()

    def test_get_endpoint_by_operation_id_no_spec(self, parser):
        """Test operation ID lookup with no spec loaded."""
        endpoint = parser.get_endpoint_by_operation_id("test")
        assert endpoint is None

    def test_get_endpoint_by_method_path_no_spec(self, parser):
        """Test method/path lookup with no spec loaded."""
        endpoint = parser.get_endpoint_by_method_path("GET", "/test")
        assert endpoint is None

    def test_get_all_operation_ids_no_spec(self, parser):
        """Test getting all operation IDs with no spec loaded."""
        op_ids = parser.get_all_operation_ids()
        assert op_ids == []

    def test_get_all_paths_no_spec(self, parser):
        """Test getting all paths with no spec loaded."""
        paths = parser.get_all_paths()
        assert paths == {}

    def test_extract_response_schema_no_spec(self, parser):
        """Test extracting response schema with no spec loaded."""
        schema = parser.extract_response_schema(operation_id="test")
        assert schema is None
