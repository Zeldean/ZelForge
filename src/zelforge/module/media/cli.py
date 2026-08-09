from __future__ import annotations

import json
from pathlib import Path

import typer

from . import service
from . import storage


cli = typer.Typer(help="Media commands.", no_args_is_help=True)
movies_app = typer.Typer(help="Movie library commands.")
series_app = typer.Typer(help="Series library commands.")
paths_app = typer.Typer(help="Media path commands.")
cli.add_typer(movies_app, name="movies")
cli.add_typer(series_app, name="series")
cli.add_typer(paths_app, name="paths")


@cli.callback()
def main() -> None:
    """Manage media libraries."""


@cli.command()
def init(
    media_dir: str | None = typer.Argument(
        None,
        help="Media root directory. Defaults to ~/Media.",
    ),
) -> None:
    """Create media folders and media state files."""
    result = service.init_media(media_dir)
    typer.echo(f"initialized media at {result['root']}")
    for key, path in result["paths"].items():
        typer.echo(f"{key:<16} {path}")


@cli.command()
def info() -> None:
    """Show media diagnostics."""
    typer.echo("ZelForge Media")
    typer.echo(f"state           {storage.get_media_state_dir()}")
    typer.echo(f"movies.json     {storage.get_movies_path()}")
    for key, path in service.get_media_paths().items():
        typer.echo(f"{key:<16} {path}")


@cli.command()
def scan(
    folder: str | None = typer.Argument(None, help="Folder to scan."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON."),
) -> None:
    """Recursively list video files."""
    root = Path(folder).expanduser() if folder else service.get_media_path("video")
    videos = service.scan_videos(root)
    if json_output:
        typer.echo(json.dumps(videos, indent=2))
        return

    if not videos:
        typer.echo("no video files found")
        return

    for video in videos:
        typer.echo(video["path"])


@cli.command()
def move(
    source: str,
    destination: str,
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes."),
) -> None:
    """Move videos from source to destination, flattening recursively."""
    try:
        actions = service.move_videos(source, destination, dry_run=dry_run)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    _echo_actions(actions, dry_run=dry_run)


@paths_app.callback(invoke_without_command=True)
def paths_root(ctx: typer.Context) -> None:
    """List media paths."""
    if ctx.invoked_subcommand is None:
        _list_paths()


@paths_app.command("list")
def list_paths() -> None:
    """List media paths."""
    _list_paths()


def _list_paths() -> None:
    for key, path in service.get_media_paths().items():
        typer.echo(f"{key:<16} {path}")


@movies_app.command("scan")
def scan_movies(
    folder: str | None = typer.Option(None, "--path", "-p", help="Movie folder."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON."),
) -> None:
    """List movie video files."""
    root = service.get_media_path("movies", folder)
    videos = service.scan_videos(root)
    if json_output:
        typer.echo(json.dumps(videos, indent=2))
        return

    if not videos:
        typer.echo("no movie files found")
        return

    for video in videos:
        typer.echo(video["path"])


@movies_app.command("rename")
def rename_movies(
    folder: str | None = typer.Option(None, "--path", "-p", help="Movie folder."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes."),
    refresh: bool = typer.Option(False, "--refresh", help="Refresh metadata lookup."),
) -> None:
    """Rename movie files using database metadata when available."""
    try:
        actions = service.rename_movies(folder=folder, dry_run=dry_run, refresh=refresh)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    _echo_actions(actions, dry_run=dry_run)


@movies_app.command("list")
def list_movies() -> None:
    """List stored movie metadata."""
    movies = storage.load_movies_data()["movies"]
    if not movies:
        typer.echo("no movies stored")
        return

    for movie in movies:
        year = movie.get("year") or "????"
        typer.echo(f"{movie.get('title', '-'):<40} {year}  {movie.get('path', '-')}")


@movies_app.command("notes")
def generate_notes(
    output: str = typer.Option(..., "--out", "-o", help="Output notes directory."),
) -> None:
    """Generate Markdown notes from stored movie metadata."""
    actions = service.generate_movie_notes(output)
    _echo_actions(actions)


@movies_app.command("links")
def links(
    output: str | None = typer.Option(None, "--out", "-o", help="Write links to a file."),
) -> None:
    """Print YTS links for stored movies."""
    _echo_links(service.movie_links(), output)


@movies_app.command("rec-links")
def rec_links(
    output: str | None = typer.Option(None, "--out", "-o", help="Write links to a file."),
) -> None:
    """Print YTS links for recommended movies not already stored."""
    _echo_links(service.movie_links(recommended=True), output)


@series_app.command("rename")
def rename_series(
    folder: str | None = typer.Option(None, "--path", "-p", help="Shows folder."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes."),
    fix_structure: bool = typer.Option(
        False,
        "--fix-structure",
        help="Move root-level episodes into Season_XX folders.",
    ),
) -> None:
    """Normalize series folders, season folders, and episode names."""
    try:
        actions = service.rename_series_library(
            folder=folder,
            dry_run=dry_run,
            fix_structure=fix_structure,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    _echo_actions(actions, dry_run=dry_run)


def _echo_actions(actions: list[service.FileAction], dry_run: bool = False) -> None:
    if not actions:
        typer.echo("no changes")
        return

    for action in actions:
        prefix = "would " if dry_run and action.status == "planned" else ""
        target = f" -> {action.target}" if action.target else ""
        reason = f" ({action.reason})" if action.reason else ""
        typer.echo(f"{prefix}{action.action}: {action.source}{target} [{action.status}]{reason}")


def _echo_links(links: list[tuple[str, str, str]], output: str | None = None) -> None:
    lines = [url for _, _, url in links]
    text = "\n".join(lines)
    if output:
        Path(output).expanduser().write_text(text, encoding="utf-8")
        typer.echo(f"wrote {len(lines)} links to {output}")
        return

    typer.echo(text)


if __name__ == "__main__":
    cli()
