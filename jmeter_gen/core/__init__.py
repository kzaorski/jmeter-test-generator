"""Core modules for JMeter Test Generator."""

from jmeter_gen.core.data_structures import EndpointChange, SpecDiff, UpdateResult
from jmeter_gen.core.jmx_generator import JMXGenerator
from jmeter_gen.core.jmx_updater import JMXUpdater
from jmeter_gen.core.jmx_validator import JMXValidator
from jmeter_gen.core.openapi_parser import OpenAPIParser
from jmeter_gen.core.project_analyzer import ProjectAnalyzer
from jmeter_gen.core.snapshot_manager import SnapshotManager
from jmeter_gen.core.spec_comparator import SpecComparator

# v2 Scenario modules
from jmeter_gen.core.scenario_data import (
    AssertConfig,
    CaptureConfig,
    CorrelationMapping,
    CorrelationResult,
    ParsedScenario,
    ResolvedPath,
    ScenarioSettings,
    ScenarioStep,
)
from jmeter_gen.core.ptscenario_parser import PtScenarioParser
from jmeter_gen.core.correlation_analyzer import CorrelationAnalyzer
from jmeter_gen.core.scenario_visualizer import ScenarioVisualizer
from jmeter_gen.core.scenario_jmx_generator import ScenarioJMXGenerator
from jmeter_gen.core.scenario_mermaid import (
    generate_mermaid_diagram,
    generate_text_visualization,
)

__all__ = [
    # v1 modules
    "ProjectAnalyzer",
    "OpenAPIParser",
    "JMXGenerator",
    "JMXValidator",
    "SpecComparator",
    "SnapshotManager",
    "JMXUpdater",
    "EndpointChange",
    "SpecDiff",
    "UpdateResult",
    # v2 modules
    "PtScenarioParser",
    "CorrelationAnalyzer",
    "ScenarioVisualizer",
    "ScenarioJMXGenerator",
    "generate_mermaid_diagram",
    "generate_text_visualization",
    # v2 data structures
    "ScenarioSettings",
    "CaptureConfig",
    "AssertConfig",
    "ScenarioStep",
    "ParsedScenario",
    "CorrelationMapping",
    "CorrelationResult",
    "ResolvedPath",
]
