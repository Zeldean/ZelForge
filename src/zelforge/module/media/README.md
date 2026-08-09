# Media Module

## Purpose

The media module manages local media libraries under one root folder.

The default layout is:

```text
~/Media/
  aud/
  doc/
  img/
  vid/
    Movies/
    Shows/
```

The root can be changed during init, and paths are saved through the shared
ZelForge path config.

## Commands

```bash
zelmedia init
zelmedia init /home/zeldean/Media
zelmedia info
zelmedia paths list
zelmedia paths set shows ~/Media/vid/Shows
zelmedia scan
zelmedia move ~/Downloads ~/Media/vid/Movies --dry-run
```

Movie commands:

```bash
zelmedia movies scan
zelmedia movies rename --dry-run
zelmedia movies rename
zelmedia movies list
zelmedia movies notes --out ~/Vault/Media
zelmedia movies links
zelmedia movies rec-links --out recs.txt
```

Series commands:

```bash
zelmedia series rename --dry-run
zelmedia series rename --fix-structure
```

## Paths

Media paths are stored as shared config keys:

```text
media.root
media.audio
media.documents
media.images
media.video
media.movies
media.shows
```

Default shows path:

```text
$MEDIA_DIR/vid/Shows
```

Default movie path:

```text
$MEDIA_DIR/vid/Movies
```

Most commands also accept runtime paths with `--path` or explicit source and
destination arguments.

## Movies

Movie renaming should be metadata-first. The renamer uses `TMDB_API_KEY` when
available and renames from the database result instead of trying to clean scene
release names with large bad-word lists.

When metadata is found, files are renamed to:

```text
Movie_Title_(YEAR).ext
```

Metadata is stored in:

```text
~/.local/state/zelforge/media/movies.json
```

If no metadata is found or no API key is configured, the movie is skipped rather
than guessed.

Stored metadata can also generate Markdown notes and YTS-style links. These
features read from `movies.json`; they do not rescan or rename files by
themselves.

## Series

Series renaming is still mostly local filename parsing for now.

Expected structure:

```text
Shows/
  Series_Name/
    Season_01/
      Series_Name_S01E01.mkv
```

The renamer can:

- normalize series folder names
- normalize season folders to `Season_XX`
- rename episodes to `Series_Name_S01E01.ext`
- optionally move root-level episodes into season folders with `--fix-structure`

## Notes

This is the first new-architecture media slice. The movie metadata store is now
the center of the movie workflow; more fields and better matching can be added
without changing the CLI shape.
