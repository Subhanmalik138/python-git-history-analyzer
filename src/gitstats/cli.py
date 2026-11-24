"""Command-line interface for gitstats.

Usage::

    gitstats [PATH] [--since DATE] [--until DATE] [--author NAME]
             [--top N] [--json] [--from-file FILE]

``PATH`` defaults to the current directory. ``--from-file`` analyses a
previously saved ``git log`` dump instead of running Git, which is handy
for offline analysis and for the test suite.
"""

from __future__ import annotations

import argparse
import sys

from .collector import GitError, collect_commits, collect_from_file
from .report import render_json, render_text
from .stats import analyse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gitstats",
        description=(
            "Analyse a Git repository's history: authors, file churn, "
            "commit rhythms, bus factor and streaks."
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="path to the repository (default: current directory)",
    )
    parser.add_argument("--since", metavar="DATE", help="only commits after DATE")
    parser.add_argument("--until", metavar="DATE", help="only commits before DATE")
    parser.add_argument("--author", metavar="NAME", help="only commits by NAME")
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        metavar="N",
        help="how many authors/files to list (default: 10)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument(
        "--from-file",
        metavar="FILE",
        help="read saved `git log --numstat` output instead of running git",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.top < 1:
        print("error: --top must be at least 1", file=sys.stderr)
        return 2
    try:
        if args.from_file:
            commits = collect_from_file(args.from_file)
        else:
            commits = collect_commits(
                args.path, since=args.since, until=args.until, author=args.author
            )
    except GitError as exc:
        print(f"gitstats: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"gitstats: cannot read {args.from_file}: {exc}", file=sys.stderr)
        return 1

    analysis = analyse(commits)
    if args.json:
        print(render_json(analysis, top=args.top), end="")
    else:
        print(render_text(analysis, top=args.top), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
