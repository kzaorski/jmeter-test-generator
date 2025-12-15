"""OpenAPI specification parser for JMeter test generation.

This module provides functionality to parse OpenAPI 3.0.x and Swagger 2.0 specifications
and extract endpoint information for JMeter test plan generation.
"""

import json
from pathlib import Path
from typing import Any, Optional

import yaml

from jmeter_gen.exceptions import (
    AmbiguousPathException,
    EndpointNotFoundException,
    InvalidSpecException,
    UnsupportedVersionException,
)
from jmeter_gen.core.scenario_data import ResolvedPath

# Supported Swagger versions
SUPPORTED_SWAGGER_VERSIONS = ["2.0"]

# Supported HTTP methods
SUPPORTED_METHODS = ["get", "post", "put", "delete", "patch"]


def _is_supported_openapi_version(version: str) -> bool:
    """Check if OpenAPI version is supported.

    Supports all OpenAPI 3.x versions (3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.1.0, 3.1.1, etc.)

    Args:
        version: Version string (e.g., "3.0.3", "3.1.0")

    Returns:
        True if version is 3.x, False otherwise
    """
    try:
        parts = version.split('.')
        if len(parts) >= 1:
            major = int(parts[0])
            return major == 3
    except (ValueError, IndexError):
        return False
    return False


class OpenAPIParser:
    """Parse OpenAPI 3.x and Swagger 2.0 specifications and extract endpoint information."""

    def __init__(self) -> None:
        """Initialize OpenAPI parser."""
        self._spec: dict[str, Any] = {}  # Store full spec for $ref resolution

    def parse(self, spec_path: str) -> dict[str, Any]:
        """Parse OpenAPI specification file.

        Reads and parses an OpenAPI specification file in YAML or JSON format,
        validates the OpenAPI version, extracts metadata and endpoints.

        Args:
            spec_path: Path to OpenAPI spec file (YAML or JSON)

        Returns:
            Dictionary with parsed spec data:
                {
                    "title": str,             # API title from info.title
                    "version": str,           # API version from info.version
                    "base_url": str,          # Base URL from servers
                    "endpoints": List[Dict],  # Parsed endpoints
                    "spec": Dict              # Full spec for reference
                }

        Raises:
            FileNotFoundError: Spec file doesn't exist
            yaml.YAMLError: Invalid YAML syntax
            json.JSONDecodeError: Invalid JSON syntax
            InvalidSpecException: Invalid OpenAPI structure
            UnsupportedVersionException: OpenAPI version not 3.x

        Example:
            >>> parser = OpenAPIParser()
            >>> result = parser.parse("openapi.yaml")
            >>> print(result["title"])
            'My API'
        """
        # Detect format from file extension
        spec_file = Path(spec_path)

        if not spec_file.exists():
            raise FileNotFoundError(f"OpenAPI spec file not found: {spec_path}")

        # Parse file based on extension
        if spec_file.suffix in [".yaml", ".yml"]:
            with open(spec_file, encoding="utf-8") as f:
                spec = yaml.safe_load(f)
        elif spec_file.suffix == ".json":
            with open(spec_file, encoding="utf-8") as f:
                spec = json.load(f)
        else:
            raise InvalidSpecException(
                f"Unsupported file format: {spec_file.suffix}. Expected .yaml, .yml, or .json"
            )

        # Detect specification type and version
        spec_version = None
        spec_type = None

        if "openapi" in spec:
            spec_version = spec["openapi"]
            spec_type = "openapi"
        elif "swagger" in spec:
            spec_version = spec["swagger"]
            spec_type = "swagger"
        else:
            raise InvalidSpecException(
                f"Missing version field in spec: {spec_path}. "
                f"Expected 'openapi' (3.0.x) or 'swagger' (2.0)"
            )

        # Validate version based on spec type
        if spec_type == "openapi":
            if not _is_supported_openapi_version(spec_version):
                raise UnsupportedVersionException(
                    f"Unsupported OpenAPI version: {spec_version}. "
                    f"Supported versions: 3.x (e.g., 3.0.0, 3.0.3, 3.1.0)"
                )
        elif spec_type == "swagger":
            if spec_version not in SUPPORTED_SWAGGER_VERSIONS:
                raise UnsupportedVersionException(
                    f"Unsupported Swagger version: {spec_version}. "
                    f"Supported versions: {', '.join(SUPPORTED_SWAGGER_VERSIONS)}"
                )

        # Validate required fields
        if "info" not in spec:
            raise InvalidSpecException(f"Missing required field 'info' in spec: {spec_path}")

        if "paths" not in spec:
            raise InvalidSpecException(f"Missing required field 'paths' in spec: {spec_path}")

        # Extract metadata
        info = spec["info"]
        title = info.get("title", "Untitled API")
        api_version = info.get("version", "1.0.0")

        # Extract base URL based on spec type
        # Also extract basePath for Swagger 2.0 to prepend to endpoint paths
        path_prefix = ""
        if spec_type == "openapi":
            # OpenAPI 3.0 uses servers array
            servers = spec.get("servers", [])
            base_url = self._get_base_url(servers)
        elif spec_type == "swagger":
            # Swagger 2.0 uses host, basePath, schemes
            host = spec.get("host")
            base_path = spec.get("basePath")
            schemes = spec.get("schemes")
            base_url = self._get_base_url_from_swagger(host, base_path, schemes)
            # Store basePath to prepend to endpoint paths
            path_prefix = base_path if base_path else ""

        # Store spec for $ref resolution
        self._spec = spec

        # Parse endpoints (with path prefix for Swagger 2.0)
        paths = spec["paths"]
        endpoints = self._parse_endpoints(paths, path_prefix)

        return {
            "title": title,
            "version": api_version,
            "base_url": base_url,
            "endpoints": endpoints,
            "spec": spec,
            "spec_type": spec_type,  # "openapi" or "swagger"
            "spec_version": spec_version,  # "3.0.0" or "2.0"
        }

    def _resolve_schema_ref(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Resolve $ref in schema to actual schema definition.

        Recursively resolves JSON Schema $ref pointers to components/schemas.
        Handles nested references and prevents infinite loops.

        Args:
            schema: Schema object that may contain $ref

        Returns:
            Resolved schema object

        Example:
            >>> parser = OpenAPIParser()
            >>> schema = {"$ref": "#/components/schemas/User"}
            >>> resolved = parser._resolve_schema_ref(schema)
            >>> resolved["type"]
            'object'
        """
        if not isinstance(schema, dict):
            return schema

        # Check if schema contains $ref
        if "$ref" not in schema:
            return schema

        ref_path = schema["$ref"]

        # Only handle local references to components/schemas
        if not ref_path.startswith("#/components/schemas/"):
            # Return original schema if $ref is external or unsupported
            return schema

        # Extract schema name from #/components/schemas/SchemaName
        schema_name = ref_path.split("/")[-1]

        # Get schema from components/schemas
        components = self._spec.get("components", {})
        schemas = components.get("schemas", {})

        if schema_name not in schemas:
            # Schema not found, return original
            return schema

        resolved_schema = schemas[schema_name]

        # Recursively resolve nested $refs
        if isinstance(resolved_schema, dict) and "$ref" in resolved_schema:
            return self._resolve_schema_ref(resolved_schema)

        return resolved_schema

    def generate_sample_body(self, schema: Optional[dict[str, Any]]) -> dict[str, Any]:
        """Generate sample request body from JSON Schema.

        Creates a sample JSON object based on the schema definition. Uses defaults,
        examples, or type-appropriate placeholder values. If no schema provided,
        returns a placeholder object with instructions.

        Args:
            schema: JSON Schema object (can be None)

        Returns:
            Dictionary representing sample request body

        Example:
            >>> parser = OpenAPIParser()
            >>> schema = {"type": "object", "properties": {"name": {"type": "string"}}}
            >>> parser.generate_sample_body(schema)
            {'name': 'string'}
        """
        # If no schema, return placeholder with manual instruction
        if not schema:
            return {
                "_comment": "PLACEHOLDER: Add your request body here",
                "_instruction": "Replace this object with actual request data"
            }

        # If schema is not a dict, return placeholder
        if not isinstance(schema, dict):
            return {
                "_comment": "PLACEHOLDER: Add your request body here",
                "_instruction": "Schema format not recognized"
            }

        # Generate sample based on schema type
        schema_type = schema.get("type", "object")

        if schema_type == "object":
            return self._generate_object_sample(schema)
        elif schema_type == "array":
            return self._generate_array_sample(schema)
        elif schema_type == "string":
            return self._generate_string_sample(schema)
        elif schema_type == "integer":
            return self._generate_integer_sample(schema)
        elif schema_type == "number":
            return self._generate_number_sample(schema)
        elif schema_type == "boolean":
            return schema.get("default", True)
        else:
            # Unknown type, return placeholder
            return {
                "_comment": "PLACEHOLDER: Add your request body here",
                "_instruction": f"Schema type '{schema_type}' not supported"
            }

    def _generate_object_sample(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate sample object from object schema."""
        sample = {}
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for prop_name, prop_schema in properties.items():
            # Check if property has example
            if "example" in prop_schema:
                sample[prop_name] = prop_schema["example"]
            # Check if property has default
            elif "default" in prop_schema:
                sample[prop_name] = prop_schema["default"]
            # Generate based on type
            else:
                prop_type = prop_schema.get("type", "string")

                if prop_type == "string":
                    sample[prop_name] = self._generate_string_sample(prop_schema)
                elif prop_type == "integer":
                    sample[prop_name] = self._generate_integer_sample(prop_schema)
                elif prop_type == "number":
                    sample[prop_name] = self._generate_number_sample(prop_schema)
                elif prop_type == "boolean":
                    sample[prop_name] = prop_schema.get("default", True)
                elif prop_type == "array":
                    sample[prop_name] = self._generate_array_sample(prop_schema)
                elif prop_type == "object":
                    # Recursive call for nested objects
                    sample[prop_name] = self._generate_object_sample(prop_schema)
                else:
                    # Unknown type
                    sample[prop_name] = f"<{prop_type}>"

        # If no properties generated and it's not required, return minimal object
        if not sample:
            return {"_placeholder": "Add object properties here"}

        return sample

    def _generate_array_sample(self, schema: dict[str, Any]) -> list[Any]:
        """Generate sample array from array schema."""
        items_schema = schema.get("items", {})

        # Check for example in array schema
        if "example" in schema:
            return schema["example"]

        # Generate one sample item
        if items_schema:
            item_type = items_schema.get("type", "string")

            if item_type == "string":
                sample_item = self._generate_string_sample(items_schema)
            elif item_type == "integer":
                sample_item = self._generate_integer_sample(items_schema)
            elif item_type == "number":
                sample_item = self._generate_number_sample(items_schema)
            elif item_type == "boolean":
                sample_item = items_schema.get("default", True)
            elif item_type == "object":
                sample_item = self._generate_object_sample(items_schema)
            else:
                sample_item = f"<{item_type}>"

            return [sample_item]

        return []

    def _generate_string_sample(self, schema: dict[str, Any]) -> str:
        """Generate sample string from string schema."""
        # Check for example
        if "example" in schema:
            return str(schema["example"])

        # Check for default
        if "default" in schema:
            return str(schema["default"])

        # Check for enum
        if "enum" in schema and schema["enum"]:
            return str(schema["enum"][0])

        # Check for format hints
        format_hint = schema.get("format", "")
        if format_hint == "email":
            return "user@example.com"
        elif format_hint == "uri":
            return "https://example.com"
        elif format_hint == "date":
            return "2025-01-01"
        elif format_hint == "date-time":
            return "2025-01-01T00:00:00Z"
        elif format_hint == "uuid":
            return "123e4567-e89b-12d3-a456-426614174000"

        # Default string
        return "string"

    def _generate_integer_sample(self, schema: dict[str, Any]) -> int:
        """Generate sample integer from integer schema."""
        # Check for example
        if "example" in schema:
            return int(schema["example"])

        # Check for default
        if "default" in schema:
            return int(schema["default"])

        # Check for minimum
        if "minimum" in schema:
            return int(schema["minimum"])

        # Default integer
        return 0

    def _generate_number_sample(self, schema: dict[str, Any]) -> float:
        """Generate sample number from number schema."""
        # Check for example
        if "example" in schema:
            return float(schema["example"])

        # Check for default
        if "default" in schema:
            return float(schema["default"])

        # Check for minimum
        if "minimum" in schema:
            return float(schema["minimum"])

        # Default number
        return 0.0

    def _parse_endpoints(self, paths: dict[str, Any], path_prefix: str = "") -> list[dict[str, Any]]:
        """Extract endpoints from OpenAPI paths.

        Iterates through all paths and HTTP methods to extract endpoint
        information including method, parameters, and request body presence.

        Args:
            paths: OpenAPI paths object
            path_prefix: Optional prefix to prepend to all paths (e.g., "/v2" for Swagger 2.0 basePath)

        Returns:
            List of endpoint dictionaries with structure:
                {
                    "path": str,              # "/api/users/{id}" (with path_prefix prepended if provided)
                    "method": str,            # "GET", "POST" (uppercase)
                    "operationId": str,       # "getUser"
                    "summary": str,           # "Retrieve user by ID"
                    "description": str,       # Longer description
                    "requestBody": bool,      # True if has request body
                    "parameters": List[Dict]  # List of parameters
                }

        Example:
            >>> parser = OpenAPIParser()
            >>> paths = {"/users": {"get": {"summary": "Get users"}}}
            >>> endpoints = parser._parse_endpoints(paths, "/v2")
            >>> endpoints[0]["path"]
            '/v2/users'
        """
        endpoints = []

        for path, path_item in paths.items():
            # Prepend path_prefix if provided (for Swagger 2.0 basePath)
            full_path = f"{path_prefix}{path}" if path_prefix else path
            # Iterate through HTTP methods
            for method in SUPPORTED_METHODS:
                if method not in path_item:
                    continue

                operation = path_item[method]

                # Extract operation details
                operation_id = operation.get(
                    "operationId", f"{method}_{path.replace('/', '_').strip('_')}"
                )
                summary = operation.get("summary", "")
                description = operation.get("description", "")

                # Check for request body and extract schema
                # OpenAPI 3.0 style: requestBody field
                # Swagger 2.0 style: body or formData parameters
                has_request_body = False
                content_type: Optional[str] = None
                request_body_schema: Optional[dict[str, Any]] = None

                if "requestBody" in operation:
                    # OpenAPI 3.0
                    has_request_body = True
                    request_body_obj = operation["requestBody"]

                    # Extract content type and schema
                    content = request_body_obj.get("content", {})
                    if content:
                        # Get first content type (usually application/json)
                        content_type = list(content.keys())[0]
                        media_type_obj = content[content_type]

                        # Extract schema
                        if "schema" in media_type_obj:
                            schema = media_type_obj["schema"]
                            # Resolve $ref if present
                            request_body_schema = self._resolve_schema_ref(schema)
                else:
                    # Swagger 2.0 - check parameters for body or formData
                    parameters_list = operation.get("parameters", [])
                    for param in parameters_list:
                        if param.get("in") == "body":
                            has_request_body = True
                            content_type = "application/json"  # Default for Swagger 2.0 body
                            # Extract schema from parameter
                            if "schema" in param:
                                schema = param["schema"]
                                request_body_schema = self._resolve_schema_ref(schema)
                            break
                        elif param.get("in") == "formData":
                            has_request_body = True
                            content_type = "application/x-www-form-urlencoded"
                            # Form data doesn't have unified schema in Swagger 2.0
                            break

                # Extract parameters
                parameters = operation.get("parameters", [])

                # Extract expected response codes from responses section
                responses = operation.get("responses", {})
                expected_response_codes = []

                # Get success response codes (2xx range)
                for status_code in responses.keys():
                    try:
                        code_int = int(status_code)
                        if 200 <= code_int < 300:
                            expected_response_codes.append(status_code)
                    except (ValueError, TypeError):
                        # Skip "default" or other non-numeric codes
                        continue

                # Note: If no 2xx codes found, expected_response_codes stays empty
                # (no fallback to 200/201 - assertions only for explicitly defined codes)

                # Create endpoint dict (using full_path which includes path_prefix)
                endpoint = {
                    "path": full_path,
                    "method": method.upper(),  # Uppercase method
                    "operationId": operation_id,
                    "summary": summary,
                    "description": description,
                    "requestBody": has_request_body,
                    "content_type": content_type,
                    "request_body_schema": request_body_schema,
                    "parameters": parameters,
                    "expected_response_codes": expected_response_codes,
                }

                endpoints.append(endpoint)

        return endpoints

    def _get_base_url(self, servers: list[dict[str, Any]]) -> str:
        """Extract base URL from servers, prefer localhost.

        Selects the appropriate base URL from the OpenAPI servers array.
        Preference order:
        1. Server with "localhost" in URL
        2. First server in list
        3. Default "http://localhost:8080" if no servers

        Args:
            servers: OpenAPI servers array

        Returns:
            Base URL string

        Example:
            >>> parser = OpenAPIParser()
            >>> servers = [{"url": "http://localhost:3000"}]
            >>> parser._get_base_url(servers)
            'http://localhost:3000'
        """
        # Default if no servers
        if not servers:
            return "http://localhost:8080"

        # Prefer localhost server
        for server in servers:
            url: str = str(server.get("url", ""))
            if "localhost" in url.lower():
                return url

        # Otherwise return first server
        return str(servers[0].get("url", "http://localhost:8080"))

    def _get_base_url_from_swagger(
        self,
        host: Optional[str],
        base_path: Optional[str],
        schemes: Optional[list[str]]
    ) -> str:
        """Extract base URL from Swagger 2.0 spec fields.

        Constructs base URL from separate host and schemes fields.
        Note: basePath is NOT included in the returned URL - it should be
        prepended to individual endpoint paths instead.

        Preference order for scheme:
        1. HTTPS if available in schemes
        2. First scheme in list
        3. HTTP as default

        Args:
            host: Server hostname from 'host' field (e.g., "petstore.swagger.io")
            base_path: Path prefix from 'basePath' field (e.g., "/v2") - NOT USED in returned URL
            schemes: Protocol schemes from 'schemes' array (e.g., ["https", "http"])

        Returns:
            Constructed base URL string (without basePath)

        Example:
            >>> parser = OpenAPIParser()
            >>> parser._get_base_url_from_swagger(
            ...     "petstore.swagger.io", "/v2", ["https", "http"]
            ... )
            'https://petstore.swagger.io'
        """
        # Default values
        if not host:
            host = "localhost:8080"
        if not schemes:
            schemes = ["http"]

        # Prefer https over http, otherwise use first scheme
        scheme = "https" if "https" in schemes else schemes[0]

        # Construct base URL (without basePath)
        base_url = f"{scheme}://{host}"

        return base_url

    # === v2 Methods for Scenario Support ===

    def get_endpoint_by_operation_id(self, operation_id: str) -> Optional[dict[str, Any]]:
        """Get endpoint data by operationId.

        Args:
            operation_id: The operationId to search for

        Returns:
            Endpoint dictionary if found, None otherwise

        Example:
            >>> parser = OpenAPIParser()
            >>> parser.parse("openapi.yaml")
            >>> endpoint = parser.get_endpoint_by_operation_id("getUser")
        """
        if not self._spec:
            return None

        paths = self._spec.get("paths", {})
        for path, path_item in paths.items():
            for method in SUPPORTED_METHODS:
                if method not in path_item:
                    continue
                operation = path_item[method]
                if operation.get("operationId") == operation_id:
                    return {
                        "path": path,
                        "method": method.upper(),
                        "operationId": operation_id,
                        "operation": operation,
                    }
        return None

    def get_endpoint_by_method_path(
        self, method: str, path: str
    ) -> Optional[dict[str, Any]]:
        """Get endpoint data by HTTP method and path.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path

        Returns:
            Endpoint dictionary if found, None otherwise
        """
        if not self._spec:
            return None

        method_lower = method.lower()
        paths = self._spec.get("paths", {})

        if path in paths and method_lower in paths[path]:
            operation = paths[path][method_lower]
            return {
                "path": path,
                "method": method.upper(),
                "operationId": operation.get("operationId", ""),
                "operation": operation,
            }
        return None

    def get_all_operation_ids(self) -> list[str]:
        """Get list of all operationIds in the spec.

        Returns:
            List of operationId strings
        """
        operation_ids: list[str] = []

        if not self._spec:
            return operation_ids

        paths = self._spec.get("paths", {})
        for path_item in paths.values():
            for method in SUPPORTED_METHODS:
                if method not in path_item:
                    continue
                operation = path_item[method]
                op_id = operation.get("operationId")
                if op_id:
                    operation_ids.append(op_id)

        return operation_ids

    def get_all_paths(self) -> dict[str, list[str]]:
        """Get all paths with their supported methods.

        Returns:
            Dictionary mapping path to list of methods
            Example: {"/users": ["GET", "POST"], "/users/{id}": ["GET", "PUT", "DELETE"]}
        """
        result: dict[str, list[str]] = {}

        if not self._spec:
            return result

        paths = self._spec.get("paths", {})
        for path, path_item in paths.items():
            methods = []
            for method in SUPPORTED_METHODS:
                if method in path_item:
                    methods.append(method.upper())
            if methods:
                result[path] = methods

        return result

    def extract_response_schema(
        self,
        operation_id: Optional[str] = None,
        method: Optional[str] = None,
        path: Optional[str] = None,
        status_code: str = "200",
    ) -> Optional[dict[str, Any]]:
        """Extract response schema for an endpoint.

        Can lookup endpoint by operationId or method+path.
        Handles both OpenAPI 3.0 and Swagger 2.0 response schemas.

        Args:
            operation_id: operationId to lookup
            method: HTTP method (if using method+path)
            path: URL path (if using method+path)
            status_code: Response status code (default: "200")

        Returns:
            Response schema dictionary or None
        """
        if not self._spec:
            return None

        # Find the operation
        operation = None
        if operation_id:
            endpoint = self.get_endpoint_by_operation_id(operation_id)
            if endpoint:
                operation = endpoint.get("operation")
        elif method and path:
            endpoint = self.get_endpoint_by_method_path(method, path)
            if endpoint:
                operation = endpoint.get("operation")

        if not operation:
            return None

        responses = operation.get("responses", {})

        # Try requested status code, then fallbacks
        for code in [status_code, "201", "200", "default"]:
            if code in responses:
                response = responses[code]
                schema = self._extract_schema_from_response(response)
                if schema:
                    return self._resolve_schema_ref(schema)

        return None

    def _extract_schema_from_response(
        self, response: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Extract schema from response object.

        Handles both OpenAPI 3.0 (content.application/json.schema)
        and Swagger 2.0 (schema) formats.
        """
        # OpenAPI 3.0: responses.{code}.content.application/json.schema
        content = response.get("content", {})
        if content:
            # Prefer application/json
            for content_type in ["application/json", "*/*"]:
                if content_type in content:
                    return content[content_type].get("schema")
            # Try first available content type
            if content:
                first_type = list(content.keys())[0]
                return content[first_type].get("schema")

        # Swagger 2.0: responses.{code}.schema
        if "schema" in response:
            return response["schema"]

        return None

    def resolve_short_path(self, method: str, short_path: str) -> ResolvedPath:
        """Resolve shortened path to full path from spec.

        Matching rules:
        1. Exact match first
        2. Suffix match (paths ending with short_path)

        Args:
            method: HTTP method
            short_path: Short path to resolve (e.g., "/trigger")

        Returns:
            ResolvedPath with full path information

        Raises:
            EndpointNotFoundException: No match found
            AmbiguousPathException: Multiple matches found
        """
        method_upper = method.upper()
        all_paths = self.get_all_paths()

        # Exact match
        if short_path in all_paths:
            if method_upper in all_paths[short_path]:
                return ResolvedPath(
                    full_path=short_path,
                    method=method_upper,
                    match_type="exact",
                )

        # Suffix match
        matches = self.find_suffix_matches(method, short_path)

        if not matches:
            raise EndpointNotFoundException(
                f"No endpoint found matching {method_upper} {short_path}"
            )

        if len(matches) == 1:
            return ResolvedPath(
                full_path=matches[0],
                method=method_upper,
                match_type="suffix",
            )

        # Multiple matches - ambiguous
        raise AmbiguousPathException(short_path, matches)

    def find_suffix_matches(self, method: str, suffix: str) -> list[str]:
        """Find all paths ending with given suffix for given method.

        Args:
            method: HTTP method
            suffix: Path suffix to match

        Returns:
            List of matching full paths
        """
        method_upper = method.upper()
        all_paths = self.get_all_paths()
        matches: list[str] = []

        for path, methods in all_paths.items():
            if method_upper in methods:
                # Check if path ends with suffix
                # Handle both "/trigger" matching "/api/v2/trigger"
                # and "trigger" matching "/api/v2/trigger"
                if path == suffix or path.endswith(suffix):
                    matches.append(path)

        return matches
