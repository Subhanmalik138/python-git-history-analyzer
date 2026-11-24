"""End-to-end CLI tests against a real throwaway Git repository."""

import json
import os
import subprocess

import pytest

from gitstats.cli import main


def _git(repo, *args, env=None):
    full_env = dict(os.environ)
    full_env.update(env or {})
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env=full_env,
    )


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.name", "Dana")
    _git(tmp_path, "config", "user.email", "dana@example.com")
    # Three commits on three consecutive days.
    for day, name, body in [
        ("2026-02-02T09:00:00+00:00", "a.py", "print('one')\n"),
        ("2026-02-03T09:00:00+00:00", "a.py", "print('one')\nprint('two')\n"),
        ("2026-02-04T09:00:00+00:00", "b.py", "x = 1\n"),
    ]:
        (tmp_path / name).write_text(body)
        _git(tmp_path, "add", ".")
        _git(
            tmp_path,
            "commit",
            "-m",
            f"commit {day}",
            env={
                "GIT_AUTHOR_DATE": day,
                "GIT_COMMITTER_DATE": day,
            },
        )
    return tmp_path


def test_cli_reports_real_repo(repo, capsys):
    assert main([str(repo)]) == 0
    out = capsys.readouterr().out
    assert "Commits:        3" in out
    assert "Authors:        1" in out
    assert "Dana" in out
    assert "Longest streak: 3 days" in out
    assert "a.py" in out


def test_cli_json_output(repo, capsys):
    assert main([str(repo), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_commits"] == 3
    assert payload["longest_streak_days"] == 3
    assert payload["authors"][0]["name"] == "Dana"


def test_cli_since_filter(repo, capsys):
    assert main([str(repo), "--since", "2026-02-03"]) == 0
    assert "Commits:        2" in capsys.readouterr().out


def test_cli_author_filter_no_match(repo, capsys):
    assert main([str(repo), "--author", "Nobody"]) == 0
    assert "No commits found" in capsys.readouterr().out


def test_cli_from_file(repo, tmp_path, capsys):
    log = subprocess.run(
        ["git", "-C", str(repo), "log",
         "--format=%x1e%H%x1f%an%x1f%ae%x1f%aI%x1f%s%x1f%P", "--numstat"],
        check=True, capture_output=True, text=True,
    ).stdout
    dump = tmp_path / "history.log"
    dump.write_text(log)
    assert main(["--from-file", str(dump)]) == 0
    assert "Commits:        3" in capsys.readouterr().out


def test_cli_empty_repo(tmp_path, capsys):
    _git(tmp_path, "init", "-b", "main")
    assert main([str(tmp_path)]) == 0
    assert "No commits found" in capsys.readouterr().out


def test_cli_not_a_repo(tmp_path, capsys):
    assert main([str(tmp_path)]) == 1
    assert "not a git repository" in capsys.readouterr().err


def test_cli_bad_top_value(capsys):
    assert main(["--top", "0"]) == 2
    assert "--top must be at least 1" in capsys.readouterr().err
