"""Project analyzer for discovering OpenAPI specifications.

This module provides functionality to scan project directories and locate
OpenAPI specification files for JMeter test generation.

Supports change detection via analyze_with_change_detection().
"""

from pathlib import Path
from typing import Any, Optional

from jmeter_gen.core.data_structures import SpecDiff
from jmeter_gen.core.openapi_parser import OpenAPIParser

# Common OpenAPI spec filenames to search for
COMMON_SPEC_NAMES = [
    "openapi.yaml",
    "openapi.yml",
    "openapi.json",
    "swagger.yaml",
    "swagger.yml",
    "swagger.json",
    "api-spec.yaml",
    "api.yaml",
]

# Common scenario filenames to search for (v2)
COMMON_SCENARIO_NAMES = [
    "pt_scenario.yaml",
    "pt_scenario.yml",
]

# Maximum directory depth for recursive search
MAX_SEARCH_DEPTH = 3


class ProjectAnalyzer:
    """Analyzes projects to discover and locate OpenAPI specifications."""

    def find_openapi_spec(self, project_path: str) -> Optional[dict[str, Any]]:
        """Find OpenAPI specification file in project directory.

        Searches for common OpenAPI spec filenames in the project root first,
        then recursively searches subdirectories up to MAX_SEARCH_DEPTH levels.
        Prefers openapi.yaml over swagger.json if multiple specs are found.

        Args:
            project_path: Root directory path of the project to analyze

        Returns:
            Dictionary with spec information if found:
                {
                    "spec_path": str,  # Absolute path to spec file
                    "format": str,     # "yaml" or "json"
                    "found": bool      # True if found
                }
            Returns None if no spec file is found

        Raises:
            No exceptions raised - returns None on error
        """
        all_specs = self.find_all_openapi_specs(project_path)
        return all_specs[0] if all_specs else None

    def find_all_openapi_specs(self, project_path: str) -> list[dict[str, Any]]:
        """Find all OpenAPI specification files in project directory.

        Searches for common OpenAPI spec filenames in the project root first,
        then recursively searches subdirectories up to MAX_SEARCH_DEPTH levels.
        Results are sorted by priority (openapi > swagger, yaml > json, root > subdirs).

        Args:
            project_path: Root directory path of the project to analyze

        Returns:
            List of spec dictionaries sorted by priority (best match first):
                [
                    {
                        "spec_path": str,  # Absolute path to spec file
                        "format": str,     # "yaml" or "json"
                        "found": bool      # True
                    },
                    ...
                ]
            Returns empty list if no spec files are found

        Raises:
            No exceptions raised - returns empty list on error
        """
        try:
            project_dir = Path(project_path).resolve()

            # Validate project path exists
            if not project_dir.exists() or not project_dir.is_dir():
                return []

            found_specs: list[dict[str, Any]] = []

            # First, check common spec names in project root
            for spec_name in COMMON_SPEC_NAMES:
                spec_path = project_dir / spec_name
                if spec_path.exists() and spec_path.is_file():
                    found_specs.append({
                        "spec_path": str(spec_path),
                        "format": "yaml" if spec_name.endswith((".yaml", ".yml")) else "json",
                        "found": True,
                        "in_root": True,
                    })

            # Search subdirectories recursively
            self._search_subdirectories(project_dir, 0, found_specs)

            if not found_specs:
                return []

            # Sort by preference:
            # 1. Root directory first (in_root=True)
            # 2. OpenAPI naming preferred over swagger
            # 3. YAML preferred over JSON
            found_specs.sort(
                key=lambda x: (
                    not x.get("in_root", False),
                    "openapi" not in x["spec_path"].lower(),
                    x["format"] == "json",
                )
            )

            return found_specs

        except (OSError, PermissionError):
            # Return empty list on filesystem errors
            return []

    def _search_subdirectories(self, current_dir: Path, depth: int, found_specs: list) -> None:
        """Recursively search subdirectories for OpenAPI specs.

        Args:
            current_dir: Current directory to search
            depth: Current search depth
            found_specs: List to accumulate found spec file info
        """
        if depth >= MAX_SEARCH_DEPTH:
            return

        try:
            for item in current_dir.iterdir():
                # Skip hidden directories and common exclude patterns
                if item.name.startswith(".") or item.name in {
                    "node_modules",
                    "__pycache__",
                    "venv",
                    "env",
                    ".git",
                }:
                    continue

                if item.is_dir():
                    # Check for spec files in this subdirectory
                    for spec_name in COMMON_SPEC_NAMES:
                        spec_path = item / spec_name
                        if spec_path.exists() and spec_path.is_file():
                            found_specs.append(
                                {
                                    "spec_path": str(spec_path),
                                    "format": "yaml"
                                    if spec_name.endswith((".yaml", ".yml"))
                                    else "json",
                                    "found": True,
                                }
                            )

                    # Continue recursive search
                    self._search_subdirectories(item, depth + 1, found_specs)

        except (OSError, PermissionError):
            # Skip directories with permission issues
            pass

    def analyze_project(self, project_path: str) -> dict:
        """Analyze project and extract OpenAPI spec information.

        Finds the OpenAPI spec file and parses it to extract metadata,
        endpoints, and generate recommendations for JMX test plan generation.

        Args:
            project_path: Root directory path of the project to analyze

        Returns:
            Dictionary with analysis results if spec found:
                {
                    "openapi_spec_found": bool,
                    "spec_path": str,
                    "spec_format": str,
                    "endpoints_count": int,
                    "endpoints": List[Dict],
                    "base_url": str,
                    "api_title": str,
                    "recommended_jmx_name": str,
                    "available_specs": List[Dict],  # All found specs
                    "multiple_specs_found": bool    # True if >1 spec found
                }
            Or error dictionary if spec not found:
                {
                    "openapi_spec_found": False,
                    "message": str,
                    "available_specs": [],
                    "multiple_specs_found": False
                }

        Raises:
            No exceptions raised - returns error dict on failure
        """
        # Find all spec files
        all_specs = self.find_all_openapi_specs(project_path)

        if not all_specs:
            return {
                "openapi_spec_found": False,
                "message": f"No OpenAPI specification found in {project_path}",
                "available_specs": [],
                "multiple_specs_found": False,
            }

        # Use the first (best match) spec for primary analysis
        spec_info = all_specs[0]

        try:
            # Parse the OpenAPI spec to get real metadata
            parser = OpenAPIParser()
            spec_data = parser.parse(spec_info["spec_path"])

            api_title = spec_data.get("title", "Unknown API")

            return {
                "openapi_spec_found": True,
                "spec_path": spec_info["spec_path"],
                "spec_format": spec_info["format"],
                "api_title": api_title,
                "recommended_jmx_name": self._generate_jmx_name(api_title),
                "endpoints_count": len(spec_data.get("endpoints", [])),
                "endpoints": spec_data.get("endpoints", []),
                "base_url": spec_data.get("base_url", ""),
                # Multi-spec support
                "available_specs": all_specs,
                "multiple_specs_found": len(all_specs) > 1,
            }

        except (OSError, PermissionError, ValueError) as e:
            return {
                "openapi_spec_found": False,
                "message": f"Error analyzing spec at {spec_info['spec_path']}: {e}",
                "available_specs": all_specs,
                "multiple_specs_found": len(all_specs) > 1,
            }

    def _generate_jmx_name(self, api_title: str) -> str:
        """Generate recommended JMX filename from API title.

        Converts API title to a standardized JMX filename format:
        lowercase, spaces to hyphens, appends "-test.jmx"

        Args:
            api_title: API title from OpenAPI spec

        Returns:
            Recommended JMX filename

        Example:
            >>> analyzer = ProjectAnalyzer()
            >>> analyzer._generate_jmx_name("User Management API")
            'user-management-api-test.jmx'
        """
        # Convert to lowercase and replace spaces/periods with hyphens
        filename = api_title.lower().replace(" ", "-").replace(".", "-")

        # Remove any characters that aren't alphanumeric or hyphens
        filename = "".join(c for c in filename if c.isalnum() or c == "-")

        # Remove consecutive hyphens
        while "--" in filename:
            filename = filename.replace("--", "-")

        # Remove leading/trailing hyphens
        filename = filename.strip("-")

        # Handle empty string case
        if not filename:
            return "test.jmx"

        # Append suffix
        return f"{filename}-test.jmx"

    def analyze_with_change_detection(
        self,
        project_path: str,
        jmx_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """Analyze project with change detection from snapshot.

        Extends analyze_project() with change detection by comparing current
        spec with saved snapshot.

        Args:
            project_path: Root directory path of the project to analyze.
            jmx_path: Path to JMX file for snapshot lookup.
                     If None, uses recommended_jmx_name from analysis.

        Returns:
            Dictionary with analysis results plus change detection:
                {
                    ... (all analyze_project fields) ...
                    "changes_detected": bool,
                    "spec_diff": Optional[SpecDiff],
                    "snapshot_exists": bool,
                    "snapshot_path": Optional[str],
                }

        Example:
            >>> analyzer = ProjectAnalyzer()
            >>> result = analyzer.analyze_with_change_detection("/path/to/project")
            >>> if result.get("changes_detected"):
            ...     print(f"Changes: {result['spec_diff'].summary}")
        """
        # Import here to avoid circular imports
        from jmeter_gen.core.openapi_parser import OpenAPIParser
        from jmeter_gen.core.snapshot_manager import SnapshotManager
        from jmeter_gen.core.spec_comparator import SpecComparator

        # First, do basic analysis
        result = self.analyze_project(project_path)

        # Add change detection fields with defaults
        result["changes_detected"] = False
        result["spec_diff"] = None
        result["snapshot_exists"] = False
        result["snapshot_path"] = None

        # If no spec found, return early
        if not result.get("openapi_spec_found"):
            return result

        try:
            # Parse the current spec
            parser = OpenAPIParser()
            spec_data = parser.parse(result["spec_path"])

            # Update result with parsed data
            result["endpoints_count"] = len(spec_data.get("endpoints", []))
            result["endpoints"] = spec_data.get("endpoints", [])
            result["base_url"] = spec_data.get("base_url", "")
            result["api_title"] = spec_data.get("title", result.get("api_title", ""))

            # Initialize snapshot manager in spec's directory (not project_path)
            # Snapshots are stored alongside the spec file
            spec_dir = str(Path(result["spec_path"]).parent)
            manager = SnapshotManager(spec_dir)

            # Find snapshot by spec path (more reliable than JMX-based lookup)
            snapshot = None
            snapshot_path = None
            snapshot_result = manager.find_snapshot_for_spec(result["spec_path"])
            if snapshot_result:
                snapshot, snapshot_path = snapshot_result

            if snapshot:
                result["snapshot_exists"] = True
                result["snapshot_path"] = str(snapshot_path)

                # Compare current spec with snapshot
                snapshot_spec_data = {
                    "endpoints": snapshot.get("endpoints", []),
                    "version": snapshot.get("spec", {}).get("api_version", ""),
                }

                comparator = SpecComparator()
                diff = comparator.compare(snapshot_spec_data, spec_data)

                if diff.has_changes:
                    result["changes_detected"] = True
                    result["spec_diff"] = diff

        except (OSError, ValueError, KeyError):
            # On parser/comparator error, return result without change detection
            pass

        return result

    def find_scenario_file(self, project_path: str = ".") -> Optional[str]:
        """Find pt_scenario.yaml file in project directory.

        Searches for scenario file in the following order:
        1. pt_scenario.yaml in project root
        2. pt_scenario.yml in project root
        3. *_scenario.yaml / *_scenario.yml patterns in root

        Args:
            project_path: Root directory path of the project to analyze

        Returns:
            Path to scenario file if found, None otherwise

        Example:
            >>> analyzer = ProjectAnalyzer()
            >>> scenario = analyzer.find_scenario_file("/path/to/project")
            >>> if scenario:
            ...     print(f"Found scenario: {scenario}")
        """
        try:
            project_dir = Path(project_path).resolve()

            if not project_dir.exists() or not project_dir.is_dir():
                return None

            # Check common scenario names in root
            for name in COMMON_SCENARIO_NAMES:
                scenario_path = project_dir / name
                if scenario_path.exists() and scenario_path.is_file():
                    return str(scenario_path)

            # Check for *_scenario.yaml pattern in root
            for pattern in ["*_scenario.yaml", "*_scenario.yml"]:
                matches = list(project_dir.glob(pattern))
                if matches:
                    # Return first match (sorted for determinism)
                    return str(sorted(matches)[0])

            return None

        except (OSError, PermissionError):
            return None
