"""Custom exceptions for JMeter Test Generator.

This module defines the exception hierarchy for the JMeter Test Generator.
All custom exceptions inherit from JMeterGenException base class.
"""


class JMeterGenException(Exception):
    """Base exception for all JMeter Generator errors.

    All custom exceptions in the JMeter Test Generator inherit from this
    base class to allow catching all tool-specific errors.
    """

    pass


class InvalidSpecException(JMeterGenException):
    """Raised when OpenAPI specification structure is invalid.

    This exception is raised when:
    - Required fields are missing (info, paths, etc.)
    - Spec structure doesn't conform to OpenAPI schema
    - Required metadata is malformed
    """

    pass


class UnsupportedVersionException(JMeterGenException):
    """Raised when OpenAPI version is not supported.

    This exception is raised when the OpenAPI version is not supported.
    Currently supports OpenAPI 3.x (3.0.0, 3.0.1, 3.0.2, 3.0.3, 3.1.0, etc.)
    and Swagger 2.0. Older versions are not supported.
    """

    pass


class JMXGenerationException(JMeterGenException):
    """Raised when JMX file generation fails.

    This exception is raised when:
    - Failed to create JMX XML structure
    - Failed to write JMX file to disk
    - Invalid configuration parameters provided
    - URL parsing fails for base_url extraction
    """

    pass


class JMXValidationException(JMeterGenException):
    """Raised when JMX validation encounters critical errors.

    This exception is raised when:
    - XML parsing fails
    - JMX file structure is critically malformed
    - Validation process encounters unrecoverable errors
    """

    pass


# Spec Comparison Exceptions


class SpecComparisonException(JMeterGenException):
    """Base exception for spec comparison errors.

    This exception is raised when specification comparison fails.
    """

    pass


class InvalidSpecFormatException(SpecComparisonException):
    """Raised when specification format is invalid for comparison.

    This exception is raised when:
    - Spec is missing required fields for comparison
    - Endpoints structure is malformed
    - Spec cannot be normalized for fingerprinting
    """

    pass


# JMX Update Exceptions


class JMXUpdateException(JMeterGenException):
    """Base exception for JMX update errors.

    This exception is raised when JMX file update fails.
    """

    pass


class JMXParseException(JMXUpdateException):
    """Raised when JMX file parsing fails.

    This exception is raised when:
    - XML is malformed
    - JMX structure is invalid
    - Required elements are missing
    """

    pass


class JMXBackupException(JMXUpdateException):
    """Raised when backup creation fails.

    This exception is raised when:
    - Cannot create backup directory
    - Cannot write backup file
    - Disk space insufficient
    """

    pass


# Snapshot Exceptions


class SnapshotException(JMeterGenException):
    """Base exception for snapshot errors.

    This exception is raised when snapshot operations fail.
    """

    pass


class SnapshotSaveException(SnapshotException):
    """Raised when snapshot save fails.

    This exception is raised when:
    - Cannot create snapshot directory
    - Cannot write snapshot file
    - Serialization fails
    """

    pass


class SnapshotLoadException(SnapshotException):
    """Raised when snapshot load fails.

    This exception is raised when:
    - Snapshot file not found
    - JSON parsing fails
    - Snapshot format invalid
    """

    pass


# Scenario Exceptions (v2)


class PtScenarioException(JMeterGenException):
    """Base exception for scenario-related errors.

    This exception is raised when scenario parsing or processing fails.
    """

    pass


class ScenarioParseException(PtScenarioException):
    """Raised when pt_scenario.yaml parsing fails.

    This exception is raised when:
    - YAML syntax is invalid
    - File cannot be read
    - Required fields are missing
    """

    pass


class ScenarioValidationException(PtScenarioException):
    """Raised when scenario validation fails.

    This exception is raised when:
    - Scenario structure is invalid
    - Step configuration is malformed
    - References are invalid
    """

    pass


class EndpointNotFoundException(PtScenarioException):
    """Raised when endpoint is not found in OpenAPI spec.

    This exception is raised when:
    - operationId does not exist in spec
    - METHOD /path combination not found
    """

    pass


class InvalidEndpointFormatException(PtScenarioException):
    """Raised when endpoint format is invalid.

    This exception is raised when:
    - Endpoint is neither valid operationId nor METHOD /path
    - HTTP method is not recognized
    - Path format is malformed
    """

    pass


class UndefinedVariableException(PtScenarioException):
    """Raised when variable is used before definition.

    This exception is raised when:
    - Variable referenced in step is not defined in variables section
    - Variable referenced before capture step that defines it
    """

    pass


class AmbiguousPathException(PtScenarioException):
    """Raised when multiple paths match a short path.

    This exception is raised when:
    - Short path matches multiple full paths in spec
    - User needs to select the correct path

    Attributes:
        short_path: The ambiguous short path
        candidates: List of matching full paths
    """

    def __init__(self, short_path: str, candidates: list[str]) -> None:
        """Initialize with short path and candidates.

        Args:
            short_path: The ambiguous path that was provided
            candidates: List of full paths that match
        """
        self.short_path = short_path
        self.candidates = candidates
        super().__init__(
            f"Ambiguous path '{short_path}' matches multiple endpoints: {candidates}"
        )


# Correlation Exceptions (v2)


class CorrelationException(PtScenarioException):
    """Base exception for correlation analysis errors.

    This exception is raised when correlation analysis fails.
    """

    pass


class SchemaNotFoundException(CorrelationException):
    """Raised when response schema cannot be found.

    This exception is raised when:
    - Endpoint has no response definition
    - Response schema is not defined
    - Schema reference cannot be resolved
    """

    pass


class FieldNotFoundException(CorrelationException):
    """Raised when capture field cannot be matched.

    This exception is raised when:
    - Capture variable name not found in response schema
    - No matching field in nested schema structure
    """

    pass
