"""JMX Generator for creating JMeter test plans from OpenAPI specifications.

This module provides the JMXGenerator class for generating JMeter JMX files
from parsed OpenAPI specifications. It creates XML-based test plans with
HTTP Request Defaults, Thread Groups, HTTP Samplers, and Response Assertions.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse
from xml.dom import minidom

from jmeter_gen.core.openapi_parser import OpenAPIParser
from jmeter_gen.exceptions import JMXGenerationException


class JMXGenerator:
    """Generates JMeter JMX test plans from OpenAPI specifications.

    This class creates JMeter test plans with the following structure:
    - Test Plan (root container)
    - HTTP Request Defaults (centralizes server configuration at TestPlan level)
    - Thread Group (defines load profile: threads, ramp-up, duration)
    - HTTP Samplers (one per endpoint, inherits server config from defaults)
    - Response Assertions (validates response codes)

    The generator uses the HTTP Request Defaults pattern where server
    configuration (domain, port, protocol) is defined once at the TestPlan
    level and inherited by all HTTP Samplers. This enables environment-specific
    testing and allows the configuration to apply globally to all ThreadGroups.
    """

    # Default test plan configuration
    # Set to 1 thread, 1 iteration for single-run testing
    DEFAULT_THREADS = 1
    DEFAULT_RAMPUP = 0
    DEFAULT_DURATION = None  # No duration controller - use loop count instead

    def __init__(self) -> None:
        """Initialize the JMX Generator."""
        pass

    def generate(
        self,
        spec_data: dict,
        output_path: str,
        base_url: Optional[str] = None,
        endpoints: Optional[list[str]] = None,
        threads: int = DEFAULT_THREADS,
        rampup: int = DEFAULT_RAMPUP,
        duration: Optional[int] = DEFAULT_DURATION,
    ) -> dict:
        """Generate JMeter JMX file from OpenAPI specification.

        Creates a complete JMeter test plan with HTTP Request Defaults,
        Thread Group, HTTP Samplers for each endpoint, and Response Assertions.

        Args:
            spec_data: Parsed OpenAPI specification from OpenAPIParser.parse()
                      Must contain: title, version, base_url, endpoints
            output_path: Path where to save the JMX file
            base_url: Override base URL from spec (e.g., for different environments)
                     If None, uses spec_data["base_url"]
            endpoints: Filter endpoints by operationId (None = include all)
            threads: Number of virtual users (default: 1)
            rampup: Ramp-up period in seconds (default: 0)
            duration: Test duration in seconds (default: None - uses loop count instead)

        Returns:
            Dictionary with generation results:
            {
                "success": bool,
                "jmx_path": str,
                "samplers_created": int,
                "assertions_added": int,
                "threads": int,
                "rampup": int,
                "duration": int,
                "summary": str
            }

        Raises:
            JMXGenerationException: If generation fails due to invalid data or write errors
        """
        try:
            # Use base_url from parameter or fall back to spec_data
            effective_base_url = base_url or spec_data.get("base_url", "http://localhost")

            # Parse base URL to extract domain, port, protocol
            domain, port, protocol = self._parse_url(effective_base_url)

            # Filter endpoints if specific operationIds requested
            all_endpoints = spec_data.get("endpoints", [])
            if endpoints:
                filtered_endpoints = [
                    ep for ep in all_endpoints if ep.get("operationId") in endpoints
                ]
            else:
                filtered_endpoints = all_endpoints

            if not filtered_endpoints:
                raise JMXGenerationException(
                    f"No endpoints found to generate. "
                    f"Available endpoints: {[ep.get('operationId') for ep in all_endpoints]}"
                )

            # Create root jmeterTestPlan element
            jmeter_test_plan = ET.Element(
                "jmeterTestPlan", {"version": "1.2", "properties": "5.0", "jmeter": "5.0"}
            )

            # Create main hashTree
            main_hashtree = ET.SubElement(jmeter_test_plan, "hashTree")

            # Create Test Plan
            test_plan = self._create_test_plan(
                spec_data.get("title", "API Test Plan"), spec_data.get("version", "1.0")
            )
            main_hashtree.append(test_plan)

            # Create Test Plan hashTree
            test_plan_hashtree = ET.SubElement(main_hashtree, "hashTree")

            # CRITICAL: Add HTTP Request Defaults at TestPlan level (before ThreadGroups)
            # This allows configuration to apply globally to all ThreadGroups
            http_defaults = self._create_http_defaults(domain, port, protocol)
            test_plan_hashtree.append(http_defaults)

            # HTTP Defaults hashTree (empty)
            ET.SubElement(test_plan_hashtree, "hashTree")

            # Add listeners to Test Plan (before Thread Group)
            # View Results Tree listener
            view_results_tree = self._create_view_results_tree_listener()
            test_plan_hashtree.append(view_results_tree)
            ET.SubElement(test_plan_hashtree, "hashTree")

            # Aggregate Report listener
            aggregate_report = self._create_aggregate_report_listener()
            test_plan_hashtree.append(aggregate_report)
            ET.SubElement(test_plan_hashtree, "hashTree")

            # Create Thread Group
            thread_group = self._create_thread_group(threads, rampup, duration)
            test_plan_hashtree.append(thread_group)

            # Create Thread Group hashTree
            thread_group_hashtree = ET.SubElement(test_plan_hashtree, "hashTree")

            # Create OpenAPIParser instance for generating sample bodies
            parser = OpenAPIParser()

            # Create HTTP Samplers and Assertions for each endpoint
            samplers_created = 0
            assertions_added = 0
            headers_added = 0

            for endpoint in filtered_endpoints:
                # Generate request body if endpoint has one
                request_body_json = None
                has_request_body = endpoint.get("requestBody", False)
                content_type = endpoint.get("content_type")
                request_body_schema = endpoint.get("request_body_schema")

                if has_request_body and content_type:
                    # Generate sample body from schema
                    sample_body = parser.generate_sample_body(request_body_schema)
                    # Convert to JSON string with pretty formatting
                    request_body_json = json.dumps(sample_body, indent=2)

                # Create HTTP Sampler (domain/port/protocol are EMPTY - inherited)
                # Returns tuple: (sampler, header_params_dict)
                sampler, header_params = self._create_http_sampler(endpoint, request_body_json)
                thread_group_hashtree.append(sampler)
                samplers_created += 1

                # Create Sampler hashTree
                sampler_hashtree = ET.SubElement(thread_group_hashtree, "hashTree")

                # Merge Content-Type with parameter headers
                headers_to_add: dict[str, str] = {}

                # Add Content-Type if endpoint has request body
                if has_request_body and content_type:
                    headers_to_add["Content-Type"] = content_type

                # Merge header parameters
                headers_to_add.update(header_params)

                # Add HeaderManager if there are any headers
                if headers_to_add:
                    header_manager = self._create_header_manager(headers_to_add)
                    sampler_hashtree.append(header_manager)
                    headers_added += 1
                    # HeaderManager hashTree (empty)
                    ET.SubElement(sampler_hashtree, "hashTree")

                # Create Response Assertions
                assertions = self._create_assertions(endpoint)
                for assertion in assertions:
                    sampler_hashtree.append(assertion)
                    assertions_added += 1
                    # Assertion hashTree (empty)
                    ET.SubElement(sampler_hashtree, "hashTree")

            # Convert to pretty-printed XML string
            xml_string = self._prettify_xml(jmeter_test_plan)

            # Write to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(xml_string, encoding="utf-8")

            # Generate summary
            if duration is not None:
                load_profile = f"{threads} threads, {rampup}s ramp-up, {duration}s duration"
            else:
                load_profile = f"{threads} threads, {rampup}s ramp-up, 1 iteration"

            summary = (
                f"Generated JMX test plan with {samplers_created} HTTP samplers, "
                f"{headers_added} header managers, and {assertions_added} assertions. "
                f"Load profile: {load_profile}."
            )

            return {
                "success": True,
                "jmx_path": str(output_file.absolute()),
                "samplers_created": samplers_created,
                "headers_added": headers_added,
                "assertions_added": assertions_added,
                "threads": threads,
                "rampup": rampup,
                "duration": duration,
                "summary": summary,
            }

        except Exception as e:
            if isinstance(e, JMXGenerationException):
                raise
            raise JMXGenerationException(f"Failed to generate JMX file: {str(e)}") from e

    def _parse_url(self, url: str) -> tuple[str, str, str]:
        """Parse URL to extract domain, port, and protocol.

        Args:
            url: URL to parse (e.g., "http://localhost:8080/api")

        Returns:
            Tuple of (domain, port, protocol)
            Example: ("localhost", "8080", "http")

        Raises:
            JMXGenerationException: If URL parsing fails
        """
        try:
            parsed = urlparse(url)

            # Extract protocol (default to http if not specified)
            protocol = parsed.scheme or "http"

            # Extract domain
            domain = parsed.hostname or "localhost"

            # Extract port (empty string if default port)
            if parsed.port:
                port = str(parsed.port)
            else:
                # Use empty string for default ports (JMeter will use protocol defaults)
                port = ""

            return domain, port, protocol

        except Exception as e:
            raise JMXGenerationException(f"Failed to parse URL '{url}': {str(e)}") from e

    def _prettify_xml(self, elem: ET.Element) -> str:
        """Convert XML Element to pretty-printed string with 2-space indentation.

        Args:
            elem: XML Element to prettify

        Returns:
            Pretty-printed XML string with 2-space indentation
        """
        # Convert to string
        rough_string = ET.tostring(elem, encoding="unicode")

        # Parse with minidom for pretty printing
        reparsed = minidom.parseString(rough_string)

        # Pretty print with 2-space indentation
        pretty_xml = reparsed.toprettyxml(indent="  ")

        # Remove extra blank lines
        lines = [line for line in pretty_xml.split("\n") if line.strip()]

        return "\n".join(lines)

    def _create_test_plan(self, title: str, version: str) -> ET.Element:
        """Create JMeter Test Plan element.

        Args:
            title: API title from OpenAPI spec
            version: API version from OpenAPI spec

        Returns:
            TestPlan XML Element
        """
        test_plan = ET.Element(
            "TestPlan",
            {
                "guiclass": "TestPlanGui",
                "testclass": "TestPlan",
                "testname": f"{title} v{version}",
                "enabled": "true",
            },
        )

        # Add functional mode property
        ET.SubElement(test_plan, "boolProp", {"name": "TestPlan.functional_mode"}).text = "false"

        # Add serialize threadgroups property
        ET.SubElement(
            test_plan, "boolProp", {"name": "TestPlan.serialize_threadgroups"}
        ).text = "false"

        # Add elementProp for Test Plan arguments
        elem_prop = ET.SubElement(
            test_plan,
            "elementProp",
            {
                "name": "TestPlan.user_defined_variables",
                "elementType": "Arguments",
                "guiclass": "ArgumentsPanel",
                "testclass": "Arguments",
                "testname": "User Defined Variables",
                "enabled": "true",
            },
        )

        # Add empty collectionProp for arguments
        ET.SubElement(elem_prop, "collectionProp", {"name": "Arguments.arguments"})

        return test_plan

    def _create_thread_group(self, threads: int, rampup: int, duration: Optional[int]) -> ET.Element:
        """Create JMeter Thread Group element.

        Args:
            threads: Number of virtual users
            rampup: Ramp-up period in seconds
            duration: Test duration in seconds (None for iteration-based testing)

        Returns:
            ThreadGroup XML Element
        """
        thread_group = ET.Element(
            "ThreadGroup",
            {
                "guiclass": "ThreadGroupGui",
                "testclass": "ThreadGroup",
                "testname": "Thread Group",
                "enabled": "true",
            },
        )

        # Number of threads
        ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.num_threads"}).text = str(
            threads
        )

        # Ramp-up time
        ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.ramp_time"}).text = str(
            rampup
        )

        # Duration and scheduler configuration
        if duration is not None:
            # Duration-based testing: use scheduler with specified duration
            ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.duration"}).text = str(
                duration
            )
            ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.delay"}).text = "0"
            ET.SubElement(thread_group, "boolProp", {"name": "ThreadGroup.scheduler"}).text = "true"
            loop_count = "-1"  # Loop forever, duration limits execution
        else:
            # Iteration-based testing: no scheduler, fixed loop count
            ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.duration"}).text = ""
            ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.delay"}).text = ""
            ET.SubElement(thread_group, "boolProp", {"name": "ThreadGroup.scheduler"}).text = "false"
            loop_count = "1"  # Single iteration

        # Loop Controller
        loop_controller = ET.SubElement(
            thread_group,
            "elementProp",
            {
                "name": "ThreadGroup.main_controller",
                "elementType": "LoopController",
                "guiclass": "LoopControlPanel",
                "testclass": "LoopController",
                "testname": "Loop Controller",
                "enabled": "true",
            },
        )

        # Loop count: -1 for duration-based, 1 for iteration-based
        ET.SubElement(loop_controller, "stringProp", {"name": "LoopController.loops"}).text = loop_count

        # Continue forever
        ET.SubElement(
            loop_controller, "boolProp", {"name": "LoopController.continue_forever"}
        ).text = "false"

        return thread_group

    def _create_http_defaults(self, domain: str, port: str, protocol: str) -> ET.Element:
        """Create HTTP Request Defaults (ConfigTestElement).

        CRITICAL: This element centralizes server configuration so individual
        HTTP Samplers can have empty domain/port/protocol and inherit these values.
        This enables environment-specific testing (dev/staging/prod).

        Args:
            domain: Server domain (e.g., "localhost")
            port: Server port (e.g., "8080" or "" for default)
            protocol: Protocol (e.g., "http" or "https")

        Returns:
            ConfigTestElement XML Element for HTTP Request Defaults
        """
        config = ET.Element(
            "ConfigTestElement",
            {
                "guiclass": "HttpDefaultsGui",
                "testclass": "ConfigTestElement",
                "testname": "HTTP Request Defaults",
                "enabled": "true",
            },
        )

        # Add elementProp for HTTP Sampler arguments
        elem_prop = ET.SubElement(
            config,
            "elementProp",
            {
                "name": "HTTPsampler.Arguments",
                "elementType": "Arguments",
                "guiclass": "HTTPArgumentsPanel",
                "testclass": "Arguments",
                "testname": "User Defined Variables",
                "enabled": "true",
            },
        )

        # Add empty collectionProp for arguments
        ET.SubElement(elem_prop, "collectionProp", {"name": "Arguments.arguments"})

        # Server domain
        ET.SubElement(config, "stringProp", {"name": "HTTPSampler.domain"}).text = domain

        # Server port (empty string for default)
        ET.SubElement(config, "stringProp", {"name": "HTTPSampler.port"}).text = port

        # Protocol
        ET.SubElement(config, "stringProp", {"name": "HTTPSampler.protocol"}).text = protocol

        return config

    def _create_header_manager(self, headers: dict[str, str]) -> ET.Element:
        """Create HTTP Header Manager with multiple headers.

        Adds a HeaderManager element that can set multiple HTTP headers,
        including Content-Type for request bodies and custom headers from
        OpenAPI parameters.

        Args:
            headers: Dictionary of header name -> value pairs
                    (e.g., {"Content-Type": "application/json", "Authorization": "Bearer ${token}"})

        Returns:
            HeaderManager XML Element

        Example:
            >>> generator = JMXGenerator()
            >>> headers = {"Content-Type": "application/json", "X-API-Key": "${api_key}"}
            >>> header_mgr = generator._create_header_manager(headers)
        """
        header_manager = ET.Element(
            "HeaderManager",
            {
                "guiclass": "HeaderPanel",
                "testclass": "HeaderManager",
                "testname": "HTTP Header Manager",
                "enabled": "true",
            },
        )

        # Create collectionProp for headers
        coll_prop = ET.SubElement(header_manager, "collectionProp", {"name": "HeaderManager.headers"})

        # Create elementProp for each header
        for header_name, header_value in headers.items():
            elem_prop = ET.SubElement(
                coll_prop,
                "elementProp",
                {
                    "name": "",
                    "elementType": "Header",
                },
            )

            # Header name
            ET.SubElement(elem_prop, "stringProp", {"name": "Header.name"}).text = header_name

            # Header value
            ET.SubElement(elem_prop, "stringProp", {"name": "Header.value"}).text = header_value

        return header_manager

    def _create_query_parameters_element(self, parameters: list[dict]) -> ET.Element:
        """Create Arguments element with query parameters.

        Query parameters are added to the HTTPsampler.Arguments collectionProp
        as HTTPArgument elements. Each parameter uses JMeter variable syntax
        ${paramName} to allow users to provide values via User Defined Variables
        or CSV Data Set Config.

        Args:
            parameters: List of parameter dicts from OpenAPI spec

        Returns:
            elementProp for HTTPsampler.Arguments with query parameters

        Example:
            parameters = [
                {"name": "username", "in": "query", "required": True},
                {"name": "format", "in": "query", "default": "json"}
            ]

            Generates:
            <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
              <collectionProp name="Arguments.arguments">
                <elementProp name="username" elementType="HTTPArgument">
                  <stringProp name="Argument.name">username</stringProp>
                  <stringProp name="Argument.value">${username}</stringProp>
                  ...
                </elementProp>
              </collectionProp>
            </elementProp>
        """
        elem_prop = ET.Element(
            "elementProp",
            {
                "name": "HTTPsampler.Arguments",
                "elementType": "Arguments",
                "guiclass": "HTTPArgumentsPanel",
                "testclass": "Arguments",
                "testname": "User Defined Variables",
                "enabled": "true",
            },
        )

        coll_prop = ET.SubElement(elem_prop, "collectionProp", {"name": "Arguments.arguments"})

        # Filter and process query parameters only
        query_params = [p for p in parameters if p.get("in") == "query"]

        for param in query_params:
            name = param.get("name", "param")

            # Try to get example/default value, otherwise use JMeter variable
            value = param.get("example") or param.get("default")
            if value is None:
                value = f"${{{name}}}"  # JMeter variable syntax
            else:
                value = str(value)

            # Create HTTPArgument element for this parameter
            arg_elem = ET.SubElement(
                coll_prop, "elementProp", {"name": name, "elementType": "HTTPArgument"}
            )

            ET.SubElement(arg_elem, "boolProp", {"name": "HTTPArgument.always_encode"}).text = (
                "false"
            )
            ET.SubElement(arg_elem, "stringProp", {"name": "Argument.name"}).text = name
            ET.SubElement(arg_elem, "stringProp", {"name": "Argument.value"}).text = value
            ET.SubElement(arg_elem, "stringProp", {"name": "Argument.metadata"}).text = "="
            ET.SubElement(arg_elem, "boolProp", {"name": "HTTPArgument.use_equals"}).text = "true"

        return elem_prop

    def _is_ugly_operation_id(self, operation_id: str, method: str) -> bool:
        """Check if operationId looks like auto-generated garbage.

        FastAPI and similar frameworks auto-generate operationIds by concatenating
        method + path without separators when no explicit operationId is provided.

        Criteria for "ugly" operationId:
        - Contains version patterns like _1.0_ or _v1_ (strong signal of path-based)
        - Has too many segments (more than 5 underscores/hyphens)
        - Starts with method prefix AND very long (>35 chars)
        - No separators, starts with method, and longer than 20 chars (FastAPI style)

        Args:
            operation_id: The operationId from spec
            method: HTTP method (GET, POST, etc.)

        Returns:
            True if operationId looks auto-generated and ugly
        """
        import re

        # Short names are always OK
        if len(operation_id) <= 20:
            return False

        # Has camelCase = likely intentional = OK
        if not operation_id.islower():
            return False

        method_lower = method.lower()

        # Contains version patterns like _1.0_ or _v1_ = definitely path-based
        if re.search(r"_v?\d+\.?\d*_", operation_id):
            return True

        # Too many segments (>5 underscores or hyphens) = path-based
        segment_count = operation_id.count("_") + operation_id.count("-")
        if segment_count > 5:
            return True

        # Starts with method prefix AND very long = likely path-based
        if operation_id.startswith(f"{method_lower}_") and len(operation_id) > 35:
            return True

        # No separators, starts with method = FastAPI style (no explicit operationId)
        if "_" not in operation_id and "-" not in operation_id:
            if operation_id.startswith(method_lower):
                return True

        return False

    def _create_name_from_path(self, path: str, method: str) -> str:
        """Create readable name from path's last segment.

        Extracts the last non-parameter segment from the path and converts it
        to PascalCase for better readability.

        Args:
            path: The endpoint path (e.g., "/api/v1/validate_module_db")
            method: HTTP method as fallback

        Returns:
            PascalCase name (e.g., "ValidateModuleDb")

        Example:
            /api/v1/validate_module_db -> ValidateModuleDb
            /users/{id}/items -> Items
            /health-check -> HealthCheck
        """
        # Get last non-parameter segment
        segments = [s for s in path.split("/") if s and not s.startswith("{")]
        if not segments:
            return f"{method.upper()}_request"

        last_segment = segments[-1]
        # Convert snake_case or kebab-case to PascalCase
        words = last_segment.replace("-", "_").split("_")
        pascal_case = "".join(word.capitalize() for word in words if word)

        return pascal_case or f"{method.upper()}_request"

    def _get_readable_operation_name(
        self, operation_id: str, path: str, method: str
    ) -> str:
        """Get a readable operation name, fixing ugly auto-generated operationIds.

        If the operationId looks like auto-generated garbage (e.g.,
        "postserviceagenttestcasesgenapi10validatemoduledb"), this method
        creates a better name from the path's last segment.

        Args:
            operation_id: The operationId from spec
            path: The endpoint path
            method: HTTP method

        Returns:
            A readable name for the sampler
        """
        if self._is_ugly_operation_id(operation_id, method):
            return self._create_name_from_path(path, method)
        return operation_id

    def _convert_path_parameters(self, path: str, parameters: list[dict]) -> str:
        """Convert OpenAPI path parameters to JMeter variable syntax.

        OpenAPI uses {paramName} syntax for path parameters, while JMeter
        uses ${paramName} syntax. This method converts the path format.

        Args:
            path: OpenAPI path with {paramName} syntax (e.g., "/users/{id}")
            parameters: List of parameter dicts from OpenAPI spec

        Returns:
            Path with ${paramName} JMeter variable syntax (e.g., "/users/${id}")

        Example:
            path = "/users/{id}/items/{itemId}"
            parameters = [
                {"name": "id", "in": "path"},
                {"name": "itemId", "in": "path"}
            ]

            Returns: "/users/${id}/items/${itemId}"
        """
        import re

        # Get set of path parameter names
        path_params = {p.get("name") for p in parameters if p.get("in") == "path"}

        # Replace {paramName} with ${paramName} for path parameters
        def replace_param(match):
            param_name = match.group(1)
            if param_name in path_params:
                return f"${{{param_name}}}"
            return match.group(0)  # Leave unchanged if not a path param

        return re.sub(r"\{([^}]+)\}", replace_param, path)

    def _create_http_sampler(
        self, endpoint: dict, request_body_json: Optional[str] = None
    ) -> tuple[ET.Element, dict[str, str]]:
        """Create HTTP Sampler for a single endpoint.

        Individual samplers have EMPTY domain/port/protocol properties because
        they inherit these values from HTTP Request Defaults. Only path and
        method are specified here.

        Args:
            endpoint: Endpoint dictionary with keys:
                     - path: URL path (e.g., "/api/users/{id}")
                     - method: HTTP method (e.g., "GET", "POST")
                     - operationId: Unique operation identifier
                     - summary: Brief description (optional)
                     - requestBody: Boolean indicating if endpoint has request body
                     - parameters: List of parameter dicts (optional)
            request_body_json: JSON string of request body (None if no body)

        Returns:
            Tuple of (HTTPSamplerProxy XML Element, dict of header parameters)
        """
        path = endpoint.get("path", "/")
        method = endpoint.get("method", "GET")
        operation_id = endpoint.get("operationId", "UnknownOperation")
        summary = endpoint.get("summary", "")
        parameters = endpoint.get("parameters", [])

        # Convert path parameters from {param} to ${param}
        jmeter_path = self._convert_path_parameters(path, parameters)

        # Get readable operation name (fixes ugly auto-generated operationIds)
        display_name = self._get_readable_operation_name(operation_id, path, method)

        # Use display name and summary for test name
        test_name = display_name
        if summary:
            test_name = f"{display_name} - {summary}"

        sampler = ET.Element(
            "HTTPSamplerProxy",
            {
                "guiclass": "HttpTestSampleGui",
                "testclass": "HTTPSamplerProxy",
                "testname": test_name,
                "enabled": "true",
            },
        )

        # Add Arguments element - either query parameters or empty
        query_params = [p for p in parameters if p.get("in") == "query"]
        if query_params:
            # Use helper method to create query parameters
            args_elem = self._create_query_parameters_element(parameters)
            sampler.append(args_elem)
        else:
            # Add empty elementProp for HTTP Sampler arguments
            elem_prop = ET.SubElement(
                sampler,
                "elementProp",
                {
                    "name": "HTTPsampler.Arguments",
                    "elementType": "Arguments",
                    "guiclass": "HTTPArgumentsPanel",
                    "testclass": "Arguments",
                    "testname": "User Defined Variables",
                    "enabled": "true",
                },
            )
            # Add empty collectionProp for arguments
            ET.SubElement(elem_prop, "collectionProp", {"name": "Arguments.arguments"})

        # EMPTY domain (inherited from HTTP Request Defaults)
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.domain"})

        # EMPTY port (inherited from HTTP Request Defaults)
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.port"})

        # EMPTY protocol (inherited from HTTP Request Defaults)
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.protocol"})

        # Path (this is what we specify)
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.path"}).text = jmeter_path

        # Method (this is what we specify)
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.method"}).text = method

        # Follow redirects
        ET.SubElement(sampler, "boolProp", {"name": "HTTPSampler.follow_redirects"}).text = "true"

        # Use keepalive
        ET.SubElement(sampler, "boolProp", {"name": "HTTPSampler.use_keepalive"}).text = "true"

        # Auto redirects (false if follow_redirects is true)
        ET.SubElement(sampler, "boolProp", {"name": "HTTPSampler.auto_redirects"}).text = "false"

        # Add request body if provided
        if request_body_json:
            # Add postBodyRaw property
            ET.SubElement(sampler, "boolProp", {"name": "HTTPSampler.postBodyRaw"}).text = "true"

            # Add elementProp for body data
            body_elem_prop = ET.SubElement(
                sampler,
                "elementProp",
                {
                    "name": "HTTPsampler.Arguments",
                    "elementType": "Arguments",
                },
            )

            # Add collectionProp for arguments
            body_coll_prop = ET.SubElement(
                body_elem_prop, "collectionProp", {"name": "Arguments.arguments"}
            )

            # Add elementProp for the body argument
            body_arg_elem = ET.SubElement(
                body_coll_prop,
                "elementProp",
                {
                    "name": "",
                    "elementType": "HTTPArgument",
                },
            )

            # Add body value
            ET.SubElement(body_arg_elem, "boolProp", {"name": "HTTPArgument.always_encode"}).text = (
                "false"
            )
            ET.SubElement(body_arg_elem, "stringProp", {"name": "Argument.value"}).text = (
                request_body_json
            )
            ET.SubElement(body_arg_elem, "stringProp", {"name": "Argument.metadata"}).text = "="

        # Collect header parameters
        headers_dict: dict[str, str] = {}
        for param in parameters:
            if param.get("in") == "header":
                param_name = param.get("name", "")
                # Try to get example/default value, otherwise use JMeter variable
                param_value = param.get("example") or param.get("default")
                if param_value is None:
                    param_value = f"${{{param_name}}}"
                else:
                    param_value = str(param_value)
                headers_dict[param_name] = param_value

        return sampler, headers_dict

    def _create_assertions(self, endpoint: dict) -> list[ET.Element]:
        """Create Response Assertions for an endpoint.

        Creates assertions to validate response codes based on OpenAPI spec.
        If spec defines response codes, uses those. Otherwise falls back to:
        - POST requests: Expect 201 (Created)
        - Other requests: Expect 200 (OK)

        Args:
            endpoint: Endpoint dictionary with expected_response_codes key

        Returns:
            List of ResponseAssertion XML Elements
        """
        # Get expected response codes from endpoint data (extracted from spec)
        expected_codes = endpoint.get("expected_response_codes", [])

        # Fallback to hardcoded logic if no codes in endpoint data
        # (for backward compatibility with older parser versions)
        if not expected_codes:
            method = endpoint.get("method", "GET")
            if method == "POST":
                expected_codes = ["201"]
            else:
                expected_codes = ["200"]

        assertions = []

        # Create assertion for each expected response code
        # Most endpoints will have one code, but some may have multiple (e.g., 200, 201, 204)
        for expected_code in expected_codes:
            assertion = ET.Element(
                "ResponseAssertion",
                {
                    "guiclass": "AssertionGui",
                    "testclass": "ResponseAssertion",
                    "testname": f"Response Code {expected_code}",
                    "enabled": "true",
                },
            )

            # Test field: response code
            ET.SubElement(
                assertion, "stringProp", {"name": "Assertion.test_field"}
            ).text = "Assertion.response_code"

            # Test type: 8 = equals
            ET.SubElement(assertion, "intProp", {"name": "Assertion.test_type"}).text = "8"

            # Test strings collection (note the typo: "Asserion" not "Assertion")
            # This is a known JMeter typo that must be preserved for compatibility
            coll_prop = ET.SubElement(assertion, "collectionProp", {"name": "Asserion.test_strings"})

            # Add expected response code
            ET.SubElement(
                coll_prop,
                "stringProp",
                {
                    "name": str(hash(expected_code))  # Use hash as unique identifier
                },
            ).text = expected_code

            assertions.append(assertion)

        return assertions

    def _create_view_results_tree_listener(self) -> ET.Element:
        """Create View Results Tree listener for detailed request/response viewing.

        Creates a ResultCollector configured as View Results Tree listener,
        which allows viewing detailed information about each request and response
        in the JMeter GUI.

        Returns:
            ResultCollector XML Element configured as View Results Tree
        """
        listener = ET.Element(
            "ResultCollector",
            {
                "guiclass": "ViewResultsFullVisualizer",
                "testclass": "ResultCollector",
                "testname": "View Results Tree",
                "enabled": "true",
            },
        )

        # Error logging disabled by default
        ET.SubElement(listener, "boolProp", {"name": "ResultCollector.error_logging"}).text = (
            "false"
        )

        # Sample save configuration
        obj_prop = ET.SubElement(listener, "objProp")
        name_elem = ET.SubElement(obj_prop, "name")
        name_elem.text = "saveConfig"

        value_elem = ET.SubElement(obj_prop, "value", {"class": "SampleSaveConfiguration"})

        # Configure what to save
        config_items = {
            "time": "true",
            "latency": "true",
            "timestamp": "true",
            "success": "true",
            "label": "true",
            "code": "true",
            "message": "true",
            "threadName": "true",
            "dataType": "true",
            "encoding": "false",
            "assertions": "true",
            "subresults": "true",
            "responseData": "false",
            "samplerData": "false",
            "xml": "false",
            "fieldNames": "true",
            "responseHeaders": "false",
            "requestHeaders": "false",
            "responseDataOnError": "false",
            "saveAssertionResultsFailureMessage": "true",
            "assertionsResultsToSave": "0",
            "bytes": "true",
            "sentBytes": "true",
            "url": "true",
            "threadCounts": "true",
            "idleTime": "true",
            "connectTime": "true",
        }

        for key, val in config_items.items():
            ET.SubElement(value_elem, key).text = val

        return listener

    def _create_aggregate_report_listener(self) -> ET.Element:
        """Create Aggregate Report listener for statistical summary.

        Creates a ResultCollector configured as Aggregate Report listener,
        which displays aggregated statistics (throughput, average time, etc.)
        for all requests in the JMeter GUI.

        Returns:
            ResultCollector XML Element configured as Aggregate Report
        """
        listener = ET.Element(
            "ResultCollector",
            {
                "guiclass": "StatVisualizer",
                "testclass": "ResultCollector",
                "testname": "Aggregate Report",
                "enabled": "true",
            },
        )

        # Error logging disabled by default
        ET.SubElement(listener, "boolProp", {"name": "ResultCollector.error_logging"}).text = (
            "false"
        )

        # Sample save configuration
        obj_prop = ET.SubElement(listener, "objProp")
        name_elem = ET.SubElement(obj_prop, "name")
        name_elem.text = "saveConfig"

        value_elem = ET.SubElement(obj_prop, "value", {"class": "SampleSaveConfiguration"})

        # Configure what to save (same as View Results Tree)
        config_items = {
            "time": "true",
            "latency": "true",
            "timestamp": "true",
            "success": "true",
            "label": "true",
            "code": "true",
            "message": "true",
            "threadName": "true",
            "dataType": "true",
            "encoding": "false",
            "assertions": "true",
            "subresults": "true",
            "responseData": "false",
            "samplerData": "false",
            "xml": "false",
            "fieldNames": "true",
            "responseHeaders": "false",
            "requestHeaders": "false",
            "responseDataOnError": "false",
            "saveAssertionResultsFailureMessage": "true",
            "assertionsResultsToSave": "0",
            "bytes": "true",
            "sentBytes": "true",
            "url": "true",
            "threadCounts": "true",
            "idleTime": "true",
            "connectTime": "true",
        }

        for key, val in config_items.items():
            ET.SubElement(value_elem, key).text = val

        return listener
