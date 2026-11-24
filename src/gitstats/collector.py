"""Collect commits from a local repository by shelling out to ``git``.

The package never reads ``.git`` internals directly: invoking the Git CLI
keeps it correct across repository formats and lets Git do the hard work
of walking history. Only ``git log`` is ever executed, with no user input
interpolated into a shell — arguments are passed as a list.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .models import Commit
from .parser import FIELD_SEP, RECORD_SEP, parse_log

# %x1e / %x1f are literal control characters; %aI is strict ISO-8601.
LOG_FORMAT = (
    f"{RECORD_SEP}%H{FIELD_SEP}%an{FIELD_SEP}%ae{FIELD_SEP}%aI"
    f"{FIELD_SEP}%s{FIELD_SEP}%P"
)


class GitError(RuntimeError):
    """Raised when the ``git`` invocation itself fails."""


def collect_commits(
    path: str | Path = ".",
    *,
    since: str | None = None,
    until: str | None = None,
    author: str | None = None,
) -> list[Commit]:
    """Return the commits of the repository at *path*, newest first.

    An empty repository (no commits yet) yields ``[]`` instead of an error.
    A path that is not a Git repository raises :class:`GitError`.
    """
    repo = Path(path)
    if not repo.is_dir():
        raise GitError(f"not a directory: {path}")
    args = ["git", "-C", str(repo), "log", f"--format={LOG_FORMAT}", "--numstat"]
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    if author:
        args.append(f"--author={author}")
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        if "does not have any commits yet" in stderr:
            return []
        if "not a git repository" in stderr:
            raise GitError(f"not a git repository: {path}")
        raise GitError(f"git log failed: {stderr or proc.returncode}")
    return parse_log(proc.stdout)


def collect_from_file(path: str | Path) -> list[Commit]:
    """Parse previously saved ``git log`` output (same format as the CLI)."""
    return parse_log(Path(path).read_text(encoding="utf-8"))
