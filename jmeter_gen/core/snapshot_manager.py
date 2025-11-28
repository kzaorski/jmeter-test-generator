"""Snapshot Manager for OpenAPI Change Detection.

This module manages OpenAPI specification snapshots for change detection.
Snapshots are saved to .jmeter-gen/snapshots/ (committed to git) and
backups are stored in .jmeter-gen/backups/ (gitignored).
"""

import copy
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from jmeter_gen.exceptions import SnapshotLoadException, SnapshotSaveException


class SnapshotManager:
    """Manage OpenAPI specification snapshots for change detection.

    This class provides functionality to save and load filtered spec snapshots,
    calculate hashes for change detection, and extract git metadata.

    Example:
        >>> manager = SnapshotManager("/path/to/project")
        >>> snapshot_path = manager.save_snapshot(
        ...     "openapi.yaml", "test.jmx", spec_data
        ... )
        >>> snapshot = manager.load_snapshot("test.jmx")
    """

    # Snapshot format version
    SNAPSHOT_VERSION = "1.0"

    # Regex patterns for sensitive data detection
    SENSITIVE_PATTERNS = [
        r"(?i)(api[_-]?key|apikey|api_secret)",
        r"(?i)(token|access[_-]?token|auth[_-]?token|bearer)",
        r"(?i)(password|passwd|pwd|secret|client[_-]?secret)",
        r"(?i)(authorization|auth|credential|credentials)",
        r"(?i)(ssn|social[_-]?security|credit[_-]?card|cvv|cvv2)",
        r"(?i)(private[_-]?key|secret[_-]?key|encryption[_-]?key)",
    ]

    # Fields to filter from OpenAPI specs
    SENSITIVE_FIELDS = [
        "example",
        "examples",
        "default",
        "x-api-key",
        "x-auth-token",
    ]

    def __init__(self, project_path: str = ".") -> None:
        """Initialize snapshot manager.

        Args:
            project_path: Root path of project (default: current directory).
        """
        self.project_path = Path(project_path).resolve()
        self.snapshot_dir = self.project_path / ".jmeter-gen" / "snapshots"
        self.backup_dir = self.project_path / ".jmeter-gen" / "backups"
        self.max_backups = 10
        # Compile regex patterns for performance
        self._compiled_patterns = [re.compile(p) for p in self.SENSITIVE_PATTERNS]

    def save_snapshot(
        self,
        spec_path: str,
        jmx_path: str,
        spec_data: dict[str, Any],
    ) -> str:
        """Save filtered snapshot of OpenAPI spec.

        Args:
            spec_path: Path to OpenAPI specification file.
            jmx_path: Path to associated JMX file.
            spec_data: Parsed OpenAPI specification data.

        Returns:
            Path to created snapshot file.

        Raises:
            SnapshotSaveException: If snapshot creation fails.
        """
        try:
            # Create snapshot directory
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)

            # Filter sensitive data from spec
            filtered_spec = self.filter_sensitive_data(spec_data)

            # Calculate spec hash
            spec_hash = self.calculate_spec_hash(filtered_spec)

            # Calculate JMX hash if file exists
            jmx_hash = None
            jmx_file = Path(jmx_path)
            if jmx_file.exists():
                with open(jmx_file, "rb") as f:
                    jmx_content = f.read()
                    jmx_hash = f"sha256:{hashlib.sha256(jmx_content).hexdigest()}"

            # Extract git metadata
            git_meta = self.get_git_metadata()

            # Build snapshot structure
            snapshot = {
                "version": self.SNAPSHOT_VERSION,
                "format": "jmeter-gen-snapshot",
                "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "captured_by": git_meta.get("git_author") or "unknown",
                "git_commit": git_meta.get("git_commit"),
                "git_branch": git_meta.get("git_branch"),
                "spec": {
                    "path": spec_path,
                    "hash": spec_hash,
                    "api_version": spec_data.get("version", "unknown"),
                    "api_title": spec_data.get("title", "unknown"),
                    "base_url": spec_data.get("base_url", ""),
                    "endpoints_count": len(spec_data.get("endpoints", [])),
                },
                "jmx": {
                    "path": jmx_path,
                    "hash": jmx_hash,
                },
                "endpoints": filtered_spec.get("endpoints", []),
                "security": {
                    "filtered": True,
                    "note": "Sensitive data removed for git storage",
                },
            }

            # Write JSON file
            snapshot_path = self._get_snapshot_path(jmx_path)
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2, sort_keys=False)

            # Ensure gitignore exists
            self.ensure_gitignore()

            return str(snapshot_path)

        except (OSError, IOError) as e:
            raise SnapshotSaveException(f"Cannot save snapshot: {e}") from e

    def load_snapshot(self, jmx_path: str) -> Optional[dict[str, Any]]:
        """Load snapshot for given JMX file.

        Args:
            jmx_path: Path to JMX file.

        Returns:
            Snapshot dictionary or None if not found.

        Raises:
            SnapshotLoadException: If snapshot file is corrupted.
        """
        snapshot_path = self._get_snapshot_path(jmx_path)

        if not snapshot_path.exists():
            return None

        try:
            with open(snapshot_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise SnapshotLoadException(
                f"Corrupted snapshot file: {snapshot_path}, {e}"
            ) from e
        except (OSError, IOError):
            return None

    def find_snapshot_for_spec(
        self, spec_path: str
    ) -> Optional[tuple[dict[str, Any], Path]]:
        """Find snapshot by spec path instead of JMX name.

        This method searches all snapshots in the snapshot directory and
        matches by the stored spec.path field. This is more reliable than
        JMX-based lookup because it works even if api_title changes.

        Args:
            spec_path: Path to OpenAPI specification file.

        Returns:
            Tuple of (snapshot_data, snapshot_file_path) or None if not found.

        Raises:
            SnapshotLoadException: If a matching snapshot file is corrupted.
        """
        if not self.snapshot_dir.exists():
            return None

        for snapshot_file in self.snapshot_dir.glob("*.spec.json"):
            try:
                with open(snapshot_file, "r", encoding="utf-8") as f:
                    snapshot = json.load(f)
                if snapshot.get("spec", {}).get("path") == spec_path:
                    return (snapshot, snapshot_file)
            except json.JSONDecodeError as e:
                raise SnapshotLoadException(
                    f"Corrupted snapshot file: {snapshot_file}, {e}"
                ) from e
            except (OSError, IOError):
                continue
        return None

    def calculate_spec_hash(self, spec_data: dict[str, Any]) -> str:
        """Calculate SHA256 hash of normalized spec.

        Args:
            spec_data: OpenAPI specification data.

        Returns:
            SHA256 hash as hex string with 'sha256:' prefix.
        """
        normalized = self._normalize_for_hash(spec_data)
        json_str = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        hash_obj = hashlib.sha256(json_str.encode("utf-8"))
        return f"sha256:{hash_obj.hexdigest()}"

    def filter_sensitive_data(self, spec_data: dict[str, Any]) -> dict[str, Any]:
        """Remove sensitive data from spec for safe git storage.

        Args:
            spec_data: OpenAPI specification data.

        Returns:
            Filtered specification (deep copy).
        """
        filtered = copy.deepcopy(spec_data)
        return self._filter_object(filtered)

    def get_git_metadata(self) -> dict[str, Optional[str]]:
        """Extract git metadata (commit, branch, author).

        Returns:
            Dictionary with git_commit, git_branch, git_author.
            Returns None values if not a git repository.
        """
        git_dir = self.project_path / ".git"
        if not git_dir.exists():
            return {
                "git_commit": None,
                "git_branch": None,
                "git_author": None,
            }

        try:
            # Get current commit hash
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_path,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()

            # Get current branch
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.project_path,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()

            # Get user email
            try:
                author = subprocess.check_output(
                    ["git", "config", "user.email"],
                    cwd=self.project_path,
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
            except subprocess.CalledProcessError:
                author = None

            return {
                "git_commit": commit,
                "git_branch": branch,
                "git_author": author,
            }

        except (subprocess.CalledProcessError, FileNotFoundError):
            return {
                "git_commit": None,
                "git_branch": None,
                "git_author": None,
            }

    def ensure_gitignore(self) -> None:
        """Create/update .gitignore for backups directory.

        Creates .jmeter-gen/.gitignore with backups/ ignored
        and snapshots/ not ignored.
        """
        jmeter_gen_dir = self.project_path / ".jmeter-gen"
        jmeter_gen_dir.mkdir(parents=True, exist_ok=True)

        gitignore_path = jmeter_gen_dir / ".gitignore"

        gitignore_content = """# JMeter Test Generator
# Backups are local only (not committed)
backups/

# Snapshots are committed for team collaboration
!snapshots/
"""

        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write(gitignore_content)

    def rotate_backups(self, jmx_basename: str) -> None:
        """Keep only last N backups, delete oldest.

        Args:
            jmx_basename: Base name of JMX file (without extension).
        """
        if not self.backup_dir.exists():
            return

        # Find all backups for this JMX
        pattern = f"{jmx_basename}.jmx.backup.*"
        backups = sorted(self.backup_dir.glob(pattern))

        # Delete oldest backups if exceeding limit
        while len(backups) > self.max_backups:
            oldest = backups.pop(0)
            oldest.unlink()

    def _get_snapshot_path(self, jmx_path: str) -> Path:
        """Get snapshot file path for JMX file.

        Args:
            jmx_path: Path to JMX file.

        Returns:
            Path to snapshot file.
        """
        jmx_file = Path(jmx_path)
        basename = jmx_file.stem  # filename without extension
        snapshot_filename = f"{basename}.spec.json"
        return self.snapshot_dir / snapshot_filename

    def _normalize_for_hash(self, data: Any) -> Any:
        """Normalize data structure for consistent hashing.

        Args:
            data: Data to normalize (dict, list, or primitive).

        Returns:
            Normalized data (sorted keys, consistent ordering).
        """
        if isinstance(data, dict):
            return {k: self._normalize_for_hash(v) for k, v in sorted(data.items())}
        elif isinstance(data, list):
            return [self._normalize_for_hash(item) for item in data]
        else:
            return data

    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if field name is sensitive.

        Args:
            field_name: Field name to check.

        Returns:
            True if field should be filtered.
        """
        # Exact match (case-insensitive)
        if field_name.lower() in [f.lower() for f in self.SENSITIVE_FIELDS]:
            return True

        # Regex pattern match
        for pattern in self._compiled_patterns:
            if pattern.search(field_name):
                return True

        return False

    def _filter_object(self, obj: Any, path: str = "") -> Any:
        """Recursively filter sensitive data from object.

        Args:
            obj: Object to filter (dict, list, or primitive).
            path: Current path in object tree (for logging).

        Returns:
            Filtered object.
        """
        if isinstance(obj, dict):
            filtered_dict = {}
            for key, value in obj.items():
                # Check if field name is sensitive
                if self._is_sensitive_field(key):
                    continue  # Skip this field

                # Special handling for OpenAPI security structures
                if key == "securitySchemes":
                    continue  # Remove all security schemes

                if key == "security":
                    continue  # Remove security requirements

                # Recursively filter value
                filtered_value = self._filter_object(value, f"{path}.{key}")
                filtered_dict[key] = filtered_value

            return filtered_dict

        elif isinstance(obj, list):
            return [
                self._filter_object(item, f"{path}[{i}]") for i, item in enumerate(obj)
            ]

        else:
            # Primitive value - return as-is
            return obj
