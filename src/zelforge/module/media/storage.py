from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zelforge.core.paths import get_state_dir
from zelforge.core.storage import ensure_dir, get_meta, read_json, write_json


STATE_NAME = "media"
SCHEMA_VERSION = 1


def get_media_state_dir() -> Path:
    return get_state_dir() / STATE_NAME


def get_movies_path() -> Path:
    return get_media_state_dir() / "movies.json"


def init() -> dict[str, Any]:
    ensure_dir(get_media_state_dir())
    if not get_movies_path().exists():
        write_json(get_movies_path(), _make_movies_data())

    return {"status": "success"}


def load_movies_data() -> dict[str, Any]:
    data = read_json(get_movies_path())
    if data is None:
        init()
        data = read_json(get_movies_path())

    data.setdefault("movies", [])
    return data


def save_movies_data(data: dict[str, Any]) -> dict[str, Any]:
    data.setdefault("movies", [])
    data["updated_at"] = _now()
    write_json(get_movies_path(), data)
    return data


def upsert_movie(movie: dict[str, Any]) -> dict[str, Any]:
    data = load_movies_data()
    movies = data["movies"]
    for index, existing in enumerate(movies):
        if (
            existing.get("path") == movie.get("path")
            or (
                existing.get("tmdb_id")
                and movie.get("tmdb_id")
                and existing.get("tmdb_id") == movie.get("tmdb_id")
            )
        ):
            movies[index] = {**existing, **movie, "updated_at": _now()}
            save_movies_data(data)
            return movies[index]

    now = _now()
    movie.setdefault("created_at", now)
    movie.setdefault("updated_at", now)
    movies.append(movie)
    save_movies_data(data)
    return movie


def _make_movies_data() -> dict[str, Any]:
    data = get_meta(SCHEMA_VERSION, "ZelForge movie metadata.")
    data["movies"] = []
    return data


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
