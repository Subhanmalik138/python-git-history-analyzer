from datetime import datetime, timezone

from gitstats.models import Commit, FileChange
from gitstats.stats import analyse


def _commit(sha, name, email, iso, files, parents=()):
    return Commit(
        sha=sha,
        author_name=name,
        author_email=email,
        date=datetime.fromisoformat(iso),
        subject=sha,
        parents=parents,
        changes=tuple(FileChange(p, a, d) for p, a, d in files),
    )


def _sample_commits():
    # Alice: 3 commits over Jan 1-3 (a 3-day streak), Bob: 2 commits.
    return [
        _commit("c1", "Alice", "alice@x", "2026-01-01T09:00:00+00:00",
                [("a.py", 10, 2), ("b.py", 5, 0)]),
        _commit("c2", "Alice", "alice@x", "2026-01-02T10:00:00+00:00",
                [("a.py", 3, 1)]),
        _commit("c3", "Bob", "bob@x", "2026-01-02T15:00:00+00:00",
                [("b.py", 20, 5)], parents=("c1", "c2")),
        _commit("c4", "Alice", "alice@x", "2026-01-03T09:00:00+00:00",
                [("a.py", 1, 0)]),
        _commit("c5", "Bob", "bob@x", "2026-01-10T09:00:00+00:00",
                [("c.py", 7, 7)]),
    ]


def test_overview_totals():
    a = analyse(_sample_commits())
    assert a.total_commits == 5
    assert a.total_authors == 2
    assert a.total_files == 3
    assert a.total_added == 10 + 5 + 3 + 20 + 1 + 7
    assert a.total_deleted == 2 + 1 + 5 + 7
    assert a.merge_commits == 1
    assert a.timespan_days == 10  # Jan 1 .. Jan 10 inclusive


def test_author_ranking_and_stats():
    a = analyse(_sample_commits())
    alice, bob = a.authors
    assert (alice.name, alice.commits) == ("Alice", 3)
    assert (bob.name, bob.commits) == ("Bob", 2)
    assert alice.added == 10 + 5 + 3 + 1
    assert alice.files_touched == {"a.py", "b.py"}
    assert len(alice.active_days) == 3
    assert bob.deleted == 5 + 7


def test_file_churn_ranking():
    a = analyse(_sample_commits())
    assert a.files[0].path == "a.py"
    assert a.files[0].commits == 3
    assert a.files[1].path == "b.py"
    assert a.files[2].path == "c.py"


def test_bus_factor():
    # Alice alone holds 3 of 5 commits (>= 50%), so the factor is 1.
    a = analyse(_sample_commits())
    assert a.bus_factor == 1
    assert a.bus_factor_authors == ["Alice"]


def test_bus_factor_needs_two_when_split_evenly():
    # 5 commits split 2/2/1: no single author reaches the 50% threshold.
    commits = [
        _commit("x1", "Ann", "ann@x", "2026-01-01T09:00:00+00:00", [("a.py", 1, 0)]),
        _commit("x2", "Ann", "ann@x", "2026-01-02T09:00:00+00:00", [("a.py", 1, 0)]),
        _commit("x3", "Bo", "bo@x", "2026-01-03T09:00:00+00:00", [("a.py", 1, 0)]),
        _commit("x4", "Bo", "bo@x", "2026-01-04T09:00:00+00:00", [("a.py", 1, 0)]),
        _commit("x5", "Cy", "cy@x", "2026-01-05T09:00:00+00:00", [("a.py", 1, 0)]),
    ]
    a = analyse(commits)
    assert a.bus_factor == 2
    assert a.bus_factor_authors == ["Ann", "Bo"]


def test_streaks():
    a = analyse(_sample_commits())
    assert a.longest_streak.days == 3
    assert str(a.longest_streak.start) == "2026-01-01"
    assert str(a.longest_streak.end) == "2026-01-03"
    assert a.author_streaks[0] == ("Alice", a.longest_streak)
    assert a.author_streaks[1][0] == "Bob"
    assert a.author_streaks[1][1].days == 1


def test_weekday_hour_and_month_buckets():
    a = analyse(_sample_commits())
    assert sum(a.by_weekday) == 5
    assert sum(a.by_hour) == 5
    assert a.by_hour[9] == 3  # 09:00 commits: c1, c4, c5
    assert a.by_month == {"2026-01": 5}


def test_empty_history():
    a = analyse([])
    assert a.total_commits == 0
    assert a.bus_factor == 0
    assert a.longest_streak.days == 0
    assert a.authors == [] and a.files == []


def test_binary_files_excluded_from_line_counts():
    commits = [
        Commit(
            sha="b1",
            author_name="Al",
            author_email="al@x",
            date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            subject="bin",
            changes=(FileChange("img.png", 0, 0, binary=True),),
        )
    ]
    a = analyse(commits)
    assert a.total_added == 0 and a.total_deleted == 0
    assert a.total_files == 1
