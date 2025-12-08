"""MCP Server for JMeter Test Generator.

This module provides a Model Context Protocol (MCP) server that exposes
JMeter test generation capabilities to GitHub Copilot and other AI assistants.

Supports change detection with detect_changes, auto_update options.
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from jmeter_gen.core.jmx_generator import JMXGenerator
from jmeter_gen.core.jmx_updater import JMXUpdater
from jmeter_gen.core.jmx_validator import JMXValidator
from jmeter_gen.core.openapi_parser import OpenAPIParser
from jmeter_gen.core.project_analyzer import ProjectAnalyzer
from jmeter_gen.core.snapshot_manager import SnapshotManager
from jmeter_gen.core.spec_comparator import SpecComparator
from jmeter_gen.exceptions import JMeterGenException

# v2 imports
from jmeter_gen.core.ptscenario_parser import PtScenarioParser
from jmeter_gen.core.correlation_analyzer import CorrelationAnalyzer
from jmeter_gen.core.scenario_jmx_generator import ScenarioJMXGenerator
from jmeter_gen.core.scenario_mermaid import (
    generate_mermaid_diagram,
    generate_text_visualization,
)

# v3 imports
import yaml
from jmeter_gen.core.scenario_wizard import ScenarioWizard
from jmeter_gen.core.scenario_validator import ScenarioValidator


# Initialize MCP Server
app = Server("jmeter-test-generator")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools for JMeter test generation.

    Returns:
        List of available tools with their schemas
    """
    return [
        Tool(
            name="analyze_project_for_jmeter",
            description=(
                "Use this tool FIRST when user wants JMeter tests for an API project. "
                "Discovers OpenAPI/Swagger specs in the current directory (default) or specified path. "
                "Returns spec location, API title, endpoint count, and recommended actions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to project directory to analyze (default: current directory)",
                        "default": ".",
                    },
                    "detect_changes": {
                        "type": "boolean",
                        "description": "Enable change detection from snapshot (default: true)",
                        "default": True,
                    },
                    "jmx_path": {
                        "type": "string",
                        "description": "JMX file path for snapshot lookup (optional)",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="generate_jmx_from_openapi",
            description=(
                "Generate a JMeter JMX test plan from an OpenAPI specification. "
                "Parses the OpenAPI spec, creates HTTP samplers for each endpoint, "
                "configures thread groups with load parameters, and validates the output. "
                "Supports both OpenAPI 3.0.x and Swagger 2.0 formats. "
                "Supports auto_update to update existing JMX when spec changes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "spec_path": {
                        "type": "string",
                        "description": "Path to OpenAPI specification file (YAML or JSON)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output path for generated JMX file",
                        "default": "test.jmx",
                    },
                    "threads": {
                        "type": "integer",
                        "description": "Number of virtual users/threads",
                        "default": 10,
                        "minimum": 1,
                    },
                    "rampup": {
                        "type": "integer",
                        "description": "Ramp-up period in seconds",
                        "default": 5,
                        "minimum": 0,
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Test duration in seconds",
                        "default": 60,
                        "minimum": 1,
                    },
                    "base_url_override": {
                        "type": "string",
                        "description": "Override base URL from spec (e.g., http://localhost:8080)",
                    },
                    "endpoints": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by operationId (optional)",
                    },
                    "auto_update": {
                        "type": "boolean",
                        "description": "Auto-update existing JMX if changes detected (default: false)",
                        "default": False,
                    },
                    "force_new": {
                        "type": "boolean",
                        "description": "Force new JMX generation (skip update, regenerate)",
                        "default": False,
                    },
                    "no_snapshot": {
                        "type": "boolean",
                        "description": "Don't save snapshot after generation (default: false)",
                        "default": False,
                    },
                },
                "required": ["spec_path"],
            },
        ),
        Tool(
            name="generate_scenario_jmx",
            description=(
                "Generate a JMeter JMX test plan from a pt_scenario.yaml file (v2). "
                "Creates sequential HTTP samplers with JSONPostProcessor elements "
                "for variable extraction and correlation. Automatically detects "
                "JSONPath expressions from OpenAPI response schemas."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "scenario_path": {
                        "type": "string",
                        "description": "Path to pt_scenario.yaml file",
                    },
                    "spec_path": {
                        "type": "string",
                        "description": "Path to OpenAPI specification file (YAML or JSON)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output path for generated JMX file",
                        "default": "scenario-test.jmx",
                    },
                    "base_url_override": {
                        "type": "string",
                        "description": "Override base URL from scenario/spec",
                    },
                },
                "required": ["scenario_path", "spec_path"],
            },
        ),
        Tool(
            name="validate_jmx",
            description=(
                "Validate an existing JMeter JMX test plan file. "
                "Checks structure, configuration, and provides recommendations "
                "for improvement. Returns validation status, issues found, "
                "and structure information."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "jmx_path": {
                        "type": "string",
                        "description": "Path to JMX file to validate",
                    },
                },
                "required": ["jmx_path"],
            },
        ),
        Tool(
            name="visualize_scenario",
            description=(
                "Parse and visualize a pt_scenario.yaml file showing the test flow. "
                "Returns structured JSON data, ASCII text visualization, and Mermaid "
                "diagram code. Optionally performs correlation analysis if spec_path "
                "is provided to show variable flows between steps."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "scenario_path": {
                        "type": "string",
                        "description": "Path to pt_scenario.yaml file",
                    },
                    "spec_path": {
                        "type": "string",
                        "description": "Path to OpenAPI spec for correlation analysis (optional)",
                    },
                },
                "required": ["scenario_path"],
            },
        ),
        # v3 scenario builder tools
        Tool(
            name="list_endpoints",
            description=(
                "Use this tool FIRST when user wants to create a JMeter test scenario. "
                "Lists all available API endpoints from an OpenAPI/Swagger spec. "
                "Essential for understanding what endpoints are available before "
                "building a test scenario. Returns method, path, operationId, and summary."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "spec_path": {
                        "type": "string",
                        "description": "Path to OpenAPI specification file (YAML or JSON)",
                    },
                },
                "required": ["spec_path"],
            },
        ),
        Tool(
            name="suggest_captures",
            description=(
                "Use this tool to find variables to capture from API responses "
                "(e.g., IDs, tokens, status fields for polling). "
                "Analyzes endpoint response schema and suggests JSONPath expressions. "
                "Essential for scenarios that need to pass data between steps or "
                "poll until a condition is met (e.g., status == 'completed')."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "spec_path": {
                        "type": "string",
                        "description": "Path to OpenAPI specification file (YAML or JSON)",
                    },
                    "endpoint": {
                        "type": "string",
                        "description": "Endpoint identifier: operationId (e.g., 'createUser') or METHOD /path (e.g., 'POST /users')",
                    },
                },
                "required": ["spec_path", "endpoint"],
            },
        ),
        Tool(
            name="build_scenario",
            description=(
                "Use this tool when the user describes a test scenario in natural language, "
                "such as 'call /trigger then poll /status until completed' or "
                "'create user, then get user details'. "
                "Builds a pt_scenario.yaml file with sequential steps, variable capture, "
                "and loop/polling support (e.g., while: '$.status != completed'). "
                "Supports both operationId and 'METHOD /path' endpoint formats."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "spec_path": {
                        "type": "string",
                        "description": "Path to OpenAPI specification file (YAML or JSON)",
                    },
                    "steps": {
                        "type": "array",
                        "description": "List of scenario steps",
                        "items": {
                            "type": "object",
                            "properties": {
                                "endpoint": {
                                    "type": "string",
                                    "description": "Endpoint: operationId or 'METHOD /path'",
                                },
                                "name": {
                                    "type": "string",
                                    "description": "Step name (optional, auto-generated if not provided)",
                                },
                                "capture": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Variables to capture from response (e.g., ['userId', 'token'])",
                                },
                                "think_time": {
                                    "type": "integer",
                                    "description": "Think time in milliseconds after this step",
                                },
                                "loop": {
                                    "type": "object",
                                    "description": "Loop configuration: {count: N} or {while: '$.condition'}",
                                },
                            },
                            "required": ["endpoint"],
                        },
                    },
                    "name": {
                        "type": "string",
                        "description": "Scenario name (default: 'Test Scenario')",
                    },
                    "description": {
                        "type": "string",
                        "description": "Scenario description (optional)",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output file path (default: 'pt_scenario.yaml')",
                    },
                    "settings": {
                        "type": "object",
                        "description": "Test settings: threads, rampup, duration, base_url",
                        "properties": {
                            "threads": {"type": "integer"},
                            "rampup": {"type": "integer"},
                            "duration": {"type": "integer"},
                            "base_url": {"type": "string"},
                        },
                    },
                },
                "required": ["spec_path", "steps"],
            },
        ),
        Tool(
            name="validate_scenario",
            description=(
                "Validate a pt_scenario.yaml file BEFORE generating JMX. "
                "Use this tool after creating or modifying a scenario to catch errors early. "
                "Checks: YAML syntax, required fields, endpoint existence in spec, "
                "variable lifecycle (undefined usage), loop configuration, capture syntax. "
                "Returns structured validation report with errors (blocking) and warnings. "
                "RECOMMENDED: Always validate before calling generate_scenario_jmx."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "scenario_path": {
                        "type": "string",
                        "description": "Path to pt_scenario.yaml file",
                    },
                    "spec_path": {
                        "type": "string",
                        "description": "Path to OpenAPI spec for endpoint validation (optional, auto-detected)",
                    },
                },
                "required": ["scenario_path"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle tool calls from MCP clients.

    Args:
        name: Name of the tool to execute
        arguments: Tool arguments as dictionary

    Returns:
        List of TextContent with tool execution results

    Raises:
        ValueError: If tool name is not recognized
    """
    if name == "analyze_project_for_jmeter":
        return await _analyze_project(arguments)
    elif name == "generate_jmx_from_openapi":
        return await _generate_jmx(arguments)
    elif name == "generate_scenario_jmx":
        return await _generate_scenario_jmx(arguments)
    elif name == "validate_jmx":
        return await _validate_jmx(arguments)
    elif name == "visualize_scenario":
        return await _visualize_scenario(arguments)
    elif name == "list_endpoints":
        return await _list_endpoints(arguments)
    elif name == "suggest_captures":
        return await _suggest_captures(arguments)
    elif name == "build_scenario":
        return await _build_scenario(arguments)
    elif name == "validate_scenario":
        return await _validate_scenario_tool(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def _analyze_project(arguments: Dict[str, Any]) -> List[TextContent]:
    """Analyze project for OpenAPI specifications.

    Args:
        arguments: Dictionary with optional 'project_path', 'detect_changes', 'jmx_path' keys

    Returns:
        List with single TextContent containing analysis results
    """
    try:
        project_path = arguments.get("project_path", ".")
        detect_changes = arguments.get("detect_changes", True)
        jmx_path = arguments.get("jmx_path")

        analyzer = ProjectAnalyzer()

        # Use change detection if enabled
        if detect_changes:
            result = analyzer.analyze_with_change_detection(project_path, jmx_path)
        else:
            result = analyzer.analyze_project(project_path)

        if not result["openapi_spec_found"]:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "error": "No OpenAPI specification found in the project.",
                            "searched_path": str(Path(project_path).absolute()),
                        },
                        indent=2,
                    ),
                )
            ]

        # Format successful result
        response = {
            "success": True,
            "spec_found": True,
            "spec_path": result["spec_path"],
            "spec_format": result["spec_format"],
            "api_title": result["api_title"],
            "endpoints_count": result["endpoints_count"],
            "base_url": result.get("base_url", ""),
            "recommended_jmx_name": result["recommended_jmx_name"],
            "next_step": f"Use generate_jmx_from_openapi with spec_path: {result['spec_path']}",
        }

        # v2: Check for scenario file
        scenario_path = analyzer.find_scenario_file(project_path)
        if scenario_path:
            try:
                scenario_parser = PtScenarioParser()
                scenario = scenario_parser.parse(scenario_path)
                response["scenario"] = {
                    "path": scenario_path,
                    "name": scenario.name,
                    "steps_count": len(scenario.steps),
                }
                response["next_step"] = (
                    f"Scenario file found. Use generate_scenario_jmx with "
                    f"scenario_path: {scenario_path} and spec_path: {result['spec_path']}"
                )
            except Exception:
                # If scenario parsing fails, just report the path
                response["scenario"] = {
                    "path": scenario_path,
                    "name": None,
                    "steps_count": None,
                    "parse_error": True,
                }
                response["next_step"] = (
                    f"Scenario file found but has errors. Fix {scenario_path} or "
                    f"use generate_jmx_from_openapi with spec_path: {result['spec_path']}"
                )

        # Add multi-spec information if available
        available_specs = result.get("available_specs", [])
        if result.get("multiple_specs_found") and len(available_specs) > 1:
            response["multiple_specs_found"] = True
            response["available_specs"] = [
                {"spec_path": s["spec_path"], "format": s["format"]}
                for s in available_specs
            ]
            response["note"] = (
                f"Found {len(available_specs)} OpenAPI specifications. "
                "The recommended spec is used by default. "
                "To use a different spec, provide its path in generate_jmx_from_openapi."
            )

        # Add change detection results if available
        if detect_changes:
            response["change_detection"] = {
                "snapshot_exists": result.get("snapshot_exists", False),
                "changes_detected": result.get("changes_detected", False),
            }

            if result.get("changes_detected") and result.get("spec_diff"):
                diff = result["spec_diff"]
                response["change_detection"]["summary"] = diff.summary
                response["change_detection"]["added_endpoints"] = [
                    {"method": ep.method, "path": ep.path}
                    for ep in diff.added_endpoints
                ]
                response["change_detection"]["removed_endpoints"] = [
                    {"method": ep.method, "path": ep.path}
                    for ep in diff.removed_endpoints
                ]
                response["change_detection"]["modified_endpoints"] = [
                    {"method": ep.method, "path": ep.path, "changes": ep.changes}
                    for ep in diff.modified_endpoints
                ]
                # Only override next_step if no scenario was found
                if "scenario" not in response:
                    response["next_step"] = (
                        "Changes detected. Use generate_jmx_from_openapi with auto_update=true "
                        f"to update existing JMX, or force_new=true to regenerate."
                    )
            elif not result.get("snapshot_exists"):
                # Only override next_step if no scenario was found
                if "scenario" not in response:
                    response["next_step"] = (
                        f"No snapshot found. Use generate_jmx_from_openapi with spec_path: "
                        f"{result['spec_path']} to generate JMX and create snapshot."
                    )

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except (OSError, ValueError, KeyError) as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    indent=2,
                ),
            )
        ]


async def _generate_jmx(arguments: Dict[str, Any]) -> List[TextContent]:
    """Generate JMX file from OpenAPI specification.

    Args:
        arguments: Dictionary with generation parameters

    Returns:
        List with single TextContent containing generation results
    """
    try:
        # Extract and validate required parameters
        spec_path = arguments.get("spec_path")
        if not spec_path:
            raise ValueError("spec_path is required")

        # Extract optional parameters with defaults
        output_path = arguments.get("output_path", "test.jmx")
        threads = arguments.get("threads", 10)
        rampup = arguments.get("rampup", 5)
        duration = arguments.get("duration", 60)
        base_url_override = arguments.get("base_url_override")
        endpoints = arguments.get("endpoints")

        # Extract change detection parameters
        auto_update = arguments.get("auto_update", False)
        force_new = arguments.get("force_new", False)
        no_snapshot = arguments.get("no_snapshot", False)

        # Verify spec file exists
        spec_file = Path(spec_path)
        if not spec_file.exists():
            raise FileNotFoundError(f"OpenAPI spec file not found: {spec_path}")

        # Parse OpenAPI spec
        parser = OpenAPIParser()
        spec_data = parser.parse(str(spec_file))

        # Determine base URL (override or from spec)
        base_url = base_url_override if base_url_override else spec_data["base_url"]

        # Check for auto-update scenario
        output_file = Path(output_path)
        if output_file.exists() and not force_new and auto_update:
            manager = SnapshotManager(".")
            snapshot = manager.load_snapshot(output_path)

            if snapshot:
                # Compare and auto-update
                snapshot_spec_data = {
                    "endpoints": snapshot.get("endpoints", []),
                    "version": snapshot.get("spec", {}).get("api_version", ""),
                }
                comparator = SpecComparator()
                diff = comparator.compare(snapshot_spec_data, spec_data)

                if diff.has_changes:
                    updater = JMXUpdater(".")
                    update_result = updater.update_jmx(output_path, diff, spec_data)

                    if update_result.success:
                        # Save new snapshot
                        snapshot_saved = None
                        if not no_snapshot:
                            snapshot_saved = manager.save_snapshot(
                                spec_path, output_path, spec_data
                            )

                        response = {
                            "success": True,
                            "mode": "updated",
                            "jmx_path": output_path,
                            "api_title": spec_data.get("title", "Unknown API"),
                            "api_version": spec_data.get("version", "Unknown"),
                            "changes_applied": update_result.changes_applied,
                            "backup_path": update_result.backup_path,
                            "warnings": update_result.warnings,
                            "snapshot_saved": snapshot_saved,
                            "next_steps": [
                                "Review updated JMX file in JMeter GUI",
                                "Run the test using: jmeter -n -t " + output_path + " -l results.jtl",
                            ],
                        }
                        return [TextContent(type="text", text=json.dumps(response, indent=2))]
                else:
                    # No changes
                    response = {
                        "success": True,
                        "mode": "no_changes",
                        "jmx_path": output_path,
                        "message": "No API changes detected. JMX file is up to date.",
                    }
                    return [TextContent(type="text", text=json.dumps(response, indent=2))]

        # Generate JMX (new or forced regeneration)
        generator = JMXGenerator()
        result = generator.generate(
            spec_data=spec_data,
            output_path=output_path,
            base_url=base_url,
            endpoints=endpoints,
            threads=threads,
            rampup=rampup,
            duration=duration,
        )

        if not result["success"]:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "error": "JMX generation failed",
                        },
                        indent=2,
                    ),
                )
            ]

        # Save snapshot unless disabled
        snapshot_saved = None
        if not no_snapshot:
            try:
                manager = SnapshotManager(".")
                snapshot_saved = manager.save_snapshot(spec_path, output_path, spec_data)
            except (OSError, PermissionError):
                pass  # Non-critical failure - snapshot save failed

        # Validate generated JMX
        validator = JMXValidator()
        validation_result = validator.validate(output_path)

        # Format successful result
        response = {
            "success": True,
            "mode": "generated",
            "jmx_path": result["jmx_path"],
            "api_title": spec_data.get("title", "Unknown API"),
            "api_version": spec_data.get("version", "Unknown"),
            "samplers_created": result["samplers_created"],
            "assertions_added": result["assertions_added"],
            "configuration": {
                "threads": result["threads"],
                "rampup": result["rampup"],
                "duration": result["duration"],
                "base_url": base_url,
            },
            "validation": {
                "valid": validation_result["valid"],
                "issues": validation_result.get("issues", []),
                "recommendations": validation_result.get("recommendations", []),
            },
            "snapshot_saved": snapshot_saved,
            "next_steps": [
                "Open the JMX file in JMeter GUI for review",
                "Run the test using: jmeter -n -t " + output_path + " -l results.jtl",
            ],
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except JMeterGenException as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    indent=2,
                ),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    indent=2,
                ),
            )
        ]


async def _generate_scenario_jmx(arguments: Dict[str, Any]) -> List[TextContent]:
    """Generate JMX file from pt_scenario.yaml (v2).

    Args:
        arguments: Dictionary with scenario generation parameters

    Returns:
        List with single TextContent containing generation results
    """
    try:
        # Extract required parameters
        scenario_path = arguments.get("scenario_path")
        spec_path = arguments.get("spec_path")

        if not scenario_path:
            raise ValueError("scenario_path is required")
        if not spec_path:
            raise ValueError("spec_path is required")

        # Extract optional parameters
        output_path = arguments.get("output_path", "scenario-test.jmx")
        base_url_override = arguments.get("base_url_override")

        # Verify files exist
        if not Path(scenario_path).exists():
            raise FileNotFoundError(f"Scenario file not found: {scenario_path}")
        if not Path(spec_path).exists():
            raise FileNotFoundError(f"OpenAPI spec file not found: {spec_path}")

        # Parse OpenAPI spec
        parser = OpenAPIParser()
        spec_data = parser.parse(spec_path)

        # Parse scenario
        scenario_parser = PtScenarioParser()
        scenario = scenario_parser.parse(scenario_path)

        # Auto-generate output filename from scenario name if not provided
        if not output_path or output_path == "scenario-test.jmx":
            # Sanitize scenario name for filename
            safe_name = scenario.name.lower().replace(" ", "-").replace("_", "-")
            # Remove any characters that aren't alphanumeric or hyphens
            safe_name = "".join(c for c in safe_name if c.isalnum() or c == "-")
            # Remove consecutive hyphens
            while "--" in safe_name:
                safe_name = safe_name.replace("--", "-")
            safe_name = safe_name.strip("-")
            if safe_name:
                output_path = f"{safe_name}-test.jmx"
            else:
                output_path = "scenario-test.jmx"

        # Run correlation analysis
        correlation_analyzer = CorrelationAnalyzer(parser)
        correlation_result = correlation_analyzer.analyze(scenario)

        # Determine base URL
        base_url = (
            base_url_override
            or scenario.settings.base_url
            or spec_data.get("base_url", "http://localhost:8080")
        )

        # Generate JMX
        generator = ScenarioJMXGenerator(parser)
        result = generator.generate(
            scenario=scenario,
            output_path=output_path,
            base_url=base_url,
            correlation_result=correlation_result,
        )

        if not result["success"]:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"success": False, "error": "Scenario JMX generation failed"},
                        indent=2,
                    ),
                )
            ]

        # Auto-validate generated JMX
        validator = JMXValidator()
        validation_result = validator.validate(output_path)

        # Format response
        response = {
            "success": True,
            "mode": "scenario",
            "jmx_path": result["jmx_path"],
            "scenario_name": scenario.name,
            "steps_count": len(scenario.steps),
            "samplers_created": result["samplers_created"],
            "extractors_created": result["extractors_created"],
            "assertions_created": result["assertions_created"],
            "configuration": {
                "threads": scenario.settings.threads,
                "rampup": scenario.settings.rampup,
                "duration": scenario.settings.duration,
                "base_url": base_url,
            },
            "correlation": {
                "mappings_count": len(correlation_result.mappings),
                "warnings": correlation_result.warnings,
                "errors": correlation_result.errors,
            },
            "validation": {
                "is_valid": validation_result["valid"],
                "issues_count": len(validation_result.get("issues", [])),
                "issues": validation_result.get("issues", []),
            },
            "next_steps": [
                "Open the JMX file in JMeter GUI for review",
                f"Run the test using: jmeter -n -t {output_path} -l results.jtl",
            ],
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except JMeterGenException as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "error": str(e), "error_type": type(e).__name__},
                    indent=2,
                ),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "error": str(e), "error_type": type(e).__name__},
                    indent=2,
                ),
            )
        ]


async def _validate_jmx(arguments: Dict[str, Any]) -> List[TextContent]:
    """Validate JMX file structure and configuration.

    Args:
        arguments: Dictionary with 'jmx_path' key

    Returns:
        List with single TextContent containing validation results
    """
    try:
        jmx_path = arguments.get("jmx_path")
        if not jmx_path:
            raise ValueError("jmx_path is required")

        # Verify file exists
        if not Path(jmx_path).exists():
            raise FileNotFoundError(f"JMX file not found: {jmx_path}")

        # Validate JMX
        validator = JMXValidator()
        result = validator.validate(jmx_path)

        # Extract structure information from the JMX file
        import xml.etree.ElementTree as ET
        tree = ET.parse(jmx_path)
        root = tree.getroot()

        # Get structure info
        test_plan = root.find(".//TestPlan")
        test_plan_name = test_plan.get("testname", "Unknown") if test_plan is not None else "Unknown"
        thread_groups = len(root.findall(".//ThreadGroup"))
        http_samplers = len(root.findall(".//HTTPSamplerProxy"))
        assertions = len(root.findall(".//ResponseAssertion"))
        extractors = len(root.findall(".//JSONPostProcessor"))

        response = {
            "success": True,
            "valid": result["valid"],
            "jmx_path": str(Path(jmx_path).absolute()),
            "structure": {
                "test_plan_name": test_plan_name,
                "thread_groups": thread_groups,
                "http_samplers": http_samplers,
                "assertions": assertions,
                "extractors": extractors,
            },
            "issues": result.get("issues", []),
            "recommendations": result.get("recommendations", []),
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except JMeterGenException as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "error": str(e), "error_type": type(e).__name__},
                    indent=2,
                ),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "error": str(e), "error_type": type(e).__name__},
                    indent=2,
                ),
            )
        ]


async def _visualize_scenario(arguments: Dict[str, Any]) -> List[TextContent]:
    """Visualize scenario file with multiple output formats.

    Args:
        arguments: Dictionary with 'scenario_path' and optional 'spec_path' keys

    Returns:
        List with single TextContent containing visualization results
    """
    try:
        scenario_path = arguments.get("scenario_path")
        spec_path = arguments.get("spec_path")

        if not scenario_path:
            raise ValueError("scenario_path is required")

        # Verify scenario file exists
        if not Path(scenario_path).exists():
            raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

        # Parse scenario
        scenario_parser = PtScenarioParser()
        scenario = scenario_parser.parse(scenario_path)

        # Perform correlation analysis if spec provided
        correlation_result = None
        if spec_path:
            if not Path(spec_path).exists():
                raise FileNotFoundError(f"OpenAPI spec file not found: {spec_path}")

            parser = OpenAPIParser()
            parser.parse(spec_path)  # Load spec into parser
            correlation_analyzer = CorrelationAnalyzer(parser)
            correlation_result = correlation_analyzer.analyze(scenario)

        # Build step information
        steps_info = []
        for idx, step in enumerate(scenario.steps, 1):
            step_info = {
                "number": idx,
                "name": step.name,
                "endpoint": step.endpoint,
                "endpoint_type": step.endpoint_type,
                "captures": [c.variable_name for c in step.captures],
                "uses_variables": [],  # Will be populated from correlation result
            }
            if step.method:
                step_info["method"] = step.method
            if step.path:
                step_info["path"] = step.path
            steps_info.append(step_info)

        # Populate variable usage from correlation result
        if correlation_result:
            for mapping in correlation_result.mappings:
                for target_step in mapping.target_steps:
                    if 0 < target_step <= len(steps_info):
                        if mapping.variable_name not in steps_info[target_step - 1]["uses_variables"]:
                            steps_info[target_step - 1]["uses_variables"].append(mapping.variable_name)

        # Build correlations info
        correlations_info = []
        if correlation_result:
            for mapping in correlation_result.mappings:
                source_step = scenario.steps[mapping.source_step - 1] if mapping.source_step <= len(scenario.steps) else None
                correlations_info.append({
                    "variable": mapping.variable_name,
                    "captured_in": f"Step {mapping.source_step}: {source_step.name if source_step else 'Unknown'}",
                    "used_in": [f"Step {t}: {scenario.steps[t-1].name if t <= len(scenario.steps) else 'Unknown'}" for t in mapping.target_steps],
                    "jsonpath": mapping.jsonpath,
                    "confidence": "high" if mapping.confidence >= 0.9 else "medium" if mapping.confidence >= 0.7 else "low",
                })

        # Generate visualizations
        text_viz = generate_text_visualization(scenario, correlation_result)
        mermaid_diagram = generate_mermaid_diagram(scenario, correlation_result)

        response = {
            "success": True,
            "scenario": {
                "name": scenario.name,
                "description": scenario.description,
                "steps": steps_info,
            },
            "correlations": correlations_info,
            "text_visualization": text_viz,
            "mermaid_diagram": mermaid_diagram,
            "warnings": correlation_result.warnings if correlation_result else [],
            "errors": correlation_result.errors if correlation_result else [],
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except JMeterGenException as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "error": str(e), "error_type": type(e).__name__},
                    indent=2,
                ),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "error": str(e), "error_type": type(e).__name__},
                    indent=2,
                ),
            )
        ]


async def _list_endpoints(arguments: Dict[str, Any]) -> List[TextContent]:
    """List all endpoints from OpenAPI specification.

    Args:
        arguments: Dictionary with 'spec_path' key

    Returns:
        List with single TextContent containing endpoint list
    """
    try:
        spec_path = arguments.get("spec_path")
        if not spec_path:
            raise ValueError("spec_path is required")

        # Verify spec file exists
        if not Path(spec_path).exists():
            raise FileNotFoundError(f"OpenAPI spec file not found: {spec_path}")

        # Parse OpenAPI spec
        parser = OpenAPIParser()
        spec_data = parser.parse(spec_path)

        # Use ScenarioWizard to get readable endpoint names
        wizard = ScenarioWizard(parser, spec_data)

        # Format endpoints with readable names
        endpoints = []
        for ep in spec_data.get("endpoints", []):
            method = ep.get("method", "GET").upper()
            path = ep.get("path", "/")
            operation_id = ep.get("operationId", "")

            # Get readable display name (fix ugly auto-generated operationIds)
            display_name = wizard._get_readable_display_name(operation_id, path, method)

            endpoints.append({
                "method": method,
                "path": path,
                "operationId": operation_id,
                "displayName": display_name,
                "summary": ep.get("summary", ""),
                "hasRequestBody": ep.get("requestBody", False),
                "parameters": ep.get("parameters", []),
            })

        response = {
            "success": True,
            "spec_path": spec_path,
            "api_title": spec_data.get("title", "Unknown API"),
            "api_version": spec_data.get("version", "Unknown"),
            "base_url": spec_data.get("base_url", ""),
            "endpoints_count": len(endpoints),
            "endpoints": endpoints,
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except JMeterGenException as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "error": str(e), "error_type": type(e).__name__},
                    indent=2,
                ),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "error": str(e), "error_type": type(e).__name__},
                    indent=2,
                ),
            )
        ]


async def _suggest_captures(arguments: Dict[str, Any]) -> List[TextContent]:
    """Suggest capturable fields for an endpoint.

    Args:
        arguments: Dictionary with 'spec_path' and 'endpoint' keys

    Returns:
        List with single TextContent containing capture suggestions
    """
    try:
        spec_path = arguments.get("spec_path")
        endpoint = arguments.get("endpoint")

        if not spec_path:
            raise ValueError("spec_path is required")
        if not endpoint:
            raise ValueError("endpoint is required")

        # Verify spec file exists
        if not Path(spec_path).exists():
            raise FileNotFoundError(f"OpenAPI spec file not found: {spec_path}")

        # Parse OpenAPI spec
        parser = OpenAPIParser()
        spec_data = parser.parse(spec_path)

        # Create wizard to use its methods
        wizard = ScenarioWizard(parser, spec_data)
        wizard._endpoints = spec_data.get("endpoints", [])  # Initialize endpoints

        # Parse endpoint identifier (operationId or "METHOD /path")
        method = None
        path = None

        if " " in endpoint and endpoint.split()[0].upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
            # "METHOD /path" format
            parts = endpoint.split(" ", 1)
            method = parts[0].upper()
            path = parts[1]
        else:
            # operationId format - find matching endpoint
            for ep in spec_data.get("endpoints", []):
                if ep.get("operationId") == endpoint:
                    method = ep.get("method", "GET").upper()
                    path = ep.get("path", "/")
                    break

        if not method or not path:
            raise ValueError(f"Endpoint not found: {endpoint}")

        # Get endpoint data
        endpoint_data = wizard._get_endpoint_data(method, path)
        if not endpoint_data:
            raise ValueError(f"Endpoint not found: {method} {path}")

        # Get capture suggestions using wizard's method
        suggestions = wizard._suggest_captures(endpoint_data)

        response = {
            "success": True,
            "endpoint": f"{method} {path}",
            "operationId": endpoint_data.get("operationId", ""),
            "suggestions": suggestions,
            "note": "Use 'capture' field in build_scenario steps to capture these variables",
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except JMeterGenException as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "error": str(e), "error_type": type(e).__name__},
                    indent=2,
                ),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "error": str(e), "error_type": type(e).__name__},
                    indent=2,
                ),
            )
        ]


async def _build_scenario(arguments: Dict[str, Any]) -> List[TextContent]:
    """Build pt_scenario.yaml from step definitions.

    Args:
        arguments: Dictionary with scenario configuration

    Returns:
        List with single TextContent containing build result
    """
    try:
        spec_path = arguments.get("spec_path")
        steps = arguments.get("steps", [])
        name = arguments.get("name", "Test Scenario")
        description = arguments.get("description", "")
        output_path = arguments.get("output_path", "pt_scenario.yaml")
        settings = arguments.get("settings", {})

        if not spec_path:
            raise ValueError("spec_path is required")
        if not steps:
            raise ValueError("steps is required and must not be empty")

        # Verify spec file exists
        if not Path(spec_path).exists():
            raise FileNotFoundError(f"OpenAPI spec file not found: {spec_path}")

        # Parse OpenAPI spec
        parser = OpenAPIParser()
        spec_data = parser.parse(spec_path)

        # Create wizard to use its methods
        wizard = ScenarioWizard(parser, spec_data)
        wizard._endpoints = spec_data.get("endpoints", [])  # Initialize endpoints

        # Validate and normalize steps
        normalized_steps = []
        warnings = []

        for idx, step in enumerate(steps):
            endpoint = step.get("endpoint")
            if not endpoint:
                raise ValueError(f"Step {idx + 1}: endpoint is required")

            # Parse endpoint identifier
            method = None
            path = None

            if " " in endpoint and endpoint.split()[0].upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                parts = endpoint.split(" ", 1)
                method = parts[0].upper()
                path = parts[1]
            else:
                # operationId format
                for ep in spec_data.get("endpoints", []):
                    if ep.get("operationId") == endpoint:
                        method = ep.get("method", "GET").upper()
                        path = ep.get("path", "/")
                        break

            if not method or not path:
                warnings.append(f"Step {idx + 1}: Endpoint '{endpoint}' not found in spec")
                # Still include it, user might know what they're doing
                normalized_step = {"endpoint": endpoint}
            else:
                endpoint_data = wizard._get_endpoint_data(method, path)
                display_name = wizard._get_readable_display_name(
                    endpoint_data.get("operationId", ""),
                    path,
                    method
                )
                normalized_step = {"endpoint": f"{method} {path}"}

                # Generate step name if not provided
                if not step.get("name"):
                    # Convert camelCase/PascalCase to Title Case
                    step_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', display_name)
                    step_name = step_name.replace("_", " ").title()
                    normalized_step["name"] = step_name
                else:
                    normalized_step["name"] = step["name"]

            # Copy other fields
            if step.get("capture"):
                normalized_step["capture"] = step["capture"]
            if step.get("think_time"):
                normalized_step["think_time"] = step["think_time"]
            if step.get("loop"):
                normalized_step["loop"] = step["loop"]
            if step.get("assert"):
                normalized_step["assert"] = step["assert"]

            normalized_steps.append(normalized_step)

        # Build scenario dict (same structure as ScenarioWizard)
        scenario: Dict[str, Any] = {
            "version": "1.0",
            "name": name,
        }

        if description:
            scenario["description"] = description

        if settings:
            scenario["settings"] = settings

        scenario["scenario"] = normalized_steps

        # Convert to YAML
        yaml_content = yaml.dump(
            scenario,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

        # Save to file
        Path(output_path).write_text(yaml_content, encoding="utf-8")

        # Auto-validate generated scenario
        validator = ScenarioValidator()
        validation_result = validator.validate(output_path, spec_path)

        response = {
            "success": True,
            "output_path": output_path,
            "scenario_name": name,
            "steps_count": len(normalized_steps),
            "yaml_content": yaml_content,
            "warnings": warnings,
            "validation": {
                "is_valid": validation_result.is_valid,
                "errors_count": validation_result.errors_count,
                "warnings_count": validation_result.warnings_count,
                "issues": [
                    {"level": i.level, "category": i.category, "message": i.message}
                    for i in validation_result.issues
                ],
            },
            "next_step": f"Use generate_scenario_jmx with scenario_path: {output_path} and spec_path: {spec_path}",
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except JMeterGenException as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "error": str(e), "error_type": type(e).__name__},
                    indent=2,
                ),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "error": str(e), "error_type": type(e).__name__},
                    indent=2,
                ),
            )
        ]


async def _validate_scenario_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    """Validate a pt_scenario.yaml file.

    Args:
        arguments: Dictionary with 'scenario_path' and optional 'spec_path' keys

    Returns:
        List with single TextContent containing validation results
    """
    try:
        scenario_path = arguments.get("scenario_path")
        spec_path = arguments.get("spec_path")

        if not scenario_path:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"success": False, "error": "Missing required parameter: scenario_path"},
                        indent=2,
                    ),
                )
            ]

        validator = ScenarioValidator()
        result = validator.validate(scenario_path, spec_path)

        # Format issues
        issues_formatted = []
        for issue in result.issues:
            issue_dict = {
                "level": issue.level,
                "category": issue.category,
                "message": issue.message,
            }
            if issue.location:
                issue_dict["location"] = issue.location
            issues_formatted.append(issue_dict)

        response = {
            "success": True,
            "scenario_path": result.scenario_path,
            "scenario_name": result.scenario_name,
            "is_valid": result.is_valid,
            "errors_count": result.errors_count,
            "warnings_count": result.warnings_count,
            "issues": issues_formatted,
            "next_step": (
                f"Scenario is valid! Use generate_scenario_jmx to generate JMX."
                if result.is_valid
                else "Fix errors above and validate again."
            ),
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except FileNotFoundError as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "error": str(e), "error_type": "FileNotFoundError"},
                    indent=2,
                ),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {"success": False, "error": str(e), "error_type": type(e).__name__},
                    indent=2,
                ),
            )
        ]


async def main() -> None:
    """Main entry point for MCP server.

    Starts the MCP server using stdio transport for communication
    with MCP clients like GitHub Copilot.
    """
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def run_server() -> None:
    """Synchronous wrapper to run the MCP server.

    This is called from the CLI mcp command.
    """
    asyncio.run(main())


if __name__ == "__main__":
    run_server()
