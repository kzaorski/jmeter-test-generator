"""Terminal visualization for scenario flows (v2).

This module provides Rich-based terminal visualization for scenario flows,
showing steps, variable dependencies, and correlation mappings.
"""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from jmeter_gen.core.scenario_data import (
    CorrelationMapping,
    CorrelationResult,
    ParsedScenario,
    ScenarioStep,
)


class ScenarioVisualizer:
    """Visualize scenario flow in terminal with Rich formatting.

    Displays scenario steps, variable captures, and correlation information
    in a visually appealing format.

    Example:
        >>> visualizer = ScenarioVisualizer()
        >>> visualizer.visualize(scenario, correlation_result)
    """

    def __init__(self, console: Optional[Console] = None) -> None:
        """Initialize visualizer.

        Args:
            console: Rich Console instance (creates new one if not provided)
        """
        self.console = console or Console()

    def visualize(
        self,
        scenario: ParsedScenario,
        correlation_result: Optional[CorrelationResult] = None,
    ) -> None:
        """Display scenario visualization in terminal.

        Args:
            scenario: Parsed scenario to visualize
            correlation_result: Optional correlation analysis result
        """
        # Header
        self.console.print()
        self.console.print(
            f"[bold blue]Scenario:[/bold blue] {scenario.name}",
            highlight=False,
        )
        if scenario.description:
            self.console.print(f"[dim]{scenario.description}[/dim]")

        # Settings summary
        self._render_settings(scenario)

        self.console.print()

        # Build mapping lookup for quick access
        mapping_by_step: dict[int, list[CorrelationMapping]] = {}
        if correlation_result:
            for mapping in correlation_result.mappings:
                step_idx = mapping.source_step
                if step_idx not in mapping_by_step:
                    mapping_by_step[step_idx] = []
                mapping_by_step[step_idx].append(mapping)

        # Render each step
        for i, step in enumerate(scenario.steps, start=1):
            step_mappings = mapping_by_step.get(i, [])
            panel = self._render_step(step, i, step_mappings)
            self.console.print(panel)

            # Show variable flow arrow if step has captures used later
            if step_mappings:
                used_vars = [m for m in step_mappings if m.target_steps]
                if used_vars:
                    var_names = ", ".join(f"${{{m.variable_name}}}" for m in used_vars)
                    self.console.print(f"         [dim]|[/dim]")
                    self.console.print(f"         [dim]| {var_names}[/dim]")
                    self.console.print(f"         [dim]v[/dim]")

        # Variable flow table
        if correlation_result and correlation_result.mappings:
            self.console.print()
            table = self._render_variable_flow(scenario, correlation_result)
            self.console.print(table)

        # Warnings and errors
        if correlation_result:
            self._render_correlation_issues(correlation_result)

    def _render_settings(self, scenario: ParsedScenario) -> None:
        """Render scenario settings summary."""
        settings = scenario.settings
        parts = []

        parts.append(f"Threads: {settings.threads}")
        parts.append(f"Ramp-up: {settings.rampup}s")

        if settings.duration:
            parts.append(f"Duration: {settings.duration}s")

        if settings.base_url:
            parts.append(f"Base URL: {settings.base_url}")

        if scenario.variables:
            parts.append(f"Variables: {len(scenario.variables)}")

        self.console.print(f"[dim]{' | '.join(parts)}[/dim]")

    def _render_step(
        self,
        step: ScenarioStep,
        index: int,
        mappings: list[CorrelationMapping],
    ) -> Panel:
        """Render single step as Rich Panel."""
        # Build content
        content = Text()

        # Endpoint line
        if step.endpoint_type == "method_path":
            method_color = self._get_method_color(step.method or "GET")
            content.append(f"{step.method} ", style=f"bold {method_color}")
            content.append(step.path or step.endpoint)
        else:
            content.append(step.endpoint, style="cyan")

        # Parameters
        if step.params:
            content.append("\n")
            content.append("params: ", style="dim")
            content.append(str(step.params), style="dim italic")

        # Payload indicator
        if step.payload:
            content.append("\n")
            content.append("body: ", style="dim")
            content.append("<JSON payload>", style="dim italic")

        # Captures with JSONPath
        if mappings:
            content.append("\n")
            content.append("capture: ", style="yellow")
            capture_parts = []
            for m in mappings:
                confidence_indicator = self._get_confidence_indicator(m.confidence)
                capture_parts.append(
                    f"{m.variable_name} ({m.jsonpath}) {confidence_indicator}"
                )
            content.append(", ".join(capture_parts), style="yellow")
        elif step.captures:
            content.append("\n")
            content.append("capture: ", style="yellow")
            content.append(
                ", ".join(c.variable_name for c in step.captures),
                style="yellow",
            )

        # Assertions
        if step.assertions:
            content.append("\n")
            content.append("assert: ", style="green")
            if step.assertions.status:
                content.append(f"status={step.assertions.status}", style="green")

        # Loop configuration
        if step.loop:
            content.append("\n")
            content.append("loop: ", style="magenta")
            loop_parts = []
            if step.loop.count:
                loop_parts.append(f"count={step.loop.count}")
            if step.loop.while_condition:
                loop_parts.append(f"while: {step.loop.while_condition}")
                loop_parts.append(f"max={step.loop.max_iterations}")
            if step.loop.interval:
                # Format interval (ms to human readable)
                interval_sec = step.loop.interval / 1000
                if interval_sec >= 1:
                    interval_str = f"{interval_sec:.0f}s" if interval_sec == int(interval_sec) else f"{interval_sec}s"
                else:
                    interval_str = f"{step.loop.interval}ms"
                loop_parts.append(f"interval={interval_str}")
            content.append(", ".join(loop_parts), style="magenta")

        # Build title
        title = f"[{index}] {step.name}"
        if not step.enabled:
            title += " [dim](disabled)[/dim]"

        # Panel style based on enabled state
        border_style = "blue" if step.enabled else "dim"

        return Panel(
            content,
            title=title,
            title_align="left",
            border_style=border_style,
            padding=(0, 1),
        )

    def _render_variable_flow(
        self,
        scenario: ParsedScenario,
        correlation_result: CorrelationResult,
    ) -> Table:
        """Render variable flow as Rich Table."""
        table = Table(title="Variable Flow", title_style="bold")

        table.add_column("Variable", style="yellow")
        table.add_column("Source", style="cyan")
        table.add_column("JSONPath", style="dim")
        table.add_column("Used In", style="green")
        table.add_column("Confidence", justify="center")

        for mapping in correlation_result.mappings:
            # Format target steps
            if mapping.target_steps:
                used_in = ", ".join(f"[{s}]" for s in mapping.target_steps)
            else:
                used_in = "[dim]-[/dim]"

            # Confidence display
            conf_display = self._get_confidence_display(mapping.confidence)

            table.add_row(
                mapping.variable_name,
                f"[{mapping.source_step}]",
                mapping.jsonpath,
                used_in,
                conf_display,
            )

        return table

    def _render_correlation_issues(
        self, correlation_result: CorrelationResult
    ) -> None:
        """Render correlation warnings and errors."""
        if correlation_result.warnings:
            self.console.print()
            self.console.print("[yellow]Warnings:[/yellow]")
            for warning in correlation_result.warnings:
                self.console.print(f"  [yellow]![/yellow] {warning}")

        if correlation_result.errors:
            self.console.print()
            self.console.print("[red]Errors:[/red]")
            for error in correlation_result.errors:
                self.console.print(f"  [red]x[/red] {error}")

    def _get_method_color(self, method: str) -> str:
        """Get color for HTTP method."""
        colors = {
            "GET": "green",
            "POST": "blue",
            "PUT": "yellow",
            "PATCH": "yellow",
            "DELETE": "red",
            "HEAD": "cyan",
            "OPTIONS": "magenta",
        }
        return colors.get(method.upper(), "white")

    def _get_confidence_indicator(self, confidence: float) -> str:
        """Get short confidence indicator."""
        if confidence >= 0.9:
            return "[green][HIGH][/green]"
        elif confidence >= 0.7:
            return "[yellow][MED][/yellow]"
        else:
            return "[red][LOW][/red]"

    def _get_confidence_display(self, confidence: float) -> str:
        """Get confidence display for table."""
        pct = f"{confidence:.0%}"
        if confidence >= 0.9:
            return f"[green]{pct}[/green]"
        elif confidence >= 0.7:
            return f"[yellow]{pct}[/yellow]"
        else:
            return f"[red]{pct}[/red]"
