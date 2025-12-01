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

# Pattern to extract JSONPath field from while condition
# e.g., "$.status != 'finished'" -> "status"
JSONPATH_FIELD_PATTERN = re.compile(r"\$\.([a-zA-Z_][a-zA-Z0-9_]*)")


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
            if not step.enabled:
                continue

            # Process explicit captures
            if step.captures:
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

            # Process auto-capture from while condition
            if step.loop and step.loop.while_condition:
                auto_capture_mapping = self._create_auto_capture_mapping(
                    step, step_index
                )
                if auto_capture_mapping:
                    # Don't duplicate if already captured explicitly
                    if auto_capture_mapping.variable_name not in captured_vars:
                        captured_vars[auto_capture_mapping.variable_name] = step_index
                        mappings.append(auto_capture_mapping)

            # Process captures from nested steps in loop_block
            if step.endpoint_type == "loop_block" and step.nested_steps:
                for nested_step in step.nested_steps:
                    if nested_step.enabled and nested_step.captures:
                        nested_mappings = self.analyze_step(nested_step, step_index)
                        for mapping in nested_mappings:
                            if mapping.confidence < 0.8:
                                warnings.append(
                                    f"Step [{step_index}]: Low confidence ({mapping.confidence:.0%}) "
                                    f"for '{mapping.variable_name}' -> {mapping.jsonpath}"
                                )
                            if mapping.variable_name not in captured_vars:
                                captured_vars[mapping.variable_name] = step_index
                                mappings.append(mapping)

        # Analyze variable usage across steps
        self._analyze_variable_usage(scenario, mappings, captured_vars)

        return CorrelationResult(
            mappings=mappings,
            warnings=warnings,
            errors=errors,
        )

    def _create_auto_capture_mapping(
        self, step: ScenarioStep, step_index: int
    ) -> Optional[CorrelationMapping]:
        """Create mapping for auto-captured variable from while condition.

        Args:
            step: Step with while loop condition
            step_index: 1-based step index

        Returns:
            CorrelationMapping if variable found in condition, None otherwise
        """
        if not step.loop or not step.loop.while_condition:
            return None

        match = JSONPATH_FIELD_PATTERN.search(step.loop.while_condition)
        if not match:
            return None

        var_name = match.group(1)
        jsonpath = f"$.{var_name}"

        return CorrelationMapping(
            variable_name=var_name,
            jsonpath=jsonpath,
            source_step=step_index,
            source_endpoint=step.endpoint,
            confidence=1.0,  # Auto-capture is always exact
            match_type="auto_capture",
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

        # Check endpoint (for METHOD /path/{var} format)
        if step.endpoint and pattern in step.endpoint:
            return True

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

        # Check nested steps (for loop_block)
        if step.nested_steps:
            for nested in step.nested_steps:
                if self._step_uses_variable(nested, var_name):
                    return True

        # Check if requestBody schema from OpenAPI has matching field
        # This catches auto-generated payload from OpenAPI schema
        request_schema = self._get_request_body_schema(step)
        if request_schema and self._schema_has_matching_field(request_schema, var_name):
            return True

        return False

    def _get_request_body_schema(self, step: ScenarioStep) -> Optional[dict[str, Any]]:
        """Get requestBody schema from OpenAPI for this endpoint.

        Args:
            step: Scenario step

        Returns:
            Request body schema dict or None
        """
        if step.endpoint_type == "operation_id":
            endpoint = self.openapi_parser.get_endpoint_by_operation_id(step.endpoint)
        elif step.endpoint_type == "method_path" and step.method and step.path:
            endpoint = self.openapi_parser.get_endpoint_by_method_path(
                step.method, step.path
            )
        else:
            return None

        if not endpoint:
            return None

        operation = endpoint.get("operation")
        if not operation:
            return None

        # OpenAPI 3.0: requestBody.content.application/json.schema
        if "requestBody" in operation:
            request_body = operation["requestBody"]
            content = request_body.get("content", {})
            if content:
                # Try application/json first, then any content type
                for content_type in ["application/json", *content.keys()]:
                    if content_type in content:
                        media_type = content[content_type]
                        if "schema" in media_type:
                            return self.openapi_parser._resolve_schema_ref(
                                media_type["schema"]
                            )
            return None

        # Swagger 2.0: parameters with in=body
        parameters = operation.get("parameters", [])
        for param in parameters:
            if param.get("in") == "body" and "schema" in param:
                return self.openapi_parser._resolve_schema_ref(param["schema"])

        return None

    def _schema_has_matching_field(self, schema: dict[str, Any], var_name: str) -> bool:
        """Check if schema has a field matching the variable name.

        Args:
            schema: JSON Schema object
            var_name: Variable name to match

        Returns:
            True if schema has a matching field
        """
        field_index = self._build_field_index(schema)
        var_lower = var_name.lower()
        for field_name in field_index.keys():
            if field_name.lower() == var_lower:
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
