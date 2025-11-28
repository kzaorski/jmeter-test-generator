"""JMX file validator for JMeter Test Generator.

This module provides validation capabilities for JMeter JMX files,
checking structure, configuration, and providing improvement recommendations.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

from jmeter_gen.exceptions import JMeterGenException


class JMXValidationException(JMeterGenException):
    """Raised when JMX validation encounters critical errors.

    This exception is raised when the JMX file cannot be validated
    due to XML parsing errors or other critical issues.
    """

    pass


class JMXValidator:
    """Validate JMeter JMX test plans.

    This class provides comprehensive validation of JMX files generated
    by the JMXGenerator or created manually. It checks for required elements,
    configuration validity, and provides recommendations for improvements.
    """

    REQUIRED_ELEMENTS = [
        "jmeterTestPlan",
        "TestPlan",
        "ThreadGroup"
    ]

    def validate(self, jmx_path: str) -> Dict:
        """Validate JMX file structure and configuration.

        Args:
            jmx_path: Path to JMX file to validate

        Returns:
            Validation results containing:
            - valid: Whether the JMX file is valid
            - issues: List of problems found
            - recommendations: List of improvement suggestions

        Raises:
            FileNotFoundError: If JMX file doesn't exist
            JMXValidationException: If XML parsing fails
        """
        # Check if file exists
        jmx_file = Path(jmx_path)
        if not jmx_file.exists():
            raise FileNotFoundError(f"JMX file not found: {jmx_path}")

        # Parse XML
        try:
            tree = ET.parse(jmx_path)
            root = tree.getroot()
        except ET.ParseError as e:
            raise JMXValidationException(f"Invalid XML in JMX file: {e}")

        # Run validation checks
        issues: List[str] = []

        # Check structure
        issues.extend(self._check_structure(root))

        # Check configuration
        issues.extend(self._check_configuration(root))

        # Check samplers
        issues.extend(self._check_samplers(root))

        # Generate recommendations
        recommendations = self._generate_recommendations(root)

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "recommendations": recommendations
        }

    def _check_structure(self, root: ET.Element) -> List[str]:
        """Check for required XML elements.

        Args:
            root: Root XML element

        Returns:
            List of issues found (empty if valid)
        """
        issues: List[str] = []

        # Check root element
        if root.tag != "jmeterTestPlan":
            issues.append("Root element must be 'jmeterTestPlan'")
            return issues  # Cannot continue without proper root

        # Check for TestPlan
        test_plan = root.find(".//TestPlan")
        if test_plan is None:
            issues.append("Missing TestPlan element")

        # Check for ThreadGroup
        thread_group = root.find(".//ThreadGroup")
        if thread_group is None:
            issues.append("Missing ThreadGroup element")

        # Check hashTree structure
        main_tree = root.find("hashTree")
        if main_tree is None:
            issues.append("Missing main hashTree element after jmeterTestPlan")

        return issues

    def _check_configuration(self, root: ET.Element) -> List[str]:
        """Check ThreadGroup configuration validity.

        Args:
            root: Root XML element

        Returns:
            List of issues found (empty if valid)
        """
        issues: List[str] = []

        thread_group = root.find(".//ThreadGroup")
        if thread_group is None:
            # Already reported in structure check
            return issues

        # Check num_threads
        num_threads_elem = thread_group.find(".//stringProp[@name='ThreadGroup.num_threads']")
        if num_threads_elem is None:
            issues.append("ThreadGroup missing 'num_threads' configuration")
        else:
            try:
                num_threads = int(num_threads_elem.text or "0")
                if num_threads <= 0:
                    issues.append(f"ThreadGroup 'num_threads' must be > 0 (found: {num_threads})")
            except ValueError:
                issues.append(f"ThreadGroup 'num_threads' must be a valid number (found: '{num_threads_elem.text}')")

        # Check ramp_time
        ramp_time_elem = thread_group.find(".//stringProp[@name='ThreadGroup.ramp_time']")
        if ramp_time_elem is None:
            issues.append("ThreadGroup missing 'ramp_time' configuration")

        # Check for duration control (scheduler or loops)
        scheduler_elem = thread_group.find(".//boolProp[@name='ThreadGroup.scheduler']")
        duration_elem = thread_group.find(".//stringProp[@name='ThreadGroup.duration']")
        loops_elem = thread_group.find(".//stringProp[@name='LoopController.loops']")

        has_scheduler = scheduler_elem is not None and scheduler_elem.text == "true"
        has_duration = duration_elem is not None
        has_loops = loops_elem is not None

        if not (has_scheduler or has_loops):
            issues.append("ThreadGroup must have either scheduler enabled or loop count configured")

        # If scheduler is enabled, verify duration is set
        if has_scheduler and not has_duration:
            issues.append("ThreadGroup has scheduler enabled but missing 'duration' configuration")

        return issues

    def _check_samplers(self, root: ET.Element) -> List[str]:
        """Check for samplers in test plan.

        Args:
            root: Root XML element

        Returns:
            List of issues found (empty if valid)
        """
        issues: List[str] = []

        # Find all HTTP samplers
        samplers = root.findall(".//HTTPSamplerProxy")

        if len(samplers) == 0:
            issues.append("No HTTP samplers found in test plan")
            return issues

        # Check each sampler has required properties
        for idx, sampler in enumerate(samplers, 1):
            sampler_name = sampler.get("testname", f"Sampler #{idx}")

            # Check path (required)
            path_elem = sampler.find(".//stringProp[@name='HTTPSampler.path']")
            if path_elem is None or not path_elem.text:
                issues.append(f"Sampler '{sampler_name}' missing path configuration")

            # Check method (required)
            method_elem = sampler.find(".//stringProp[@name='HTTPSampler.method']")
            if method_elem is None or not method_elem.text:
                issues.append(f"Sampler '{sampler_name}' missing HTTP method")

            # Check if domain/port/protocol are set (either in sampler or in defaults)
            domain_elem = sampler.find(".//stringProp[@name='HTTPSampler.domain']")
            has_domain = domain_elem is not None and domain_elem.text

            # If no domain in sampler, check for HTTP Request Defaults
            if not has_domain:
                defaults = root.find(".//ConfigTestElement[@testclass='ConfigTestElement']")
                if defaults is None:
                    issues.append(f"Sampler '{sampler_name}' has no domain and no HTTP Request Defaults found")

        return issues

    def _generate_recommendations(self, root: ET.Element) -> List[str]:
        """Generate improvement suggestions for the test plan.

        Args:
            root: Root XML element

        Returns:
            List of recommendations
        """
        recommendations: List[str] = []

        # Check for CSV Data Set Config
        csv_config = root.find(".//CSVDataSet")
        if csv_config is None:
            recommendations.append("Consider adding CSV Data Set Config for parameterized test data")

        # Check for listeners
        listeners = root.findall(".//ResultCollector")
        if len(listeners) == 0:
            recommendations.append("Consider adding listeners (View Results Tree, Summary Report) for result analysis")

        # Check for timers
        timers = root.findall(".//ConstantTimer") + root.findall(".//UniformRandomTimer")
        if len(timers) == 0:
            recommendations.append("Consider adding timers to simulate realistic user think time")

        # Check for response time assertions
        assertions = root.findall(".//ResponseAssertion")
        duration_assertions = root.findall(".//DurationAssertion")

        if len(assertions) > 0 and len(duration_assertions) == 0:
            recommendations.append("Consider adding Duration Assertions for performance validation")

        # Check for HTTP Request Defaults
        defaults = root.find(".//ConfigTestElement[@testclass='ConfigTestElement']")
        if defaults is None:
            recommendations.append("Consider using HTTP Request Defaults to centralize server configuration")

        # Check for Header Manager
        header_manager = root.find(".//HeaderManager")
        if header_manager is None:
            recommendations.append("Consider adding Header Manager for Content-Type and other headers")

        # Check thread count for realistic load testing
        thread_group = root.find(".//ThreadGroup")
        if thread_group is not None:
            num_threads_elem = thread_group.find(".//stringProp[@name='ThreadGroup.num_threads']")
            if num_threads_elem is not None and num_threads_elem.text:
                try:
                    num_threads = int(num_threads_elem.text)
                    if num_threads < 10:
                        recommendations.append(f"Thread count is low ({num_threads}). Consider increasing for realistic load testing")
                except ValueError:
                    pass  # Already handled in configuration check

        # Check for assertions on all samplers
        samplers = root.findall(".//HTTPSamplerProxy")
        if len(samplers) > 0 and len(assertions) == 0:
            recommendations.append("No assertions found. Consider adding assertions to validate responses")

        return recommendations
