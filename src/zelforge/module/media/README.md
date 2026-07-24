# Media Module

## Purpose

The media module helps manage local movie and series files.

It should focus on practical library maintenance: scanning folders, cleaning
file names, generating markdown notes, and preparing links or metadata for the
journal vault.

## Intended Flow

```text
configure media library paths
scan movie or series folders
preview file rename operations
apply safe rename operations
generate markdown notes
export useful links or metadata
```

## Important Ideas

- Media libraries should be configured as module paths, such as
  `media.movies` or `media.series`.
- Destructive file operations should support dry-run previews.
- Movie and series workflows are related but not identical.
- Generated notes may later connect to the journal vault.
- Metadata caches should live under the cache or state directory.

## Possible Commands

```bash
zel paths set media.movies ~/Media/Movies
zel paths set media.series ~/Media/Series
zel media scan
zel media clean --dry-run
zel media clean
zel media series clean --dry-run
zel media notes --out ~/Vault/Media
```

## Notes From Old Attempts

The old media app had folder scanning, movie renaming, series renaming, metadata
lookup, markdown note generation, and link exports. The new version should keep
the safety-first pieces and make path configuration explicit.
