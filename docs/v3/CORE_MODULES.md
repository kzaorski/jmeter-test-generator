# v3 Core Modules Specification

## Overview

This document specifies the new core module introduced in v3 for interactive scenario creation.

---

## 1. ScenarioWizard

**File**: `jmeter_gen/core/scenario_wizard.py`

### Purpose

Interactive wizard that guides users through creating `pt_scenario.yaml` files step by step. Provides endpoint selection, auto-capture suggestions, and special functions (loop, think time).

### Class Definition

```python
class ScenarioWizard:
    """Interactive wizard for creating pt_scenario.yaml."""

    def __init__(self, openapi_parser: OpenAPIParser):
        """Initialize wizard with OpenAPI parser.

        Args:
            openapi_parser: Parser with loaded OpenAPI spec for endpoint data
        """

    def run(self) -> dict:
        """Run interactive wizard, return scenario dict.

        Returns:
            Complete scenario dict ready for YAML serialization

        Flow:
            1. Prompt for metadata (name, description)
            2. Prompt for settings (threads, rampup, duration)
            3. Loop: prompt for action until "Done"
            4. Return scenario dict
        """

    def _prompt_metadata(self) -> dict:
        """Prompt for scenario name and description.

        Returns:
            Dict with 'name' and 'description' keys
        """

    def _prompt_settings(self) -> dict:
        """Prompt for test settings.

        Returns:
            Dict with 'threads', 'rampup', 'duration', 'base_url' keys
        """

    def _prompt_action(self) -> str:
        """Prompt user to select action.

        Returns:
            One of: "add_endpoint", "add_loop", "add_think_time", "done"
        """

    def _prompt_endpoint(self) -> dict:
        """Show endpoint list, return selected endpoint step.

        Displays endpoints sorted by:
        - Suggested first (endpoints using captured variables)
        - Then alphabetically by operationId

        Returns:
            Step dict with 'name', 'endpoint', 'capture', 'assert'
        """

    def _prompt_step_name(self, endpoint: dict) -> str:
        """Prompt for step name with smart default.

        Default: PascalCase from operationId or path
        Example: "createUser" -> "Create User"
        """

    def _suggest_captures(self, endpoint: dict) -> list[dict]:
        """Analyze response schema, suggest capture fields.

        Analyzes OpenAPI response schema for:
        - Fields ending with 'id', 'Id', 'ID'
        - Fields named 'token', 'accessToken', 'refreshToken'
        - Fields named 'key', 'apiKey'

        Returns:
            List of dicts with 'field', 'variable', 'selected' keys
        """

    def _prompt_captures(self, suggestions: list[dict]) -> list[str]:
        """Let user select which fields to capture.

        Shows checkbox list with pre-selected suggestions.

        Returns:
            List of capture configurations
        """

    def _prompt_assertions(self, endpoint: dict) -> dict:
        """Prompt for response assertions.

        Default status based on method:
        - POST: 201
        - DELETE: 200 or 204
        - Others: 200

        Returns:
            Assert config dict
        """

    def _prompt_loop(self) -> dict:
        """Prompt for loop configuration.

        Options:
        - Fixed count: count + interval
        - While condition: condition + max_iterations + interval

        Returns:
            Loop step dict with nested endpoint
        """

    def _prompt_think_time(self) -> dict:
        """Prompt for think time in milliseconds.

        Returns:
            Think time step dict: {'think_time': ms}
        """

    def _detect_variable_usage(self, path: str) -> list[str]:
        """Find which captured vars could be used in path params.

        Analyzes path parameters (e.g., {userId}) and matches
        against captured variables.

        Returns:
            List of variable names that match path parameters
        """

    def _prompt_path_params(self, path: str, endpoint: dict) -> dict:
        """Prompt for path parameter values when no captured variable matches.

        Called when endpoint has path params (e.g., {id}) but no captured
        variable matches. User can:
        - Enter static value (e.g., "123")
        - Enter variable reference (e.g., "${userId}")

        Args:
            path: URL path with parameters (e.g., "/users/{id}")
            endpoint: Endpoint data for context

        Returns:
            Dict mapping param names to values, e.g.:
            {"id": "123"} or {"id": "${userId}"}

        Example flow:
            Path "/users/{id}" with no captured 'id' or 'userId':
            ? Value for {id}: 123
            -> Returns {"id": "123"}

            Path "/users/{id}" with captured 'userId':
            -> Auto-substitutes to "/users/${userId}", no prompt
        """

    def _prompt_headers(self, endpoint: dict) -> dict:
        """Prompt for custom headers including Authorization.

        Checks if captured variables include tokens (accessToken, token, etc.)
        and suggests using them for Authorization header.

        Returns:
            Dict of header name -> value

        Example flow:
            If 'accessToken' was captured in previous step:
            ? Add Authorization header using ${accessToken}? [Y/n]: Y
            -> Returns {"Authorization": "Bearer ${accessToken}"}
        """

    def _render_preview(self) -> None:
        """Show current scenario state in terminal.

        Displays:
        - Numbered list of steps
        - Variable captures for each step
        - Variable usage indicators
        """

    def _to_yaml(self, scenario: dict) -> str:
        """Convert scenario dict to YAML string.

        Uses PyYAML with:
        - Default flow style: False (block style)
        - Sort keys: False (preserve order)
        - Allow unicode: True
        """

    def save(self, scenario: dict, output_path: str) -> None:
        """Save scenario to YAML file.

        Args:
            scenario: Complete scenario dict
            output_path: Path to save file
        """
```

### Data Structures

```python
@dataclass
class WizardState:
    """Internal state during wizard execution."""

    name: str = ""
    description: str = ""
    settings: dict = field(default_factory=dict)
    steps: list[dict] = field(default_factory=list)
    captured_vars: set[str] = field(default_factory=set)


@dataclass
class EndpointOption:
    """Endpoint option for selection list."""

    display: str          # "POST /users (createUser)"
    method: str           # "POST"
    path: str             # "/users"
    operation_id: str     # "createUser"
    uses_vars: list[str]  # Variables this endpoint could use
    suggested: bool       # True if endpoint uses captured vars
```

### Prompt Library Integration

Using `questionary` library for interactive prompts:

```python
import questionary
from questionary import Style

# Custom style for consistent look
WIZARD_STYLE = Style([
    ('question', 'bold'),
    ('answer', 'fg:green'),
    ('pointer', 'fg:cyan bold'),
    ('highlighted', 'fg:cyan'),
    ('selected', 'fg:green'),
])

# Text input with default
name = questionary.text(
    "Scenario name:",
    default="My Scenario"
).ask()

# Select from list
action = questionary.select(
    "Select action:",
    choices=[
        "Add endpoint",
        "Add loop",
        "Add think time",
        "Done - save scenario"
    ]
).ask()

# Checkbox selection
captures = questionary.checkbox(
    "Select captures:",
    choices=[
        questionary.Choice("id -> ${userId}", checked=True),
        questionary.Choice("email", checked=False),
        questionary.Choice("createdAt", checked=False),
    ]
).ask()

# Confirm
confirm = questionary.confirm(
    "Save scenario?",
    default=True
).ask()
```

### Capture Suggestion Algorithm

```python
def _suggest_captures(self, endpoint: dict) -> list[dict]:
    """
    Suggestion priority:
    1. Fields ending with 'id', 'Id', 'ID' (high priority)
    2. Fields named 'token', 'accessToken', 'refreshToken'
    3. Fields named 'key', 'apiKey'

    For each suggested field:
    - Generate variable name (camelCase)
    - Pre-select if high priority (id fields)
    - Show JSONPath for reference

    Example:
    Response schema: {"id": int, "email": str, "createdAt": str}
    Suggestions:
    - {"field": "id", "variable": "userId", "selected": True}
    - {"field": "email", "variable": "email", "selected": False}
    - {"field": "createdAt", "variable": "createdAt", "selected": False}
    """
```

### Variable Name Generation

```python
def _generate_variable_name(self, field: str, endpoint: dict) -> str:
    """
    Generate variable name from field and context.

    Rules:
    1. If field is "id":
       - Use resource name + "Id" (e.g., "userId", "orderId")
       - Resource name from endpoint path or operationId
    2. If field ends with "Id":
       - Keep as-is (e.g., "customerId" -> "customerId")
    3. Other fields:
       - Use field name as-is (e.g., "email" -> "email")

    Examples:
    - POST /users, field "id" -> "userId"
    - POST /orders, field "id" -> "orderId"
    - GET /users/{id}, field "token" -> "token"
    """

def _validate_variable_name(self, name: str) -> tuple[bool, str]:
    """
    Validate variable name for JMeter/YAML compatibility.

    Rules:
    - Must start with letter or underscore
    - Can contain letters, digits, underscores
    - No spaces or special characters
    - Not empty

    Returns:
        Tuple of (is_valid, sanitized_name)

    Examples:
    - "userId" -> (True, "userId")
    - "user id" -> (False, "userId")  # sanitized
    - "123abc" -> (False, "abc")      # sanitized
    - "user-name" -> (False, "userName")  # sanitized
    """
```

---

## Known Limitations (v3.0.0)

### Loop Scope

Loops in v3.0.0 apply to a **single endpoint only**. Multi-step loops (e.g., repeat "Add to cart" -> "Checkout" 5 times) are not supported.

```yaml
# Supported: Single endpoint loop
- name: "Poll Status"
  endpoint: "GET /status"
  loop:
    count: 5

# NOT supported: Multi-step loop
# - loop:
#     count: 5
#     steps:
#       - endpoint: "POST /cart"
#       - endpoint: "POST /checkout"
```

This limitation may be addressed in a future version.

### Authorization Header

When a token variable is captured (e.g., `accessToken`, `token`), the wizard will prompt to use it as Authorization header. This is applied per-step, not globally.

For global Authorization, users should:
1. Add token to `variables:` section manually, or
2. Use HTTP Header Manager in JMeter (outside wizard scope)

---

## 2. CLI Integration

**File**: `jmeter_gen/cli.py`

### New Command Group

```python
@cli.group()
def new():
    """Create new resources."""
    pass


@new.command()
@click.option("--spec", "-s", help="Path to OpenAPI spec")
@click.option("--output", "-o", default="pt_scenario.yaml", help="Output file name")
def scenario(spec: str, output: str):
    """Interactive wizard to create pt_scenario.yaml.

    If --spec is not provided, auto-detects OpenAPI spec in current directory.

    Examples:
        jmeter-gen new scenario
        jmeter-gen new scenario --spec api/openapi.yaml
        jmeter-gen new scenario --output my_scenario.yaml
    """
    console = Console()

    # Find or load spec
    if spec:
        spec_path = spec
    else:
        analyzer = ProjectAnalyzer()
        result = analyzer.find_openapi_spec()
        if not result:
            console.print("[red]No OpenAPI spec found. Use --spec to specify path.[/red]")
            raise SystemExit(1)
        spec_path = result["path"]
        if not questionary.confirm(
            f"OpenAPI spec found: {spec_path}\nUse this spec?",
            default=True
        ).ask():
            raise SystemExit(0)

    # Parse spec
    parser = OpenAPIParser()
    spec_data = parser.parse(spec_path)

    console.print(f"\n[green]Found {len(spec_data['endpoints'])} endpoints in spec[/green]\n")

    # Run wizard
    wizard = ScenarioWizard(parser)
    scenario_dict = wizard.run()

    # Save
    wizard.save(scenario_dict, output)

    # Summary
    console.print(f"\n[green]Saved: {output}[/green]")
    console.print(f"  {len(scenario_dict['scenario'])} steps created")
    # Count captures and loops
    captures = sum(len(s.get('capture', [])) for s in scenario_dict['scenario'])
    loops = sum(1 for s in scenario_dict['scenario'] if 'loop' in s)
    console.print(f"  {captures} captures configured")
    if loops:
        console.print(f"  {loops} loop(s) configured")
```

---

## 3. Dependencies

### New Dependency

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "questionary>=2.0.0",
]
```

### Questionary Features Used

- `questionary.text()` - Text input with default value
- `questionary.select()` - Single choice from list
- `questionary.checkbox()` - Multiple choice with checkboxes
- `questionary.confirm()` - Yes/No confirmation
- `questionary.Style` - Custom styling

---

## 4. Error Handling

### User Cancellation

```python
def run(self) -> dict:
    try:
        # ... wizard flow ...
    except KeyboardInterrupt:
        self.console.print("\n[yellow]Wizard cancelled.[/yellow]")
        raise SystemExit(0)
```

### Invalid Input

```python
def _prompt_settings(self) -> dict:
    while True:
        threads = questionary.text(
            "Threads:",
            default="1",
            validate=lambda x: x.isdigit() and int(x) > 0
        ).ask()
        if threads is None:  # User cancelled
            raise KeyboardInterrupt
        return {"threads": int(threads), ...}
```

### No Endpoints in Spec

```python
if not spec_data['endpoints']:
    console.print("[red]No endpoints found in OpenAPI spec.[/red]")
    raise SystemExit(1)
```

---

## 5. Terminal Output

### Rich Integration

The wizard uses Rich for formatted output between questionary prompts:

```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Header
console.print(Panel.fit(
    "[bold]Scenario Wizard[/bold]",
    border_style="cyan"
))

# Current scenario preview
table = Table(title="Current Scenario")
table.add_column("#", style="cyan")
table.add_column("Step", style="green")
table.add_column("Endpoint")
table.add_column("Captures", style="yellow")

for i, step in enumerate(steps, 1):
    captures = ", ".join(step.get('capture', [])) or "-"
    table.add_row(
        str(i),
        step['name'],
        step['endpoint'],
        captures
    )

console.print(table)
```

### Step Dividers

```python
console.print("\n" + "-" * 40 + "\n")
console.print(f"[bold cyan]Step {step_num}:[/bold cyan]")
```
