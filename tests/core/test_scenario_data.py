"""Unit tests for scenario data structures."""

import pytest

from jmeter_gen.core.scenario_data import (
    AssertConfig,
    CaptureConfig,
    CorrelationMapping,
    CorrelationResult,
    ParsedScenario,
    ResolvedPath,
    ScenarioSettings,
    ScenarioStep,
)

# Mark all tests in this module as v2 tests
pytestmark = pytest.mark.v2


class TestScenarioSettings:
    """Tests for ScenarioSettings dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        settings = ScenarioSettings()
        assert settings.threads == 1
        assert settings.rampup == 0
        assert settings.duration is None
        assert settings.base_url is None

    def test_custom_values(self):
        """Test custom values are stored correctly."""
        settings = ScenarioSettings(
            threads=10,
            rampup=5,
            duration=60,
            base_url="http://localhost:8080",
        )
        assert settings.threads == 10
        assert settings.rampup == 5
        assert settings.duration == 60
        assert settings.base_url == "http://localhost:8080"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        settings = ScenarioSettings(
            threads=5, rampup=10, loops=3, duration=120, base_url="http://example.com"
        )
        result = settings.to_dict()
        assert result == {
            "threads": 5,
            "rampup": 10,
            "loops": 3,
            "duration": 120,
            "base_url": "http://example.com",
        }

    def test_to_dict_with_none_values(self):
        """Test to_dict with None values."""
        settings = ScenarioSettings()
        result = settings.to_dict()
        assert result["loops"] is None
        assert result["duration"] is None
        assert result["base_url"] is None


class TestCaptureConfig:
    """Tests for CaptureConfig dataclass."""

    def test_simple_capture(self):
        """Test simple capture with auto-detected path."""
        capture = CaptureConfig(variable_name="userId")
        assert capture.variable_name == "userId"
        assert capture.source_field is None
        assert capture.jsonpath is None
        assert capture.match == "first"

    def test_mapped_capture(self):
        """Test mapped capture with different field name."""
        capture = CaptureConfig(variable_name="totalAmount", source_field="total")
        assert capture.variable_name == "totalAmount"
        assert capture.source_field == "total"

    def test_explicit_jsonpath_capture(self):
        """Test explicit JSONPath capture."""
        capture = CaptureConfig(
            variable_name="firstItemId",
            jsonpath="$.items[0].id",
        )
        assert capture.jsonpath == "$.items[0].id"

    def test_match_all(self):
        """Test capture with match='all'."""
        capture = CaptureConfig(
            variable_name="allIds",
            jsonpath="$.items[*].id",
            match="all",
        )
        assert capture.match == "all"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        capture = CaptureConfig(
            variable_name="userId",
            source_field="id",
            jsonpath="$.id",
            match="first",
        )
        result = capture.to_dict()
        assert result == {
            "variable_name": "userId",
            "source_field": "id",
            "jsonpath": "$.id",
            "match": "first",
        }


class TestAssertConfig:
    """Tests for AssertConfig dataclass."""

    def test_status_only(self):
        """Test assertion with status only."""
        assertion = AssertConfig(status=200)
        assert assertion.status == 200
        assert assertion.body == {}
        assert assertion.headers == {}

    def test_with_body_assertions(self):
        """Test assertion with body validations."""
        assertion = AssertConfig(
            status=201, body={"email": "test@example.com", "name": "Test"}
        )
        assert assertion.status == 201
        assert assertion.body == {"email": "test@example.com", "name": "Test"}

    def test_to_dict(self):
        """Test conversion to dictionary."""
        assertion = AssertConfig(status=200, body={"id": 1})
        result = assertion.to_dict()
        assert result == {"status": 200, "body": {"id": 1}, "headers": {}, "body_contains": []}


class TestScenarioStep:
    """Tests for ScenarioStep dataclass."""

    def test_minimal_step(self):
        """Test minimal step with required fields only."""
        step = ScenarioStep(
            name="Get Users",
            endpoint="GET /users",
            endpoint_type="method_path",
        )
        assert step.name == "Get Users"
        assert step.endpoint == "GET /users"
        assert step.endpoint_type == "method_path"
        assert step.captures == []

    def test_full_step(self):
        """Test step with all fields populated."""
        captures = [CaptureConfig(variable_name="userId", source_field="id")]
        assertions = AssertConfig(status=201, body={"success": True})

        step = ScenarioStep(
            name="Create User",
            endpoint="createUser",
            endpoint_type="operation_id",
            headers={"Content-Type": "application/json"},
            params={"version": "v1"},
            payload={"email": "test@example.com"},
            captures=captures,
            assertions=assertions,
        )

        assert step.headers == {"Content-Type": "application/json"}
        assert step.params == {"version": "v1"}
        assert step.payload == {"email": "test@example.com"}
        assert len(step.captures) == 1
        assert step.assertions.status == 201

    def test_method_path_type(self):
        """Test step with method_path endpoint type."""
        step = ScenarioStep(
            name="Get User",
            endpoint="GET /users/{userId}",
            endpoint_type="method_path",
            method="GET",
            path="/users/{userId}",
        )
        assert step.endpoint_type == "method_path"
        assert step.method == "GET"
        assert step.path == "/users/{userId}"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        step = ScenarioStep(
            name="Test Step",
            endpoint="GET /test",
            endpoint_type="method_path",
            headers={"X-Header": "value"},
            assertions=AssertConfig(status=200),
        )
        result = step.to_dict()
        assert result["name"] == "Test Step"
        assert result["endpoint"] == "GET /test"
        assert result["endpoint_type"] == "method_path"
        assert result["headers"] == {"X-Header": "value"}
        assert result["captures"] == []


class TestParsedScenario:
    """Tests for ParsedScenario dataclass."""

    def test_full_scenario(self):
        """Test fully populated scenario."""
        settings = ScenarioSettings(threads=5, rampup=10)
        steps = [
            ScenarioStep(
                name="Step 1",
                endpoint="GET /test",
                endpoint_type="method_path",
            )
        ]

        scenario = ParsedScenario(
            name="Test Scenario",
            description="A test scenario",
            settings=settings,
            variables={"api_key": "secret"},
            steps=steps,
        )

        assert scenario.name == "Test Scenario"
        assert scenario.description == "A test scenario"
        assert scenario.settings.threads == 5
        assert scenario.variables == {"api_key": "secret"}
        assert len(scenario.steps) == 1

    def test_to_dict(self):
        """Test conversion to dictionary."""
        scenario = ParsedScenario(
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[],
        )
        result = scenario.to_dict()
        assert result["name"] == "Test"
        assert "settings" in result
        assert "steps" in result


class TestCorrelationMapping:
    """Tests for CorrelationMapping dataclass."""

    def test_correlation_mapping(self):
        """Test correlation mapping creation."""
        mapping = CorrelationMapping(
            variable_name="userId",
            jsonpath="$.id",
            source_step=1,
            source_endpoint="createUser",
            confidence=0.9,
            match_type="exact",
        )
        assert mapping.variable_name == "userId"
        assert mapping.jsonpath == "$.id"
        assert mapping.confidence == 0.9
        assert mapping.source_step == 1
        assert mapping.source_endpoint == "createUser"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        mapping = CorrelationMapping(
            variable_name="orderId",
            jsonpath="$.order.id",
            source_step=2,
            source_endpoint="createOrder",
            confidence=0.85,
            match_type="nested",
        )
        result = mapping.to_dict()
        assert result["variable_name"] == "orderId"
        assert result["jsonpath"] == "$.order.id"
        assert result["source_step"] == 2
        assert result["confidence"] == 0.85


class TestCorrelationResult:
    """Tests for CorrelationResult dataclass."""

    def test_correlation_result(self):
        """Test correlation result creation."""
        mappings = [
            CorrelationMapping(
                variable_name="id",
                jsonpath="$.id",
                source_step=1,
                source_endpoint="createUser",
                confidence=1.0,
                match_type="exact",
            )
        ]
        result = CorrelationResult(mappings=mappings)
        assert len(result.mappings) == 1
        assert result.warnings == []
        assert result.errors == []

    def test_has_errors(self):
        """Test has_errors property."""
        result = CorrelationResult(errors=["Error 1"])
        assert result.has_errors is True

        result2 = CorrelationResult()
        assert result2.has_errors is False

    def test_has_warnings(self):
        """Test has_warnings property."""
        result = CorrelationResult(warnings=["Warning 1"])
        assert result.has_warnings is True

        result2 = CorrelationResult()
        assert result2.has_warnings is False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = CorrelationResult(
            mappings=[],
            warnings=["warn"],
            errors=["err"],
        )
        result_dict = result.to_dict()
        assert result_dict["mappings"] == []
        assert result_dict["warnings"] == ["warn"]
        assert result_dict["errors"] == ["err"]
        assert result_dict["has_errors"] is True
        assert result_dict["has_warnings"] is True


class TestResolvedPath:
    """Tests for ResolvedPath dataclass."""

    def test_resolved_path(self):
        """Test resolved path creation."""
        resolved = ResolvedPath(
            full_path="/users/{id}",
            method="GET",
            match_type="exact",
        )
        assert resolved.full_path == "/users/{id}"
        assert resolved.method == "GET"
        assert resolved.match_type == "exact"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        resolved = ResolvedPath(
            full_path="/test",
            method="POST",
            match_type="suffix",
            candidates=["/api/test", "/v2/test"],
        )
        result = resolved.to_dict()
        assert result == {
            "full_path": "/test",
            "method": "POST",
            "match_type": "suffix",
            "candidates": ["/api/test", "/v2/test"],
        }
