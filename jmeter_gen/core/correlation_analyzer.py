"""Correlation analyzer for automatic JSONPath detection (v2).

This module provides functionality to automatically detect JSONPath expressions
for variable captures by analyzing OpenAPI response schemas.
"""

import re
from typing import Any, Optional

from jmeter_gen.core.openapi_parser import OpenAPIParser
from jmeter_gen.core.scenario_data import (
    CaptureConfig,
    CorrelationMapping,
    CorrelationResult,
    ParsedScenario,
    ScenarioStep,
)

# Variable reference pattern
VARIABLE_PATTERN = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class CorrelationAnalyzer:
    """Analyze scenarios and generate correlation mappings.

    This analyzer examines capture definitions in scenarios and automatically
    detects the appropriate JSONPath expressions by analyzing OpenAPI response schemas.

    Example:
        >>> parser = OpenAPIParser()
        >>> spec = parser.parse("openapi.yaml")
        >>> analyzer = CorrelationAnalyzer(parser)
        >>> scenario = PtScenarioParser().parse("pt_scenario.yaml")
        >>> result = analyzer.analyze(scenario)
        >>> for mapping in result.mappings:
        ...     print(f"{mapping.variable_name}: {mapping.jsonpath}")
    """

    def __init__(self, openapi_parser: OpenAPIParser) -> None:
        """Initialize with OpenAPI parser.

        Args:
            openapi_parser: Parser instance with parsed spec data
        """
        self.openapi_parser = openapi_parser

    def analyze(self, scenario: ParsedScenario) -> CorrelationResult:
        """Analyze scenario and generate correlation mappings.

        Args:
            scenario: Parsed scenario to analyze

        Returns:
            CorrelationResult with mappings, warnings, and errors
        """
        mappings: list[CorrelationMapping] = []
        warnings: list[str] = []
        errors: list[str] = []

        # Track captured variables for usage analysis
        captured_vars: dict[str, int] = {}  # var_name -> step_index

        for step_index, step in enumerate(scenario.steps, start=1):
            if not step.enabled or not step.captures:
                continue

            step_mappings = self.analyze_step(step, step_index)

            for mapping in step_mappings:
                if mapping.confidence < 0.8:
                    warnings.append(
                        f"Step [{step_index}]: Low confidence ({mapping.confidence:.0%}) "
                        f"for '{mapping.variable_name}' -> {mapping.jsonpath}"
                    )

                # Track for usage analysis
                captured_vars[mapping.variable_name] = step_index
                mappings.append(mapping)

            # Check for unresolved captures
            for capture in step.captures:
                found = any(m.variable_name == capture.variable_name for m in step_mappings)
                if not found and not capture.jsonpath:
                    errors.append(
                        f"Step [{step_index}]: Could not resolve JSONPath for "
                        f"capture '{capture.variable_name}'"
                    )

        # Analyze variable usage across steps
        self._analyze_variable_usage(scenario, mappings, captured_vars)

        return CorrelationResult(
            mappings=mappings,
            warnings=warnings,
            errors=errors,
        )

    def analyze_step(
        self, step: ScenarioStep, step_index: int
    ) -> list[CorrelationMapping]:
        """Analyze captures for a single step.

        Args:
            step: Scenario step to analyze
            step_index: 1-based step index

        Returns:
            List of correlation mappings for this step
        """
        mappings: list[CorrelationMapping] = []

        # Get response schema for this endpoint
        schema = self._get_response_schema(step)

        # Build field index from schema
        field_index: dict[str, str] = {}
        if schema:
            field_index = self._build_field_index(schema)

        for capture in step.captures:
            mapping = self._match_capture(capture, field_index, step, step_index)
            if mapping:
                mappings.append(mapping)

        return mappings

    def _get_response_schema(self, step: ScenarioStep) -> Optional[dict[str, Any]]:
        """Get response schema for endpoint."""
        if step.endpoint_type == "operation_id":
            return self.openapi_parser.extract_response_schema(
                operation_id=step.endpoint
            )
        elif step.endpoint_type == "method_path" and step.method and step.path:
            return self.openapi_parser.extract_response_schema(
                method=step.method,
                path=step.path,
            )
        return None

    def _build_field_index(
        self, schema: dict[str, Any], prefix: str = "$"
    ) -> dict[str, str]:
        """Build index mapping field names to JSONPaths.

        Recursively traverses schema to build a flat index of all fields
        and their JSONPath expressions.

        Args:
            schema: JSON Schema object
            prefix: Current JSONPath prefix

        Returns:
            Dictionary mapping field names to JSONPaths
            Example: {"id": "$.id", "userId": "$.user.id", "name": "$.user.name"}
        """
        index: dict[str, str] = {}
        self._traverse_schema(schema, prefix, index)
        return index

    def _traverse_schema(
        self,
        schema: dict[str, Any],
        prefix: str,
        index: dict[str, str],
        depth: int = 0,
    ) -> None:
        """Recursively traverse schema to build field index."""
        # Limit recursion depth to prevent infinite loops
        if depth > 10:
            return

        schema_type = schema.get("type", "object")

        if schema_type == "object":
            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                prop_path = f"{prefix}.{prop_name}"

                # Add this field to index
                index[prop_name] = prop_path

                # Also add with full path as key for disambiguation
                full_key = prop_path.replace("$.", "").replace(".", "_")
                if full_key != prop_name:
                    index[full_key] = prop_path

                # Recurse into nested objects/arrays
                if isinstance(prop_schema, dict):
                    prop_type = prop_schema.get("type", "")
                    if prop_type == "object":
                        self._traverse_schema(prop_schema, prop_path, index, depth + 1)
                    elif prop_type == "array":
                        items = prop_schema.get("items", {})
                        if isinstance(items, dict):
                            # Use [*] for array access
                            array_path = f"{prop_path}[*]"
                            # Also add [0] for first item
                            first_path = f"{prop_path}[0]"
                            self._traverse_schema(items, array_path, index, depth + 1)
                            # Add first item paths too
                            self._traverse_schema(items, first_path, index, depth + 1)

        elif schema_type == "array":
            items = schema.get("items", {})
            if isinstance(items, dict):
                array_path = f"{prefix}[*]"
                self._traverse_schema(items, array_path, index, depth + 1)

    def _match_capture(
        self,
        capture: CaptureConfig,
        field_index: dict[str, str],
        step: ScenarioStep,
        step_index: int,
    ) -> Optional[CorrelationMapping]:
        """Match capture variable to schema field using priority algorithm.

        Priority order (stops at first match):
        1. Explicit JSONPath (user specified)
        2. Source field mapping (user specified different name)
        3. Exact match (variable name == field name)
        4. Case-insensitive match
        5. ID suffix removal (userId -> user, id)
        6. Nested search

        Args:
            capture: Capture configuration
            field_index: Field name to JSONPath mapping
            step: Scenario step
            step_index: 1-based step index

        Returns:
            CorrelationMapping if match found, None otherwise
        """
        var_name = capture.variable_name

        # 1. Explicit JSONPath
        if capture.jsonpath:
            return CorrelationMapping(
                variable_name=var_name,
                jsonpath=capture.jsonpath,
                source_step=step_index,
                source_endpoint=step.endpoint,
                confidence=1.0,
                match_type="explicit",
            )

        # 2. Source field mapping
        if capture.source_field:
            if capture.source_field in field_index:
                return CorrelationMapping(
                    variable_name=var_name,
                    jsonpath=field_index[capture.source_field],
                    source_step=step_index,
                    source_endpoint=step.endpoint,
                    confidence=1.0,
                    match_type="mapped",
                )
            # Try as JSONPath-like dotted path
            dotted_path = f"$.{capture.source_field}"
            return CorrelationMapping(
                variable_name=var_name,
                jsonpath=dotted_path,
                source_step=step_index,
                source_endpoint=step.endpoint,
                confidence=0.9,
                match_type="mapped_inferred",
            )

        # 3. Exact match
        if var_name in field_index:
            return CorrelationMapping(
                variable_name=var_name,
                jsonpath=field_index[var_name],
                source_step=step_index,
                source_endpoint=step.endpoint,
                confidence=1.0,
                match_type="exact",
            )

        # 4. Case-insensitive match
        var_lower = var_name.lower()
        for field_name, jsonpath in field_index.items():
            if field_name.lower() == var_lower:
                return CorrelationMapping(
                    variable_name=var_name,
                    jsonpath=jsonpath,
                    source_step=step_index,
                    source_endpoint=step.endpoint,
                    confidence=0.9,
                    match_type="case_insensitive",
                )

        # 5. ID suffix removal (userId -> id, user_id -> id)
        if var_name.lower().endswith("id"):
            # Try just "id"
            if "id" in field_index:
                return CorrelationMapping(
                    variable_name=var_name,
                    jsonpath=field_index["id"],
                    source_step=step_index,
                    source_endpoint=step.endpoint,
                    confidence=0.8,
                    match_type="id_suffix",
                )

        # 6. Nested search - look for field name as suffix
        for field_name, jsonpath in field_index.items():
            # Check if field_name ends with var_name (case insensitive)
            if field_name.lower().endswith(var_lower):
                return CorrelationMapping(
                    variable_name=var_name,
                    jsonpath=jsonpath,
                    source_step=step_index,
                    source_endpoint=step.endpoint,
                    confidence=0.7,
                    match_type="nested",
                )

        # No match found - create fallback with direct path assumption
        # This allows JMX generation to proceed with a reasonable default
        return CorrelationMapping(
            variable_name=var_name,
            jsonpath=f"$.{var_name}",
            source_step=step_index,
            source_endpoint=step.endpoint,
            confidence=0.5,
            match_type="fallback",
        )

    def _analyze_variable_usage(
        self,
        scenario: ParsedScenario,
        mappings: list[CorrelationMapping],
        captured_vars: dict[str, int],
    ) -> None:
        """Find all steps that use each captured variable.

        Updates mappings in place with target_steps information.
        """
        for mapping in mappings:
            target_steps: list[int] = []

            for step_index, step in enumerate(scenario.steps, start=1):
                # Skip steps before or at capture step
                if step_index <= mapping.source_step:
                    continue

                # Check if this step uses the variable
                if self._step_uses_variable(step, mapping.variable_name):
                    target_steps.append(step_index)

            mapping.target_steps = target_steps

    def _step_uses_variable(self, step: ScenarioStep, var_name: str) -> bool:
        """Check if a step uses a specific variable."""
        pattern = f"${{{var_name}}}"

        # Check path
        if step.path and pattern in step.path:
            return True

        # Check params
        if self._dict_contains_pattern(step.params, pattern):
            return True

        # Check headers
        if self._dict_contains_pattern(step.headers, pattern):
            return True

        # Check payload
        if step.payload and self._dict_contains_pattern(step.payload, pattern):
            return True

        return False

    def _dict_contains_pattern(self, data: Any, pattern: str) -> bool:
        """Recursively check if data contains pattern."""
        if isinstance(data, str):
            return pattern in data
        elif isinstance(data, dict):
            for value in data.values():
                if self._dict_contains_pattern(value, pattern):
                    return True
        elif isinstance(data, list):
            for item in data:
                if self._dict_contains_pattern(item, pattern):
                    return True
        return False
