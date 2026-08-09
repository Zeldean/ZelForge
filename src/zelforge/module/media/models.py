from __future__ import annotations

import re
from pathlib import Path


MEDIA_DIRS = {
    "audio": "aud",
    "documents": "doc",
    "images": "img",
    "video": "vid",
}
VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".ogm",
    ".ogv",
}
MOVIE_READY_PATTERN = re.compile(r"^(?P<title>.+)_\((?P<year>(?:19|20)\d{2})\)$")


def is_video_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS


def clean_name_part(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"\[[^\]]*\]|\([^)]*\)|\{[^}]*\}", "", cleaned)
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"[^\w\-]", "_", cleaned)
    cleaned = re.sub(r"_{2,}", "_", cleaned).strip("_")
    return cleaned or value


def build_movie_filename(title: str, year: int | str, suffix: str) -> str:
    return f"{clean_name_part(title)}_({year}){suffix}"
