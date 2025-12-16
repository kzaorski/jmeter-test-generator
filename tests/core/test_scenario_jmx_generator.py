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

    def test_loop_interval_timer_at_loop_level(self, generator, tmp_path):
        """Test that loop interval timer is sibling of TransactionController, not child of sampler."""
        scenario = ParsedScenario(
            name="Timer Placement Test",
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
                    loop=LoopConfig(count=5, interval=10000),
                ),
            ],
        )

        output_path = tmp_path / "timer_placement.jmx"
        result = generator.generate(scenario=scenario, output_path=str(output_path))
        assert result["success"] is True

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find the LoopController's hashTree
        loop_controller = root.find(".//LoopController")
        assert loop_controller is not None

        # Get the hashTree following the LoopController (its children container)
        loop_parent = None
        for elem in root.iter():
            for child in elem:
                if child is loop_controller:
                    loop_parent = elem
                    break

        assert loop_parent is not None, "LoopController parent not found"

        # Find the hashTree after LoopController (loop_hashtree)
        children = list(loop_parent)
        loop_idx = children.index(loop_controller)
        loop_hashtree = children[loop_idx + 1]
        assert loop_hashtree.tag == "hashTree", "Expected hashTree after LoopController"

        # The ConstantTimer should be a direct child of loop_hashtree
        timer = None
        for child in loop_hashtree:
            if child.tag == "ConstantTimer":
                timer = child
                break

        assert timer is not None, "ConstantTimer should be direct child of loop hashTree"

        # Verify the timer is NOT inside the HTTPSampler's hashTree
        sampler = root.find(".//HTTPSamplerProxy")
        assert sampler is not None

        # Find sampler's parent hashTree
        sampler_parent = None
        for elem in root.iter():
            for child in elem:
                if child is sampler:
                    sampler_parent = elem
                    break

        sampler_children = list(sampler_parent)
        sampler_idx = sampler_children.index(sampler)
        sampler_hashtree = sampler_children[sampler_idx + 1]

        # Timer should NOT be in sampler's hashTree
        timer_in_sampler = sampler_hashtree.find("ConstantTimer")
        assert timer_in_sampler is None, "ConstantTimer should NOT be inside sampler hashTree"

    def test_generate_while_loop_adds_extractor(self, generator, tmp_path):
        """Test that while loop adds JSONPostProcessor for condition variable."""
        scenario = ParsedScenario(
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


class TestTransactionControllerGeneration:
    """Tests for Transaction Controller JMX generation."""

    @pytest.fixture
    def parser(self, tmp_path):
        """Create a parser instance."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      operationId: getUsers
      responses:
        '200':
          description: OK
    post:
      operationId: createUser
      responses:
        '201':
          description: Created
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

    def test_create_transaction_controller_default(self, generator):
        """Test Transaction Controller creation with default properties."""
        tc = generator._create_transaction_controller("Test Transaction")

        assert tc.tag == "TransactionController"
        assert tc.get("guiclass") == "TransactionControllerGui"
        assert tc.get("testclass") == "TransactionController"
        assert tc.get("testname") == "Test Transaction"
        assert tc.get("enabled") == "true"

        # Check default properties
        include_timers = tc.find(".//boolProp[@name='TransactionController.includeTimers']")
        assert include_timers is not None
        assert include_timers.text == "false"

        parent_prop = tc.find(".//boolProp[@name='TransactionController.parent']")
        assert parent_prop is not None
        assert parent_prop.text == "true"

    def test_create_transaction_controller_custom_props(self, generator):
        """Test Transaction Controller with custom properties."""
        tc = generator._create_transaction_controller(
            "Custom TC",
            include_timers=True,
            generate_parent_sample=False
        )

        include_timers = tc.find(".//boolProp[@name='TransactionController.includeTimers']")
        assert include_timers.text == "true"

        parent_prop = tc.find(".//boolProp[@name='TransactionController.parent']")
        assert parent_prop.text == "false"

    def test_step_wrapped_in_transaction_controller(self, generator, tmp_path):
        """Test that each step is wrapped in a Transaction Controller."""
        scenario = ParsedScenario(
            name="TC Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Get Users",
                    endpoint="GET /users",
                    endpoint_type="method_path",
                    method="GET",
                    path="/users",
                ),
                ScenarioStep(
                    name="Create User",
                    endpoint="POST /users",
                    endpoint_type="method_path",
                    method="POST",
                    path="/users",
                ),
            ],
        )

        output_path = tmp_path / "tc_test.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True
        assert result["transactions_created"] == 2

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find all Transaction Controllers
        tcs = root.findall(".//TransactionController")
        assert len(tcs) == 2

        # Check naming pattern
        tc_names = [tc.get("testname") for tc in tcs]
        assert "Step 1: Get Users" in tc_names
        assert "Step 2: Create User" in tc_names

    def test_loop_with_transaction_controller(self, generator, tmp_path):
        """Test that Transaction Controller is inside LoopController."""
        scenario = ParsedScenario(
            name="Loop TC Test",
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
                    loop=LoopConfig(count=5),
                ),
            ],
        )

        output_path = tmp_path / "loop_tc.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True
        assert result["loops_created"] == 1
        assert result["transactions_created"] == 1

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Both LoopController and TransactionController should exist
        loop_controllers = root.findall(".//LoopController[@testclass='LoopController']")
        assert len(loop_controllers) >= 1

        tcs = root.findall(".//TransactionController")
        assert len(tcs) == 1

    def test_transaction_controller_naming(self, generator, tmp_path):
        """Test Transaction Controller naming format."""
        scenario = ParsedScenario(
            name="Naming Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="First Step",
                    endpoint="GET /users",
                    endpoint_type="method_path",
                    method="GET",
                    path="/users",
                ),
                ScenarioStep(
                    name="Second Step",
                    endpoint="GET /status",
                    endpoint_type="method_path",
                    method="GET",
                    path="/status",
                ),
                ScenarioStep(
                    name="Third Step",
                    endpoint="POST /users",
                    endpoint_type="method_path",
                    method="POST",
                    path="/users",
                ),
            ],
        )

        output_path = tmp_path / "naming_test.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        tree = ET.parse(output_path)
        root = tree.getroot()

        tcs = root.findall(".//TransactionController")
        tc_names = [tc.get("testname") for tc in tcs]

        # Verify naming pattern: "Step N: {step.name}"
        assert "Step 1: First Step" in tc_names
        assert "Step 2: Second Step" in tc_names
        assert "Step 3: Third Step" in tc_names

    def test_transaction_controller_contains_sampler(self, generator, tmp_path):
        """Test that HTTP sampler is inside Transaction Controller hashTree."""
        scenario = ParsedScenario(
            name="Hierarchy Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Get Users",
                    endpoint="GET /users",
                    endpoint_type="method_path",
                    method="GET",
                    path="/users",
                ),
            ],
        )

        output_path = tmp_path / "hierarchy_test.jmx"

        generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        # Read raw XML to verify hierarchy
        content = output_path.read_text()

        # TransactionController should appear before HTTPSamplerProxy
        tc_pos = content.find("TransactionController")
        sampler_pos = content.find("HTTPSamplerProxy")

        assert tc_pos < sampler_pos, "TransactionController should appear before HTTPSamplerProxy"


class TestCapturedVarsSubstitution:
    """Tests for captured variable substitution in auto-generated payloads."""

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
  /trigger:
    post:
      operationId: triggerProcess
      summary: Trigger a process
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                type: object
                properties:
                  correlationId:
                    type: string
                  processId:
                    type: integer
  /status:
    post:
      operationId: checkStatus
      summary: Check process status
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                correlationId:
                  type: string
                otherField:
                  type: string
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
        """Create a ScenarioJMXGenerator instance."""
        return ScenarioJMXGenerator(parser)

    def test_substitute_captured_vars_simple(self, generator):
        """Test simple field substitution."""
        payload = {"correlationId": "string", "otherField": "value"}
        captured_vars = {"correlationId"}

        result = generator._substitute_captured_vars(payload, captured_vars)

        assert result["correlationId"] == "${correlationId}"
        assert result["otherField"] == "value"

    def test_substitute_captured_vars_nested(self, generator):
        """Test nested object substitution."""
        payload = {
            "data": {
                "correlationId": "string",
                "nested": {
                    "processId": 0,
                    "status": "pending"
                }
            }
        }
        captured_vars = {"correlationId", "processId"}

        result = generator._substitute_captured_vars(payload, captured_vars)

        assert result["data"]["correlationId"] == "${correlationId}"
        assert result["data"]["nested"]["processId"] == "${processId}"
        assert result["data"]["nested"]["status"] == "pending"

    def test_substitute_captured_vars_array(self, generator):
        """Test substitution in arrays of objects."""
        payload = {
            "items": [
                {"id": 1, "correlationId": "string"},
                {"id": 2, "correlationId": "string"}
            ]
        }
        captured_vars = {"correlationId"}

        result = generator._substitute_captured_vars(payload, captured_vars)

        assert result["items"][0]["correlationId"] == "${correlationId}"
        assert result["items"][1]["correlationId"] == "${correlationId}"
        assert result["items"][0]["id"] == 1
        assert result["items"][1]["id"] == 2

    def test_substitute_captured_vars_empty_set(self, generator):
        """Test that no substitution happens with empty captured_vars."""
        payload = {"correlationId": "string", "field": "value"}
        captured_vars: set = set()

        result = generator._substitute_captured_vars(payload, captured_vars)

        assert result["correlationId"] == "string"
        assert result["field"] == "value"

    def test_substitute_captured_vars_no_match(self, generator):
        """Test that no substitution happens when no fields match."""
        payload = {"field1": "value1", "field2": "value2"}
        captured_vars = {"otherVar"}

        result = generator._substitute_captured_vars(payload, captured_vars)

        assert result["field1"] == "value1"
        assert result["field2"] == "value2"

    def test_generate_with_captured_var_substitution(self, generator, tmp_path):
        """Test end-to-end generation with captured variable substitution."""
        scenario = ParsedScenario(
            name="Correlation Test",
            description="Test captured variable substitution",
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Trigger",
                    endpoint="POST /trigger",
                    endpoint_type="method_path",
                    method="POST",
                    path="/trigger",
                    captures=[
                        CaptureConfig(
                            variable_name="correlationId",
                            jsonpath="$.correlationId",
                        )
                    ],
                ),
                ScenarioStep(
                    name="Check Status",
                    endpoint="POST /status",
                    endpoint_type="method_path",
                    method="POST",
                    path="/status",
                    # No payload - should be auto-generated with substitution
                ),
            ],
        )

        # Create correlation result matching the captures
        correlation_result = CorrelationResult(
            mappings=[
                CorrelationMapping(
                    source_step=1,
                    source_endpoint="POST /trigger",
                    variable_name="correlationId",
                    jsonpath="$.correlationId",
                    confidence=1.0,
                    target_steps=[2],
                )
            ],
            warnings=[],
            errors=[],
        )

        output_path = tmp_path / "correlation_test.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
            correlation_result=correlation_result,
        )

        assert result["success"] is True

        # Read the generated JMX and check for substitution
        content = output_path.read_text()

        # The second request (Check Status) should have ${correlationId} in the body
        assert "${correlationId}" in content

    def test_substitute_scenario_variables(self, generator, tmp_path):
        """Test that scenario-level variables are substituted in auto-generated payloads."""
        scenario = ParsedScenario(
            name="Variables Test",
            description="Test scenario variable substitution",
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={
                "correlationId": "test-correlation-123",
                "apiKey": "secret-key",
            },
            steps=[
                ScenarioStep(
                    name="Check Status",
                    endpoint="POST /status",
                    endpoint_type="method_path",
                    method="POST",
                    path="/status",
                    # No payload - should be auto-generated with variable substitution
                ),
            ],
        )

        output_path = tmp_path / "variables_test.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

        # Read the generated JMX and check for substitution
        content = output_path.read_text()

        # correlationId field should be substituted with ${correlationId}
        assert "${correlationId}" in content

    def test_generate_with_body_contains_assertion(self, generator, tmp_path):
        """Test that ResponseAssertion is generated for body_contains."""
        scenario = ParsedScenario(
            name="Body Contains Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Get HTML Page",
                    endpoint="GET /page",
                    endpoint_type="method_path",
                    method="GET",
                    path="/page",
                    assertions=AssertConfig(
                        status=200,
                        body_contains=["Success", "completed"],
                    ),
                )
            ],
        )

        output_path = tmp_path / "body_contains.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True
        assert result["assertions_created"] >= 2  # status + body_contains

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Should have ResponseAssertion for body_contains
        response_assertions = root.findall(".//ResponseAssertion")
        assert len(response_assertions) >= 2  # status + body_contains

        # Find the body contains assertion
        body_contains_assertion = None
        for assertion in response_assertions:
            test_field = assertion.find(".//stringProp[@name='Assertion.test_field']")
            if test_field is not None and test_field.text == "Assertion.response_data":
                body_contains_assertion = assertion
                break

        assert body_contains_assertion is not None, "Body contains assertion not found"

        # Verify test_type is 16 (Substring)
        test_type = body_contains_assertion.find(".//intProp[@name='Assertion.test_type']")
        assert test_type is not None
        assert test_type.text == "16"

        # Verify test strings are present
        coll_prop = body_contains_assertion.find(".//collectionProp[@name='Asserion.test_strings']")
        assert coll_prop is not None
        string_props = coll_prop.findall("stringProp")
        texts = [sp.text for sp in string_props]
        assert "Success" in texts
        assert "completed" in texts

    def test_generate_with_single_body_contains(self, generator, tmp_path):
        """Test body_contains with a single string value."""
        scenario = ParsedScenario(
            name="Single Body Contains Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Get Page",
                    endpoint="GET /page",
                    endpoint_type="method_path",
                    method="GET",
                    path="/page",
                    assertions=AssertConfig(
                        body_contains=["OK"],  # Single element list
                    ),
                )
            ],
        )

        output_path = tmp_path / "single_body_contains.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find body contains assertion
        response_assertions = root.findall(".//ResponseAssertion")
        body_contains_assertion = None
        for assertion in response_assertions:
            test_field = assertion.find(".//stringProp[@name='Assertion.test_field']")
            if test_field is not None and test_field.text == "Assertion.response_data":
                body_contains_assertion = assertion
                break

        assert body_contains_assertion is not None

    def test_generate_standalone_think_time(self, generator, tmp_path):
        """Test that ConstantTimer is generated for standalone think_time step."""
        scenario = ParsedScenario(
            name="Think Time Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Get Data",
                    endpoint="GET /data",
                    endpoint_type="method_path",
                    method="GET",
                    path="/data",
                ),
                ScenarioStep(
                    name="Wait",
                    endpoint="think_time",
                    endpoint_type="think_time",
                    think_time=5000,
                ),
                ScenarioStep(
                    name="Get More Data",
                    endpoint="GET /more",
                    endpoint_type="method_path",
                    method="GET",
                    path="/more",
                ),
            ],
        )

        output_path = tmp_path / "think_time.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Should have ConstantTimer
        timers = root.findall(".//ConstantTimer")
        assert len(timers) >= 1, "ConstantTimer not found"

        # Verify timer delay
        timer = timers[0]
        delay_prop = timer.find(".//stringProp[@name='ConstantTimer.delay']")
        assert delay_prop is not None
        assert delay_prop.text == "5000"

        # Verify timer name
        assert timer.get("testname") == "Wait"

    def test_generate_think_time_in_nested_loop(self, generator, tmp_path):
        """Test that ConstantTimer is generated for think_time in nested loop."""
        scenario = ParsedScenario(
            name="Nested Think Time Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Poll Loop",
                    endpoint="loop_block",
                    endpoint_type="loop_block",
                    loop=LoopConfig(count=3),
                    nested_steps=[
                        ScenarioStep(
                            name="Check Status",
                            endpoint="GET /status",
                            endpoint_type="method_path",
                            method="GET",
                            path="/status",
                        ),
                        ScenarioStep(
                            name="Wait Between Polls",
                            endpoint="think_time",
                            endpoint_type="think_time",
                            think_time=2000,
                        ),
                    ],
                ),
            ],
        )

        output_path = tmp_path / "nested_think_time.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Should have ConstantTimer for the nested think_time
        timers = root.findall(".//ConstantTimer")
        assert len(timers) >= 1, "ConstantTimer not found in nested loop"

        # Find the timer with our specific delay
        found_timer = False
        for timer in timers:
            delay_prop = timer.find(".//stringProp[@name='ConstantTimer.delay']")
            if delay_prop is not None and delay_prop.text == "2000":
                found_timer = True
                assert timer.get("testname") == "Wait Between Polls"
                break

        assert found_timer, "ConstantTimer with 2000ms delay not found"


class TestFileUploadGeneration:
    """Tests for file upload (HTTPFileArgs) JMX generation."""

    @pytest.fixture
    def parser(self, tmp_path):
        """Create a parser instance."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /upload:
    post:
      operationId: uploadFile
      responses:
        '201':
          description: Created
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

    def test_generate_single_file_upload(self, generator, tmp_path):
        """Test JMX generation with single file upload."""
        from jmeter_gen.core.scenario_data import FileConfig

        scenario = ParsedScenario(
            name="File Upload Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Upload Document",
                    endpoint="POST /upload",
                    endpoint_type="method_path",
                    method="POST",
                    path="/upload",
                    files=[
                        FileConfig(
                            path="test-data/document.pdf",
                            param="file",
                            mime_type="application/pdf",
                        )
                    ],
                ),
            ],
        )

        output_path = tmp_path / "single_file.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find HTTPFileArgs
        file_args = root.find(".//elementProp[@name='HTTPsampler.Files']")
        assert file_args is not None, "HTTPsampler.Files element not found"

        # Find file entry
        file_elem = root.find(".//elementProp[@elementType='HTTPFileArg']")
        assert file_elem is not None, "HTTPFileArg element not found"

        # Check file properties
        path_prop = file_elem.find(".//stringProp[@name='File.path']")
        assert path_prop is not None
        assert path_prop.text == "test-data/document.pdf"

        param_prop = file_elem.find(".//stringProp[@name='File.paramname']")
        assert param_prop is not None
        assert param_prop.text == "file"

        mime_prop = file_elem.find(".//stringProp[@name='File.mimetype']")
        assert mime_prop is not None
        assert mime_prop.text == "application/pdf"

    def test_generate_multiple_files(self, generator, tmp_path):
        """Test JMX generation with multiple file uploads."""
        from jmeter_gen.core.scenario_data import FileConfig

        scenario = ParsedScenario(
            name="Multi-File Upload Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Upload Multiple",
                    endpoint="POST /upload",
                    endpoint_type="method_path",
                    method="POST",
                    path="/upload",
                    files=[
                        FileConfig(
                            path="documents/report.pdf",
                            param="document",
                            mime_type="application/pdf",
                        ),
                        FileConfig(
                            path="images/logo.png",
                            param="logo",
                            mime_type="image/png",
                        ),
                    ],
                ),
            ],
        )

        output_path = tmp_path / "multi_file.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find all HTTPFileArg elements
        file_elems = root.findall(".//elementProp[@elementType='HTTPFileArg']")
        assert len(file_elems) == 2

        # Verify both files are present
        paths = []
        for elem in file_elems:
            path_prop = elem.find(".//stringProp[@name='File.path']")
            if path_prop is not None:
                paths.append(path_prop.text)

        assert "documents/report.pdf" in paths
        assert "images/logo.png" in paths

    def test_generate_file_auto_mime_type(self, generator, tmp_path):
        """Test JMX generation auto-detects MIME type from extension."""
        from jmeter_gen.core.scenario_data import FileConfig

        scenario = ParsedScenario(
            name="Auto MIME Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Upload File",
                    endpoint="POST /upload",
                    endpoint_type="method_path",
                    method="POST",
                    path="/upload",
                    files=[
                        FileConfig(
                            path="image.png",
                            param="file",
                            mime_type=None,  # Should auto-detect
                        )
                    ],
                ),
            ],
        )

        output_path = tmp_path / "auto_mime.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

        tree = ET.parse(output_path)
        root = tree.getroot()

        # Find MIME type
        file_elem = root.find(".//elementProp[@elementType='HTTPFileArg']")
        assert file_elem is not None

        mime_prop = file_elem.find(".//stringProp[@name='File.mimetype']")
        assert mime_prop is not None
        assert mime_prop.text == "image/png"

    def test_generate_file_explicit_mime_type_override(self, generator, tmp_path):
        """Test that explicit MIME type overrides auto-detection."""
        from jmeter_gen.core.scenario_data import FileConfig

        scenario = ParsedScenario(
            name="Explicit MIME Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Upload File",
                    endpoint="POST /upload",
                    endpoint_type="method_path",
                    method="POST",
                    path="/upload",
                    files=[
                        FileConfig(
                            path="data.txt",
                            param="file",
                            mime_type="application/octet-stream",  # Override text/plain
                        )
                    ],
                ),
            ],
        )

        output_path = tmp_path / "explicit_mime.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

        tree = ET.parse(output_path)
        root = tree.getroot()

        file_elem = root.find(".//elementProp[@elementType='HTTPFileArg']")
        assert file_elem is not None

        mime_prop = file_elem.find(".//stringProp[@name='File.mimetype']")
        assert mime_prop is not None
        assert mime_prop.text == "application/octet-stream"

    def test_generate_step_without_files(self, generator, tmp_path):
        """Test that step without files doesn't create HTTPFileArgs."""
        scenario = ParsedScenario(
            name="No Files Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={},
            steps=[
                ScenarioStep(
                    name="Simple POST",
                    endpoint="POST /upload",
                    endpoint_type="method_path",
                    method="POST",
                    path="/upload",
                    files=[],  # Empty files list
                ),
            ],
        )

        output_path = tmp_path / "no_files.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

        tree = ET.parse(output_path)
        root = tree.getroot()

        # HTTPsampler.Files should NOT exist
        file_args = root.find(".//elementProp[@name='HTTPsampler.Files']")
        assert file_args is None, "HTTPsampler.Files should not exist for steps without files"

    def test_create_file_args_method(self, generator):
        """Test _create_file_args method directly."""
        from jmeter_gen.core.scenario_data import FileConfig

        files = [
            FileConfig(path="report.pdf", param="file", mime_type="application/pdf"),
            FileConfig(path="data.json", param="data", mime_type="application/json"),
        ]

        file_args = generator._create_file_args(files)

        assert file_args.tag == "elementProp"
        assert file_args.get("name") == "HTTPsampler.Files"
        assert file_args.get("elementType") == "HTTPFileArgs"

        collection = file_args.find("collectionProp[@name='HTTPFileArgs.files']")
        assert collection is not None

        file_elems = collection.findall("elementProp[@elementType='HTTPFileArg']")
        assert len(file_elems) == 2

    def test_file_upload_with_variable_path(self, generator, tmp_path):
        """Test file upload with JMeter variable in path."""
        from jmeter_gen.core.scenario_data import FileConfig

        scenario = ParsedScenario(
            name="Variable Path Test",
            description=None,
            settings=ScenarioSettings(base_url="http://localhost:8000"),
            variables={"data_dir": "/path/to/data"},
            steps=[
                ScenarioStep(
                    name="Upload Variable File",
                    endpoint="POST /upload",
                    endpoint_type="method_path",
                    method="POST",
                    path="/upload",
                    files=[
                        FileConfig(
                            path="${data_dir}/upload.pdf",
                            param="file",
                            mime_type="application/pdf",
                        )
                    ],
                ),
            ],
        )

        output_path = tmp_path / "variable_path.jmx"

        result = generator.generate(
            scenario=scenario,
            output_path=str(output_path),
        )

        assert result["success"] is True

        tree = ET.parse(output_path)
        root = tree.getroot()

        file_elem = root.find(".//elementProp[@elementType='HTTPFileArg']")
        assert file_elem is not None

        path_prop = file_elem.find(".//stringProp[@name='File.path']")
        assert path_prop is not None
        assert path_prop.text == "${data_dir}/upload.pdf"
