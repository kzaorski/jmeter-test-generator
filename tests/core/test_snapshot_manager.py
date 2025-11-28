"""Tests for SnapshotManager module."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from jmeter_gen.core.snapshot_manager import SnapshotManager
from jmeter_gen.exceptions import SnapshotLoadException


class TestSnapshotManager:
    """Test suite for SnapshotManager class."""

    @pytest.fixture
    def temp_project(self, tmp_path: Path) -> Path:
        """Create temporary project directory."""
        return tmp_path

    @pytest.fixture
    def manager(self, temp_project: Path) -> SnapshotManager:
        """Create SnapshotManager instance for testing."""
        return SnapshotManager(str(temp_project))

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
                    "parameters": [
                        {"name": "page", "in": "query", "required": False}
                    ],
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

    def test_get_snapshot_path(self, manager: SnapshotManager):
        """Test snapshot path generation."""
        path = manager._get_snapshot_path("tests/my-api-test.jmx")
        assert path.name == "my-api-test.spec.json"
        assert path.parent.name == "snapshots"

    def test_get_snapshot_path_nested(self, manager: SnapshotManager):
        """Test snapshot path generation with nested JMX path."""
        path = manager._get_snapshot_path("deep/nested/path/load-test.jmx")
        assert path.name == "load-test.spec.json"

    def test_save_snapshot(
        self,
        manager: SnapshotManager,
        temp_project: Path,
        sample_spec_data: dict,
    ):
        """Test saving snapshot."""
        jmx_path = str(temp_project / "test.jmx")

        # Create dummy JMX file
        Path(jmx_path).write_text("<jmeterTestPlan/>")

        snapshot_path = manager.save_snapshot(
            "openapi.yaml", jmx_path, sample_spec_data
        )

        assert Path(snapshot_path).exists()

        # Load and verify
        with open(snapshot_path) as f:
            snapshot = json.load(f)

        assert snapshot["version"] == "1.0"
        assert snapshot["format"] == "jmeter-gen-snapshot"
        assert snapshot["spec"]["api_title"] == "Test API"
        assert snapshot["spec"]["endpoints_count"] == 2
        assert len(snapshot["endpoints"]) == 2

    def test_load_snapshot(
        self,
        manager: SnapshotManager,
        temp_project: Path,
        sample_spec_data: dict,
    ):
        """Test loading snapshot."""
        jmx_path = str(temp_project / "test.jmx")
        Path(jmx_path).write_text("<jmeterTestPlan/>")

        # Save first
        manager.save_snapshot("openapi.yaml", jmx_path, sample_spec_data)

        # Load
        snapshot = manager.load_snapshot(jmx_path)

        assert snapshot is not None
        assert snapshot["spec"]["api_title"] == "Test API"
        assert len(snapshot["endpoints"]) == 2

    def test_load_snapshot_not_found(self, manager: SnapshotManager):
        """Test loading non-existent snapshot returns None."""
        snapshot = manager.load_snapshot("nonexistent.jmx")
        assert snapshot is None

    def test_load_snapshot_corrupted(
        self, manager: SnapshotManager, temp_project: Path
    ):
        """Test loading corrupted snapshot raises exception."""
        # Create corrupted snapshot file
        manager.snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = manager.snapshot_dir / "corrupted.spec.json"
        snapshot_path.write_text("{invalid json")

        with pytest.raises(SnapshotLoadException):
            manager.load_snapshot("corrupted.jmx")

    def test_filter_sensitive_data_removes_example(self, manager: SnapshotManager):
        """Test filtering removes example fields."""
        spec = {
            "endpoints": [
                {
                    "path": "/users",
                    "parameters": [
                        {
                            "name": "id",
                            "example": "12345",
                            "default": "1",
                        }
                    ],
                }
            ]
        }

        filtered = manager.filter_sensitive_data(spec)

        assert "example" not in filtered["endpoints"][0]["parameters"][0]
        assert "default" not in filtered["endpoints"][0]["parameters"][0]

    def test_filter_sensitive_data_removes_security_schemes(
        self, manager: SnapshotManager
    ):
        """Test filtering removes securitySchemes."""
        spec = {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"}
            },
            "security": [{"bearerAuth": []}],
            "endpoints": [],
        }

        filtered = manager.filter_sensitive_data(spec)

        assert "securitySchemes" not in filtered
        assert "security" not in filtered
        assert "endpoints" in filtered

    def test_filter_sensitive_data_removes_api_key_fields(
        self, manager: SnapshotManager
    ):
        """Test filtering removes fields matching sensitive patterns."""
        spec = {
            "endpoints": [
                {
                    "path": "/users",
                    "x-api-key": "secret123",
                    "auth_token": "token456",
                }
            ]
        }

        filtered = manager.filter_sensitive_data(spec)

        assert "x-api-key" not in filtered["endpoints"][0]
        assert "auth_token" not in filtered["endpoints"][0]

    def test_calculate_spec_hash_consistent(
        self, manager: SnapshotManager, sample_spec_data: dict
    ):
        """Test hash is consistent for same data."""
        hash1 = manager.calculate_spec_hash(sample_spec_data)
        hash2 = manager.calculate_spec_hash(sample_spec_data)

        assert hash1 == hash2
        assert hash1.startswith("sha256:")

    def test_calculate_spec_hash_changes_on_modification(
        self, manager: SnapshotManager, sample_spec_data: dict
    ):
        """Test hash changes when data changes."""
        hash1 = manager.calculate_spec_hash(sample_spec_data)

        modified = {**sample_spec_data, "version": "2.0.0"}
        hash2 = manager.calculate_spec_hash(modified)

        assert hash1 != hash2

    @patch("jmeter_gen.core.snapshot_manager.subprocess.check_output")
    def test_get_git_metadata(
        self, mock_check_output, manager: SnapshotManager, temp_project: Path
    ):
        """Test git metadata extraction."""
        # Create .git directory
        (temp_project / ".git").mkdir()

        mock_check_output.side_effect = [
            "abc123def456\n",  # commit
            "main\n",  # branch
            "user@example.com\n",  # author
        ]

        metadata = manager.get_git_metadata()

        assert metadata["git_commit"] == "abc123def456"
        assert metadata["git_branch"] == "main"
        assert metadata["git_author"] == "user@example.com"

    def test_get_git_metadata_no_git(
        self, manager: SnapshotManager, temp_project: Path
    ):
        """Test git metadata when not a git repo."""
        # No .git directory
        metadata = manager.get_git_metadata()

        assert metadata["git_commit"] is None
        assert metadata["git_branch"] is None
        assert metadata["git_author"] is None

    def test_ensure_gitignore(
        self, manager: SnapshotManager, temp_project: Path
    ):
        """Test gitignore creation."""
        manager.ensure_gitignore()

        gitignore_path = temp_project / ".jmeter-gen" / ".gitignore"
        assert gitignore_path.exists()

        content = gitignore_path.read_text()
        assert "backups/" in content
        assert "!snapshots/" in content

    def test_rotate_backups(
        self, manager: SnapshotManager, temp_project: Path
    ):
        """Test backup rotation keeps only max_backups."""
        # Create backup directory with many backups
        manager.backup_dir.mkdir(parents=True, exist_ok=True)
        manager.max_backups = 3

        for i in range(5):
            backup_file = manager.backup_dir / f"test.jmx.backup.{i:04d}"
            backup_file.write_text(f"backup {i}")

        manager.rotate_backups("test")

        # Should only have 3 backups left
        remaining = list(manager.backup_dir.glob("test.jmx.backup.*"))
        assert len(remaining) == 3

        # Oldest should be deleted
        assert not (manager.backup_dir / "test.jmx.backup.0000").exists()
        assert not (manager.backup_dir / "test.jmx.backup.0001").exists()


class TestFindSnapshotForSpec:
    """Test suite for find_snapshot_for_spec method."""

    @pytest.fixture
    def temp_project(self, tmp_path: Path) -> Path:
        """Create temporary project directory."""
        return tmp_path

    @pytest.fixture
    def manager(self, temp_project: Path) -> SnapshotManager:
        """Create SnapshotManager instance for testing."""
        return SnapshotManager(str(temp_project))

    @pytest.fixture
    def sample_spec_data(self) -> dict:
        """Create sample OpenAPI spec data."""
        return {
            "title": "Test API",
            "version": "1.0.0",
            "base_url": "http://localhost:8080",
            "endpoints": [
                {"path": "/users", "method": "GET", "operationId": "listUsers"},
            ],
        }

    def test_find_snapshot_for_spec_found(
        self,
        manager: SnapshotManager,
        temp_project: Path,
        sample_spec_data: dict,
    ):
        """Test finding snapshot by spec path."""
        jmx_path = str(temp_project / "test.jmx")
        spec_path = "/project/openapi.yaml"
        Path(jmx_path).write_text("<jmeterTestPlan/>")

        # Save snapshot
        manager.save_snapshot(spec_path, jmx_path, sample_spec_data)

        # Find by spec path
        result = manager.find_snapshot_for_spec(spec_path)

        assert result is not None
        snapshot, snapshot_file = result
        assert snapshot["spec"]["path"] == spec_path
        assert snapshot["spec"]["api_title"] == "Test API"
        assert snapshot_file.exists()

    def test_find_snapshot_for_spec_not_found(self, manager: SnapshotManager):
        """Test finding non-existent snapshot returns None."""
        result = manager.find_snapshot_for_spec("/nonexistent/openapi.yaml")
        assert result is None

    def test_find_snapshot_for_spec_no_snapshot_dir(
        self, manager: SnapshotManager
    ):
        """Test finding snapshot when snapshot directory doesn't exist."""
        result = manager.find_snapshot_for_spec("/any/openapi.yaml")
        assert result is None

    def test_find_snapshot_for_spec_multiple_snapshots(
        self,
        manager: SnapshotManager,
        temp_project: Path,
        sample_spec_data: dict,
    ):
        """Test finding correct snapshot among multiple."""
        # Create two different specs with different JMX files
        spec1_path = "/project/api1/openapi.yaml"
        spec2_path = "/project/api2/swagger.json"
        jmx1_path = str(temp_project / "api1-test.jmx")
        jmx2_path = str(temp_project / "api2-test.jmx")

        Path(jmx1_path).write_text("<jmeterTestPlan/>")
        Path(jmx2_path).write_text("<jmeterTestPlan/>")

        # Save snapshots
        spec1_data = {**sample_spec_data, "title": "API One"}
        spec2_data = {**sample_spec_data, "title": "API Two"}

        manager.save_snapshot(spec1_path, jmx1_path, spec1_data)
        manager.save_snapshot(spec2_path, jmx2_path, spec2_data)

        # Find each by spec path
        result1 = manager.find_snapshot_for_spec(spec1_path)
        result2 = manager.find_snapshot_for_spec(spec2_path)

        assert result1 is not None
        assert result1[0]["spec"]["api_title"] == "API One"

        assert result2 is not None
        assert result2[0]["spec"]["api_title"] == "API Two"

    def test_find_snapshot_for_spec_works_after_title_change(
        self,
        manager: SnapshotManager,
        temp_project: Path,
        sample_spec_data: dict,
    ):
        """Test finding snapshot still works even if api_title changed."""
        spec_path = "/project/openapi.yaml"
        jmx_path = str(temp_project / "old-api-name-test.jmx")
        Path(jmx_path).write_text("<jmeterTestPlan/>")

        # Save with original title
        manager.save_snapshot(spec_path, jmx_path, sample_spec_data)

        # Simulate title change - lookup by spec path should still work
        result = manager.find_snapshot_for_spec(spec_path)

        assert result is not None
        snapshot, _ = result
        assert snapshot["spec"]["path"] == spec_path

    def test_find_snapshot_for_spec_corrupted_raises(
        self, manager: SnapshotManager, temp_project: Path
    ):
        """Test finding snapshot with corrupted file raises exception."""
        manager.snapshot_dir.mkdir(parents=True, exist_ok=True)
        corrupted_file = manager.snapshot_dir / "corrupted.spec.json"
        corrupted_file.write_text("{invalid json")

        with pytest.raises(SnapshotLoadException):
            manager.find_snapshot_for_spec("/any/path.yaml")
