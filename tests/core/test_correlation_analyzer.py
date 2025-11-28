"""Unit tests for CorrelationAnalyzer."""

import pytest

from jmeter_gen.core.correlation_analyzer import CorrelationAnalyzer
from jmeter_gen.core.openapi_parser import OpenAPIParser
from jmeter_gen.core.scenario_data import (
    CaptureConfig,
    ParsedScenario,
    ScenarioSettings,
    ScenarioStep,
)

# Mark all tests in this module as v2 tests
pytestmark = pytest.mark.v2


class TestCorrelationAnalyzer:
    """Tests for CorrelationAnalyzer class."""

    @pytest.fixture
    def parser(self, tmp_path):
        """Create a parser instance with a sample spec."""
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
servers:
  - url: http://localhost:8000
paths:
  /users:
    post:
      operationId: createUser
      summary: Create a user
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
                  email:
                    type: string
                  name:
                    type: string
                  created_at:
                    type: string
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
                type: object
                properties:
                  id:
                    type: integer
                  email:
                    type: string
                  name:
                    type: string
"""
        spec_path = tmp_path / "openapi.yaml"
        spec_path.write_text(spec_content)
        parser = OpenAPIParser()
        parser.parse(str(spec_path))
        return parser

    @pytest.fixture
    def analyzer(self, parser):
        """Create an analyzer instance."""
        return CorrelationAnalyzer(parser)

    # Basic correlation tests

    def test_analyze_simple_capture(self, analyzer):
        """Test analyzing a simple capture that matches response field exactly."""
        steps = [
            ScenarioStep(
                name="Create User",
                endpoint="createUser",
                endpoint_type="operation_id",
                captures=[CaptureConfig(variable_name="id")],
            )
        ]
        scenario = ParsedScenario(
            version="1.0",
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=steps,
        )

        result = analyzer.analyze(scenario)

        assert len(result.mappings) == 1
        mapping = result.mappings[0]
        assert mapping.variable_name == "id"
        assert mapping.jsonpath == "$.id"
        assert mapping.confidence == 1.0  # Exact match

    def test_analyze_explicit_jsonpath(self, analyzer):
        """Test analyzing capture with explicit JSONPath (highest confidence)."""
        steps = [
            ScenarioStep(
                name="Create User",
                endpoint="createUser",
                endpoint_type="operation_id",
                captures=[CaptureConfig(variable_name="userId", jsonpath="$.id")],
            )
        ]
        scenario = ParsedScenario(
            version="1.0",
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=steps,
        )

        result = analyzer.analyze(scenario)

        assert len(result.mappings) == 1
        mapping = result.mappings[0]
        assert mapping.jsonpath == "$.id"
        assert mapping.confidence == 1.0  # Explicit path always 1.0

    def test_analyze_mapped_capture(self, analyzer):
        """Test analyzing mapped capture with source_field."""
        steps = [
            ScenarioStep(
                name="Create User",
                endpoint="createUser",
                endpoint_type="operation_id",
                captures=[CaptureConfig(variable_name="userId", source_field="id")],
            )
        ]
        scenario = ParsedScenario(
            version="1.0",
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=steps,
        )

        result = analyzer.analyze(scenario)

        assert len(result.mappings) == 1
        mapping = result.mappings[0]
        assert mapping.variable_name == "userId"
        assert mapping.jsonpath == "$.id"

    def test_analyze_multiple_captures(self, analyzer):
        """Test analyzing multiple captures in one step."""
        steps = [
            ScenarioStep(
                name="Create User",
                endpoint="createUser",
                endpoint_type="operation_id",
                captures=[
                    CaptureConfig(variable_name="id"),
                    CaptureConfig(variable_name="email"),
                    CaptureConfig(variable_name="name"),
                ],
            )
        ]
        scenario = ParsedScenario(
            version="1.0",
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=steps,
        )

        result = analyzer.analyze(scenario)

        assert len(result.mappings) == 3
        paths = [m.jsonpath for m in result.mappings]
        assert "$.id" in paths
        assert "$.email" in paths
        assert "$.name" in paths

    # Edge cases

    def test_analyze_no_captures(self, analyzer):
        """Test analyzing step with no captures."""
        steps = [
            ScenarioStep(
                name="Get User",
                endpoint="getUserById",
                endpoint_type="operation_id",
                captures=[],
            )
        ]
        scenario = ParsedScenario(
            version="1.0",
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=steps,
        )

        result = analyzer.analyze(scenario)

        assert len(result.mappings) == 0
        assert len(result.errors) == 0

    def test_analyze_field_not_in_schema(self, analyzer):
        """Test analyzing capture for field not in response schema."""
        steps = [
            ScenarioStep(
                name="Create User",
                endpoint="createUser",
                endpoint_type="operation_id",
                captures=[CaptureConfig(variable_name="unknownField")],
            )
        ]
        scenario = ParsedScenario(
            version="1.0",
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=steps,
        )

        result = analyzer.analyze(scenario)

        # Should have mapping but with fallback confidence
        assert len(result.mappings) == 1
        assert result.mappings[0].confidence <= 0.5

    def test_analyze_case_insensitive_match(self, analyzer):
        """Test that field matching is case-insensitive."""
        steps = [
            ScenarioStep(
                name="Create User",
                endpoint="createUser",
                endpoint_type="operation_id",
                captures=[CaptureConfig(variable_name="EMAIL")],
            )
        ]
        scenario = ParsedScenario(
            version="1.0",
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=steps,
        )

        result = analyzer.analyze(scenario)

        assert len(result.mappings) == 1
        # Should match 'email' with slightly lower confidence
        assert result.mappings[0].jsonpath == "$.email"
        assert result.mappings[0].confidence >= 0.8

    def test_analyze_id_suffix_match(self, analyzer):
        """Test matching field with Id suffix to 'id' field."""
        steps = [
            ScenarioStep(
                name="Create User",
                endpoint="createUser",
                endpoint_type="operation_id",
                captures=[CaptureConfig(variable_name="userId")],
            )
        ]
        scenario = ParsedScenario(
            version="1.0",
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=steps,
        )

        result = analyzer.analyze(scenario)

        # Should match 'id' with Id suffix matching
        assert len(result.mappings) == 1
        mapping = result.mappings[0]
        assert mapping.jsonpath == "$.id"
        assert mapping.confidence >= 0.7

    def test_analyze_disabled_step_skipped(self, analyzer):
        """Test that disabled steps are skipped."""
        steps = [
            ScenarioStep(
                name="Create User",
                endpoint="createUser",
                endpoint_type="operation_id",
                enabled=False,
                captures=[CaptureConfig(variable_name="id")],
            )
        ]
        scenario = ParsedScenario(
            version="1.0",
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=steps,
        )

        result = analyzer.analyze(scenario)

        assert len(result.mappings) == 0

    def test_analyze_variable_usage_tracking(self, analyzer):
        """Test that variable usage across steps is tracked."""
        steps = [
            ScenarioStep(
                name="Create User",
                endpoint="createUser",
                endpoint_type="operation_id",
                captures=[CaptureConfig(variable_name="id")],
            ),
            ScenarioStep(
                name="Get User",
                endpoint="GET /users/{id}",
                endpoint_type="method_path",
                method="GET",
                path="/users/${id}",
            ),
        ]
        scenario = ParsedScenario(
            version="1.0",
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=steps,
        )

        result = analyzer.analyze(scenario)

        assert len(result.mappings) == 1
        mapping = result.mappings[0]
        # target_steps should include step 2 since it uses ${id}
        assert 2 in mapping.target_steps


class TestCorrelationAnalyzerNested:
    """Tests for nested schema handling."""

    @pytest.fixture
    def parser(self, tmp_path):
        """Create a parser with nested schema spec."""
        spec_content = """openapi: 3.0.0
info:
  title: Orders API
  version: 1.0.0
paths:
  /orders:
    post:
      operationId: createOrder
      responses:
        '201':
          description: Created
          content:
            application/json:
              schema:
                type: object
                properties:
                  orderId:
                    type: string
                  customer:
                    type: object
                    properties:
                      customerId:
                        type: string
                      name:
                        type: string
                  items:
                    type: array
                    items:
                      type: object
                      properties:
                        itemId:
                          type: string
                        productId:
                          type: string
"""
        spec_path = tmp_path / "orders.yaml"
        spec_path.write_text(spec_content)
        parser = OpenAPIParser()
        parser.parse(str(spec_path))
        return parser

    @pytest.fixture
    def analyzer(self, parser):
        """Create an analyzer instance."""
        return CorrelationAnalyzer(parser)

    def test_analyze_nested_capture(self, analyzer):
        """Test analyzing capture from nested object."""
        steps = [
            ScenarioStep(
                name="Create Order",
                endpoint="createOrder",
                endpoint_type="operation_id",
                captures=[CaptureConfig(variable_name="customerId")],
            )
        ]
        scenario = ParsedScenario(
            version="1.0",
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=steps,
        )

        result = analyzer.analyze(scenario)

        assert len(result.mappings) == 1
        mapping = result.mappings[0]
        assert mapping.variable_name == "customerId"
        assert "customer" in mapping.jsonpath

    def test_analyze_array_capture(self, analyzer):
        """Test analyzing capture from array items."""
        steps = [
            ScenarioStep(
                name="Create Order",
                endpoint="createOrder",
                endpoint_type="operation_id",
                captures=[CaptureConfig(variable_name="itemId")],
            )
        ]
        scenario = ParsedScenario(
            version="1.0",
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=steps,
        )

        result = analyzer.analyze(scenario)

        assert len(result.mappings) == 1
        mapping = result.mappings[0]
        assert "items" in mapping.jsonpath
