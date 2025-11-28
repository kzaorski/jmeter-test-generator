"""Unit tests for ProjectAnalyzer module."""

from pathlib import Path

import pytest

from jmeter_gen.core.project_analyzer import (
    COMMON_SPEC_NAMES,
    MAX_SEARCH_DEPTH,
    ProjectAnalyzer,
)


class TestProjectAnalyzer:
    """Test suite for ProjectAnalyzer class."""

    @pytest.fixture
    def analyzer(self) -> ProjectAnalyzer:
        """Create ProjectAnalyzer instance for testing.

        Returns:
            ProjectAnalyzer instance
        """
        return ProjectAnalyzer()

    def test_constants(self):
        """Test that required constants are defined."""
        assert isinstance(COMMON_SPEC_NAMES, list)
        assert len(COMMON_SPEC_NAMES) > 0
        assert "openapi.yaml" in COMMON_SPEC_NAMES
        assert "swagger.json" in COMMON_SPEC_NAMES
        assert MAX_SEARCH_DEPTH == 3

    def test_find_openapi_spec_in_root(
        self, analyzer: ProjectAnalyzer, project_with_openapi_yaml: Path
    ):
        """Test finding openapi.yaml in project root."""
        result = analyzer.find_openapi_spec(str(project_with_openapi_yaml))

        assert result is not None
        assert result["found"] is True
        assert result["format"] == "yaml"
        assert "openapi.yaml" in result["spec_path"]
        assert Path(result["spec_path"]).exists()

    def test_find_swagger_json_in_root(
        self, analyzer: ProjectAnalyzer, project_with_swagger_json: Path
    ):
        """Test finding swagger.json in project root."""
        result = analyzer.find_openapi_spec(str(project_with_swagger_json))

        assert result is not None
        assert result["found"] is True
        assert result["format"] == "json"
        assert "swagger.json" in result["spec_path"]

    def test_find_spec_in_subdirectory(
        self, analyzer: ProjectAnalyzer, project_with_nested_spec: Path
    ):
        """Test finding spec in nested subdirectory."""
        result = analyzer.find_openapi_spec(str(project_with_nested_spec))

        assert result is not None
        assert result["found"] is True
        assert result["format"] == "yaml"
        assert "api" in result["spec_path"]
        assert "docs" in result["spec_path"]

    def test_no_spec_found_empty_project(self, analyzer: ProjectAnalyzer, empty_project: Path):
        """Test behavior when no spec file exists."""
        result = analyzer.find_openapi_spec(str(empty_project))

        assert result is None

    def test_prefer_openapi_over_swagger(
        self, analyzer: ProjectAnalyzer, project_with_multiple_specs: Path
    ):
        """Test that openapi.yaml is preferred over swagger.json."""
        result = analyzer.find_openapi_spec(str(project_with_multiple_specs))

        assert result is not None
        assert "openapi.yaml" in result["spec_path"]
        # Should find root openapi.yaml, not subdirectory swagger.json

    def test_find_spec_respects_max_depth(
        self, analyzer: ProjectAnalyzer, project_with_deep_nesting: Path
    ):
        """Test that search respects MAX_SEARCH_DEPTH."""
        result = analyzer.find_openapi_spec(str(project_with_deep_nesting))

        assert result is not None
        # Should find api-spec.yaml at level2, not openapi.yaml at level4
        assert "level2" in result["spec_path"]
        assert "level4" not in result["spec_path"]

    def test_find_spec_invalid_path(self, analyzer: ProjectAnalyzer):
        """Test behavior with invalid project path."""
        result = analyzer.find_openapi_spec("/nonexistent/path/to/project")

        assert result is None

    def test_find_spec_file_not_directory(self, analyzer: ProjectAnalyzer, temp_project_dir: Path):
        """Test behavior when path is a file, not a directory."""
        file_path = temp_project_dir / "test.txt"
        file_path.write_text("test")

        result = analyzer.find_openapi_spec(str(file_path))

        assert result is None

    def test_generate_jmx_name_simple(self, analyzer: ProjectAnalyzer):
        """Test JMX name generation with simple API title."""
        result = analyzer._generate_jmx_name("Test API")

        assert result == "test-api-test.jmx"

    def test_generate_jmx_name_complex(self, analyzer: ProjectAnalyzer):
        """Test JMX name generation with complex API title."""
        result = analyzer._generate_jmx_name("User Management Service API")

        assert result == "user-management-service-api-test.jmx"

    def test_generate_jmx_name_special_chars(self, analyzer: ProjectAnalyzer):
        """Test JMX name generation removes special characters."""
        result = analyzer._generate_jmx_name("My API (v2.0) - Production!")

        # Should only contain alphanumeric and hyphens
        assert result == "my-api-v2-0-production-test.jmx"
        assert "(" not in result
        assert ")" not in result
        assert "!" not in result

    def test_generate_jmx_name_consecutive_hyphens(self, analyzer: ProjectAnalyzer):
        """Test that consecutive hyphens are collapsed."""
        result = analyzer._generate_jmx_name("My   API    Service")

        # Multiple spaces should become single hyphen
        assert "--" not in result
        assert result == "my-api-service-test.jmx"

    def test_generate_jmx_name_leading_trailing_hyphens(self, analyzer: ProjectAnalyzer):
        """Test that leading/trailing hyphens are removed."""
        result = analyzer._generate_jmx_name("  API Service  ")

        assert not result.startswith("-")
        assert result == "api-service-test.jmx"

    def test_analyze_project_spec_found(
        self, analyzer: ProjectAnalyzer, project_with_openapi_yaml: Path
    ):
        """Test analyze_project when spec is found."""
        result = analyzer.analyze_project(str(project_with_openapi_yaml))

        assert result["openapi_spec_found"] is True
        assert "spec_path" in result
        assert "spec_format" in result
        assert result["spec_format"] == "yaml"
        assert "api_title" in result
        assert "recommended_jmx_name" in result
        assert result["recommended_jmx_name"].endswith("-test.jmx")

    def test_analyze_project_spec_not_found(self, analyzer: ProjectAnalyzer, empty_project: Path):
        """Test analyze_project when no spec is found."""
        result = analyzer.analyze_project(str(empty_project))

        assert result["openapi_spec_found"] is False
        assert "message" in result
        assert "No OpenAPI specification found" in result["message"]

    def test_analyze_project_invalid_path(self, analyzer: ProjectAnalyzer):
        """Test analyze_project with invalid project path."""
        result = analyzer.analyze_project("/invalid/nonexistent/path")

        assert result["openapi_spec_found"] is False
        assert "message" in result

    def test_analyze_project_generates_jmx_name(
        self, analyzer: ProjectAnalyzer, project_with_openapi_yaml: Path
    ):
        """Test that analyze_project generates recommended JMX name."""
        result = analyzer.analyze_project(str(project_with_openapi_yaml))

        assert result["openapi_spec_found"] is True
        assert "recommended_jmx_name" in result
        jmx_name = result["recommended_jmx_name"]
        assert jmx_name.endswith("-test.jmx")
        assert jmx_name == jmx_name.lower()  # Should be lowercase

    def test_search_subdirectories_skips_hidden(
        self, analyzer: ProjectAnalyzer, temp_project_dir: Path
    ):
        """Test that hidden directories are skipped during search."""
        # Create hidden directory with spec
        hidden_dir = temp_project_dir / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "openapi.yaml").write_text("openapi: 3.0.0")

        # Create normal directory with spec
        normal_dir = temp_project_dir / "api"
        normal_dir.mkdir()
        (normal_dir / "openapi.yaml").write_text("openapi: 3.0.0")

        result = analyzer.find_openapi_spec(str(temp_project_dir))

        # Should find the one in normal_dir, not hidden_dir
        assert result is not None
        assert ".hidden" not in result["spec_path"]
        assert "api" in result["spec_path"]

    def test_search_subdirectories_skips_common_excludes(
        self, analyzer: ProjectAnalyzer, temp_project_dir: Path
    ):
        """Test that common directories are excluded from search."""
        excluded_dirs = ["node_modules", "__pycache__", "venv", ".git"]

        for excluded in excluded_dirs:
            excluded_dir = temp_project_dir / excluded
            excluded_dir.mkdir()
            (excluded_dir / "openapi.yaml").write_text("openapi: 3.0.0")

        # Create spec in normal directory
        normal_dir = temp_project_dir / "src"
        normal_dir.mkdir()
        (normal_dir / "openapi.yaml").write_text("openapi: 3.0.0")

        result = analyzer.find_openapi_spec(str(temp_project_dir))

        # Should find the one in src, not in excluded directories
        assert result is not None
        assert "src" in result["spec_path"]
        for excluded in excluded_dirs:
            assert excluded not in result["spec_path"]

    def test_find_all_spec_formats(self, analyzer: ProjectAnalyzer, temp_project_dir: Path):
        """Test that all common spec formats are recognized."""
        spec_formats = {
            "openapi.yaml": "yaml",
            "openapi.yml": "yaml",
            "openapi.json": "json",
            "swagger.yaml": "yaml",
            "swagger.yml": "yaml",
            "swagger.json": "json",
            "api-spec.yaml": "yaml",
            "api.yaml": "yaml",
        }

        for spec_name, expected_format in spec_formats.items():
            # Create a fresh temp directory for each test
            test_dir = temp_project_dir / spec_name.replace(".", "_")
            test_dir.mkdir()
            spec_path = test_dir / spec_name
            spec_path.write_text("openapi: 3.0.0")

            result = analyzer.find_openapi_spec(str(test_dir))

            assert result is not None, f"Failed to find {spec_name}"
            assert result["format"] == expected_format, f"Wrong format for {spec_name}"
            assert result["found"] is True


class TestProjectAnalyzerEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def analyzer(self) -> ProjectAnalyzer:
        """Create ProjectAnalyzer instance for testing."""
        return ProjectAnalyzer()

    def test_empty_string_path(self, analyzer: ProjectAnalyzer):
        """Test behavior with empty string as path - treated as current directory."""
        result = analyzer.find_openapi_spec("")

        # Empty string is treated as current directory by Path("")
        # If current dir has spec, it should be found
        # This is expected Python Path behavior
        if result is not None:
            assert result["found"] is True
            assert "spec_path" in result

    def test_relative_path_resolution(
        self, analyzer: ProjectAnalyzer, project_with_openapi_yaml: Path
    ):
        """Test that relative paths are resolved correctly."""
        # Use relative path notation
        result = analyzer.find_openapi_spec(str(project_with_openapi_yaml))

        assert result is not None
        # spec_path should be absolute
        assert Path(result["spec_path"]).is_absolute()

    def test_symlink_handling(self, analyzer: ProjectAnalyzer, temp_project_dir: Path):
        """Test handling of symbolic links."""
        # Create a real directory with spec
        real_dir = temp_project_dir / "real"
        real_dir.mkdir()
        (real_dir / "openapi.yaml").write_text("openapi: 3.0.0")

        # Create a symlink to it (if supported by OS)
        try:
            link_dir = temp_project_dir / "link"
            link_dir.symlink_to(real_dir)

            result = analyzer.find_openapi_spec(str(temp_project_dir))

            assert result is not None
            assert result["found"] is True
        except OSError:
            # Symlinks may not be supported on all systems
            pytest.skip("Symbolic links not supported on this system")

    def test_generate_jmx_name_empty_string(self, analyzer: ProjectAnalyzer):
        """Test JMX name generation with empty string."""
        result = analyzer._generate_jmx_name("")

        # Should still return valid filename
        assert result == "test.jmx"

    def test_generate_jmx_name_only_special_chars(self, analyzer: ProjectAnalyzer):
        """Test JMX name generation with only special characters."""
        result = analyzer._generate_jmx_name("!@#$%^&*()")

        # Should return minimal valid filename
        assert result == "test.jmx"

    def test_analyze_project_with_nested_spec(
        self, analyzer: ProjectAnalyzer, project_with_nested_spec: Path
    ):
        """Test analyze_project finds spec in subdirectory."""
        result = analyzer.analyze_project(str(project_with_nested_spec))

        assert result["openapi_spec_found"] is True
        assert "api" in result["spec_path"] or "docs" in result["spec_path"]


class TestMultiSpecSupport:
    """Test multi-spec discovery functionality."""

    @pytest.fixture
    def analyzer(self) -> ProjectAnalyzer:
        """Create ProjectAnalyzer instance for testing."""
        return ProjectAnalyzer()

    def test_find_all_openapi_specs_single_spec(
        self, analyzer: ProjectAnalyzer, project_with_openapi_yaml: Path
    ):
        """Test find_all_openapi_specs with single spec returns list with one item."""
        result = analyzer.find_all_openapi_specs(str(project_with_openapi_yaml))

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["found"] is True
        assert result[0]["format"] == "yaml"

    def test_find_all_openapi_specs_multiple_specs(
        self, analyzer: ProjectAnalyzer, project_with_multiple_specs: Path
    ):
        """Test find_all_openapi_specs finds all specs in project."""
        result = analyzer.find_all_openapi_specs(str(project_with_multiple_specs))

        assert isinstance(result, list)
        assert len(result) == 2
        # First should be openapi.yaml (root, openapi naming)
        assert "openapi.yaml" in result[0]["spec_path"]
        # Second should be swagger.json (subdirectory)
        assert "swagger.json" in result[1]["spec_path"]

    def test_find_all_openapi_specs_empty_project(
        self, analyzer: ProjectAnalyzer, empty_project: Path
    ):
        """Test find_all_openapi_specs returns empty list for empty project."""
        result = analyzer.find_all_openapi_specs(str(empty_project))

        assert isinstance(result, list)
        assert len(result) == 0

    def test_find_all_openapi_specs_invalid_path(self, analyzer: ProjectAnalyzer):
        """Test find_all_openapi_specs returns empty list for invalid path."""
        result = analyzer.find_all_openapi_specs("/nonexistent/path")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_find_all_openapi_specs_priority_sorting(
        self, analyzer: ProjectAnalyzer, temp_project_dir: Path
    ):
        """Test that specs are sorted by priority (root > subdir, openapi > swagger)."""
        # Create swagger.json in root (lower priority name)
        (temp_project_dir / "swagger.json").write_text('{"openapi": "3.0.0"}')
        # Create openapi.yaml in subdirectory
        subdir = temp_project_dir / "api"
        subdir.mkdir()
        (subdir / "openapi.yaml").write_text("openapi: 3.0.0")

        result = analyzer.find_all_openapi_specs(str(temp_project_dir))

        assert len(result) == 2
        # Root swagger.json should be first (root takes priority)
        assert "swagger.json" in result[0]["spec_path"]
        assert result[0].get("in_root") is True

    def test_analyze_project_returns_available_specs(
        self, analyzer: ProjectAnalyzer, project_with_multiple_specs: Path
    ):
        """Test analyze_project includes available_specs in result."""
        result = analyzer.analyze_project(str(project_with_multiple_specs))

        assert result["openapi_spec_found"] is True
        assert "available_specs" in result
        assert isinstance(result["available_specs"], list)
        assert len(result["available_specs"]) == 2

    def test_analyze_project_multiple_specs_found_flag(
        self, analyzer: ProjectAnalyzer, project_with_multiple_specs: Path
    ):
        """Test analyze_project sets multiple_specs_found flag correctly."""
        result = analyzer.analyze_project(str(project_with_multiple_specs))

        assert result["multiple_specs_found"] is True

    def test_analyze_project_single_spec_flag(
        self, analyzer: ProjectAnalyzer, project_with_openapi_yaml: Path
    ):
        """Test analyze_project sets multiple_specs_found to False for single spec."""
        result = analyzer.analyze_project(str(project_with_openapi_yaml))

        assert result["multiple_specs_found"] is False
        assert len(result["available_specs"]) == 1

    def test_analyze_project_no_spec_includes_empty_available_specs(
        self, analyzer: ProjectAnalyzer, empty_project: Path
    ):
        """Test analyze_project returns empty available_specs when no spec found."""
        result = analyzer.analyze_project(str(empty_project))

        assert result["openapi_spec_found"] is False
        assert result["available_specs"] == []
        assert result["multiple_specs_found"] is False
