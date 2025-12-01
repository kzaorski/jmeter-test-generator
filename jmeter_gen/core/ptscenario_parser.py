"""Parser for pt_scenario.yaml scenario files (v2).

This module provides functionality to parse pt_scenario.yaml files and
validate scenario structure for JMeter test generation.
"""

import re
from pathlib import Path
from typing import Any, Optional

import yaml

from jmeter_gen.exceptions import (
    InvalidEndpointFormatException,
    ScenarioParseException,
    ScenarioValidationException,
    UndefinedVariableException,
)
from jmeter_gen.core.scenario_data import (
    AssertConfig,
    CaptureConfig,
    LoopConfig,
    ParsedScenario,
    ScenarioSettings,
    ScenarioStep,
)

# Supported HTTP methods for METHOD /path format
HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}

# Variable reference pattern: ${varName}
VARIABLE_PATTERN = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class PtScenarioParser:
    """Parse and validate pt_scenario.yaml scenario files.

    This parser reads YAML scenario files, validates their structure,
    and converts them to ParsedScenario dataclass instances.

    Example:
        >>> parser = PtScenarioParser()
        >>> scenario = parser.parse("pt_scenario.yaml")
        >>> print(scenario.name)
        'User CRUD Flow'
    """

    def __init__(self) -> None:
        """Initialize scenario parser."""
        pass

    def parse(self, scenario_path: str) -> ParsedScenario:
        """Parse pt_scenario.yaml file and return structured data.

        Args:
            scenario_path: Path to pt_scenario.yaml file

        Returns:
            ParsedScenario instance with all scenario data

        Raises:
            FileNotFoundError: Scenario file doesn't exist
            ScenarioParseException: YAML parsing fails or required fields missing
            ScenarioValidationException: Scenario structure is invalid
        """
        path = Path(scenario_path)

        if not path.exists():
            raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

        # Parse YAML
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ScenarioParseException(f"Invalid YAML syntax in {scenario_path}: {e}")

        if not isinstance(data, dict):
            raise ScenarioParseException(
                f"Invalid scenario format in {scenario_path}: expected dictionary"
            )

        # Validate required fields
        self._validate_required_fields(data, scenario_path)

        # Parse scenario data
        name = str(data["name"])
        description = data.get("description")

        # Parse settings
        settings = self._parse_settings(data.get("settings", {}))

        # Parse variables
        variables = data.get("variables", {})
        if not isinstance(variables, dict):
            raise ScenarioValidationException(
                f"Invalid 'variables' in {scenario_path}: expected dictionary"
            )

        # Parse steps
        steps = self._parse_steps(data["scenario"], scenario_path)

        return ParsedScenario(
            name=name,
            description=description,
            settings=settings,
            variables=variables,
            steps=steps,
        )

    def validate(
        self,
        scenario: ParsedScenario,
        available_operation_ids: Optional[list[str]] = None,
        available_paths: Optional[dict[str, list[str]]] = None,
    ) -> list[str]:
        """Validate scenario against OpenAPI spec.

        Args:
            scenario: Parsed scenario to validate
            available_operation_ids: List of valid operationIds from spec
            available_paths: Dict of path -> methods from spec

        Returns:
            List of validation warnings

        Raises:
            UndefinedVariableException: Variable used before definition
        """
        warnings: list[str] = []

        # Track variables: global + captured
        defined_vars = set(scenario.variables.keys())

        for i, step in enumerate(scenario.steps, start=1):
            # Check variable usage in this step
            used_vars = self._find_variable_references(step)
            undefined = used_vars - defined_vars

            if undefined:
                raise UndefinedVariableException(
                    f"Step [{i}] '{step.name}' uses undefined variables: {undefined}"
                )

            # Add captured variables for subsequent steps
            for capture in step.captures:
                defined_vars.add(capture.variable_name)

            # Validate endpoint if spec info provided
            if step.endpoint_type == "operation_id" and available_operation_ids:
                if step.endpoint not in available_operation_ids:
                    warnings.append(
                        f"Step [{i}]: operationId '{step.endpoint}' not found in spec"
                    )
            elif step.endpoint_type == "method_path" and available_paths:
                if step.path and step.method:
                    # Check if path exists (exact or suffix match)
                    path_found = False
                    for spec_path in available_paths:
                        if spec_path == step.path or spec_path.endswith(step.path):
                            if step.method in available_paths[spec_path]:
                                path_found = True
                                break
                    if not path_found:
                        warnings.append(
                            f"Step [{i}]: {step.method} {step.path} not found in spec"
                        )

        return warnings

    def _validate_required_fields(self, data: dict, path: str) -> None:
        """Validate required fields in scenario data."""
        if "name" not in data:
            raise ScenarioParseException(f"Missing required field 'name' in {path}")

        if "scenario" not in data:
            raise ScenarioParseException(f"Missing required field 'scenario' in {path}")

        if not isinstance(data["scenario"], list):
            raise ScenarioValidationException(
                f"Invalid 'scenario' in {path}: expected list of steps"
            )

        if len(data["scenario"]) == 0:
            raise ScenarioValidationException(
                f"Empty 'scenario' in {path}: at least one step required"
            )

    def _parse_settings(self, settings_data: dict) -> ScenarioSettings:
        """Parse settings section."""
        return ScenarioSettings(
            threads=int(settings_data.get("threads", 1)),
            rampup=int(settings_data.get("rampup", 0)),
            loops=settings_data.get("loops"),
            duration=settings_data.get("duration"),
            base_url=settings_data.get("base_url"),
        )

    def _parse_steps(self, steps_data: list, scenario_path: str) -> list[ScenarioStep]:
        """Parse scenario steps."""
        steps = []

        for i, step_data in enumerate(steps_data, start=1):
            if not isinstance(step_data, dict):
                raise ScenarioValidationException(
                    f"Invalid step {i} in {scenario_path}: expected dictionary"
                )

            # Check if this is a think_time step (no name required for backward compat)
            if "think_time" in step_data and "endpoint" not in step_data and "steps" not in step_data:
                think_time_ms = step_data["think_time"]
                if not isinstance(think_time_ms, int) or think_time_ms < 0:
                    raise ScenarioValidationException(
                        f"Invalid think_time in step {i}: must be non-negative integer"
                    )
                step = ScenarioStep(
                    name=step_data.get("name", "Think Time"),
                    endpoint="think_time",
                    endpoint_type="think_time",
                    think_time=think_time_ms,
                )
                steps.append(step)
                continue

            # Check if this is a multi-step loop block (has loop + steps, no endpoint)
            if "loop" in step_data and "steps" in step_data and "endpoint" not in step_data:
                loop_config = self._parse_loop(step_data.get("loop"), i, scenario_path)
                if loop_config is None:
                    raise ScenarioValidationException(
                        f"Invalid loop configuration in step {i} of {scenario_path}"
                    )

                # Parse nested steps recursively
                nested_steps_data = step_data["steps"]
                if not isinstance(nested_steps_data, list) or not nested_steps_data:
                    raise ScenarioValidationException(
                        f"Multi-step loop in step {i} must have non-empty 'steps' list"
                    )
                nested_steps = self._parse_steps(nested_steps_data, scenario_path)

                # Create loop block name
                if loop_config.count:
                    loop_name = step_data.get("name", f"Loop {loop_config.count}x")
                else:
                    loop_name = step_data.get("name", "While Loop")

                step = ScenarioStep(
                    name=loop_name,
                    endpoint="loop_block",
                    endpoint_type="loop_block",
                    loop=loop_config,
                    nested_steps=nested_steps,
                )
                steps.append(step)
                continue

            # Validate required step fields for regular steps
            if "name" not in step_data:
                raise ScenarioValidationException(
                    f"Missing 'name' in step {i} of {scenario_path}"
                )

            # Regular endpoint step - validate endpoint field
            if "endpoint" not in step_data:
                raise ScenarioValidationException(
                    f"Missing 'endpoint' in step {i} of {scenario_path}"
                )

            # Parse endpoint
            endpoint = str(step_data["endpoint"])
            endpoint_type, method, path = self._parse_endpoint(endpoint)

            # Parse captures
            captures = self._parse_captures(step_data.get("capture", []))

            # Parse assertions
            assertions = self._parse_assert(step_data.get("assert"))

            # Parse loop configuration (single-step loop)
            loop_config = self._parse_loop(step_data.get("loop"), i, scenario_path)

            step = ScenarioStep(
                name=str(step_data["name"]),
                endpoint=endpoint,
                endpoint_type=endpoint_type,
                method=method,
                path=path,
                enabled=step_data.get("enabled", True),
                params=step_data.get("params", {}),
                headers=step_data.get("headers", {}),
                payload=step_data.get("payload"),
                captures=captures,
                assertions=assertions,
                loop=loop_config,
            )
            steps.append(step)

        return steps

    def _parse_endpoint(self, endpoint: str) -> tuple[str, Optional[str], Optional[str]]:
        """Parse endpoint string and detect format.

        Args:
            endpoint: Endpoint string (operationId or "METHOD /path")

        Returns:
            Tuple of (endpoint_type, method, path)
            - For operationId: ("operation_id", None, None)
            - For METHOD /path: ("method_path", "GET", "/users")

        Raises:
            InvalidEndpointFormatException: Invalid endpoint format
        """
        # Try to parse as METHOD /path
        parts = endpoint.split(" ", 1)

        if len(parts) == 2:
            method_candidate = parts[0].upper()
            path_candidate = parts[1].strip()

            if method_candidate in HTTP_METHODS:
                # Validate path format
                if not path_candidate.startswith("/"):
                    raise InvalidEndpointFormatException(
                        f"Invalid path in endpoint '{endpoint}': path must start with '/'"
                    )
                return ("method_path", method_candidate, path_candidate)
            else:
                # Not a valid HTTP method - might be operationId with space
                raise InvalidEndpointFormatException(
                    f"Invalid endpoint format '{endpoint}': "
                    f"'{method_candidate}' is not a valid HTTP method. "
                    f"Expected one of: {', '.join(sorted(HTTP_METHODS))}"
                )

        # Single word - assume operationId
        # Validate it's not empty and doesn't contain invalid characters
        if not endpoint or endpoint.isspace():
            raise InvalidEndpointFormatException("Endpoint cannot be empty")

        return ("operation_id", None, None)

    def _parse_captures(self, capture_data: Any) -> list[CaptureConfig]:
        """Parse capture configuration.

        Supports three syntaxes:
        1. Simple: ["userId", "email"] - auto-detect JSONPath
        2. Mapped: [{"userId": "id"}] - capture $.id as userId
        3. Explicit: [{"itemId": {"path": "$.items[0].id", "match": "first"}}]
        """
        if not capture_data:
            return []

        if not isinstance(capture_data, list):
            capture_data = [capture_data]

        captures = []
        for item in capture_data:
            capture = self._parse_single_capture(item)
            if capture:
                captures.append(capture)

        return captures

    def _parse_single_capture(self, item: Any) -> Optional[CaptureConfig]:
        """Parse a single capture item."""
        if isinstance(item, str):
            # Simple syntax: just variable name
            return CaptureConfig(variable_name=item)

        elif isinstance(item, dict):
            if len(item) != 1:
                return None

            var_name = list(item.keys())[0]
            value = item[var_name]

            if isinstance(value, str):
                # Mapped syntax: {"userId": "id"}
                return CaptureConfig(
                    variable_name=var_name,
                    source_field=value,
                )

            elif isinstance(value, dict):
                # Explicit syntax: {"itemId": {"path": "$.items[0].id"}}
                return CaptureConfig(
                    variable_name=var_name,
                    jsonpath=value.get("path"),
                    match=value.get("match", "first"),
                )

        return None

    def _parse_assert(self, assert_data: Optional[dict]) -> Optional[AssertConfig]:
        """Parse assertion configuration."""
        if not assert_data:
            return None

        return AssertConfig(
            status=assert_data.get("status"),
            body=assert_data.get("body", {}),
            headers=assert_data.get("headers", {}),
        )

    def _parse_loop(
        self, loop_data: Optional[dict], step_num: int, scenario_path: str
    ) -> Optional[LoopConfig]:
        """Parse loop configuration.

        Supports two loop types:
        - Fixed count: loop: {count: 10, interval: 30000}
        - While condition: loop: {while: "$.status != 'finished'", max: 100, interval: 30000}

        Args:
            loop_data: Loop configuration dictionary
            step_num: Step number (for error messages)
            scenario_path: Path to scenario file (for error messages)

        Returns:
            LoopConfig or None if no loop configured

        Raises:
            ScenarioValidationException: Invalid loop configuration
        """
        if not loop_data:
            return None

        if not isinstance(loop_data, dict):
            raise ScenarioValidationException(
                f"Invalid 'loop' in step {step_num} of {scenario_path}: expected dictionary"
            )

        count = loop_data.get("count")
        while_condition = loop_data.get("while")
        max_iterations = loop_data.get("max", 100)
        interval = loop_data.get("interval")

        # Validate: either count OR while, not both
        if count is not None and while_condition is not None:
            raise ScenarioValidationException(
                f"Invalid 'loop' in step {step_num} of {scenario_path}: "
                "cannot specify both 'count' and 'while'"
            )

        # Validate: at least one must be specified
        if count is None and while_condition is None:
            raise ScenarioValidationException(
                f"Invalid 'loop' in step {step_num} of {scenario_path}: "
                "must specify either 'count' or 'while'"
            )

        # Validate count
        if count is not None:
            if not isinstance(count, int) or count < 1:
                raise ScenarioValidationException(
                    f"Invalid 'loop.count' in step {step_num} of {scenario_path}: "
                    "must be a positive integer"
                )

        # Validate while condition - use placeholder if empty
        if while_condition is not None:
            if not isinstance(while_condition, str):
                raise ScenarioValidationException(
                    f"Invalid 'loop.while' in step {step_num} of {scenario_path}: "
                    "must be a string"
                )
            if not while_condition.strip():
                # Use placeholder for empty while condition
                while_condition = "$.status != 'done'"

        # Validate max_iterations
        if not isinstance(max_iterations, int) or max_iterations < 1:
            raise ScenarioValidationException(
                f"Invalid 'loop.max' in step {step_num} of {scenario_path}: "
                "must be a positive integer"
            )

        # Validate interval
        if interval is not None:
            if not isinstance(interval, int) or interval < 0:
                raise ScenarioValidationException(
                    f"Invalid 'loop.interval' in step {step_num} of {scenario_path}: "
                    "must be a non-negative integer (milliseconds)"
                )

        return LoopConfig(
            count=count,
            while_condition=while_condition,
            max_iterations=max_iterations,
            interval=interval,
        )

    def _find_variable_references(self, step: ScenarioStep) -> set[str]:
        """Find all variable references in a step.

        Searches for ${varName} patterns in params, headers, payload, and path.
        """
        references: set[str] = set()

        # Search in params
        self._extract_vars_from_dict(step.params, references)

        # Search in headers
        self._extract_vars_from_dict(step.headers, references)

        # Search in payload
        if step.payload:
            self._extract_vars_from_dict(step.payload, references)

        # Search in path (for method_path type)
        if step.path:
            references.update(VARIABLE_PATTERN.findall(step.path))

        return references

    def _extract_vars_from_dict(self, data: Any, references: set[str]) -> None:
        """Recursively extract variable references from data."""
        if isinstance(data, str):
            references.update(VARIABLE_PATTERN.findall(data))
        elif isinstance(data, dict):
            for value in data.values():
                self._extract_vars_from_dict(value, references)
        elif isinstance(data, list):
            for item in data:
                self._extract_vars_from_dict(item, references)
