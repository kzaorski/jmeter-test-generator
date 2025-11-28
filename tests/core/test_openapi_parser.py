"""Unit tests for OpenAPIParser module."""

import json
from pathlib import Path

import pytest
import yaml

from jmeter_gen.core.openapi_parser import (
    SUPPORTED_METHODS,
    SUPPORTED_SWAGGER_VERSIONS,
    OpenAPIParser,
    _is_supported_openapi_version,
)
from jmeter_gen.exceptions import InvalidSpecException, UnsupportedVersionException


class TestOpenAPIParser:
    """Test suite for OpenAPIParser class."""

    @pytest.fixture
    def parser(self) -> OpenAPIParser:
        """Create OpenAPIParser instance for testing.

        Returns:
            OpenAPIParser instance
        """
        return OpenAPIParser()

    def test_constants(self):
        """Test that required constants are defined correctly."""
        assert isinstance(SUPPORTED_SWAGGER_VERSIONS, list)
        assert len(SUPPORTED_SWAGGER_VERSIONS) > 0
        assert "2.0" in SUPPORTED_SWAGGER_VERSIONS

        assert isinstance(SUPPORTED_METHODS, list)
        assert "get" in SUPPORTED_METHODS
        assert "post" in SUPPORTED_METHODS
        assert "put" in SUPPORTED_METHODS
        assert "delete" in SUPPORTED_METHODS
        assert "patch" in SUPPORTED_METHODS

    def test_is_supported_openapi_version(self):
        """Test that version check function works correctly."""
        # Test valid 3.x versions
        assert _is_supported_openapi_version("3.0.0") is True
        assert _is_supported_openapi_version("3.0.1") is True
        assert _is_supported_openapi_version("3.0.2") is True
        assert _is_supported_openapi_version("3.0.3") is True
        assert _is_supported_openapi_version("3.1.0") is True
        assert _is_supported_openapi_version("3.1.1") is True
        assert _is_supported_openapi_version("3.2.0") is True

        # Test invalid versions
        assert _is_supported_openapi_version("2.0") is False
        assert _is_supported_openapi_version("2.0.0") is False
        assert _is_supported_openapi_version("4.0.0") is False
        assert _is_supported_openapi_version("invalid") is False
        assert _is_supported_openapi_version("") is False

    def test_parse_valid_yaml_spec(self, parser: OpenAPIParser, project_with_openapi_yaml: Path):
        """Test parsing a valid YAML OpenAPI spec."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        result = parser.parse(str(spec_path))

        assert result is not None
        assert "title" in result
        assert "version" in result
        assert "base_url" in result
        assert "endpoints" in result
        assert "spec" in result

    def test_parse_valid_json_spec(self, parser: OpenAPIParser, project_with_swagger_json: Path):
        """Test parsing a valid JSON OpenAPI spec."""
        spec_path = project_with_swagger_json / "swagger.json"
        result = parser.parse(str(spec_path))

        assert result is not None
        assert "title" in result
        assert "version" in result
        assert "base_url" in result
        assert "endpoints" in result
        assert "spec" in result

    def test_parse_extracts_correct_title(
        self, parser: OpenAPIParser, project_with_openapi_yaml: Path
    ):
        """Test that parse extracts the correct API title."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        result = parser.parse(str(spec_path))

        assert result["title"] == "Test API"

    def test_parse_extracts_correct_version(
        self, parser: OpenAPIParser, project_with_openapi_yaml: Path
    ):
        """Test that parse extracts the correct API version."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        result = parser.parse(str(spec_path))

        assert result["version"] == "1.0.0"

    def test_parse_extracts_base_url(self, parser: OpenAPIParser, project_with_openapi_yaml: Path):
        """Test that parse extracts base URL from servers."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        result = parser.parse(str(spec_path))

        assert result["base_url"] == "http://localhost:8000"

    def test_parse_extracts_endpoints(self, parser: OpenAPIParser, project_with_openapi_yaml: Path):
        """Test that parse extracts endpoints list."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        result = parser.parse(str(spec_path))

        assert isinstance(result["endpoints"], list)
        assert len(result["endpoints"]) > 0

    def test_parse_includes_full_spec(self, parser: OpenAPIParser, project_with_openapi_yaml: Path):
        """Test that parse includes full spec in result."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        result = parser.parse(str(spec_path))

        assert isinstance(result["spec"], dict)
        assert "openapi" in result["spec"]
        assert "info" in result["spec"]
        assert "paths" in result["spec"]


class TestParseEndpoints:
    """Test suite for endpoint parsing."""

    @pytest.fixture
    def parser(self) -> OpenAPIParser:
        """Create OpenAPIParser instance for testing."""
        return OpenAPIParser()

    def test_parse_endpoints_extracts_all_methods(
        self, parser: OpenAPIParser, temp_project_dir: Path
    ):
        """Test that _parse_endpoints extracts all HTTP methods."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get users
    post:
      summary: Create user
    put:
      summary: Update user
    delete:
      summary: Delete user
    patch:
      summary: Patch user
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        result = parser.parse(str(spec_path))

        assert len(result["endpoints"]) == 5
        methods = {ep["method"] for ep in result["endpoints"]}
        assert methods == {"GET", "POST", "PUT", "DELETE", "PATCH"}

    def test_parse_endpoints_uppercase_methods(
        self, parser: OpenAPIParser, project_with_openapi_yaml: Path
    ):
        """Test that methods are converted to uppercase."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        result = parser.parse(str(spec_path))

        for endpoint in result["endpoints"]:
            assert endpoint["method"].isupper()
            assert endpoint["method"] in ["GET", "POST", "PUT", "DELETE", "PATCH"]

    def test_parse_endpoints_with_parameters(self, parser: OpenAPIParser, temp_project_dir: Path):
        """Test parsing endpoints with parameters."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users/{id}:
    get:
      summary: Get user by ID
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
        - name: format
          in: query
          required: false
          schema:
            type: string
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        result = parser.parse(str(spec_path))

        assert len(result["endpoints"]) == 1
        endpoint = result["endpoints"][0]
        assert len(endpoint["parameters"]) == 2
        assert endpoint["parameters"][0]["name"] == "id"
        assert endpoint["parameters"][1]["name"] == "format"

    def test_parse_endpoints_with_request_body(self, parser: OpenAPIParser, temp_project_dir: Path):
        """Test parsing endpoints with request body."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    post:
      summary: Create user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        result = parser.parse(str(spec_path))

        assert len(result["endpoints"]) == 1
        endpoint = result["endpoints"][0]
        assert endpoint["requestBody"] is True

    def test_parse_endpoints_without_request_body(
        self, parser: OpenAPIParser, project_with_openapi_yaml: Path
    ):
        """Test that endpoints without request body have requestBody=False."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        result = parser.parse(str(spec_path))

        # The test spec has a GET /users which doesn't have a request body
        get_endpoint = [ep for ep in result["endpoints"] if ep["method"] == "GET"][0]
        assert get_endpoint["requestBody"] is False

    def test_parse_endpoints_extracts_operation_id(
        self, parser: OpenAPIParser, temp_project_dir: Path
    ):
        """Test that operationId is extracted correctly."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      operationId: listUsers
      summary: Get users
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        result = parser.parse(str(spec_path))

        assert len(result["endpoints"]) == 1
        endpoint = result["endpoints"][0]
        assert endpoint["operationId"] == "listUsers"

    def test_parse_endpoints_generates_operation_id_if_missing(
        self, parser: OpenAPIParser, temp_project_dir: Path
    ):
        """Test that operationId is generated if not provided."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get users
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        result = parser.parse(str(spec_path))

        assert len(result["endpoints"]) == 1
        endpoint = result["endpoints"][0]
        # Generated operationId should be based on method and path
        assert "get" in endpoint["operationId"].lower()
        assert "users" in endpoint["operationId"].lower()

    def test_parse_endpoints_extracts_summary(
        self, parser: OpenAPIParser, project_with_openapi_yaml: Path
    ):
        """Test that summary is extracted correctly."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        result = parser.parse(str(spec_path))

        endpoint = result["endpoints"][0]
        assert endpoint["summary"] == "Get users"

    def test_parse_endpoints_extracts_description(
        self, parser: OpenAPIParser, temp_project_dir: Path
    ):
        """Test that description is extracted correctly."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get users
      description: Retrieve a list of all users in the system
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        result = parser.parse(str(spec_path))

        endpoint = result["endpoints"][0]
        assert endpoint["description"] == "Retrieve a list of all users in the system"

    def test_parse_endpoints_extracts_path(
        self, parser: OpenAPIParser, project_with_openapi_yaml: Path
    ):
        """Test that path is extracted correctly."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        result = parser.parse(str(spec_path))

        endpoint = result["endpoints"][0]
        assert endpoint["path"] == "/users"

    def test_parse_endpoints_extracts_response_codes(
        self, parser: OpenAPIParser, temp_project_dir: Path
    ):
        """Test that expected response codes are extracted from spec."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "getUsers",
                        "responses": {
                            "200": {"description": "Success"},
                            "404": {"description": "Not Found"}
                        }
                    },
                    "post": {
                        "operationId": "createUser",
                        "responses": {
                            "200": {"description": "Success"},
                            "201": {"description": "Created"}
                        }
                    }
                }
            }
        }

        spec_path = temp_project_dir / "openapi.json"
        spec_path.write_text(json.dumps(spec))

        result = parser.parse(str(spec_path))

        # GET should extract 200 (ignoring 404 which is not 2xx)
        get_endpoint = [ep for ep in result["endpoints"] if ep["method"] == "GET"][0]
        assert "expected_response_codes" in get_endpoint
        assert get_endpoint["expected_response_codes"] == ["200"]

        # POST should extract both 200 and 201
        post_endpoint = [ep for ep in result["endpoints"] if ep["method"] == "POST"][0]
        assert "expected_response_codes" in post_endpoint
        assert set(post_endpoint["expected_response_codes"]) == {"200", "201"}

    def test_parse_endpoints_fallback_response_codes(
        self, parser: OpenAPIParser, temp_project_dir: Path
    ):
        """Test fallback to default response codes when spec has no responses."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "getUsers"
                        # No responses section
                    },
                    "post": {
                        "operationId": "createUser"
                        # No responses section
                    }
                }
            }
        }

        spec_path = temp_project_dir / "openapi.json"
        spec_path.write_text(json.dumps(spec))

        result = parser.parse(str(spec_path))

        # GET should default to 200
        get_endpoint = [ep for ep in result["endpoints"] if ep["method"] == "GET"][0]
        assert get_endpoint["expected_response_codes"] == ["200"]

        # POST should default to 201
        post_endpoint = [ep for ep in result["endpoints"] if ep["method"] == "POST"][0]
        assert post_endpoint["expected_response_codes"] == ["201"]

    def test_parse_endpoints_ignores_non_success_codes(
        self, parser: OpenAPIParser, temp_project_dir: Path
    ):
        """Test that only 2xx response codes are extracted."""
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "getUsers",
                        "responses": {
                            "200": {"description": "Success"},
                            "400": {"description": "Bad Request"},
                            "404": {"description": "Not Found"},
                            "500": {"description": "Server Error"},
                            "default": {"description": "Error"}
                        }
                    }
                }
            }
        }

        spec_path = temp_project_dir / "openapi.json"
        spec_path.write_text(json.dumps(spec))

        result = parser.parse(str(spec_path))

        # Should only extract 200, ignoring 4xx, 5xx, and default
        endpoint = result["endpoints"][0]
        assert endpoint["expected_response_codes"] == ["200"]


class TestGetBaseUrl:
    """Test suite for base URL extraction."""

    @pytest.fixture
    def parser(self) -> OpenAPIParser:
        """Create OpenAPIParser instance for testing."""
        return OpenAPIParser()

    def test_get_base_url_prefers_localhost(self, parser: OpenAPIParser):
        """Test that _get_base_url prefers localhost server."""
        servers = [
            {"url": "https://api.example.com"},
            {"url": "http://localhost:3000"},
            {"url": "https://staging.example.com"},
        ]

        base_url = parser._get_base_url(servers)

        assert base_url == "http://localhost:3000"

    def test_get_base_url_returns_first_if_no_localhost(self, parser: OpenAPIParser):
        """Test that _get_base_url returns first server if no localhost."""
        servers = [
            {"url": "https://api.example.com"},
            {"url": "https://staging.example.com"},
        ]

        base_url = parser._get_base_url(servers)

        assert base_url == "https://api.example.com"

    def test_get_base_url_defaults_when_empty(self, parser: OpenAPIParser):
        """Test that _get_base_url returns default when servers is empty."""
        base_url = parser._get_base_url([])

        assert base_url == "http://localhost:8080"

    def test_get_base_url_case_insensitive_localhost(self, parser: OpenAPIParser):
        """Test that localhost detection is case-insensitive."""
        servers = [
            {"url": "https://api.example.com"},
            {"url": "http://LocalHost:3000"},
        ]

        base_url = parser._get_base_url(servers)

        assert base_url == "http://LocalHost:3000"


class TestErrorHandling:
    """Test suite for error handling."""

    @pytest.fixture
    def parser(self) -> OpenAPIParser:
        """Create OpenAPIParser instance for testing."""
        return OpenAPIParser()

    def test_file_not_found_raises(self, parser: OpenAPIParser):
        """Test that FileNotFoundError is raised for non-existent file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            parser.parse("/nonexistent/path/to/spec.yaml")

        assert "not found" in str(exc_info.value).lower()

    def test_invalid_yaml_raises(self, parser: OpenAPIParser, temp_project_dir: Path):
        """Test that invalid YAML raises YAMLError."""
        spec_path = temp_project_dir / "invalid.yaml"
        spec_path.write_text("invalid: yaml: content: [[[")

        with pytest.raises(yaml.YAMLError):
            parser.parse(str(spec_path))

    def test_unsupported_file_format_raises(self, parser: OpenAPIParser, temp_project_dir: Path):
        """Test that unsupported file format raises InvalidSpecException."""
        spec_path = temp_project_dir / "spec.txt"
        spec_path.write_text("some content")

        with pytest.raises(InvalidSpecException) as exc_info:
            parser.parse(str(spec_path))

        assert "unsupported file format" in str(exc_info.value).lower()

    def test_missing_version_field_raises(self, parser: OpenAPIParser, temp_project_dir: Path):
        """Test that missing both 'openapi' and 'swagger' fields raises InvalidSpecException."""
        spec_content = """info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get users
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        with pytest.raises(InvalidSpecException) as exc_info:
            parser.parse(str(spec_path))

        assert "version field" in str(exc_info.value).lower()

    def test_unsupported_version_raises(self, parser: OpenAPIParser, temp_project_dir: Path):
        """Test that unsupported OpenAPI version raises exception."""
        spec_content = """openapi: 4.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get users
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        with pytest.raises(UnsupportedVersionException) as exc_info:
            parser.parse(str(spec_path))

        assert "4.0.0" in str(exc_info.value)
        assert "unsupported" in str(exc_info.value).lower()

    def test_missing_info_field_raises(self, parser: OpenAPIParser, temp_project_dir: Path):
        """Test that missing 'info' field raises InvalidSpecException."""
        spec_content = """openapi: 3.0.0
paths:
  /users:
    get:
      summary: Get users
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        with pytest.raises(InvalidSpecException) as exc_info:
            parser.parse(str(spec_path))

        assert "info" in str(exc_info.value).lower()

    def test_missing_paths_field_raises(self, parser: OpenAPIParser, temp_project_dir: Path):
        """Test that missing 'paths' field raises InvalidSpecException."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        with pytest.raises(InvalidSpecException) as exc_info:
            parser.parse(str(spec_path))

        assert "paths" in str(exc_info.value).lower()


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.fixture
    def parser(self) -> OpenAPIParser:
        """Create OpenAPIParser instance for testing."""
        return OpenAPIParser()

    def test_parse_spec_with_no_servers(self, parser: OpenAPIParser, temp_project_dir: Path):
        """Test parsing spec without servers array."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get users
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        result = parser.parse(str(spec_path))

        assert result["base_url"] == "http://localhost:8080"

    def test_parse_spec_with_empty_paths(self, parser: OpenAPIParser, temp_project_dir: Path):
        """Test parsing spec with empty paths object."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths: {}
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        result = parser.parse(str(spec_path))

        assert result["endpoints"] == []

    def test_parse_spec_with_missing_title(self, parser: OpenAPIParser, temp_project_dir: Path):
        """Test parsing spec without title uses default."""
        spec_content = """openapi: 3.0.0
info:
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get users
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        result = parser.parse(str(spec_path))

        assert result["title"] == "Untitled API"

    def test_parse_spec_with_missing_version(self, parser: OpenAPIParser, temp_project_dir: Path):
        """Test parsing spec without version uses default."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
paths:
  /users:
    get:
      summary: Get users
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        result = parser.parse(str(spec_path))

        assert result["version"] == "1.0.0"

    def test_parse_all_supported_versions(self, parser: OpenAPIParser, temp_project_dir: Path):
        """Test that all supported OpenAPI 3.x versions can be parsed."""
        test_versions = ["3.0.0", "3.0.1", "3.0.2", "3.0.3", "3.1.0", "3.1.1", "3.2.0"]
        for version in test_versions:
            spec_content = f"""openapi: {version}
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get users
"""
            spec_path = temp_project_dir / f"openapi_{version}.yaml"
            spec_path.write_text(spec_content)

            result = parser.parse(str(spec_path))

            assert result is not None
            assert result["title"] == "Test API"


class TestSwagger2Support:
    """Test suite for Swagger 2.0 specification support."""

    @pytest.fixture
    def parser(self) -> OpenAPIParser:
        """Create OpenAPIParser instance for testing."""
        return OpenAPIParser()

    def test_parse_swagger2_yaml(self, parser: OpenAPIParser, project_with_swagger2_yaml: Path):
        """Test parsing a valid Swagger 2.0 YAML spec."""
        spec_path = project_with_swagger2_yaml / "swagger.yaml"
        result = parser.parse(str(spec_path))

        assert result is not None
        assert result["spec_type"] == "swagger"
        assert result["spec_version"] == "2.0"
        assert result["title"] == "Test API"
        assert result["version"] == "1.0.0"

    def test_parse_swagger2_json(self, parser: OpenAPIParser, project_with_swagger2_json: Path):
        """Test parsing a valid Swagger 2.0 JSON spec."""
        spec_path = project_with_swagger2_json / "swagger.json"
        result = parser.parse(str(spec_path))

        assert result is not None
        assert result["spec_type"] == "swagger"
        assert result["spec_version"] == "2.0"
        assert result["title"] == "Test API"
        assert result["version"] == "1.0.0"

    def test_swagger2_base_url_construction(
        self, parser: OpenAPIParser, project_with_swagger2_yaml: Path
    ):
        """Test that base URL is correctly constructed from host + schemes (without basePath)."""
        spec_path = project_with_swagger2_yaml / "swagger.yaml"
        result = parser.parse(str(spec_path))

        # Swagger 2.0 spec has: host="localhost:8000", basePath="/api/v1", schemes=["https", "http"]
        # Should prefer HTTPS but NOT include basePath (that goes in endpoint paths)
        assert result["base_url"] == "https://localhost:8000"

        # Verify basePath is prepended to endpoint paths
        assert all(endpoint["path"].startswith("/api/v1") for endpoint in result["endpoints"])

    def test_swagger2_endpoints_extracted(
        self, parser: OpenAPIParser, project_with_swagger2_yaml: Path
    ):
        """Test that endpoints are extracted from Swagger 2.0 spec."""
        spec_path = project_with_swagger2_yaml / "swagger.yaml"
        result = parser.parse(str(spec_path))

        # The fixture has 3 endpoints: GET /users, POST /users, GET /users/{id}
        assert len(result["endpoints"]) == 3

        # Verify endpoint structure
        for endpoint in result["endpoints"]:
            assert "path" in endpoint
            assert "method" in endpoint
            assert "operationId" in endpoint
            assert "summary" in endpoint
            assert "requestBody" in endpoint
            assert "parameters" in endpoint

    def test_swagger2_body_parameter_detection(
        self, parser: OpenAPIParser, project_with_swagger2_yaml: Path
    ):
        """Test that body parameters are detected as request body in Swagger 2.0."""
        spec_path = project_with_swagger2_yaml / "swagger.yaml"
        result = parser.parse(str(spec_path))

        # POST /users has a body parameter
        post_endpoint = [ep for ep in result["endpoints"] if ep["method"] == "POST"][0]
        assert post_endpoint["requestBody"] is True

        # GET /users doesn't have a body parameter
        get_endpoint = [ep for ep in result["endpoints"] if ep["method"] == "GET"][0]
        assert get_endpoint["requestBody"] is False

    def test_swagger2_path_parameters(
        self, parser: OpenAPIParser, project_with_swagger2_yaml: Path
    ):
        """Test that path parameters are extracted from Swagger 2.0 spec."""
        spec_path = project_with_swagger2_yaml / "swagger.yaml"
        result = parser.parse(str(spec_path))

        # GET /api/v1/users/{id} has a path parameter (basePath prepended)
        get_by_id = [
            ep for ep in result["endpoints"]
            if ep["path"] == "/api/v1/users/{id}" and ep["method"] == "GET"
        ][0]

        assert len(get_by_id["parameters"]) == 1
        assert get_by_id["parameters"][0]["name"] == "id"
        assert get_by_id["parameters"][0]["in"] == "path"
        assert get_by_id["parameters"][0]["required"] is True

    def test_swagger2_operation_ids(
        self, parser: OpenAPIParser, project_with_swagger2_yaml: Path
    ):
        """Test that operationIds are extracted from Swagger 2.0 spec."""
        spec_path = project_with_swagger2_yaml / "swagger.yaml"
        result = parser.parse(str(spec_path))

        operation_ids = {ep["operationId"] for ep in result["endpoints"]}
        assert "getUsers" in operation_ids
        assert "createUser" in operation_ids
        assert "getUserById" in operation_ids

    def test_unsupported_swagger_version_raises(
        self, parser: OpenAPIParser, temp_project_dir: Path
    ):
        """Test that unsupported Swagger version raises exception."""
        spec_content = """swagger: '1.0'
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get users
"""
        spec_path = temp_project_dir / "swagger.yaml"
        spec_path.write_text(spec_content)

        with pytest.raises(UnsupportedVersionException) as exc_info:
            parser.parse(str(spec_path))

        assert "1.0" in str(exc_info.value)
        assert "unsupported" in str(exc_info.value).lower()

    def test_all_supported_swagger_versions(
        self, parser: OpenAPIParser, temp_project_dir: Path
    ):
        """Test that all supported Swagger versions can be parsed."""
        for version in SUPPORTED_SWAGGER_VERSIONS:
            spec_content = f"""swagger: '{version}'
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get users
"""
            spec_path = temp_project_dir / f"swagger_{version}.yaml"
            spec_path.write_text(spec_content)

            result = parser.parse(str(spec_path))

            assert result is not None
            assert result["title"] == "Test API"
            assert result["spec_type"] == "swagger"
            assert result["spec_version"] == version


class TestSwagger2BaseUrlConstruction:
    """Test suite for Swagger 2.0 base URL construction."""

    @pytest.fixture
    def parser(self) -> OpenAPIParser:
        """Create OpenAPIParser instance for testing."""
        return OpenAPIParser()

    def test_base_url_prefers_https(self, parser: OpenAPIParser):
        """Test that _get_base_url_from_swagger prefers HTTPS over HTTP."""
        base_url = parser._get_base_url_from_swagger(
            host="api.example.com",
            base_path="/v2",
            schemes=["http", "https"]
        )

        # basePath is NOT included in base_url (goes to endpoint paths instead)
        assert base_url == "https://api.example.com"

    def test_base_url_with_http_only(self, parser: OpenAPIParser):
        """Test base URL construction with HTTP only."""
        base_url = parser._get_base_url_from_swagger(
            host="localhost:8080",
            base_path="/api",
            schemes=["http"]
        )

        # basePath is NOT included in base_url (goes to endpoint paths instead)
        assert base_url == "http://localhost:8080"

    def test_base_url_with_no_base_path(self, parser: OpenAPIParser):
        """Test base URL construction without basePath."""
        base_url = parser._get_base_url_from_swagger(
            host="api.example.com",
            base_path=None,
            schemes=["https"]
        )

        assert base_url == "https://api.example.com"

    def test_base_url_with_empty_base_path(self, parser: OpenAPIParser):
        """Test base URL construction with empty basePath."""
        base_url = parser._get_base_url_from_swagger(
            host="api.example.com",
            base_path="",
            schemes=["https"]
        )

        assert base_url == "https://api.example.com"

    def test_base_url_defaults_when_all_none(self, parser: OpenAPIParser):
        """Test base URL defaults when all parameters are None."""
        base_url = parser._get_base_url_from_swagger(
            host=None,
            base_path=None,
            schemes=None
        )

        assert base_url == "http://localhost:8080"

    def test_base_url_with_port_in_host(self, parser: OpenAPIParser):
        """Test base URL construction when host includes port."""
        base_url = parser._get_base_url_from_swagger(
            host="petstore.swagger.io:443",
            base_path="/v2",
            schemes=["https"]
        )

        # basePath is NOT included in base_url
        assert base_url == "https://petstore.swagger.io:443"

    def test_base_url_removes_leading_slash_from_base_path(self, parser: OpenAPIParser):
        """Test that basePath is not included in base_url regardless of leading slash."""
        base_url = parser._get_base_url_from_swagger(
            host="api.example.com",
            base_path="/v2",  # With leading slash
            schemes=["https"]
        )

        # basePath should not be in the result at all
        assert base_url == "https://api.example.com"
        assert "/v2" not in base_url


class TestOpenAPI3Support:
    """Test suite for OpenAPI 3.0 support."""

    @pytest.fixture
    def parser(self) -> OpenAPIParser:
        """Create OpenAPIParser instance for testing."""
        return OpenAPIParser()

    def test_openapi3_spec_type_and_version(
        self, parser: OpenAPIParser, project_with_openapi_yaml: Path
    ):
        """Test that OpenAPI 3.0 specs include spec_type and spec_version."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        result = parser.parse(str(spec_path))

        assert result["spec_type"] == "openapi"
        assert result["spec_version"] == "3.0.0"

    def test_openapi3_request_body_detection(
        self, parser: OpenAPIParser, temp_project_dir: Path
    ):
        """Test OpenAPI 3.0 requestBody detection."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    post:
      summary: Create user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
      responses:
        '201':
          description: Created
"""
        spec_path = temp_project_dir / "openapi.yaml"
        spec_path.write_text(spec_content)

        result = parser.parse(str(spec_path))

        post_endpoint = result["endpoints"][0]
        assert post_endpoint["requestBody"] is True

    def test_openapi3_servers_array(
        self, parser: OpenAPIParser, temp_project_dir: Path
    ):
        """Test OpenAPI 3.0 servers array parsing."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
servers:
  - url: https://api.example.com/v1
  - url: http://localhost:3000
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

        result = parser.parse(str(spec_path))

        # Should prefer localhost
        assert result["base_url"] == "http://localhost:3000"

    def test_openapi3_all_versions_supported(
        self, parser: OpenAPIParser, temp_project_dir: Path
    ):
        """Test all OpenAPI 3.x versions are supported."""
        test_versions = ["3.0.0", "3.0.1", "3.0.2", "3.0.3", "3.1.0", "3.1.1"]
        for version in test_versions:
            spec_content = f"""openapi: {version}
info:
  title: Test API
  version: 1.0.0
paths:
  /test:
    get:
      summary: Test endpoint
      responses:
        '200':
          description: Success
"""
            spec_path = temp_project_dir / f"openapi_{version}.yaml"
            spec_path.write_text(spec_content)

            result = parser.parse(str(spec_path))

            assert result is not None
            assert result["spec_type"] == "openapi"
            assert result["spec_version"] == version
            assert result["title"] == "Test API"


class TestRequestBodySupport:
    """Tests for request body schema extraction and sample generation."""

    @pytest.fixture
    def parser(self) -> OpenAPIParser:
        """Provide OpenAPIParser instance."""
        return OpenAPIParser()

    def test_resolve_schema_ref_with_valid_ref(self, parser: OpenAPIParser, temp_project_dir: Path):
        """Test that $ref to components/schemas is resolved correctly."""
        spec_content = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0"},
            "paths": {},
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
                    }
                }
            },
        }

        spec_file = temp_project_dir / "openapi.yaml"
        with open(spec_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(spec_content, f)

        # Parse to initialize _spec
        parser.parse(str(spec_file))

        # Test resolution
        schema_with_ref = {"$ref": "#/components/schemas/User"}
        resolved = parser._resolve_schema_ref(schema_with_ref)

        assert resolved["type"] == "object"
        assert "properties" in resolved
        assert "name" in resolved["properties"]
        assert "age" in resolved["properties"]

    def test_resolve_schema_ref_without_ref(self, parser: OpenAPIParser):
        """Test that schema without $ref is returned unchanged."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        resolved = parser._resolve_schema_ref(schema)
        assert resolved == schema

    def test_parse_endpoints_extracts_content_type_and_schema(
        self, parser: OpenAPIParser, temp_project_dir: Path
    ):
        """Test that endpoints with request body extract content_type and schema."""
        spec_content = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0"},
            "paths": {
                "/users": {
                    "post": {
                        "operationId": "createUser",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"name": {"type": "string"}},
                                    }
                                }
                            }
                        },
                    }
                }
            },
        }

        spec_file = temp_project_dir / "openapi.yaml"
        with open(spec_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(spec_content, f)

        result = parser.parse(str(spec_file))
        endpoint = result["endpoints"][0]

        assert endpoint["requestBody"] is True
        assert endpoint["content_type"] == "application/json"
        assert endpoint["request_body_schema"] is not None
        assert endpoint["request_body_schema"]["type"] == "object"

    def test_generate_sample_body_with_object_schema(self, parser: OpenAPIParser):
        """Test generating sample body from object schema."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string", "format": "email"},
            },
        }

        sample = parser.generate_sample_body(schema)

        assert isinstance(sample, dict)
        assert "name" in sample
        assert "age" in sample
        assert "email" in sample
        assert sample["name"] == "string"
        assert sample["age"] == 0
        assert sample["email"] == "user@example.com"

    def test_generate_sample_body_with_no_schema(self, parser: OpenAPIParser):
        """Test that placeholder is returned when no schema provided."""
        sample = parser.generate_sample_body(None)

        assert isinstance(sample, dict)
        assert "_comment" in sample
        assert "_instruction" in sample
        assert "PLACEHOLDER" in sample["_comment"]

    def test_generate_sample_body_with_array_schema(self, parser: OpenAPIParser):
        """Test generating sample body from array schema."""
        schema = {"type": "array", "items": {"type": "string"}}

        sample = parser.generate_sample_body(schema)

        assert isinstance(sample, list)
        assert len(sample) == 1
        assert sample[0] == "string"

    def test_generate_sample_body_with_non_dict_schema(self, parser: OpenAPIParser):
        """Test that non-dict schema returns placeholder."""
        sample = parser.generate_sample_body("not a dict")

        assert isinstance(sample, dict)
        assert "_comment" in sample
        assert "_instruction" in sample
        assert "Schema format not recognized" in sample["_instruction"]

    def test_generate_sample_body_with_string_type(self, parser: OpenAPIParser):
        """Test generating sample body with string type schema."""
        schema = {"type": "string"}

        sample = parser.generate_sample_body(schema)

        assert sample == "string"

    def test_generate_sample_body_with_integer_type(self, parser: OpenAPIParser):
        """Test generating sample body with integer type schema."""
        schema = {"type": "integer"}

        sample = parser.generate_sample_body(schema)

        assert sample == 0

    def test_generate_sample_body_with_number_type(self, parser: OpenAPIParser):
        """Test generating sample body with number type schema."""
        schema = {"type": "number"}

        sample = parser.generate_sample_body(schema)

        assert sample == 0.0

    def test_generate_sample_body_with_boolean_type(self, parser: OpenAPIParser):
        """Test generating sample body with boolean type schema."""
        schema = {"type": "boolean"}

        sample = parser.generate_sample_body(schema)

        assert sample is True

    def test_generate_sample_body_with_unknown_type(self, parser: OpenAPIParser):
        """Test generating sample body with unknown type returns placeholder."""
        schema = {"type": "unknown_type"}

        sample = parser.generate_sample_body(schema)

        assert isinstance(sample, dict)
        assert "_comment" in sample
        assert "unknown_type" in sample["_instruction"]

    def test_generate_string_sample_with_format_email(self, parser: OpenAPIParser):
        """Test string generation with email format."""
        schema = {"type": "string", "format": "email"}

        result = parser._generate_string_sample(schema)

        assert result == "user@example.com"

    def test_generate_string_sample_with_format_uri(self, parser: OpenAPIParser):
        """Test string generation with URI format."""
        schema = {"type": "string", "format": "uri"}

        result = parser._generate_string_sample(schema)

        assert result == "https://example.com"

    def test_generate_string_sample_with_format_date(self, parser: OpenAPIParser):
        """Test string generation with date format."""
        schema = {"type": "string", "format": "date"}

        result = parser._generate_string_sample(schema)

        assert result == "2025-01-01"

    def test_generate_string_sample_with_format_datetime(self, parser: OpenAPIParser):
        """Test string generation with date-time format."""
        schema = {"type": "string", "format": "date-time"}

        result = parser._generate_string_sample(schema)

        assert result == "2025-01-01T00:00:00Z"

    def test_generate_string_sample_with_format_uuid(self, parser: OpenAPIParser):
        """Test string generation with UUID format."""
        schema = {"type": "string", "format": "uuid"}

        result = parser._generate_string_sample(schema)

        assert result == "123e4567-e89b-12d3-a456-426614174000"

    def test_generate_string_sample_with_example(self, parser: OpenAPIParser):
        """Test string generation with example value."""
        schema = {"type": "string", "example": "test@example.com"}

        result = parser._generate_string_sample(schema)

        assert result == "test@example.com"

    def test_generate_string_sample_with_default(self, parser: OpenAPIParser):
        """Test string generation with default value."""
        schema = {"type": "string", "default": "default_value"}

        result = parser._generate_string_sample(schema)

        assert result == "default_value"

    def test_generate_string_sample_with_enum(self, parser: OpenAPIParser):
        """Test string generation with enum values."""
        schema = {"type": "string", "enum": ["active", "inactive", "pending"]}

        result = parser._generate_string_sample(schema)

        assert result == "active"

    def test_generate_integer_sample_with_example(self, parser: OpenAPIParser):
        """Test integer generation with example value."""
        schema = {"type": "integer", "example": 42}

        result = parser._generate_integer_sample(schema)

        assert result == 42

    def test_generate_integer_sample_with_default(self, parser: OpenAPIParser):
        """Test integer generation with default value."""
        schema = {"type": "integer", "default": 10}

        result = parser._generate_integer_sample(schema)

        assert result == 10

    def test_generate_integer_sample_with_minimum(self, parser: OpenAPIParser):
        """Test integer generation with minimum value."""
        schema = {"type": "integer", "minimum": 5}

        result = parser._generate_integer_sample(schema)

        assert result == 5

    def test_generate_number_sample_with_example(self, parser: OpenAPIParser):
        """Test number generation with example value."""
        schema = {"type": "number", "example": 3.14}

        result = parser._generate_number_sample(schema)

        assert result == 3.14

    def test_generate_number_sample_with_default(self, parser: OpenAPIParser):
        """Test number generation with default value."""
        schema = {"type": "number", "default": 2.5}

        result = parser._generate_number_sample(schema)

        assert result == 2.5

    def test_generate_number_sample_with_minimum(self, parser: OpenAPIParser):
        """Test number generation with minimum value."""
        schema = {"type": "number", "minimum": 1.5}

        result = parser._generate_number_sample(schema)

        assert result == 1.5

    def test_generate_array_sample_with_example(self, parser: OpenAPIParser):
        """Test array generation with example value."""
        schema = {"type": "array", "example": ["item1", "item2"], "items": {"type": "string"}}

        result = parser._generate_array_sample(schema)

        assert result == ["item1", "item2"]

    def test_generate_array_sample_with_integer_items(self, parser: OpenAPIParser):
        """Test array generation with integer items."""
        schema = {"type": "array", "items": {"type": "integer"}}

        result = parser._generate_array_sample(schema)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == 0

    def test_generate_array_sample_with_number_items(self, parser: OpenAPIParser):
        """Test array generation with number items."""
        schema = {"type": "array", "items": {"type": "number"}}

        result = parser._generate_array_sample(schema)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == 0.0

    def test_generate_array_sample_with_boolean_items(self, parser: OpenAPIParser):
        """Test array generation with boolean items."""
        schema = {"type": "array", "items": {"type": "boolean"}}

        result = parser._generate_array_sample(schema)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] is True

    def test_generate_array_sample_with_object_items(self, parser: OpenAPIParser):
        """Test array generation with object items."""
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                }
            }
        }

        result = parser._generate_array_sample(schema)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert "name" in result[0]

    def test_generate_array_sample_with_unknown_item_type(self, parser: OpenAPIParser):
        """Test array generation with unknown item type."""
        schema = {"type": "array", "items": {"type": "custom_type"}}

        result = parser._generate_array_sample(schema)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "<custom_type>"

    def test_generate_array_sample_without_items(self, parser: OpenAPIParser):
        """Test array generation without items schema."""
        schema = {"type": "array"}

        result = parser._generate_array_sample(schema)

        assert isinstance(result, list)
        assert len(result) == 0

    def test_resolve_schema_ref_with_non_dict(self, parser: OpenAPIParser):
        """Test resolving ref with non-dict schema returns original."""
        result = parser._resolve_schema_ref("not a dict")

        assert result == "not a dict"

    def test_resolve_schema_ref_with_external_ref(self, parser: OpenAPIParser):
        """Test resolving external ref returns original schema."""
        schema = {"$ref": "https://example.com/schemas/User"}

        result = parser._resolve_schema_ref(schema)

        assert result == schema

    def test_resolve_schema_ref_with_missing_schema(self, parser: OpenAPIParser):
        """Test resolving ref to non-existent schema returns original."""
        parser._spec = {
            "components": {
                "schemas": {
                    "User": {"type": "object"}
                }
            }
        }
        schema = {"$ref": "#/components/schemas/NonExistent"}

        result = parser._resolve_schema_ref(schema)

        assert result == schema

    def test_resolve_schema_ref_with_nested_ref(self, parser: OpenAPIParser):
        """Test resolving nested $ref references."""
        parser._spec = {
            "components": {
                "schemas": {
                    "User": {"$ref": "#/components/schemas/Person"},
                    "Person": {"type": "object", "properties": {"name": {"type": "string"}}}
                }
            }
        }
        schema = {"$ref": "#/components/schemas/User"}

        result = parser._resolve_schema_ref(schema)

        assert result["type"] == "object"
        assert "name" in result["properties"]
