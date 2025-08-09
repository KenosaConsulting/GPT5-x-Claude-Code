"""Enhanced CLI interface for aidev."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import AIDevConfig, create_default_config, load_config
from .logging import TokenTracker, get_logger, setup_logging
from .prompts import get_implementation_prompt, get_review_prompt, get_spec_prompt
from .providers import AnthropicProvider, OpenAIProvider
from .tools import ToolExecutor

console = Console()
logger = get_logger(__name__)


def setup_api_keys(config: AIDevConfig) -> AIDevConfig:
    """Interactive setup of API keys if not configured."""
    needs_setup = False
    
    if not config.openai_api_key:
        config.openai_api_key = click.prompt(
            "Enter your OpenAI API key",
            type=str,
            hide_input=True
        )
        needs_setup = True
    
    if not config.anthropic_api_key:
        config.anthropic_api_key = click.prompt(
            "Enter your Anthropic API key",
            type=str,
            hide_input=True
        )
        needs_setup = True
    
    if needs_setup:
        console.print("[yellow]Consider saving these keys to .env or config file[/yellow]")
    
    return config


@click.group()
@click.option('--config', '-c', type=click.Path(), help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx: click.Context, config: Optional[str], verbose: bool) -> None:
    """GPT-5 × Claude Code Terminal Orchestrator v2.0"""
    
    # Load configuration
    try:
        if config:
            # TODO: Support loading config from specific path
            aidev_config = load_config()
        else:
            aidev_config = load_config()
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        sys.exit(1)
    
    # Setup logging
    if verbose:
        aidev_config.logging.level = "DEBUG"
    
    setup_logging(aidev_config.logging)
    
    # Store in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj['config'] = aidev_config
    ctx.obj['token_tracker'] = TokenTracker()


@cli.command()
@click.argument('prompt')
@click.option('--output', '-o', default='aidev_spec.json', help='Output file for specification')
@click.pass_context
def spec(ctx: click.Context, prompt: str, output: str) -> None:
    """Generate implementation specification from natural language prompt."""
    
    config: AIDevConfig = ctx.obj['config']
    token_tracker: TokenTracker = ctx.obj['token_tracker']
    
    if not prompt.strip():
        console.print("[red]Please provide a non-empty prompt[/red]")
        sys.exit(1)
    
    try:
        # Setup API key if needed
        config = setup_api_keys(config)
        
        # Initialize OpenAI provider
        openai_provider = OpenAIProvider(config, token_tracker)
        
        console.print("[cyan]Generating specification...[/cyan]")
        
        # Generate specification
        spec_data = openai_provider.generate_spec(prompt, get_spec_prompt())
        
        # Save to file
        output_path = Path(output)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(spec_data, f, indent=2)
        
        console.print(f"[green]Specification saved to {output}[/green]")
        
        # Display summary
        display_spec_summary(spec_data)
        
        # Show token usage
        usage = token_tracker.get_summary()
        console.print(f"\n[dim]Token usage: {usage['total_tokens']} tokens (~${usage['estimated_cost_usd']})[/dim]")
    
    except Exception as e:
        logger.error(f"Error generating specification: {e}")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--spec-file', '-s', default='aidev_spec.json', help='Specification file to implement')
@click.option('--max-iterations', '-i', type=int, help='Maximum implementation iterations')
@click.option('--auto-confirm', '-y', is_flag=True, help='Skip confirmation prompts')
@click.pass_context
def implement(ctx: click.Context, spec_file: str, max_iterations: Optional[int], auto_confirm: bool) -> None:
    """Implement specification using Claude Code with tools."""
    
    config: AIDevConfig = ctx.obj['config']
    token_tracker: TokenTracker = ctx.obj['token_tracker']
    
    # Load specification
    spec_path = Path(spec_file)
    if not spec_path.exists():
        console.print(f"[red]Specification file not found: {spec_file}[/red]")
        console.print("[yellow]Run 'aidev spec \"your prompt\"' first to generate a specification[/yellow]")
        sys.exit(1)
    
    try:
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec_data = json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading specification: {e}[/red]")
        sys.exit(1)
    
    # Display implementation plan
    display_implementation_plan(spec_data)
    
    if not auto_confirm and config.require_confirmation:
        if not click.confirm("Proceed with implementation?"):
            console.print("[yellow]Implementation cancelled[/yellow]")
            return
    
    try:
        # Setup API key if needed
        config = setup_api_keys(config)
        
        # Initialize providers and tools
        anthropic_provider = AnthropicProvider(config, token_tracker)
        tool_executor = ToolExecutor(config)
        
        console.print("[cyan]Starting implementation...[/cyan]")
        
        # Implement specification
        result = anthropic_provider.implement_spec(
            spec_data,
            get_implementation_prompt(spec_data),
            tool_executor,
            max_iterations
        )
        
        if result["ok"]:
            console.print(f"[green]Implementation completed in {result['iterations']} iterations[/green]")
            console.print(result["response"])
        else:
            console.print(f"[red]Implementation failed: {result['error']}[/red]")
            if "iterations" in result:
                console.print(f"[yellow]Completed {result['iterations']} iterations before failure[/yellow]")
        
        # Show token usage
        usage = token_tracker.get_summary()
        console.print(f"\n[dim]Token usage: {usage['total_tokens']} tokens (~${usage['estimated_cost_usd']})[/dim]")
    
    except Exception as e:
        logger.error(f"Error during implementation: {e}")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--spec-file', '-s', default='aidev_spec.json', help='Specification file for context')
@click.option('--output', '-o', default='aidev_review.json', help='Output file for review')
@click.pass_context
def review(ctx: click.Context, spec_file: str, output: str) -> None:
    """Review code changes against specification using GPT-5."""
    
    config: AIDevConfig = ctx.obj['config']
    token_tracker: TokenTracker = ctx.obj['token_tracker']
    
    # Load specification
    spec_path = Path(spec_file)
    if not spec_path.exists():
        console.print(f"[red]Specification file not found: {spec_file}[/red]")
        sys.exit(1)
    
    try:
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec_data = json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading specification: {e}[/red]")
        sys.exit(1)
    
    try:
        # Setup API key if needed
        config = setup_api_keys(config)
        
        # Get git diff
        tool_executor = ToolExecutor(config)
        diff_result = tool_executor.git_diff()
        
        if not diff_result["ok"]:
            console.print(f"[red]Error getting git diff: {diff_result['error']}[/red]")
            sys.exit(1)
        
        diff_text = diff_result["diff"]
        if not diff_text.strip():
            console.print("[yellow]No changes to review[/yellow]")
            return
        
        # Initialize OpenAI provider
        openai_provider = OpenAIProvider(config, token_tracker)
        
        console.print("[cyan]Reviewing code changes...[/cyan]")
        
        # Review code
        review_data = openai_provider.review_code(diff_text, spec_data, get_review_prompt())
        
        # Save review
        output_path = Path(output)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(review_data, f, indent=2)
        
        console.print(f"[green]Review saved to {output}[/green]")
        
        # Display review summary
        display_review_summary(review_data)
        
        # Show token usage
        usage = token_tracker.get_summary()
        console.print(f"\n[dim]Token usage: {usage['total_tokens']} tokens (~${usage['estimated_cost_usd']})[/dim]")
    
    except Exception as e:
        logger.error(f"Error during code review: {e}")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--apply', is_flag=True, help='Apply the diff to git staging area')
@click.pass_context
def patch(ctx: click.Context, apply: bool) -> None:
    """Show or apply current git diff."""
    
    config: AIDevConfig = ctx.obj['config']
    
    try:
        tool_executor = ToolExecutor(config)
        diff_result = tool_executor.git_diff()
        
        if not diff_result["ok"]:
            console.print(f"[red]Error getting git diff: {diff_result['error']}[/red]")
            sys.exit(1)
        
        diff_text = diff_result["diff"]
        if not diff_text.strip():
            console.print("[yellow]No changes to show[/yellow]")
            return
        
        if apply:
            if config.require_confirmation and not click.confirm("Apply changes to git staging area?"):
                console.print("[yellow]Patch application cancelled[/yellow]")
                return
            
            apply_result = tool_executor.git_apply(diff_text)
            if apply_result["ok"]:
                console.print("[green]Changes applied to git staging area[/green]")
                console.print("[cyan]Run 'git commit -m \"your message\"' to commit changes[/cyan]")
            else:
                console.print(f"[red]Error applying patch: {apply_result['error']}[/red]")
        else:
            console.print(diff_text)
    
    except Exception as e:
        logger.error(f"Error handling patch: {e}")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--path', default='.', help='Path to create config file')
@click.pass_context
def init(ctx: click.Context, path: str) -> None:
    """Initialize aidev configuration."""
    
    config_path = Path(path) / "aidev.yaml"
    
    if config_path.exists():
        if not click.confirm(f"Configuration file {config_path} exists. Overwrite?"):
            console.print("[yellow]Initialization cancelled[/yellow]")
            return
    
    try:
        created_path = create_default_config(config_path)
        console.print(f"[green]Configuration created at {created_path}[/green]")
        console.print("[cyan]Edit the file to customize settings, then set your API keys:[/cyan]")
        console.print("  export OPENAI_API_KEY='sk-...'")
        console.print("  export ANTHROPIC_API_KEY='sk-ant-...'")
    
    except Exception as e:
        console.print(f"[red]Error creating configuration: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show aidev status and configuration."""
    
    config: AIDevConfig = ctx.obj['config']
    token_tracker: TokenTracker = ctx.obj['token_tracker']
    
    # Configuration table
    config_table = Table(title="Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    
    config_table.add_row("OpenAI Model", config.models.openai_model)
    config_table.add_row("Anthropic Model", config.models.anthropic_model)
    config_table.add_row("Target Repository", str(config.target_repo or Path.cwd()))
    config_table.add_row("Auto-detect Tools", "Yes" if config.auto_detect_tools else "No")
    config_table.add_row("Require Confirmation", "Yes" if config.require_confirmation else "No")
    config_table.add_row("Max Iterations", str(config.max_iterations))
    
    console.print(config_table)
    
    # API key status
    api_status = Table(title="API Keys")
    api_status.add_column("Provider", style="cyan")
    api_status.add_column("Status", style="green")
    
    api_status.add_row("OpenAI", "✓ Configured" if config.openai_api_key else "✗ Missing")
    api_status.add_row("Anthropic", "✓ Configured" if config.anthropic_api_key else "✗ Missing")
    
    console.print(api_status)
    
    # Check for spec file
    spec_exists = Path("aidev_spec.json").exists()
    console.print(f"\nSpecification file: {'✓ Found' if spec_exists else '✗ Not found'} (aidev_spec.json)")


def display_spec_summary(spec: Dict[str, Any]) -> None:
    """Display a summary of the generated specification."""
    
    panel_content = []
    panel_content.append(f"[bold]{spec.get('title', 'Untitled')}[/bold]")
    panel_content.append(f"\n{spec.get('summary', 'No summary provided')}")
    
    if tasks := spec.get('tasks', []):
        panel_content.append(f"\n[cyan]Tasks ({len(tasks)}):[/cyan]")
        for i, task in enumerate(tasks[:5], 1):  # Show first 5 tasks
            panel_content.append(f"  {i}. {task}")
        if len(tasks) > 5:
            panel_content.append(f"  ... and {len(tasks) - 5} more")
    
    if files := spec.get('files', {}):
        panel_content.append(f"\n[cyan]Files ({len(files)}):[/cyan]")
        for file_path in list(files.keys())[:3]:  # Show first 3 files
            panel_content.append(f"  • {file_path}")
        if len(files) > 3:
            panel_content.append(f"  ... and {len(files) - 3} more")
    
    console.print(Panel("\n".join(panel_content), title="Specification Summary", border_style="green"))


def display_implementation_plan(spec: Dict[str, Any]) -> None:
    """Display implementation plan for confirmation."""
    
    console.print(Panel(
        f"[bold]{spec.get('title', 'Implementation')}[/bold]\n\n"
        f"{spec.get('summary', 'No summary')}\n\n"
        f"[cyan]Files to be modified:[/cyan] {len(spec.get('files', {}))}\n"
        f"[cyan]Tasks to complete:[/cyan] {len(spec.get('tasks', []))}\n"
        f"[cyan]Test requirements:[/cyan] {len(spec.get('tests', {}).get('test_requirements', []))}",
        title="Implementation Plan",
        border_style="yellow"
    ))


def display_review_summary(review: Dict[str, Any]) -> None:
    """Display code review summary."""
    
    approval_colors = {
        "approved": "green",
        "approved_with_comments": "yellow", 
        "changes_requested": "red"
    }
    
    approval = review.get('approval_status', 'unknown')
    color = approval_colors.get(approval, "white")
    
    console.print(Panel(
        f"[bold]{review.get('summary', 'No summary')}[/bold]\n\n"
        f"[cyan]Overall Score:[/cyan] {review.get('overall_score', 'N/A')}/10\n"
        f"[cyan]Approval Status:[/cyan] [{color}]{approval.replace('_', ' ').title()}[/{color}]\n"
        f"[cyan]Security Findings:[/cyan] {len(review.get('security_findings', []))}\n"
        f"[cyan]Actionable Fixes:[/cyan] {len(review.get('actionable_fixes', []))}",
        title="Code Review Summary",
        border_style=color
    ))
    
    # Show critical security findings
    security_findings = review.get('security_findings', [])
    critical_findings = [f for f in security_findings if f.get('severity') == 'critical']
    
    if critical_findings:
        console.print("\n[red bold]Critical Security Issues:[/red bold]")
        for finding in critical_findings:
            console.print(f"  • {finding.get('issue', 'Unknown issue')}")


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()