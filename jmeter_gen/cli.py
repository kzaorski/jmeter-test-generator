"""Command-line interface for JMeter Test Generator.

This module provides a Click-based CLI for generating JMeter JMX files
from OpenAPI specifications.

Supports change detection (enabled by default), --auto-update options.
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from jmeter_gen.core.jmx_generator import JMXGenerator
from jmeter_gen.core.jmx_updater import JMXUpdater
from jmeter_gen.core.jmx_validator import JMXValidator
from jmeter_gen.core.openapi_parser import OpenAPIParser
from jmeter_gen.core.project_analyzer import ProjectAnalyzer
from jmeter_gen.core.snapshot_manager import SnapshotManager
from jmeter_gen.core.spec_comparator import SpecComparator
from jmeter_gen.exceptions import JMeterGenException

# v2 imports
from jmeter_gen.core.ptscenario_parser import PtScenarioParser
from jmeter_gen.core.correlation_analyzer import CorrelationAnalyzer
from jmeter_gen.core.scenario_visualizer import ScenarioVisualizer
from jmeter_gen.core.scenario_jmx_generator import ScenarioJMXGenerator

console = Console()


def _get_spec_status(spec_path: str) -> str:
    """Get status for a spec: New, No changes, or Changes detected.

    Args:
        spec_path: Path to the OpenAPI specification file.

    Returns:
        Status string for display.
    """
    from jmeter_gen.core.snapshot_manager import SnapshotManager
    from jmeter_gen.core.openapi_parser import OpenAPIParser
    from jmeter_gen.core.spec_comparator import SpecComparator

    spec_dir = str(Path(spec_path).parent)
    manager = SnapshotManager(spec_dir)

    snapshot_result = manager.find_snapshot_for_spec(spec_path)
    if not snapshot_result:
        return "[blue]New[/blue]"

    snapshot, _ = snapshot_result

    # Compare with current spec
    try:
        parser = OpenAPIParser()
        current_spec = parser.parse(spec_path)

        snapshot_spec_data = {
            "endpoints": snapshot.get("endpoints", []),
            "version": snapshot.get("spec", {}).get("api_version", ""),
        }

        comparator = SpecComparator()
        diff = comparator.compare(snapshot_spec_data, current_spec)

        if diff.has_changes:
            return "[yellow]Changes[/yellow]"
        else:
            return "[green]OK[/green]"
    except (OSError, ValueError):
        return "[dim]?[/dim]"


@click.group()
@click.version_option(version="2.1.1", prog_name="jmeter-gen")
def cli():
    """JMeter Test Generator - Generate JMX test plans from OpenAPI specifications.

    This tool analyzes your project for OpenAPI specs, parses them, and generates
    JMeter JMX files for performance testing.
    """
    pass


@cli.command()
@click.option(
    "--path",
    default=".",
    help="Project path to analyze (default: current directory)",
    type=click.Path(exists=True),
)
@click.option(
    "--no-detect-changes",
    is_flag=True,
    help="Disable change detection from snapshot",
)
@click.option(
    "--show-details",
    is_flag=True,
    help="Show detailed change breakdown",
)
@click.option(
    "--export-diff",
    type=click.Path(),
    help="Export diff to JSON file",
)
@click.option(
    "--jmx",
    type=click.Path(),
    help="JMX file path for snapshot lookup",
)
def analyze(
    path: str,
    no_detect_changes: bool,
    show_details: bool,
    export_diff: Optional[str],
    jmx: Optional[str],
):
    """Analyze project for OpenAPI specifications.

    Scans the specified project directory for OpenAPI specification files
    and displays information about discovered specs.

    Change detection is enabled by default. Use --no-detect-changes to disable.

    Example:
        jmeter-gen analyze
        jmeter-gen analyze --path /path/to/project
        jmeter-gen analyze --show-details
        jmeter-gen analyze --export-diff changes.json
        jmeter-gen analyze --no-detect-changes
    """
    try:
        analyzer = ProjectAnalyzer()

        console.print(f"\n[bold]Analyzing project:[/bold] {path}")

        # Use change detection unless disabled
        if not no_detect_changes:
            result = analyzer.analyze_with_change_detection(path, jmx)
        else:
            result = analyzer.analyze_project(path)

        if not result["openapi_spec_found"]:
            console.print(
                "\n[yellow]No OpenAPI specification found in the project.[/yellow]"
            )
            console.print(
                "\nSearched for common spec files: openapi.yaml, swagger.json, api.yaml, etc."
            )
            return

        # Check for multiple specs
        available_specs = result.get("available_specs", [])
        multiple_specs = result.get("multiple_specs_found", False)

        if multiple_specs:
            # Display all found specs in a table with status
            specs_table = Table(
                title=f"Found {len(available_specs)} OpenAPI Specifications",
                show_header=True,
            )
            specs_table.add_column("#", style="dim", width=3)
            specs_table.add_column("Path", style="cyan")
            specs_table.add_column("Format", style="green")
            specs_table.add_column("Status", style="yellow")

            for idx, spec in enumerate(available_specs, 1):
                # Check snapshot status for each spec
                status = _get_spec_status(spec["spec_path"])
                specs_table.add_row(
                    str(idx),
                    spec["spec_path"],
                    spec["format"],
                    status,
                )

            console.print()
            console.print(specs_table)
            console.print()
            console.print(
                "[dim]Use 'generate' command to select a spec interactively[/dim]"
            )
        else:
            # Display single spec details in a rich table
            table = Table(title="OpenAPI Specification Found", show_header=True)
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Spec File", result["spec_path"])
            table.add_row("Format", result["spec_format"])
            table.add_row("API Title", result["api_title"])
            table.add_row("Endpoints", str(result["endpoints_count"]))
            table.add_row("Suggested JMX", result["recommended_jmx_name"])

            console.print()
            console.print(table)
            console.print()

            console.print(
                f"[bold green]✓[/bold green] Found OpenAPI spec: {result['api_title']}"
            )

        # Display project status and change detection (only for single spec)
        if not multiple_specs:
            if result.get("snapshot_exists"):
                if result.get("changes_detected"):
                    console.print(
                        "[yellow]Status: Changes detected[/yellow] - "
                        "spec modified since last generation"
                    )
                    if show_details:
                        _display_change_detection_results(result, show_details)

                    # Export diff if requested
                    if export_diff and result.get("spec_diff"):
                        diff_data = result["spec_diff"].to_dict()
                        with open(export_diff, "w", encoding="utf-8") as f:
                            json.dump(diff_data, f, indent=2)
                        console.print(f"\n[dim]Diff exported to:[/dim] {export_diff}")
                else:
                    console.print(
                        "[green]Status: No changes[/green] - "
                        "spec unchanged since last generation"
                    )
            else:
                console.print(
                    "[blue]Status: New project[/blue] - "
                    "no previous generation found"
                )

        # v2: Check for scenario file
        scenario_path = analyzer.find_scenario_file(path)
        if scenario_path:
            console.print(f"\n[bold magenta]Scenario file found:[/bold magenta] {scenario_path}")
            try:
                scenario_parser = PtScenarioParser()
                scenario = scenario_parser.parse(scenario_path)
                console.print(f"  [dim]Name:[/dim] {scenario.name}")
                console.print(f"  [dim]Steps:[/dim] {len(scenario.steps)}")
                console.print(
                    f"\n[dim]Next step:[/dim] jmeter-gen generate "
                    f"[dim](will use scenario-based generation)[/dim]"
                )
            except Exception as e:
                console.print(f"  [yellow]Warning: Could not parse scenario: {e}[/yellow]")
                console.print(f"\n[dim]Next step:[/dim] jmeter-gen generate")
        else:
            console.print(f"\n[dim]Next step:[/dim] jmeter-gen generate")

    except (OSError, ValueError) as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        sys.exit(1)


def _display_change_detection_results(result: dict, show_details: bool) -> None:
    """Display change detection results with Rich formatting.

    Args:
        result: Analysis result with spec_diff.
        show_details: Whether to show detailed breakdown.
    """
    if not result.get("changes_detected"):
        console.print("\n[green]No API changes detected since last snapshot.[/green]")
        return

    diff = result["spec_diff"]
    summary = diff.summary

    # Summary panel
    summary_text = (
        f"[green]Added:[/green] {summary['added']} endpoint(s)\n"
        f"[red]Removed:[/red] {summary['removed']} endpoint(s)\n"
        f"[yellow]Modified:[/yellow] {summary['modified']} endpoint(s)"
    )
    console.print(
        Panel(summary_text, title="API Changes Detected", border_style="cyan")
    )

    if show_details:
        # Detailed table
        if diff.added_endpoints:
            console.print("\n[bold green]Added Endpoints:[/bold green]")
            for ep in diff.added_endpoints:
                console.print(f"  [green]+[/green] {ep.method} {ep.path}")

        if diff.removed_endpoints:
            console.print("\n[bold red]Removed Endpoints:[/bold red]")
            for ep in diff.removed_endpoints:
                console.print(f"  [red]-[/red] {ep.method} {ep.path}")

        if diff.modified_endpoints:
            console.print("\n[bold yellow]Modified Endpoints:[/bold yellow]")
            for ep in diff.modified_endpoints:
                console.print(f"  [yellow]~[/yellow] {ep.method} {ep.path}")
                for key, change in ep.changes.items():
                    console.print(f"      {key}: {change}")


@cli.command()
@click.option(
    "--spec",
    help="Path to OpenAPI specification file (YAML or JSON)",
    type=click.Path(exists=True),
)
@click.option(
    "--output",
    default=None,
    help="Output JMX file path. If not provided, prompts for output folder (default: current directory) and generates filename from API title",
    type=click.Path(),
)
@click.option(
    "--threads",
    default=1,
    help="Number of virtual users/threads (default: 1)",
    type=click.IntRange(min=1),
)
@click.option(
    "--rampup",
    default=0,
    help="Ramp-up period in seconds (default: 0)",
    type=click.IntRange(min=0),
)
@click.option(
    "--duration",
    default=None,
    help="Test duration in seconds (default: None for iteration-based)",
    type=click.IntRange(min=1),
)
@click.option(
    "--endpoints",
    multiple=True,
    help="Filter by operationId (can be specified multiple times)",
)
@click.option(
    "--base-url",
    help="Override base URL from spec (e.g., http://localhost:8080)",
)
@click.option(
    "--auto-update",
    is_flag=True,
    help="Auto-update JMX if changes detected (no prompt)",
)
@click.option(
    "--force-new",
    is_flag=True,
    help="Force new JMX (skip update, regenerate)",
)
@click.option(
    "--no-snapshot",
    is_flag=True,
    help="Don't save snapshot (one-time generation)",
)
def generate(
    spec: Optional[str],
    output: Optional[str],
    threads: int,
    rampup: int,
    duration: int,
    endpoints: Tuple[str, ...],
    base_url: Optional[str],
    auto_update: bool,
    force_new: bool,
    no_snapshot: bool,
):
    """Generate JMeter JMX test plan from OpenAPI specification.

    Parses the OpenAPI spec and creates a JMX file with HTTP samplers
    for each endpoint, configured with the specified load parameters.

    When --output is not provided, prompts for output folder (default: current
    directory) and generates filename from API title.

    Supports --auto-update to update existing JMX when spec changes.

    Example:
        jmeter-gen generate                           # Prompts for output folder
        jmeter-gen generate --output ./tests/api.jmx  # Skips folder prompt
        jmeter-gen generate --spec openapi.yaml --output my-test.jmx
        jmeter-gen generate --threads 50 --rampup 10 --duration 300
        jmeter-gen generate --base-url http://staging.example.com
        jmeter-gen generate --endpoints getUsers --endpoints createUser
        jmeter-gen generate --auto-update  # Update existing JMX if changes detected
        jmeter-gen generate --force-new    # Force regeneration
    """
    try:
        # Create analyzer for scenario detection (used in both paths)
        analyzer = ProjectAnalyzer()

        # If no spec provided, try to find one
        analysis = None
        if not spec:
            console.print("\n[bold]No spec file specified, searching project...[/bold]")
            analysis = analyzer.analyze_project(".")

            if not analysis["openapi_spec_found"]:
                console.print(
                    "\n[bold red]Error:[/bold red] No OpenAPI spec found in current directory."
                )
                console.print("Please specify a spec file with --spec option.")
                sys.exit(1)

            # Check for multiple specs and let user choose
            available_specs = analysis.get("available_specs", [])
            if analysis.get("multiple_specs_found") and len(available_specs) > 1:
                console.print(
                    f"\n[yellow]Found {len(available_specs)} OpenAPI specifications:[/yellow]\n"
                )
                for idx, s in enumerate(available_specs, 1):
                    marker = " [recommended]" if idx == 1 else ""
                    console.print(f"  {idx}. {s['spec_path']}{marker}")

                console.print()
                choice = console.input(
                    "Select spec number [1]: "
                ).strip()

                if choice:
                    try:
                        choice_idx = int(choice) - 1
                        if 0 <= choice_idx < len(available_specs):
                            spec = available_specs[choice_idx]["spec_path"]
                        else:
                            console.print("[yellow]Invalid choice, using recommended spec[/yellow]")
                            spec = analysis["spec_path"]
                    except ValueError:
                        console.print("[yellow]Invalid input, using recommended spec[/yellow]")
                        spec = analysis["spec_path"]
                else:
                    spec = analysis["spec_path"]
            else:
                spec = analysis["spec_path"]

            console.print(f"[green]✓[/green] Using spec: {spec}\n")

        # v2: Check for scenario file
        scenario_path = analyzer.find_scenario_file("." if not spec else str(Path(spec).parent))
        if scenario_path:
            console.print(f"[bold magenta]Scenario file found:[/bold magenta] {scenario_path}")
            console.print("[dim]Using scenario-based generation (v2)[/dim]\n")

            # Parse spec first for correlation analysis
            parser = OpenAPIParser()
            spec_data = parser.parse(spec)

            # Parse scenario
            scenario_parser = PtScenarioParser()
            scenario = scenario_parser.parse(scenario_path)

            # Run correlation analysis
            correlation_analyzer = CorrelationAnalyzer(parser)
            correlation_result = correlation_analyzer.analyze(scenario)

            # Visualize scenario
            visualizer = ScenarioVisualizer(console)
            visualizer.visualize(scenario, correlation_result)

            # Generate default output if not provided
            if not output:
                safe_name = re.sub(r'[^\w\s-]', '', scenario.name.lower())
                safe_name = re.sub(r'[\s_-]+', '-', safe_name).strip('-')
                default_filename = f"{safe_name}-scenario.jmx" if safe_name else "scenario-test.jmx"

                # Prompt for output folder
                default_folder = "."
                console.print(f"\n[bold]Output Folder Configuration[/bold]")
                console.print(f"Default folder: [cyan]{default_folder}[/cyan]")
                folder_input = console.input(
                    "\nEnter output folder (press Enter for default): "
                ).strip()
                output_folder = folder_input if folder_input else default_folder
                output = str(Path(output_folder) / default_filename)

            # Prompt for base URL if not provided
            final_base_url = base_url
            if not final_base_url:
                default_url = scenario.settings.base_url or spec_data.get("base_url", "http://localhost:8080")
                console.print(f"\n[bold]Base URL Configuration[/bold]")
                console.print(f"Default: [cyan]{default_url}[/cyan]")
                user_input = console.input("\nEnter base URL (press Enter for default): ").strip()
                final_base_url = user_input if user_input else default_url

            # Generate scenario-based JMX
            console.print(f"\n[bold]Generating scenario JMX:[/bold] {output}")
            scenario_generator = ScenarioJMXGenerator(parser)
            result = scenario_generator.generate(
                scenario=scenario,
                output_path=output,
                base_url=final_base_url,
                correlation_result=correlation_result,
            )

            if result["success"]:
                panel = Panel(
                    f"[bold green]Scenario JMX generated successfully![/bold green]\n\n"
                    f"[cyan]File:[/cyan] {result['jmx_path']}\n"
                    f"[cyan]Samplers:[/cyan] {result['samplers_created']}\n"
                    f"[cyan]Extractors:[/cyan] {result['extractors_created']}\n"
                    f"[cyan]Assertions:[/cyan] {result['assertions_created']}\n\n"
                    f"[dim]Next step: Open in JMeter GUI or run headless[/dim]",
                    title="Scenario Generation Complete",
                    border_style="green",
                )
                console.print(panel)

                if result.get("correlation_warnings"):
                    console.print("\n[yellow]Correlation warnings:[/yellow]")
                    for w in result["correlation_warnings"]:
                        console.print(f"  [yellow]![/yellow] {w}")

                if result.get("correlation_errors"):
                    console.print("\n[red]Correlation errors:[/red]")
                    for e in result["correlation_errors"]:
                        console.print(f"  [red]x[/red] {e}")
            else:
                console.print(f"\n[bold red]Error:[/bold red] Scenario JMX generation failed")
                sys.exit(1)

            return  # Exit after scenario generation

        # Parse OpenAPI spec
        console.print(f"[bold]Parsing OpenAPI specification:[/bold] {spec}")
        parser = OpenAPIParser()
        spec_data = parser.parse(spec)

        console.print(
            f"[green]✓[/green] Parsed {spec_data['title']} v{spec_data['version']}"
        )
        console.print(
            f"[dim]  Found {len(spec_data['endpoints'])} endpoint(s)[/dim]\n"
        )

        # Generate default output name if not provided
        if not output:
            # Use recommended name from analysis if available
            if analysis and analysis.get("recommended_jmx_name"):
                default_filename = analysis["recommended_jmx_name"]
            else:
                # Fallback: generate from API title
                safe_title = re.sub(r'[^\w\s-]', '', spec_data['title'].lower())
                safe_title = re.sub(r'[\s_-]+', '-', safe_title).strip('-')
                default_filename = f"{safe_title}-test.jmx" if safe_title else "test.jmx"

            # Prompt for output folder
            default_folder = "."
            console.print(f"[bold]Output Folder Configuration[/bold]")
            console.print(f"Default folder: [cyan]{default_folder}[/cyan]")
            folder_input = console.input(
                "\nEnter output folder (press Enter for default): "
            ).strip()
            output_folder = folder_input if folder_input else default_folder
            output = str(Path(output_folder) / default_filename)
            console.print()

        # Prompt for base URL if not provided via flag
        final_base_url = base_url
        if not final_base_url:
            default_url = spec_data["base_url"]
            console.print(f"[bold]Base URL Configuration[/bold]")
            console.print(f"Default from spec: [cyan]{default_url}[/cyan]")

            user_input = console.input(
                "\nEnter base URL (press Enter for default): "
            ).strip()

            final_base_url = user_input if user_input else default_url
            console.print()

        # Filter endpoints if specified
        endpoint_list = list(endpoints) if endpoints else None

        # Check for auto-update scenario
        output_path = Path(output)
        if output_path.exists() and not force_new:
            # Check if we have a snapshot and changes
            # Use spec file's parent directory for snapshot lookup
            project_path = str(Path(spec).parent.resolve())
            manager = SnapshotManager(project_path)
            snapshot = manager.load_snapshot(output)

            if snapshot and auto_update:
                # Compare and auto-update
                snapshot_spec_data = {
                    "endpoints": snapshot.get("endpoints", []),
                    "version": snapshot.get("spec", {}).get("api_version", ""),
                }
                comparator = SpecComparator()
                diff = comparator.compare(snapshot_spec_data, spec_data)

                if diff.has_changes:
                    console.print("[bold]Changes detected, updating JMX...[/bold]\n")
                    _display_change_detection_results(
                        {"changes_detected": True, "spec_diff": diff}, True
                    )

                    updater = JMXUpdater(project_path)
                    update_result = updater.update_jmx(output, diff, spec_data)

                    if update_result.success:
                        # Save new snapshot
                        if not no_snapshot:
                            manager.save_snapshot(spec, output, spec_data)

                        panel = Panel(
                            f"[bold green]✓ JMX file updated successfully![/bold green]\n\n"
                            f"[cyan]File:[/cyan] {output}\n"
                            f"[cyan]Added:[/cyan] {update_result.changes_applied['added']}\n"
                            f"[cyan]Disabled:[/cyan] {update_result.changes_applied['disabled']}\n"
                            f"[cyan]Updated:[/cyan] {update_result.changes_applied['updated']}\n"
                            f"[cyan]Backup:[/cyan] {update_result.backup_path}",
                            title="Update Complete",
                            border_style="green",
                        )
                        console.print(panel)
                        return
                    else:
                        console.print(
                            "[yellow]Update failed, falling back to regeneration...[/yellow]\n"
                        )
                else:
                    console.print(
                        "[green]No changes detected, JMX is up to date.[/green]\n"
                    )
                    return

        # Generate JMX
        console.print(f"[bold]Generating JMX file:[/bold] {output}")
        console.print(f"[dim]  Threads: {threads}[/dim]")
        console.print(f"[dim]  Ramp-up: {rampup}s[/dim]")
        if duration is not None:
            console.print(f"[dim]  Duration: {duration}s[/dim]")
        else:
            console.print(f"[dim]  Iterations: 1 (duration-based disabled)[/dim]")
        console.print(f"[dim]  Base URL: {final_base_url}[/dim]\n")

        generator = JMXGenerator()
        result = generator.generate(
            spec_data=spec_data,
            output_path=output,
            base_url=final_base_url,
            endpoints=endpoint_list,
            threads=threads,
            rampup=rampup,
            duration=duration,
        )

        if result["success"]:
            # Save snapshot unless --no-snapshot
            if not no_snapshot:
                try:
                    # Use spec file's parent directory for snapshot storage
                    project_path = str(Path(spec).parent.resolve())
                    manager = SnapshotManager(project_path)
                    snapshot_path = manager.save_snapshot(spec, output, spec_data)
                    console.print(f"[dim]Snapshot saved: {snapshot_path}[/dim]\n")
                except (OSError, PermissionError) as e:
                    console.print(f"[dim]Warning: Could not save snapshot: {e}[/dim]\n")

            # Display success panel
            if result['duration'] is not None:
                config_str = f"{result['threads']} threads, {result['rampup']}s ramp-up, {result['duration']}s duration"
            else:
                config_str = f"{result['threads']} threads, {result['rampup']}s ramp-up, 1 iteration"

            panel = Panel(
                f"[bold green]✓ JMX file generated successfully![/bold green]\n\n"
                f"[cyan]File:[/cyan] {result['jmx_path']}\n"
                f"[cyan]Samplers:[/cyan] {result['samplers_created']}\n"
                f"[cyan]Assertions:[/cyan] {result['assertions_added']}\n"
                f"[cyan]Configuration:[/cyan] {config_str}\n\n"
                f"[dim]Next step: Open in JMeter GUI or run headless[/dim]",
                title="Generation Complete",
                border_style="green",
            )
            console.print(panel)
        else:
            console.print(
                f"\n[bold red]Error:[/bold red] JMX generation failed"
            )
            sys.exit(1)

    except JMeterGenException as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("jmx_path", type=click.Path(exists=True))
def validate(jmx_path: str):
    """Validate JMX test plan structure and configuration.

    Checks the JMX file for required elements, valid configuration,
    and provides recommendations for improvements.

    Example:
        jmeter-gen validate test.jmx
        jmeter-gen validate /path/to/performance-test.jmx
    """
    try:
        console.print(f"\n[bold]Validating JMX file:[/bold] {jmx_path}\n")

        validator = JMXValidator()
        result = validator.validate(jmx_path)

        if result["valid"]:
            console.print(
                Panel(
                    "[bold green]✓ JMX file is valid![/bold green]",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold red]✗ JMX file has {len(result['issues'])} issue(s)[/bold red]",
                    border_style="red",
                )
            )

            # Display issues
            if result["issues"]:
                console.print("\n[bold red]Issues Found:[/bold red]")
                for i, issue in enumerate(result["issues"], 1):
                    console.print(f"  {i}. {issue}")

        # Display recommendations
        if result["recommendations"]:
            console.print(f"\n[bold yellow]Recommendations:[/bold yellow]")
            for i, rec in enumerate(result["recommendations"], 1):
                console.print(f"  {i}. {rec}")

        console.print()

        if not result["valid"]:
            sys.exit(1)

    except FileNotFoundError:
        console.print(f"\n[bold red]Error:[/bold red] File not found: {jmx_path}")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
def mcp():
    """Start MCP Server mode for GitHub Copilot integration.

    Launches the MCP (Model Context Protocol) server that allows
    GitHub Copilot and other AI assistants to generate JMeter tests.

    Example:
        jmeter-gen mcp
    """
    try:
        from jmeter_gen.mcp_server import run_server

        console.print(
            Panel(
                "[bold green]Starting MCP Server...[/bold green]\n\n"
                "The server is now running and ready to accept connections.\n"
                "Use this with GitHub Copilot or other MCP clients.\n\n"
                "[dim]Press Ctrl+C to stop the server[/dim]",
                title="MCP Server",
                border_style="green",
            )
        )

        run_server()

    except KeyboardInterrupt:
        console.print("\n[yellow]MCP Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Error starting MCP server:[/bold red] {e}")
        sys.exit(1)


def main():
    """Entry point for CLI application."""
    cli()


if __name__ == "__main__":
    main()
