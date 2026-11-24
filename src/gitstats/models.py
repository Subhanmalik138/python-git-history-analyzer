"""Data model for a parsed Git history.

The parser produces plain immutable dataclasses; every later stage
(statistics, reporting) works only with these, so the analysis logic can be
tested without ever touching a real repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FileChange:
    """One file touched by one commit, as reported by ``git log --numstat``."""

    path: str
    added: int
    deleted: int
    binary: bool = False


@dataclass(frozen=True)
class Commit:
    """A single commit: identity, author, timestamp and file changes."""

    sha: str
    author_name: str
    author_email: str
    date: datetime
    subject: str
    parents: tuple[str, ...] = ()
    changes: tuple[FileChange, ...] = ()

    @property
    def is_merge(self) -> bool:
        """True when the commit has more than one parent."""
        return len(self.parents) > 1

    @property
    def lines_changed(self) -> int:
        return sum(c.added + c.deleted for c in self.changes)
