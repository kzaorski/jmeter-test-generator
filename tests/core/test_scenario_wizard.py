"""Unit tests for ScenarioWizard."""

import pytest
from unittest.mock import MagicMock, patch

from jmeter_gen.core.scenario_wizard import (
    ScenarioWizard,
    WizardState,
    EndpointOption,
)


class TestWizardState:
    """Tests for WizardState dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        state = WizardState()
        assert state.name == ""
        assert state.description == ""
        assert state.settings == {}
        assert state.steps == []
        assert state.captured_vars == set()
        assert state.token_vars == set()

    def test_custom_values(self):
        """Test custom values are stored correctly."""
        state = WizardState(
            name="Test",
            description="Desc",
            settings={"threads": 10},
            steps=[{"name": "Step1"}],
            captured_vars={"userId"},
            token_vars={"accessToken"},
        )
        assert state.name == "Test"
        assert state.description == "Desc"
        assert state.settings == {"threads": 10}
        assert state.steps == [{"name": "Step1"}]
        assert state.captured_vars == {"userId"}
        assert state.token_vars == {"accessToken"}


class TestEndpointOption:
    """Tests for EndpointOption dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        opt = EndpointOption(
            display="GET /users",
            method="GET",
            path="/users",
            operation_id="getUsers",
        )
        assert opt.display == "GET /users"
        assert opt.method == "GET"
        assert opt.path == "/users"
        assert opt.operation_id == "getUsers"
        assert opt.uses_vars == []
        assert opt.suggested is False

    def test_with_uses_vars(self):
        """Test with uses_vars set."""
        opt = EndpointOption(
            display="GET /users/{id}",
            method="GET",
            path="/users/{id}",
            operation_id="getUserById",
            uses_vars=["userId"],
            suggested=True,
        )
        assert opt.uses_vars == ["userId"]
        assert opt.suggested is True


class TestScenarioWizard:
    """Tests for ScenarioWizard class."""

    @pytest.fixture
    def mock_parser(self):
        """Create mock OpenAPIParser."""
        parser = MagicMock()
        parser.extract_response_schema.return_value = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "email": {"type": "string"},
            },
        }
        return parser

    @pytest.fixture
    def spec_data(self):
        """Create mock spec data."""
        return {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "method": "POST",
                    "path": "/users",
                    "operationId": "createUser",
                },
                {
                    "method": "GET",
                    "path": "/users/{id}",
                    "operationId": "getUserById",
                },
                {
                    "method": "DELETE",
                    "path": "/users/{id}",
                    "operationId": "deleteUser",
                },
            ],
        }

    @pytest.fixture
    def wizard(self, mock_parser, spec_data):
        """Create ScenarioWizard instance."""
        return ScenarioWizard(mock_parser, spec_data)

    def test_init(self, wizard, mock_parser, spec_data):
        """Test wizard initialization."""
        assert wizard.parser == mock_parser
        assert wizard._spec_data == spec_data
        assert isinstance(wizard.state, WizardState)
        assert wizard._endpoints == []

    def test_detect_variable_usage_no_match(self, wizard):
        """Test variable detection when no variables captured."""
        wizard.state.captured_vars = set()
        result = wizard._detect_variable_usage("/users/{id}")
        assert result == []

    def test_detect_variable_usage_exact_match(self, wizard):
        """Test variable detection with exact match."""
        wizard.state.captured_vars = {"id"}
        result = wizard._detect_variable_usage("/users/{id}")
        assert "id" in result

    def test_detect_variable_usage_suffix_match(self, wizard):
        """Test variable detection with ID suffix match."""
        wizard.state.captured_vars = {"userId"}
        result = wizard._detect_variable_usage("/users/{id}")
        assert "userId" in result

    def test_detect_variable_usage_case_insensitive(self, wizard):
        """Test variable detection is case insensitive."""
        wizard.state.captured_vars = {"userId"}
        result = wizard._detect_variable_usage("/users/{userId}")
        assert "userId" in result

    def test_generate_variable_name_id_field(self, wizard):
        """Test variable name generation for 'id' field."""
        endpoint = {"operationId": "createUser", "path": "/users"}
        result = wizard._generate_variable_name("id", endpoint)
        assert result == "userId"

    def test_generate_variable_name_id_field_from_path(self, wizard):
        """Test variable name generation from path when no operationId."""
        endpoint = {"path": "/orders", "operationId": ""}
        result = wizard._generate_variable_name("id", endpoint)
        assert result == "orderId"

    def test_generate_variable_name_other_field(self, wizard):
        """Test variable name generation for non-id fields."""
        endpoint = {"operationId": "createUser", "path": "/users"}
        result = wizard._generate_variable_name("email", endpoint)
        assert result == "email"

    def test_generate_variable_name_token_field(self, wizard):
        """Test variable name generation for token field."""
        endpoint = {"operationId": "login", "path": "/auth/login"}
        result = wizard._generate_variable_name("accessToken", endpoint)
        assert result == "accessToken"

    def test_validate_variable_name_valid(self, wizard):
        """Test valid variable name validation."""
        valid, sanitized = wizard._validate_variable_name("userId")
        assert valid is True
        assert sanitized == "userId"

    def test_validate_variable_name_with_spaces(self, wizard):
        """Test variable name with spaces."""
        valid, sanitized = wizard._validate_variable_name("user id")
        assert valid is False
        assert sanitized == "userId"

    def test_validate_variable_name_starts_with_digit(self, wizard):
        """Test variable name starting with digit."""
        valid, sanitized = wizard._validate_variable_name("123abc")
        assert valid is False
        assert sanitized == "abc"

    def test_validate_variable_name_with_hyphen(self, wizard):
        """Test variable name with hyphen."""
        valid, sanitized = wizard._validate_variable_name("user-name")
        assert valid is False
        assert sanitized == "userName"

    def test_validate_variable_name_empty(self, wizard):
        """Test empty variable name."""
        valid, sanitized = wizard._validate_variable_name("")
        assert valid is False
        assert sanitized == "variable"

    # Tests for ugly operationId detection
    def test_is_ugly_operation_id_true(self, wizard):
        """Test detection of auto-generated ugly operationId."""
        # Typical FastAPI auto-generated operationId
        assert wizard._is_ugly_operation_id(
            "postserviceagenttestcasesgenapi10graphstatehistory", "POST"
        ) is True

    def test_is_ugly_operation_id_false_short(self, wizard):
        """Test that short operationIds are not considered ugly."""
        assert wizard._is_ugly_operation_id("createUser", "POST") is False

    def test_is_ugly_operation_id_false_camelcase(self, wizard):
        """Test that camelCase operationIds are not considered ugly."""
        assert wizard._is_ugly_operation_id(
            "createUserWithEmailAddress", "POST"
        ) is False

    def test_is_ugly_operation_id_false_with_underscores(self, wizard):
        """Test that operationIds with underscores are not considered ugly."""
        assert wizard._is_ugly_operation_id(
            "create_user_with_email_address", "POST"
        ) is False

    def test_is_ugly_operation_id_false_with_hyphens(self, wizard):
        """Test that operationIds with hyphens are not considered ugly."""
        assert wizard._is_ugly_operation_id(
            "create-user-with-email-address", "POST"
        ) is False

    def test_create_name_from_path_snake_case(self, wizard):
        """Test creating name from path with snake_case."""
        result = wizard._create_name_from_path(
            "/service/agent-testcasesgen/api/1.0/graph_state_history", "POST"
        )
        assert result == "GraphStateHistory"

    def test_create_name_from_path_kebab_case(self, wizard):
        """Test creating name from path with kebab-case."""
        result = wizard._create_name_from_path("/api/v1/health-check", "GET")
        assert result == "HealthCheck"

    def test_create_name_from_path_with_param(self, wizard):
        """Test creating name from path with parameter at end."""
        result = wizard._create_name_from_path("/users/{id}", "GET")
        assert result == "Users"

    def test_create_name_from_path_empty_segments(self, wizard):
        """Test creating name from path with only parameters."""
        result = wizard._create_name_from_path("/{param}", "GET")
        assert result == "GET_request"

    def test_get_readable_display_name_ugly(self, wizard):
        """Test that ugly operationIds are replaced with readable names."""
        result = wizard._get_readable_display_name(
            "postserviceagenttestcasesgenapi10graphstatehistory",
            "/service/agent-testcasesgen/api/1.0/graph_state_history",
            "POST",
        )
        assert result == "GraphStateHistory"

    def test_get_readable_display_name_good(self, wizard):
        """Test that good operationIds are preserved."""
        result = wizard._get_readable_display_name(
            "createUser",
            "/users",
            "POST",
        )
        assert result == "createUser"

    def test_build_endpoint_options_with_ugly_operation_id(self, wizard):
        """Test that endpoint options use readable names for ugly operationIds."""
        wizard._endpoints = [
            {
                "method": "POST",
                "path": "/service/agent-testcasesgen/api/1.0/graph_state_history",
                "operationId": "postserviceagenttestcasesgenapi10graphstatehistory",
            }
        ]
        options = wizard._build_endpoint_options()

        assert len(options) == 1
        # Display should show readable name, not ugly operationId
        assert "GraphStateHistory" in options[0].display
        assert "postserviceagenttestcasesgenapi10graphstatehistory" not in options[0].display
        # But operation_id should preserve original for internal use
        assert options[0].operation_id == "postserviceagenttestcasesgenapi10graphstatehistory"

    def test_build_endpoint_options(self, wizard, spec_data):
        """Test building endpoint options."""
        wizard._endpoints = spec_data["endpoints"]
        options = wizard._build_endpoint_options()

        assert len(options) == 3
        assert options[0].method == "POST"
        assert options[0].path == "/users"
        assert options[0].operation_id == "createUser"

    def test_build_endpoint_options_with_suggestions(self, wizard, spec_data):
        """Test endpoint options with variable suggestions."""
        wizard._endpoints = spec_data["endpoints"]
        wizard.state.captured_vars = {"userId"}

        options = wizard._build_endpoint_options()

        # GET /users/{id} should be suggested
        get_option = next(opt for opt in options if opt.operation_id == "getUserById")
        assert get_option.suggested is True
        assert "userId" in get_option.uses_vars

    def test_get_endpoint_data(self, wizard, spec_data):
        """Test getting endpoint data by method and path."""
        wizard._endpoints = spec_data["endpoints"]

        result = wizard._get_endpoint_data("POST", "/users")
        assert result["operationId"] == "createUser"

    def test_get_endpoint_data_not_found(self, wizard, spec_data):
        """Test getting endpoint data when not found."""
        wizard._endpoints = spec_data["endpoints"]

        result = wizard._get_endpoint_data("PUT", "/nonexistent")
        assert result == {}

    def test_build_scenario_dict(self, wizard):
        """Test building scenario dictionary."""
        wizard.state.name = "Test Scenario"
        wizard.state.description = "Test description"
        wizard.state.settings = {"threads": 10, "rampup": 5}
        wizard.state.steps = [
            {"name": "Step 1", "endpoint": "POST /users"},
            {"name": "Step 2", "endpoint": "GET /users/{id}"},
        ]

        result = wizard._build_scenario_dict()

        assert result["name"] == "Test Scenario"
        assert result["description"] == "Test description"
        assert result["settings"] == {"threads": 10, "rampup": 5}
        assert len(result["scenario"]) == 2

    def test_build_scenario_dict_no_description(self, wizard):
        """Test building scenario dict without description."""
        wizard.state.name = "Test Scenario"
        wizard.state.description = ""
        wizard.state.settings = {}
        wizard.state.steps = [{"name": "Step 1", "endpoint": "POST /users"}]

        result = wizard._build_scenario_dict()

        assert "description" not in result

    def test_to_yaml(self, wizard):
        """Test YAML conversion."""
        scenario = {
            "name": "Test",
            "scenario": [{"name": "Step 1", "endpoint": "POST /users"}],
        }

        yaml_output = wizard._to_yaml(scenario)

        assert "name: Test" in yaml_output
        assert "scenario:" in yaml_output
        assert "endpoint: POST /users" in yaml_output

    def test_save(self, wizard, tmp_path):
        """Test saving scenario to file."""
        scenario = {
            "name": "Test Scenario",
            "scenario": [{"name": "Step 1", "endpoint": "POST /users"}],
        }
        output_path = tmp_path / "test_scenario.yaml"

        wizard.save(scenario, str(output_path))

        assert output_path.exists()
        content = output_path.read_text()
        assert "name: Test Scenario" in content

    def test_suggest_captures_id_field(self, wizard):
        """Test capture suggestions for id field."""
        endpoint = {
            "method": "POST",
            "path": "/users",
            "operationId": "createUser",
        }
        wizard.parser.extract_response_schema.return_value = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "email": {"type": "string"},
            },
        }

        suggestions = wizard._suggest_captures(endpoint)

        # Should suggest 'id' field
        id_suggestion = next(
            (s for s in suggestions if s["field"] == "id"), None
        )
        assert id_suggestion is not None
        assert id_suggestion["variable"] == "userId"
        assert id_suggestion["selected"] is True

    def test_suggest_captures_token_field(self, wizard):
        """Test capture suggestions for token field."""
        endpoint = {
            "method": "POST",
            "path": "/auth/login",
            "operationId": "login",
        }
        wizard.parser.extract_response_schema.return_value = {
            "type": "object",
            "properties": {
                "accessToken": {"type": "string"},
                "refreshToken": {"type": "string"},
            },
        }

        suggestions = wizard._suggest_captures(endpoint)

        # Should suggest token fields
        token_suggestions = [s for s in suggestions if s.get("is_token")]
        assert len(token_suggestions) >= 1

    def test_suggest_captures_no_schema(self, wizard):
        """Test capture suggestions when no schema available."""
        endpoint = {
            "method": "POST",
            "path": "/users",
            "operationId": "createUser",
        }
        wizard.parser.extract_response_schema.return_value = None

        suggestions = wizard._suggest_captures(endpoint)
        assert suggestions == []


class TestScenarioWizardIntegration:
    """Integration tests for ScenarioWizard (with mocked prompts)."""

    @pytest.fixture
    def mock_parser(self):
        """Create mock OpenAPIParser."""
        parser = MagicMock()
        parser.extract_response_schema.return_value = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
            },
        }
        return parser

    @pytest.fixture
    def spec_data(self):
        """Create mock spec data."""
        return {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "method": "POST",
                    "path": "/users",
                    "operationId": "createUser",
                },
            ],
        }

    @patch("questionary.text")
    @patch("questionary.select")
    @patch("questionary.confirm")
    @patch("questionary.checkbox")
    def test_run_basic_flow(
        self,
        mock_checkbox,
        mock_confirm,
        mock_select,
        mock_text,
        mock_parser,
        spec_data,
    ):
        """Test basic wizard flow with mocked prompts."""
        # Configure mock returns
        mock_text.return_value.ask.side_effect = [
            "Test Scenario",  # name
            "Test description",  # description
            "1",  # threads
            "0",  # rampup
            "1",  # loops (for fixed iterations mode)
            "",  # base_url
            "Create User",  # step name
        ]
        mock_select.return_value.ask.side_effect = [
            "Fixed iterations (run N times)",  # test mode
            "Add endpoint",  # first action
            "POST /users (createUser)",  # endpoint selection
            "Done - save scenario",  # second action (done)
        ]
        mock_confirm.return_value.ask.side_effect = [
            False,  # add custom capture?
            True,  # status assertion
        ]
        mock_checkbox.return_value.ask.return_value = []  # no captures

        wizard = ScenarioWizard(mock_parser, spec_data)
        result = wizard.run()

        assert result["name"] == "Test Scenario"
        assert result["description"] == "Test description"
        assert len(result["scenario"]) == 1
        assert result["scenario"][0]["name"] == "Create User"

    @patch("questionary.text")
    @patch("questionary.select")
    @patch("questionary.confirm")
    @patch("questionary.checkbox")
    def test_run_with_think_time(
        self,
        mock_checkbox,
        mock_confirm,
        mock_select,
        mock_text,
        mock_parser,
        spec_data,
    ):
        """Test wizard flow with think time step."""
        mock_text.return_value.ask.side_effect = [
            "Test Scenario",  # name
            "",  # description
            "1",  # threads
            "0",  # rampup
            "1",  # loops (for fixed iterations mode)
            "",  # base_url
            "2000",  # think time ms
        ]
        mock_select.return_value.ask.side_effect = [
            "Fixed iterations (run N times)",  # test mode
            "Add think time",  # first action
            "Done - save scenario",  # second action (done)
        ]

        wizard = ScenarioWizard(mock_parser, spec_data)
        result = wizard.run()

        assert len(result["scenario"]) == 1
        assert result["scenario"][0]["think_time"] == 2000
        assert result["scenario"][0]["name"] == "Think Time"
