"""Tests for MCP Server functionality."""

import json
from pathlib import Path
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jmeter_gen.mcp_server import (
    _analyze_project,
    _generate_jmx,
    _generate_scenario_jmx,
    _validate_jmx,
    _visualize_scenario,
    call_tool,
    list_tools,
)


class TestListTools:
    """Tests for list_tools() handler."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_five_tools(self):
        """Test that list_tools returns exactly 5 tools (v1 + v2)."""
        tools = await list_tools()
        assert len(tools) == 5

    @pytest.mark.asyncio
    async def test_list_tools_contains_analyze_project(self):
        """Test that analyze_project_for_jmeter tool is included."""
        tools = await list_tools()
        tool_names = [tool.name for tool in tools]
        assert "analyze_project_for_jmeter" in tool_names

    @pytest.mark.asyncio
    async def test_list_tools_contains_generate_jmx(self):
        """Test that generate_jmx_from_openapi tool is included."""
        tools = await list_tools()
        tool_names = [tool.name for tool in tools]
        assert "generate_jmx_from_openapi" in tool_names

    @pytest.mark.asyncio
    async def test_analyze_project_tool_schema(self):
        """Test that analyze_project_for_jmeter has correct schema."""
        tools = await list_tools()
        analyze_tool = next(t for t in tools if t.name == "analyze_project_for_jmeter")

        assert analyze_tool.description is not None
        assert "OpenAPI" in analyze_tool.description
        assert analyze_tool.inputSchema is not None
        assert analyze_tool.inputSchema["type"] == "object"
        assert "project_path" in analyze_tool.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_generate_jmx_tool_schema(self):
        """Test that generate_jmx_from_openapi has correct schema."""
        tools = await list_tools()
        generate_tool = next(t for t in tools if t.name == "generate_jmx_from_openapi")

        assert generate_tool.description is not None
        assert "JMeter" in generate_tool.description
        assert generate_tool.inputSchema is not None
        assert generate_tool.inputSchema["type"] == "object"

        # Check required fields
        assert "spec_path" in generate_tool.inputSchema["required"]

        # Check all expected properties
        props = generate_tool.inputSchema["properties"]
        assert "spec_path" in props
        assert "output_path" in props
        assert "threads" in props
        assert "rampup" in props
        assert "duration" in props
        assert "base_url_override" in props
        assert "endpoints" in props

    @pytest.mark.asyncio
    async def test_list_tools_contains_generate_scenario_jmx(self):
        """Test that generate_scenario_jmx tool is included (v2)."""
        tools = await list_tools()
        tool_names = [tool.name for tool in tools]
        assert "generate_scenario_jmx" in tool_names

    @pytest.mark.asyncio
    async def test_generate_scenario_jmx_tool_schema(self):
        """Test that generate_scenario_jmx has correct schema (v2)."""
        tools = await list_tools()
        scenario_tool = next(t for t in tools if t.name == "generate_scenario_jmx")

        assert scenario_tool.description is not None
        assert "scenario" in scenario_tool.description.lower()
        assert scenario_tool.inputSchema is not None
        assert scenario_tool.inputSchema["type"] == "object"

        # Check required fields
        assert "scenario_path" in scenario_tool.inputSchema["required"]
        assert "spec_path" in scenario_tool.inputSchema["required"]

        # Check all expected properties
        props = scenario_tool.inputSchema["properties"]
        assert "scenario_path" in props
        assert "spec_path" in props
        assert "output_path" in props
        assert "base_url_override" in props


class TestCallTool:
    """Tests for call_tool() handler."""

    @pytest.mark.asyncio
    async def test_call_tool_with_unknown_tool(self):
        """Test that call_tool raises ValueError for unknown tool."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await call_tool("nonexistent_tool", {})

    @pytest.mark.asyncio
    async def test_call_tool_routes_to_analyze_project(self):
        """Test that call_tool routes analyze_project_for_jmeter correctly."""
        with patch("jmeter_gen.mcp_server._analyze_project") as mock_analyze:
            mock_analyze.return_value = [MagicMock()]
            args = {"project_path": "."}

            result = await call_tool("analyze_project_for_jmeter", args)

            # Verify the mock was called with exact arguments
            mock_analyze.assert_called_once_with(args)
            assert args["project_path"] == "."
            assert result is not None

    @pytest.mark.asyncio
    async def test_call_tool_routes_to_generate_jmx(self):
        """Test that call_tool routes generate_jmx_from_openapi correctly."""
        with patch("jmeter_gen.mcp_server._generate_jmx") as mock_generate:
            mock_generate.return_value = [MagicMock()]
            args = {"spec_path": "openapi.yaml"}

            result = await call_tool("generate_jmx_from_openapi", args)

            # Verify the mock was called with exact arguments
            mock_generate.assert_called_once_with(args)
            assert args["spec_path"] == "openapi.yaml"
            assert result is not None


class TestAnalyzeProject:
    """Tests for _analyze_project() tool implementation."""

    @pytest.mark.asyncio
    async def test_analyze_project_with_spec_found(self, project_with_openapi_yaml: Path):
        """Test successful project analysis with OpenAPI spec."""
        arguments = {"project_path": str(project_with_openapi_yaml)}

        result = await _analyze_project(arguments)

        assert len(result) == 1
        assert result[0].type == "text"

        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["spec_found"] is True
        assert "openapi.yaml" in response["spec_path"]
        assert response["api_title"] is not None
        assert response["endpoints_count"] >= 1  # Real endpoint count from parsed spec
        assert "next_step" in response

    @pytest.mark.asyncio
    async def test_analyze_project_with_no_spec(self, empty_project: Path):
        """Test project analysis when no OpenAPI spec found."""
        arguments = {"project_path": str(empty_project)}

        result = await _analyze_project(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is False
        # Error response uses standardized "error" field
        assert "No OpenAPI specification found" in response["error"]
        assert "searched_path" in response

    @pytest.mark.asyncio
    async def test_analyze_project_with_default_path(self, project_with_swagger_json: Path):
        """Test project analysis with default path argument."""
        # Change to project directory
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(str(project_with_swagger_json))

            result = await _analyze_project({})

            assert len(result) == 1
            response = json.loads(result[0].text)
            assert response["success"] is True
            assert response["spec_found"] is True
        finally:
            os.chdir(original_dir)

    @pytest.mark.asyncio
    async def test_analyze_project_handles_errors(self):
        """Test that analyze_project handles exceptions gracefully."""
        arguments = {"project_path": "/nonexistent/path/that/does/not/exist"}

        result = await _analyze_project(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is False
        # All error responses use standardized "error" field
        assert "error" in response

    @pytest.mark.asyncio
    async def test_analyze_project_with_swagger2(self, project_with_swagger2_yaml: Path):
        """Test project analysis with Swagger 2.0 spec."""
        arguments = {"project_path": str(project_with_swagger2_yaml)}

        result = await _analyze_project(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["spec_found"] is True
        assert response["api_title"] is not None
        assert response["endpoints_count"] >= 1  # Real endpoint count from parsed spec


class TestGenerateJMX:
    """Tests for _generate_jmx() tool implementation."""

    @pytest.mark.asyncio
    async def test_generate_jmx_with_valid_spec(
        self, project_with_openapi_yaml: Path, temp_project_dir: Path
    ):
        """Test successful JMX generation from OpenAPI spec."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        output_path = temp_project_dir / "test.jmx"

        arguments = {
            "spec_path": str(spec_path),
            "output_path": str(output_path),
            "threads": 20,
            "rampup": 10,
            "duration": 120,
        }

        result = await _generate_jmx(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert output_path.exists()
        assert response["api_title"] == "Test API"
        assert response["api_version"] == "1.0.0"
        assert response["samplers_created"] == 1
        assert response["configuration"]["threads"] == 20
        assert response["configuration"]["rampup"] == 10
        assert response["configuration"]["duration"] == 120
        assert "validation" in response
        assert "next_steps" in response

    @pytest.mark.asyncio
    async def test_generate_jmx_with_base_url_override(
        self, project_with_openapi_yaml: Path, temp_project_dir: Path
    ):
        """Test JMX generation with base URL override."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        output_path = temp_project_dir / "test.jmx"

        arguments = {
            "spec_path": str(spec_path),
            "output_path": str(output_path),
            "base_url_override": "http://staging.example.com:9000",
        }

        result = await _generate_jmx(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["configuration"]["base_url"] == "http://staging.example.com:9000"

    @pytest.mark.asyncio
    async def test_generate_jmx_with_default_parameters(
        self, project_with_openapi_yaml: Path, temp_project_dir: Path
    ):
        """Test JMX generation with default parameters."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"

        arguments = {"spec_path": str(spec_path)}

        result = await _generate_jmx(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["configuration"]["threads"] == 10
        assert response["configuration"]["rampup"] == 5
        assert response["configuration"]["duration"] == 60

    @pytest.mark.asyncio
    async def test_generate_jmx_without_spec_path(self):
        """Test that missing spec_path raises ValueError."""
        arguments = {}

        result = await _generate_jmx(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is False
        assert "spec_path is required" in response["error"]

    @pytest.mark.asyncio
    async def test_generate_jmx_with_nonexistent_spec(self, temp_project_dir: Path):
        """Test error handling when spec file doesn't exist."""
        arguments = {
            "spec_path": str(temp_project_dir / "nonexistent.yaml"),
            "output_path": "test.jmx",
        }

        result = await _generate_jmx(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is False
        assert "error" in response
        assert "error_type" in response

    @pytest.mark.asyncio
    async def test_generate_jmx_with_endpoint_filter(
        self, project_with_swagger2_yaml: Path, temp_project_dir: Path
    ):
        """Test JMX generation with endpoint filtering."""
        spec_path = project_with_swagger2_yaml / "swagger.yaml"
        output_path = temp_project_dir / "filtered.jmx"

        arguments = {
            "spec_path": str(spec_path),
            "output_path": str(output_path),
            "endpoints": ["getUsers", "createUser"],
        }

        result = await _generate_jmx(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        # Should only create 2 samplers instead of all 3
        assert response["samplers_created"] == 2

    @pytest.mark.asyncio
    async def test_generate_jmx_includes_validation_results(
        self, project_with_openapi_yaml: Path, temp_project_dir: Path
    ):
        """Test that generation includes validation results."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        output_path = temp_project_dir / "validated.jmx"

        arguments = {
            "spec_path": str(spec_path),
            "output_path": str(output_path),
        }

        result = await _generate_jmx(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert "validation" in response
        assert "valid" in response["validation"]
        assert "issues" in response["validation"]
        assert "recommendations" in response["validation"]

    @pytest.mark.asyncio
    async def test_generate_jmx_with_swagger2_spec(
        self, project_with_swagger2_json: Path, temp_project_dir: Path
    ):
        """Test JMX generation from Swagger 2.0 spec."""
        spec_path = project_with_swagger2_json / "swagger.json"
        output_path = temp_project_dir / "swagger2.jmx"

        arguments = {
            "spec_path": str(spec_path),
            "output_path": str(output_path),
        }

        result = await _generate_jmx(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["samplers_created"] == 1
        # Swagger 2.0 should use base URL from host + basePath
        assert "https://api.example.com" in response["configuration"]["base_url"]

    @pytest.mark.asyncio
    async def test_generate_jmx_error_handling_for_invalid_spec(
        self, temp_project_dir: Path
    ):
        """Test error handling for invalid OpenAPI spec."""
        # Create an invalid spec file
        invalid_spec = temp_project_dir / "invalid.yaml"
        invalid_spec.write_text("not: valid\nopenapi: spec")

        arguments = {
            "spec_path": str(invalid_spec),
            "output_path": "test.jmx",
        }

        result = await _generate_jmx(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is False
        assert "error" in response


class TestMCPServerIntegration:
    """Integration tests for MCP server components."""

    @pytest.mark.asyncio
    async def test_end_to_end_analyze_and_generate(
        self, project_with_openapi_yaml: Path, temp_project_dir: Path
    ):
        """Test complete workflow: analyze project then generate JMX."""
        # Step 1: Analyze project
        analyze_args = {"project_path": str(project_with_openapi_yaml)}
        analyze_result = await _analyze_project(analyze_args)

        analyze_response = json.loads(analyze_result[0].text)
        assert analyze_response["success"] is True

        # Step 2: Use spec_path from analysis to generate JMX
        spec_path = analyze_response["spec_path"]
        output_path = temp_project_dir / "generated.jmx"

        generate_args = {
            "spec_path": spec_path,
            "output_path": str(output_path),
        }
        generate_result = await _generate_jmx(generate_args)

        generate_response = json.loads(generate_result[0].text)
        assert generate_response["success"] is True
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_all_tools_accessible_via_call_tool(
        self, project_with_openapi_yaml: Path
    ):
        """Test that all listed tools are accessible via call_tool."""
        tools = await list_tools()

        # Test analyze_project_for_jmeter
        analyze_result = await call_tool(
            "analyze_project_for_jmeter",
            {"project_path": str(project_with_openapi_yaml)},
        )
        assert len(analyze_result) == 1
        analyze_response = json.loads(analyze_result[0].text)
        assert analyze_response["success"] is True

        # Test generate_jmx_from_openapi
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        generate_result = await call_tool(
            "generate_jmx_from_openapi",
            {"spec_path": str(spec_path)},
        )
        assert len(generate_result) == 1
        generate_response = json.loads(generate_result[0].text)
        assert generate_response["success"] is True


class TestMCPServerErrorHandling:
    """Tests for error handling in MCP server."""

    @pytest.mark.asyncio
    async def test_analyze_project_with_permission_error(self):
        """Test graceful error handling for permission errors."""
        arguments = {"project_path": "/root/restricted"}

        result = await _analyze_project(arguments)

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is False
        # When path doesn't exist or no spec found, returns message
        assert "message" in response or "error" in response

    @pytest.mark.asyncio
    async def test_generate_jmx_with_invalid_threads(
        self, project_with_openapi_yaml: Path
    ):
        """Test that invalid thread count is handled."""
        spec_path = project_with_openapi_yaml / "openapi.yaml"

        arguments = {
            "spec_path": str(spec_path),
            "threads": -5,  # Invalid negative value
        }

        result = await _generate_jmx(arguments)

        # Should still process but core validation might catch it
        assert len(result) == 1
        response = json.loads(result[0].text)
        # Either fails or succeeds, but should not crash
        assert "success" in response


class TestValidateJmxTool:
    """Tests for validate_jmx tool."""

    @pytest.mark.asyncio
    async def test_list_tools_contains_validate_jmx(self):
        """Test that validate_jmx tool is included."""
        tools = await list_tools()
        tool_names = [tool.name for tool in tools]
        assert "validate_jmx" in tool_names

    @pytest.mark.asyncio
    async def test_validate_jmx_tool_schema(self):
        """Test that validate_jmx has correct schema."""
        tools = await list_tools()
        validate_tool = next(t for t in tools if t.name == "validate_jmx")

        assert validate_tool.description is not None
        assert "Validate" in validate_tool.description
        assert validate_tool.inputSchema is not None
        assert validate_tool.inputSchema["type"] == "object"
        assert "jmx_path" in validate_tool.inputSchema["required"]

    @pytest.mark.asyncio
    async def test_validate_jmx_with_valid_file(
        self, project_with_openapi_yaml: Path, temp_project_dir: Path
    ):
        """Test validation of a valid JMX file."""
        # First generate a JMX file
        spec_path = project_with_openapi_yaml / "openapi.yaml"
        output_path = temp_project_dir / "valid.jmx"

        gen_result = await _generate_jmx({
            "spec_path": str(spec_path),
            "output_path": str(output_path),
        })
        gen_response = json.loads(gen_result[0].text)
        assert gen_response["success"] is True

        # Now validate it
        result = await _validate_jmx({"jmx_path": str(output_path)})

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["valid"] is True
        assert "structure" in response
        assert response["structure"]["http_samplers"] >= 1
        assert "recommendations" in response

    @pytest.mark.asyncio
    async def test_validate_jmx_without_jmx_path(self):
        """Test that missing jmx_path raises error."""
        result = await _validate_jmx({})

        response = json.loads(result[0].text)
        assert response["success"] is False
        assert "jmx_path is required" in response["error"]

    @pytest.mark.asyncio
    async def test_validate_jmx_with_nonexistent_file(self):
        """Test validation with non-existent file."""
        result = await _validate_jmx({"jmx_path": "/nonexistent/file.jmx"})

        response = json.loads(result[0].text)
        assert response["success"] is False
        assert "not found" in response["error"]


class TestVisualizeScenarioTool:
    """Tests for visualize_scenario tool."""

    @pytest.mark.asyncio
    async def test_list_tools_contains_visualize_scenario(self):
        """Test that visualize_scenario tool is included."""
        tools = await list_tools()
        tool_names = [tool.name for tool in tools]
        assert "visualize_scenario" in tool_names

    @pytest.mark.asyncio
    async def test_visualize_scenario_tool_schema(self):
        """Test that visualize_scenario has correct schema."""
        tools = await list_tools()
        viz_tool = next(t for t in tools if t.name == "visualize_scenario")

        assert viz_tool.description is not None
        assert "visualize" in viz_tool.description.lower()
        assert viz_tool.inputSchema is not None
        assert viz_tool.inputSchema["type"] == "object"
        assert "scenario_path" in viz_tool.inputSchema["required"]
        assert "spec_path" in viz_tool.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_visualize_scenario_basic(self, tmp_path: Path):
        """Test basic scenario visualization without spec."""
        # Create a simple scenario file
        scenario_path = tmp_path / "pt_scenario.yaml"
        scenario_path.write_text("""
version: "1.0"
name: "Test Scenario"
description: "A test scenario"
scenario:
  - name: "Create User"
    endpoint: "POST /users"
  - name: "Get User"
    endpoint: "GET /users/{userId}"
""")

        result = await _visualize_scenario({"scenario_path": str(scenario_path)})

        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["scenario"]["name"] == "Test Scenario"
        assert len(response["scenario"]["steps"]) == 2
        assert "text_visualization" in response
        assert "mermaid_diagram" in response
        assert "flowchart TD" in response["mermaid_diagram"]

    @pytest.mark.asyncio
    async def test_visualize_scenario_with_captures(self, tmp_path: Path):
        """Test scenario visualization with captures."""
        scenario_path = tmp_path / "pt_scenario.yaml"
        scenario_path.write_text("""
version: "1.0"
name: "User Flow"
scenario:
  - name: "Create User"
    endpoint: "POST /users"
    capture:
      - userId
  - name: "Get User"
    endpoint: "GET /users/{userId}"
""")

        result = await _visualize_scenario({"scenario_path": str(scenario_path)})

        response = json.loads(result[0].text)
        assert response["success"] is True
        # Step 1 should have captures
        step1 = response["scenario"]["steps"][0]
        assert "userId" in step1["captures"]

    @pytest.mark.asyncio
    async def test_visualize_scenario_without_scenario_path(self):
        """Test that missing scenario_path raises error."""
        result = await _visualize_scenario({})

        response = json.loads(result[0].text)
        assert response["success"] is False
        assert "scenario_path is required" in response["error"]

    @pytest.mark.asyncio
    async def test_visualize_scenario_with_nonexistent_file(self):
        """Test visualization with non-existent scenario file."""
        result = await _visualize_scenario({"scenario_path": "/nonexistent/scenario.yaml"})

        response = json.loads(result[0].text)
        assert response["success"] is False
        assert "not found" in response["error"]


class TestAnalyzeWithScenarioDetection:
    """Tests for scenario detection in analyze_project tool."""

    @pytest.mark.asyncio
    async def test_analyze_detects_scenario_file(self, tmp_path: Path):
        """Test that analyze reports scenario file when present."""
        # Create OpenAPI spec
        spec_path = tmp_path / "openapi.yaml"
        spec_path.write_text("""
openapi: "3.0.0"
info:
  title: "Test API"
  version: "1.0.0"
paths:
  /users:
    post:
      operationId: createUser
      responses:
        201:
          description: Created
""")

        # Create scenario file
        scenario_path = tmp_path / "pt_scenario.yaml"
        scenario_path.write_text("""
version: "1.0"
name: "User Registration"
scenario:
  - name: "Create User"
    endpoint: "createUser"
""")

        result = await _analyze_project({"project_path": str(tmp_path)})

        response = json.loads(result[0].text)
        assert response["success"] is True
        assert "scenario" in response
        assert response["scenario"]["path"] == str(scenario_path)
        assert response["scenario"]["name"] == "User Registration"
        assert response["scenario"]["steps_count"] == 1
        assert "generate_scenario_jmx" in response["next_step"]

    @pytest.mark.asyncio
    async def test_analyze_without_scenario_file(self, project_with_openapi_yaml: Path):
        """Test that analyze works without scenario file."""
        result = await _analyze_project({"project_path": str(project_with_openapi_yaml)})

        response = json.loads(result[0].text)
        assert response["success"] is True
        # No scenario field when no scenario file
        assert "scenario" not in response or response.get("scenario") is None


class TestGenerateScenarioJmxAutoFilename:
    """Tests for auto-filename generation in generate_scenario_jmx."""

    @pytest.mark.asyncio
    async def test_auto_generates_filename_from_scenario_name(self, tmp_path: Path):
        """Test that output filename is auto-generated from scenario name."""
        # Create OpenAPI spec
        spec_path = tmp_path / "openapi.yaml"
        spec_path.write_text("""
openapi: "3.0.0"
info:
  title: "Test API"
  version: "1.0.0"
servers:
  - url: http://localhost:8080
paths:
  /users:
    post:
      operationId: createUser
      responses:
        201:
          description: Created
""")

        # Create scenario file with specific name
        scenario_path = tmp_path / "pt_scenario.yaml"
        scenario_path.write_text("""
version: "1.0"
name: "User Registration Flow"
scenario:
  - name: "Create User"
    endpoint: "createUser"
""")

        result = await _generate_scenario_jmx({
            "scenario_path": str(scenario_path),
            "spec_path": str(spec_path),
            # No output_path - should auto-generate
        })

        response = json.loads(result[0].text)
        assert response["success"] is True
        # Should have generated filename from scenario name
        assert "user-registration-flow-test.jmx" in response["jmx_path"]

    @pytest.mark.asyncio
    async def test_uses_provided_output_path(self, tmp_path: Path):
        """Test that provided output_path is used instead of auto-generated."""
        # Create OpenAPI spec
        spec_path = tmp_path / "openapi.yaml"
        spec_path.write_text("""
openapi: "3.0.0"
info:
  title: "Test API"
  version: "1.0.0"
servers:
  - url: http://localhost:8080
paths:
  /users:
    post:
      operationId: createUser
      responses:
        201:
          description: Created
""")

        # Create scenario file
        scenario_path = tmp_path / "pt_scenario.yaml"
        scenario_path.write_text("""
version: "1.0"
name: "User Registration"
scenario:
  - name: "Create User"
    endpoint: "createUser"
""")

        custom_output = tmp_path / "custom-name.jmx"
        result = await _generate_scenario_jmx({
            "scenario_path": str(scenario_path),
            "spec_path": str(spec_path),
            "output_path": str(custom_output),
        })

        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["jmx_path"] == str(custom_output)
