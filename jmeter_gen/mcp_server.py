"""MCP Server for JMeter Test Generator.

This module provides a Model Context Protocol (MCP) server that exposes
JMeter test generation capabilities to GitHub Copilot and other AI assistants.

Supports change detection with detect_changes, auto_update options.
"""

import asyncio
import json
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
                "Analyze a project directory to discover OpenAPI specifications. "
                "Searches for common spec files (openapi.yaml, swagger.json, etc.) "
                "and returns metadata about discovered specs including endpoint count, "
                "API title, and recommended JMX filename. "
                "Supports change detection to identify API changes since last snapshot."
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
