import pytest

from gitstats.parser import LogParseError, parse_log


def test_parses_all_commits(sample_log):
    commits = parse_log(sample_log)
    assert len(commits) == 3
    assert [c.sha for c in commits] == ["aaa111", "bbb222", "ccc333"]


def test_parses_header_fields(sample_log):
    first = parse_log(sample_log)[0]
    assert first.author_name == "Alice"
    assert first.author_email == "alice@example.com"
    assert first.subject == "Add README"
    assert first.date.year == 2026 and first.date.day == 6
    assert first.parents == ()


def test_merge_detection(sample_log):
    merge = parse_log(sample_log)[1]
    assert merge.is_merge
    assert merge.parents == ("aaa111", "ccc333")
    assert not parse_log(sample_log)[0].is_merge


def test_numstat_and_binary(sample_log):
    merge = parse_log(sample_log)[1]
    app, logo = merge.changes
    assert (app.path, app.added, app.deleted, app.binary) == ("src/app.py", 5, 2, False)
    assert logo.path == "assets/logo.png"
    assert logo.binary and logo.added == 0 and logo.deleted == 0


def test_rename_normalised_to_new_path(sample_log):
    renamed = parse_log(sample_log)[2].changes[0]
    assert renamed.path == "src/new.py"
    assert (renamed.added, renamed.deleted) == (3, 1)


def test_empty_log_parses_to_empty_list():
    assert parse_log("") == []
    assert parse_log("\n") == []


def test_malformed_header_raises():
    with pytest.raises(LogParseError):
        parse_log("\x1eonly-one-field")


def test_malformed_numstat_raises():
    bad = "\x1e" + "\x1f".join(
        ["abc", "A", "a@x", "2026-01-01T00:00:00+00:00", "s", ""]
    )
    with pytest.raises(LogParseError):
        parse_log(bad + "\nnot-a-numstat-line")


def test_bad_date_raises():
    bad = "\x1e" + "\x1f".join(["abc", "A", "a@x", "yesterday", "s", ""])
    with pytest.raises(LogParseError):
        parse_log(bad)
