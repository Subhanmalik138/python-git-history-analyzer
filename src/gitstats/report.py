"""Render an :class:`~gitstats.stats.Analysis` as text or JSON."""

from __future__ import annotations

import json

from .stats import Analysis

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
BAR_WIDTH = 30


def _bar(count: int, peak: int) -> str:
    if peak <= 0:
        return ""
    return "#" * max(1, round(count / peak * BAR_WIDTH)) if count else ""


def render_text(analysis: Analysis, *, top: int = 10) -> str:
    """Human-readable multi-section report."""
    if analysis.total_commits == 0:
        return "No commits found in the selected history.\n"

    lines: list[str] = []
    a = analysis
    lines.append("Git history report")
    lines.append("=" * 40)
    lines.append(f"Commits:        {a.total_commits} ({a.merge_commits} merges)")
    lines.append(f"Authors:        {a.total_authors}")
    lines.append(f"Files touched:  {a.total_files}")
    lines.append(f"Lines:          +{a.total_added} / -{a.total_deleted}")
    if a.first_date and a.last_date:
        lines.append(
            f"Timespan:       {a.first_date} to {a.last_date} "
            f"({a.timespan_days} days)"
        )
    lines.append(
        f"Bus factor:     {a.bus_factor} "
        f"({', '.join(a.bus_factor_authors)})"
    )
    streak = a.longest_streak
    if streak.days:
        lines.append(
            f"Longest streak: {streak.days} days "
            f"({streak.start} to {streak.end})"
        )

    lines.append("")
    lines.append(f"Top authors (top {top})")
    lines.append("-" * 40)
    for author in a.authors[:top]:
        share = 100 * author.commits / a.total_commits
        lines.append(
            f"{author.name:<24} {author.commits:>4} commits "
            f"({share:4.1f}%)  +{author.added}/-{author.deleted}  "
            f"{len(author.files_touched)} files"
        )

    lines.append("")
    lines.append(f"Most-changed files (top {top})")
    lines.append("-" * 40)
    for entry in a.files[:top]:
        lines.append(
            f"{entry.path:<40} {entry.commits:>4} commits  "
            f"+{entry.added}/-{entry.deleted}"
        )

    lines.append("")
    lines.append("Commits by weekday")
    lines.append("-" * 40)
    peak = max(a.by_weekday)
    for name, count in zip(WEEKDAYS, a.by_weekday):
        lines.append(f"{name}  {count:>4}  {_bar(count, peak)}")

    lines.append("")
    lines.append("Commits by hour")
    lines.append("-" * 40)
    peak = max(a.by_hour)
    for hour, count in enumerate(a.by_hour):
        if count:
            lines.append(f"{hour:02d}:00  {count:>4}  {_bar(count, peak)}")

    if len(a.by_month) > 1:
        lines.append("")
        lines.append("Commits by month")
        lines.append("-" * 40)
        peak = max(a.by_month.values())
        for month, count in a.by_month.items():
            lines.append(f"{month}  {count:>4}  {_bar(count, peak)}")

    lines.append("")
    return "\n".join(lines)


def render_json(analysis: Analysis, *, top: int = 10) -> str:
    """Machine-readable report; same numbers as the text version."""
    a = analysis

    def _date(value):
        return value.isoformat() if value else None

    payload = {
        "total_commits": a.total_commits,
        "merge_commits": a.merge_commits,
        "total_authors": a.total_authors,
        "total_files": a.total_files,
        "total_added": a.total_added,
        "total_deleted": a.total_deleted,
        "first_date": _date(a.first_date),
        "last_date": _date(a.last_date),
        "timespan_days": a.timespan_days,
        "bus_factor": a.bus_factor,
        "bus_factor_authors": a.bus_factor_authors,
        "longest_streak_days": a.longest_streak.days,
        "longest_streak_start": _date(a.longest_streak.start),
        "longest_streak_end": _date(a.longest_streak.end),
        "authors": [
            {
                "name": author.name,
                "email": author.email,
                "commits": author.commits,
                "added": author.added,
                "deleted": author.deleted,
                "files_touched": len(author.files_touched),
                "first_date": _date(author.first_date),
                "last_date": _date(author.last_date),
                "active_days": len(author.active_days),
            }
            for author in a.authors[:top]
        ],
        "files": [
            {
                "path": entry.path,
                "commits": entry.commits,
                "added": entry.added,
                "deleted": entry.deleted,
            }
            for entry in a.files[:top]
        ],
        "by_weekday": dict(zip(WEEKDAYS, a.by_weekday)),
        "by_hour": {f"{h:02d}": c for h, c in enumerate(a.by_hour) if c},
        "by_month": a.by_month,
    }
    return json.dumps(payload, indent=2) + "\n"
