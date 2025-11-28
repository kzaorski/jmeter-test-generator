"""Unit tests for ProjectAnalyzer v2 methods."""

import pytest

from jmeter_gen.core.project_analyzer import ProjectAnalyzer

# Mark all tests in this module as v2 tests
pytestmark = pytest.mark.v2


class TestProjectAnalyzerV2Methods:
    """Tests for v2 methods added to ProjectAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create an analyzer instance."""
        return ProjectAnalyzer()

    # find_scenario_file tests

    def test_find_scenario_file_pt_scenario_yaml(self, analyzer, tmp_path):
        """Test finding pt_scenario.yaml in root."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "Step"
    endpoint: "GET /test"
"""
        (tmp_path / "pt_scenario.yaml").write_text(scenario_content)

        result = analyzer.find_scenario_file(str(tmp_path))

        assert result is not None
        assert "pt_scenario.yaml" in result

    def test_find_scenario_file_pt_scenario_yml(self, analyzer, tmp_path):
        """Test finding pt_scenario.yml in root."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "Step"
    endpoint: "GET /test"
"""
        (tmp_path / "pt_scenario.yml").write_text(scenario_content)

        result = analyzer.find_scenario_file(str(tmp_path))

        assert result is not None
        assert "pt_scenario.yml" in result

    def test_find_scenario_file_not_found(self, analyzer, tmp_path):
        """Test that None is returned when no scenario file exists."""
        # Create some other files
        (tmp_path / "README.md").write_text("# Test")
        (tmp_path / "openapi.yaml").write_text("openapi: 3.0.0")

        result = analyzer.find_scenario_file(str(tmp_path))

        assert result is None

    def test_find_scenario_file_priority_pt_scenario(self, analyzer, tmp_path):
        """Test that pt_scenario.yaml has higher priority than scenario.yaml."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "Step"
    endpoint: "GET /test"
"""
        (tmp_path / "pt_scenario.yaml").write_text(scenario_content)
        (tmp_path / "scenario.yaml").write_text(scenario_content)

        result = analyzer.find_scenario_file(str(tmp_path))

        assert result is not None
        # pt_scenario.yaml should be preferred
        assert "pt_scenario" in result

    def test_find_scenario_file_with_openapi_spec(self, analyzer, tmp_path):
        """Test finding scenario file when OpenAPI spec also exists."""
        openapi_content = """openapi: 3.0.0
info:
  title: Test
  version: 1.0.0
paths:
  /test:
    get:
      operationId: test
      responses:
        '200':
          description: OK
"""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "Step"
    endpoint: "GET /test"
"""
        (tmp_path / "openapi.yaml").write_text(openapi_content)
        (tmp_path / "pt_scenario.yaml").write_text(scenario_content)

        result = analyzer.find_scenario_file(str(tmp_path))

        assert result is not None
        assert "pt_scenario.yaml" in result

    def test_find_scenario_file_with_path_object(self, analyzer, tmp_path):
        """Test that Path objects are accepted."""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "Step"
    endpoint: "GET /test"
"""
        (tmp_path / "pt_scenario.yaml").write_text(scenario_content)

        # Pass Path object instead of string
        result = analyzer.find_scenario_file(tmp_path)

        assert result is not None


class TestProjectAnalyzerV2Integration:
    """Integration tests for v2 ProjectAnalyzer methods."""

    @pytest.fixture
    def analyzer(self):
        """Create an analyzer instance."""
        return ProjectAnalyzer()

    def test_analyze_project_with_scenario(self, analyzer, tmp_path):
        """Test that analyze_project works when scenario files exist."""
        openapi_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
servers:
  - url: http://localhost:8000
paths:
  /users:
    get:
      operationId: getUsers
      responses:
        '200':
          description: Success
"""
        scenario_content = """version: "1.0"
name: "User Flow"
scenario:
  - name: "Get Users"
    endpoint: "getUsers"
    assert:
      status: 200
"""
        (tmp_path / "openapi.yaml").write_text(openapi_content)
        (tmp_path / "pt_scenario.yaml").write_text(scenario_content)

        result = analyzer.analyze_project(str(tmp_path))

        # analyze_project returns openapi_spec_found, not found
        assert result["openapi_spec_found"] is True
        assert result["spec_path"] is not None

        # Check if scenario was also detected
        scenario_path = analyzer.find_scenario_file(str(tmp_path))
        assert scenario_path is not None

    def test_find_all_openapi_specs_excludes_scenario(self, analyzer, tmp_path):
        """Test that scenario files are not included in OpenAPI specs."""
        openapi_content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /test:
    get:
      operationId: test
      responses:
        '200':
          description: OK
"""
        scenario_content = """version: "1.0"
name: "Test"
scenario:
  - name: "Step"
    endpoint: "GET /test"
"""
        (tmp_path / "openapi.yaml").write_text(openapi_content)
        (tmp_path / "pt_scenario.yaml").write_text(scenario_content)

        specs = analyzer.find_all_openapi_specs(str(tmp_path))

        # Scenario file should NOT be in OpenAPI specs list
        # find_all_openapi_specs returns spec_path, not path
        for spec in specs:
            assert "pt_scenario" not in spec["spec_path"]
            assert "scenario.yaml" not in spec["spec_path"]
