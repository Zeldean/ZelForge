from __future__ import annotations

import json

import typer

from . import __version__
from .core import config
from .core import domains as domain_store
from .core.paths import get_base_path_info
from .core.storage import ensure_base_dirs


cli = typer.Typer(help="ZelForge CLI.")
paths_app = typer.Typer(help="Manage module paths.")
config_app = typer.Typer(help="Manage ZelForge settings.")
domains_app = typer.Typer(help="Manage shared domains.")
cli.add_typer(paths_app, name="paths")
cli.add_typer(config_app, name="config")
cli.add_typer(domains_app, name="domains")


MODULES = [
    ("timer", "zeltimer", "Track named timers and work sessions."),
    ("task", "zeltask", "Manage tasks and task blueprints."),
    ("journal", "zeljournal", "Capture notes and index journal vaults."),
    ("media", "zelmedia", "Manage local media libraries."),
    ("script", "zelscript", "Run small utility scripts."),
    ("repo", "zelrepo", "Index and inspect local repositories."),
    ("habit", "zelhabit", "Track daily habits."),
    ("block", "zelblock", "Plan time blocks."),
    ("sandbox", "zelsandbox", "Standalone TUI mockups for testing frontends."),
]


@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """ZelForge CLI. Bare command opens the TUI."""
    if ctx.invoked_subcommand is None:
        from .tui import run

        run()


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
    domain_store.init_domains()

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


@domains_app.callback(invoke_without_command=True)
def domains_root(ctx: typer.Context) -> None:
    """List shared domains."""
    if ctx.invoked_subcommand is None:
        _list_domains()


@domains_app.command("list")
def list_domains(
    all_domains: bool = typer.Option(False, "--all", "-a", help="Show inactive domains."),
) -> None:
    """List shared domains."""
    _list_domains(include_inactive=all_domains)


@domains_app.command("add")
def add_domain(
    code: str,
    name: str | None = typer.Option(None, "--name", "-n", help="Display name."),
    description: str = typer.Option("", "--description", "-d", help="Description."),
) -> None:
    """Add a shared domain."""
    try:
        domain = domain_store.add_domain(
            code=code,
            name=name,
            description=description,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"added domain {domain['code']}: {domain['name']}")


@domains_app.command("rename")
def rename_domain(
    code: str,
    new_code: str,
    name: str | None = typer.Option(None, "--name", "-n", help="New display name."),
) -> None:
    """Rename a shared domain code."""
    try:
        domain = domain_store.rename_domain(code, new_code, name=name)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"renamed domain {code} -> {domain['code']}")


@domains_app.command("deactivate")
def deactivate_domain(code: str) -> None:
    """Mark a domain inactive."""
    try:
        domain = domain_store.set_domain_active(code, False)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"deactivated domain {domain['code']}")


@domains_app.command("activate")
def activate_domain(code: str) -> None:
    """Mark a domain active."""
    try:
        domain = domain_store.set_domain_active(code, True)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"activated domain {domain['code']}")


@domains_app.command("remove")
def remove_domain(
    code: str,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
) -> None:
    """Remove a shared domain."""
    if not yes and not typer.confirm(f"Remove domain {code}?", default=False):
        typer.echo("Remove cancelled.")
        raise typer.Exit()

    try:
        removed = domain_store.remove_domain(code)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    if removed:
        typer.echo(f"removed domain {code}")
        return

    typer.echo(f"domain {code} was not set")


@domains_app.command("default")
def set_default_domain(code: str | None = typer.Argument(None)) -> None:
    """Show or set the default domain."""
    if code is None:
        typer.echo(domain_store.get_default_domain() or "-")
        return

    try:
        default_domain = domain_store.set_default_domain(code)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"default domain {default_domain}")


@domains_app.command("clear-default")
def clear_default_domain() -> None:
    """Clear the default domain."""
    domain_store.set_default_domain(None)
    typer.echo("cleared default domain")


def _list_domains(include_inactive: bool = False) -> None:
    data = domain_store.load_domains_data()
    default_domain = data.get("default_domain")
    domains = domain_store.list_domains(include_inactive=include_inactive)
    if not domains:
        typer.echo("no domains configured")
        return

    for domain in domains:
        code = domain.get("code") or domain.get("key") or "-"
        marker = "*" if code == default_domain else " "
        active = "" if domain.get("active") is not False else " inactive"
        typer.echo(f"{marker} {code:<8} {domain['name']}{active}")


def _echo_core_paths() -> None:
    for path_info in get_base_path_info():
        source = path_info.env_var if path_info.is_env_override else "default"
        typer.echo(f"{path_info.label:<7} {path_info.path}  ({source})")


def _echo_core_path_env_vars() -> None:
    for path_info in get_base_path_info():
        typer.echo(f"  {path_info.env_var} for {path_info.label}")


if __name__ == "__main__":
    cli()
