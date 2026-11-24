"""Parse the output of ``git log --numstat`` into :class:`Commit` objects.

The collector asks Git for a machine-readable format that cannot collide
with commit content: records start with ``\\x1e`` and fields are separated
by ``\\x1f``. The layout of one record is::

    <sha> <author name> <author email> <ISO-8601 date> <subject> <parents>
    <added>\\t<deleted>\\t<path>          (one line per changed file)

``--numstat`` prints ``-`` for both counts on binary files, and renames as
``old/path => new/path`` (or ``dir/{old => new}``); renames are normalised
to the new path so churn is attributed to the file that exists now.
"""

from __future__ import annotations

from datetime import datetime

from .models import Commit, FileChange

RECORD_SEP = "\x1e"
FIELD_SEP = "\x1f"

# Must match the --format string built in collector.LOG_FORMAT.
HEADER_FIELDS = 6


class LogParseError(ValueError):
    """Raised when a git log record does not match the expected layout."""


def _normalize_path(path: str) -> str:
    """Collapse a rename entry (``a/{old => new}``) to the new path."""
    if " => " not in path:
        return path
    before, after = path.rsplit(" => ", 1)
    after = after.rstrip("}")
    if "{" in before:
        return before[: before.index("{")] + after
    return after


def _parse_numstat_line(line: str) -> FileChange:
    parts = line.split("\t")
    if len(parts) != 3:
        raise LogParseError(f"malformed numstat line: {line!r}")
    added_s, deleted_s, path = parts
    if added_s == "-" or deleted_s == "-":
        return FileChange(path=_normalize_path(path), added=0, deleted=0, binary=True)
    try:
        added, deleted = int(added_s), int(deleted_s)
    except ValueError as exc:
        raise LogParseError(f"malformed numstat counts: {line!r}") from exc
    return FileChange(path=_normalize_path(path), added=added, deleted=deleted)


def _parse_record(record: str) -> Commit:
    lines = record.strip("\n").splitlines()
    if not lines:
        raise LogParseError("empty log record")
    fields = lines[0].split(FIELD_SEP)
    if len(fields) != HEADER_FIELDS:
        raise LogParseError(
            f"expected {HEADER_FIELDS} header fields, got {len(fields)}: {lines[0]!r}"
        )
    sha, author_name, author_email, date_s, subject, parents_s = fields
    try:
        date = datetime.fromisoformat(date_s)
    except ValueError as exc:
        raise LogParseError(f"unparsable commit date: {date_s!r}") from exc
    parents = tuple(p for p in parents_s.split() if p)
    changes = tuple(_parse_numstat_line(line) for line in lines[1:] if line.strip())
    return Commit(
        sha=sha,
        author_name=author_name,
        author_email=author_email,
        date=date,
        subject=subject,
        parents=parents,
        changes=changes,
    )


def parse_log(text: str) -> list[Commit]:
    """Parse full ``git log`` output into a list of commits, newest first."""
    commits: list[Commit] = []
    for record in text.split(RECORD_SEP):
        if not record.strip():
            continue
        commits.append(_parse_record(record))
    return commits
