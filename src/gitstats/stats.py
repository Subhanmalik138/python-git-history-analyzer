"""Aggregate a list of commits into the numbers the report renders.

Everything here is pure computation over :class:`Commit` objects, which is
what makes the analysis easy to unit-test: build commits in a test, call
:meth:`analyse`, and assert on the numbers.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from .models import Commit

#: Share of all commits whose authors define the bus factor.
BUS_FACTOR_SHARE = 0.5


@dataclass
class AuthorStats:
    name: str
    email: str
    commits: int = 0
    added: int = 0
    deleted: int = 0
    files_touched: set[str] = field(default_factory=set)
    first_date: date | None = None
    last_date: date | None = None
    active_days: set[date] = field(default_factory=set)

    @property
    def lines_changed(self) -> int:
        return self.added + self.deleted


@dataclass
class FileStats:
    path: str
    commits: int = 0
    added: int = 0
    deleted: int = 0

    @property
    def lines_changed(self) -> int:
        return self.added + self.deleted


@dataclass
class Streak:
    days: int
    start: date | None
    end: date | None


@dataclass
class Analysis:
    total_commits: int
    total_authors: int
    total_files: int
    total_added: int
    total_deleted: int
    merge_commits: int
    first_date: date | None
    last_date: date | None
    timespan_days: int
    authors: list[AuthorStats]
    files: list[FileStats]
    by_weekday: list[int]  # Monday (0) .. Sunday (6)
    by_hour: list[int]  # 0 .. 23, local time as recorded by git
    by_month: dict[str, int]  # "YYYY-MM" -> commits, ascending
    bus_factor: int
    bus_factor_authors: list[str]
    longest_streak: Streak
    author_streaks: list[tuple[str, Streak]]  # longest first


def _longest_streak(days: set[date]) -> Streak:
    """Longest run of consecutive calendar days in *days*."""
    if not days:
        return Streak(0, None, None)
    ordered = sorted(days)
    best_start = cur_start = ordered[0]
    best_len = cur_len = 1
    for prev, today in zip(ordered, ordered[1:]):
        if today == prev + timedelta(days=1):
            cur_len += 1
        else:
            cur_start, cur_len = today, 1
        if cur_len > best_len:
            best_len, best_start = cur_len, cur_start
    return Streak(best_len, best_start, best_start + timedelta(days=best_len - 1))


def analyse(commits: list[Commit]) -> Analysis:
    """Compute every statistic from a list of commits (newest first)."""
    authors: dict[str, AuthorStats] = {}
    files: dict[str, FileStats] = {}
    by_weekday = [0] * 7
    by_hour = [0] * 24
    by_month: Counter[str] = Counter()
    total_added = total_deleted = merges = 0
    commit_dates: set[date] = set()
    first_date = last_date = None

    for commit in commits:
        day = commit.date.date()
        commit_dates.add(day)
        if first_date is None or day < first_date:
            first_date = day
        if last_date is None or day > last_date:
            last_date = day
        by_weekday[day.weekday()] += 1
        by_hour[commit.date.hour] += 1
        by_month[commit.date.strftime("%Y-%m")] += 1
        if commit.is_merge:
            merges += 1

        key = commit.author_email or commit.author_name
        author = authors.setdefault(
            key, AuthorStats(name=commit.author_name, email=commit.author_email)
        )
        author.commits += 1
        author.active_days.add(day)
        if author.first_date is None or day < author.first_date:
            author.first_date = day
        if author.last_date is None or day > author.last_date:
            author.last_date = day

        for change in commit.changes:
            author.files_touched.add(change.path)
            if not change.binary:
                author.added += change.added
                author.deleted += change.deleted
                total_added += change.added
                total_deleted += change.deleted
            entry = files.setdefault(change.path, FileStats(path=change.path))
            entry.commits += 1
            entry.added += change.added
            entry.deleted += change.deleted

    ranked_authors = sorted(
        authors.values(), key=lambda a: (-a.commits, -a.lines_changed, a.name)
    )
    ranked_files = sorted(
        files.values(), key=lambda f: (-f.commits, -f.lines_changed, f.path)
    )

    # Bus factor: fewest top authors whose commits cover >= 50% of history.
    # Greedy by commit count is exact here — shares are additive and sorted.
    bus_factor = 0
    bus_factor_authors: list[str] = []
    covered = 0
    threshold = len(commits) * BUS_FACTOR_SHARE
    for author in ranked_authors:
        if covered >= threshold:
            break
        covered += author.commits
        bus_factor += 1
        bus_factor_authors.append(author.name)

    author_streaks = sorted(
        ((a.name, _longest_streak(a.active_days)) for a in ranked_authors),
        key=lambda item: -item[1].days,
    )

    return Analysis(
        total_commits=len(commits),
        total_authors=len(authors),
        total_files=len(files),
        total_added=total_added,
        total_deleted=total_deleted,
        merge_commits=merges,
        first_date=first_date,
        last_date=last_date,
        timespan_days=(last_date - first_date).days + 1 if first_date else 0,
        authors=ranked_authors,
        files=ranked_files,
        by_weekday=by_weekday,
        by_hour=by_hour,
        by_month=dict(sorted(by_month.items())),
        bus_factor=bus_factor,
        bus_factor_authors=bus_factor_authors,
        longest_streak=_longest_streak(commit_dates),
        author_streaks=author_streaks,
    )
