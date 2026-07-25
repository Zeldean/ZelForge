from __future__ import annotations

import json

import typer

from . import __version__
from .core import config
from .core.paths import get_base_path_info
from .core.storage import ensure_base_dirs


cli = typer.Typer(help="ZelForge CLI.")
paths_app = typer.Typer(help="Manage module paths.")
config_app = typer.Typer(help="Manage ZelForge settings.")
cli.add_typer(paths_app, name="paths")
cli.add_typer(config_app, name="config")


MODULES = [
    ("timer", "zeltimer", "Track named timers and work sessions."),
    ("task", "zeltask", "Manage tasks and task blueprints."),
    ("journal", "zeljournal", "Capture notes and index journal vaults."),
    ("media", "zelmedia", "Manage local media libraries."),
    ("script", "zelscript", "Run small utility scripts."),
    ("repo", "zelrepo", "Index and inspect local repositories."),
    ("habit", "zelhabit", "Track daily habits."),
    ("block", "zelblock", "Plan time blocks."),
]


@cli.callback()
def main() -> None:
    """ZelForge CLI."""


@cli.command()
def version() -> None:
    """Show the installed ZelForge version."""
    typer.echo(f"zelforge {__version__}")


@cli.command()
def modules() -> None:
    """List available ZelForge modules and their commands."""
    for name, command, description in MODULES:
        typer.echo(f"{name:<8} {command:<10} {description}")


@cli.command()
def init(yes: bool = typer.Option(False, "--yes", "-y", help="Accept defaults.")) -> None:
    """Initialize ZelForge folders and starter files."""
    typer.echo("ZelForge will use:")
    _echo_core_paths()
    typer.echo("")
    typer.echo("To use custom core locations, set these before running init:")
    _echo_core_path_env_vars()

    if not yes and not typer.confirm("Continue with these locations?", default=True):
        typer.echo("Init cancelled.")
        raise typer.Exit()

    ensure_base_dirs()
    config.init_config()

    typer.echo("Initialized ZelForge.")


@paths_app.callback(invoke_without_command=True)
def paths(ctx: typer.Context) -> None:
    """Show core folders and configured module paths."""
    if ctx.invoked_subcommand is not None:
        return

    _list_paths()


@paths_app.command("list")
def list_paths() -> None:
    """List core folders and configured module paths."""
    _list_paths()


def _list_paths() -> None:
    _echo_core_paths()

    module_paths = config.load_config()["paths"]
    if not module_paths:
        typer.echo("module  no module paths configured")
        return

    for key, value in sorted(module_paths.items()):
        typer.echo(f"{key}  {value}")


@paths_app.command("get")
def get_module_path(key: str) -> None:
    """Show one module path value."""
    value = config.get_path(key)
    if value is None:
        raise typer.BadParameter(f"Unknown path key: {key}")

    typer.echo(value)


@paths_app.command("set")
def set_module_path(key: str, value: str) -> None:
    """Set one module path value."""
    try:
        data = config.set_path(key, value)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"set path {key} = {data['paths'][key]}")


@paths_app.command("unset")
def unset_module_path(key: str) -> None:
    """Remove one module path value."""
    try:
        existed = config.unset_path(key)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    if existed:
        typer.echo(f"unset path {key}")
        return

    typer.echo(f"path {key} was not set")


@config_app.callback(invoke_without_command=True)
def config_root(ctx: typer.Context) -> None:
    """Show the full ZelForge config."""
    if ctx.invoked_subcommand is None:
        typer.echo(json.dumps(config.load_config(), indent=2))


@config_app.command("show")
def show_config() -> None:
    """Show the full ZelForge config."""
    typer.echo(json.dumps(config.load_config(), indent=2))


@config_app.command("get")
def get_setting(key: str) -> None:
    """Show one setting value."""
    value = config.get_setting(key)
    if value is None:
        raise typer.BadParameter(f"Unknown setting key: {key}")

    typer.echo(value)


@config_app.command("set")
def set_setting(key: str, value: str) -> None:
    """Set one setting value."""
    try:
        config.set_setting(key, value)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"set config {key} = {value}")


@config_app.command("unset")
def unset_setting(key: str) -> None:
    """Remove one setting value."""
    try:
        existed = config.unset_setting(key)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    if existed:
        typer.echo(f"unset config {key}")
        return

    typer.echo(f"config {key} was not set")


def _echo_core_paths() -> None:
    for path_info in get_base_path_info():
        source = path_info.env_var if path_info.is_env_override else "default"
        typer.echo(f"{path_info.label:<7} {path_info.path}  ({source})")


def _echo_core_path_env_vars() -> None:
    for path_info in get_base_path_info():
        typer.echo(f"  {path_info.env_var} for {path_info.label}")


if __name__ == "__main__":
    cli()
