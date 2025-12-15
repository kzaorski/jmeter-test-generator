"""Mermaid diagram generator for scenario visualization.

This module generates Mermaid flowchart diagrams from parsed scenarios
and correlation results, providing a visual representation of test flows
and variable dependencies.
"""

import re
from typing import Optional

from jmeter_gen.core.scenario_data import (
    CorrelationMapping,
    CorrelationResult,
    ParsedScenario,
    ScenarioStep,
)

# Pattern to extract JSONPath field from while condition
# e.g., "$.status != 'finished'" -> "status"
JSONPATH_FIELD_PATTERN = re.compile(r"\$\.([a-zA-Z_][a-zA-Z0-9_]*)")


def generate_mermaid_diagram(
    scenario: ParsedScenario,
    correlation_result: Optional[CorrelationResult] = None,
) -> str:
    """Generate Mermaid flowchart from scenario and correlations.

    Creates a top-down flowchart showing:
    - Sequential test steps as nodes
    - Variable flows as labeled edges between steps
    - Captures and variable usage annotations

    Args:
        scenario: Parsed scenario with steps
        correlation_result: Optional correlation analysis result for variable flows

    Returns:
        Mermaid diagram code as a string

    Example:
        >>> diagram = generate_mermaid_diagram(scenario, correlations)
        >>> print(diagram)
        flowchart TD
            step1["1. Create User<br/>POST /users"]
            step2["2. Get User<br/>GET /users/{userId}"]
            step1 -->|userId| step2
    """
    lines: list[str] = ["flowchart TD"]

    # Build variable capture/usage map
    captures_by_step: dict[int, list[str]] = {}  # step_index -> [variable_names]
    uses_by_step: dict[int, list[str]] = {}  # step_index -> [variable_names]

    if correlation_result:
        for mapping in correlation_result.mappings:
            step_idx = mapping.source_step
            if step_idx not in captures_by_step:
                captures_by_step[step_idx] = []
            captures_by_step[step_idx].append(mapping.variable_name)

            for target_step in mapping.target_steps:
                if target_step not in uses_by_step:
                    uses_by_step[target_step] = []
                uses_by_step[target_step].append(mapping.variable_name)

    # Generate step nodes
    for idx, step in enumerate(scenario.steps, 1):
        node_id = f"step{idx}"
        node_label = _build_node_label(step, idx, captures_by_step.get(idx, []))
        lines.append(f'    {node_id}["{node_label}"]')

    # Add empty line before edges
    if len(scenario.steps) > 1:
        lines.append("")

    # Generate edges between consecutive steps
    for idx in range(1, len(scenario.steps)):
        from_node = f"step{idx}"
        to_node = f"step{idx + 1}"

        # Check if there are variables flowing from this step to the next
        captured_vars = captures_by_step.get(idx, [])
        used_vars = uses_by_step.get(idx + 1, [])
        flowing_vars = [v for v in captured_vars if v in used_vars]

        if flowing_vars:
            # Show variable names on the edge
            var_label = ", ".join(flowing_vars)
            lines.append(f"    {from_node} -->|{var_label}| {to_node}")
        else:
            lines.append(f"    {from_node} --> {to_node}")

    # Add non-consecutive variable flows (if any)
    if correlation_result:
        for mapping in correlation_result.mappings:
            source_step = mapping.source_step
            for target_step in mapping.target_steps:
                # Only add if not consecutive (consecutive already handled above)
                if target_step != source_step + 1:
                    lines.append(
                        f"    step{source_step} -.->|{mapping.variable_name}| step{target_step}"
                    )

    return "\n".join(lines)


def _build_node_label(
    step: ScenarioStep,
    step_number: int,
    captures: list[str],
) -> str:
    """Build the label for a step node.

    Args:
        step: The scenario step
        step_number: 1-based step number
        captures: List of variable names captured in this step

    Returns:
        HTML-escaped label string for Mermaid node
    """
    # Escape special characters for Mermaid
    name = _escape_mermaid(step.name)

    # Handle think_time steps
    if step.endpoint_type == "think_time":
        return f"{step_number}. {name}<br/>think_time: {step.think_time}ms"

    # Handle loop_block (multi-step loop)
    if step.endpoint_type == "loop_block" and step.nested_steps:
        if step.loop and step.loop.count:
            loop_info = f"loop: {step.loop.count}x"
        elif step.loop and step.loop.while_condition:
            loop_info = f"while: {_escape_mermaid(step.loop.while_condition)}"
            # Add auto-capture for while condition variable
            match = JSONPATH_FIELD_PATTERN.search(step.loop.while_condition)
            if match:
                condition_var = match.group(1)
                loop_info += f"<br/><i>auto-capture: {condition_var}</i>"
        else:
            loop_info = "loop"

        # List nested steps
        nested_labels = []
        for nested_step in step.nested_steps:
            if nested_step.endpoint_type == "think_time":
                nested_labels.append(f"think_time: {nested_step.think_time}ms")
            elif nested_step.endpoint_type == "method_path" and nested_step.method:
                nested_labels.append(f"{nested_step.method} {nested_step.path}")
            else:
                nested_labels.append(nested_step.endpoint)

        nested_str = "<br/>".join(_escape_mermaid(n) for n in nested_labels)
        return f"{step_number}. {name}<br/>{loop_info}<br/>{nested_str}"

    # Build endpoint string for regular steps
    if step.endpoint_type == "method_path" and step.method and step.path:
        endpoint = f"{step.method} {step.path}"
    else:
        endpoint = step.endpoint
    endpoint = _escape_mermaid(endpoint)

    # Build label with line breaks
    label = f"{step_number}. {name}<br/>{endpoint}"

    # Add loop info for single-step loops
    if step.loop:
        if step.loop.count:
            label += f"<br/>loop: {step.loop.count}x"
        elif step.loop.while_condition:
            label += f"<br/>while: {_escape_mermaid(step.loop.while_condition)}"
            # Add auto-capture for while condition variable
            match = JSONPATH_FIELD_PATTERN.search(step.loop.while_condition)
            if match:
                condition_var = match.group(1)
                label += f"<br/><i>auto-capture: {condition_var}</i>"

    # Add captures annotation if any
    if captures:
        captures_str = ", ".join(captures)
        label += f"<br/><i>captures: {captures_str}</i>"

    return label


def _escape_mermaid(text: str) -> str:
    """Escape special characters for Mermaid diagrams.

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for Mermaid
    """
    # Replace characters that have special meaning in Mermaid
    text = text.replace('"', "&quot;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    # Keep braces for path parameters but escape if needed
    return text


def generate_text_visualization(
    scenario: ParsedScenario,
    correlation_result: Optional[CorrelationResult] = None,
) -> str:
    """Generate ASCII text visualization of scenario flow.

    Creates a simple text-based visualization showing:
    - Sequential test steps
    - Variable captures and usage
    - Flow arrows between steps

    Args:
        scenario: Parsed scenario with steps
        correlation_result: Optional correlation analysis result

    Returns:
        Text visualization as a string

    Example:
        >>> viz = generate_text_visualization(scenario, correlations)
        >>> print(viz)
        User Registration Flow
        =======================
        [1] Create User
            POST /users
            Captures: userId
            |
            v
        [2] Get User
            GET /users/{userId}
            Uses: userId
    """
    lines: list[str] = []

    # Title
    lines.append(scenario.name)
    lines.append("=" * len(scenario.name))

    # Build variable maps
    captures_by_step: dict[int, list[str]] = {}
    uses_by_step: dict[int, list[str]] = {}

    if correlation_result:
        for mapping in correlation_result.mappings:
            step_idx = mapping.source_step
            if step_idx not in captures_by_step:
                captures_by_step[step_idx] = []
            captures_by_step[step_idx].append(mapping.variable_name)

            for target_step in mapping.target_steps:
                if target_step not in uses_by_step:
                    uses_by_step[target_step] = []
                uses_by_step[target_step].append(mapping.variable_name)

    # Generate steps
    for idx, step in enumerate(scenario.steps, 1):
        lines.append(f"[{idx}] {step.name}")

        # Handle think_time steps
        if step.endpoint_type == "think_time":
            lines.append(f"    think_time: {step.think_time}ms")
        # Handle loop_block (multi-step loop)
        elif step.endpoint_type == "loop_block" and step.nested_steps:
            if step.loop and step.loop.count:
                lines.append(f"    loop: {step.loop.count}x")
            elif step.loop and step.loop.while_condition:
                lines.append(f"    while: {step.loop.while_condition}")
                # Show auto-capture for while condition variable
                match = JSONPATH_FIELD_PATTERN.search(step.loop.while_condition)
                if match:
                    condition_var = match.group(1)
                    lines.append(f"    Auto-capture: {condition_var} (for condition)")
            for nested_idx, nested_step in enumerate(step.nested_steps, 1):
                if nested_step.endpoint_type == "think_time":
                    lines.append(f"      [{nested_idx}] {nested_step.name}: {nested_step.think_time}ms")
                elif nested_step.endpoint_type == "method_path" and nested_step.method:
                    lines.append(f"      [{nested_idx}] {nested_step.method} {nested_step.path}")
                else:
                    lines.append(f"      [{nested_idx}] {nested_step.endpoint}")
                if nested_step.captures:
                    caps = ", ".join(c.variable_name for c in nested_step.captures)
                    lines.append(f"          Captures: {caps}")
        # Endpoint (regular step)
        elif step.endpoint_type == "method_path" and step.method and step.path:
            lines.append(f"    {step.method} {step.path}")
        else:
            lines.append(f"    {step.endpoint}")

        # Show loop info for single-step loops
        if step.loop and step.endpoint_type not in ("think_time", "loop_block"):
            if step.loop.count:
                lines.append(f"    loop: {step.loop.count}x")
            elif step.loop.while_condition:
                lines.append(f"    while: {step.loop.while_condition}")
                # Show auto-capture for while condition variable
                match = JSONPATH_FIELD_PATTERN.search(step.loop.while_condition)
                if match:
                    condition_var = match.group(1)
                    lines.append(f"    Auto-capture: {condition_var} (for condition)")

        # Captures
        if idx in captures_by_step:
            lines.append(f"    Captures: {', '.join(captures_by_step[idx])}")

        # Uses
        if idx in uses_by_step:
            lines.append(f"    Uses: {', '.join(uses_by_step[idx])}")

        # Flow arrow (except for last step)
        if idx < len(scenario.steps):
            lines.append("    |")
            lines.append("    v")

    return "\n".join(lines)
