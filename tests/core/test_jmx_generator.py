"""Tests for JMX Generator module."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from jmeter_gen.core.jmx_generator import JMXGenerator
from jmeter_gen.exceptions import JMXGenerationException


class TestJMXGenerator:
    """Test suite for JMXGenerator class."""

    @pytest.fixture
    def generator(self) -> JMXGenerator:
        """Create a JMXGenerator instance for testing.

        Returns:
            JMXGenerator instance
        """
        return JMXGenerator()

    @pytest.fixture
    def sample_spec_data(self) -> dict:
        """Create sample OpenAPI spec data for testing.

        Returns:
            Dictionary with parsed OpenAPI data
        """
        return {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/api/users",
                    "method": "GET",
                    "operationId": "getUsers",
                    "summary": "Get all users",
                    "requestBody": False,
                    "parameters": []
                },
                {
                    "path": "/api/users",
                    "method": "POST",
                    "operationId": "createUser",
                    "summary": "Create a new user",
                    "requestBody": True,
                    "parameters": []
                },
                {
                    "path": "/api/users/{id}",
                    "method": "PUT",
                    "operationId": "updateUser",
                    "summary": "Update user",
                    "requestBody": True,
                    "parameters": [{"name": "id", "in": "path"}]
                },
                {
                    "path": "/api/users/{id}",
                    "method": "DELETE",
                    "operationId": "deleteUser",
                    "summary": "Delete user",
                    "requestBody": False,
                    "parameters": [{"name": "id", "in": "path"}]
                }
            ],
            "spec": {}
        }

    @pytest.fixture
    def minimal_spec_data(self) -> dict:
        """Create minimal spec data with single endpoint.

        Returns:
            Dictionary with minimal OpenAPI data
        """
        return {
            "title": "Minimal API",
            "version": "1.0",
            "base_url": "http://localhost:3000",
            "endpoints": [
                {
                    "path": "/health",
                    "method": "GET",
                    "operationId": "healthCheck",
                    "summary": "",
                    "requestBody": False,
                    "parameters": []
                }
            ],
            "spec": {}
        }

    def test_generator_initialization(self, generator: JMXGenerator) -> None:
        """Test that JMXGenerator initializes correctly."""
        assert generator is not None
        assert generator.DEFAULT_THREADS == 1
        assert generator.DEFAULT_RAMPUP == 0
        assert generator.DEFAULT_DURATION is None

    def test_parse_url_with_port(self, generator: JMXGenerator) -> None:
        """Test URL parsing with explicit port."""
        domain, port, protocol = generator._parse_url("http://localhost:8080/api")

        assert domain == "localhost"
        assert port == "8080"
        assert protocol == "http"

    def test_parse_url_without_port(self, generator: JMXGenerator) -> None:
        """Test URL parsing without explicit port (default port)."""
        domain, port, protocol = generator._parse_url("http://example.com")

        assert domain == "example.com"
        assert port == ""  # Empty string for default port
        assert protocol == "http"

    def test_parse_url_https(self, generator: JMXGenerator) -> None:
        """Test URL parsing with HTTPS protocol."""
        domain, port, protocol = generator._parse_url("https://api.example.com:443/v1")

        assert domain == "api.example.com"
        assert port == "443"
        assert protocol == "https"

    def test_parse_url_localhost_default(self, generator: JMXGenerator) -> None:
        """Test URL parsing defaults to localhost."""
        domain, port, protocol = generator._parse_url("http://localhost")

        assert domain == "localhost"
        assert port == ""
        assert protocol == "http"

    def test_parse_url_custom_port(self, generator: JMXGenerator) -> None:
        """Test URL parsing with custom port."""
        domain, port, protocol = generator._parse_url("http://192.168.1.100:9090")

        assert domain == "192.168.1.100"
        assert port == "9090"
        assert protocol == "http"

    def test_prettify_xml(self, generator: JMXGenerator) -> None:
        """Test XML prettification with 2-space indentation."""
        # Create simple XML element
        root = ET.Element("root")
        child1 = ET.SubElement(root, "child1")
        child2 = ET.SubElement(child1, "child2")
        child2.text = "value"

        pretty = generator._prettify_xml(root)

        # Should have 2-space indentation
        assert "  <child1>" in pretty
        assert "    <child2>value</child2>" in pretty
        # Should not have excessive blank lines
        assert "\n\n\n" not in pretty

    def test_create_test_plan(self, generator: JMXGenerator) -> None:
        """Test Test Plan element creation."""
        test_plan = generator._create_test_plan("My API", "2.0.0")

        assert test_plan.tag == "TestPlan"
        assert test_plan.get("testname") == "My API v2.0.0"
        assert test_plan.get("enabled") == "true"
        assert test_plan.get("guiclass") == "TestPlanGui"
        assert test_plan.get("testclass") == "TestPlan"

        # Check properties
        bool_props = test_plan.findall("boolProp")
        assert len(bool_props) == 2

        functional_mode = test_plan.find("boolProp[@name='TestPlan.functional_mode']")
        assert functional_mode is not None
        assert functional_mode.text == "false"

        # Check elementProp for user defined variables
        elem_prop = test_plan.find("elementProp[@name='TestPlan.user_defined_variables']")
        assert elem_prop is not None
        assert elem_prop.get("elementType") == "Arguments"

    def test_create_thread_group(self, generator: JMXGenerator) -> None:
        """Test Thread Group element creation."""
        thread_group = generator._create_thread_group(threads=20, rampup=10, duration=120)

        assert thread_group.tag == "ThreadGroup"
        assert thread_group.get("testname") == "Thread Group"
        assert thread_group.get("enabled") == "true"

        # Check thread count
        num_threads = thread_group.find("stringProp[@name='ThreadGroup.num_threads']")
        assert num_threads is not None
        assert num_threads.text == "20"

        # Check ramp-up
        ramp_time = thread_group.find("stringProp[@name='ThreadGroup.ramp_time']")
        assert ramp_time is not None
        assert ramp_time.text == "10"

        # Check duration
        duration_prop = thread_group.find("stringProp[@name='ThreadGroup.duration']")
        assert duration_prop is not None
        assert duration_prop.text == "120"

        # Check scheduler enabled
        scheduler = thread_group.find("boolProp[@name='ThreadGroup.scheduler']")
        assert scheduler is not None
        assert scheduler.text == "true"

        # Check loop controller
        loop_controller = thread_group.find("elementProp[@name='ThreadGroup.main_controller']")
        assert loop_controller is not None
        assert loop_controller.get("elementType") == "LoopController"

        # Check loop count is -1 (infinite)
        loops = loop_controller.find("stringProp[@name='LoopController.loops']")
        assert loops is not None
        assert loops.text == "-1"

    def test_create_thread_group_iteration_based(self, generator: JMXGenerator) -> None:
        """Test Thread Group element creation with iteration-based mode (duration=None)."""
        thread_group = generator._create_thread_group(threads=1, rampup=0, duration=None)

        assert thread_group.tag == "ThreadGroup"
        assert thread_group.get("testname") == "Thread Group"
        assert thread_group.get("enabled") == "true"

        # Check thread count
        num_threads = thread_group.find("stringProp[@name='ThreadGroup.num_threads']")
        assert num_threads is not None
        assert num_threads.text == "1"

        # Check ramp-up
        ramp_time = thread_group.find("stringProp[@name='ThreadGroup.ramp_time']")
        assert ramp_time is not None
        assert ramp_time.text == "0"

        # Check duration is empty (not None or a number)
        duration_prop = thread_group.find("stringProp[@name='ThreadGroup.duration']")
        assert duration_prop is not None
        assert duration_prop.text == ""

        # Check scheduler disabled
        scheduler = thread_group.find("boolProp[@name='ThreadGroup.scheduler']")
        assert scheduler is not None
        assert scheduler.text == "false"

        # Check loop controller
        loop_controller = thread_group.find("elementProp[@name='ThreadGroup.main_controller']")
        assert loop_controller is not None
        assert loop_controller.get("elementType") == "LoopController"

        # Check loop count is 1 (single iteration)
        loops = loop_controller.find("stringProp[@name='LoopController.loops']")
        assert loops is not None
        assert loops.text == "1"

    def test_create_view_results_tree_listener(self, generator: JMXGenerator) -> None:
        """Test View Results Tree listener creation."""
        listener = generator._create_view_results_tree_listener()

        assert listener.tag == "ResultCollector"
        assert listener.get("guiclass") == "ViewResultsFullVisualizer"
        assert listener.get("testclass") == "ResultCollector"
        assert listener.get("testname") == "View Results Tree"
        assert listener.get("enabled") == "true"

        # Check error logging disabled
        error_logging = listener.find("boolProp[@name='ResultCollector.error_logging']")
        assert error_logging is not None
        assert error_logging.text == "false"

        # Check saveConfig exists
        obj_prop = listener.find("objProp")
        assert obj_prop is not None
        value_elem = obj_prop.find("value[@class='SampleSaveConfiguration']")
        assert value_elem is not None

    def test_create_aggregate_report_listener(self, generator: JMXGenerator) -> None:
        """Test Aggregate Report listener creation."""
        listener = generator._create_aggregate_report_listener()

        assert listener.tag == "ResultCollector"
        assert listener.get("guiclass") == "StatVisualizer"
        assert listener.get("testclass") == "ResultCollector"
        assert listener.get("testname") == "Aggregate Report"
        assert listener.get("enabled") == "true"

        # Check error logging disabled
        error_logging = listener.find("boolProp[@name='ResultCollector.error_logging']")
        assert error_logging is not None
        assert error_logging.text == "false"

        # Check saveConfig exists
        obj_prop = listener.find("objProp")
        assert obj_prop is not None
        value_elem = obj_prop.find("value[@class='SampleSaveConfiguration']")
        assert value_elem is not None

    def test_create_http_defaults(self, generator: JMXGenerator) -> None:
        """Test HTTP Request Defaults element creation."""
        http_defaults = generator._create_http_defaults(
            domain="example.com",
            port="8080",
            protocol="https"
        )

        assert http_defaults.tag == "ConfigTestElement"
        assert http_defaults.get("testname") == "HTTP Request Defaults"
        assert http_defaults.get("guiclass") == "HttpDefaultsGui"
        assert http_defaults.get("testclass") == "ConfigTestElement"

        # Check domain
        domain = http_defaults.find("stringProp[@name='HTTPSampler.domain']")
        assert domain is not None
        assert domain.text == "example.com"

        # Check port
        port = http_defaults.find("stringProp[@name='HTTPSampler.port']")
        assert port is not None
        assert port.text == "8080"

        # Check protocol
        protocol = http_defaults.find("stringProp[@name='HTTPSampler.protocol']")
        assert protocol is not None
        assert protocol.text == "https"

        # Check arguments elementProp
        elem_prop = http_defaults.find("elementProp[@name='HTTPsampler.Arguments']")
        assert elem_prop is not None
        assert elem_prop.get("elementType") == "Arguments"

    def test_create_http_defaults_empty_port(self, generator: JMXGenerator) -> None:
        """Test HTTP Request Defaults with empty port (default)."""
        http_defaults = generator._create_http_defaults(
            domain="localhost",
            port="",
            protocol="http"
        )

        port = http_defaults.find("stringProp[@name='HTTPSampler.port']")
        assert port is not None
        assert port.text == ""  # Empty string for default port

    def test_create_http_sampler_get(self, generator: JMXGenerator) -> None:
        """Test HTTP Sampler creation for GET request."""
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "operationId": "getUsers",
            "summary": "Get all users",
            "parameters": []
        }

        sampler, headers = generator._create_http_sampler(endpoint)

        assert sampler.tag == "HTTPSamplerProxy"
        assert sampler.get("testname") == "getUsers - Get all users"
        assert sampler.get("enabled") == "true"

        # CRITICAL: domain, port, protocol should be EMPTY (inherited from defaults)
        domain = sampler.find("stringProp[@name='HTTPSampler.domain']")
        assert domain is not None
        assert domain.text is None or domain.text == ""

        port = sampler.find("stringProp[@name='HTTPSampler.port']")
        assert port is not None
        assert port.text is None or port.text == ""

        protocol = sampler.find("stringProp[@name='HTTPSampler.protocol']")
        assert protocol is not None
        assert protocol.text is None or protocol.text == ""

        # Check path and method are specified
        path = sampler.find("stringProp[@name='HTTPSampler.path']")
        assert path is not None
        assert path.text == "/api/users"

        method = sampler.find("stringProp[@name='HTTPSampler.method']")
        assert method is not None
        assert method.text == "GET"

        # Check follow redirects
        follow_redirects = sampler.find("boolProp[@name='HTTPSampler.follow_redirects']")
        assert follow_redirects is not None
        assert follow_redirects.text == "true"

        # Check keepalive
        keepalive = sampler.find("boolProp[@name='HTTPSampler.use_keepalive']")
        assert keepalive is not None
        assert keepalive.text == "true"

    def test_create_http_sampler_post(self, generator: JMXGenerator) -> None:
        """Test HTTP Sampler creation for POST request."""
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "operationId": "createUser",
            "summary": "Create user",
            "parameters": []
        }

        sampler, headers = generator._create_http_sampler(endpoint)

        method = sampler.find("stringProp[@name='HTTPSampler.method']")
        assert method.text == "POST"

    def test_create_http_sampler_no_summary(self, generator: JMXGenerator) -> None:
        """Test HTTP Sampler creation without summary."""
        endpoint = {
            "path": "/health",
            "method": "GET",
            "operationId": "healthCheck",
            "summary": "",
            "parameters": []
        }

        sampler, headers = generator._create_http_sampler(endpoint)
        # Test name should just be operationId when summary is empty
        assert sampler.get("testname") == "healthCheck"

    def test_is_ugly_operation_id_detects_auto_generated(
        self, generator: JMXGenerator
    ) -> None:
        """Test detection of auto-generated ugly operationIds."""
        # Ugly: all lowercase, no separators, >20 chars, starts with method
        assert generator._is_ugly_operation_id(
            "postserviceagenttestcasesgenapi10validatemoduledb", "POST"
        )
        assert generator._is_ugly_operation_id(
            "getserviceagenttestcasesgenapi10trigger", "GET"
        )

    def test_is_ugly_operation_id_accepts_good_names(
        self, generator: JMXGenerator
    ) -> None:
        """Test that good operationIds are not marked as ugly."""
        # Good: has capitals (camelCase)
        assert not generator._is_ugly_operation_id("getUsers", "GET")
        assert not generator._is_ugly_operation_id("HealthCheck", "GET")

        # Good: has separators
        assert not generator._is_ugly_operation_id("get_users_by_id_and_name", "GET")
        assert not generator._is_ugly_operation_id("get-users-by-id", "GET")

        # Good: too short to be sure
        assert not generator._is_ugly_operation_id("postapi", "POST")
        assert not generator._is_ugly_operation_id("getusers", "GET")

    def test_create_name_from_path_snake_case(
        self, generator: JMXGenerator
    ) -> None:
        """Test name creation from snake_case path segment."""
        result = generator._create_name_from_path(
            "/service/agent/api/1.0/validate_module_db", "POST"
        )
        assert result == "ValidateModuleDb"

    def test_create_name_from_path_kebab_case(
        self, generator: JMXGenerator
    ) -> None:
        """Test name creation from kebab-case path segment."""
        result = generator._create_name_from_path("/api/health-check", "GET")
        assert result == "HealthCheck"

    def test_create_name_from_path_simple(self, generator: JMXGenerator) -> None:
        """Test name creation from simple path segment."""
        result = generator._create_name_from_path("/users", "GET")
        assert result == "Users"

    def test_create_name_from_path_with_params(
        self, generator: JMXGenerator
    ) -> None:
        """Test that path parameters are skipped."""
        result = generator._create_name_from_path("/users/{id}/items", "GET")
        assert result == "Items"

    def test_create_name_from_path_empty(self, generator: JMXGenerator) -> None:
        """Test fallback when path is empty."""
        result = generator._create_name_from_path("/", "POST")
        assert result == "POST_request"

    def test_get_readable_operation_name_fixes_ugly(
        self, generator: JMXGenerator
    ) -> None:
        """Test that ugly operationIds get fixed."""
        result = generator._get_readable_operation_name(
            "postserviceagenttestcasesgenapi10validatemoduledb",
            "/service/agent/api/1.0/validate_module_db",
            "POST",
        )
        assert result == "ValidateModuleDb"

    def test_get_readable_operation_name_keeps_good(
        self, generator: JMXGenerator
    ) -> None:
        """Test that good operationIds are unchanged."""
        result = generator._get_readable_operation_name(
            "HealthCheck", "/health", "GET"
        )
        assert result == "HealthCheck"

    def test_create_http_sampler_fixes_ugly_operation_id(
        self, generator: JMXGenerator
    ) -> None:
        """Test HTTP Sampler uses readable name for ugly operationId."""
        endpoint = {
            "path": "/service/agent/api/1.0/validate_module_db",
            "method": "POST",
            "operationId": "postserviceagenttestcasesgenapi10validatemoduledb",
            "summary": "Check if module exists",
            "parameters": [],
        }

        sampler, headers = generator._create_http_sampler(endpoint)

        # Should use path-derived name, not the ugly operationId
        testname = sampler.get("testname")
        assert testname == "ValidateModuleDb - Check if module exists"
        assert "postserviceagenttestcases" not in testname

    def test_create_assertions_for_post(self, generator: JMXGenerator) -> None:
        """Test Response Assertion creation for POST request (expects 201)."""
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "operationId": "createUser"
        }

        assertions = generator._create_assertions(endpoint)

        assert len(assertions) == 1
        assertion = assertions[0]

        assert assertion.tag == "ResponseAssertion"
        assert assertion.get("testname") == "Response Code 201"

        # Check test field
        test_field = assertion.find("stringProp[@name='Assertion.test_field']")
        assert test_field is not None
        assert test_field.text == "Assertion.response_code"

        # Check test type (8 = equals)
        test_type = assertion.find("intProp[@name='Assertion.test_type']")
        assert test_type is not None
        assert test_type.text == "8"

        # Check test strings (note the typo: "Asserion")
        test_strings = assertion.find("collectionProp[@name='Asserion.test_strings']")
        assert test_strings is not None

        # Should contain 201
        string_props = test_strings.findall("stringProp")
        assert len(string_props) == 1
        assert string_props[0].text == "201"

    def test_create_assertions_for_get(self, generator: JMXGenerator) -> None:
        """Test Response Assertion creation for GET request (expects 200)."""
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "operationId": "getUsers"
        }

        assertions = generator._create_assertions(endpoint)

        assert len(assertions) == 1
        assertion = assertions[0]

        assert assertion.get("testname") == "Response Code 200"

        # Check test strings contain 200
        test_strings = assertion.find("collectionProp[@name='Asserion.test_strings']")
        string_props = test_strings.findall("stringProp")
        assert string_props[0].text == "200"

    def test_create_assertions_for_put(self, generator: JMXGenerator) -> None:
        """Test Response Assertion creation for PUT request (expects 200)."""
        endpoint = {
            "path": "/api/users/{id}",
            "method": "PUT",
            "operationId": "updateUser"
        }

        assertions = generator._create_assertions(endpoint)
        assertion = assertions[0]

        test_strings = assertion.find("collectionProp[@name='Asserion.test_strings']")
        string_props = test_strings.findall("stringProp")
        assert string_props[0].text == "200"

    def test_create_assertions_for_delete(self, generator: JMXGenerator) -> None:
        """Test Response Assertion creation for DELETE request (expects 200)."""
        endpoint = {
            "path": "/api/users/{id}",
            "method": "DELETE",
            "operationId": "deleteUser"
        }

        assertions = generator._create_assertions(endpoint)
        assertion = assertions[0]

        test_strings = assertion.find("collectionProp[@name='Asserion.test_strings']")
        string_props = test_strings.findall("stringProp")
        assert string_props[0].text == "200"

    def test_create_assertions_with_spec_defined_code(self, generator: JMXGenerator) -> None:
        """Test Response Assertion creation using spec-defined response code."""
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "operationId": "createUser",
            "expected_response_codes": ["200"]  # Spec says 200, not 201
        }

        assertions = generator._create_assertions(endpoint)

        assert len(assertions) == 1
        assertion = assertions[0]

        # Should use spec-defined code (200), not hardcoded POST default (201)
        assert assertion.get("testname") == "Response Code 200"

        test_strings = assertion.find("collectionProp[@name='Asserion.test_strings']")
        string_props = test_strings.findall("stringProp")
        assert len(string_props) == 1
        assert string_props[0].text == "200"

    def test_create_assertions_with_multiple_codes(self, generator: JMXGenerator) -> None:
        """Test Response Assertion creation with multiple expected codes."""
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "operationId": "createUser",
            "expected_response_codes": ["200", "201"]  # Multiple success codes
        }

        assertions = generator._create_assertions(endpoint)

        # Should create assertion for each code
        assert len(assertions) == 2

        # Check both assertions are created with correct codes
        codes = []
        for assertion in assertions:
            test_strings = assertion.find("collectionProp[@name='Asserion.test_strings']")
            string_props = test_strings.findall("stringProp")
            codes.append(string_props[0].text)

        assert set(codes) == {"200", "201"}

    def test_create_assertions_fallback_for_missing_codes(self, generator: JMXGenerator) -> None:
        """Test fallback to default codes when expected_response_codes is missing."""
        # POST without expected_response_codes should default to 201
        post_endpoint = {
            "path": "/api/users",
            "method": "POST",
            "operationId": "createUser"
            # No expected_response_codes key
        }

        post_assertions = generator._create_assertions(post_endpoint)
        assert len(post_assertions) == 1
        assert post_assertions[0].get("testname") == "Response Code 201"

        # GET without expected_response_codes should default to 200
        get_endpoint = {
            "path": "/api/users",
            "method": "GET",
            "operationId": "getUsers"
            # No expected_response_codes key
        }

        get_assertions = generator._create_assertions(get_endpoint)
        assert len(get_assertions) == 1
        assert get_assertions[0].get("testname") == "Response Code 200"

    def test_generate_success(
        self,
        generator: JMXGenerator,
        sample_spec_data: dict,
        temp_project_dir: Path
    ) -> None:
        """Test successful JMX generation."""
        output_path = temp_project_dir / "test.jmx"

        result = generator.generate(
            spec_data=sample_spec_data,
            output_path=str(output_path),
            threads=15,
            rampup=8,
            duration=90
        )

        # Check result structure
        assert result["success"] is True
        assert result["jmx_path"] == str(output_path.absolute())
        assert result["samplers_created"] == 4  # 4 endpoints
        assert result["assertions_added"] == 4  # 1 per endpoint
        assert result["threads"] == 15
        assert result["rampup"] == 8
        assert result["duration"] == 90
        assert "summary" in result
        assert "4 HTTP samplers" in result["summary"]

        # Check file was created
        assert output_path.exists()

        # Check file is valid XML
        tree = ET.parse(output_path)
        root = tree.getroot()
        assert root.tag == "jmeterTestPlan"

    def test_generate_with_base_url_override(
        self,
        generator: JMXGenerator,
        sample_spec_data: dict,
        temp_project_dir: Path
    ) -> None:
        """Test JMX generation with base URL override."""
        output_path = temp_project_dir / "test.jmx"

        result = generator.generate(
            spec_data=sample_spec_data,
            output_path=str(output_path),
            base_url="https://staging.example.com:9090"
        )

        assert result["success"] is True

        # Parse generated JMX and check HTTP Request Defaults
        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find HTTP Request Defaults
        config = root.find(".//ConfigTestElement[@testname='HTTP Request Defaults']")
        assert config is not None

        # Check domain, port, protocol match override
        domain = config.find("stringProp[@name='HTTPSampler.domain']")
        assert domain.text == "staging.example.com"

        port = config.find("stringProp[@name='HTTPSampler.port']")
        assert port.text == "9090"

        protocol = config.find("stringProp[@name='HTTPSampler.protocol']")
        assert protocol.text == "https"

    def test_generate_with_endpoint_filter(
        self,
        generator: JMXGenerator,
        sample_spec_data: dict,
        temp_project_dir: Path
    ) -> None:
        """Test JMX generation with endpoint filtering."""
        output_path = temp_project_dir / "test.jmx"

        result = generator.generate(
            spec_data=sample_spec_data,
            output_path=str(output_path),
            endpoints=["getUsers", "createUser"]  # Only 2 of 4 endpoints
        )

        assert result["success"] is True
        assert result["samplers_created"] == 2
        assert result["assertions_added"] == 2

    def test_generate_minimal_spec(
        self,
        generator: JMXGenerator,
        minimal_spec_data: dict,
        temp_project_dir: Path
    ) -> None:
        """Test JMX generation with minimal spec data."""
        output_path = temp_project_dir / "minimal.jmx"

        result = generator.generate(
            spec_data=minimal_spec_data,
            output_path=str(output_path)
        )

        assert result["success"] is True
        assert result["samplers_created"] == 1
        assert output_path.exists()

    def test_generate_creates_directories(
        self,
        generator: JMXGenerator,
        sample_spec_data: dict,
        temp_project_dir: Path
    ) -> None:
        """Test that generate creates parent directories if needed."""
        output_path = temp_project_dir / "subdir" / "nested" / "test.jmx"

        result = generator.generate(
            spec_data=sample_spec_data,
            output_path=str(output_path)
        )

        assert result["success"] is True
        assert output_path.exists()
        assert output_path.parent.exists()

    def test_generate_xml_structure(
        self,
        generator: JMXGenerator,
        sample_spec_data: dict,
        temp_project_dir: Path
    ) -> None:
        """Test that generated JMX has correct XML structure."""
        output_path = temp_project_dir / "structure.jmx"

        generator.generate(
            spec_data=sample_spec_data,
            output_path=str(output_path)
        )

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Check root element
        assert root.tag == "jmeterTestPlan"
        assert root.get("version") == "1.2"

        # Check TestPlan exists
        test_plan = root.find(".//TestPlan")
        assert test_plan is not None
        assert test_plan.get("testname") == "Test API v1.0.0"

        # Check ThreadGroup exists
        thread_group = root.find(".//ThreadGroup")
        assert thread_group is not None

        # CRITICAL: Check HTTP Request Defaults is at TestPlan level (not ThreadGroup)
        config = root.find(".//ConfigTestElement[@testname='HTTP Request Defaults']")
        assert config is not None

        # Verify HTTP Request Defaults is a child of TestPlan's hashTree, not ThreadGroup's hashTree
        # Navigate the structure: root -> hashTree -> TestPlan -> hashTree
        main_hashtree = root.find("hashTree")
        assert main_hashtree is not None

        # Find TestPlan's hashTree (the hashTree that follows TestPlan)
        test_plan_hashtree = None
        found_testplan = False
        for child in main_hashtree:
            if found_testplan and child.tag == "hashTree":
                test_plan_hashtree = child
                break
            if child.tag == "TestPlan":
                found_testplan = True

        assert test_plan_hashtree is not None, "Could not find TestPlan's hashTree"

        # ConfigTestElement should be a direct child of TestPlan's hashTree
        config_in_testplan = None
        for child in test_plan_hashtree:
            if child.tag == "ConfigTestElement" and child.get("testname") == "HTTP Request Defaults":
                config_in_testplan = child
                break

        assert config_in_testplan is not None, "HTTP Request Defaults should be at TestPlan level"

        # Verify ConfigTestElement is NOT in ThreadGroup's hashTree
        # Find ThreadGroup's hashTree (the hashTree that follows ThreadGroup in test_plan_hashtree)
        thread_group_hashtree = None
        found_threadgroup = False
        for child in test_plan_hashtree:
            if found_threadgroup and child.tag == "hashTree":
                thread_group_hashtree = child
                break
            if child.tag == "ThreadGroup":
                found_threadgroup = True

        if thread_group_hashtree is not None:
            config_in_threadgroup = None
            for child in thread_group_hashtree:
                if child.tag == "ConfigTestElement" and child.get("testname") == "HTTP Request Defaults":
                    config_in_threadgroup = child
                    break

            assert config_in_threadgroup is None, "HTTP Request Defaults should NOT be in ThreadGroup"

        # Check HTTP Samplers exist
        samplers = root.findall(".//HTTPSamplerProxy")
        assert len(samplers) == 4

        # Verify samplers have empty domain/port/protocol
        for sampler in samplers:
            domain = sampler.find("stringProp[@name='HTTPSampler.domain']")
            assert domain.text is None or domain.text == ""

            port = sampler.find("stringProp[@name='HTTPSampler.port']")
            assert port.text is None or port.text == ""

            protocol = sampler.find("stringProp[@name='HTTPSampler.protocol']")
            assert protocol.text is None or protocol.text == ""

        # Check Response Assertions exist
        assertions = root.findall(".//ResponseAssertion")
        assert len(assertions) == 4

    def test_generate_with_default_values(
        self,
        generator: JMXGenerator,
        minimal_spec_data: dict,
        temp_project_dir: Path
    ) -> None:
        """Test that default thread/rampup/duration values are used."""
        output_path = temp_project_dir / "defaults.jmx"

        result = generator.generate(
            spec_data=minimal_spec_data,
            output_path=str(output_path)
            # Not specifying threads/rampup/duration
        )

        assert result["threads"] == JMXGenerator.DEFAULT_THREADS
        assert result["rampup"] == JMXGenerator.DEFAULT_RAMPUP
        assert result["duration"] == JMXGenerator.DEFAULT_DURATION

        # Verify in XML
        tree = ET.parse(output_path)
        thread_group = tree.find(".//ThreadGroup")

        num_threads = thread_group.find("stringProp[@name='ThreadGroup.num_threads']")
        assert num_threads.text == str(JMXGenerator.DEFAULT_THREADS)

    def test_generate_no_endpoints_error(
        self,
        generator: JMXGenerator,
        temp_project_dir: Path
    ) -> None:
        """Test error when spec has no endpoints."""
        spec_data = {
            "title": "Empty API",
            "version": "1.0",
            "base_url": "http://localhost",
            "endpoints": []
        }
        output_path = temp_project_dir / "test.jmx"

        with pytest.raises(JMXGenerationException) as exc_info:
            generator.generate(spec_data=spec_data, output_path=str(output_path))

        assert "No endpoints found" in str(exc_info.value)

    def test_generate_filtered_endpoints_not_found(
        self,
        generator: JMXGenerator,
        sample_spec_data: dict,
        temp_project_dir: Path
    ) -> None:
        """Test error when filtered endpoints don't exist."""
        output_path = temp_project_dir / "test.jmx"

        with pytest.raises(JMXGenerationException) as exc_info:
            generator.generate(
                spec_data=sample_spec_data,
                output_path=str(output_path),
                endpoints=["nonExistentOperation"]
            )

        assert "No endpoints found" in str(exc_info.value)

    def test_generate_with_none_base_url(
        self,
        generator: JMXGenerator,
        sample_spec_data: dict,
        temp_project_dir: Path
    ) -> None:
        """Test that None base URL defaults to localhost."""
        output_path = temp_project_dir / "test.jmx"
        sample_spec_data["base_url"] = None

        result = generator.generate(spec_data=sample_spec_data, output_path=str(output_path))

        # Should succeed and use localhost as default
        assert result["success"] is True

        # Verify HTTP Request Defaults uses localhost
        tree = ET.parse(output_path)
        config = tree.find(".//ConfigTestElement[@testname='HTTP Request Defaults']")
        domain = config.find("stringProp[@name='HTTPSampler.domain']")
        assert domain.text == "localhost"

    def test_hashtree_structure(
        self,
        generator: JMXGenerator,
        minimal_spec_data: dict,
        temp_project_dir: Path
    ) -> None:
        """Test that hashTree elements are properly structured."""
        output_path = temp_project_dir / "hashtree.jmx"

        generator.generate(
            spec_data=minimal_spec_data,
            output_path=str(output_path)
        )

        # Read file content
        content = output_path.read_text()

        # Every major element should be followed by hashTree
        assert content.count("<hashTree>") > 0 or content.count("<hashTree/>") > 0

        # Parse and check structure
        tree = ET.parse(output_path)
        root = tree.getroot()

        # Main hashTree should be child of jmeterTestPlan
        main_hashtree = list(root)[0]
        assert main_hashtree.tag == "hashTree"


class TestRequestBodySupport:
    """Tests for request body and HeaderManager functionality."""

    @pytest.fixture
    def generator(self) -> JMXGenerator:
        """Provide JMXGenerator instance."""
        return JMXGenerator()

    @pytest.fixture
    def temp_output_dir(self, tmp_path: Path) -> Path:
        """Provide temporary directory for test outputs."""
        return tmp_path / "jmx_output"

    def test_create_header_manager(self, generator: JMXGenerator) -> None:
        """Test creating HTTP Header Manager with Content-Type."""
        header_manager = generator._create_header_manager({"Content-Type": "application/json"})

        assert header_manager is not None
        assert header_manager.tag == "HeaderManager"
        assert header_manager.get("guiclass") == "HeaderPanel"
        assert header_manager.get("testclass") == "HeaderManager"
        assert header_manager.get("testname") == "HTTP Header Manager"

        # Check for header collection
        coll_prop = header_manager.find(".//collectionProp[@name='HeaderManager.headers']")
        assert coll_prop is not None

        # Check for Content-Type header
        elem_prop = coll_prop.find(".//elementProp[@elementType='Header']")
        assert elem_prop is not None

        header_name = elem_prop.find(".//stringProp[@name='Header.name']")
        assert header_name is not None
        assert header_name.text == "Content-Type"

        header_value = elem_prop.find(".//stringProp[@name='Header.value']")
        assert header_value is not None
        assert header_value.text == "application/json"

    def test_create_http_sampler_with_body(self, generator: JMXGenerator) -> None:
        """Test creating HTTP Sampler with request body."""
        endpoint = {
            "path": "/api/users",
            "method": "POST",
            "operationId": "createUser",
            "summary": "Create a new user",
            "requestBody": True,
            "parameters": []
        }

        request_body_json = '{"name": "John", "age": 30}'
        sampler, headers = generator._create_http_sampler(endpoint, request_body_json)

        assert sampler is not None
        assert sampler.tag == "HTTPSamplerProxy"

        # Check for postBodyRaw property
        post_body_raw = sampler.find(".//boolProp[@name='HTTPSampler.postBodyRaw']")
        assert post_body_raw is not None
        assert post_body_raw.text == "true"

        # Check for body value
        body_arg = sampler.find(".//elementProp[@elementType='HTTPArgument']")
        assert body_arg is not None

        arg_value = body_arg.find(".//stringProp[@name='Argument.value']")
        assert arg_value is not None
        assert arg_value.text == request_body_json

    def test_create_http_sampler_without_body(self, generator: JMXGenerator) -> None:
        """Test creating HTTP Sampler without request body."""
        endpoint = {
            "path": "/api/users",
            "method": "GET",
            "operationId": "getUsers",
            "summary": "Get all users",
            "requestBody": False,
            "parameters": []
        }

        sampler, headers = generator._create_http_sampler(endpoint, None)

        assert sampler is not None
        assert sampler.tag == "HTTPSamplerProxy"

        # Check that postBodyRaw is NOT present
        post_body_raw = sampler.find(".//boolProp[@name='HTTPSampler.postBodyRaw']")
        assert post_body_raw is None

    def test_generate_with_request_body(
        self, generator: JMXGenerator, temp_output_dir: Path
    ) -> None:
        """Test full generation with endpoints that have request bodies."""
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/api/users",
                    "method": "POST",
                    "operationId": "createUser",
                    "summary": "Create user",
                    "requestBody": True,
                    "content_type": "application/json",
                    "request_body_schema": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    },
                    "parameters": [],
                }
            ],
        }

        output_path = temp_output_dir / "test_with_body.jmx"
        result = generator.generate(spec_data, str(output_path))

        assert result["success"] is True
        assert result["samplers_created"] == 1
        assert result["headers_added"] == 1
        assert result["assertions_added"] == 1

        # Verify file was created
        assert output_path.exists()

        # Parse and verify structure
        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find HeaderManager
        header_manager = root.find(".//HeaderManager")
        assert header_manager is not None

        # Find HTTP Sampler with body
        sampler = root.find(".//HTTPSamplerProxy")
        assert sampler is not None

        post_body_raw = sampler.find(".//boolProp[@name='HTTPSampler.postBodyRaw']")
        assert post_body_raw is not None

    def test_generate_without_request_body(
        self, generator: JMXGenerator, temp_output_dir: Path
    ) -> None:
        """Test generation with endpoints that don't have request bodies."""
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/api/users",
                    "method": "GET",
                    "operationId": "getUsers",
                    "summary": "Get users",
                    "requestBody": False,
                    "content_type": None,
                    "request_body_schema": None,
                    "parameters": [],
                }
            ],
        }

        output_path = temp_output_dir / "test_without_body.jmx"
        result = generator.generate(spec_data, str(output_path))

        assert result["success"] is True
        assert result["samplers_created"] == 1
        assert result["headers_added"] == 0  # No HeaderManager for GET
        assert result["assertions_added"] == 1

        # Verify file was created
        assert output_path.exists()

        # Parse and verify structure
        tree = ET.parse(output_path)
        root = tree.getroot()

        # HeaderManager should NOT be present
        header_manager = root.find(".//HeaderManager")
        assert header_manager is None

        # HTTP Sampler should NOT have postBodyRaw
        sampler = root.find(".//HTTPSamplerProxy")
        assert sampler is not None

        post_body_raw = sampler.find(".//boolProp[@name='HTTPSampler.postBodyRaw']")
        assert post_body_raw is None

    def test_create_query_parameters_element(self, generator: JMXGenerator) -> None:
        """Test _create_query_parameters_element helper method."""
        parameters = [
            {"name": "username", "in": "query", "example": "testuser"},
            {"name": "limit", "in": "query", "default": "10"},
            {"name": "offset", "in": "query"},  # No example/default
            {"name": "id", "in": "path"},  # Should be ignored
        ]

        elem = generator._create_query_parameters_element(parameters)

        assert elem.tag == "elementProp"
        assert elem.get("name") == "HTTPsampler.Arguments"
        assert elem.get("elementType") == "Arguments"

        # Find collectionProp
        coll_prop = elem.find("collectionProp[@name='Arguments.arguments']")
        assert coll_prop is not None

        # Find all HTTPArgument elements
        http_args = coll_prop.findall("elementProp[@elementType='HTTPArgument']")
        assert len(http_args) == 3  # Only query params, not path param

        # Verify first parameter (with example)
        arg1 = http_args[0]
        assert arg1.get("name") == "username"
        arg1_name = arg1.find("stringProp[@name='Argument.name']")
        assert arg1_name is not None
        assert arg1_name.text == "username"
        arg1_value = arg1.find("stringProp[@name='Argument.value']")
        assert arg1_value is not None
        assert arg1_value.text == "testuser"

        # Verify second parameter (with default)
        arg2 = http_args[1]
        assert arg2.get("name") == "limit"
        arg2_value = arg2.find("stringProp[@name='Argument.value']")
        assert arg2_value is not None
        assert arg2_value.text == "10"

        # Verify third parameter (no example/default - should use JMeter variable)
        arg3 = http_args[2]
        assert arg3.get("name") == "offset"
        arg3_value = arg3.find("stringProp[@name='Argument.value']")
        assert arg3_value is not None
        assert arg3_value.text == "${offset}"

    def test_create_query_parameters_element_empty(self, generator: JMXGenerator) -> None:
        """Test _create_query_parameters_element with no query parameters."""
        parameters = [
            {"name": "id", "in": "path"},
            {"name": "Authorization", "in": "header"},
        ]

        elem = generator._create_query_parameters_element(parameters)

        # Should still create valid structure but with no arguments
        coll_prop = elem.find("collectionProp[@name='Arguments.arguments']")
        assert coll_prop is not None

        http_args = coll_prop.findall("elementProp[@elementType='HTTPArgument']")
        assert len(http_args) == 0

    def test_convert_path_parameters(self, generator: JMXGenerator) -> None:
        """Test _convert_path_parameters helper method."""
        parameters = [
            {"name": "id", "in": "path"},
            {"name": "itemId", "in": "path"},
        ]

        # Test with path parameters
        path1 = "/users/{id}/items/{itemId}"
        result1 = generator._convert_path_parameters(path1, parameters)
        assert result1 == "/users/${id}/items/${itemId}"

        # Test with single parameter
        path2 = "/users/{id}"
        result2 = generator._convert_path_parameters(path2, parameters)
        assert result2 == "/users/${id}"

        # Test with no parameters in path
        path3 = "/users"
        result3 = generator._convert_path_parameters(path3, parameters)
        assert result3 == "/users"

    def test_convert_path_parameters_only_actual_params(self, generator: JMXGenerator) -> None:
        """Test that only parameters in the parameters list are converted."""
        parameters = [
            {"name": "id", "in": "path"},
        ]

        # {notInList} should NOT be converted because it's not in parameters
        path = "/users/{id}/items/{notInList}"
        result = generator._convert_path_parameters(path, parameters)
        assert result == "/users/${id}/items/{notInList}"

    def test_convert_path_parameters_empty(self, generator: JMXGenerator) -> None:
        """Test _convert_path_parameters with no path parameters."""
        parameters = [
            {"name": "limit", "in": "query"},
        ]

        path = "/users/{id}"
        result = generator._convert_path_parameters(path, parameters)
        # {id} should remain unchanged because no path parameter named 'id'
        assert result == "/users/{id}"

    def test_create_header_manager_multiple_headers(self, generator: JMXGenerator) -> None:
        """Test _create_header_manager with multiple headers."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer ${token}",
            "X-API-Key": "${apiKey}",
        }

        header_manager = generator._create_header_manager(headers)

        assert header_manager.tag == "HeaderManager"
        assert header_manager.get("testname") == "HTTP Header Manager"

        # Find collectionProp
        coll_prop = header_manager.find("collectionProp[@name='HeaderManager.headers']")
        assert coll_prop is not None

        # Find all Header elements
        header_elems = coll_prop.findall("elementProp[@elementType='Header']")
        assert len(header_elems) == 3

        # Collect actual headers
        actual_headers = {}
        for header_elem in header_elems:
            name_prop = header_elem.find("stringProp[@name='Header.name']")
            value_prop = header_elem.find("stringProp[@name='Header.value']")
            if name_prop is not None and value_prop is not None:
                actual_headers[name_prop.text] = value_prop.text

        assert actual_headers == headers

    def test_create_header_manager_single_header(self, generator: JMXGenerator) -> None:
        """Test _create_header_manager with single header."""
        headers = {"Content-Type": "application/json"}

        header_manager = generator._create_header_manager(headers)

        coll_prop = header_manager.find("collectionProp[@name='HeaderManager.headers']")
        assert coll_prop is not None

        header_elems = coll_prop.findall("elementProp[@elementType='Header']")
        assert len(header_elems) == 1

        name_prop = header_elems[0].find("stringProp[@name='Header.name']")
        value_prop = header_elems[0].find("stringProp[@name='Header.value']")
        assert name_prop.text == "Content-Type"
        assert value_prop.text == "application/json"

    def test_create_header_manager_empty(self, generator: JMXGenerator) -> None:
        """Test _create_header_manager with empty dict."""
        headers = {}

        header_manager = generator._create_header_manager(headers)

        coll_prop = header_manager.find("collectionProp[@name='HeaderManager.headers']")
        assert coll_prop is not None

        header_elems = coll_prop.findall("elementProp[@elementType='Header']")
        assert len(header_elems) == 0

    def test_generate_with_query_parameters(
        self, generator: JMXGenerator, temp_output_dir: Path
    ) -> None:
        """Test generation with query parameters."""
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/api/users",
                    "method": "GET",
                    "operationId": "getUsers",
                    "summary": "Get users with filters",
                    "requestBody": False,
                    "content_type": None,
                    "request_body_schema": None,
                    "parameters": [
                        {"name": "limit", "in": "query", "default": "10"},
                        {"name": "offset", "in": "query"},
                    ],
                }
            ],
        }

        output_path = temp_output_dir / "test_query_params.jmx"
        result = generator.generate(spec_data, str(output_path))

        assert result["success"] is True
        assert result["samplers_created"] == 1

        # Parse and verify structure
        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find HTTP Sampler
        sampler = root.find(".//HTTPSamplerProxy")
        assert sampler is not None

        # Find Arguments collectionProp
        args_coll = sampler.find(".//collectionProp[@name='Arguments.arguments']")
        assert args_coll is not None

        # Find HTTPArgument elements
        http_args = args_coll.findall("elementProp[@elementType='HTTPArgument']")
        assert len(http_args) == 2

        # Verify query parameters
        arg_names = [arg.get("name") for arg in http_args]
        assert "limit" in arg_names
        assert "offset" in arg_names

    def test_generate_with_path_parameters(
        self, generator: JMXGenerator, temp_output_dir: Path
    ) -> None:
        """Test generation with path parameters."""
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/api/users/{id}/items/{itemId}",
                    "method": "GET",
                    "operationId": "getUserItem",
                    "summary": "Get user item",
                    "requestBody": False,
                    "content_type": None,
                    "request_body_schema": None,
                    "parameters": [
                        {"name": "id", "in": "path"},
                        {"name": "itemId", "in": "path"},
                    ],
                }
            ],
        }

        output_path = temp_output_dir / "test_path_params.jmx"
        result = generator.generate(spec_data, str(output_path))

        assert result["success"] is True

        # Parse and verify path conversion
        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find HTTP Sampler path
        path_prop = root.find(".//stringProp[@name='HTTPSampler.path']")
        assert path_prop is not None
        assert path_prop.text == "/api/users/${id}/items/${itemId}"

    def test_generate_with_header_parameters(
        self, generator: JMXGenerator, temp_output_dir: Path
    ) -> None:
        """Test generation with header parameters."""
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/api/users",
                    "method": "GET",
                    "operationId": "getUsers",
                    "summary": "Get users",
                    "requestBody": False,
                    "content_type": None,
                    "request_body_schema": None,
                    "parameters": [
                        {"name": "Authorization", "in": "header", "example": "Bearer token123"},
                        {"name": "X-API-Key", "in": "header"},
                    ],
                }
            ],
        }

        output_path = temp_output_dir / "test_header_params.jmx"
        result = generator.generate(spec_data, str(output_path))

        assert result["success"] is True
        assert result["headers_added"] == 1

        # Parse and verify HeaderManager
        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find HeaderManager
        header_manager = root.find(".//HeaderManager")
        assert header_manager is not None

        # Find Header elements
        headers_coll = header_manager.find(".//collectionProp[@name='HeaderManager.headers']")
        assert headers_coll is not None

        header_elems = headers_coll.findall("elementProp[@elementType='Header']")
        assert len(header_elems) == 2

        # Collect header names
        header_names = []
        for header_elem in header_elems:
            name_prop = header_elem.find("stringProp[@name='Header.name']")
            if name_prop is not None:
                header_names.append(name_prop.text)

        assert "Authorization" in header_names
        assert "X-API-Key" in header_names

    def test_generate_with_all_parameter_types(
        self, generator: JMXGenerator, temp_output_dir: Path
    ) -> None:
        """Test generation with query, path, and header parameters combined."""
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/api/users/{id}",
                    "method": "GET",
                    "operationId": "getUser",
                    "summary": "Get user by ID",
                    "requestBody": False,
                    "content_type": None,
                    "request_body_schema": None,
                    "parameters": [
                        {"name": "id", "in": "path"},
                        {"name": "include", "in": "query", "default": "profile"},
                        {"name": "Authorization", "in": "header"},
                    ],
                }
            ],
        }

        output_path = temp_output_dir / "test_all_params.jmx"
        result = generator.generate(spec_data, str(output_path))

        assert result["success"] is True
        assert result["samplers_created"] == 1
        assert result["headers_added"] == 1

        # Parse and verify all parameter types
        tree = ET.parse(output_path)
        root = tree.getroot()

        # Verify path parameter conversion
        path_prop = root.find(".//stringProp[@name='HTTPSampler.path']")
        assert path_prop is not None
        assert path_prop.text == "/api/users/${id}"

        # Verify query parameter
        sampler = root.find(".//HTTPSamplerProxy")
        args_coll = sampler.find(".//collectionProp[@name='Arguments.arguments']")
        http_args = args_coll.findall("elementProp[@elementType='HTTPArgument']")
        assert len(http_args) == 1
        assert http_args[0].get("name") == "include"

        # Verify header parameter
        header_manager = root.find(".//HeaderManager")
        assert header_manager is not None
        headers_coll = header_manager.find(".//collectionProp[@name='HeaderManager.headers']")
        header_elems = headers_coll.findall("elementProp[@elementType='Header']")
        assert len(header_elems) == 1
        header_name = header_elems[0].find("stringProp[@name='Header.name']")
        assert header_name.text == "Authorization"

    def test_generate_with_request_body_and_header_parameters(
        self, generator: JMXGenerator, temp_output_dir: Path
    ) -> None:
        """Test that Content-Type and header parameters are merged correctly."""
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/api/users",
                    "method": "POST",
                    "operationId": "createUser",
                    "summary": "Create user",
                    "requestBody": True,
                    "content_type": "application/json",
                    "request_body_schema": {"type": "object"},
                    "parameters": [
                        {"name": "X-Request-ID", "in": "header", "example": "req-123"},
                    ],
                }
            ],
        }

        output_path = temp_output_dir / "test_body_and_headers.jmx"
        result = generator.generate(spec_data, str(output_path))

        assert result["success"] is True
        assert result["headers_added"] == 1

        # Parse and verify HeaderManager has both Content-Type and custom header
        tree = ET.parse(output_path)
        root = tree.getroot()

        header_manager = root.find(".//HeaderManager")
        assert header_manager is not None

        headers_coll = header_manager.find(".//collectionProp[@name='HeaderManager.headers']")
        header_elems = headers_coll.findall("elementProp[@elementType='Header']")
        assert len(header_elems) == 2

        # Collect headers
        headers = {}
        for header_elem in header_elems:
            name_prop = header_elem.find("stringProp[@name='Header.name']")
            value_prop = header_elem.find("stringProp[@name='Header.value']")
            if name_prop is not None and value_prop is not None:
                headers[name_prop.text] = value_prop.text

        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert "X-Request-ID" in headers
        assert headers["X-Request-ID"] == "req-123"
