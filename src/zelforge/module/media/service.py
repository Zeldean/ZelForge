from __future__ import annotations

import json
import os
import re
import shutil
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from zelforge.core import config

from . import storage
from .models import MEDIA_DIRS, MOVIE_READY_PATTERN, build_movie_filename, clean_name_part, is_video_file


TMDB_API = "https://api.themoviedb.org/3"


@dataclass
class FileAction:
    action: str
    source: Path
    target: Path | None = None
    status: str = "planned"
    reason: str = ""


def init_media(media_dir: str | None = None) -> dict:
    """Create the media folder structure and module state."""
    root = Path(media_dir).expanduser() if media_dir else get_media_root()
    paths = {
        "media.root": root,
        "media.audio": root / MEDIA_DIRS["audio"],
        "media.documents": root / MEDIA_DIRS["documents"],
        "media.images": root / MEDIA_DIRS["images"],
        "media.video": root / MEDIA_DIRS["video"],
        "media.movies": root / MEDIA_DIRS["video"] / "Movies",
        "media.shows": root / MEDIA_DIRS["video"] / "Shows",
    }

    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    for key, path in paths.items():
        config.set_path(key, str(path))

    storage.init()
    return {"status": "success", "root": root, "paths": paths}


def get_media_root() -> Path:
    configured = config.get_path("media.root")
    return Path(configured).expanduser() if configured else Path.home() / "Media"


def get_media_path(key: str, override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser()

    normalized = key if key.startswith("media.") else f"media.{key}"
    configured = config.get_path(normalized)
    if configured:
        return Path(configured).expanduser()

    root = get_media_root()
    defaults = {
        "media.root": root,
        "media.audio": root / MEDIA_DIRS["audio"],
        "media.documents": root / MEDIA_DIRS["documents"],
        "media.images": root / MEDIA_DIRS["images"],
        "media.video": root / MEDIA_DIRS["video"],
        "media.movies": root / MEDIA_DIRS["video"] / "Movies",
        "media.shows": root / MEDIA_DIRS["video"] / "Shows",
    }
    if normalized not in defaults:
        raise ValueError(f"Unknown media path: {key}")

    return defaults[normalized]


def get_media_paths() -> dict[str, Path]:
    keys = [
        "media.root",
        "media.audio",
        "media.documents",
        "media.images",
        "media.video",
        "media.movies",
        "media.shows",
    ]
    return {key: get_media_path(key) for key in keys}


def scan_videos(folder: str | Path) -> list[dict]:
    root = Path(folder).expanduser()
    _require_dir(root)
    return [
        {
            "name": path.name,
            "path": str(path),
            "size": path.stat().st_size,
        }
        for path in sorted(root.rglob("*"))
        if is_video_file(path)
    ]


def move_videos(source: str, destination: str, dry_run: bool = False) -> list[FileAction]:
    source_path = Path(source).expanduser()
    destination_path = Path(destination).expanduser()
    _require_dir(source_path)
    actions = []

    for file_path in sorted(path for path in source_path.rglob("*") if is_video_file(path)):
        target = _dedupe_target(destination_path / file_path.name)
        action = FileAction("move", file_path, target)
        actions.append(action)
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(target))
            action.status = "done"

    return actions


def rename_movies(
    folder: str | Path | None = None,
    dry_run: bool = False,
    refresh: bool = False,
) -> list[FileAction]:
    root = get_media_path("movies", str(folder) if folder else None)
    _require_dir(root)
    actions = []

    for file_path in sorted(path for path in root.iterdir() if is_video_file(path)):
        movie = identify_movie(file_path, refresh=refresh)
        if not movie:
            actions.append(
                FileAction(
                    "rename",
                    file_path,
                    status="skipped",
                    reason="metadata not found",
                )
            )
            continue

        target = file_path.with_name(
            build_movie_filename(movie["title"], movie["year"], file_path.suffix)
        )
        action = FileAction("rename", file_path, target)
        if target == file_path:
            action.status = "unchanged"
        elif target.exists():
            action.status = "skipped"
            action.reason = "target exists"
        elif not dry_run:
            file_path.rename(target)
            action.status = "done"
            movie["path"] = str(target)

        storage.upsert_movie(movie)
        actions.append(action)

    return actions


def identify_movie(file_path: Path, refresh: bool = False) -> dict | None:
    candidate = parse_movie_candidate(file_path)
    if not candidate:
        return None

    metadata = lookup_movie(candidate["title"], candidate.get("year"), refresh=refresh)
    if not metadata:
        return None

    return {
        "id": str(uuid4()),
        "path": str(file_path),
        "source_name": file_path.name,
        "title": metadata["title"],
        "year": metadata["year"],
        "tmdb_id": metadata.get("tmdb_id"),
        "original_title": metadata.get("original_title"),
        "release_date": metadata.get("release_date"),
        "overview": metadata.get("overview", ""),
        "runtime": metadata.get("runtime"),
        "genres": metadata.get("genres", []),
        "poster_path": metadata.get("poster_path"),
        "matched_query": candidate["title"],
        "matched_year": candidate.get("year"),
        "updated_at": _now(),
    }


def parse_movie_candidate(file_path: Path) -> dict | None:
    stem = file_path.stem
    ready = MOVIE_READY_PATTERN.match(stem)
    if ready:
        return {
            "title": ready.group("title").replace("_", " "),
            "year": int(ready.group("year")),
        }

    year = None
    match = re.search(r"(19|20)\d{2}", stem)
    if match:
        year = int(match.group(0))
        stem = f"{stem[:match.start()]} {stem[match.end():]}"

    title = re.sub(r"[._\-]+", " ", stem)
    title = re.sub(r"\[[^\]]*\]|\([^)]*\)|\{[^}]*\}", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    if not title:
        return None

    return {"title": title, "year": year}


def lookup_movie(title: str, year: int | None = None, refresh: bool = False) -> dict | None:
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        return None

    search = _tmdb_get(
        "search/movie",
        {
            "query": title,
            **({"year": str(year)} if year else {}),
        },
        api_key,
    )
    results = search.get("results", [])
    if not results:
        return None

    best = results[0]
    details = _tmdb_get(
        f"movie/{best['id']}",
        {"append_to_response": "external_ids"},
        api_key,
    )
    release_date = details.get("release_date") or best.get("release_date") or ""
    return {
        "tmdb_id": details.get("id") or best.get("id"),
        "title": details.get("title") or best.get("title") or title,
        "original_title": details.get("original_title") or best.get("original_title"),
        "year": int(release_date[:4]) if release_date[:4].isdigit() else year or "????",
        "release_date": release_date,
        "overview": details.get("overview") or best.get("overview") or "",
        "runtime": details.get("runtime"),
        "genres": [genre["name"] for genre in details.get("genres", [])],
        "poster_path": details.get("poster_path") or best.get("poster_path"),
        "imdb_id": details.get("external_ids", {}).get("imdb_id"),
    }


def rename_series_library(
    folder: str | Path | None = None,
    dry_run: bool = False,
    fix_structure: bool = False,
) -> list[FileAction]:
    root = get_media_path("shows", str(folder) if folder else None)
    _require_dir(root)
    actions = []
    for series_folder in sorted(path for path in root.iterdir() if path.is_dir()):
        actions.extend(
            clean_single_series_folder(
                series_folder,
                dry_run=dry_run,
                fix_structure=fix_structure,
            )
        )
    return actions


def clean_single_series_folder(
    series_folder: Path,
    dry_run: bool = False,
    fix_structure: bool = False,
) -> list[FileAction]:
    actions = []
    normalized_series = _safe_rename(
        series_folder,
        clean_name_part(series_folder.name),
        dry_run=dry_run,
    )
    actions.append(normalized_series)
    if normalized_series.target and normalized_series.status == "done":
        series_folder = normalized_series.target

    actions.extend(_normalize_season_folders(series_folder, dry_run=dry_run))
    if fix_structure:
        actions.extend(_move_root_episodes(series_folder, dry_run=dry_run))
        actions.extend(_normalize_season_folders(series_folder, dry_run=dry_run))

    actions.extend(_rename_episode_files(series_folder, dry_run=dry_run))
    return [action for action in actions if action.status != "unchanged"]


def _normalize_season_folders(series_folder: Path, dry_run: bool) -> list[FileAction]:
    actions = []
    for item in sorted(path for path in series_folder.iterdir() if path.is_dir()):
        season = _season_from_folder(item.name)
        if season is None:
            continue

        actions.append(_safe_rename(item, f"Season_{season:02d}", dry_run=dry_run))

    return actions


def _move_root_episodes(series_folder: Path, dry_run: bool) -> list[FileAction]:
    actions = []
    for item in sorted(path for path in series_folder.iterdir() if is_video_file(path)):
        season = _season_from_filename(item.name)
        if season is None:
            continue

        destination = series_folder / f"Season_{season:02d}"
        target = destination / item.name
        action = FileAction("move", item, target)
        if not dry_run:
            destination.mkdir(parents=True, exist_ok=True)
            item.rename(target)
            action.status = "done"
        actions.append(action)

    return actions


def _rename_episode_files(series_folder: Path, dry_run: bool) -> list[FileAction]:
    actions = []
    for season_folder in sorted(path for path in series_folder.iterdir() if path.is_dir()):
        season = _season_from_folder(season_folder.name)
        if season is None:
            continue

        for file_path in sorted(path for path in season_folder.iterdir() if is_video_file(path)):
            episode = _episode_from_filename(file_path.name, folder_season=season)
            if not episode:
                continue

            target = file_path.with_name(
                _build_episode_name(file_path, series_folder.name, episode)
            )
            actions.append(_safe_rename(file_path, target.name, dry_run=dry_run))

    return actions


def _safe_rename(path: Path, new_name: str, dry_run: bool) -> FileAction:
    target = path.with_name(new_name)
    action = FileAction("rename", path, target)
    if target == path:
        action.status = "unchanged"
    elif target.exists():
        action.status = "skipped"
        action.reason = "target exists"
    elif not dry_run:
        path.rename(target)
        action.status = "done"

    return action


def _season_from_folder(folder_name: str) -> int | None:
    match = re.search(
        r"(?i)(?:^|[._\-\s])(?:season|s)[\s._-]*0*(\d{1,2})(?=$|[._\-\s])",
        folder_name.strip(),
    )
    if not match:
        return None

    season = int(match.group(1))
    return season if season > 0 else None


def _season_from_filename(filename: str) -> int | None:
    match = re.search(r"(?i)\bS\s*0*(\d{1,2})\s*[-_ ]?\s*E", Path(filename).stem)
    return int(match.group(1)) if match else None


def _episode_from_filename(filename: str, folder_season: int | None = None) -> dict | None:
    stem = Path(filename).stem
    patterns = [
        re.compile(r"(?i)\bS\s*0*(\d{1,2})\s*[-_ ]?\s*E\s*0*(\d{1,3})(?:\s*[-_ ]?\s*E\s*0*(\d{1,3}))?\b"),
        re.compile(r"(?i)\bE\s*0*(\d{1,3})(?:\s*[-_ ]?\s*E\s*0*(\d{1,3}))?\b"),
        re.compile(r"(?<!\d)(\d{1,3})(?!\d)\s*$"),
        re.compile(r"(?:^|[\s._-])0*(\d{1,3})(?=$|[\s._-])"),
        re.compile(r"^\s*0*(\d{1,3})(?=$|[^0-9])"),
    ]
    for index, pattern in enumerate(patterns):
        match = pattern.search(stem)
        if not match:
            continue

        if index == 0:
            season = int(match.group(1))
            episode = int(match.group(2))
            end_episode = int(match.group(3)) if match.group(3) else None
        else:
            if folder_season is None:
                continue
            season = folder_season
            episode = int(match.group(1))
            end_episode = int(match.group(2)) if index == 1 and match.group(2) else None

        return {
            "season": season,
            "episode": episode,
            "end_episode": end_episode,
            "is_range": end_episode is not None,
        }

    return None


def _build_episode_name(file_path: Path, series_name: str, episode: dict) -> str:
    base = clean_name_part(series_name)
    part = f"S{episode['season']:02d}E{episode['episode']:02d}"
    if episode["is_range"]:
        part = f"{part}-E{episode['end_episode']:02d}"

    return f"{base}_{part}{file_path.suffix}"


def _tmdb_get(endpoint: str, params: dict[str, str], api_key: str) -> dict:
    params = {**params, "api_key": api_key}
    url = f"{TMDB_API}/{endpoint}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "ZelForge/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _dedupe_target(target: Path) -> Path:
    if not target.exists():
        return target

    counter = 1
    while True:
        candidate = target.with_name(f"[DUP {counter}] {target.name}")
        if not candidate.exists():
            return candidate
        counter += 1


def _require_dir(path: Path) -> None:
    if not path.exists() or not path.is_dir():
        raise ValueError(f"Directory does not exist: {path}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
