"""Unit tests for ScenarioValidator."""

from pathlib import Path

import pytest

from jmeter_gen.core.scenario_validator import ScenarioValidator, ValidationIssue, ValidationResult

# Mark all tests in this module as v2 tests
pytestmark = pytest.mark.v2


class TestScenarioValidator:
    """Tests for ScenarioValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return ScenarioValidator()

    @pytest.fixture
    def fixtures_dir(self):
        """Return the path to test fixtures directory."""
        return Path(__file__).parent.parent / "fixtures" / "scenarios"

    # Valid scenario tests

    def test_validate_valid_basic(self, validator, fixtures_dir):
        """Test validating a minimal valid scenario."""
        result = validator.validate(str(fixtures_dir / "valid_basic.yaml"))

        assert result.is_valid
        assert result.errors_count == 0
        assert result.warnings_count == 0
        assert result.scenario_name == "Basic Test Scenario"

    def test_validate_valid_full(self, validator, fixtures_dir):
        """Test validating a scenario with all features."""
        result = validator.validate(str(fixtures_dir / "valid_full.yaml"))

        assert result.is_valid
        assert result.errors_count == 0
        assert result.scenario_name == "Full Feature Scenario"

    # File not found test

    def test_validate_file_not_found(self, validator):
        """Test validation when file doesn't exist."""
        result = validator.validate("/nonexistent/path/scenario.yaml")

        assert not result.is_valid
        assert result.errors_count == 1
        assert result.issues[0].level == "error"
        assert result.issues[0].category == "yaml"
        assert "not found" in result.issues[0].message

    # Invalid YAML tests

    def test_validate_invalid_yaml(self, validator, tmp_path):
        """Test validation with invalid YAML syntax."""
        scenario_file = tmp_path / "invalid.yaml"
        scenario_file.write_text("invalid: yaml: content: [")

        result = validator.validate(str(scenario_file))

        assert not result.is_valid
        assert result.errors_count == 1
        assert result.issues[0].level == "error"
        assert result.issues[0].category == "yaml"

    # Missing required fields tests

    def test_validate_missing_name_field(self, validator, tmp_path):
        """Test validation when 'name' field is missing."""
        scenario_file = tmp_path / "missing_name.yaml"
        scenario_file.write_text("""
scenario:
  - name: Step 1
    endpoint: getUser
""")

        result = validator.validate(str(scenario_file))

        assert not result.is_valid
        assert result.errors_count == 1
        assert result.issues[0].level == "error"
        assert "name" in result.issues[0].message

    def test_validate_missing_scenario_field(self, validator, tmp_path):
        """Test validation when 'scenario' field is missing."""
        scenario_file = tmp_path / "missing_scenario.yaml"
        scenario_file.write_text("name: Test Scenario")

        result = validator.validate(str(scenario_file))

        assert not result.is_valid
        assert result.errors_count == 1
        assert result.issues[0].level == "error"
        assert "scenario" in result.issues[0].message

    # Undefined variable tests

    def test_validate_undefined_variable(self, validator, tmp_path):
        """Test validation with undefined variable in step."""
        scenario_file = tmp_path / "undefined_var.yaml"
        scenario_file.write_text("""
name: Test Scenario
scenario:
  - name: Step 1
    endpoint: getUser
    params:
      id: ${undefined_var}
""")

        result = validator.validate(str(scenario_file))

        assert not result.is_valid
        assert result.errors_count == 1
        assert result.issues[0].level == "error"
        assert result.issues[0].category == "variables"
        assert "undefined" in result.issues[0].message.lower()

    # Endpoint validation tests (requires spec)

    def test_validate_endpoint_not_in_spec(self, validator, fixtures_dir):
        """Test validation with endpoint not found in spec."""
        # Use a spec and scenario where endpoints don't match
        # For now, this test assumes we have test fixtures set up
        result = validator.validate(
            str(fixtures_dir / "valid_basic.yaml"),
            spec_path=str(fixtures_dir / "../specs/nonexistent-api.yaml"),
        )

        # Either endpoint not found (error) or spec not found (error)
        assert not result.is_valid
        assert result.errors_count > 0

    # Multiple issues tests

    def test_validate_multiple_issues(self, validator, tmp_path):
        """Test validation with multiple issues."""
        scenario_file = tmp_path / "multiple_issues.yaml"
        scenario_file.write_text("""
name: Test Scenario
scenario:
  - name: Step 1
    endpoint: getUser
    params:
      id: ${undefined_var}
  - name: Step 2
    endpoint: invalid endpoint format with bad space
""")

        result = validator.validate(str(scenario_file))

        assert not result.is_valid
        # Should have errors for both undefined variable and invalid endpoint
        assert result.errors_count >= 1

    # ValidationIssue structure tests

    def test_validation_issue_with_location(self, validator, tmp_path):
        """Test ValidationIssue with location field."""
        scenario_file = tmp_path / "test_location.yaml"
        scenario_file.write_text("""
name: Test Scenario
scenario:
  - name: Step 1
    endpoint: getUser
    params:
      id: ${undefined_var}
""")

        result = validator.validate(str(scenario_file))

        # Should have ValidationIssue objects
        assert len(result.issues) > 0
        assert isinstance(result.issues[0], ValidationIssue)
        assert hasattr(result.issues[0], "level")
        assert hasattr(result.issues[0], "category")
        assert hasattr(result.issues[0], "message")

    # ValidationResult structure tests

    def test_validation_result_properties(self, validator, fixtures_dir):
        """Test ValidationResult properties and counts."""
        result = validator.validate(str(fixtures_dir / "valid_basic.yaml"))

        assert isinstance(result, ValidationResult)
        assert hasattr(result, "scenario_path")
        assert hasattr(result, "scenario_name")
        assert hasattr(result, "is_valid")
        assert hasattr(result, "issues")
        assert hasattr(result, "errors_count")
        assert hasattr(result, "warnings_count")

        # Properties should be calculated from issues
        error_count = sum(1 for i in result.issues if i.level == "error")
        assert result.errors_count == error_count

        warning_count = sum(1 for i in result.issues if i.level == "warning")
        assert result.warnings_count == warning_count

    def test_validation_result_is_valid_property(self, validator, tmp_path):
        """Test that is_valid is False when there are errors."""
        scenario_file = tmp_path / "has_errors.yaml"
        scenario_file.write_text("""
name: Test Scenario
scenario:
  - name: Step 1
    endpoint: getUser
    params:
      id: ${undefined_var}
""")

        result = validator.validate(str(scenario_file))

        # is_valid should be False when errors exist
        assert result.is_valid == (result.errors_count == 0)
