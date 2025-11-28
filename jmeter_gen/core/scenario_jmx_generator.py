"""JMX Generator for scenario-based test plans (v2).

This module generates JMeter JMX files from parsed scenarios with
JSONPostProcessor elements for variable extraction and correlation.
"""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse
from xml.dom import minidom

from jmeter_gen.core.openapi_parser import OpenAPIParser
from jmeter_gen.core.scenario_data import (
    AssertConfig,
    CorrelationMapping,
    CorrelationResult,
    LoopConfig,
    ParsedScenario,
    ScenarioStep,
)
from jmeter_gen.exceptions import JMXGenerationException

# Pattern to extract JSONPath field from while condition
# e.g., "$.status != 'finished'" -> "status"
JSONPATH_FIELD_PATTERN = re.compile(r"\$\.([a-zA-Z_][a-zA-Z0-9_]*)")


class ScenarioJMXGenerator:
    """Generate JMeter JMX files from scenarios with correlation support.

    Creates sequential HTTP samplers with JSONPostProcessor elements
    for variable extraction, enabling realistic user flow testing.

    Example:
        >>> parser = OpenAPIParser()
        >>> spec = parser.parse("openapi.yaml")
        >>> generator = ScenarioJMXGenerator(parser)
        >>> result = generator.generate(scenario, "output.jmx")
    """

    def __init__(
        self,
        openapi_parser: OpenAPIParser,
    ) -> None:
        """Initialize generator.

        Args:
            openapi_parser: Parser instance with parsed spec data
        """
        self.openapi_parser = openapi_parser

    def generate(
        self,
        scenario: ParsedScenario,
        output_path: str,
        base_url: Optional[str] = None,
        correlation_result: Optional[CorrelationResult] = None,
    ) -> dict[str, Any]:
        """Generate JMX file from scenario.

        Args:
            scenario: Parsed scenario to generate
            output_path: Path where to save JMX file
            base_url: Override base URL (uses scenario/spec URL if not provided)
            correlation_result: Pre-computed correlation mappings

        Returns:
            Dictionary with generation results:
            {
                "success": bool,
                "jmx_path": str,
                "samplers_created": int,
                "extractors_created": int,
                "assertions_created": int,
                "loops_created": int,
                "correlation_warnings": list[str],
                "correlation_errors": list[str]
            }

        Raises:
            JMXGenerationException: If generation fails
        """
        try:
            # Determine effective base URL
            effective_base_url = (
                base_url
                or scenario.settings.base_url
                or "http://localhost:8080"
            )

            # Parse URL
            domain, port, protocol = self._parse_url(effective_base_url)

            # Build mapping lookup for quick access
            mapping_by_step: dict[int, list[CorrelationMapping]] = {}
            if correlation_result:
                for mapping in correlation_result.mappings:
                    step_idx = mapping.source_step
                    if step_idx not in mapping_by_step:
                        mapping_by_step[step_idx] = []
                    mapping_by_step[step_idx].append(mapping)

            # Create JMX structure
            jmeter_test_plan = ET.Element(
                "jmeterTestPlan",
                {"version": "1.2", "properties": "5.0", "jmeter": "5.0"},
            )

            main_hashtree = ET.SubElement(jmeter_test_plan, "hashTree")

            # Test Plan
            test_plan = self._create_test_plan(scenario.name, scenario.version)
            main_hashtree.append(test_plan)

            test_plan_hashtree = ET.SubElement(main_hashtree, "hashTree")

            # HTTP Request Defaults
            http_defaults = self._create_http_defaults(domain, port, protocol)
            test_plan_hashtree.append(http_defaults)
            ET.SubElement(test_plan_hashtree, "hashTree")

            # User Defined Variables (from scenario.variables)
            if scenario.variables:
                udv = self._create_user_defined_variables(scenario.variables)
                test_plan_hashtree.append(udv)
                ET.SubElement(test_plan_hashtree, "hashTree")

            # Listeners
            view_results = self._create_view_results_tree_listener()
            test_plan_hashtree.append(view_results)
            ET.SubElement(test_plan_hashtree, "hashTree")

            aggregate_report = self._create_aggregate_report_listener()
            test_plan_hashtree.append(aggregate_report)
            ET.SubElement(test_plan_hashtree, "hashTree")

            # Thread Group
            thread_group = self._create_thread_group(
                scenario.settings.threads,
                scenario.settings.rampup,
                scenario.settings.duration,
            )
            test_plan_hashtree.append(thread_group)

            thread_group_hashtree = ET.SubElement(test_plan_hashtree, "hashTree")

            # Create samplers for each step
            samplers_created = 0
            extractors_created = 0
            assertions_created = 0
            loops_created = 0

            for step_index, step in enumerate(scenario.steps, start=1):
                if not step.enabled:
                    continue

                # Get correlation mappings for this step
                step_mappings = mapping_by_step.get(step_index, [])

                # Resolve endpoint to get full path info
                endpoint_data = self._resolve_endpoint(step)

                # Determine where to add the sampler (directly to thread group or inside loop controller)
                if step.loop:
                    # Create loop controller and add it to thread group
                    if step.loop.count:
                        # Fixed count loop
                        loop_controller = self._create_loop_controller(step.name, step.loop.count)
                    else:
                        # While loop (condition-based)
                        loop_controller = self._create_while_controller(
                            step.name,
                            step.loop.while_condition or "",
                            step.loop.max_iterations,
                        )

                    thread_group_hashtree.append(loop_controller)
                    loop_hashtree = ET.SubElement(thread_group_hashtree, "hashTree")
                    loops_created += 1

                    # Sampler goes inside loop controller
                    parent_hashtree = loop_hashtree
                else:
                    # No loop - sampler goes directly in thread group
                    parent_hashtree = thread_group_hashtree

                # Create HTTP Sampler
                sampler = self._create_step_sampler(step, endpoint_data, step_index)
                parent_hashtree.append(sampler)
                samplers_created += 1

                # Sampler hashTree for children
                sampler_hashtree = ET.SubElement(parent_hashtree, "hashTree")

                # Add Header Manager if headers present
                if step.headers:
                    header_mgr = self._create_header_manager(step.headers)
                    sampler_hashtree.append(header_mgr)
                    ET.SubElement(sampler_hashtree, "hashTree")

                # Add JSONPostProcessor for each capture
                for mapping in step_mappings:
                    extractor = self._create_json_post_processor(mapping)
                    sampler_hashtree.append(extractor)
                    ET.SubElement(sampler_hashtree, "hashTree")
                    extractors_created += 1

                # For while loops, add extractor for the condition variable
                if step.loop and step.loop.while_condition:
                    condition_extractor = self._create_condition_extractor(step.loop.while_condition)
                    if condition_extractor is not None:
                        sampler_hashtree.append(condition_extractor)
                        ET.SubElement(sampler_hashtree, "hashTree")
                        extractors_created += 1

                # Add constant timer for loop interval
                if step.loop and step.loop.interval:
                    timer = self._create_constant_timer(step.loop.interval)
                    sampler_hashtree.append(timer)
                    ET.SubElement(sampler_hashtree, "hashTree")

                # Add assertions
                if step.assertions:
                    assertion_elements = self._create_response_assertions(step.assertions)
                    for assertion in assertion_elements:
                        sampler_hashtree.append(assertion)
                        ET.SubElement(sampler_hashtree, "hashTree")
                        assertions_created += 1

            # Convert to pretty XML and write
            xml_string = self._prettify_xml(jmeter_test_plan)
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(xml_string, encoding="utf-8")

            return {
                "success": True,
                "jmx_path": str(output_file.absolute()),
                "samplers_created": samplers_created,
                "extractors_created": extractors_created,
                "assertions_created": assertions_created,
                "loops_created": loops_created,
                "correlation_warnings": correlation_result.warnings if correlation_result else [],
                "correlation_errors": correlation_result.errors if correlation_result else [],
            }

        except Exception as e:
            if isinstance(e, JMXGenerationException):
                raise
            raise JMXGenerationException(f"Failed to generate scenario JMX: {e}") from e

    def _resolve_endpoint(self, step: ScenarioStep) -> dict[str, Any]:
        """Resolve endpoint to get path and method."""
        if step.endpoint_type == "operation_id":
            endpoint = self.openapi_parser.get_endpoint_by_operation_id(step.endpoint)
            if endpoint:
                return {
                    "path": endpoint["path"],
                    "method": endpoint["method"],
                    "operation": endpoint.get("operation", {}),
                }
            # Fallback if not found in spec
            return {
                "path": f"/{step.endpoint}",
                "method": "GET",
                "operation": {},
            }
        else:
            # method_path type
            return {
                "path": step.path or "/",
                "method": step.method or "GET",
                "operation": {},
            }

    def _create_step_sampler(
        self,
        step: ScenarioStep,
        endpoint_data: dict[str, Any],
        step_index: int,
    ) -> ET.Element:
        """Create HTTP Sampler for scenario step."""
        path = endpoint_data["path"]
        method = endpoint_data["method"]

        # Apply parameter substitutions to path
        if step.params:
            path = self._substitute_path_params(path, step.params)

        # Convert remaining {param} to ${param}
        path = self._convert_path_params(path)

        # Create sampler
        sampler = ET.Element(
            "HTTPSamplerProxy",
            {
                "guiclass": "HttpTestSampleGui",
                "testclass": "HTTPSamplerProxy",
                "testname": f"[{step_index}] {step.name}",
                "enabled": "true",
            },
        )

        # Arguments element
        if step.params:
            args_elem = self._create_query_params_element(step.params)
            sampler.append(args_elem)
        else:
            args_elem = ET.SubElement(
                sampler,
                "elementProp",
                {
                    "name": "HTTPsampler.Arguments",
                    "elementType": "Arguments",
                    "guiclass": "HTTPArgumentsPanel",
                    "testclass": "Arguments",
                    "testname": "User Defined Variables",
                    "enabled": "true",
                },
            )
            ET.SubElement(args_elem, "collectionProp", {"name": "Arguments.arguments"})

        # Empty domain/port/protocol (inherited from defaults)
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.domain"})
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.port"})
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.protocol"})

        # Path and method
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.path"}).text = path
        ET.SubElement(sampler, "stringProp", {"name": "HTTPSampler.method"}).text = method

        # Follow redirects
        ET.SubElement(sampler, "boolProp", {"name": "HTTPSampler.follow_redirects"}).text = "true"
        ET.SubElement(sampler, "boolProp", {"name": "HTTPSampler.use_keepalive"}).text = "true"
        ET.SubElement(sampler, "boolProp", {"name": "HTTPSampler.auto_redirects"}).text = "false"

        # Request body
        if step.payload:
            payload_json = json.dumps(step.payload, indent=2)
            ET.SubElement(sampler, "boolProp", {"name": "HTTPSampler.postBodyRaw"}).text = "true"

            body_elem = ET.SubElement(
                sampler,
                "elementProp",
                {"name": "HTTPsampler.Arguments", "elementType": "Arguments"},
            )
            body_coll = ET.SubElement(body_elem, "collectionProp", {"name": "Arguments.arguments"})
            body_arg = ET.SubElement(
                body_coll,
                "elementProp",
                {"name": "", "elementType": "HTTPArgument"},
            )
            ET.SubElement(body_arg, "boolProp", {"name": "HTTPArgument.always_encode"}).text = "false"
            ET.SubElement(body_arg, "stringProp", {"name": "Argument.value"}).text = payload_json
            ET.SubElement(body_arg, "stringProp", {"name": "Argument.metadata"}).text = "="

        return sampler

    def _create_json_post_processor(self, mapping: CorrelationMapping) -> ET.Element:
        """Create JSONPostProcessor element for variable extraction.

        Args:
            mapping: Correlation mapping with variable name and JSONPath

        Returns:
            JSONPostProcessor XML Element
        """
        extractor = ET.Element(
            "JSONPostProcessor",
            {
                "guiclass": "JSONPostProcessorGui",
                "testclass": "JSONPostProcessor",
                "testname": f"Extract {mapping.variable_name}",
                "enabled": "true",
            },
        )

        # Variable name
        ET.SubElement(
            extractor,
            "stringProp",
            {"name": "JSONPostProcessor.referenceNames"},
        ).text = mapping.variable_name

        # JSONPath expression
        ET.SubElement(
            extractor,
            "stringProp",
            {"name": "JSONPostProcessor.jsonPathExprs"},
        ).text = mapping.jsonpath

        # Match number (1 = first, -1 = all, 0 = random)
        match_num = "1"  # Default to first
        if hasattr(mapping, "match") and mapping.match == "all":
            match_num = "-1"
        ET.SubElement(
            extractor,
            "stringProp",
            {"name": "JSONPostProcessor.match_numbers"},
        ).text = match_num

        # Default value
        ET.SubElement(
            extractor,
            "stringProp",
            {"name": "JSONPostProcessor.defaultValues"},
        ).text = "NOT_FOUND"

        return extractor

    def _create_response_assertions(self, assertions: AssertConfig) -> list[ET.Element]:
        """Create assertion elements from AssertConfig."""
        elements: list[ET.Element] = []

        # Status code assertion
        if assertions.status:
            assertion = ET.Element(
                "ResponseAssertion",
                {
                    "guiclass": "AssertionGui",
                    "testclass": "ResponseAssertion",
                    "testname": f"Assert Status {assertions.status}",
                    "enabled": "true",
                },
            )
            ET.SubElement(
                assertion,
                "stringProp",
                {"name": "Assertion.test_field"},
            ).text = "Assertion.response_code"
            ET.SubElement(
                assertion,
                "intProp",
                {"name": "Assertion.test_type"},
            ).text = "8"  # equals
            coll_prop = ET.SubElement(
                assertion,
                "collectionProp",
                {"name": "Asserion.test_strings"},  # JMeter typo
            )
            ET.SubElement(
                coll_prop,
                "stringProp",
                {"name": str(hash(str(assertions.status)))},
            ).text = str(assertions.status)
            elements.append(assertion)

        # Body assertions (JSONPath)
        for field, expected in assertions.body.items():
            assertion = ET.Element(
                "JSONPathAssertion",
                {
                    "guiclass": "JSONPathAssertionGui",
                    "testclass": "JSONPathAssertion",
                    "testname": f"Assert {field}",
                    "enabled": "true",
                },
            )
            ET.SubElement(
                assertion,
                "stringProp",
                {"name": "JSON_PATH"},
            ).text = f"$.{field}"
            ET.SubElement(
                assertion,
                "stringProp",
                {"name": "EXPECTED_VALUE"},
            ).text = str(expected)
            ET.SubElement(
                assertion,
                "boolProp",
                {"name": "JSONVALIDATION"},
            ).text = "true"
            ET.SubElement(
                assertion,
                "boolProp",
                {"name": "EXPECT_NULL"},
            ).text = "false"
            ET.SubElement(
                assertion,
                "boolProp",
                {"name": "INVERT"},
            ).text = "false"
            elements.append(assertion)

        return elements

    def _substitute_path_params(self, path: str, params: dict[str, Any]) -> str:
        """Substitute parameter values in path."""
        result = path
        for name, value in params.items():
            # Replace {name} with value
            result = result.replace(f"{{{name}}}", str(value))
        return result

    def _convert_path_params(self, path: str) -> str:
        """Convert {param} to ${param} for JMeter."""
        return re.sub(r"\{([^}]+)\}", r"${\1}", path)

    def _create_query_params_element(self, params: dict[str, Any]) -> ET.Element:
        """Create query parameters element."""
        elem_prop = ET.Element(
            "elementProp",
            {
                "name": "HTTPsampler.Arguments",
                "elementType": "Arguments",
                "guiclass": "HTTPArgumentsPanel",
                "testclass": "Arguments",
                "testname": "User Defined Variables",
                "enabled": "true",
            },
        )
        coll_prop = ET.SubElement(elem_prop, "collectionProp", {"name": "Arguments.arguments"})

        for name, value in params.items():
            # Skip path parameters (they're in the URL)
            if isinstance(value, str) and (value.startswith("${") or "{" in value):
                continue

            arg_elem = ET.SubElement(
                coll_prop,
                "elementProp",
                {"name": name, "elementType": "HTTPArgument"},
            )
            ET.SubElement(arg_elem, "boolProp", {"name": "HTTPArgument.always_encode"}).text = "false"
            ET.SubElement(arg_elem, "stringProp", {"name": "Argument.name"}).text = name
            ET.SubElement(arg_elem, "stringProp", {"name": "Argument.value"}).text = str(value)
            ET.SubElement(arg_elem, "stringProp", {"name": "Argument.metadata"}).text = "="
            ET.SubElement(arg_elem, "boolProp", {"name": "HTTPArgument.use_equals"}).text = "true"

        return elem_prop

    def _create_user_defined_variables(self, variables: dict[str, Any]) -> ET.Element:
        """Create User Defined Variables element."""
        udv = ET.Element(
            "Arguments",
            {
                "guiclass": "ArgumentsPanel",
                "testclass": "Arguments",
                "testname": "User Defined Variables",
                "enabled": "true",
            },
        )
        coll_prop = ET.SubElement(udv, "collectionProp", {"name": "Arguments.arguments"})

        for name, value in variables.items():
            elem_prop = ET.SubElement(
                coll_prop,
                "elementProp",
                {"name": name, "elementType": "Argument"},
            )
            ET.SubElement(elem_prop, "stringProp", {"name": "Argument.name"}).text = name
            ET.SubElement(elem_prop, "stringProp", {"name": "Argument.value"}).text = str(value)
            ET.SubElement(elem_prop, "stringProp", {"name": "Argument.metadata"}).text = "="

        return udv

    # === Reused methods from JMXGenerator ===

    def _parse_url(self, url: str) -> tuple[str, str, str]:
        """Parse URL to extract domain, port, and protocol."""
        try:
            parsed = urlparse(url)
            protocol = parsed.scheme or "http"
            domain = parsed.hostname or "localhost"
            port = str(parsed.port) if parsed.port else ""
            return domain, port, protocol
        except Exception as e:
            raise JMXGenerationException(f"Failed to parse URL '{url}': {e}") from e

    def _prettify_xml(self, elem: ET.Element) -> str:
        """Convert XML Element to pretty-printed string."""
        rough_string = ET.tostring(elem, encoding="unicode")
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        lines = [line for line in pretty_xml.split("\n") if line.strip()]
        return "\n".join(lines)

    def _create_test_plan(self, title: str, version: str) -> ET.Element:
        """Create Test Plan element."""
        test_plan = ET.Element(
            "TestPlan",
            {
                "guiclass": "TestPlanGui",
                "testclass": "TestPlan",
                "testname": f"{title} v{version}",
                "enabled": "true",
            },
        )
        ET.SubElement(test_plan, "boolProp", {"name": "TestPlan.functional_mode"}).text = "false"
        ET.SubElement(test_plan, "boolProp", {"name": "TestPlan.serialize_threadgroups"}).text = "false"

        elem_prop = ET.SubElement(
            test_plan,
            "elementProp",
            {
                "name": "TestPlan.user_defined_variables",
                "elementType": "Arguments",
                "guiclass": "ArgumentsPanel",
                "testclass": "Arguments",
                "testname": "User Defined Variables",
                "enabled": "true",
            },
        )
        ET.SubElement(elem_prop, "collectionProp", {"name": "Arguments.arguments"})
        return test_plan

    def _create_thread_group(
        self, threads: int, rampup: int, duration: Optional[int]
    ) -> ET.Element:
        """Create Thread Group element."""
        thread_group = ET.Element(
            "ThreadGroup",
            {
                "guiclass": "ThreadGroupGui",
                "testclass": "ThreadGroup",
                "testname": "Scenario Thread Group",
                "enabled": "true",
            },
        )

        ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.num_threads"}).text = str(threads)
        ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.ramp_time"}).text = str(rampup)

        if duration:
            ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.duration"}).text = str(duration)
            ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.delay"}).text = "0"
            ET.SubElement(thread_group, "boolProp", {"name": "ThreadGroup.scheduler"}).text = "true"
            loop_count = "-1"
        else:
            ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.duration"}).text = ""
            ET.SubElement(thread_group, "stringProp", {"name": "ThreadGroup.delay"}).text = ""
            ET.SubElement(thread_group, "boolProp", {"name": "ThreadGroup.scheduler"}).text = "false"
            loop_count = "1"

        loop_controller = ET.SubElement(
            thread_group,
            "elementProp",
            {
                "name": "ThreadGroup.main_controller",
                "elementType": "LoopController",
                "guiclass": "LoopControlPanel",
                "testclass": "LoopController",
                "testname": "Loop Controller",
                "enabled": "true",
            },
        )
        ET.SubElement(loop_controller, "stringProp", {"name": "LoopController.loops"}).text = loop_count
        ET.SubElement(loop_controller, "boolProp", {"name": "LoopController.continue_forever"}).text = "false"

        return thread_group

    def _create_http_defaults(self, domain: str, port: str, protocol: str) -> ET.Element:
        """Create HTTP Request Defaults element."""
        config = ET.Element(
            "ConfigTestElement",
            {
                "guiclass": "HttpDefaultsGui",
                "testclass": "ConfigTestElement",
                "testname": "HTTP Request Defaults",
                "enabled": "true",
            },
        )

        elem_prop = ET.SubElement(
            config,
            "elementProp",
            {
                "name": "HTTPsampler.Arguments",
                "elementType": "Arguments",
                "guiclass": "HTTPArgumentsPanel",
                "testclass": "Arguments",
                "testname": "User Defined Variables",
                "enabled": "true",
            },
        )
        ET.SubElement(elem_prop, "collectionProp", {"name": "Arguments.arguments"})

        ET.SubElement(config, "stringProp", {"name": "HTTPSampler.domain"}).text = domain
        ET.SubElement(config, "stringProp", {"name": "HTTPSampler.port"}).text = port
        ET.SubElement(config, "stringProp", {"name": "HTTPSampler.protocol"}).text = protocol

        return config

    def _create_header_manager(self, headers: dict[str, str]) -> ET.Element:
        """Create Header Manager element."""
        header_manager = ET.Element(
            "HeaderManager",
            {
                "guiclass": "HeaderPanel",
                "testclass": "HeaderManager",
                "testname": "HTTP Header Manager",
                "enabled": "true",
            },
        )
        coll_prop = ET.SubElement(header_manager, "collectionProp", {"name": "HeaderManager.headers"})

        for name, value in headers.items():
            elem_prop = ET.SubElement(coll_prop, "elementProp", {"name": "", "elementType": "Header"})
            ET.SubElement(elem_prop, "stringProp", {"name": "Header.name"}).text = name
            ET.SubElement(elem_prop, "stringProp", {"name": "Header.value"}).text = value

        return header_manager

    def _create_view_results_tree_listener(self) -> ET.Element:
        """Create View Results Tree listener."""
        listener = ET.Element(
            "ResultCollector",
            {
                "guiclass": "ViewResultsFullVisualizer",
                "testclass": "ResultCollector",
                "testname": "View Results Tree",
                "enabled": "true",
            },
        )
        ET.SubElement(listener, "boolProp", {"name": "ResultCollector.error_logging"}).text = "false"

        obj_prop = ET.SubElement(listener, "objProp")
        ET.SubElement(obj_prop, "name").text = "saveConfig"
        value_elem = ET.SubElement(obj_prop, "value", {"class": "SampleSaveConfiguration"})

        for key in ["time", "latency", "timestamp", "success", "label", "code", "message"]:
            ET.SubElement(value_elem, key).text = "true"

        return listener

    def _create_aggregate_report_listener(self) -> ET.Element:
        """Create Aggregate Report listener."""
        listener = ET.Element(
            "ResultCollector",
            {
                "guiclass": "StatVisualizer",
                "testclass": "ResultCollector",
                "testname": "Aggregate Report",
                "enabled": "true",
            },
        )
        ET.SubElement(listener, "boolProp", {"name": "ResultCollector.error_logging"}).text = "false"

        obj_prop = ET.SubElement(listener, "objProp")
        ET.SubElement(obj_prop, "name").text = "saveConfig"
        value_elem = ET.SubElement(obj_prop, "value", {"class": "SampleSaveConfiguration"})

        for key in ["time", "latency", "timestamp", "success", "label", "code", "message"]:
            ET.SubElement(value_elem, key).text = "true"

        return listener

    # === Loop Controller Methods ===

    def _create_loop_controller(self, name: str, count: int) -> ET.Element:
        """Create LoopController element for fixed count loops.

        Args:
            name: Display name for the controller
            count: Number of iterations

        Returns:
            LoopController XML Element
        """
        controller = ET.Element(
            "LoopController",
            {
                "guiclass": "LoopControlPanel",
                "testclass": "LoopController",
                "testname": f"{name} Loop",
                "enabled": "true",
            },
        )
        ET.SubElement(
            controller,
            "boolProp",
            {"name": "LoopController.continue_forever"},
        ).text = "false"
        ET.SubElement(
            controller,
            "stringProp",
            {"name": "LoopController.loops"},
        ).text = str(count)

        return controller

    def _create_while_controller(
        self,
        name: str,
        condition: str,
        max_iterations: int,
    ) -> ET.Element:
        """Create WhileController element for condition-based loops.

        Args:
            name: Display name for the controller
            condition: JSONPath condition (e.g., "$.status != 'finished'")
            max_iterations: Safety limit to prevent infinite loops

        Returns:
            WhileController XML Element
        """
        controller = ET.Element(
            "WhileController",
            {
                "guiclass": "WhileControllerGui",
                "testclass": "WhileController",
                "testname": name,
                "enabled": "true",
            },
        )

        # Convert JSONPath condition to Groovy expression
        groovy_condition = self._convert_condition_to_groovy(condition, max_iterations)

        ET.SubElement(
            controller,
            "stringProp",
            {"name": "WhileController.condition"},
        ).text = groovy_condition

        return controller

    def _convert_condition_to_groovy(self, condition: str, max_iterations: int) -> str:
        """Convert JSONPath condition to Groovy expression for JMeter.

        Args:
            condition: JSONPath condition (e.g., "$.status != 'finished'")
            max_iterations: Safety limit for loop iterations

        Returns:
            Groovy expression string for JMeter WhileController
        """
        # Extract field name from JSONPath ($.status -> status)
        match = JSONPATH_FIELD_PATTERN.search(condition)
        if not match:
            # Fallback: use counter limit only
            return f'${{__groovy(vars.getIteration() <= {max_iterations})}}'

        var_name = match.group(1)

        # Parse operator and value
        # Supported patterns: $.field != 'value', $.field == 'value'
        # $.field != "value", $.field == "value"
        operators = ["!=", "==", "<", ">", "<=", ">="]
        operator = None
        value = None

        for op in operators:
            if op in condition:
                operator = op
                # Extract value after operator
                after_op = condition.split(op, 1)[1].strip()
                # Remove quotes from string values
                if after_op.startswith(("'", '"')):
                    value = after_op.strip("'\"")
                else:
                    value = after_op
                break

        if operator and value:
            # Build Groovy condition with counter safety limit
            # vars.get() returns String, so compare with string value
            # Use iteration counter for safety limit
            return (
                f'${{__groovy('
                f'vars.get("{var_name}") {operator} "{value}" '
                f'&& vars.getIteration() <= {max_iterations}'
                f')}}'
            )
        else:
            # Fallback: just use counter limit
            return f'${{__groovy(vars.getIteration() <= {max_iterations})}}'

    def _create_constant_timer(self, delay_ms: int) -> ET.Element:
        """Create ConstantTimer element for delays between loop iterations.

        Args:
            delay_ms: Delay in milliseconds

        Returns:
            ConstantTimer XML Element
        """
        timer = ET.Element(
            "ConstantTimer",
            {
                "guiclass": "ConstantTimerGui",
                "testclass": "ConstantTimer",
                "testname": "Loop Interval",
                "enabled": "true",
            },
        )
        ET.SubElement(
            timer,
            "stringProp",
            {"name": "ConstantTimer.delay"},
        ).text = str(delay_ms)

        return timer

    def _create_condition_extractor(self, condition: str) -> Optional[ET.Element]:
        """Create JSONPostProcessor to extract variable used in while condition.

        Args:
            condition: JSONPath condition (e.g., "$.status != 'finished'")

        Returns:
            JSONPostProcessor Element or None if no variable found
        """
        # Extract field name from JSONPath
        match = JSONPATH_FIELD_PATTERN.search(condition)
        if not match:
            return None

        var_name = match.group(1)
        jsonpath = f"$.{var_name}"

        extractor = ET.Element(
            "JSONPostProcessor",
            {
                "guiclass": "JSONPostProcessorGui",
                "testclass": "JSONPostProcessor",
                "testname": f"Extract {var_name} for condition",
                "enabled": "true",
            },
        )

        ET.SubElement(
            extractor,
            "stringProp",
            {"name": "JSONPostProcessor.referenceNames"},
        ).text = var_name

        ET.SubElement(
            extractor,
            "stringProp",
            {"name": "JSONPostProcessor.jsonPathExprs"},
        ).text = jsonpath

        ET.SubElement(
            extractor,
            "stringProp",
            {"name": "JSONPostProcessor.match_numbers"},
        ).text = "1"

        ET.SubElement(
            extractor,
            "stringProp",
            {"name": "JSONPostProcessor.defaultValues"},
        ).text = "NOT_FOUND"

        return extractor
