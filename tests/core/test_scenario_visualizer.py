"""Unit tests for ScenarioVisualizer."""

from io import StringIO

import pytest
from rich.console import Console

from jmeter_gen.core.scenario_visualizer import ScenarioVisualizer
from jmeter_gen.core.scenario_data import (
    AssertConfig,
    CaptureConfig,
    CorrelationMapping,
    CorrelationResult,
    ParsedScenario,
    ScenarioSettings,
    ScenarioStep,
)

# Mark all tests in this module as v2 tests
pytestmark = pytest.mark.v2


class TestScenarioVisualizer:
    """Tests for ScenarioVisualizer class."""

    @pytest.fixture
    def console_output(self):
        """Create a string buffer for console output."""
        return StringIO()

    @pytest.fixture
    def visualizer(self, console_output):
        """Create a visualizer instance with captured output."""
        console = Console(file=console_output, force_terminal=True, width=120)
        return ScenarioVisualizer(console=console)

    @pytest.fixture
    def simple_scenario(self):
        """Create a simple scenario for testing."""
        return ParsedScenario(
            name="Test Scenario",
            description="A test scenario",
            settings=ScenarioSettings(
                threads=5, rampup=10, duration=60, base_url="http://localhost:8000"
            ),
            variables={"api_key": "secret123"},
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
                    payload={"name": "Test User", "email": "test@example.com"},
                    captures=[CaptureConfig(variable_name="userId", source_field="id")],
                    assertions=AssertConfig(status=201, body={"name": "Test User"}),
                ),
                ScenarioStep(
                    name="Get User By ID",
                    endpoint="GET /users/${userId}",
                    endpoint_type="method_path",
                    method="GET",
                    path="/users/${userId}",
                    assertions=AssertConfig(status=200),
                ),
            ],
        )

    @pytest.fixture
    def correlation_results(self):
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

    def test_visualize_does_not_raise(self, visualizer, simple_scenario, console_output):
        """Test that visualize doesn't raise exceptions."""
        # Should not raise
        visualizer.visualize(simple_scenario)

        output = console_output.getvalue()
        assert len(output) > 0

    def test_visualize_contains_scenario_name(self, visualizer, simple_scenario, console_output):
        """Test that output contains the scenario name."""
        visualizer.visualize(simple_scenario)
        output = console_output.getvalue()
        assert "Test Scenario" in output

    def test_visualize_contains_step_names(self, visualizer, simple_scenario, console_output):
        """Test that output contains step names."""
        visualizer.visualize(simple_scenario)
        output = console_output.getvalue()
        assert "Get Users" in output
        assert "Create User" in output
        assert "Get User By ID" in output

    def test_visualize_contains_settings(self, visualizer, simple_scenario, console_output):
        """Test that output contains settings."""
        visualizer.visualize(simple_scenario)
        output = console_output.getvalue()
        # Settings should be shown somewhere
        assert "5" in output  # threads
        assert "10" in output  # rampup

    def test_visualize_with_correlations(
        self, visualizer, simple_scenario, correlation_results, console_output
    ):
        """Test visualization with correlation results."""
        visualizer.visualize(simple_scenario, correlation_result=correlation_results)
        output = console_output.getvalue()

        # Should show correlation information
        assert "userId" in output

    def test_visualize_shows_assertions(self, visualizer, simple_scenario, console_output):
        """Test that assertions are visualized."""
        visualizer.visualize(simple_scenario)
        output = console_output.getvalue()

        # Status codes should be visible
        assert "200" in output or "201" in output

    def test_visualize_empty_scenario(self, visualizer, console_output):
        """Test visualization of scenario with no steps."""
        scenario = ParsedScenario(
            name="Empty Scenario",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[],
        )

        visualizer.visualize(scenario)
        output = console_output.getvalue()
        assert "Empty Scenario" in output

    def test_visualize_no_captures(self, visualizer, console_output):
        """Test visualization of scenario without captures."""
        scenario = ParsedScenario(
            name="No Captures",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Simple GET",
                    endpoint="GET /test",
                    endpoint_type="method_path",
                    method="GET",
                    path="/test",
                )
            ],
        )

        visualizer.visualize(scenario)
        output = console_output.getvalue()
        assert "Simple GET" in output
        assert "GET" in output


class TestScenarioVisualizerMethods:
    """Tests for specific visualizer methods."""

    @pytest.fixture
    def console_output(self):
        """Create a string buffer for console output."""
        return StringIO()

    @pytest.fixture
    def visualizer(self, console_output):
        """Create a visualizer instance with captured output."""
        console = Console(file=console_output, force_terminal=True, width=120)
        return ScenarioVisualizer(console=console)

    def test_method_colors(self, visualizer, console_output):
        """Test that different HTTP methods are displayed."""
        scenario = ParsedScenario(
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="GET Request",
                    endpoint="GET /test",
                    endpoint_type="method_path",
                    method="GET",
                    path="/test",
                ),
                ScenarioStep(
                    name="POST Request",
                    endpoint="POST /test",
                    endpoint_type="method_path",
                    method="POST",
                    path="/test",
                ),
            ],
        )

        visualizer.visualize(scenario)
        output = console_output.getvalue()

        # Both methods should appear
        assert "GET" in output
        assert "POST" in output

    def test_render_to_console(self, visualizer, console_output):
        """Test rendering to a Rich console."""
        scenario = ParsedScenario(
            name="Console Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Test Step",
                    endpoint="GET /test",
                    endpoint_type="method_path",
                    method="GET",
                    path="/test",
                )
            ],
        )

        visualizer.visualize(scenario)
        output = console_output.getvalue()

        # Should produce non-empty output
        assert len(output) > 0


class TestScenarioVisualizerEdgeCases:
    """Edge case tests for ScenarioVisualizer."""

    @pytest.fixture
    def console_output(self):
        """Create a string buffer for console output."""
        return StringIO()

    @pytest.fixture
    def visualizer(self, console_output):
        """Create a visualizer instance with captured output."""
        console = Console(file=console_output, force_terminal=True, width=120)
        return ScenarioVisualizer(console=console)

    def test_long_step_names(self, visualizer, console_output):
        """Test handling of long step names."""
        long_name = "This is a very long step name that might cause formatting issues " * 3

        scenario = ParsedScenario(
            name="Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name=long_name,
                    endpoint="GET /test",
                    endpoint_type="method_path",
                    method="GET",
                    path="/test",
                )
            ],
        )

        # Should not raise
        visualizer.visualize(scenario)
        output = console_output.getvalue()
        assert len(output) > 0

    def test_many_steps(self, visualizer, console_output):
        """Test handling of many steps."""
        steps = [
            ScenarioStep(
                name=f"Step {i}",
                endpoint=f"GET /test/{i}",
                endpoint_type="method_path",
                method="GET",
                path=f"/test/{i}",
            )
            for i in range(50)
        ]

        scenario = ParsedScenario(
            name="Many Steps",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=steps,
        )

        # Should not raise
        visualizer.visualize(scenario)
        output = console_output.getvalue()
        assert "Step 0" in output
        assert "Step 49" in output

    def test_many_captures(self, visualizer, console_output):
        """Test handling of many captures in one step."""
        captures = [
            CaptureConfig(variable_name=f"var{i}")
            for i in range(20)
        ]

        scenario = ParsedScenario(
            name="Many Captures",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Capture All",
                    endpoint="GET /data",
                    endpoint_type="method_path",
                    method="GET",
                    path="/data",
                    captures=captures,
                )
            ],
        )

        # Should not raise
        visualizer.visualize(scenario)
        output = console_output.getvalue()
        assert "var0" in output

    def test_disabled_step(self, visualizer, console_output):
        """Test visualization of disabled step."""
        scenario = ParsedScenario(
            name="Disabled Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Disabled Step",
                    endpoint="GET /test",
                    endpoint_type="method_path",
                    method="GET",
                    path="/test",
                    enabled=False,
                )
            ],
        )

        visualizer.visualize(scenario)
        output = console_output.getvalue()
        # Should indicate the step is disabled
        assert "Disabled Step" in output
        assert "disabled" in output.lower()

    def test_correlation_warnings(self, visualizer, console_output):
        """Test display of correlation warnings."""
        scenario = ParsedScenario(
            name="Warnings Test",
            description=None,
            settings=ScenarioSettings(),
            variables={},
            steps=[
                ScenarioStep(
                    name="Step",
                    endpoint="GET /test",
                    endpoint_type="method_path",
                    method="GET",
                    path="/test",
                )
            ],
        )

        correlation_result = CorrelationResult(
            warnings=["Low confidence for variable 'foo'"],
            errors=["Could not resolve 'bar'"],
        )

        visualizer.visualize(scenario, correlation_result=correlation_result)
        output = console_output.getvalue()
        # Should display warnings and errors
        assert "Low confidence" in output or "Warnings" in output
