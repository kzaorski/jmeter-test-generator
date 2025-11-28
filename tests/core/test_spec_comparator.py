"""Tests for SpecComparator module."""

import pytest

from jmeter_gen.core.spec_comparator import SpecComparator
from jmeter_gen.exceptions import InvalidSpecFormatException


class TestSpecComparator:
    """Test suite for SpecComparator class."""

    @pytest.fixture
    def comparator(self) -> SpecComparator:
        """Create SpecComparator instance for testing."""
        return SpecComparator()

    @pytest.fixture
    def base_spec(self) -> dict:
        """Create base spec with 3 endpoints."""
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
                    "responses": {"200": {}, "400": {}},
                },
                {
                    "path": "/users/{id}",
                    "method": "GET",
                    "operationId": "getUser",
                    "requestBody": False,
                    "parameters": [
                        {"name": "id", "in": "path", "required": True}
                    ],
                    "responses": {"200": {}, "404": {}},
                },
                {
                    "path": "/users",
                    "method": "POST",
                    "operationId": "createUser",
                    "requestBody": True,
                    "parameters": [],
                    "responses": {"201": {}, "400": {}},
                },
            ],
        }

    def test_compare_no_changes(self, comparator: SpecComparator, base_spec: dict):
        """Test comparing identical specs returns no changes."""
        diff = comparator.compare(base_spec, base_spec)

        assert diff.has_changes is False
        assert diff.summary["added"] == 0
        assert diff.summary["removed"] == 0
        assert diff.summary["modified"] == 0
        assert len(diff.added_endpoints) == 0
        assert len(diff.removed_endpoints) == 0
        assert len(diff.modified_endpoints) == 0

    def test_compare_added_endpoint(self, comparator: SpecComparator, base_spec: dict):
        """Test detecting added endpoint."""
        new_spec = {
            **base_spec,
            "version": "1.1.0",
            "endpoints": base_spec["endpoints"]
            + [
                {
                    "path": "/users/{id}",
                    "method": "DELETE",
                    "operationId": "deleteUser",
                    "requestBody": False,
                    "parameters": [
                        {"name": "id", "in": "path", "required": True}
                    ],
                    "responses": {"204": {}},
                }
            ],
        }

        diff = comparator.compare(base_spec, new_spec)

        assert diff.has_changes is True
        assert diff.summary["added"] == 1
        assert diff.summary["removed"] == 0
        assert diff.summary["modified"] == 0
        assert len(diff.added_endpoints) == 1
        assert diff.added_endpoints[0].path == "/users/{id}"
        assert diff.added_endpoints[0].method == "DELETE"
        assert diff.added_endpoints[0].change_type == "added"

    def test_compare_removed_endpoint(
        self, comparator: SpecComparator, base_spec: dict
    ):
        """Test detecting removed endpoint."""
        new_spec = {
            **base_spec,
            "version": "1.1.0",
            "endpoints": base_spec["endpoints"][:2],  # Remove POST /users
        }

        diff = comparator.compare(base_spec, new_spec)

        assert diff.has_changes is True
        assert diff.summary["added"] == 0
        assert diff.summary["removed"] == 1
        assert diff.summary["modified"] == 0
        assert len(diff.removed_endpoints) == 1
        assert diff.removed_endpoints[0].path == "/users"
        assert diff.removed_endpoints[0].method == "POST"
        assert diff.removed_endpoints[0].change_type == "removed"

    def test_compare_modified_request_body(
        self, comparator: SpecComparator, base_spec: dict
    ):
        """Test detecting modified request body."""
        new_endpoints = []
        for ep in base_spec["endpoints"]:
            if ep["path"] == "/users" and ep["method"] == "GET":
                # Add request body to GET /users
                new_endpoints.append({**ep, "requestBody": True})
            else:
                new_endpoints.append(ep)

        new_spec = {**base_spec, "version": "1.1.0", "endpoints": new_endpoints}

        diff = comparator.compare(base_spec, new_spec)

        assert diff.has_changes is True
        assert diff.summary["modified"] == 1
        assert len(diff.modified_endpoints) == 1
        assert diff.modified_endpoints[0].path == "/users"
        assert diff.modified_endpoints[0].method == "GET"
        assert "request_body" in diff.modified_endpoints[0].changes

    def test_compare_added_parameter(
        self, comparator: SpecComparator, base_spec: dict
    ):
        """Test detecting added parameter."""
        new_endpoints = []
        for ep in base_spec["endpoints"]:
            if ep["path"] == "/users" and ep["method"] == "GET":
                # Add limit parameter
                new_params = ep["parameters"] + [
                    {"name": "limit", "in": "query", "required": False}
                ]
                new_endpoints.append({**ep, "parameters": new_params})
            else:
                new_endpoints.append(ep)

        new_spec = {**base_spec, "version": "1.1.0", "endpoints": new_endpoints}

        diff = comparator.compare(base_spec, new_spec)

        assert diff.has_changes is True
        assert diff.summary["modified"] == 1
        assert "parameters" in diff.modified_endpoints[0].changes
        assert len(diff.modified_endpoints[0].changes["parameters"]["added"]) == 1

    def test_compare_invalid_spec_not_dict(self, comparator: SpecComparator):
        """Test error when spec is not a dictionary."""
        with pytest.raises(InvalidSpecFormatException) as exc_info:
            comparator.compare("not a dict", {"endpoints": []})  # type: ignore

        assert "expected dictionary" in str(exc_info.value)

    def test_compare_invalid_spec_missing_endpoints(
        self, comparator: SpecComparator
    ):
        """Test error when spec missing endpoints field."""
        with pytest.raises(InvalidSpecFormatException) as exc_info:
            comparator.compare({"title": "Test"}, {"endpoints": []})

        assert "missing required field 'endpoints'" in str(exc_info.value)

    def test_compare_empty_specs(self, comparator: SpecComparator):
        """Test comparing empty specs returns no changes."""
        old_spec = {"endpoints": []}
        new_spec = {"endpoints": []}

        diff = comparator.compare(old_spec, new_spec)

        assert diff.has_changes is False
        assert diff.summary["added"] == 0
        assert diff.summary["removed"] == 0
        assert diff.summary["modified"] == 0

    def test_fingerprint_consistency(
        self, comparator: SpecComparator, base_spec: dict
    ):
        """Test fingerprint is consistent for same endpoint."""
        endpoint = base_spec["endpoints"][0]
        normalized = comparator._normalize_endpoint(endpoint)

        fp1 = comparator._calculate_fingerprint(normalized)
        fp2 = comparator._calculate_fingerprint(normalized)

        assert fp1 == fp2
        assert len(fp1) == 64  # SHA256 hex length

    def test_to_dict_serialization(
        self, comparator: SpecComparator, base_spec: dict
    ):
        """Test SpecDiff can be serialized to dict."""
        new_spec = {
            **base_spec,
            "endpoints": base_spec["endpoints"]
            + [
                {
                    "path": "/health",
                    "method": "GET",
                    "operationId": "healthCheck",
                    "requestBody": False,
                    "parameters": [],
                    "responses": {"200": {}},
                }
            ],
        }

        diff = comparator.compare(base_spec, new_spec)
        result = diff.to_dict()

        assert isinstance(result, dict)
        assert "added_endpoints" in result
        assert "summary" in result
        assert result["has_changes"] is True

    def test_compare_parameter_type_change(
        self, comparator: SpecComparator, base_spec: dict
    ):
        """Test detecting parameter type changes (query -> path)."""
        new_endpoints = []
        for ep in base_spec["endpoints"]:
            if ep["path"] == "/users" and ep["method"] == "GET":
                # Change 'page' parameter from query to path
                new_params = [
                    {"name": "page", "in": "path", "required": True}
                ]
                new_endpoints.append({**ep, "parameters": new_params})
            else:
                new_endpoints.append(ep)

        new_spec = {**base_spec, "version": "1.1.0", "endpoints": new_endpoints}

        diff = comparator.compare(base_spec, new_spec)

        assert diff.has_changes is True
        assert diff.summary["modified"] == 1
        assert "parameters" in diff.modified_endpoints[0].changes

    def test_compare_removed_parameter(
        self, comparator: SpecComparator, base_spec: dict
    ):
        """Test detecting removed parameter."""
        new_endpoints = []
        for ep in base_spec["endpoints"]:
            if ep["path"] == "/users" and ep["method"] == "GET":
                # Remove all parameters
                new_endpoints.append({**ep, "parameters": []})
            else:
                new_endpoints.append(ep)

        new_spec = {**base_spec, "version": "1.1.0", "endpoints": new_endpoints}

        diff = comparator.compare(base_spec, new_spec)

        assert diff.has_changes is True
        assert diff.summary["modified"] == 1
        assert "parameters" in diff.modified_endpoints[0].changes
        assert len(diff.modified_endpoints[0].changes["parameters"]["removed"]) == 1

    def test_compare_multiple_changes_simultaneously(
        self, comparator: SpecComparator, base_spec: dict
    ):
        """Test detecting multiple types of changes at once."""
        # Add new endpoint, remove one, and modify another
        new_endpoints = [
            # Keep GET /users but add a parameter
            {
                **base_spec["endpoints"][0],
                "parameters": base_spec["endpoints"][0]["parameters"]
                + [{"name": "limit", "in": "query", "required": False}],
            },
            # Remove GET /users/{id} (by not including it)
            # Keep POST /users
            base_spec["endpoints"][2],
            # Add new DELETE endpoint
            {
                "path": "/users/{id}",
                "method": "DELETE",
                "operationId": "deleteUser",
                "requestBody": False,
                "parameters": [{"name": "id", "in": "path", "required": True}],
                "responses": {"204": {}},
            },
        ]

        new_spec = {**base_spec, "version": "2.0.0", "endpoints": new_endpoints}

        diff = comparator.compare(base_spec, new_spec)

        assert diff.has_changes is True
        assert diff.summary["added"] == 1  # DELETE endpoint
        assert diff.summary["removed"] == 1  # GET /users/{id}
        assert diff.summary["modified"] == 1  # GET /users with new param

    def test_compare_response_code_change(
        self, comparator: SpecComparator, base_spec: dict
    ):
        """Test detecting changed response codes."""
        new_endpoints = []
        for ep in base_spec["endpoints"]:
            if ep["path"] == "/users" and ep["method"] == "POST":
                # Change response codes
                new_endpoints.append({
                    **ep,
                    "responses": {"200": {}, "400": {}, "409": {}},  # Added 409, changed 201->200
                })
            else:
                new_endpoints.append(ep)

        new_spec = {**base_spec, "version": "1.1.0", "endpoints": new_endpoints}

        diff = comparator.compare(base_spec, new_spec)

        assert diff.has_changes is True
        assert diff.summary["modified"] == 1
        # Response code changes should be detected
        modified_ep = diff.modified_endpoints[0]
        assert modified_ep.path == "/users"
        assert modified_ep.method == "POST"

    def test_compare_request_body_schema_change(
        self, comparator: SpecComparator
    ):
        """Test detecting changes in request body schema structure."""
        old_spec = {
            "endpoints": [
                {
                    "path": "/users",
                    "method": "POST",
                    "operationId": "createUser",
                    "requestBody": True,
                    "request_body_schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                        },
                        "required": ["name"],
                    },
                    "parameters": [],
                    "responses": {"201": {}},
                }
            ]
        }

        new_spec = {
            "endpoints": [
                {
                    "path": "/users",
                    "method": "POST",
                    "operationId": "createUser",
                    "requestBody": True,
                    "request_body_schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                            "phone": {"type": "string"},  # New field
                        },
                        "required": ["name", "email"],  # email now required
                    },
                    "parameters": [],
                    "responses": {"201": {}},
                }
            ]
        }

        comparator = SpecComparator()
        diff = comparator.compare(old_spec, new_spec)

        assert diff.has_changes is True
        assert diff.summary["modified"] == 1

    def test_fingerprint_differs_for_different_methods(
        self, comparator: SpecComparator
    ):
        """Test fingerprints differ when only method changes."""
        endpoint_get = {
            "path": "/users",
            "method": "GET",
            "operationId": "getUsers",
            "requestBody": False,
            "parameters": [],
        }
        endpoint_post = {
            "path": "/users",
            "method": "POST",
            "operationId": "createUsers",
            "requestBody": True,
            "parameters": [],
        }

        norm_get = comparator._normalize_endpoint(endpoint_get)
        norm_post = comparator._normalize_endpoint(endpoint_post)

        fp_get = comparator._calculate_fingerprint(norm_get)
        fp_post = comparator._calculate_fingerprint(norm_post)

        assert fp_get != fp_post

    def test_endpoint_key_uniqueness(self, comparator: SpecComparator):
        """Test endpoint keys uniquely identify method+path combinations."""
        spec = {
            "endpoints": [
                {"path": "/users", "method": "GET", "operationId": "listUsers"},
                {"path": "/users", "method": "POST", "operationId": "createUser"},
                {"path": "/users/{id}", "method": "GET", "operationId": "getUser"},
                {"path": "/users/{id}", "method": "PUT", "operationId": "updateUser"},
                {"path": "/users/{id}", "method": "DELETE", "operationId": "deleteUser"},
            ]
        }

        # Build endpoint keys as the comparator would
        keys = set()
        for ep in spec["endpoints"]:
            key = f"{ep['method'].upper()}:{ep['path']}"
            keys.add(key)

        # All 5 should be unique
        assert len(keys) == 5
