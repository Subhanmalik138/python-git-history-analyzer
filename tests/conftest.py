"""Shared fixtures: a small synthetic git log in the collector's format."""

import pytest

RS = "\x1e"
FS = "\x1f"


def record(sha, name, email, iso, subject, parents, numstat=()):
    header = FS.join([sha, name, email, iso, subject, parents])
    body = "\n".join(numstat)
    return RS + header + ("\n" + body if body else "")


@pytest.fixture
def sample_log():
    return "\n".join(
        [
            record(
                "aaa111",
                "Alice",
                "alice@example.com",
                "2026-01-06T10:00:00+00:00",
                "Add README",
                "",
                ["12\t0\tREADME.md"],
            ),
            record(
                "bbb222",
                "Bob",
                "bob@example.com",
                "2026-01-07T14:30:00+00:00",
                "Merge branch feature",
                "aaa111 ccc333",
                ["5\t2\tsrc/app.py", "-\t-\tassets/logo.png"],
            ),
            record(
                "ccc333",
                "Alice",
                "alice@example.com",
                "2026-01-06T11:00:00+00:00",
                "Rename module",
                "",
                ["3\t1\tsrc/{old.py => new.py}"],
            ),
        ]
    )
