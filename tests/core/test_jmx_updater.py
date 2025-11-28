"""Tests for JMXUpdater module."""

from pathlib import Path

import pytest

from jmeter_gen.core.data_structures import EndpointChange, SpecDiff
from jmeter_gen.core.jmx_updater import JMXUpdater
from jmeter_gen.exceptions import JMXParseException


class TestJMXUpdater:
    """Test suite for JMXUpdater class."""

    @pytest.fixture
    def temp_project(self, tmp_path: Path) -> Path:
        """Create temporary project directory."""
        return tmp_path

    @pytest.fixture
    def updater(self, temp_project: Path) -> JMXUpdater:
        """Create JMXUpdater instance for testing."""
        return JMXUpdater(str(temp_project))

    @pytest.fixture
    def sample_jmx_content(self) -> str:
        """Create sample JMX content."""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan" enabled="true">
      <stringProp name="TestPlan.comments"></stringProp>
    </TestPlan>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group" enabled="true">
        <stringProp name="ThreadGroup.num_threads">1</stringProp>
      </ThreadGroup>
      <hashTree>
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="listUsers" enabled="true">
          <stringProp name="HTTPSampler.path">/users</stringProp>
          <stringProp name="HTTPSampler.method">GET</stringProp>
        </HTTPSamplerProxy>
        <hashTree>
          <ResponseAssertion guiclass="AssertionGui" testclass="ResponseAssertion" testname="Response Code 200" enabled="true">
            <collectionProp name="Asserion.test_strings">
              <stringProp name="">200</stringProp>
            </collectionProp>
          </ResponseAssertion>
          <hashTree/>
        </hashTree>
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="getUser" enabled="true">
          <stringProp name="HTTPSampler.path">/users/{id}</stringProp>
          <stringProp name="HTTPSampler.method">GET</stringProp>
        </HTTPSamplerProxy>
        <hashTree/>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>'''

    @pytest.fixture
    def sample_spec_data(self) -> dict:
        """Create sample OpenAPI spec data."""
        return {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {
                    "path": "/users",
                    "method": "GET",
                    "operationId": "listUsers",
                    "requestBody": False,
                    "parameters": [],
                },
                {
                    "path": "/users/{id}",
                    "method": "GET",
                    "operationId": "getUser",
                    "requestBody": False,
                    "parameters": [],
                },
                {
                    "path": "/users",
                    "method": "POST",
                    "operationId": "createUser",
                    "requestBody": True,
                    "parameters": [],
                },
            ],
        }

    def test_parse_jmx_valid(
        self,
        updater: JMXUpdater,
        temp_project: Path,
        sample_jmx_content: str,
    ):
        """Test parsing valid JMX file."""
        jmx_path = temp_project / "test.jmx"
        jmx_path.write_text(sample_jmx_content)

        tree = updater.parse_jmx(str(jmx_path))

        assert tree is not None
        assert tree.getroot().tag == "jmeterTestPlan"

    def test_parse_jmx_file_not_found(self, updater: JMXUpdater):
        """Test parsing non-existent JMX file raises exception."""
        with pytest.raises(JMXParseException) as exc_info:
            updater.parse_jmx("nonexistent.jmx")

        assert "not found" in str(exc_info.value)

    def test_parse_jmx_invalid_xml(
        self, updater: JMXUpdater, temp_project: Path
    ):
        """Test parsing invalid XML raises exception."""
        jmx_path = temp_project / "invalid.jmx"
        jmx_path.write_text("<invalid xml content")

        with pytest.raises(JMXParseException):
            updater.parse_jmx(str(jmx_path))

    def test_parse_jmx_wrong_root_element(
        self, updater: JMXUpdater, temp_project: Path
    ):
        """Test parsing JMX with wrong root element."""
        jmx_path = temp_project / "wrong.jmx"
        jmx_path.write_text("<wrongRoot></wrongRoot>")

        with pytest.raises(JMXParseException) as exc_info:
            updater.parse_jmx(str(jmx_path))

        assert "expected 'jmeterTestPlan'" in str(exc_info.value)

    def test_create_backup(
        self,
        updater: JMXUpdater,
        temp_project: Path,
        sample_jmx_content: str,
    ):
        """Test backup creation."""
        jmx_path = temp_project / "test.jmx"
        jmx_path.write_text(sample_jmx_content)

        backup_path = updater._create_backup(str(jmx_path))

        assert Path(backup_path).exists()
        assert "backup" in backup_path
        assert Path(backup_path).read_text() == sample_jmx_content

    def test_find_samplers(
        self,
        updater: JMXUpdater,
        temp_project: Path,
        sample_jmx_content: str,
    ):
        """Test finding HTTP Samplers in JMX."""
        jmx_path = temp_project / "test.jmx"
        jmx_path.write_text(sample_jmx_content)

        tree = updater.parse_jmx(str(jmx_path))
        samplers = updater._find_samplers(tree)

        assert len(samplers) == 2
        assert samplers[0].get("testname") == "listUsers"
        assert samplers[1].get("testname") == "getUser"

    def test_match_sampler_to_endpoint(
        self,
        updater: JMXUpdater,
        temp_project: Path,
        sample_jmx_content: str,
    ):
        """Test extracting path and method from sampler."""
        jmx_path = temp_project / "test.jmx"
        jmx_path.write_text(sample_jmx_content)

        tree = updater.parse_jmx(str(jmx_path))
        samplers = updater._find_samplers(tree)

        result = updater._match_sampler_to_endpoint(samplers[0])

        assert result == ("/users", "GET")

    def test_update_jmx_add_endpoint(
        self,
        updater: JMXUpdater,
        temp_project: Path,
        sample_jmx_content: str,
        sample_spec_data: dict,
    ):
        """Test adding new endpoint to JMX."""
        jmx_path = temp_project / "test.jmx"
        jmx_path.write_text(sample_jmx_content)

        diff = SpecDiff(
            old_version="1.0.0",
            new_version="1.1.0",
            old_hash="sha256:old",
            new_hash="sha256:new",
            added_endpoints=[
                EndpointChange(
                    path="/users",
                    method="POST",
                    operation_id="createUser",
                    change_type="added",
                    changes={},
                    fingerprint="sha256:xxx",
                )
            ],
            removed_endpoints=[],
            modified_endpoints=[],
        )

        result = updater.update_jmx(str(jmx_path), diff, sample_spec_data)

        assert result.success is True
        assert result.changes_applied["added"] == 1
        assert result.backup_path is not None

        # Verify new sampler was added
        tree = updater.parse_jmx(str(jmx_path))
        samplers = updater._find_samplers(tree)
        assert len(samplers) == 3  # 2 original + 1 new

    def test_update_jmx_disable_endpoint(
        self,
        updater: JMXUpdater,
        temp_project: Path,
        sample_jmx_content: str,
        sample_spec_data: dict,
    ):
        """Test disabling removed endpoint in JMX."""
        jmx_path = temp_project / "test.jmx"
        jmx_path.write_text(sample_jmx_content)

        diff = SpecDiff(
            old_version="1.0.0",
            new_version="1.1.0",
            old_hash="sha256:old",
            new_hash="sha256:new",
            added_endpoints=[],
            removed_endpoints=[
                EndpointChange(
                    path="/users/{id}",
                    method="GET",
                    operation_id="getUser",
                    change_type="removed",
                    changes={},
                    fingerprint="sha256:xxx",
                )
            ],
            modified_endpoints=[],
        )

        result = updater.update_jmx(str(jmx_path), diff, sample_spec_data)

        assert result.success is True
        assert result.changes_applied["disabled"] == 1

        # Verify sampler was disabled
        tree = updater.parse_jmx(str(jmx_path))
        samplers = updater._find_samplers(tree)
        disabled = [s for s in samplers if s.get("enabled") == "false"]
        assert len(disabled) == 1
        assert disabled[0].get("testname") == "getUser"

    def test_update_jmx_no_changes(
        self,
        updater: JMXUpdater,
        temp_project: Path,
        sample_jmx_content: str,
        sample_spec_data: dict,
    ):
        """Test updating JMX with no changes."""
        jmx_path = temp_project / "test.jmx"
        jmx_path.write_text(sample_jmx_content)

        diff = SpecDiff(
            old_version="1.0.0",
            new_version="1.0.0",
            old_hash="sha256:same",
            new_hash="sha256:same",
            added_endpoints=[],
            removed_endpoints=[],
            modified_endpoints=[],
        )

        result = updater.update_jmx(str(jmx_path), diff, sample_spec_data)

        assert result.success is True
        assert result.changes_applied["added"] == 0
        assert result.changes_applied["disabled"] == 0
        assert result.changes_applied["updated"] == 0

    def test_update_jmx_sampler_not_found_warning(
        self,
        updater: JMXUpdater,
        temp_project: Path,
        sample_jmx_content: str,
        sample_spec_data: dict,
    ):
        """Test warning when sampler not found for removed endpoint."""
        jmx_path = temp_project / "test.jmx"
        jmx_path.write_text(sample_jmx_content)

        diff = SpecDiff(
            old_version="1.0.0",
            new_version="1.1.0",
            old_hash="sha256:old",
            new_hash="sha256:new",
            added_endpoints=[],
            removed_endpoints=[
                EndpointChange(
                    path="/nonexistent",
                    method="DELETE",
                    operation_id="deleteNonexistent",
                    change_type="removed",
                    changes={},
                    fingerprint="sha256:xxx",
                )
            ],
            modified_endpoints=[],
        )

        result = updater.update_jmx(str(jmx_path), diff, sample_spec_data)

        assert result.success is True  # Still succeeds
        assert len(result.warnings) == 1
        assert "Could not find sampler" in result.warnings[0]

    def test_rotate_backups(
        self,
        updater: JMXUpdater,
        temp_project: Path,
    ):
        """Test backup rotation keeps only max_backups."""
        updater.backup_dir.mkdir(parents=True, exist_ok=True)
        updater.max_backups = 3

        # Create 5 backups
        for i in range(5):
            backup_file = updater.backup_dir / f"test.jmx.backup.{i:04d}"
            backup_file.write_text(f"backup {i}")

        updater._rotate_backups("test")

        remaining = list(updater.backup_dir.glob("test.jmx.backup.*"))
        assert len(remaining) == 3
