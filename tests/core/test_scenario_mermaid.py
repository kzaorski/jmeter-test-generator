"""Tests for scenario_mermaid module."""

import pytest

from jmeter_gen.core.scenario_mermaid import (
    generate_mermaid_diagram,
    generate_text_visualization,
    _escape_mermaid,
    _build_node_label,
)
from jmeter_gen.core.scenario_data import (
    CaptureConfig,
    CorrelationMapping,
    CorrelationResult,
    ParsedScenario,
    ScenarioSettings,
    ScenarioStep,
)


class TestGenerateMermaidDiagram:
    """Tests for generate_mermaid_diagram function."""

    def test_single_step_scenario(self):
        """Test diagram generation with single step."""
        scenario = ParsedScenario(
            name="Simple Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Create User",
                    endpoint="POST /users",
                    endpoint_type="method_path",
                    method="POST",
                    path="/users",
                )
            ],
        )

        diagram = generate_mermaid_diagram(scenario)

        assert "flowchart TD" in diagram
        assert "step1" in diagram
        assert "Create User" in diagram
        assert "POST /users" in diagram

    def test_multi_step_scenario(self):
        """Test diagram generation with multiple steps."""
        scenario = ParsedScenario(
            name="User Flow",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Create User",
                    endpoint="POST /users",
                    endpoint_type="method_path",
                    method="POST",
                    path="/users",
                ),
                ScenarioStep(
                    name="Get User",
                    endpoint="GET /users/{id}",
                    endpoint_type="method_path",
                    method="GET",
                    path="/users/{id}",
                ),
            ],
        )

        diagram = generate_mermaid_diagram(scenario)

        assert "step1" in diagram
        assert "step2" in diagram
        assert "step1 --> step2" in diagram

    def test_diagram_with_correlations(self):
        """Test diagram shows variable flows from correlations."""
        scenario = ParsedScenario(
            name="Correlated Flow",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Create User",
                    endpoint="createUser",
                    endpoint_type="operation_id",
                    captures=[CaptureConfig(variable_name="userId")],
                ),
                ScenarioStep(
                    name="Get User",
                    endpoint="getUser",
                    endpoint_type="operation_id",
                ),
            ],
        )

        correlations = CorrelationResult(
            mappings=[
                CorrelationMapping(
                    variable_name="userId",
                    jsonpath="$.id",
                    source_step=1,
                    source_endpoint="createUser",
                    target_steps=[2],
                )
            ]
        )

        diagram = generate_mermaid_diagram(scenario, correlations)

        # Should show variable on edge between consecutive steps
        assert "userId" in diagram
        assert "step1 -->|userId| step2" in diagram

    def test_diagram_with_non_consecutive_variable_flow(self):
        """Test diagram shows dashed edges for non-consecutive variable flows."""
        scenario = ParsedScenario(
            name="Long Flow",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(name="Step 1", endpoint="op1", endpoint_type="operation_id"),
                ScenarioStep(name="Step 2", endpoint="op2", endpoint_type="operation_id"),
                ScenarioStep(name="Step 3", endpoint="op3", endpoint_type="operation_id"),
            ],
        )

        correlations = CorrelationResult(
            mappings=[
                CorrelationMapping(
                    variable_name="token",
                    jsonpath="$.token",
                    source_step=1,
                    source_endpoint="op1",
                    target_steps=[3],  # Skip step 2
                )
            ]
        )

        diagram = generate_mermaid_diagram(scenario, correlations)

        # Should show dashed arrow for non-consecutive flow
        assert "step1 -.->|token| step3" in diagram

    def test_diagram_without_correlations(self):
        """Test diagram works without correlation result."""
        scenario = ParsedScenario(
            name="No Correlations",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(name="Step 1", endpoint="op1", endpoint_type="operation_id"),
                ScenarioStep(name="Step 2", endpoint="op2", endpoint_type="operation_id"),
            ],
        )

        diagram = generate_mermaid_diagram(scenario, None)

        assert "flowchart TD" in diagram
        assert "step1 --> step2" in diagram

    def test_operationid_endpoint_format(self):
        """Test diagram with operationId endpoint format."""
        scenario = ParsedScenario(
            name="OpId Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Create User",
                    endpoint="createUser",
                    endpoint_type="operation_id",
                )
            ],
        )

        diagram = generate_mermaid_diagram(scenario)

        # Should show operationId as endpoint
        assert "createUser" in diagram


class TestGenerateTextVisualization:
    """Tests for generate_text_visualization function."""

    def test_basic_text_visualization(self):
        """Test basic text output format."""
        scenario = ParsedScenario(
            name="Test Scenario",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Create User",
                    endpoint="POST /users",
                    endpoint_type="method_path",
                    method="POST",
                    path="/users",
                )
            ],
        )

        text = generate_text_visualization(scenario)

        assert "Test Scenario" in text
        assert "=" * len("Test Scenario") in text
        assert "[1] Create User" in text
        assert "POST /users" in text

    def test_text_with_captures_and_uses(self):
        """Test text shows captures and variable usage."""
        scenario = ParsedScenario(
            name="Flow",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Create",
                    endpoint="op1",
                    endpoint_type="operation_id",
                    captures=[CaptureConfig(variable_name="id")],
                ),
                ScenarioStep(
                    name="Get",
                    endpoint="op2",
                    endpoint_type="operation_id",
                ),
            ],
        )

        correlations = CorrelationResult(
            mappings=[
                CorrelationMapping(
                    variable_name="id",
                    jsonpath="$.id",
                    source_step=1,
                    source_endpoint="op1",
                    target_steps=[2],
                )
            ]
        )

        text = generate_text_visualization(scenario, correlations)

        assert "Captures: id" in text
        assert "Uses: id" in text

    def test_text_shows_flow_arrows(self):
        """Test text shows flow arrows between steps."""
        scenario = ParsedScenario(
            name="Multi Step",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(name="Step 1", endpoint="op1", endpoint_type="operation_id"),
                ScenarioStep(name="Step 2", endpoint="op2", endpoint_type="operation_id"),
            ],
        )

        text = generate_text_visualization(scenario)

        # Should have flow indicators between steps
        assert "|" in text
        assert "v" in text


class TestEscapeMermaid:
    """Tests for _escape_mermaid helper function."""

    def test_escapes_quotes(self):
        """Test that double quotes are escaped."""
        result = _escape_mermaid('Test "quoted" text')
        assert "&quot;" in result
        assert '"' not in result

    def test_escapes_angle_brackets(self):
        """Test that angle brackets are escaped."""
        result = _escape_mermaid("Test <tag> text")
        assert "&lt;" in result
        assert "&gt;" in result

    def test_preserves_braces(self):
        """Test that braces for path params are preserved."""
        result = _escape_mermaid("/users/{userId}")
        assert "{userId}" in result


class TestBuildNodeLabel:
    """Tests for _build_node_label helper function."""

    def test_method_path_format(self):
        """Test label for method_path endpoint type."""
        step = ScenarioStep(
            name="Create User",
            endpoint="POST /users",
            endpoint_type="method_path",
            method="POST",
            path="/users",
        )

        label = _build_node_label(step, 1, [])

        assert "1. Create User" in label
        assert "POST /users" in label
        assert "<br/>" in label

    def test_operation_id_format(self):
        """Test label for operation_id endpoint type."""
        step = ScenarioStep(
            name="Create User",
            endpoint="createUser",
            endpoint_type="operation_id",
        )

        label = _build_node_label(step, 1, [])

        assert "1. Create User" in label
        assert "createUser" in label

    def test_label_with_captures(self):
        """Test label includes captures annotation."""
        step = ScenarioStep(
            name="Create User",
            endpoint="createUser",
            endpoint_type="operation_id",
        )

        label = _build_node_label(step, 1, ["userId", "token"])

        assert "captures: userId, token" in label
        assert "<i>" in label
