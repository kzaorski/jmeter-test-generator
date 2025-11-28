"""Spec Comparator for OpenAPI Change Detection.

This module compares two OpenAPI/Swagger specifications and detects
changes between them - identifying added, removed, and modified endpoints.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Optional

from jmeter_gen.core.data_structures import EndpointChange, SpecDiff
from jmeter_gen.exceptions import InvalidSpecFormatException


class SpecComparator:
    """Compare OpenAPI/Swagger specifications and detect changes.

    This class provides functionality to compare two API specifications
    and identify which endpoints have been added, removed, or modified.

    Example:
        >>> comparator = SpecComparator()
        >>> diff = comparator.compare(old_spec_data, new_spec_data)
        >>> print(f"Added: {diff.summary['added']}")
    """

    def compare(
        self, old_spec: dict[str, Any], new_spec: dict[str, Any]
    ) -> SpecDiff:
        """Compare two specifications and return structured diff.

        Args:
            old_spec: Previous OpenAPI/Swagger specification (parsed spec_data).
            new_spec: Current OpenAPI/Swagger specification (parsed spec_data).

        Returns:
            SpecDiff containing all detected changes.

        Raises:
            InvalidSpecFormatException: If spec format is invalid.
        """
        self._validate_spec(old_spec, "old_spec")
        self._validate_spec(new_spec, "new_spec")

        old_endpoints = old_spec.get("endpoints", [])
        new_endpoints = new_spec.get("endpoints", [])

        # Calculate spec hashes
        old_hash = self._calculate_spec_hash(old_spec)
        new_hash = self._calculate_spec_hash(new_spec)

        # Match endpoints between specs
        added_map, removed_map, matched_pairs = self._match_endpoints(
            old_endpoints, new_endpoints
        )

        # Build EndpointChange lists
        added_endpoints = []
        for key, ep in added_map.items():
            normalized = self._normalize_endpoint(ep)
            added_endpoints.append(
                EndpointChange(
                    path=ep["path"],
                    method=ep["method"].upper(),
                    operation_id=ep.get("operationId", ""),
                    change_type="added",
                    changes={},
                    fingerprint=self._calculate_fingerprint(normalized),
                )
            )

        removed_endpoints = []
        for key, ep in removed_map.items():
            normalized = self._normalize_endpoint(ep)
            removed_endpoints.append(
                EndpointChange(
                    path=ep["path"],
                    method=ep["method"].upper(),
                    operation_id=ep.get("operationId", ""),
                    change_type="removed",
                    changes={},
                    fingerprint=self._calculate_fingerprint(normalized),
                )
            )

        modified_endpoints = []
        for old_ep, new_ep in matched_pairs:
            old_normalized = self._normalize_endpoint(old_ep)
            new_normalized = self._normalize_endpoint(new_ep)
            changes = self._detect_modifications(old_normalized, new_normalized)
            if changes:
                modified_endpoints.append(
                    EndpointChange(
                        path=new_ep["path"],
                        method=new_ep["method"].upper(),
                        operation_id=new_ep.get("operationId", ""),
                        change_type="modified",
                        changes=changes,
                        fingerprint=self._calculate_fingerprint(new_normalized),
                    )
                )

        return SpecDiff(
            old_version=old_spec.get("version", ""),
            new_version=new_spec.get("version", ""),
            old_hash=old_hash,
            new_hash=new_hash,
            added_endpoints=added_endpoints,
            removed_endpoints=removed_endpoints,
            modified_endpoints=modified_endpoints,
            timestamp=datetime.now().isoformat(),
        )

    def _validate_spec(self, spec: dict[str, Any], name: str) -> None:
        """Validate spec has required structure.

        Args:
            spec: The spec data to validate.
            name: Name of the spec for error messages.

        Raises:
            InvalidSpecFormatException: If spec is invalid.
        """
        if not isinstance(spec, dict):
            raise InvalidSpecFormatException(
                f"Invalid {name}: expected dictionary, got {type(spec).__name__}"
            )
        if "endpoints" not in spec:
            raise InvalidSpecFormatException(
                f"Invalid {name}: missing required field 'endpoints'"
            )

    def _normalize_endpoint(self, endpoint: dict[str, Any]) -> dict[str, Any]:
        """Normalize endpoint for consistent comparison.

        Args:
            endpoint: Raw endpoint from OpenAPI parser.

        Returns:
            Normalized endpoint dictionary with sorted keys.
        """
        # Normalize parameters
        raw_params = endpoint.get("parameters", [])
        normalized_params = []
        for p in raw_params:
            normalized_params.append(
                {
                    "name": p.get("name", ""),
                    "in": p.get("in", "query"),
                    "required": p.get("required", False),
                }
            )
        # Sort by (in, name)
        normalized_params.sort(key=lambda p: (p["in"], p["name"]))

        # Get responses - could be dict or list
        responses = endpoint.get("responses", {})
        if isinstance(responses, dict):
            response_codes = sorted(responses.keys())
        else:
            response_codes = []

        # Normalize request body schema for comparison
        request_body_schema = endpoint.get("request_body_schema")
        normalized_request_schema = self._normalize_schema(request_body_schema)

        return {
            "path": endpoint.get("path", ""),
            "method": endpoint.get("method", "").upper(),
            "operation_id": endpoint.get("operationId", ""),
            "request_body": bool(endpoint.get("requestBody", False)),
            "request_body_schema": normalized_request_schema,
            "parameters": normalized_params,
            "responses": response_codes,
        }

    def _normalize_schema(self, schema: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """Normalize schema for consistent comparison.

        Removes volatile fields like examples, descriptions, and sorts keys.

        Args:
            schema: JSON Schema object or None.

        Returns:
            Normalized schema or None.
        """
        if schema is None:
            return None

        if not isinstance(schema, dict):
            return schema

        # Fields to exclude from comparison (volatile/non-structural)
        exclude_fields = {"example", "examples", "description", "title", "default"}

        normalized: dict[str, Any] = {}
        for key, value in sorted(schema.items()):
            if key in exclude_fields:
                continue

            if key == "properties" and isinstance(value, dict):
                # Recursively normalize properties
                normalized[key] = {
                    prop_name: self._normalize_schema(prop_schema)
                    for prop_name, prop_schema in sorted(value.items())
                }
            elif key == "items" and isinstance(value, dict):
                # Recursively normalize array items
                normalized[key] = self._normalize_schema(value)
            elif isinstance(value, dict):
                normalized[key] = self._normalize_schema(value)
            elif isinstance(value, list):
                # Sort lists if they contain primitives (like required, enum)
                if value and isinstance(value[0], (str, int, float, bool)):
                    normalized[key] = sorted(value)
                else:
                    normalized[key] = value
            else:
                normalized[key] = value

        return normalized

    def _calculate_fingerprint(self, normalized_endpoint: dict[str, Any]) -> str:
        """Calculate SHA256 fingerprint of normalized endpoint.

        Args:
            normalized_endpoint: Normalized endpoint dictionary.

        Returns:
            SHA256 hash as hex string.
        """
        # Create fingerprint data excluding description/summary
        fingerprint_data = {
            "path": normalized_endpoint["path"],
            "method": normalized_endpoint["method"],
            "operation_id": normalized_endpoint["operation_id"],
            "request_body": normalized_endpoint["request_body"],
            "request_body_schema": normalized_endpoint.get("request_body_schema"),
            "parameters": normalized_endpoint["parameters"],
            "responses": normalized_endpoint["responses"],
        }

        # Canonical JSON representation
        json_str = json.dumps(fingerprint_data, sort_keys=True, separators=(",", ":"))

        # SHA256 hash
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def _calculate_spec_hash(self, spec: dict[str, Any]) -> str:
        """Calculate hash of entire spec for quick comparison.

        Args:
            spec: Parsed spec data.

        Returns:
            SHA256 hash as hex string with sha256: prefix.
        """
        # Hash based on endpoints only
        endpoints = spec.get("endpoints", [])
        normalized = [self._normalize_endpoint(ep) for ep in endpoints]
        json_str = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def _match_endpoints(
        self,
        old_endpoints: list[dict[str, Any]],
        new_endpoints: list[dict[str, Any]],
    ) -> tuple[
        dict[tuple[str, str], dict[str, Any]],
        dict[tuple[str, str], dict[str, Any]],
        list[tuple[dict[str, Any], dict[str, Any]]],
    ]:
        """Match endpoints between old and new specs.

        Uses (path, method) as the primary matching key.

        Args:
            old_endpoints: List of endpoints from old spec.
            new_endpoints: List of endpoints from new spec.

        Returns:
            Tuple of (added_map, removed_map, matched_pairs):
            - added_map: New endpoints not in old spec
            - removed_map: Old endpoints not in new spec
            - matched_pairs: List of (old, new) endpoint pairs
        """
        # Create index of old endpoints by (path, method)
        old_index: dict[tuple[str, str], dict[str, Any]] = {}
        for ep in old_endpoints:
            key = (ep.get("path", ""), ep.get("method", "").upper())
            old_index[key] = ep

        # Create index of new endpoints by (path, method)
        new_index: dict[tuple[str, str], dict[str, Any]] = {}
        for ep in new_endpoints:
            key = (ep.get("path", ""), ep.get("method", "").upper())
            new_index[key] = ep

        matched_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
        added_map: dict[tuple[str, str], dict[str, Any]] = {}

        for key, new_ep in new_index.items():
            if key in old_index:
                matched_pairs.append((old_index[key], new_ep))
            else:
                added_map[key] = new_ep

        removed_map: dict[tuple[str, str], dict[str, Any]] = {}
        for key, old_ep in old_index.items():
            if key not in new_index:
                removed_map[key] = old_ep

        return added_map, removed_map, matched_pairs

    def _detect_modifications(
        self,
        old_endpoint: dict[str, Any],
        new_endpoint: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Detect specific modifications in endpoint.

        Args:
            old_endpoint: Normalized old endpoint.
            new_endpoint: Normalized new endpoint.

        Returns:
            Dictionary of changes or None if identical.
        """
        # Quick fingerprint check
        old_fp = self._calculate_fingerprint(old_endpoint)
        new_fp = self._calculate_fingerprint(new_endpoint)

        if old_fp == new_fp:
            return None  # No changes

        changes: dict[str, Any] = {}

        # Compare request body
        if old_endpoint["request_body"] != new_endpoint["request_body"]:
            changes["request_body"] = {
                "old": old_endpoint["request_body"],
                "new": new_endpoint["request_body"],
            }

        # Compare parameters
        param_changes = self._compare_parameters(
            old_endpoint["parameters"],
            new_endpoint["parameters"],
        )
        if param_changes:
            changes["parameters"] = param_changes

        # Compare responses
        old_responses = set(old_endpoint["responses"])
        new_responses = set(new_endpoint["responses"])
        if old_responses != new_responses:
            changes["responses"] = {
                "added": list(new_responses - old_responses),
                "removed": list(old_responses - new_responses),
            }

        # Compare operationId
        if old_endpoint["operation_id"] != new_endpoint["operation_id"]:
            changes["operation_id"] = {
                "old": old_endpoint["operation_id"],
                "new": new_endpoint["operation_id"],
            }

        # Compare request body schema
        old_schema = old_endpoint.get("request_body_schema")
        new_schema = new_endpoint.get("request_body_schema")
        if old_schema != new_schema:
            changes["request_body_schema"] = {
                "old": old_schema,
                "new": new_schema,
            }

        return changes if changes else None

    def _compare_parameters(
        self,
        old_params: list[dict[str, Any]],
        new_params: list[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Compare parameter lists for changes.

        Args:
            old_params: Normalized parameters from old endpoint.
            new_params: Normalized parameters from new endpoint.

        Returns:
            Dictionary of parameter changes or None if identical.
        """
        old_set = {(p["name"], p["in"]) for p in old_params}
        new_set = {(p["name"], p["in"]) for p in new_params}

        added = new_set - old_set
        removed = old_set - new_set

        # Check for modifications in matched parameters
        modified = []
        for key in old_set & new_set:
            old_p = next(p for p in old_params if (p["name"], p["in"]) == key)
            new_p = next(p for p in new_params if (p["name"], p["in"]) == key)

            if old_p != new_p:
                modified.append(
                    {
                        "name": key[0],
                        "in": key[1],
                        "old": old_p,
                        "new": new_p,
                    }
                )

        if not (added or removed or modified):
            return None

        return {
            "added": [{"name": k[0], "in": k[1]} for k in added],
            "removed": [{"name": k[0], "in": k[1]} for k in removed],
            "modified": modified,
        }
