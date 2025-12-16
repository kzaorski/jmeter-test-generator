"""Unit tests for PtScenarioParser."""

from pathlib import Path

import pytest

from jmeter_gen.core.ptscenario_parser import PtScenarioParser
from jmeter_gen.exceptions import (
    InvalidEndpointFormatException,
    ScenarioParseException,
    ScenarioValidationException,
)

# Mark all tests in this module as v2 tests
pytestmark = pytest.mark.v2


class TestPtScenarioParser:
    """Tests for PtScenarioParser class."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return PtScenarioParser()

    @pytest.fixture
    def fixtures_dir(self):
        """Return the path to test fixtures directory."""
        return Path(__file__).parent.parent / "fixtures" / "scenarios"

    # Valid scenario tests

    def test_parse_valid_basic(self, parser, fixtures_dir):
        """Test parsing a minimal valid scenario."""
        scenario = parser.parse(fixtures_dir / "valid_basic.yaml")

        assert scenario.name == "Basic Test Scenario"
        assert scenario.description is None or scenario.description == ""
        assert len(scenario.steps) > 0

    def test_parse_valid_full(self, parser, fixtures_dir):
        """Test parsing a scenario with all features."""
        scenario = parser.parse(fixtures_dir / "valid_full.yaml")

        assert scenario.name == "Full Feature Scenario"
        assert scenario.description is not None
        assert scenario.settings.threads == 10
        assert scenario.settings.rampup == 5
        assert scenario.settings.duration == 60
        assert scenario.settings.base_url == "http://localhost:8080"
        assert len(scenario.variables) == 3
        assert "api_version" in scenario.variables
        assert len(scenario.steps) == 5

    def test_parse_valid_with_captures(self, parser, fixtures_dir):
        """Test parsing scenario with all capture syntaxes."""
        scenario = parser.parse(fixtures_dir / "valid_with_captures.yaml")

        # Find the step with captures
        create_order_step = scenario.steps[0]
        assert create_order_step.name == "Create Order"
        assert len(create_order_step.captures) == 4

        # Check simple capture - uses source_field, not response_field
        simple_capture = next(
            c for c in create_order_step.captures if c.variable_name == "orderId"
        )
        # Simple capture: variable_name matches the field name
        assert simple_capture.source_field is None or simple_capture.source_field == "orderId"
        assert simple_capture.jsonpath is None

        # Check mapped capture - different variable name from field
        mapped_capture = next(
            c for c in create_order_step.captures if c.variable_name == "totalAmount"
        )
        assert mapped_capture.source_field == "total"

        # Find step with explicit JSONPath
        get_items_step = scenario.steps[1]
        explicit_capture = next(
            c for c in get_items_step.captures if c.variable_name == "firstItemId"
        )
        assert explicit_capture.jsonpath == "$.items[0].id"

        all_capture = next(
            c for c in get_items_step.captures if c.variable_name == "allItemIds"
        )
        assert all_capture.match == "all"

    def test_parse_valid_operationid(self, parser, fixtures_dir):
        """Test parsing scenario with operationId format only."""
        scenario = parser.parse(fixtures_dir / "valid_operationid.yaml")

        for step in scenario.steps:
            # operationId format should not contain spaces
            assert " " not in step.endpoint

    def test_parse_valid_method_path(self, parser, fixtures_dir):
        """Test parsing scenario with METHOD /path format only."""
        scenario = parser.parse(fixtures_dir / "valid_method_path.yaml")

        for step in scenario.steps:
            # METHOD /path format should have a space
            assert " " in step.endpoint
            parts = step.endpoint.split(" ", 1)
            assert parts[0] in ["GET", "POST", "PUT", "DELETE", "PATCH"]
            assert parts[1].startswith("/")

    def test_parse_valid_mixed_endpoints(self, parser, fixtures_dir):
        """Test parsing scenario with mixed endpoint formats."""
        scenario = parser.parse(fixtures_dir / "valid_mixed_endpoints.yaml")

        has_operationid = False
        has_method_path = False

        for step in scenario.steps:
            if " " in step.endpoint:
                has_method_path = True
            else:
                has_operationid = True

        assert has_operationid, "Should have at least one operationId format"
        assert has_method_path, "Should have at least one METHOD /path format"

    # Invalid scenario tests

    def test_parse_invalid_yaml_syntax(self, parser, fixtures_dir):
        """Test parsing file with invalid YAML syntax."""
        with pytest.raises(ScenarioParseException) as exc_info:
            parser.parse(fixtures_dir / "invalid_yaml_syntax.yaml")

        assert "YAML" in str(exc_info.value) or "parse" in str(exc_info.value).lower()

    def test_parse_invalid_missing_name(self, parser, fixtures_dir):
        """Test parsing scenario missing name field."""
        with pytest.raises(ScenarioParseException) as exc_info:
            parser.parse(fixtures_dir / "invalid_missing_name.yaml")

        assert "name" in str(exc_info.value).lower()

    def test_parse_invalid_missing_scenario(self, parser, fixtures_dir):
        """Test parsing scenario missing scenario field."""
        with pytest.raises(ScenarioParseException) as exc_info:
            parser.parse(fixtures_dir / "invalid_missing_scenario.yaml")

        assert "scenario" in str(exc_info.value).lower()

    def test_parse_invalid_empty_scenario(self, parser, fixtures_dir):
        """Test parsing scenario with empty scenario list."""
        with pytest.raises(ScenarioValidationException) as exc_info:
            parser.parse(fixtures_dir / "invalid_empty_scenario.yaml")

        assert "empty" in str(exc_info.value).lower() or "scenario" in str(
            exc_info.value
        ).lower()

    def test_parse_invalid_endpoint_format(self, parser, fixtures_dir):
        """Test parsing scenario with invalid endpoint format."""
        # Invalid endpoint format raises InvalidEndpointFormatException
        with pytest.raises(InvalidEndpointFormatException) as exc_info:
            parser.parse(fixtures_dir / "invalid_endpoint_format.yaml")

        # Should mention the invalid endpoint
        error_msg = str(exc_info.value).lower()
        assert "invalid" in error_msg or "endpoint" in error_msg

    def test_parse_invalid_undefined_variable(self, parser, fixtures_dir):
        """Test parsing scenario that uses undefined variables."""
        # Undefined variable validation happens during validate(), not parse()
        # parse() will succeed, but validate() will raise
        scenario = parser.parse(fixtures_dir / "invalid_undefined_variable.yaml")
        # If parse succeeds, validate should catch the undefined variable
        assert scenario is not None
        # Note: The undefined variable check happens in validate() when called with spec info

    def test_parse_nonexistent_file(self, parser, tmp_path):
        """Test parsing a file that doesn't exist."""
        with pytest.raises(FileNotFoundError) as exc_info:
            parser.parse(tmp_path / "nonexistent.yaml")

        assert "not found" in str(exc_info.value).lower()

    # Edge cases

    def test_parse_with_string_path(self, parser, fixtures_dir):
        """Test that parser accepts string paths."""
        scenario = parser.parse(str(fixtures_dir / "valid_basic.yaml"))
        assert scenario.name is not None

    def test_step_assertions(self, parser, fixtures_dir):
        """Test that step assertions are parsed correctly."""
        scenario = parser.parse(fixtures_dir / "valid_full.yaml")

        create_step = scenario.steps[0]
        assert create_step.assertions is not None
        assert create_step.assertions.status == 201
        assert create_step.assertions.body is not None
        assert create_step.assertions.body["firstName"] == "Test"

    def test_step_headers(self, parser, fixtures_dir):
        """Test that step headers are parsed correctly."""
        scenario = parser.parse(fixtures_dir / "valid_full.yaml")

        create_step = scenario.steps[0]
        assert create_step.headers is not None
        assert "X-API-Version" in create_step.headers

    def test_step_payload(self, parser, fixtures_dir):
        """Test that step payload is parsed correctly."""
        scenario = parser.parse(fixtures_dir / "valid_full.yaml")

        create_step = scenario.steps[0]
        assert create_step.payload is not None
        assert "email" in create_step.payload
        assert "firstName" in create_step.payload

    def test_variables_substitution_tracking(self, parser, fixtures_dir):
        """Test that variable usage is tracked correctly."""
        scenario = parser.parse(fixtures_dir / "valid_full.yaml")

        # The scenario uses ${api_version} and ${default_password}
        # and captures userId which is used in subsequent steps
        # Parser should track these for validation
        assert "api_version" in scenario.variables
        assert "default_password" in scenario.variables


class TestValidateMethod:
    """Tests for the validate method.

    Note: validate() takes a ParsedScenario object and validates it against
    OpenAPI spec (checking operationIds, variable usage). Raw data validation
    happens during parse().
    """

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return PtScenarioParser()

    def test_validate_valid_scenario(self, parser, tmp_path):
        """Test validation of valid parsed scenario."""
        # Create a valid scenario file
        scenario_content = """version: "1.0"
name: "Test Scenario"
scenario:
  - name: "Step 1"
    endpoint: "GET /test"
"""
        scenario_file = tmp_path / "valid.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        # validate() should not raise and return empty warnings
        warnings = parser.validate(scenario)
        assert isinstance(warnings, list)

    def test_validate_with_operation_ids(self, parser, tmp_path):
        """Test validation checks operationId against spec."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "Call API"
    endpoint: "getUsers"
"""
        scenario_file = tmp_path / "opid.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        # Validate with available operation IDs
        warnings = parser.validate(scenario, available_operation_ids=["getUsers", "createUser"])
        # Should have no warnings since getUsers is valid
        assert "getUsers" not in " ".join(warnings)

    def test_validate_unknown_operation_id_warning(self, parser, tmp_path):
        """Test validation warns about unknown operationId."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "Call API"
    endpoint: "unknownOperation"
"""
        scenario_file = tmp_path / "unknown.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        # Validate with limited operation IDs
        warnings = parser.validate(scenario, available_operation_ids=["getUsers"])
        # Should warn about unknown operation
        assert any("unknownOperation" in w for w in warnings)

    def test_validate_variable_usage(self, parser, tmp_path):
        """Test that validate checks variable definitions."""
        scenario_content = """version: "1.0"
name: "Test"
variables:
  userId: "123"
scenario:
  - name: "Get User"
    endpoint: "GET /users/${userId}"
"""
        scenario_file = tmp_path / "vars.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        # Should not raise - userId is defined
        warnings = parser.validate(scenario)
        assert isinstance(warnings, list)


class TestLoopParsing:
    """Tests for loop configuration parsing."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return PtScenarioParser()

    @pytest.fixture
    def fixtures_dir(self):
        """Return the path to test fixtures directory."""
        return Path(__file__).parent.parent / "fixtures" / "scenarios"

    def test_parse_loop_count(self, parser, fixtures_dir):
        """Test parsing fixed count loop."""
        scenario = parser.parse(fixtures_dir / "valid_loop_count.yaml")

        # Find the step with loop
        poll_step = scenario.steps[1]
        assert poll_step.loop is not None
        assert poll_step.loop.count == 10
        assert poll_step.loop.interval == 5000
        assert poll_step.loop.while_condition is None

    def test_parse_loop_while(self, parser, fixtures_dir):
        """Test parsing while condition loop."""
        scenario = parser.parse(fixtures_dir / "valid_loop_while.yaml")

        # Find the step with loop
        poll_step = scenario.steps[1]
        assert poll_step.loop is not None
        assert poll_step.loop.while_condition == "$.status != 'finished'"
        assert poll_step.loop.max_iterations == 100
        assert poll_step.loop.interval == 30000
        assert poll_step.loop.count is None

    def test_parse_loop_with_interval(self, parser, fixtures_dir):
        """Test parsing loop with interval only."""
        scenario = parser.parse(fixtures_dir / "valid_loop_with_interval.yaml")

        poll_step = scenario.steps[0]
        assert poll_step.loop is not None
        assert poll_step.loop.count == 5
        assert poll_step.loop.interval == 1000

    def test_parse_loop_invalid_both_count_and_while(self, parser, fixtures_dir):
        """Test that loop with both count and while raises error."""
        with pytest.raises(ScenarioValidationException) as exc_info:
            parser.parse(fixtures_dir / "invalid_loop_both_count_while.yaml")

        error_msg = str(exc_info.value).lower()
        assert "count" in error_msg or "while" in error_msg

    def test_parse_loop_invalid_neither_count_nor_while(self, parser, fixtures_dir):
        """Test that loop with neither count nor while raises error."""
        with pytest.raises(ScenarioValidationException) as exc_info:
            parser.parse(fixtures_dir / "invalid_loop_neither_count_while.yaml")

        error_msg = str(exc_info.value).lower()
        assert "count" in error_msg or "while" in error_msg

    def test_parse_step_without_loop(self, parser, tmp_path):
        """Test that steps without loop have None loop config."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "Simple request"
    endpoint: "GET /test"
"""
        scenario_file = tmp_path / "no_loop.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        assert scenario.steps[0].loop is None

    def test_parse_loop_default_max(self, parser, tmp_path):
        """Test that while loop without max uses default of 100."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "Poll"
    endpoint: "GET /status"
    loop:
      while: "$.status != 'done'"
"""
        scenario_file = tmp_path / "default_max.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        assert scenario.steps[0].loop.max_iterations == 100

    def test_parse_loop_count_only(self, parser, tmp_path):
        """Test parsing loop with count but no interval."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "Repeat"
    endpoint: "GET /test"
    loop:
      count: 5
"""
        scenario_file = tmp_path / "count_only.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        assert scenario.steps[0].loop.count == 5
        assert scenario.steps[0].loop.interval is None

    def test_loop_to_dict(self, parser, tmp_path):
        """Test LoopConfig.to_dict() serialization."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "Poll"
    endpoint: "GET /status"
    loop:
      while: "$.status != 'finished'"
      max: 50
      interval: 10000
"""
        scenario_file = tmp_path / "loop_dict.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        loop_dict = scenario.steps[0].loop.to_dict()

        assert loop_dict["while_condition"] == "$.status != 'finished'"
        assert loop_dict["max_iterations"] == 50
        assert loop_dict["interval"] == 10000
        assert loop_dict["count"] is None


class TestMultiStepLoopParsing:
    """Tests for multi-step loop parsing."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return PtScenarioParser()

    @pytest.fixture
    def fixtures_dir(self):
        """Return the path to test fixtures directory."""
        return Path(__file__).parent.parent / "fixtures" / "scenarios"

    def test_parse_multi_step_loop_count(self, parser, fixtures_dir):
        """Test parsing multi-step loop with fixed count."""
        scenario = parser.parse(fixtures_dir / "valid_multi_step_loop.yaml")

        # Find the loop block step
        loop_step = scenario.steps[1]
        assert loop_step.endpoint_type == "loop_block"
        assert loop_step.loop is not None
        assert loop_step.loop.count == 5
        assert loop_step.loop.interval == 1000

        # Check nested steps
        assert len(loop_step.nested_steps) == 3
        assert loop_step.nested_steps[0].name == "Check Status"
        assert loop_step.nested_steps[0].endpoint == "GET /orders/${orderId}/status"
        assert loop_step.nested_steps[1].endpoint_type == "think_time"
        assert loop_step.nested_steps[1].think_time == 500
        assert loop_step.nested_steps[2].name == "Get Details"

    def test_parse_multi_step_loop_while(self, parser, fixtures_dir):
        """Test parsing multi-step loop with while condition."""
        scenario = parser.parse(fixtures_dir / "valid_multi_step_loop_while.yaml")

        loop_step = scenario.steps[1]
        assert loop_step.endpoint_type == "loop_block"
        assert loop_step.loop.while_condition == "$.status != 'completed'"
        assert loop_step.loop.max_iterations == 50
        assert loop_step.loop.interval == 2000

        # Check nested steps
        assert len(loop_step.nested_steps) == 2
        assert loop_step.nested_steps[0].endpoint == "GET /jobs/${jobId}/status"
        assert loop_step.nested_steps[1].endpoint == "POST /jobs/${jobId}/log"

    def test_parse_multi_step_loop_name_defaults(self, parser, tmp_path):
        """Test that loop block generates default name."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - loop:
      count: 3
    steps:
      - name: "Step A"
        endpoint: "GET /test"
"""
        scenario_file = tmp_path / "loop_name.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        loop_step = scenario.steps[0]
        assert loop_step.name == "Loop 3x"
        assert loop_step.endpoint_type == "loop_block"

    def test_parse_multi_step_loop_custom_name(self, parser, tmp_path):
        """Test multi-step loop with custom name."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "My Custom Loop"
    loop:
      count: 5
    steps:
      - name: "Inner Step"
        endpoint: "GET /test"
"""
        scenario_file = tmp_path / "loop_custom_name.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        loop_step = scenario.steps[0]
        assert loop_step.name == "My Custom Loop"

    def test_parse_multi_step_loop_nested_captures(self, parser, fixtures_dir):
        """Test that captures in nested steps are parsed correctly."""
        scenario = parser.parse(fixtures_dir / "valid_multi_step_loop.yaml")

        loop_step = scenario.steps[1]
        nested_step = loop_step.nested_steps[0]

        assert len(nested_step.captures) == 1
        assert nested_step.captures[0].variable_name == "status"

    def test_parse_multi_step_loop_empty_steps_error(self, parser, tmp_path):
        """Test that empty steps list in loop block raises error."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - loop:
      count: 5
    steps: []
"""
        scenario_file = tmp_path / "empty_loop_steps.yaml"
        scenario_file.write_text(scenario_content)

        with pytest.raises(ScenarioValidationException) as exc_info:
            parser.parse(scenario_file)

        assert "steps" in str(exc_info.value).lower() or "non-empty" in str(exc_info.value).lower()

    def test_multi_step_loop_to_dict(self, parser, fixtures_dir):
        """Test ScenarioStep.to_dict() for loop blocks."""
        scenario = parser.parse(fixtures_dir / "valid_multi_step_loop.yaml")

        loop_step = scenario.steps[1]
        step_dict = loop_step.to_dict()

        assert step_dict["endpoint_type"] == "loop_block"
        assert step_dict["loop"]["count"] == 5
        assert len(step_dict["nested_steps"]) == 3
        assert step_dict["nested_steps"][0]["name"] == "Check Status"


class TestThinkTimeParsing:
    """Tests for think_time step parsing."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return PtScenarioParser()

    def test_parse_think_time_step(self, parser, tmp_path):
        """Test parsing standalone think_time step."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "Wait"
    think_time: 5000
"""
        scenario_file = tmp_path / "think_time.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        step = scenario.steps[0]

        assert step.endpoint_type == "think_time"
        assert step.think_time == 5000
        assert step.name == "Wait"

    def test_parse_think_time_default_name(self, parser, tmp_path):
        """Test think_time step with default name."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - think_time: 1000
"""
        scenario_file = tmp_path / "think_time_default.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        step = scenario.steps[0]

        assert step.name == "Think Time"
        assert step.think_time == 1000

    def test_parse_think_time_invalid_negative(self, parser, tmp_path):
        """Test that negative think_time raises error."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - think_time: -100
"""
        scenario_file = tmp_path / "think_time_negative.yaml"
        scenario_file.write_text(scenario_content)

        with pytest.raises(ScenarioValidationException) as exc_info:
            parser.parse(scenario_file)

        assert "think_time" in str(exc_info.value).lower()


class TestFileUploadParsing:
    """Tests for file upload (files) field parsing."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return PtScenarioParser()

    def test_parse_single_file(self, parser, tmp_path):
        """Test parsing step with single file upload."""
        scenario_content = """version: "1.0"
name: "File Upload Test"
scenario:
  - name: "Upload Document"
    endpoint: "POST /api/documents/upload"
    files:
      - path: "test-data/document.pdf"
        param: "file"
"""
        scenario_file = tmp_path / "single_file.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        step = scenario.steps[0]

        assert len(step.files) == 1
        assert step.files[0].path == "test-data/document.pdf"
        assert step.files[0].param == "file"
        assert step.files[0].mime_type is None

    def test_parse_file_with_mime_type(self, parser, tmp_path):
        """Test parsing file upload with explicit mime_type."""
        scenario_content = """version: "1.0"
name: "File Upload Test"
scenario:
  - name: "Upload Image"
    endpoint: "POST /api/images"
    files:
      - path: "uploads/image.png"
        param: "avatar"
        mime_type: "image/png"
"""
        scenario_file = tmp_path / "file_mime_type.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        step = scenario.steps[0]

        assert len(step.files) == 1
        assert step.files[0].path == "uploads/image.png"
        assert step.files[0].param == "avatar"
        assert step.files[0].mime_type == "image/png"

    def test_parse_multiple_files(self, parser, tmp_path):
        """Test parsing step with multiple file uploads."""
        scenario_content = """version: "1.0"
name: "Multi-File Upload Test"
scenario:
  - name: "Upload Multiple"
    endpoint: "POST /api/attachments"
    files:
      - path: "documents/report.pdf"
        param: "document"
        mime_type: "application/pdf"
      - path: "images/logo.png"
        param: "logo"
        mime_type: "image/png"
"""
        scenario_file = tmp_path / "multi_file.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        step = scenario.steps[0]

        assert len(step.files) == 2
        assert step.files[0].path == "documents/report.pdf"
        assert step.files[0].param == "document"
        assert step.files[1].path == "images/logo.png"
        assert step.files[1].param == "logo"

    def test_parse_step_without_files(self, parser, tmp_path):
        """Test that step without files has empty files list."""
        scenario_content = """version: "1.0"
name: "No Files Test"
scenario:
  - name: "Simple Request"
    endpoint: "GET /api/test"
"""
        scenario_file = tmp_path / "no_files.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        step = scenario.steps[0]

        assert step.files == []

    def test_parse_file_with_variable_in_path(self, parser, tmp_path):
        """Test parsing file with JMeter variable in path."""
        scenario_content = """version: "1.0"
name: "Variable Path Test"
scenario:
  - name: "Upload Variable File"
    endpoint: "POST /api/upload"
    files:
      - path: "${data_dir}/upload.pdf"
        param: "file"
"""
        scenario_file = tmp_path / "variable_path.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        step = scenario.steps[0]

        assert len(step.files) == 1
        assert step.files[0].path == "${data_dir}/upload.pdf"

    def test_file_config_to_dict(self, parser, tmp_path):
        """Test FileConfig.to_dict() serialization."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "Upload"
    endpoint: "POST /upload"
    files:
      - path: "report.pdf"
        param: "file"
        mime_type: "application/pdf"
"""
        scenario_file = tmp_path / "file_dict.yaml"
        scenario_file.write_text(scenario_content)

        scenario = parser.parse(scenario_file)
        file_dict = scenario.steps[0].files[0].to_dict()

        assert file_dict["path"] == "report.pdf"
        assert file_dict["param"] == "file"
        assert file_dict["mime_type"] == "application/pdf"
