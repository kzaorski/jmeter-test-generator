"""JMX Updater for updating existing JMX files based on spec changes.

This module updates existing JMX files based on OpenAPI specification changes.
It parses JMX XML, matches HTTP Samplers to endpoints, and applies changes
while preserving user customizations.
"""

import shutil
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from xml.dom import minidom

from jmeter_gen.core.data_structures import SpecDiff, UpdateResult
from jmeter_gen.exceptions import JMXBackupException, JMXParseException, JMXUpdateException


class JMXUpdater:
    """Update existing JMX files based on OpenAPI spec changes.

    This class provides functionality to update JMX files when the OpenAPI
    specification changes. It can add new samplers, disable removed ones,
    and update modified endpoints while preserving user customizations.

    Example:
        >>> updater = JMXUpdater()
        >>> result = updater.update_jmx("test.jmx", spec_diff, spec_data)
        >>> print(f"Added: {result.changes_applied['added']}")
    """

    def __init__(self, project_path: str = ".") -> None:
        """Initialize JMX updater.

        Args:
            project_path: Root path of project (default: current directory).
        """
        self.project_path = Path(project_path).resolve()
        self.backup_dir = self.project_path / ".jmeter-gen" / "backups"
        self.max_backups = 10

    def update_jmx(
        self,
        jmx_path: str,
        diff: SpecDiff,
        spec_data: dict[str, Any],
    ) -> UpdateResult:
        """Apply SpecDiff changes to existing JMX file.

        Args:
            jmx_path: Path to JMX file to update.
            diff: SpecDiff from SpecComparator.
            spec_data: Full OpenAPI spec data (for generating new samplers).

        Returns:
            UpdateResult with success status and details.

        Raises:
            JMXUpdateException: If update fails critically.
        """
        backup_path = None
        changes_applied = {"added": 0, "disabled": 0, "updated": 0}
        errors: list[str] = []
        warnings: list[str] = []

        try:
            # Step 1: Create backup
            backup_path = self._create_backup(jmx_path)

            # Step 2: Parse JMX
            tree = self.parse_jmx(jmx_path)

            # Step 3-4: Find and index samplers
            samplers = self._find_samplers(tree)
            sampler_index = self._create_sampler_index(samplers, warnings)

            # Step 5: Add new endpoints
            thread_group = self._find_thread_group(tree)
            thread_group_hashtree = self._find_thread_group_hashtree(tree)

            for change in diff.added_endpoints:
                try:
                    endpoint = self._find_endpoint_in_spec(
                        spec_data, change.path, change.method
                    )
                    if endpoint:
                        self._add_new_sampler(thread_group_hashtree, endpoint)
                        changes_applied["added"] += 1
                except Exception as e:
                    errors.append(f"Failed to add {change.method} {change.path}: {e}")

            # Step 6: Disable removed endpoints
            for change in diff.removed_endpoints:
                key = (change.path, change.method)
                if key in sampler_index:
                    self._disable_sampler(sampler_index[key])
                    changes_applied["disabled"] += 1
                else:
                    warnings.append(
                        f"Could not find sampler for removed endpoint: "
                        f"{change.method} {change.path}"
                    )

            # Step 7: Update modified endpoints
            for change in diff.modified_endpoints:
                key = (change.path, change.method)
                if key in sampler_index:
                    try:
                        sampler = sampler_index[key]
                        self._update_sampler(sampler, change.changes)
                        changes_applied["updated"] += 1
                    except Exception as e:
                        errors.append(
                            f"Failed to update {change.method} {change.path}: {e}"
                        )
                else:
                    warnings.append(
                        f"Could not find sampler for modified endpoint: "
                        f"{change.method} {change.path}"
                    )

            # Step 8: Save
            tree.write(jmx_path, encoding="utf-8", xml_declaration=True)
            self._prettify_jmx(jmx_path)

        except JMXUpdateException:
            # Re-raise JMX exceptions as-is
            raise
        except Exception as e:
            # Restore from backup on unexpected error
            if backup_path and Path(backup_path).exists():
                shutil.copy2(backup_path, jmx_path)
            raise JMXUpdateException(
                f"Update failed, restored from backup: {e}"
            ) from e

        return UpdateResult(
            success=len(errors) == 0,
            jmx_path=jmx_path,
            backup_path=backup_path,
            changes_applied=changes_applied,
            errors=errors,
            warnings=warnings,
        )

    def parse_jmx(self, jmx_path: str) -> ET.ElementTree:
        """Parse JMX file to ElementTree.

        Args:
            jmx_path: Path to JMX file.

        Returns:
            Parsed ElementTree.

        Raises:
            JMXParseException: If parsing fails.
        """
        path = Path(jmx_path)
        if not path.exists():
            raise JMXParseException(f"JMX file not found: {jmx_path}")

        try:
            tree = ET.parse(jmx_path)
            root = tree.getroot()

            if root.tag != "jmeterTestPlan":
                raise JMXParseException(
                    f"Invalid JMX file: root element is '{root.tag}', "
                    f"expected 'jmeterTestPlan'"
                )

            return tree

        except ET.ParseError as e:
            raise JMXParseException(f"Failed to parse JMX file: {e}") from e

    def _create_backup(self, jmx_path: str) -> str:
        """Create timestamped backup of JMX file.

        Args:
            jmx_path: Path to JMX file.

        Returns:
            Path to backup file.

        Raises:
            JMXBackupException: If backup creation fails.
        """
        try:
            path = Path(jmx_path)
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{path.stem}.jmx.backup.{timestamp}"
            backup_path = self.backup_dir / backup_filename

            shutil.copy2(jmx_path, backup_path)

            # Rotate old backups
            self._rotate_backups(path.stem)

            return str(backup_path)

        except (OSError, IOError) as e:
            raise JMXBackupException(f"Failed to create backup: {e}") from e

    def _rotate_backups(self, jmx_basename: str) -> None:
        """Keep only last N backups, delete oldest.

        Args:
            jmx_basename: Base name of JMX file (without extension).
        """
        if not self.backup_dir.exists():
            return

        pattern = f"{jmx_basename}.jmx.backup.*"
        backups = sorted(self.backup_dir.glob(pattern))

        while len(backups) > self.max_backups:
            oldest = backups.pop(0)
            oldest.unlink()

    def _find_samplers(self, tree: ET.ElementTree) -> list[ET.Element]:
        """Find all HTTP Samplers in JMX tree.

        Args:
            tree: Parsed JMX ElementTree.

        Returns:
            List of HTTPSamplerProxy elements.
        """
        root = tree.getroot()
        return root.findall(".//HTTPSamplerProxy")

    def _match_sampler_to_endpoint(
        self, sampler: ET.Element
    ) -> Optional[tuple[str, str]]:
        """Extract (path, method) from HTTP Sampler.

        Args:
            sampler: HTTPSamplerProxy XML element.

        Returns:
            Tuple of (path, method) or None if not extractable.
        """
        path_elem = sampler.find(".//stringProp[@name='HTTPSampler.path']")
        method_elem = sampler.find(".//stringProp[@name='HTTPSampler.method']")

        if path_elem is None or method_elem is None:
            return None

        path = path_elem.text or ""
        method = (method_elem.text or "GET").upper()

        return (path, method)

    def _create_sampler_index(
        self,
        samplers: list[ET.Element],
        warnings: list[str],
    ) -> dict[tuple[str, str], ET.Element]:
        """Create index of samplers by (path, method).

        Args:
            samplers: List of HTTPSamplerProxy elements.
            warnings: List to append warnings to.

        Returns:
            Dictionary mapping (path, method) to sampler element.
        """
        index: dict[tuple[str, str], ET.Element] = {}

        for sampler in samplers:
            key = self._match_sampler_to_endpoint(sampler)
            if key is None:
                testname = sampler.get("testname", "unknown")
                warnings.append(
                    f"Could not extract path/method from sampler: {testname}"
                )
                continue

            if key in index:
                warnings.append(
                    f"Duplicate sampler for {key[1]} {key[0]}, keeping first"
                )
                continue

            index[key] = sampler

        return index

    def _find_thread_group(self, tree: ET.ElementTree) -> ET.Element:
        """Find ThreadGroup in JMX tree.

        Args:
            tree: Parsed JMX ElementTree.

        Returns:
            ThreadGroup element.

        Raises:
            JMXUpdateException: If no ThreadGroup found.
        """
        root = tree.getroot()
        thread_groups = root.findall(".//ThreadGroup")

        if not thread_groups:
            raise JMXUpdateException("No ThreadGroup found in JMX file")

        return thread_groups[0]

    def _find_thread_group_hashtree(self, tree: ET.ElementTree) -> ET.Element:
        """Find hashTree that follows ThreadGroup.

        Args:
            tree: Parsed JMX ElementTree.

        Returns:
            hashTree element that contains samplers.

        Raises:
            JMXUpdateException: If structure is invalid.
        """
        root = tree.getroot()

        # Find ThreadGroup and its following sibling hashTree
        for parent in root.iter():
            children = list(parent)
            for i, child in enumerate(children):
                if child.tag == "ThreadGroup":
                    # Next sibling should be hashTree
                    if i + 1 < len(children) and children[i + 1].tag == "hashTree":
                        return children[i + 1]

        raise JMXUpdateException("Could not find ThreadGroup hashTree in JMX file")

    def _find_endpoint_in_spec(
        self,
        spec_data: dict[str, Any],
        path: str,
        method: str,
    ) -> Optional[dict[str, Any]]:
        """Find endpoint in spec data by path and method.

        Args:
            spec_data: Parsed OpenAPI spec data.
            path: Endpoint path.
            method: HTTP method.

        Returns:
            Endpoint dictionary or None if not found.
        """
        endpoints = spec_data.get("endpoints", [])
        for ep in endpoints:
            if ep.get("path") == path and ep.get("method", "").upper() == method.upper():
                return ep
        return None

    def _add_new_sampler(
        self,
        thread_group_hashtree: ET.Element,
        endpoint: dict[str, Any],
    ) -> ET.Element:
        """Add new HTTP Sampler to ThreadGroup.

        Args:
            thread_group_hashtree: ThreadGroup's hashTree element.
            endpoint: Endpoint data from OpenAPI parser.

        Returns:
            Created HTTPSamplerProxy element.
        """
        # Create HTTP Sampler
        sampler = ET.SubElement(
            thread_group_hashtree,
            "HTTPSamplerProxy",
            {
                "guiclass": "HttpTestSampleGui",
                "testclass": "HTTPSamplerProxy",
                "testname": endpoint.get("operationId", f"{endpoint['method']} {endpoint['path']}"),
                "enabled": "true",
            },
        )

        # Add method
        method_prop = ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.method"})
        method_prop.text = endpoint.get("method", "GET").upper()

        # Add path
        path_prop = ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.path"})
        path_prop.text = endpoint.get("path", "")

        # Add other required properties
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.domain"})
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.port"})
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.protocol"})

        follow_redirects = ET.SubElement(
            sampler, "boolProp", {"name": "HTTPSampler.follow_redirects"}
        )
        follow_redirects.text = "true"

        auto_redirects = ET.SubElement(
            sampler, "boolProp", {"name": "HTTPSampler.auto_redirects"}
        )
        auto_redirects.text = "false"

        use_keepalive = ET.SubElement(
            sampler, "boolProp", {"name": "HTTPSampler.use_keepalive"}
        )
        use_keepalive.text = "true"

        # Create sampler hashTree with assertion
        sampler_hashtree = ET.SubElement(thread_group_hashtree, "hashTree")

        # Add response assertion
        self._add_default_assertion(sampler_hashtree, endpoint)

        return sampler

    def _add_default_assertion(
        self,
        sampler_hashtree: ET.Element,
        endpoint: dict[str, Any],
    ) -> None:
        """Add default response code assertion.

        Args:
            sampler_hashtree: Sampler's hashTree element.
            endpoint: Endpoint data.
        """
        # Determine expected status code
        method = endpoint.get("method", "GET").upper()
        if method == "POST":
            expected_code = "201"
        elif method == "DELETE":
            expected_code = "204"
        else:
            expected_code = "200"

        assertion = ET.SubElement(
            sampler_hashtree,
            "ResponseAssertion",
            {
                "guiclass": "AssertionGui",
                "testclass": "ResponseAssertion",
                "testname": f"Response Code {expected_code}",
                "enabled": "true",
            },
        )

        # Test field - response code
        test_field = ET.SubElement(
            assertion, "stringProp", {"name": "Assertion.test_field"}
        )
        test_field.text = "Assertion.response_code"

        # Test type - equals (16)
        test_type = ET.SubElement(
            assertion, "intProp", {"name": "Assertion.test_type"}
        )
        test_type.text = "16"

        # Test strings collection
        collection = ET.SubElement(
            assertion, "collectionProp", {"name": "Asserion.test_strings"}
        )
        string_prop = ET.SubElement(collection, "stringProp", {"name": ""})
        string_prop.text = expected_code

        # Assume success
        assume_success = ET.SubElement(
            assertion, "boolProp", {"name": "Assertion.assume_success"}
        )
        assume_success.text = "false"

        # Empty hashTree for assertion
        ET.SubElement(sampler_hashtree, "hashTree")

    def _disable_sampler(self, sampler: ET.Element) -> None:
        """Disable sampler by setting enabled='false'.

        Args:
            sampler: HTTPSamplerProxy element to disable.
        """
        sampler.set("enabled", "false")

        # Add comment explaining why disabled
        comment_prop = sampler.find(".//stringProp[@name='TestPlan.comments']")
        if comment_prop is None:
            comment_prop = ET.SubElement(
                sampler, "stringProp", {"name": "TestPlan.comments"}
            )
        comment_prop.text = "Disabled - endpoint removed from OpenAPI spec"

    def _update_sampler(
        self,
        sampler: ET.Element,
        changes: dict[str, Any],
    ) -> None:
        """Update sampler properties based on changes.

        Args:
            sampler: HTTPSamplerProxy element to update.
            changes: Specific changes from SpecDiff.
        """
        # Update operationId (testname)
        if "operation_id" in changes:
            new_op_id = changes["operation_id"]["new"]
            sampler.set("testname", new_op_id)

        # Note: Other changes (parameters, request_body) are more complex
        # and would require schema-aware updates. For MVP, we just update
        # the testname if operationId changed.

    def _prettify_jmx(self, jmx_path: str) -> None:
        """Pretty-print JMX file with proper indentation.

        Args:
            jmx_path: Path to JMX file.
        """
        with open(jmx_path, "r", encoding="utf-8") as f:
            content = f.read()

        dom = minidom.parseString(content)
        pretty = dom.toprettyxml(indent="  ")

        # Remove extra blank lines
        lines = [line for line in pretty.split("\n") if line.strip()]
        # Skip xml declaration (already in file)
        if lines and lines[0].startswith("<?xml"):
            lines = lines[1:]

        with open(jmx_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write("\n".join(lines))
