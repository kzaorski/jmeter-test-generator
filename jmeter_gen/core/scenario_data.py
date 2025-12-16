"""Data structures for scenario-based test generation (v2).

This module defines dataclasses used for parsing pt_scenario.yaml files,
correlation analysis, and scenario-based JMX generation.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ScenarioSettings:
    """Settings for scenario execution.

    Attributes:
        threads: Number of concurrent threads (default: 1)
        rampup: Ramp-up period in seconds (default: 0)
        loops: Number of iterations per thread (None=auto, 0/-1=infinite, N=fixed)
        duration: Test duration in seconds (optional, used when loops is infinite)
        base_url: Override base URL from OpenAPI spec (optional)
    """

    threads: int = 1
    rampup: int = 0
    loops: Optional[int] = None
    duration: Optional[int] = None
    base_url: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "threads": self.threads,
            "rampup": self.rampup,
            "loops": self.loops,
            "duration": self.duration,
            "base_url": self.base_url,
        }


@dataclass
class CaptureConfig:
    """Configuration for capturing a variable from response.

    Attributes:
        variable_name: Name of the variable to store captured value
        source_field: Field name in response to capture (for mapped syntax)
        jsonpath: Explicit JSONPath expression (for explicit syntax)
        match: Match strategy - "first", "all", or a number (default: "first")
    """

    variable_name: str
    source_field: Optional[str] = None
    jsonpath: Optional[str] = None
    match: str = "first"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "variable_name": self.variable_name,
            "source_field": self.source_field,
            "jsonpath": self.jsonpath,
            "match": self.match,
        }


@dataclass
class AssertConfig:
    """Configuration for response assertions.

    Attributes:
        status: Expected HTTP status code (optional)
        body: Dictionary of field -> expected value assertions
        headers: Dictionary of header -> expected value assertions
        body_contains: List of substrings that must be present in response body
    """

    status: Optional[int] = None
    body: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    body_contains: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status,
            "body": self.body,
            "headers": self.headers,
            "body_contains": self.body_contains,
        }


@dataclass
class FileConfig:
    """Configuration for file upload.

    Attributes:
        path: Path to the file to upload
        param: Form field parameter name
        mime_type: MIME type of the file (optional, auto-detected if not specified)
    """

    path: str
    param: str
    mime_type: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": self.path,
            "param": self.param,
            "mime_type": self.mime_type,
        }


@dataclass
class LoopConfig:
    """Configuration for step-level looping.

    Supports two loop types:
    - Fixed count: Execute step N times
    - While condition: Execute while JSONPath condition is true

    Attributes:
        count: Number of iterations for fixed count loop
        while_condition: JSONPath condition for while loop (e.g. "$.status != 'finished'")
        max_iterations: Safety limit for while loops (default: 100)
        interval: Milliseconds between iterations (optional)
    """

    count: Optional[int] = None
    while_condition: Optional[str] = None
    max_iterations: int = 100
    interval: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "count": self.count,
            "while_condition": self.while_condition,
            "max_iterations": self.max_iterations,
            "interval": self.interval,
        }


@dataclass
class ScenarioStep:
    """A single step in the scenario.

    Attributes:
        name: Display name for the step
        endpoint: Endpoint reference (operationId or "METHOD /path")
        endpoint_type: Type of endpoint - "operation_id", "method_path", "think_time", or "loop_block"
        method: HTTP method (only for method_path type)
        path: URL path (only for method_path type)
        enabled: Whether step is enabled (default: True)
        params: Path and query parameters
        headers: Additional HTTP headers
        payload: Request body (JSON)
        files: List of files to upload
        captures: List of variables to capture from response
        assertions: Response assertions
        loop: Loop configuration for repeating this step
        think_time: Think time in milliseconds (only for think_time type)
        nested_steps: Nested steps for multi-step loops (only for loop_block type)
    """

    name: str
    endpoint: str
    endpoint_type: str  # "operation_id", "method_path", "think_time", or "loop_block"
    method: Optional[str] = None
    path: Optional[str] = None
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    payload: Optional[dict[str, Any]] = None
    files: list[FileConfig] = field(default_factory=list)
    captures: list[CaptureConfig] = field(default_factory=list)
    assertions: Optional[AssertConfig] = None
    loop: Optional[LoopConfig] = None
    think_time: Optional[int] = None
    nested_steps: list["ScenarioStep"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "endpoint": self.endpoint,
            "endpoint_type": self.endpoint_type,
            "method": self.method,
            "path": self.path,
            "enabled": self.enabled,
            "params": self.params,
            "headers": self.headers,
            "payload": self.payload,
            "files": [f.to_dict() for f in self.files],
            "captures": [c.to_dict() for c in self.captures],
            "assertions": self.assertions.to_dict() if self.assertions else None,
            "loop": self.loop.to_dict() if self.loop else None,
            "think_time": self.think_time,
            "nested_steps": [s.to_dict() for s in self.nested_steps],
        }


@dataclass
class ParsedScenario:
    """Parsed pt_scenario.yaml file.

    Attributes:
        name: Scenario name
        description: Optional scenario description
        settings: Execution settings
        variables: Global variables defined in scenario
        steps: List of scenario steps
    """

    name: str
    description: Optional[str]
    settings: ScenarioSettings
    variables: dict[str, Any]
    steps: list[ScenarioStep]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "settings": self.settings.to_dict(),
            "variables": self.variables,
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass
class CorrelationMapping:
    """Mapping between a capture variable and its JSONPath.

    Attributes:
        variable_name: Name of the captured variable
        jsonpath: JSONPath expression to extract value
        source_step: Step index where variable is captured (1-based)
        source_endpoint: Endpoint where variable is captured
        target_steps: List of step indices using this variable
        confidence: Confidence score of the mapping (0.0-1.0)
        match_type: How the match was found (explicit, exact, case_insensitive, suffix, nested)
    """

    variable_name: str
    jsonpath: str
    source_step: int
    source_endpoint: str
    target_steps: list[int] = field(default_factory=list)
    confidence: float = 1.0
    match_type: str = "explicit"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "variable_name": self.variable_name,
            "jsonpath": self.jsonpath,
            "source_step": self.source_step,
            "source_endpoint": self.source_endpoint,
            "target_steps": self.target_steps,
            "confidence": self.confidence,
            "match_type": self.match_type,
        }


@dataclass
class CorrelationResult:
    """Result of correlation analysis.

    Attributes:
        mappings: Successfully resolved correlation mappings
        warnings: List of warning messages (low confidence matches)
        errors: List of error messages (unresolvable captures)
    """

    mappings: list[CorrelationMapping] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if there are any unresolvable captures."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any low-confidence matches."""
        return len(self.warnings) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "mappings": [m.to_dict() for m in self.mappings],
            "warnings": self.warnings,
            "errors": self.errors,
            "has_errors": self.has_errors,
            "has_warnings": self.has_warnings,
        }


@dataclass
class ResolvedPath:
    """Result of short path resolution.

    Attributes:
        full_path: The full path from OpenAPI spec
        method: HTTP method
        match_type: How the path was matched ("exact" or "suffix")
        candidates: Other matching paths (for ambiguous cases)
    """

    full_path: str
    method: str
    match_type: str  # "exact" or "suffix"
    candidates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "full_path": self.full_path,
            "method": self.method,
            "match_type": self.match_type,
            "candidates": self.candidates,
        }
