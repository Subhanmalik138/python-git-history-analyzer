# gitstats — Git History Analyzer CLI

Turn any local Git repository's history into a readable report: who did the
work, which files churn the most, when the team actually commits, how
concentrated the knowledge is, and who keeps the longest streak.

```text
$ gitstats ~/projects/my-app

Git history report
========================================
Commits:        342 (18 merges)
Authors:        7
Files touched:  96
Lines:          +18420 / -7311
Timespan:       2025-03-04 to 2026-11-20 (626 days)
Bus factor:     2 (Ana, Ben)
Longest streak: 14 days (2026-04-06 to 2026-04-19)

Top authors (top 10)
----------------------------------------
Ana                      148 commits (43.3%)  +8211/-2904  74 files
...
```

## Installation

Requires Python 3.10+ and Git. No third-party dependencies.

```bash
pip install .
gitstats --help
```

Or run it without installing:

```bash
PYTHONPATH=src python -m gitstats.cli ~/projects/my-app
```

## Usage

```bash
gitstats [PATH] [options]
```

| Option | What it does |
| --- | --- |
| `PATH` | Repository to analyse (default: current directory) |
| `--since DATE` | Only commits after DATE (e.g. `2026-01-01`, `3 months ago`) |
| `--until DATE` | Only commits before DATE |
| `--author NAME` | Only commits by NAME (substring match, like `git log`) |
| `--top N` | How many authors/files to list (default: 10) |
| `--json` | Emit the full report as JSON instead of text |
| `--from-file FILE` | Analyse a saved `git log --numstat` dump instead of running Git |

Examples:

```bash
# This quarter's work only
gitstats . --since 2026-10-01 --json > q4-report.json

# One contributor's footprint
gitstats . --author "Ana" --top 5

# Analyse a log captured on another machine
git log --format='%x1e%H%x1f%an%x1f%ae%x1f%aI%x1f%s%x1f%P' --numstat > history.log
gitstats --from-file history.log
```

## What the report measures

- **Overview** — commits, merges, authors, files touched, lines added/removed,
  and the timespan the history covers.
- **Top authors** — commits, share of history, lines changed, files touched.
- **Most-changed files** — the churn hotspots; files that appear in many
  commits are usually the ones worth refactoring or documenting first.
- **Commit rhythms** — commits by weekday, by hour, and by month, so you can
  see when the team actually works.
- **Bus factor** — the smallest number of top authors whose commits cover at
  least 50% of the history. A bus factor of 1 means one person leaving takes
  half the project's knowledge with them.
- **Streaks** — the longest run of consecutive days with at least one commit,
  overall and per author.

## Design decisions

1. **Shell out to Git, don't parse `.git` by hand.** Git's on-disk format is
   an implementation detail; `git log` is the stable interface, and it keeps
   the tool correct for worktrees, shallow clones, and future formats.
2. **A machine-readable log format.** The parser asks Git for records
   separated by `\x1e` and fields by `\x1f` — control characters that cannot
   appear in a commit subject — so parsing never has to guess where a field
   ends, the way regexes over the default pretty format do.
3. **Parsing, statistics, and rendering are separate modules.** The parser
   produces plain dataclasses, `stats` computes pure numbers from them, and
   `report` only formats. That split is what lets the test suite cover the
   statistics without ever creating a repository.
4. **Renames are attributed to the new path.** `--numstat` reports a rename
   as `old => new`; counting it under the new name keeps churn attached to
   the file that exists now.

## Project layout

```text
src/gitstats/
  models.py     # Commit / FileChange dataclasses
  parser.py     # git log --numstat -> Commit objects
  collector.py  # runs `git log`, handles empty/non-repo cases
  stats.py      # author/file/rhythm/bus-factor/streak aggregation
  report.py     # text and JSON rendering
  cli.py        # argparse entry point
tests/
  test_parser.py  test_stats.py  test_report.py  test_cli.py
```

## Running the tests

```bash
python -m pytest
```

30 tests, including end-to-end runs against real repositories created in
temporary directories.

## License

MIT — see [LICENSE](LICENSE).
