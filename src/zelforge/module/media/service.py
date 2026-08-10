from __future__ import annotations

import json
import os
import re
import shutil
import urllib.parse
import urllib.request
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from uuid import uuid4

from zelforge.core import config

from . import storage
from .models import MEDIA_DIRS, MOVIE_READY_PATTERN, build_movie_filename, clean_name_part, is_video_file


TMDB_API = "https://api.themoviedb.org/3"
MIN_TITLE_SIMILARITY = 0.86
MIN_TOKEN_OVERLAP = 0.80


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
        movie, reason = identify_movie(file_path, refresh=refresh)
        if not movie:
            actions.append(
                FileAction(
                    "rename",
                    file_path,
                    status="skipped",
                    reason=reason or "metadata not found",
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


def identify_movie(file_path: Path, refresh: bool = False) -> tuple[dict | None, str]:
    candidate = parse_movie_candidate(file_path)
    if not candidate:
        return None, "could not parse filename"

    metadata = lookup_movie(candidate["title"], candidate.get("year"), refresh=refresh)
    if not metadata:
        return None, "metadata not found"

    match_error = validate_movie_match(candidate, metadata)
    if match_error:
        return None, match_error

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
        "similar": metadata.get("similar", []),
        "matched_query": candidate["title"],
        "matched_year": candidate.get("year"),
        "match_score": metadata.get("match_score"),
        "token_overlap": metadata.get("token_overlap"),
        "updated_at": _now(),
    }, ""


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

    best = _best_movie_result(title, year, results)
    if not best:
        return None

    details = _tmdb_get(
        f"movie/{best['id']}",
        {"append_to_response": "external_ids,recommendations"},
        api_key,
    )
    release_date = details.get("release_date") or best.get("release_date") or ""
    similar = details.get("recommendations", {}).get("results", [])
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
        "match_score": best.get("_match_score"),
        "token_overlap": best.get("_token_overlap"),
        "similar": [
            {
                "title": movie.get("title"),
                "release_date": movie.get("release_date"),
            }
            for movie in similar
            if movie.get("title")
        ],
    }


def generate_movie_notes(output: str) -> list[FileAction]:
    """Generate one Markdown note per stored movie."""
    output_dir = Path(output).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    actions = []

    for movie in storage.load_movies_data()["movies"]:
        title = movie.get("title")
        year = movie.get("year") or "????"
        if not title:
            continue

        note_path = output_dir / f"{clean_name_part(title)}_({year}).md"
        note_path.write_text(_movie_note(movie), encoding="utf-8")
        actions.append(FileAction("write", note_path, status="done"))

    return actions


def movie_links(recommended: bool = False) -> list[tuple[str, str, str]]:
    """Return YTS-style links for stored or recommended movies."""
    movies = storage.load_movies_data()["movies"]
    if not recommended:
        return [
            (
                movie.get("title", ""),
                str(movie.get("year") or "????"),
                _yts_url(movie.get("title", ""), movie.get("year") or "????"),
            )
            for movie in movies
            if movie.get("title")
        ]

    owned = {
        (movie.get("title", "").lower(), str(movie.get("year") or "????"))
        for movie in movies
    }
    seen = set()
    links = []
    for movie in movies:
        for similar in movie.get("similar", []):
            title = similar.get("title", "")
            year = _year_from_release_date(similar.get("release_date"))
            key = (title.lower(), str(year))
            if not title or key in owned or key in seen:
                continue

            seen.add(key)
            links.append((title, str(year), _yts_url(title, year)))

    return links


def validate_movie_match(candidate: dict, metadata: dict) -> str | None:
    """Return a skip reason when TMDb metadata is not a strong filename match."""
    candidate_year = candidate.get("year")
    metadata_year = metadata.get("year")
    if candidate_year and metadata_year != candidate_year:
        return f"year mismatch: {candidate_year} != {metadata_year}"

    candidate_title = candidate["title"]
    metadata_title = metadata.get("title") or ""
    similarity = _title_similarity(candidate_title, metadata_title)
    overlap = _token_overlap(candidate_title, metadata_title)
    if similarity < MIN_TITLE_SIMILARITY and overlap < MIN_TOKEN_OVERLAP:
        return (
            "weak title match: "
            f"{candidate_title!r} -> {metadata_title!r} "
            f"score={similarity:.2f} overlap={overlap:.2f}"
        )

    discriminator_error = _validate_discriminators(candidate_title, metadata_title)
    if discriminator_error:
        return discriminator_error

    return None


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


def _best_movie_result(title: str, year: int | None, results: list[dict]) -> dict | None:
    scored = []
    for result in results:
        result_title = result.get("title") or result.get("original_title") or ""
        result_year = _year_from_release_date(result.get("release_date"))
        if year and result_year != year:
            continue

        similarity = _title_similarity(title, result_title)
        overlap = _token_overlap(title, result_title)
        discriminator_error = _validate_discriminators(title, result_title)
        if discriminator_error:
            continue

        if similarity < MIN_TITLE_SIMILARITY and overlap < MIN_TOKEN_OVERLAP:
            continue

        scored.append(
            (
                max(similarity, overlap),
                result.get("popularity") or 0,
                {
                    **result,
                    "_match_score": round(similarity, 3),
                    "_token_overlap": round(overlap, 3),
                },
            )
        )

    if not scored:
        return None

    return sorted(scored, key=lambda item: (item[0], item[1]), reverse=True)[0][2]


def _title_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalize_title(left), _normalize_title(right)).ratio()


def _token_overlap(left: str, right: str) -> float:
    left_tokens = set(_title_tokens(left))
    right_tokens = set(_title_tokens(right))
    if not left_tokens or not right_tokens:
        return 0

    return len(left_tokens & right_tokens) / max(len(left_tokens), len(right_tokens))


def _validate_discriminators(left: str, right: str) -> str | None:
    left_discriminators = _title_discriminators(left)
    right_discriminators = _title_discriminators(right)
    if left_discriminators != right_discriminators:
        return (
            "title marker mismatch: "
            f"{sorted(left_discriminators)} != {sorted(right_discriminators)}"
        )

    return None


def _normalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    normalized = normalized.lower()
    normalized = normalized.replace("&", " and ")
    normalized = normalized.replace("'", "").replace("’", "")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _title_tokens(value: str) -> list[str]:
    return [token for token in _normalize_title(value).split() if token]


def _title_discriminators(value: str) -> set[str]:
    tokens = _title_tokens(value)
    discriminators = set()
    consumed_indexes = set()
    roman = {
        "i": "1",
        "ii": "2",
        "iii": "3",
        "iv": "4",
        "v": "5",
        "vi": "6",
        "vii": "7",
        "viii": "8",
        "ix": "9",
        "x": "10",
    }
    number_words = {
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
    }

    for index, token in enumerate(tokens[:-1]):
        next_token = tokens[index + 1]
        if token in {"part", "episode", "chapter"} and (
            next_token.isdigit() or next_token in roman or next_token in number_words
        ):
            number = (
                next_token
                if next_token.isdigit()
                else roman.get(next_token, number_words.get(next_token, next_token))
            )
            discriminators.add(f"{token}:{number}")
            consumed_indexes.add(index + 1)

    for index, token in enumerate(tokens):
        if index not in consumed_indexes and token.isdigit():
            discriminators.add(token)

    return discriminators


def _movie_note(movie: dict) -> str:
    title = movie.get("title", "Untitled")
    year = movie.get("year") or "????"
    genres = movie.get("genres", [])
    poster_path = movie.get("poster_path") or ""
    poster = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else ""
    similar = movie.get("similar", [])
    similar_lines = [
        f"- [[{clean_name_part(item['title'])}_({_year_from_release_date(item.get('release_date'))})|"
        f"{item['title']} ({_year_from_release_date(item.get('release_date'))})]]"
        for item in similar
        if item.get("title")
    ]

    return (
        "---\n"
        "cssclasses: mediaNote\n"
        "tags:\n"
        "  - media/movie\n"
        f"title: {title} ({year})\n"
        f"yearReleased: {year}\n"
        f"runtime: {movie.get('runtime') or ''}\n"
        f"genres: {json.dumps(genres)}\n"
        f"poster: {poster}\n"
        "---\n"
        "# Synopsis\n"
        f"{movie.get('overview') or ''}\n\n"
        "---\n"
        "# More Like This\n"
        f"{chr(10).join(similar_lines) if similar_lines else '- TODO'}\n"
    )


def _yts_url(title: str, year: int | str) -> str:
    return f"https://yts.mx/movies/{_slugify(title)}-{year}"


def _slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^\w]+", "-", text.lower()).strip("-")


def _year_from_release_date(value: str | None) -> int | str:
    return int(value[:4]) if value and value[:4].isdigit() else "????"


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
