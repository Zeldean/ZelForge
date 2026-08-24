from __future__ import annotations

import re


# Matches a `#tag` token anywhere in note text, including hierarchical tags
# like `#meta/test`. Kept separate from the note's explicit `tags` field,
# which is set via CLI flags or the TUI's tags input.
INLINE_TAG_PATTERN = re.compile(r"#([A-Za-z0-9_][A-Za-z0-9_/-]*)")


def extract_inline_tags(body: str) -> list[str]:
    """Return the lowercased `#tag` tokens written inline in note text."""
    return [match.lower() for match in INLINE_TAG_PATTERN.findall(body)]


def normalize_tags(tags: list[str] | None) -> list[str]:
    """Return a deduplicated, lowercased, ordered list of explicit tags."""
    if not tags:
        return []

    seen: set[str] = set()
    normalized: list[str] = []
    for tag in tags:
        cleaned = tag.strip().lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            normalized.append(cleaned)

    return normalized
