"""Validator for pt_scenario.yaml scenario files.

This module provides structured validation with error/warning distinction.
Wraps PtScenarioParser to collect validation results as structured issues.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from jmeter_gen.core.ptscenario_parser import PtScenarioParser
from jmeter_gen.core.openapi_parser import OpenAPIParser
from jmeter_gen.exceptions import (
    ScenarioParseException,
    ScenarioValidationException,
    UndefinedVariableException,
    InvalidEndpointFormatException,
)


@dataclass
class ValidationIssue:
    """Single validation issue (error or warning)."""

    level: str  # "error" | "warning"
    category: str  # "yaml", "structure", "endpoints", "variables", "captures", "loops"
    message: str
    location: Optional[str] = None  # step name, step number, etc.


@dataclass
class ValidationResult:
    """Result of scenario validation."""

    scenario_path: str
    scenario_name: Optional[str]
    is_valid: bool  # True if no errors (warnings ok)
    issues: list[ValidationIssue]

    @property
    def errors_count(self) -> int:
        """Count validation errors."""
        return sum(1 for issue in self.issues if issue.level == "error")

    @property
    def warnings_count(self) -> int:
        """Count validation warnings."""
        return sum(1 for issue in self.issues if issue.level == "warning")


class ScenarioValidator:
    """Validate pt_scenario.yaml files with structured error reporting.

    Validates YAML syntax, structure, endpoint existence, variable lifecycle,
    loop configuration, and capture syntax.

    Example:
        >>> validator = ScenarioValidator()
        >>> result = validator.validate("pt_scenario.yaml", "openapi.yaml")
        >>> print(f"Valid: {result.is_valid}")
        >>> for issue in result.issues:
        ...     print(f"[{issue.level.upper()}] {issue.message}")
    """

    def validate(
        self, scenario_path: str, spec_path: Optional[str] = None
    ) -> ValidationResult:
        """Validate scenario file.

        Args:
            scenario_path: Path to pt_scenario.yaml
            spec_path: Optional path to OpenAPI spec for endpoint validation

        Returns:
            ValidationResult with list of issues

        Raises:
            None - all errors collected in result.issues
        """
        issues: list[ValidationIssue] = []
        scenario_name: Optional[str] = None

        # Step 1: Validate file exists
        path = Path(scenario_path)
        if not path.exists():
            issues.append(
                ValidationIssue(
                    level="error",
                    category="yaml",
                    message=f"Scenario file not found: {scenario_path}",
                )
            )
            return ValidationResult(
                scenario_path=scenario_path, scenario_name=None, is_valid=False, issues=issues
            )

        # Step 2: Parse scenario
        parser = PtScenarioParser()
        try:
            scenario = parser.parse(scenario_path)
            scenario_name = scenario.name
        except ScenarioParseException as e:
            issues.append(
                ValidationIssue(
                    level="error",
                    category="yaml" if "YAML" in str(e) else "structure",
                    message=str(e),
                )
            )
            return ValidationResult(
                scenario_path=scenario_path,
                scenario_name=scenario_name,
                is_valid=False,
                issues=issues,
            )
        except (ScenarioValidationException, InvalidEndpointFormatException) as e:
            issues.append(
                ValidationIssue(level="error", category="structure", message=str(e))
            )
            return ValidationResult(
                scenario_path=scenario_path,
                scenario_name=scenario_name,
                is_valid=False,
                issues=issues,
            )

        # Step 3: Get spec info if provided
        available_operation_ids: Optional[list[str]] = None
        available_paths: Optional[dict[str, list[str]]] = None

        if spec_path:
            try:
                spec_parser = OpenAPIParser()
                spec_data = spec_parser.parse(spec_path)
                available_operation_ids = [
                    ep["operationId"] for ep in spec_data["endpoints"] if "operationId" in ep
                ]
                # Build available_paths dict
                available_paths = {}
                for endpoint in spec_data["endpoints"]:
                    path = endpoint.get("path", "")
                    method = endpoint.get("method", "").upper()
                    if path:
                        if path not in available_paths:
                            available_paths[path] = []
                        available_paths[path].append(method)
            except Exception as e:
                issues.append(
                    ValidationIssue(
                        level="error",
                        category="structure",
                        message=f"Failed to parse OpenAPI spec: {e}",
                    )
                )
                return ValidationResult(
                    scenario_path=scenario_path,
                    scenario_name=scenario_name,
                    is_valid=False,
                    issues=issues,
                )

        # Step 4: Run scenario validation against spec
        try:
            warnings = parser.validate(
                scenario,
                available_operation_ids=available_operation_ids,
                available_paths=available_paths,
            )
            # Convert warnings to errors (endpoint not found = blocking error)
            for warning in warnings:
                issues.append(
                    ValidationIssue(level="error", category="endpoints", message=warning)
                )
        except UndefinedVariableException as e:
            issues.append(
                ValidationIssue(
                    level="error", category="variables", message=str(e)
                )
            )

        # Determine if valid (no errors allowed)
        is_valid = not any(issue.level == "error" for issue in issues)

        return ValidationResult(
            scenario_path=scenario_path,
            scenario_name=scenario_name,
            is_valid=is_valid,
            issues=issues,
        )
