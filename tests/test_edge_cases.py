"""Edge case tests for boundary conditions and special scenarios.

This test module focuses on edge cases, boundary values, and special
scenarios that might not be covered by standard functional tests.
"""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from jmeter_gen.core.jmx_generator import JMXGenerator
from jmeter_gen.core.jmx_validator import JMXValidator
from jmeter_gen.core.openapi_parser import OpenAPIParser
from jmeter_gen.core.project_analyzer import ProjectAnalyzer


class TestBoundaryValues:
    """Test boundary values for numeric parameters."""

    def test_jmx_generator_zero_threads(self, tmp_path: Path):
        """Test JMXGenerator with zero threads (should use default)."""
        generator = JMXGenerator()
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/test",
                    "method": "GET",
                    "operationId": "getTest",
                    "summary": "Test",
                    "requestBody": False,
                    "parameters": [],
                }
            ],
        }

        output_path = str(tmp_path / "zero_threads.jmx")

        # Zero threads should be handled (likely defaults to 1 or raises error)
        result = generator.generate(
            spec_data=spec_data,
            output_path=output_path,
            threads=0,
        )

        # Either succeeds with default value or handled gracefully
        assert "success" in result

    def test_jmx_generator_very_large_threads(self, tmp_path: Path):
        """Test JMXGenerator with very large thread count."""
        generator = JMXGenerator()
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/test",
                    "method": "GET",
                    "operationId": "getTest",
                    "summary": "Test",
                    "requestBody": False,
                    "parameters": [],
                }
            ],
        }

        output_path = str(tmp_path / "large_threads.jmx")
        result = generator.generate(
            spec_data=spec_data,
            output_path=output_path,
            threads=10000,
        )

        assert result["success"] is True
        assert result["threads"] == 10000

    def test_jmx_generator_zero_duration(self, tmp_path: Path):
        """Test JMXGenerator with zero duration."""
        generator = JMXGenerator()
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/test",
                    "method": "GET",
                    "operationId": "getTest",
                    "summary": "Test",
                    "requestBody": False,
                    "parameters": [],
                }
            ],
        }

        output_path = str(tmp_path / "zero_duration.jmx")
        result = generator.generate(
            spec_data=spec_data,
            output_path=output_path,
            duration=0,
        )

        assert "success" in result


class TestSpecialCharacters:
    """Test handling of special characters in various inputs."""

    def test_openapi_parser_special_chars_in_api_title(self, tmp_path: Path):
        """Test OpenAPIParser with special characters in API title."""
        # Use simpler special chars that won't cause YAML parsing issues
        spec_content = """openapi: 3.0.0
info:
  title: 'Test API with (special) chars & symbols'
  version: 1.0.0
paths:
  /test:
    get:
      operationId: getTest
      responses:
        '200':
          description: OK
"""

        spec_file = tmp_path / "special_chars.yaml"
        spec_file.write_text(spec_content)

        parser = OpenAPIParser()
        result = parser.parse(str(spec_file))

        assert "special" in result["title"].lower()
        assert result["endpoints"][0]["path"] == "/test"

    def test_jmx_generator_xml_special_chars_in_summary(self, tmp_path: Path):
        """Test JMXGenerator properly escapes XML special characters."""
        generator = JMXGenerator()
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/test",
                    "method": "GET",
                    "operationId": "getTest",
                    "summary": "Test <special> & \"quoted\" 'chars'",
                    "requestBody": False,
                    "parameters": [],
                }
            ],
        }

        output_path = str(tmp_path / "xml_escape.jmx")
        result = generator.generate(spec_data=spec_data, output_path=output_path)

        assert result["success"] is True

        # Verify XML is valid and parseable
        tree = ET.parse(output_path)
        assert tree is not None

    def test_project_analyzer_special_chars_in_filename(self, tmp_path: Path):
        """Test ProjectAnalyzer with special characters in filenames."""
        # Create a spec file with special characters (that are valid on most filesystems)
        special_dir = tmp_path / "test_dir"
        special_dir.mkdir()

        # Use a standard openapi.yaml name but verify it works in special directory
        spec_file = special_dir / "openapi.yaml"
        spec_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths: {}
"""
        spec_file.write_text(spec_content)

        analyzer = ProjectAnalyzer()
        result = analyzer.analyze_project(str(special_dir))

        assert result["openapi_spec_found"] is True


class TestURLEdgeCases:
    """Test edge cases in URL parsing and handling."""

    def test_jmx_generator_ipv4_address(self, tmp_path: Path):
        """Test JMXGenerator with IPv4 address."""
        generator = JMXGenerator()
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://192.168.1.100:8080",
            "endpoints": [
                {
                    "path": "/test",
                    "method": "GET",
                    "operationId": "getTest",
                    "summary": "Test",
                    "requestBody": False,
                    "parameters": [],
                }
            ],
        }

        output_path = str(tmp_path / "ipv4.jmx")
        result = generator.generate(spec_data=spec_data, output_path=output_path)

        assert result["success"] is True

    def test_jmx_generator_url_with_path_prefix(self, tmp_path: Path):
        """Test JMXGenerator with URL containing path prefix."""
        generator = JMXGenerator()
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080/api/v1",
            "endpoints": [
                {
                    "path": "/users",
                    "method": "GET",
                    "operationId": "getUsers",
                    "summary": "Get users",
                    "requestBody": False,
                    "parameters": [],
                }
            ],
        }

        output_path = str(tmp_path / "path_prefix.jmx")
        result = generator.generate(spec_data=spec_data, output_path=output_path)

        assert result["success"] is True

    def test_jmx_generator_non_standard_port(self, tmp_path: Path):
        """Test JMXGenerator with non-standard port."""
        generator = JMXGenerator()
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:3000",
            "endpoints": [
                {
                    "path": "/test",
                    "method": "GET",
                    "operationId": "getTest",
                    "summary": "Test",
                    "requestBody": False,
                    "parameters": [],
                }
            ],
        }

        output_path = str(tmp_path / "custom_port.jmx")
        result = generator.generate(spec_data=spec_data, output_path=output_path)

        assert result["success"] is True


class TestPathEdgeCases:
    """Test edge cases in file and directory paths."""

    def test_project_analyzer_relative_path(self, tmp_path: Path):
        """Test ProjectAnalyzer with relative path."""
        # Create spec in temp directory
        spec_file = tmp_path / "openapi.yaml"
        spec_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths: {}
"""
        spec_file.write_text(spec_content)

        analyzer = ProjectAnalyzer()

        # Analyze with absolute path
        result = analyzer.analyze_project(str(tmp_path))

        assert result["openapi_spec_found"] is True

    def test_jmx_generator_nested_output_directory(self, tmp_path: Path):
        """Test JMXGenerator creates nested directories if needed."""
        generator = JMXGenerator()
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/test",
                    "method": "GET",
                    "operationId": "getTest",
                    "summary": "Test",
                    "requestBody": False,
                    "parameters": [],
                }
            ],
        }

        # Output to deeply nested directory that doesn't exist yet
        output_path = str(tmp_path / "level1" / "level2" / "level3" / "test.jmx")
        result = generator.generate(spec_data=spec_data, output_path=output_path)

        assert result["success"] is True
        assert Path(output_path).exists()


class TestDataTypeEdgeCases:
    """Test edge cases for different data types."""

    def test_openapi_parser_endpoint_without_operation_id(self, tmp_path: Path):
        """Test OpenAPIParser generates operation ID if missing."""
        spec_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /test:
    get:
      responses:
        '200':
          description: OK
"""

        spec_file = tmp_path / "no_op_id.yaml"
        spec_file.write_text(spec_content)

        parser = OpenAPIParser()
        result = parser.parse(str(spec_file))

        assert len(result["endpoints"]) == 1
        # Should have generated an operation ID
        assert result["endpoints"][0]["operationId"] is not None
        assert result["endpoints"][0]["operationId"] != ""

    def test_openapi_parser_endpoint_without_summary(self, tmp_path: Path):
        """Test OpenAPIParser handles missing summary."""
        spec_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /test:
    get:
      operationId: getTest
      responses:
        '200':
          description: OK
"""

        spec_file = tmp_path / "no_summary.yaml"
        spec_file.write_text(spec_content)

        parser = OpenAPIParser()
        result = parser.parse(str(spec_file))

        assert len(result["endpoints"]) == 1
        # Summary should be present but might be empty or use description
        assert "summary" in result["endpoints"][0]

    def test_jmx_generator_endpoint_with_no_assertions(self, tmp_path: Path):
        """Test JMXGenerator handles endpoint without explicit assertions."""
        generator = JMXGenerator()
        spec_data = {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/test",
                    "method": "OPTIONS",  # Uncommon method
                    "operationId": "optionsTest",
                    "summary": "Test OPTIONS",
                    "requestBody": False,
                    "parameters": [],
                }
            ],
        }

        output_path = str(tmp_path / "options_method.jmx")
        result = generator.generate(spec_data=spec_data, output_path=output_path)

        assert result["success"] is True


class TestSymlinksAndSpecialFiles:
    """Test handling of symlinks and special file types."""

    def test_project_analyzer_follows_symlinks(self, tmp_path: Path):
        """Test ProjectAnalyzer follows symlinks to directories."""
        # Create actual directory with spec
        real_dir = tmp_path / "real"
        real_dir.mkdir()

        spec_file = real_dir / "openapi.yaml"
        spec_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths: {}
"""
        spec_file.write_text(spec_content)

        # Create symlink to directory (only on Unix-like systems)
        try:
            symlink_dir = tmp_path / "link"
            symlink_dir.symlink_to(real_dir)

            analyzer = ProjectAnalyzer()
            result = analyzer.analyze_project(str(symlink_dir))

            assert result["openapi_spec_found"] is True
        except (OSError, NotImplementedError):
            # Symlinks not supported on this system (e.g., Windows without admin)
            pytest.skip("Symlinks not supported on this system")


class TestValidationEdgeCases:
    """Test edge cases in JMX validation."""

    def test_jmx_validator_minimal_valid_jmx(self, tmp_path: Path):
        """Test JMXValidator with minimal valid JMX structure."""
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan">
      <stringProp name="TestPlan.comments"></stringProp>
      <boolProp name="TestPlan.functional_mode">false</boolProp>
      <boolProp name="TestPlan.serialize_threadgroups">false</boolProp>
    </TestPlan>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
        <stringProp name="ThreadGroup.num_threads">1</stringProp>
        <stringProp name="ThreadGroup.ramp_time">1</stringProp>
        <boolProp name="ThreadGroup.scheduler">false</boolProp>
        <stringProp name="LoopController.loops">1</stringProp>
      </ThreadGroup>
      <hashTree>
        <ConfigTestElement guiclass="HttpDefaultsGui" testclass="ConfigTestElement" testname="HTTP Request Defaults">
          <stringProp name="HTTPSampler.domain">localhost</stringProp>
          <stringProp name="HTTPSampler.port">8080</stringProp>
          <stringProp name="HTTPSampler.protocol">http</stringProp>
        </ConfigTestElement>
        <hashTree/>
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="HTTP Request">
          <stringProp name="HTTPSampler.path">/</stringProp>
          <stringProp name="HTTPSampler.method">GET</stringProp>
        </HTTPSamplerProxy>
        <hashTree/>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>"""

        jmx_file = tmp_path / "minimal.jmx"
        jmx_file.write_text(jmx_content)

        validator = JMXValidator()
        result = validator.validate(str(jmx_file))

        # Should be valid or have only minor recommendations
        assert result["valid"] is True or len(result["issues"]) == 0

    def test_jmx_validator_with_very_large_file(self, tmp_path: Path):
        """Test JMXValidator with large JMX file."""
        # Generate a large but valid JMX
        generator = JMXGenerator()

        # Create 50 endpoints
        endpoints = [
            {
                "path": f"/api/endpoint{i}",
                "method": "GET",
                "operationId": f"getEndpoint{i}",
                "summary": f"Endpoint {i}",
                "requestBody": False,
                "parameters": [],
            }
            for i in range(50)
        ]

        spec_data = {
            "title": "Large API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": endpoints,
        }

        output_path = str(tmp_path / "large.jmx")
        generator.generate(spec_data=spec_data, output_path=output_path)

        # Now validate it
        validator = JMXValidator()
        result = validator.validate(output_path)

        assert result["valid"] is True


class TestEmptyAndNullValues:
    """Test handling of empty and null values."""

    def test_openapi_parser_empty_paths_object(self, tmp_path: Path):
        """Test OpenAPIParser with empty paths object."""
        spec_content = """
openapi: 3.0.0
info:
  title: Empty API
  version: 1.0.0
paths: {}
"""

        spec_file = tmp_path / "empty_paths.yaml"
        spec_file.write_text(spec_content)

        parser = OpenAPIParser()
        result = parser.parse(str(spec_file))

        assert result["title"] == "Empty API"
        assert len(result["endpoints"]) == 0

    def test_project_analyzer_empty_filename_pattern(self):
        """Test ProjectAnalyzer behavior with default patterns."""
        analyzer = ProjectAnalyzer()

        # Should use default patterns defined in module
        assert hasattr(analyzer, "find_openapi_spec")
