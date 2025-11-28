"""Tests for CLI module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from jmeter_gen.cli import analyze, cli, generate, mcp, validate
from jmeter_gen.exceptions import JMXGenerationException, JMXValidationException


# Module-level fixture to ensure find_scenario_file returns None by default
# This prevents v2 scenario-based generation from interfering with v1 tests
@pytest.fixture(autouse=True)
def mock_find_scenario_file():
    """Mock find_scenario_file to return None (no scenario file) for all tests."""
    with patch.object(
        __import__("jmeter_gen.core.project_analyzer", fromlist=["ProjectAnalyzer"]).ProjectAnalyzer,
        "find_scenario_file",
        return_value=None
    ):
        yield


class TestCLI:
    """Test suite for CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI runner for testing.

        Returns:
            CliRunner instance
        """
        return CliRunner()

    def test_cli_help(self, runner: CliRunner):
        """Test CLI help message displays correctly.

        Args:
            runner: CLI runner fixture
        """
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "JMeter Test Generator" in result.output
        assert "analyze" in result.output
        assert "generate" in result.output
        assert "validate" in result.output
        assert "mcp" in result.output

    def test_cli_version(self, runner: CliRunner):
        """Test CLI version flag.

        Args:
            runner: CLI runner fixture
        """
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "2.1.1" in result.output


class TestAnalyzeCommand:
    """Test suite for analyze command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI runner for testing.

        Returns:
            CliRunner instance
        """
        return CliRunner()

    @patch("jmeter_gen.cli.ProjectAnalyzer")
    def test_analyze_spec_found(self, mock_analyzer_class: Mock, runner: CliRunner):
        """Test analyze command when spec is found.

        Args:
            mock_analyzer_class: Mock ProjectAnalyzer class
            runner: CLI runner fixture
        """
        # Mock analyzer instance and response
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        # analyze uses analyze_with_change_detection by default
        mock_analyzer.analyze_with_change_detection.return_value = {
            "openapi_spec_found": True,
            "spec_path": "/path/to/openapi.yaml",
            "spec_format": "yaml",
            "api_title": "Test API",
            "endpoints_count": 5,
            "recommended_jmx_name": "test-api.jmx",
            "changes_detected": False,
            "spec_diff": None,
            "snapshot_exists": False,
            "snapshot_path": None,
        }

        result = runner.invoke(analyze, ["--path", "."])

        assert result.exit_code == 0
        assert "Analyzing project" in result.output
        assert "OpenAPI Specification Found" in result.output
        assert "/path/to/openapi.yaml" in result.output
        assert "Test API" in result.output
        mock_analyzer.analyze_with_change_detection.assert_called_once_with(".", None)

    @patch("jmeter_gen.cli.ProjectAnalyzer")
    def test_analyze_no_spec_found(
        self, mock_analyzer_class: Mock, runner: CliRunner
    ):
        """Test analyze command when no spec is found.

        Args:
            mock_analyzer_class: Mock ProjectAnalyzer class
            runner: CLI runner fixture
        """
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        # analyze uses analyze_with_change_detection by default
        mock_analyzer.analyze_with_change_detection.return_value = {
            "openapi_spec_found": False,
            "message": "No spec found",
        }

        result = runner.invoke(analyze, ["--path", "."])

        assert result.exit_code == 0
        assert "No OpenAPI specification found" in result.output

    @patch("jmeter_gen.cli.ProjectAnalyzer")
    def test_analyze_with_exception(
        self, mock_analyzer_class: Mock, runner: CliRunner
    ):
        """Test analyze command handles exceptions.

        Args:
            mock_analyzer_class: Mock ProjectAnalyzer class
            runner: CLI runner fixture
        """
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        # analyze uses analyze_with_change_detection by default
        # Use OSError as it's one of the caught exception types
        mock_analyzer.analyze_with_change_detection.side_effect = OSError("Test error")

        result = runner.invoke(analyze)

        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Test error" in result.output


class TestGenerateCommand:
    """Test suite for generate command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI runner for testing.

        Returns:
            CliRunner instance
        """
        return CliRunner()

    @pytest.fixture
    def mock_spec_data(self) -> dict:
        """Create mock OpenAPI spec data.

        Returns:
            Mock spec data dictionary
        """
        return {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {"path": "/api/test", "method": "GET", "operationId": "getTest"}
            ],
        }

    @patch("jmeter_gen.cli.JMXGenerator")
    @patch("jmeter_gen.cli.OpenAPIParser")
    def test_generate_with_spec_and_base_url_flag(
        self,
        mock_parser_class: Mock,
        mock_generator_class: Mock,
        runner: CliRunner,
        tmp_path: Path,
        mock_spec_data: dict,
    ):
        """Test generate command with spec file and base-url flag.

        Args:
            mock_parser_class: Mock OpenAPIParser class
            mock_generator_class: Mock JMXGenerator class
            runner: CLI runner fixture
            tmp_path: Pytest temporary directory fixture
            mock_spec_data: Mock spec data fixture
        """
        # Create temp spec file
        spec_file = tmp_path / "openapi.yaml"
        spec_file.write_text("openapi: 3.0.0")

        # Mock parser
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.return_value = mock_spec_data

        # Mock generator
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate.return_value = {
            "success": True,
            "jmx_path": str(tmp_path / "test.jmx"),
            "samplers_created": 1,
            "assertions_added": 1,
            "threads": 10,
            "rampup": 5,
            "duration": 60,
        }

        result = runner.invoke(
            generate,
            [
                "--spec",
                str(spec_file),
                "--output",
                str(tmp_path / "test.jmx"),
                "--base-url",
                "http://staging.example.com",
            ],
        )

        assert result.exit_code == 0
        assert "Generation Complete" in result.output
        assert "JMX file generated successfully" in result.output
        mock_parser.parse.assert_called_once_with(str(spec_file))
        mock_generator.generate.assert_called_once()

        # Verify all arguments were passed correctly
        call_args = mock_generator.generate.call_args
        assert call_args[1]["base_url"] == "http://staging.example.com"
        assert call_args[1]["spec_data"] == mock_spec_data
        assert call_args[1]["output_path"] == str(tmp_path / "test.jmx")

    @patch("jmeter_gen.cli.JMXGenerator")
    @patch("jmeter_gen.cli.OpenAPIParser")
    @patch("jmeter_gen.cli.ProjectAnalyzer")
    def test_generate_without_spec_auto_discover(
        self,
        mock_analyzer_class: Mock,
        mock_parser_class: Mock,
        mock_generator_class: Mock,
        runner: CliRunner,
        tmp_path: Path,
        mock_spec_data: dict,
    ):
        """Test generate command auto-discovers spec when not provided.

        Args:
            mock_analyzer_class: Mock ProjectAnalyzer class
            mock_parser_class: Mock OpenAPIParser class
            mock_generator_class: Mock JMXGenerator class
            runner: CLI runner fixture
            tmp_path: Pytest temporary directory fixture
            mock_spec_data: Mock spec data fixture
        """
        # Mock analyzer - use tmp_path for spec_path so snapshot can be saved
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_analyzer.analyze_project.return_value = {
            "openapi_spec_found": True,
            "spec_path": str(tmp_path / "openapi.yaml"),
            "available_specs": [{"spec_path": str(tmp_path / "openapi.yaml"), "format": "yaml"}],
            "multiple_specs_found": False,
        }
        mock_analyzer.find_scenario_file.return_value = None  # No scenario file for v1 tests

        # Mock parser
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.return_value = mock_spec_data

        # Mock generator
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate.return_value = {
            "success": True,
            "jmx_path": str(tmp_path / "test.jmx"),
            "samplers_created": 1,
            "assertions_added": 1,
            "threads": 10,
            "rampup": 5,
            "duration": 60,
        }

        # Simulate user pressing Enter (empty input for default base URL)
        result = runner.invoke(
            generate, ["--output", str(tmp_path / "test.jmx")], input="\n"
        )

        assert result.exit_code == 0
        assert "No spec file specified, searching project" in result.output
        assert "Using spec" in result.output
        mock_analyzer.analyze_project.assert_called_once_with(".")

    @patch("jmeter_gen.cli.ProjectAnalyzer")
    def test_generate_no_spec_found(
        self, mock_analyzer_class: Mock, runner: CliRunner
    ):
        """Test generate command when no spec found in auto-discovery.

        Args:
            mock_analyzer_class: Mock ProjectAnalyzer class
            runner: CLI runner fixture
        """
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_analyzer.analyze_project.return_value = {"openapi_spec_found": False}

        result = runner.invoke(generate)

        assert result.exit_code == 1
        assert "No OpenAPI spec found" in result.output

    @patch("jmeter_gen.cli.JMXGenerator")
    @patch("jmeter_gen.cli.OpenAPIParser")
    def test_generate_with_custom_parameters(
        self,
        mock_parser_class: Mock,
        mock_generator_class: Mock,
        runner: CliRunner,
        tmp_path: Path,
        mock_spec_data: dict,
    ):
        """Test generate command with custom thread/rampup/duration parameters.

        Args:
            mock_parser_class: Mock OpenAPIParser class
            mock_generator_class: Mock JMXGenerator class
            runner: CliRunner fixture
            tmp_path: Pytest temporary directory fixture
            mock_spec_data: Mock spec data fixture
        """
        spec_file = tmp_path / "openapi.yaml"
        spec_file.write_text("openapi: 3.0.0")

        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.return_value = mock_spec_data

        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate.return_value = {
            "success": True,
            "jmx_path": str(tmp_path / "test.jmx"),
            "samplers_created": 1,
            "assertions_added": 1,
            "threads": 50,
            "rampup": 10,
            "duration": 300,
        }

        result = runner.invoke(
            generate,
            [
                "--spec",
                str(spec_file),
                "--threads",
                "50",
                "--rampup",
                "10",
                "--duration",
                "300",
                "--base-url",
                "http://test.com",
            ],
            input="\n",  # Press Enter for output folder prompt
        )

        assert result.exit_code == 0
        call_args = mock_generator.generate.call_args[1]
        assert call_args["threads"] == 50
        assert call_args["rampup"] == 10
        assert call_args["duration"] == 300

    @patch("jmeter_gen.cli.OpenAPIParser")
    def test_generate_parser_exception(
        self, mock_parser_class: Mock, runner: CliRunner, tmp_path: Path
    ):
        """Test generate command handles parser exceptions.

        Args:
            mock_parser_class: Mock OpenAPIParser class
            runner: CLI runner fixture
            tmp_path: Pytest temporary directory fixture
        """
        spec_file = tmp_path / "openapi.yaml"
        spec_file.write_text("invalid")

        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.side_effect = Exception("Parse error")

        result = runner.invoke(generate, ["--spec", str(spec_file)])

        assert result.exit_code == 1
        assert "error" in result.output.lower()

    @patch("jmeter_gen.cli.JMXGenerator")
    @patch("jmeter_gen.cli.OpenAPIParser")
    def test_generate_failure_returns_false(
        self,
        mock_parser_class: Mock,
        mock_generator_class: Mock,
        runner: CliRunner,
        tmp_path: Path,
        mock_spec_data: dict,
    ):
        """Test generate command when generation returns success=False.

        Args:
            mock_parser_class: Mock OpenAPIParser class
            mock_generator_class: Mock JMXGenerator class
            runner: CLI runner fixture
            tmp_path: Pytest temporary directory fixture
            mock_spec_data: Mock spec data fixture
        """
        spec_file = tmp_path / "openapi.yaml"
        spec_file.write_text("openapi: 3.0.0")

        # Mock parser
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.return_value = mock_spec_data

        # Mock generator to return failure
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate.return_value = {
            "success": False,
            "error": "Generation failed",
        }

        result = runner.invoke(
            generate,
            [
                "--spec",
                str(spec_file),
                "--base-url",
                "http://test.com",
            ],
            input="\n",  # Press Enter for output folder prompt
        )

        assert result.exit_code == 1
        assert "JMX generation failed" in result.output


class TestValidateCommand:
    """Test suite for validate command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI runner for testing.

        Returns:
            CliRunner instance
        """
        return CliRunner()

    @patch("jmeter_gen.cli.JMXValidator")
    def test_validate_valid_jmx(
        self, mock_validator_class: Mock, runner: CliRunner, tmp_path: Path
    ):
        """Test validate command with valid JMX file.

        Args:
            mock_validator_class: Mock JMXValidator class
            runner: CLI runner fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_file = tmp_path / "test.jmx"
        jmx_file.write_text('<?xml version="1.0"?><jmeterTestPlan/>')

        mock_validator = Mock()
        mock_validator_class.return_value = mock_validator
        mock_validator.validate.return_value = {
            "valid": True,
            "issues": [],
            "recommendations": ["Add CSV config", "Add timers"],
        }

        result = runner.invoke(validate, [str(jmx_file)])

        assert result.exit_code == 0
        assert "JMX file is valid" in result.output
        assert "Recommendations" in result.output
        assert "Add CSV config" in result.output
        mock_validator.validate.assert_called_once_with(str(jmx_file))

    @patch("jmeter_gen.cli.JMXValidator")
    def test_validate_invalid_jmx(
        self, mock_validator_class: Mock, runner: CliRunner, tmp_path: Path
    ):
        """Test validate command with invalid JMX file.

        Args:
            mock_validator_class: Mock JMXValidator class
            runner: CLI runner fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_file = tmp_path / "test.jmx"
        jmx_file.write_text('<?xml version="1.0"?><jmeterTestPlan/>')

        mock_validator = Mock()
        mock_validator_class.return_value = mock_validator
        mock_validator.validate.return_value = {
            "valid": False,
            "issues": ["Missing ThreadGroup", "No samplers found"],
            "recommendations": [],
        }

        result = runner.invoke(validate, [str(jmx_file)])

        assert result.exit_code == 1
        assert "JMX file has 2 issue(s)" in result.output
        assert "Missing ThreadGroup" in result.output
        assert "No samplers found" in result.output

    def test_validate_file_not_found(self, runner: CliRunner):
        """Test validate command with nonexistent file.

        Args:
            runner: CLI runner fixture
        """
        result = runner.invoke(validate, ["/nonexistent/file.jmx"])

        # Click returns exit code 2 for usage errors
        assert result.exit_code == 2
        assert "does not exist" in result.output

    @patch("jmeter_gen.cli.JMXValidator")
    def test_validate_with_exception(
        self, mock_validator_class: Mock, runner: CliRunner, tmp_path: Path
    ):
        """Test validate command handles exceptions.

        Args:
            mock_validator_class: Mock JMXValidator class
            runner: CLI runner fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_file = tmp_path / "test.jmx"
        jmx_file.write_text("invalid")

        mock_validator = Mock()
        mock_validator_class.return_value = mock_validator
        mock_validator.validate.side_effect = Exception("Validation error")

        result = runner.invoke(validate, [str(jmx_file)])

        assert result.exit_code == 1
        assert "Error" in result.output

    @patch("jmeter_gen.cli.JMXValidator")
    def test_validate_file_not_found_exception(
        self, mock_validator_class: Mock, runner: CliRunner, tmp_path: Path
    ):
        """Test validate command handles FileNotFoundError exception.

        Args:
            mock_validator_class: Mock JMXValidator class
            runner: CLI runner fixture
            tmp_path: Pytest temporary directory fixture
        """
        # Create a file path that exists for Click validation but will raise FileNotFoundError
        jmx_file = tmp_path / "test.jmx"
        jmx_file.write_text("test")

        mock_validator = Mock()
        mock_validator_class.return_value = mock_validator
        mock_validator.validate.side_effect = FileNotFoundError("File disappeared")

        result = runner.invoke(validate, [str(jmx_file)])

        assert result.exit_code == 1
        assert "File not found" in result.output


class TestMCPCommand:
    """Test suite for mcp command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI runner for testing.

        Returns:
            CliRunner instance
        """
        return CliRunner()

    def test_mcp_server_starts(self, runner: CliRunner):
        """Test MCP command shows server starting message.

        Args:
            runner: CLI runner fixture
        """
        # Note: We can't actually run the server in tests as it blocks,
        # but we can verify the command structure is correct
        # The server would normally run indefinitely, so we just check
        # that the import works and doesn't raise an exception
        try:
            from jmeter_gen.mcp_server import run_server
            # Verify function exists and is callable
            assert callable(run_server)
        except ImportError:
            # MCP dependencies may not be fully installed in test environment
            pytest.skip("MCP dependencies not available")

    @patch.dict("sys.modules", {"jmeter_gen.mcp_server": Mock()})
    def test_mcp_server_keyboard_interrupt(self, runner: CliRunner):
        """Test MCP command handles keyboard interrupt gracefully.

        Args:
            runner: CLI runner fixture
        """
        import sys
        sys.modules["jmeter_gen.mcp_server"].run_server.side_effect = KeyboardInterrupt()

        result = runner.invoke(mcp)

        assert result.exit_code == 0
        assert "MCP Server stopped by user" in result.output

    @patch.dict("sys.modules", {"jmeter_gen.mcp_server": Mock()})
    def test_mcp_server_exception(self, runner: CliRunner):
        """Test MCP command handles general exceptions.

        Args:
            runner: CLI runner fixture
        """
        import sys
        sys.modules["jmeter_gen.mcp_server"].run_server.side_effect = Exception("Server startup error")

        result = runner.invoke(mcp)

        assert result.exit_code == 1
        assert "Error starting MCP server" in result.output
        assert "Server startup error" in result.output


class TestAnalyzeCommandFlags:
    """Test suite for analyze command flags."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI runner for testing."""
        return CliRunner()

    @patch("jmeter_gen.cli.ProjectAnalyzer")
    def test_analyze_change_detection_enabled_by_default(
        self, mock_analyzer_class: Mock, runner: CliRunner
    ):
        """Test analyze command uses change detection by default."""
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_analyzer.analyze_with_change_detection.return_value = {
            "openapi_spec_found": True,
            "spec_path": "/path/to/openapi.yaml",
            "spec_format": "yaml",
            "api_title": "Test API",
            "endpoints_count": 5,
            "recommended_jmx_name": "test-api-test.jmx",
            "available_specs": [],
            "multiple_specs_found": False,
            "snapshot_exists": False,
            "changes_detected": False,
        }

        # No flags - should use change detection by default
        result = runner.invoke(analyze, [])

        assert result.exit_code == 0
        mock_analyzer.analyze_with_change_detection.assert_called_once_with(".", None)

    @patch("jmeter_gen.cli.ProjectAnalyzer")
    def test_analyze_no_detect_changes_flag(
        self, mock_analyzer_class: Mock, runner: CliRunner
    ):
        """Test analyze command with --no-detect-changes flag."""
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_analyzer.analyze_project.return_value = {
            "openapi_spec_found": True,
            "spec_path": "/path/to/openapi.yaml",
            "spec_format": "yaml",
            "api_title": "Test API",
            "endpoints_count": 5,
            "recommended_jmx_name": "test-api-test.jmx",
            "available_specs": [],
            "multiple_specs_found": False,
        }

        result = runner.invoke(analyze, ["--no-detect-changes"])

        assert result.exit_code == 0
        # Should call analyze_project instead of analyze_with_change_detection
        mock_analyzer.analyze_project.assert_called_once_with(".")

    @patch("jmeter_gen.cli.ProjectAnalyzer")
    def test_analyze_export_diff_flag(
        self, mock_analyzer_class: Mock, runner: CliRunner, tmp_path: Path
    ):
        """Test analyze command with --export-diff flag."""
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        # Mock spec_diff object
        mock_diff = Mock()
        mock_diff.summary = "1 added, 0 removed, 0 modified"
        mock_diff.added_endpoints = []
        mock_diff.removed_endpoints = []
        mock_diff.modified_endpoints = []
        mock_diff.to_dict.return_value = {"summary": "1 added, 0 removed, 0 modified"}

        mock_analyzer.analyze_with_change_detection.return_value = {
            "openapi_spec_found": True,
            "spec_path": "/path/to/openapi.yaml",
            "spec_format": "yaml",
            "api_title": "Test API",
            "endpoints_count": 5,
            "recommended_jmx_name": "test-api-test.jmx",
            "available_specs": [],
            "multiple_specs_found": False,
            "snapshot_exists": True,
            "changes_detected": True,
            "spec_diff": mock_diff,
        }

        diff_file = tmp_path / "changes.json"
        result = runner.invoke(analyze, ["--export-diff", str(diff_file)])

        assert result.exit_code == 0
        assert diff_file.exists()

    @patch("jmeter_gen.cli.ProjectAnalyzer")
    def test_analyze_show_details_flag(
        self, mock_analyzer_class: Mock, runner: CliRunner
    ):
        """Test analyze command with --show-details flag."""
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        # Mock spec_diff object with details - must have proper summary dict
        mock_endpoint = Mock()
        mock_endpoint.method = "POST"
        mock_endpoint.path = "/api/users"
        mock_endpoint.operation_id = "createUser"
        mock_endpoint.changes = {"description": "changed"}

        mock_diff = Mock()
        mock_diff.summary = {"added": 0, "removed": 0, "modified": 1}
        mock_diff.has_changes = True
        mock_diff.added_endpoints = []
        mock_diff.removed_endpoints = []
        mock_diff.modified_endpoints = [mock_endpoint]

        mock_analyzer.analyze_with_change_detection.return_value = {
            "openapi_spec_found": True,
            "spec_path": "/path/to/openapi.yaml",
            "spec_format": "yaml",
            "api_title": "Test API",
            "endpoints_count": 5,
            "recommended_jmx_name": "test-api-test.jmx",
            "available_specs": [],
            "multiple_specs_found": False,
            "snapshot_exists": True,
            "changes_detected": True,
            "spec_diff": mock_diff,
        }

        result = runner.invoke(analyze, ["--show-details"])

        assert result.exit_code == 0
        # Should show detailed breakdown
        assert "Modified" in result.output


class TestGenerateCommandFlags:
    """Test suite for generate command flags."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def mock_spec_data(self) -> dict:
        """Create mock OpenAPI spec data."""
        return {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:3000",
            "endpoints": [
                {
                    "path": "/api/users",
                    "method": "GET",
                    "operationId": "getUsers",
                    "summary": "Get all users",
                }
            ],
        }

    @patch("jmeter_gen.cli.JMXGenerator")
    @patch("jmeter_gen.cli.OpenAPIParser")
    def test_generate_endpoints_flag(
        self,
        mock_parser_class: Mock,
        mock_generator_class: Mock,
        runner: CliRunner,
        tmp_path: Path,
        mock_spec_data: dict,
    ):
        """Test generate command with --endpoints flag."""
        spec_file = tmp_path / "openapi.yaml"
        spec_file.write_text("openapi: 3.0.0")

        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.return_value = mock_spec_data

        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate.return_value = {
            "success": True,
            "jmx_path": str(tmp_path / "test.jmx"),
            "samplers_created": 1,
            "assertions_added": 1,
            "threads": 1,
            "rampup": 0,
            "duration": None,
        }

        result = runner.invoke(
            generate,
            [
                "--spec", str(spec_file),
                "--endpoints", "getUsers",
                "--endpoints", "createUser",
                "--base-url", "http://test.com",
            ],
            input="\n",  # Press Enter for output folder prompt
        )

        assert result.exit_code == 0
        call_args = mock_generator.generate.call_args[1]
        # Endpoints are passed as list, not tuple
        assert list(call_args["endpoints"]) == ["getUsers", "createUser"]

    def test_generate_auto_update_flag_accepted(
        self,
        runner: CliRunner,
    ):
        """Test generate command accepts --auto-update flag without error."""
        # Just verify the flag is recognized and doesn't cause argument errors
        result = runner.invoke(
            generate,
            ["--help"],
        )

        assert result.exit_code == 0
        assert "--auto-update" in result.output
        assert "Auto-update JMX" in result.output

    @patch("jmeter_gen.cli.JMXGenerator")
    @patch("jmeter_gen.cli.OpenAPIParser")
    def test_generate_force_new_flag(
        self,
        mock_parser_class: Mock,
        mock_generator_class: Mock,
        runner: CliRunner,
        tmp_path: Path,
        mock_spec_data: dict,
    ):
        """Test generate command with --force-new flag."""
        spec_file = tmp_path / "openapi.yaml"
        spec_file.write_text("openapi: 3.0.0")
        jmx_file = tmp_path / "test.jmx"
        jmx_file.write_text('<?xml version="1.0"?><jmeterTestPlan/>')

        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.return_value = mock_spec_data

        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate.return_value = {
            "success": True,
            "jmx_path": str(jmx_file),
            "samplers_created": 1,
            "assertions_added": 1,
            "threads": 1,
            "rampup": 0,
            "duration": None,
        }

        result = runner.invoke(
            generate,
            [
                "--spec", str(spec_file),
                "--output", str(jmx_file),
                "--force-new",
                "--base-url", "http://test.com",
            ],
        )

        assert result.exit_code == 0
        # With force-new, should call generator.generate directly
        mock_generator.generate.assert_called_once()
        # Verify key arguments
        call_args = mock_generator.generate.call_args[1]
        assert call_args["spec_data"] == mock_spec_data
        assert call_args["output_path"] == str(jmx_file)
        assert call_args["base_url"] == "http://test.com"

    @patch("jmeter_gen.cli.SnapshotManager")
    @patch("jmeter_gen.cli.JMXGenerator")
    @patch("jmeter_gen.cli.OpenAPIParser")
    def test_generate_no_snapshot_flag(
        self,
        mock_parser_class: Mock,
        mock_generator_class: Mock,
        mock_snapshot_class: Mock,
        runner: CliRunner,
        tmp_path: Path,
        mock_spec_data: dict,
    ):
        """Test generate command with --no-snapshot flag."""
        spec_file = tmp_path / "openapi.yaml"
        spec_file.write_text("openapi: 3.0.0")

        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.return_value = mock_spec_data

        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate.return_value = {
            "success": True,
            "jmx_path": str(tmp_path / "test.jmx"),
            "samplers_created": 1,
            "assertions_added": 1,
            "threads": 1,
            "rampup": 0,
            "duration": None,
        }

        result = runner.invoke(
            generate,
            [
                "--spec", str(spec_file),
                "--no-snapshot",
                "--base-url", "http://test.com",
            ],
            input="\n",  # Press Enter for output folder prompt
        )

        assert result.exit_code == 0
        # With --no-snapshot, save_snapshot should NOT be called
        mock_snapshot_class.return_value.save_snapshot.assert_not_called()


class TestUserInteraction:
    """Test suite for user interaction (prompts, confirmations)."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def mock_spec_data(self) -> dict:
        """Create mock OpenAPI spec data."""
        return {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:3000",
            "endpoints": [
                {
                    "path": "/api/users",
                    "method": "GET",
                    "operationId": "getUsers",
                    "summary": "Get all users",
                }
            ],
        }

    @patch("jmeter_gen.cli.JMXGenerator")
    @patch("jmeter_gen.cli.OpenAPIParser")
    def test_generate_base_url_prompt_uses_default(
        self,
        mock_parser_class: Mock,
        mock_generator_class: Mock,
        runner: CliRunner,
        tmp_path: Path,
        mock_spec_data: dict,
    ):
        """Test generate command prompts for base URL and uses default on empty input."""
        spec_file = tmp_path / "openapi.yaml"
        spec_file.write_text("openapi: 3.0.0")

        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.return_value = mock_spec_data

        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate.return_value = {
            "success": True,
            "jmx_path": str(tmp_path / "test.jmx"),
            "samplers_created": 1,
            "assertions_added": 1,
            "threads": 1,
            "rampup": 0,
            "duration": None,
        }

        # Simulate user pressing Enter for both output folder and base URL
        result = runner.invoke(
            generate,
            ["--spec", str(spec_file)],
            input="\n\n",  # Press Enter for output folder + base URL
        )

        assert result.exit_code == 0
        # Check the generator was called with spec's base_url
        call_args = mock_generator.generate.call_args[1]
        assert call_args["base_url"] == "http://localhost:3000"

    @patch("jmeter_gen.cli.JMXGenerator")
    @patch("jmeter_gen.cli.OpenAPIParser")
    def test_generate_base_url_prompt_uses_custom_input(
        self,
        mock_parser_class: Mock,
        mock_generator_class: Mock,
        runner: CliRunner,
        tmp_path: Path,
        mock_spec_data: dict,
    ):
        """Test generate command uses custom base URL from user input."""
        spec_file = tmp_path / "openapi.yaml"
        spec_file.write_text("openapi: 3.0.0")

        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.return_value = mock_spec_data

        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate.return_value = {
            "success": True,
            "jmx_path": str(tmp_path / "test.jmx"),
            "samplers_created": 1,
            "assertions_added": 1,
            "threads": 1,
            "rampup": 0,
            "duration": None,
        }

        # Simulate user pressing Enter for output folder, then entering custom URL
        result = runner.invoke(
            generate,
            ["--spec", str(spec_file)],
            input="\nhttp://custom.example.com:8080\n",  # Default folder + custom URL
        )

        assert result.exit_code == 0
        # Check the generator was called with custom base_url
        call_args = mock_generator.generate.call_args[1]
        assert call_args["base_url"] == "http://custom.example.com:8080"

    @patch("jmeter_gen.cli.JMXGenerator")
    @patch("jmeter_gen.cli.OpenAPIParser")
    @patch("jmeter_gen.cli.ProjectAnalyzer")
    def test_generate_multiple_specs_prompts_selection(
        self,
        mock_analyzer_class: Mock,
        mock_parser_class: Mock,
        mock_generator_class: Mock,
        runner: CliRunner,
        tmp_path: Path,
        mock_spec_data: dict,
    ):
        """Test generate command prompts for spec selection when multiple found."""
        # Create two mock spec files
        spec1 = tmp_path / "openapi.yaml"
        spec1.write_text("openapi: 3.0.0")
        spec2 = tmp_path / "swagger.json"
        spec2.write_text('{"swagger": "2.0"}')

        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_analyzer.analyze_project.return_value = {
            "openapi_spec_found": True,
            "spec_path": str(spec1),
            "available_specs": [
                {"spec_path": str(spec1), "format": "yaml"},
                {"spec_path": str(spec2), "format": "json"},
            ],
            "multiple_specs_found": True,
        }
        mock_analyzer.find_scenario_file.return_value = None  # No scenario file for v1 tests

        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.return_value = mock_spec_data

        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate.return_value = {
            "success": True,
            "jmx_path": str(tmp_path / "test.jmx"),
            "samplers_created": 1,
            "assertions_added": 1,
            "threads": 1,
            "rampup": 0,
            "duration": None,
        }

        # Simulate user selecting first spec (1) and then pressing Enter for default base URL
        result = runner.invoke(
            generate,
            ["--output", str(tmp_path / "test.jmx")],
            input="1\n\n",  # Select first spec, then default base URL
        )

        assert result.exit_code == 0
        # Verify the prompt about multiple specs was shown
        assert "multiple" in result.output.lower() or "spec" in result.output.lower()

    @patch("jmeter_gen.cli.JMXGenerator")
    @patch("jmeter_gen.cli.OpenAPIParser")
    def test_generate_output_folder_prompt_uses_default(
        self,
        mock_parser_class: Mock,
        mock_generator_class: Mock,
        runner: CliRunner,
        tmp_path: Path,
        mock_spec_data: dict,
    ):
        """Test generate command uses current directory when Enter pressed for output folder."""
        spec_file = tmp_path / "openapi.yaml"
        spec_file.write_text("openapi: 3.0.0")

        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.return_value = mock_spec_data

        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate.return_value = {
            "success": True,
            "jmx_path": "./test-api-test.jmx",
            "samplers_created": 1,
            "assertions_added": 1,
            "threads": 1,
            "rampup": 0,
            "duration": None,
        }

        # Press Enter for both output folder and base URL
        result = runner.invoke(
            generate,
            ["--spec", str(spec_file)],
            input="\n\n",
        )

        assert result.exit_code == 0
        # Verify output folder prompt was shown
        assert "Output Folder Configuration" in result.output
        assert "Default folder:" in result.output
        # Verify output path uses current directory (. resolves to just filename)
        call_args = mock_generator.generate.call_args[1]
        assert call_args["output_path"] == "test-api-test.jmx"

    @patch("jmeter_gen.cli.JMXGenerator")
    @patch("jmeter_gen.cli.OpenAPIParser")
    def test_generate_output_folder_prompt_uses_custom_folder(
        self,
        mock_parser_class: Mock,
        mock_generator_class: Mock,
        runner: CliRunner,
        tmp_path: Path,
        mock_spec_data: dict,
    ):
        """Test generate command uses custom folder from user input."""
        spec_file = tmp_path / "openapi.yaml"
        spec_file.write_text("openapi: 3.0.0")

        custom_folder = str(tmp_path / "custom_output")

        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.return_value = mock_spec_data

        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate.return_value = {
            "success": True,
            "jmx_path": f"{custom_folder}/test-api-test.jmx",
            "samplers_created": 1,
            "assertions_added": 1,
            "threads": 1,
            "rampup": 0,
            "duration": None,
        }

        # Enter custom folder, then press Enter for base URL
        result = runner.invoke(
            generate,
            ["--spec", str(spec_file)],
            input=f"{custom_folder}\n\n",
        )

        assert result.exit_code == 0
        # Verify output path uses custom folder
        call_args = mock_generator.generate.call_args[1]
        assert custom_folder in call_args["output_path"]
        assert call_args["output_path"].endswith("test-api-test.jmx")

    @patch("jmeter_gen.cli.JMXGenerator")
    @patch("jmeter_gen.cli.OpenAPIParser")
    def test_generate_output_flag_skips_folder_prompt(
        self,
        mock_parser_class: Mock,
        mock_generator_class: Mock,
        runner: CliRunner,
        tmp_path: Path,
        mock_spec_data: dict,
    ):
        """Test generate command skips output folder prompt when --output is provided."""
        spec_file = tmp_path / "openapi.yaml"
        spec_file.write_text("openapi: 3.0.0")
        output_file = tmp_path / "my-output.jmx"

        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.return_value = mock_spec_data

        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate.return_value = {
            "success": True,
            "jmx_path": str(output_file),
            "samplers_created": 1,
            "assertions_added": 1,
            "threads": 1,
            "rampup": 0,
            "duration": None,
        }

        # Only base URL prompt when --output is provided
        result = runner.invoke(
            generate,
            ["--spec", str(spec_file), "--output", str(output_file)],
            input="\n",  # Only base URL prompt
        )

        assert result.exit_code == 0
        # Verify output folder prompt was NOT shown
        assert "Output Folder Configuration" not in result.output
        # Verify the specified output path was used
        call_args = mock_generator.generate.call_args[1]
        assert call_args["output_path"] == str(output_file)
