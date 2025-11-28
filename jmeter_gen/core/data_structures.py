"""Data structures for OpenAPI Change Detection.

This module defines dataclasses used for spec comparison, JMX updates,
and snapshot management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class EndpointChange:
    """Represents a change to a single endpoint.

    Attributes:
        path: The endpoint path (e.g., "/users/{id}")
        method: HTTP method in uppercase (e.g., "GET", "POST")
        operation_id: Operation ID from spec (e.g., "getUser")
        change_type: Type of change - "added", "removed", or "modified"
        changes: Dictionary of specific field changes for modified endpoints
        fingerprint: SHA256 hash of normalized endpoint
    """

    path: str
    method: str
    operation_id: str
    change_type: str
    changes: dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the endpoint change.
        """
        return {
            "path": self.path,
            "method": self.method,
            "operation_id": self.operation_id,
            "change_type": self.change_type,
            "changes": self.changes,
            "fingerprint": self.fingerprint,
        }


@dataclass
class SpecDiff:
    """Structured difference between two OpenAPI specifications.

    Attributes:
        old_version: API version from old spec
        new_version: API version from new spec
        old_hash: SHA256 hash of old spec
        new_hash: SHA256 hash of new spec
        added_endpoints: List of endpoints added in new spec
        removed_endpoints: List of endpoints removed from old spec
        modified_endpoints: List of endpoints modified between specs
        summary: Count summary {"added": n, "removed": n, "modified": n}
        timestamp: ISO 8601 timestamp of comparison
        has_changes: True if any changes detected
    """

    old_version: str
    new_version: str
    old_hash: str
    new_hash: str
    added_endpoints: list[EndpointChange] = field(default_factory=list)
    removed_endpoints: list[EndpointChange] = field(default_factory=list)
    modified_endpoints: list[EndpointChange] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    has_changes: bool = False

    def __post_init__(self) -> None:
        """Calculate summary and has_changes after initialization."""
        self.summary = {
            "added": len(self.added_endpoints),
            "removed": len(self.removed_endpoints),
            "modified": len(self.modified_endpoints),
        }
        self.has_changes = (
            len(self.added_endpoints) > 0
            or len(self.removed_endpoints) > 0
            or len(self.modified_endpoints) > 0
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the spec diff.
        """
        return {
            "old_version": self.old_version,
            "new_version": self.new_version,
            "old_hash": self.old_hash,
            "new_hash": self.new_hash,
            "added_endpoints": [e.to_dict() for e in self.added_endpoints],
            "removed_endpoints": [e.to_dict() for e in self.removed_endpoints],
            "modified_endpoints": [e.to_dict() for e in self.modified_endpoints],
            "summary": self.summary,
            "timestamp": self.timestamp,
            "has_changes": self.has_changes,
        }


@dataclass
class UpdateResult:
    """Result of a JMX update operation.

    Attributes:
        success: True if update completed without errors
        jmx_path: Path to the updated JMX file
        backup_path: Path to backup file if created, None otherwise
        changes_applied: Count of changes {"added": n, "disabled": n, "updated": n}
        errors: List of error messages encountered
        warnings: List of warning messages encountered
    """

    success: bool
    jmx_path: str
    backup_path: Optional[str] = None
    changes_applied: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the update result.
        """
        return {
            "success": self.success,
            "jmx_path": self.jmx_path,
            "backup_path": self.backup_path,
            "changes_applied": self.changes_applied,
            "errors": self.errors,
            "warnings": self.warnings,
        }
