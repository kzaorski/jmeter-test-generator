"""Unit tests for ScenarioJMXGenerator."""

import xml.etree.ElementTree as ET

import pytest

from jmeter_gen.core.openapi_parser import OpenAPIParser
from jmeter_gen.core.scenario_jmx_generator import ScenarioJMXGenerator
from jmeter_gen.core.scenario_data import (
    AssertConfig,
    CaptureConfig,
    CorrelationMapping,
    CorrelationResult,
    LoopConfig,
    ParsedScenario,
    ScenarioSettings,
    ScenarioStep,
)

# Mark all tests in this module as v2 tests
pytestmark = pytest.mark.v2


class TestScenarioJMXGenerator:
    """Tests for ScenarioJMXGenerator class."""

    @pytest.fixture
    def parser(self, tmp_path):
        """Create a parser instance with sample spec."""
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
      summary: List users
      responses:
        '200':
          description: Success
    post:
      operationId: createUser
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
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: integer
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
"""
        spec_path = tmp_path / "openapi.yaml"
        spec_path.write_text(spec_content)
        parser = OpenAPIParser()
        parser.parse(str(spec_path))
        return parser

    @pytest.fixture
    def generator(self, parser):
        """Create a generator instance."""
        return ScenarioJMXGenerator(parser)

    @pytest.fixture
    def simple_scenario(self):
        """Create a simple scenario for testing."""
        return ParsedScenario(
            version="1.0",
            name="Test Scenario",
            description="A test scenario",
            settings=ScenarioSettings(
                threads=5, rampup=10, duration=60, base_url="http://localhost:8000"
            ),
            variables={"api_key": "test123"},
            steps=[
                ScenarioStep(
                    name="Get Users",
                    endpoint="GET /users",
                    endpoint_type="method_path",
                    method="GET",
                    path="/users",
                    headers={"Authorization": "Bearer ${api_key}"},
                    assertions=AssertConfig(status=200),
                ),
                ScenarioStep(
                    name="Create User",
                    endpoint="POST /users",
                    endpoint_type="method_path",
                    method="POST",
                    path="/users",
                    headers={"Content-Type": "application/json"},
                    payload={"name": "Test", "email": "test@example.com"},
                    captures=[CaptureConfig(variable_name="userId", source_field="id")],
                    assertions=AssertConfig(status=201),
                ),
                ScenarioStep(
                    name="Get User",
                    endpoint="GET /users/${userId}",
                    endpoint_type="method_path",
                    method="GET",
                    path="/users/${userId}",
                    assertions=AssertConfig(status=200),
                ),
            ],
        )

    @pytest.fixture
    def correlation_result(self):
        """Create correlation results for testing."""
        return CorrelationResult(
            mappings=[
                CorrelationMapping(
                    variable_name="userId",
                    jsonpath="$.id",
                    source_step=2,
                    source_endpoint="POST /users",
                    target_steps=[3],
                    confidence=1.0,
                    match_type="mapped",
                )
            ]
        )

    def test_generate_creates_file(self, generator, simple_scenario, tmp_path):
        """Test that generate creates a JMX file."""
        output_path = tmp_path / "test.jmx"

        result = generator.generate(
            scenario=simple_scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True
        assert output_path.exists()
        assert "jmx_path" in result

    def test_generate_valid_xml(self, generator, simple_scenario, tmp_path):
        """Test that generated file is valid XML."""
        output_path = tmp_path / "test.jmx"

        generator.generate(
            scenario=simple_scenario,
            output_path=str(output_path),
        )

        # Should not raise
        tree = ET.parse(output_path)
        root = tree.getroot()
        assert root.tag == "jmeterTestPlan"

    def test_generate_contains_test_plan(self, generator, simple_scenario, tmp_path):
        """Test that generated JMX contains TestPlan element."""
        output_path = tmp_path / "test.jmx"

        generator.generate(
            scenario=simple_scenario,
            output_path=str(output_path),
        )

        tree = ET.parse(output_path)
        root = tree.getroot()

        test_plan = root.find(".//TestPlan")
        assert test_plan is not None
        assert "Test Scenario" in test_plan.get("testname")

    def test_generate_contains_thread_group(self, generator, simple_scenario, tmp_path):
        """Test that generated JMX contains ThreadGroup with correct settings."""
        output_path = tmp_path / "test.jmx"

        generator.generate(
            scenario=simple_scenario,
            output_path=str(output_path),
        )

        tree = ET.parse(output_path)
        root = tree.getroot()

        thread_group = root.find(".//ThreadGroup")
        assert thread_group is not None

        # Check thread count
        num_threads = thread_group.find(".//stringProp[@name='ThreadGroup.num_threads']")
        assert num_threads is not None
        assert num_threads.text == "5"

        # Check ramp-up
        rampup = thread_group.find(".//stringProp[@name='ThreadGroup.ramp_time']")
        assert rampup is not None
        assert rampup.text == "10"

    def test_generate_contains_http_samplers(self, generator, simple_scenario, tmp_path):
        """Test that generated JMX contains HTTP samplers for each step."""
        output_path = tmp_path / "test.jmx"

        generator.generate(
            scenario=simple_scenario,
            output_path=str(output_path),
        )

        tree = ET.parse(output_path)
        root = tree.getroot()

        samplers = root.findall(".//HTTPSamplerProxy")
        assert len(samplers) == 3

    def test_generate_http_sampler_methods(self, generator, simple_scenario, tmp_path):
        """Test that HTTP samplers have correct methods."""
        output_path = tmp_path / "test.jmx"

        generator.generate(
            scenario=simple_scenario,
            output_path=str(output_path),
        )

        tree = ET.parse(output_path)
        root = tree.getroot()

        samplers = root.findall(".//HTTPSamplerProxy")

        methods = []
        for sampler in samplers:
            method_prop = sampler.find(".//stringProp[@name='HTTPSampler.method']")
            if method_prop is not None:
                methods.append(method_prop.text)

        assert "GET" in methods
        assert "POST" in methods

    def test_generate_with_correlations(
        self, generator, simple_scenario, correlation_result, tmp_path
    ):
        """Test that JSON extractors are added for correlations."""
        output_path = tmp_path / "test.jmx"

        generator.generate(
            scenario=simple_scenario,
            output_path=str(output_path),
            correlation_result=correlation_result,
        )

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Look for JSON Post Processor
        extractors = root.findall(".//JSONPostProcessor")
        assert len(extractors) >= 1

        # Check extractor configuration
        extractor = extractors[0]
        ref_names = extractor.find(".//stringProp[@name='JSONPostProcessor.referenceNames']")
        assert ref_names is not None
        assert "userId" in ref_names.text

        json_paths = extractor.find(".//stringProp[@name='JSONPostProcessor.jsonPathExprs']")
        assert json_paths is not None
        assert "$.id" in json_paths.text

    def test_generate_with_response_assertion(self, generator, simple_scenario, tmp_path):
        """Test that response assertions are added."""
        output_path = tmp_path / "test.jmx"

        generator.generate(
            scenario=simple_scenario,
            output_path=str(output_path),
        )

        tree = ET.parse(output_path)
        root = tree.getroot()

        assertions = root.findall(".//ResponseAssertion")
        assert len(assertions) >= 1

    def test_generate_with_headers(self, generator, simple_scenario, tmp_path):
        """Test that headers are included in requests."""
        output_path = tmp_path / "test.jmx"

        generator.generate(
            scenario=simple_scenario,
            output_path=str(output_path),
        )

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Look for Header Manager
        header_managers = root.findall(".//HeaderManager")
        assert len(header_managers) >= 1

    def test_generate_returns_metadata(self, generator, simple_scenario, tmp_path):
        """Test that generate returns useful metadata."""
        output_path = tmp_path / "test.jmx"

        result = generator.generate(
            scenario=simple_scenario,
            output_path=str(output_path),
        )

        assert "success" in result
        assert "jmx_path" in result
        assert "samplers_created" in result
        assert result["samplers_created"] == 3


class TestScenarioJMXGeneratorEdgeCases:
    """Edge case tests for ScenarioJMXGenerator."""

    @pytest.fixture
    def parser(self, tmp_path):
        """Create a parser instance."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /test:
    get:
      operationId: test
      responses:
        '200':
          description: OK
"""
        spec_path = tmp_path / "spec.yaml"
        spec_path.write_text(spec_content)
        parser = OpenAPIParser()
        parser.parse(str(spec_path))
        return parser

    @pytest.fixture
    def generator(self, parser):
        """Create a generator instance."""
        return ScenarioJMXGenerator(parser)

    def test_generate_minimal_scenario(self, generator, tmp_path):
        """Test generating from minimal scenario."""
        scenario = ParsedScenario(
            version="1.0",
            name="Minimal",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Simple Request",
                    endpoint="GET /test",
                    endpoint_type="method_path",
                    method="GET",
                    path="/test",
                )
            ],
        )

        output_path = tmp_path / "minimal.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True
        assert output_path.exists()

    def test_generate_with_operationid_endpoint(self, generator, tmp_path):
        """Test generating with operationId format endpoint."""
        scenario = ParsedScenario(
            version="1.0",
            name="OperationId Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Test Op",
                    endpoint="test",
                    endpoint_type="operation_id",
                )
            ],
        )

        output_path = tmp_path / "opid.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

    def test_generate_with_body_assertions(self, generator, tmp_path):
        """Test generating with body assertions."""
        scenario = ParsedScenario(
            version="1.0",
            name="Body Assert Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Get User",
                    endpoint="GET /users/1",
                    endpoint_type="method_path",
                    method="GET",
                    path="/users/1",
                    assertions=AssertConfig(
                        status=200, body={"name": "Test User", "email": "test@example.com"}
                    ),
                )
            ],
        )

        output_path = tmp_path / "body_assert.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Should have JSONPath assertions for body content
        json_assertions = root.findall(".//JSONPathAssertion")
        assert len(json_assertions) >= 1

    def test_generate_http_defaults(self, generator, tmp_path):
        """Test that HTTP Request Defaults are generated."""
        scenario = ParsedScenario(
            version="1.0",
            name="Defaults Test",
            description=None,
            settings=ScenarioSettings(
                base_url="http://api.example.com:8080"
            ),
            variables={},
            steps=[
                ScenarioStep(
                    name="Test",
                    endpoint="GET /test",
                    endpoint_type="method_path",
                    method="GET",
                    path="/test",
                )
            ],
        )

        output_path = tmp_path / "defaults.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Look for ConfigTestElement (HTTP Request Defaults)
        config_elements = root.findall(".//ConfigTestElement")
        http_defaults = [
            e
            for e in config_elements
            if e.get("guiclass") == "HttpDefaultsGui"
        ]

        assert len(http_defaults) >= 1

    def test_generate_user_defined_variables(self, generator, tmp_path):
        """Test that user-defined variables are included."""
        scenario = ParsedScenario(
            version="1.0",
            name="Variables Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={"api_key": "secret123", "timeout": "5000"},
            steps=[
                ScenarioStep(
                    name="Test",
                    endpoint="GET /test",
                    endpoint_type="method_path",
                    method="GET",
                    path="/test",
                    headers={"Authorization": "Bearer ${api_key}"},
                )
            ],
        )

        output_path = tmp_path / "variables.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Look for User Defined Variables
        udv = root.find(".//Arguments[@testname='User Defined Variables']")
        assert udv is not None

    def test_generate_disabled_step_skipped(self, generator, tmp_path):
        """Test that disabled steps are skipped."""
        scenario = ParsedScenario(
            version="1.0",
            name="Disabled Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Enabled",
                    endpoint="GET /test",
                    endpoint_type="method_path",
                    method="GET",
                    path="/test",
                    enabled=True,
                ),
                ScenarioStep(
                    name="Disabled",
                    endpoint="GET /disabled",
                    endpoint_type="method_path",
                    method="GET",
                    path="/disabled",
                    enabled=False,
                ),
            ],
        )

        output_path = tmp_path / "disabled.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True
        # Only 1 sampler should be created (disabled skipped)
        assert result["samplers_created"] == 1


class TestLoopControllerGeneration:
    """Tests for loop controller JMX generation."""

    @pytest.fixture
    def parser(self, tmp_path):
        """Create a parser instance."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /trigger:
    post:
      operationId: trigger
      responses:
        '200':
          description: OK
  /status:
    get:
      operationId: getStatus
      responses:
        '200':
          description: OK
"""
        spec_path = tmp_path / "spec.yaml"
        spec_path.write_text(spec_content)
        parser = OpenAPIParser()
        parser.parse(str(spec_path))
        return parser

    @pytest.fixture
    def generator(self, parser):
        """Create a generator instance."""
        return ScenarioJMXGenerator(parser)

    def test_generate_loop_controller_count(self, generator, tmp_path):
        """Test that LoopController is generated for count loops."""
        scenario = ParsedScenario(
            version="1.0",
            name="Count Loop Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Poll Status",
                    endpoint="GET /status",
                    endpoint_type="method_path",
                    method="GET",
                    path="/status",
                    loop=LoopConfig(count=10),
                ),
            ],
        )

        output_path = tmp_path / "loop_count.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True
        assert result["loops_created"] == 1

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find LoopController
        loop_controllers = root.findall(".//LoopController")
        assert len(loop_controllers) >= 1

        # Check the testclass
        loop_ctrl = [lc for lc in loop_controllers if lc.get("testclass") == "LoopController"]
        assert len(loop_ctrl) >= 1

        # Check loop count
        for lc in loop_ctrl:
            loops_prop = lc.find(".//stringProp[@name='LoopController.loops']")
            if loops_prop is not None and loops_prop.text == "10":
                break
        else:
            pytest.fail("LoopController with 10 iterations not found")

    def test_generate_while_controller(self, generator, tmp_path):
        """Test that WhileController is generated for while loops."""
        scenario = ParsedScenario(
            version="1.0",
            name="While Loop Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Poll Until Done",
                    endpoint="GET /status",
                    endpoint_type="method_path",
                    method="GET",
                    path="/status",
                    loop=LoopConfig(while_condition="$.status != 'finished'", max_iterations=50),
                ),
            ],
        )

        output_path = tmp_path / "loop_while.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True
        assert result["loops_created"] == 1

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find WhileController
        while_controllers = root.findall(".//WhileController")
        assert len(while_controllers) == 1

        # Check condition contains groovy
        while_ctrl = while_controllers[0]
        condition_prop = while_ctrl.find(".//stringProp[@name='WhileController.condition']")
        assert condition_prop is not None
        assert "__groovy" in condition_prop.text
        assert "status" in condition_prop.text

    def test_generate_loop_with_interval(self, generator, tmp_path):
        """Test that ConstantTimer is generated for loop interval."""
        scenario = ParsedScenario(
            version="1.0",
            name="Loop Interval Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Poll Status",
                    endpoint="GET /status",
                    endpoint_type="method_path",
                    method="GET",
                    path="/status",
                    loop=LoopConfig(count=5, interval=30000),
                ),
            ],
        )

        output_path = tmp_path / "loop_interval.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find ConstantTimer
        timers = root.findall(".//ConstantTimer")
        assert len(timers) == 1

        # Check delay
        delay_prop = timers[0].find(".//stringProp[@name='ConstantTimer.delay']")
        assert delay_prop is not None
        assert delay_prop.text == "30000"

    def test_generate_while_loop_adds_extractor(self, generator, tmp_path):
        """Test that while loop adds JSONPostProcessor for condition variable."""
        scenario = ParsedScenario(
            version="1.0",
            name="While Extractor Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Poll Status",
                    endpoint="GET /status",
                    endpoint_type="method_path",
                    method="GET",
                    path="/status",
                    loop=LoopConfig(while_condition="$.status != 'done'", max_iterations=100),
                ),
            ],
        )

        output_path = tmp_path / "while_extractor.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True
        # Should have at least 1 extractor for the condition variable
        assert result["extractors_created"] >= 1

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find JSONPostProcessor for status variable
        extractors = root.findall(".//JSONPostProcessor")
        found_status_extractor = False
        for ext in extractors:
            ref_prop = ext.find(".//stringProp[@name='JSONPostProcessor.referenceNames']")
            if ref_prop is not None and ref_prop.text == "status":
                found_status_extractor = True
                break

        assert found_status_extractor, "JSONPostProcessor for 'status' variable not found"

    def test_generate_step_without_loop(self, generator, tmp_path):
        """Test that steps without loop don't get controllers."""
        scenario = ParsedScenario(
            version="1.0",
            name="No Loop Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Simple Request",
                    endpoint="GET /status",
                    endpoint_type="method_path",
                    method="GET",
                    path="/status",
                ),
            ],
        )

        output_path = tmp_path / "no_loop.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True
        assert result["loops_created"] == 0

        tree = ET.parse(output_path)
        root = tree.getroot()

        # No WhileController or standalone LoopController
        while_controllers = root.findall(".//WhileController")
        assert len(while_controllers) == 0

    def test_generate_mixed_loop_and_no_loop(self, generator, tmp_path):
        """Test scenario with both looped and non-looped steps."""
        scenario = ParsedScenario(
            version="1.0",
            name="Mixed Loop Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Trigger",
                    endpoint="POST /trigger",
                    endpoint_type="method_path",
                    method="POST",
                    path="/trigger",
                ),
                ScenarioStep(
                    name="Poll Status",
                    endpoint="GET /status",
                    endpoint_type="method_path",
                    method="GET",
                    path="/status",
                    loop=LoopConfig(count=10, interval=5000),
                ),
            ],
        )

        output_path = tmp_path / "mixed_loop.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True
        assert result["samplers_created"] == 2
        assert result["loops_created"] == 1

    def test_convert_condition_to_groovy(self, generator):
        """Test Groovy condition conversion."""
        # Test basic condition
        groovy = generator._convert_condition_to_groovy("$.status != 'finished'", 100)
        assert "__groovy" in groovy
        assert "status" in groovy
        assert "finished" in groovy
        assert "100" in groovy
        assert "vars.get" in groovy

        # Test equals condition
        groovy2 = generator._convert_condition_to_groovy("$.done == 'true'", 50)
        assert "__groovy" in groovy2
        assert "done" in groovy2
        assert "50" in groovy2

    def test_create_condition_extractor(self, generator):
        """Test condition extractor creation."""
        extractor = generator._create_condition_extractor("$.status != 'done'")
        assert extractor is not None
        assert extractor.tag == "JSONPostProcessor"

        ref_prop = extractor.find(".//stringProp[@name='JSONPostProcessor.referenceNames']")
        assert ref_prop.text == "status"

        path_prop = extractor.find(".//stringProp[@name='JSONPostProcessor.jsonPathExprs']")
        assert path_prop.text == "$.status"

    def test_create_condition_extractor_no_match(self, generator):
        """Test condition extractor returns None for invalid condition."""
        extractor = generator._create_condition_extractor("invalid condition without jsonpath")
        assert extractor is None
