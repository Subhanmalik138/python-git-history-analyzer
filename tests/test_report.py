import json

from gitstats.parser import parse_log
from gitstats.report import render_json, render_text
from gitstats.stats import analyse


def test_text_report_sections(sample_log):
    text = render_text(analyse(parse_log(sample_log)))
    assert "Git history report" in text
    assert "Commits:        3 (1 merges)" in text
    assert "Authors:        2" in text
    assert "Bus factor:     1 (Alice)" in text
    assert "Top authors" in text and "Alice" in text
    assert "Most-changed files" in text
    assert "Commits by weekday" in text
    assert "Commits by hour" in text


def test_text_report_empty_history():
    assert render_text(analyse([])).startswith("No commits found")


def test_json_report_round_trip(sample_log):
    payload = json.loads(render_json(analyse(parse_log(sample_log))))
    assert payload["total_commits"] == 3
    assert payload["merge_commits"] == 1
    assert payload["total_authors"] == 2
    assert payload["bus_factor"] == 1
    assert payload["authors"][0]["name"] == "Alice"
    assert payload["authors"][0]["commits"] == 2
    # All files have 1 commit each, so ranking falls back to lines changed.
    assert payload["files"][0]["path"] == "README.md"
    assert payload["files"][0]["added"] == 12
    assert sum(payload["by_weekday"].values()) == 3
    assert payload["by_month"] == {"2026-01": 3}


def test_top_limits_lists(sample_log):
    payload = json.loads(render_json(analyse(parse_log(sample_log)), top=1))
    assert len(payload["authors"]) == 1
    assert len(payload["files"]) == 1
