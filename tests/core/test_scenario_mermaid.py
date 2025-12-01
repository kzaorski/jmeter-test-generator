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
    LoopConfig,
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


class TestWhileConditionAutoCapture:
    """Tests for while condition auto-capture visualization."""

    def test_mermaid_single_step_while_shows_auto_capture(self):
        """Test that single-step while loop shows auto-capture in Mermaid diagram."""
        scenario = ParsedScenario(
            name="While Loop Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Poll Status",
                    endpoint="GET /status",
                    endpoint_type="method_path",
                    method="GET",
                    path="/status",
                    loop=LoopConfig(
                        while_condition="$.status != 'finished'",
                        max_iterations=100,
                    ),
                )
            ],
        )

        diagram = generate_mermaid_diagram(scenario)

        # Should show the while condition
        assert "while" in diagram.lower()
        # Should show auto-capture for the condition variable
        assert "auto-capture" in diagram.lower()
        assert "status" in diagram

    def test_mermaid_loop_block_while_shows_auto_capture(self):
        """Test that loop_block with while condition shows auto-capture in Mermaid."""
        scenario = ParsedScenario(
            name="Loop Block While Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Poll with Delay",
                    endpoint="loop_block",
                    endpoint_type="loop_block",
                    loop=LoopConfig(
                        while_condition="$.jobStatus != 'complete'",
                        max_iterations=50,
                    ),
                    nested_steps=[
                        ScenarioStep(
                            name="Check Job",
                            endpoint="GET /job/status",
                            endpoint_type="method_path",
                            method="GET",
                            path="/job/status",
                        ),
                    ],
                )
            ],
        )

        diagram = generate_mermaid_diagram(scenario)

        # Should show the while condition
        assert "while" in diagram.lower()
        # Should show auto-capture for the condition variable
        assert "auto-capture" in diagram.lower()
        assert "jobStatus" in diagram

    def test_mermaid_fixed_count_loop_no_auto_capture(self):
        """Test that fixed count loop does not show auto-capture in Mermaid."""
        scenario = ParsedScenario(
            name="Count Loop Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Repeat Action",
                    endpoint="POST /action",
                    endpoint_type="method_path",
                    method="POST",
                    path="/action",
                    loop=LoopConfig(count=5),
                )
            ],
        )

        diagram = generate_mermaid_diagram(scenario)

        # Should show loop count
        assert "loop" in diagram.lower() or "5x" in diagram
        # Should NOT show auto-capture (no while condition)
        assert "auto-capture" not in diagram.lower()

    def test_text_single_step_while_shows_auto_capture(self):
        """Test that single-step while loop shows auto-capture in text visualization."""
        scenario = ParsedScenario(
            name="While Loop Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Poll Status",
                    endpoint="GET /status",
                    endpoint_type="method_path",
                    method="GET",
                    path="/status",
                    loop=LoopConfig(
                        while_condition="$.status != 'finished'",
                        max_iterations=100,
                    ),
                )
            ],
        )

        text = generate_text_visualization(scenario)

        # Should show the while condition
        assert "while" in text.lower()
        assert "status" in text
        # Should show auto-capture for the condition variable
        assert "Auto-capture" in text

    def test_text_loop_block_while_shows_auto_capture(self):
        """Test that loop_block with while shows auto-capture in text visualization."""
        scenario = ParsedScenario(
            name="Loop Block While Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Poll with Delay",
                    endpoint="loop_block",
                    endpoint_type="loop_block",
                    loop=LoopConfig(
                        while_condition="$.jobStatus != 'complete'",
                        max_iterations=50,
                    ),
                    nested_steps=[
                        ScenarioStep(
                            name="Check Job",
                            endpoint="GET /job/status",
                            endpoint_type="method_path",
                            method="GET",
                            path="/job/status",
                        ),
                    ],
                )
            ],
        )

        text = generate_text_visualization(scenario)

        # Should show the while condition
        assert "while" in text.lower()
        assert "jobStatus" in text
        # Should show auto-capture for the condition variable
        assert "Auto-capture" in text

    def test_text_fixed_count_loop_no_auto_capture(self):
        """Test that fixed count loop does not show auto-capture in text visualization."""
        scenario = ParsedScenario(
            name="Count Loop Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Repeat Action",
                    endpoint="POST /action",
                    endpoint_type="method_path",
                    method="POST",
                    path="/action",
                    loop=LoopConfig(count=5),
                )
            ],
        )

        text = generate_text_visualization(scenario)

        # Should show loop count
        assert "loop" in text.lower() or "5x" in text
        # Should NOT show auto-capture (no while condition)
        assert "Auto-capture" not in text
