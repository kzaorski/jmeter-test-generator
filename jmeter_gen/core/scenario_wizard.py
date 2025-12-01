"""Interactive wizard for creating pt_scenario.yaml files.

This module provides a step-by-step wizard that guides users through
creating scenario files with endpoint selection, capture suggestions,
and special functions (loop, think time).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import questionary
import yaml
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from jmeter_gen.core.openapi_parser import OpenAPIParser


# Custom style for consistent look
WIZARD_STYLE = Style([
    ("question", "bold"),
    ("answer", "fg:green"),
    ("pointer", "fg:cyan bold"),
    ("highlighted", "fg:cyan"),
    ("selected", "fg:green"),
])


@dataclass
class WizardState:
    """Internal state during wizard execution."""

    name: str = ""
    description: str = ""
    settings: dict = field(default_factory=dict)
    steps: list[dict] = field(default_factory=list)
    captured_vars: set[str] = field(default_factory=set)
    token_vars: set[str] = field(default_factory=set)  # Track token variables


@dataclass
class EndpointOption:
    """Endpoint option for selection list."""

    display: str  # "POST /users (createUser)"
    method: str  # "POST"
    path: str  # "/users"
    operation_id: str  # "createUser"
    uses_vars: list[str] = field(default_factory=list)  # Variables this endpoint could use
    suggested: bool = False  # True if endpoint uses captured vars


class ScenarioWizard:
    """Interactive wizard for creating pt_scenario.yaml."""

    # Fields that suggest token/auth usage
    TOKEN_FIELDS = {"token", "accesstoken", "access_token", "refreshtoken", "refresh_token",
                    "authtoken", "auth_token", "bearer", "jwt", "apikey", "api_key"}

    # Fields that suggest ID capture
    ID_SUFFIXES = ("id", "Id", "ID", "_id")

    def __init__(self, openapi_parser: OpenAPIParser, spec_data: Optional[dict] = None):
        """Initialize wizard with OpenAPI parser.

        Args:
            openapi_parser: Parser with loaded OpenAPI spec for endpoint data
            spec_data: Parsed spec data (if already parsed)
        """
        self.parser = openapi_parser
        self.console = Console()
        self.state = WizardState()
        self._endpoints: list[dict] = []
        self._spec_data = spec_data

    def run(self) -> dict:
        """Run interactive wizard, return scenario dict.

        Returns:
            Complete scenario dict ready for YAML serialization

        Raises:
            KeyboardInterrupt: If user cancels the wizard
        """
        try:
            self.console.print(Panel.fit(
                "[bold]Scenario Wizard[/bold]",
                border_style="cyan"
            ))
            self.console.print()

            # Load endpoints from spec data
            if not self._spec_data:
                raise ValueError("Spec data not provided. Call parser.parse() first.")
            self._endpoints = self._spec_data.get("endpoints", [])

            if not self._endpoints:
                self.console.print("[red]No endpoints found in OpenAPI spec.[/red]")
                raise SystemExit(1)

            # Show endpoint list
            self._print_endpoint_list()

            # Step 1: Metadata
            metadata = self._prompt_metadata()
            self.state.name = metadata["name"]
            self.state.description = metadata.get("description", "")

            # Step 2: Settings
            self.state.settings = self._prompt_settings()

            # Step 3: Build scenario steps
            step_num = 1
            while True:
                self.console.print("\n" + "-" * 40)
                self.console.print(f"\n[bold cyan]Step {step_num}:[/bold cyan]")

                action = self._prompt_action()

                if action == "done":
                    if not self.state.steps:
                        self.console.print("[yellow]No steps added. Add at least one step.[/yellow]")
                        continue
                    break

                if action == "add_endpoint":
                    step = self._prompt_endpoint()
                    if step:
                        self.state.steps.append(step)
                        step_num += 1
                elif action == "add_loop":
                    step = self._prompt_loop()
                    if step:
                        self.state.steps.append(step)
                        step_num += 1
                elif action == "add_think_time":
                    step = self._prompt_think_time()
                    if step:
                        self.state.steps.append(step)
                        step_num += 1

                # Show preview
                self._render_preview()

            return self._build_scenario_dict()

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Wizard cancelled.[/yellow]")
            raise

    def _print_endpoint_list(self) -> None:
        """Print compact list of available endpoints."""
        self.console.print(f"[dim]Available endpoints ({len(self._endpoints)}):[/dim]")

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Method", style="cyan", width=6)
        table.add_column("Path", style="white")
        table.add_column("Name", style="dim")

        for ep in self._endpoints:
            method = ep.get("method", "GET").upper()
            path = ep.get("path", "/")
            operation_id = ep.get("operationId", "")

            # Get readable display name
            display_name = self._get_readable_display_name(operation_id, path, method)

            table.add_row(method, path, display_name)

        self.console.print(table)
        self.console.print()

    def _prompt_metadata(self) -> dict:
        """Prompt for scenario name and description.

        Returns:
            Dict with 'name' and 'description' keys
        """
        name = questionary.text(
            "Scenario name:",
            default="My Test Scenario",
            style=WIZARD_STYLE,
        ).ask()

        if name is None:
            raise KeyboardInterrupt

        description = questionary.text(
            "Description (optional):",
            default="",
            style=WIZARD_STYLE,
        ).ask()

        if description is None:
            raise KeyboardInterrupt

        return {"name": name, "description": description}

    def _prompt_settings(self) -> dict:
        """Prompt for test settings.

        Returns:
            Dict with 'threads', 'rampup', 'loops', 'duration', 'base_url' keys
        """
        self.console.print("\n[bold]Settings:[/bold]")

        threads = self._prompt_positive_int("Threads", default=1)
        rampup = self._prompt_non_negative_int("Ramp-up (seconds)", default=0)

        # Test mode: fixed iterations vs time-based
        test_mode = questionary.select(
            "Test mode:",
            choices=[
                "Fixed iterations (run N times)",
                "Time-based (run for duration)",
            ],
            style=WIZARD_STYLE,
        ).ask()

        if test_mode is None:
            raise KeyboardInterrupt

        settings: dict = {
            "threads": threads,
            "rampup": rampup,
        }

        if "Fixed iterations" in test_mode:
            loops = self._prompt_positive_int("Number of iterations (loops)", default=1)
            settings["loops"] = loops
        else:
            duration = self._prompt_positive_int("Duration (seconds)", default=60)
            settings["duration"] = duration

        base_url = questionary.text(
            "Base URL override (empty to use from spec):",
            default="",
            style=WIZARD_STYLE,
        ).ask()

        if base_url is None:
            raise KeyboardInterrupt

        if base_url.strip():
            settings["base_url"] = base_url.strip()

        return settings

    def _prompt_positive_int(self, label: str, default: int) -> int:
        """Prompt for a positive integer with validation."""
        while True:
            value = questionary.text(
                f"{label}:",
                default=str(default),
                style=WIZARD_STYLE,
            ).ask()

            if value is None:
                raise KeyboardInterrupt

            try:
                num = int(value)
                if num > 0:
                    return num
                self.console.print("[yellow]Must be a positive number[/yellow]")
            except ValueError:
                self.console.print("[yellow]Invalid number[/yellow]")

    def _prompt_non_negative_int(self, label: str, default: int) -> int:
        """Prompt for a non-negative integer with validation."""
        while True:
            value = questionary.text(
                f"{label}:",
                default=str(default),
                style=WIZARD_STYLE,
            ).ask()

            if value is None:
                raise KeyboardInterrupt

            try:
                num = int(value)
                if num >= 0:
                    return num
                self.console.print("[yellow]Must be a non-negative number[/yellow]")
            except ValueError:
                self.console.print("[yellow]Invalid number[/yellow]")

    def _prompt_action(self) -> str:
        """Prompt user to select action.

        Returns:
            One of: "add_endpoint", "add_loop", "add_think_time", "done"
        """
        choices = [
            "Add endpoint",
            "Add loop",
            "Add think time",
            "Done - save scenario",
        ]

        action = questionary.select(
            "Select action:",
            choices=choices,
            style=WIZARD_STYLE,
        ).ask()

        if action is None:
            raise KeyboardInterrupt

        action_map = {
            "Add endpoint": "add_endpoint",
            "Add loop": "add_loop",
            "Add think time": "add_think_time",
            "Done - save scenario": "done",
        }

        return action_map[action]

    def _prompt_endpoint(self) -> Optional[dict]:
        """Show endpoint list, return selected endpoint step.

        Returns:
            Step dict with 'name', 'endpoint', 'capture', 'assert'
        """
        # Build endpoint options
        options = self._build_endpoint_options()

        # Sort: suggested first, then alphabetically
        options.sort(key=lambda x: (not x.suggested, x.display.lower()))

        # Build choices with suggestions marked
        choices = []
        for opt in options:
            display = opt.display
            if opt.suggested:
                display += f"  [uses: {', '.join(opt.uses_vars)}]"
            choices.append(display)

        selected = questionary.select(
            "Select endpoint:",
            choices=choices,
            style=WIZARD_STYLE,
        ).ask()

        if selected is None:
            raise KeyboardInterrupt

        # Find selected option
        selected_clean = selected.split("  [uses:")[0]  # Remove suggestion marker
        selected_opt = next(opt for opt in options if opt.display == selected_clean)

        # Get endpoint data
        endpoint_data = self._get_endpoint_data(selected_opt.method, selected_opt.path)

        # Prompt for step name
        step_name = self._prompt_step_name(endpoint_data)

        # Build endpoint string
        endpoint_str = f"{selected_opt.method} {selected_opt.path}"

        # Check for path parameters that need values
        params = self._prompt_path_params(selected_opt.path, endpoint_data)

        # Suggest captures
        captures = self._prompt_captures_for_endpoint(endpoint_data)

        # Prompt for assertions
        assertions = self._prompt_assertions(endpoint_data)

        # Prompt for headers (including Authorization)
        headers = self._prompt_headers(endpoint_data)

        # Build step dict
        step: dict[str, Any] = {
            "name": step_name,
            "endpoint": endpoint_str,
        }

        if params:
            step["params"] = params

        if headers:
            step["headers"] = headers

        if captures:
            step["capture"] = captures
            # Track captured variables
            for cap in captures:
                if isinstance(cap, str):
                    self.state.captured_vars.add(cap)
                elif isinstance(cap, dict):
                    for var_name in cap.keys():
                        self.state.captured_vars.add(var_name)
                        # Track token variables
                        if var_name.lower() in self.TOKEN_FIELDS:
                            self.state.token_vars.add(var_name)

        if assertions:
            step["assert"] = assertions

        return step

    def _is_ugly_operation_id(self, operation_id: str, method: str) -> bool:
        """Check if operationId looks like auto-generated garbage.

        FastAPI and similar frameworks auto-generate operationIds by concatenating
        method + path without separators when no explicit operationId is provided.

        Criteria for "ugly" operationId:
        - Contains version patterns like _1.0_ or _v1_ (strong signal of path-based)
        - Has too many segments (more than 5 underscores/hyphens)
        - Starts with method prefix AND very long (>35 chars)
        - No separators, starts with method, and longer than 20 chars (FastAPI style)

        Args:
            operation_id: The operationId from spec
            method: HTTP method (GET, POST, etc.)

        Returns:
            True if operationId looks auto-generated and ugly
        """
        # Short names are always OK
        if len(operation_id) <= 20:
            return False

        # Has camelCase = likely intentional = OK
        if not operation_id.islower():
            return False

        method_lower = method.lower()

        # Contains version patterns like _1.0_ or _v1_ = definitely path-based
        if re.search(r"_v?\d+\.?\d*_", operation_id):
            return True

        # Too many segments (>5 underscores or hyphens) = path-based
        segment_count = operation_id.count("_") + operation_id.count("-")
        if segment_count > 5:
            return True

        # Starts with method prefix AND very long = likely path-based
        if operation_id.startswith(f"{method_lower}_") and len(operation_id) > 35:
            return True

        # No separators, starts with method = FastAPI style (no explicit operationId)
        if "_" not in operation_id and "-" not in operation_id:
            if operation_id.startswith(method_lower):
                return True

        return False

    def _create_name_from_path(self, path: str, method: str) -> str:
        """Create readable name from path's last segment.

        Extracts the last non-parameter segment from the path and converts it
        to PascalCase for better readability.

        Args:
            path: The endpoint path (e.g., "/api/v1/validate_module_db")
            method: HTTP method as fallback

        Returns:
            PascalCase name (e.g., "ValidateModuleDb")

        Example:
            /api/v1/validate_module_db -> ValidateModuleDb
            /users/{id}/items -> Items
            /health-check -> HealthCheck
        """
        # Get last non-parameter segment
        segments = [s for s in path.split("/") if s and not s.startswith("{")]
        if not segments:
            return f"{method.upper()}_request"

        last_segment = segments[-1]
        # Convert snake_case or kebab-case to PascalCase
        words = last_segment.replace("-", "_").split("_")
        pascal_case = "".join(word.capitalize() for word in words if word)

        return pascal_case or f"{method.upper()}_request"

    def _get_readable_display_name(
        self, operation_id: str, path: str, method: str
    ) -> str:
        """Get a readable display name, fixing ugly auto-generated operationIds.

        If the operationId looks like auto-generated garbage (e.g.,
        "postserviceagenttestcasesgenapi10validatemoduledb"), this method
        creates a better name from the path's last segment.

        Args:
            operation_id: The operationId from spec
            path: The endpoint path
            method: HTTP method

        Returns:
            A readable name for display
        """
        if self._is_ugly_operation_id(operation_id, method):
            return self._create_name_from_path(path, method)
        return operation_id

    def _build_endpoint_options(self) -> list[EndpointOption]:
        """Build list of endpoint options for selection."""
        options = []

        for ep in self._endpoints:
            method = ep.get("method", "GET").upper()
            path = ep.get("path", "/")
            operation_id = ep.get("operationId", "")

            # Get readable display name (fix ugly auto-generated operationIds)
            display_name = self._get_readable_display_name(operation_id, path, method)

            # Format display
            if display_name:
                display = f"{method} {path} ({display_name})"
            else:
                display = f"{method} {path}"

            # Check which captured vars this endpoint could use
            uses_vars = self._detect_variable_usage(path)

            opt = EndpointOption(
                display=display,
                method=method,
                path=path,
                operation_id=operation_id,
                uses_vars=uses_vars,
                suggested=len(uses_vars) > 0,
            )
            options.append(opt)

        return options

    def _get_endpoint_data(self, method: str, path: str) -> dict:
        """Get endpoint data by method and path."""
        for ep in self._endpoints:
            if ep.get("method", "").upper() == method and ep.get("path", "") == path:
                return ep
        return {}

    def _prompt_step_name(self, endpoint: dict) -> str:
        """Prompt for step name with smart default."""
        # Generate default from operationId or path
        operation_id = endpoint.get("operationId", "")
        path = endpoint.get("path", "/")
        method = endpoint.get("method", "GET").upper()

        # Get readable name (fix ugly auto-generated operationIds)
        readable_name = self._get_readable_display_name(operation_id, path, method)

        if readable_name:
            # Convert camelCase/PascalCase to Title Case with spaces
            default_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', readable_name)
            default_name = default_name.replace("_", " ").title()
        else:
            # Generate from path
            parts = [p for p in path.split("/") if p and not p.startswith("{")]
            if parts:
                default_name = f"{method.title()} {parts[-1].title()}"
            else:
                default_name = f"{method.title()} Request"

        name = questionary.text(
            f"Step name [{default_name}]:",
            default=default_name,
            style=WIZARD_STYLE,
        ).ask()

        if name is None:
            raise KeyboardInterrupt

        return name or default_name

    def _detect_variable_usage(self, path: str) -> list[str]:
        """Find which captured vars could be used in path params."""
        # Extract path parameters like {userId}
        params = re.findall(r'\{(\w+)\}', path)

        used_vars = []
        for param in params:
            # Check if we have a captured var that matches
            for var in self.state.captured_vars:
                # Match: userId matches {userId} or {id}
                if var.lower() == param.lower():
                    used_vars.append(var)
                elif param.lower() == "id" and var.lower().endswith("id"):
                    used_vars.append(var)

        return used_vars

    def _prompt_path_params(self, path: str, endpoint: dict) -> dict:
        """Prompt for path parameter values when no captured variable matches."""
        # Extract path parameters
        params = re.findall(r'\{(\w+)\}', path)
        if not params:
            return {}

        result = {}
        for param in params:
            # Check if a captured variable matches
            matching_var = None
            for var in self.state.captured_vars:
                if var.lower() == param.lower():
                    matching_var = var
                    break
                if param.lower() == "id" and var.lower().endswith("id"):
                    matching_var = var
                    break

            if matching_var:
                # Auto-use captured variable
                result[param] = f"${{{matching_var}}}"
                self.console.print(f"[dim]Auto-using ${{{matching_var}}} for {{{param}}}[/dim]")
            else:
                # Prompt for value
                value = questionary.text(
                    f"Value for {{{param}}}:",
                    default="",
                    style=WIZARD_STYLE,
                ).ask()

                if value is None:
                    raise KeyboardInterrupt

                if value.strip():
                    result[param] = value.strip()

        return result

    def _suggest_captures(self, endpoint: dict) -> list[dict]:
        """Analyze response schema, suggest capture fields."""
        suggestions = []

        # Get response schema
        response_schema = self.parser.extract_response_schema(
            method=endpoint.get("method", "GET"),
            path=endpoint.get("path", "/"),
        )

        if not response_schema:
            return suggestions

        # Analyze schema properties
        properties = response_schema.get("properties", {})
        self._analyze_properties_for_capture(properties, "", endpoint, suggestions)

        return suggestions

    def _analyze_properties_for_capture(
        self,
        properties: dict,
        prefix: str,
        endpoint: dict,
        suggestions: list
    ) -> None:
        """Recursively analyze properties for capture suggestions."""
        for field_name, field_schema in properties.items():
            full_path = f"{prefix}.{field_name}" if prefix else field_name
            field_lower = field_name.lower()

            # Check if this is an ID field
            is_id_field = (
                field_name.endswith(self.ID_SUFFIXES) or
                field_name == "id"
            )

            # Check if this is a token field
            is_token_field = field_lower in self.TOKEN_FIELDS

            if is_id_field or is_token_field:
                var_name = self._generate_variable_name(field_name, endpoint)
                suggestions.append({
                    "field": field_name,
                    "variable": var_name,
                    "selected": is_id_field,  # Pre-select ID fields
                    "is_token": is_token_field,
                })

            # Recurse into nested objects
            if field_schema.get("type") == "object":
                nested_props = field_schema.get("properties", {})
                self._analyze_properties_for_capture(
                    nested_props, full_path, endpoint, suggestions
                )

    def _generate_variable_name(self, field: str, endpoint: dict) -> str:
        """Generate variable name from field and context."""
        if field.lower() == "id":
            # Use resource name + Id
            path = endpoint.get("path", "/")
            operation_id = endpoint.get("operationId", "")

            # Try to get resource from operationId (e.g., createUser -> user)
            if operation_id:
                # Remove common prefixes
                for prefix in ("create", "get", "update", "delete", "list", "add", "remove"):
                    if operation_id.lower().startswith(prefix):
                        resource = operation_id[len(prefix):]
                        if resource:
                            return resource[0].lower() + resource[1:] + "Id"

            # Try to get resource from path
            parts = [p for p in path.split("/") if p and not p.startswith("{")]
            if parts:
                resource = parts[-1].rstrip("s")  # Remove plural 's'
                return resource + "Id"

            return "itemId"

        # Keep as-is for other fields
        return field

    def _validate_variable_name(self, name: str) -> tuple[bool, str]:
        """Validate variable name for JMeter/YAML compatibility."""
        if not name:
            return False, "variable"

        # Sanitize: remove invalid characters
        sanitized = re.sub(r'[^\w]', '', name)

        # Must start with letter or underscore
        if sanitized and sanitized[0].isdigit():
            sanitized = sanitized.lstrip("0123456789")

        if not sanitized:
            sanitized = "variable"

        # Convert to camelCase if has spaces/hyphens
        if " " in name or "-" in name:
            parts = re.split(r'[\s\-_]+', name)
            sanitized = parts[0].lower() + "".join(p.title() for p in parts[1:])

        return name == sanitized, sanitized

    def _prompt_captures(self, suggestions: list[dict]) -> list:
        """Let user select which fields to capture."""
        captures = []

        if suggestions:
            self.console.print("\n[bold]Suggested captures from response schema:[/bold]")

            choices = []
            for sug in suggestions:
                label = f"{sug['field']} -> ${{{sug['variable']}}}"
                if sug.get('is_token'):
                    label += " (token)"
                choices.append(questionary.Choice(label, checked=sug['selected']))

            selected = questionary.checkbox(
                "Select captures:",
                choices=choices,
                style=WIZARD_STYLE,
            ).ask()

            if selected is None:
                raise KeyboardInterrupt

            # Build capture list from suggestions
            for sel in selected:
                # Parse selection to get variable and field
                parts = sel.split(" -> ")
                if len(parts) == 2:
                    field = parts[0].strip()
                    var = parts[1].replace("${", "").replace("}", "").split()[0]

                    # Track token variables
                    if "(token)" in sel:
                        self.state.token_vars.add(var)

                    if field == var:
                        captures.append(var)
                    else:
                        captures.append({var: field})

        # Always offer custom capture option
        captures = self._prompt_custom_captures(captures)

        return captures

    def _prompt_custom_captures(self, captures: list) -> list:
        """Prompt for custom captures with explicit JSONPath."""
        add_custom = questionary.confirm(
            "Add custom capture?",
            default=False,
            style=WIZARD_STYLE,
        ).ask()

        if add_custom is None:
            raise KeyboardInterrupt

        while add_custom:
            var_name = questionary.text(
                "Variable name (e.g., status):",
                style=WIZARD_STYLE,
            ).ask()

            if var_name is None:
                raise KeyboardInterrupt

            if not var_name.strip():
                self.console.print("[yellow]Variable name cannot be empty.[/yellow]")
                continue

            var_name = var_name.strip()

            jsonpath = questionary.text(
                "JSONPath (e.g., $.status):",
                default=f"$.{var_name}",
                style=WIZARD_STYLE,
            ).ask()

            if jsonpath is None:
                raise KeyboardInterrupt

            # Add as explicit JSONPath capture
            captures.append({var_name: {"path": jsonpath}})
            self.state.captured_vars.add(var_name)

            add_custom = questionary.confirm(
                "Add another custom capture?",
                default=False,
                style=WIZARD_STYLE,
            ).ask()

            if add_custom is None:
                raise KeyboardInterrupt

        return captures

    def _prompt_captures_for_endpoint(self, endpoint: dict) -> list:
        """Get capture suggestions and prompt user."""
        suggestions = self._suggest_captures(endpoint)
        return self._prompt_captures(suggestions)

    def _prompt_assertions(self, endpoint: dict) -> dict:
        """Prompt for response assertions."""
        method = endpoint.get("method", "GET").upper()

        # Default status based on method
        if method == "POST":
            default_status = 201
        elif method == "DELETE":
            default_status = 200
        else:
            default_status = 200

        confirm = questionary.confirm(
            f"Add status assertion ({default_status})?",
            default=True,
            style=WIZARD_STYLE,
        ).ask()

        if confirm is None:
            raise KeyboardInterrupt

        if confirm:
            return {"status": default_status}

        return {}

    def _prompt_headers(self, endpoint: dict) -> dict:
        """Prompt for custom headers including Authorization."""
        headers = {}

        # Check if we have token variables from previous captures
        if self.state.token_vars:
            token_var = list(self.state.token_vars)[0]  # Use first available token

            confirm = questionary.confirm(
                f"Add Authorization header using ${{{token_var}}}?",
                default=True,
                style=WIZARD_STYLE,
            ).ask()

            if confirm is None:
                raise KeyboardInterrupt

            if confirm:
                headers["Authorization"] = f"Bearer ${{{token_var}}}"

        return headers

    def _prompt_loop(self) -> Optional[dict]:
        """Prompt for loop configuration."""
        # Ask for single vs multi-step loop
        loop_mode = questionary.select(
            "Loop mode:",
            choices=["Single endpoint", "Multiple steps"],
            style=WIZARD_STYLE,
        ).ask()

        if loop_mode is None:
            raise KeyboardInterrupt

        loop_type = questionary.select(
            "Loop type:",
            choices=["Fixed count", "While condition"],
            style=WIZARD_STYLE,
        ).ask()

        if loop_type is None:
            raise KeyboardInterrupt

        loop_config: dict[str, Any] = {}

        if loop_type == "Fixed count":
            count = self._prompt_positive_int("Count", default=5)
            loop_config["count"] = count
        else:
            condition = questionary.text(
                "While condition (JSONPath, e.g., $.status != 'finished'):",
                style=WIZARD_STYLE,
            ).ask()

            if condition is None:
                raise KeyboardInterrupt

            loop_config["while"] = condition
            loop_config["max_iterations"] = 100

        # Interval
        interval = self._prompt_non_negative_int("Interval between iterations (ms)", default=0)
        if interval > 0:
            loop_config["interval"] = interval

        if loop_mode == "Single endpoint":
            # Original single endpoint behavior
            self.console.print("\n[bold]Select endpoint for loop:[/bold]")
            endpoint_step = self._prompt_endpoint()

            if endpoint_step:
                endpoint_step["loop"] = loop_config
                return endpoint_step
            return None
        else:
            # Multi-step loop
            return self._prompt_multi_step_loop(loop_config)

    def _prompt_multi_step_loop(self, loop_config: dict) -> Optional[dict]:
        """Prompt for multiple steps inside a loop."""
        nested_steps: list[dict] = []

        self.console.print("\n[bold]Add steps to loop (select 'Done' when finished):[/bold]")

        while True:
            action = questionary.select(
                f"Step {len(nested_steps) + 1} in loop:",
                choices=["Add endpoint", "Add think time", "Done - finish loop"],
                style=WIZARD_STYLE,
            ).ask()

            if action is None:
                raise KeyboardInterrupt

            if action == "Done - finish loop":
                if not nested_steps:
                    self.console.print("[yellow]Add at least one step to loop.[/yellow]")
                    continue
                break

            if action == "Add endpoint":
                step = self._prompt_endpoint()
                if step:
                    nested_steps.append(step)
            elif action == "Add think time":
                step = self._prompt_think_time()
                if step:
                    nested_steps.append(step)

        # Build loop block
        if loop_config.get("count"):
            loop_name = f"Loop {loop_config['count']}x"
        else:
            loop_name = "While Loop"

        return {
            "name": loop_name,
            "loop": loop_config,
            "steps": nested_steps,
        }

    def _prompt_think_time(self) -> Optional[dict]:
        """Prompt for think time in milliseconds."""
        ms = self._prompt_positive_int("Think time (ms)", default=1000)

        return {
            "name": "Think Time",
            "think_time": ms,
        }

    def _render_preview(self) -> None:
        """Show current scenario state in terminal."""
        if not self.state.steps:
            return

        self.console.print("\n[bold]Current scenario:[/bold]")

        table = Table(show_header=True)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Step", style="green")
        table.add_column("Endpoint/Action")
        table.add_column("Captures", style="yellow")

        for i, step in enumerate(self.state.steps, 1):
            name = step.get("name", "")
            captures_str = self._format_captures(step)

            if "think_time" in step and "endpoint" not in step:
                # Standalone think_time step
                endpoint = f"think_time: {step['think_time']}ms"
                table.add_row(str(i), name, endpoint, "-")
            elif "loop" in step and "steps" in step:
                # Multi-step loop block
                loop = step["loop"]
                if "count" in loop:
                    loop_label = f"(loop {loop['count']}x)"
                else:
                    loop_label = f"(while: {loop.get('while', '')})"
                table.add_row(str(i), loop_label, "", "")

                # Add nested steps with indentation
                for nested_step in step["steps"]:
                    nested_name = nested_step.get("name", "")
                    nested_captures = self._format_captures(nested_step)
                    if "think_time" in nested_step and "endpoint" not in nested_step:
                        nested_endpoint = f"think_time: {nested_step['think_time']}ms"
                        table.add_row("", f"  {nested_name}", f"  {nested_endpoint}", "-")
                    else:
                        nested_endpoint = nested_step.get("endpoint", "")
                        table.add_row("", f"  {nested_name}", f"  {nested_endpoint}", nested_captures)
            elif "loop" in step:
                # Single-step loop (endpoint with loop config)
                loop = step["loop"]
                if "count" in loop:
                    loop_label = f"(loop {loop['count']}x)"
                    loop_info = ""
                else:
                    loop_label = "(while)"
                    loop_info = loop.get("while", "")
                table.add_row(str(i), loop_label, loop_info, "")

                # Add indented endpoint row
                endpoint = step.get("endpoint", "")
                table.add_row("", f"  {name}", f"  {endpoint}", captures_str)
            else:
                # Regular step
                endpoint = step.get("endpoint", "")
                table.add_row(str(i), name, endpoint, captures_str)

        self.console.print(table)

    def _format_captures(self, step: dict) -> str:
        """Format captures list for display."""
        captures = step.get("capture", [])
        if not captures:
            return "-"

        cap_names = []
        for c in captures:
            if isinstance(c, str):
                cap_names.append(c)
            elif isinstance(c, dict):
                cap_names.extend(c.keys())
        return ", ".join(cap_names)

    def _build_scenario_dict(self) -> dict:
        """Build final scenario dictionary."""
        scenario: dict[str, Any] = {
            "version": "1.0",
            "name": self.state.name,
        }

        if self.state.description:
            scenario["description"] = self.state.description

        if self.state.settings:
            scenario["settings"] = self.state.settings

        scenario["scenario"] = self.state.steps

        return scenario

    def _to_yaml(self, scenario: dict) -> str:
        """Convert scenario dict to YAML string."""
        return yaml.dump(
            scenario,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    def save(self, scenario: dict, output_path: str) -> None:
        """Save scenario to YAML file.

        Args:
            scenario: Complete scenario dict
            output_path: Path to save file
        """
        yaml_content = self._to_yaml(scenario)
        Path(output_path).write_text(yaml_content, encoding="utf-8")
