"""Tests for scripts/release/next_version.py, which decides every release."""

from __future__ import annotations

import importlib.util
import subprocess  # nosec B404 - builds throwaway git repos with fixed arguments
import sys
from datetime import date
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release" / "next_version.py"
_spec = importlib.util.spec_from_file_location("next_version", _SCRIPT)
nv = importlib.util.module_from_spec(_spec)
sys.modules["next_version"] = nv
_spec.loader.exec_module(nv)


def commit(subject: str, body: str = "") -> nv.Commit:
    return nv.Commit("0" * 40, subject, body)


@pytest.mark.parametrize(
    ("subject", "body", "level"),
    [
        ("fix(cli): stop writing into site-packages (#92)", "", "patch"),
        ("perf: vectorise the mixer", "", "patch"),
        ("feat(typing): ship py.typed (#88)", "", "minor"),
        ("feat!: rename the import package", "", "major"),
        ("fix(api)!: drop the deprecated alias", "", "major"),
        ("refactor: split trim", "BREAKING CHANGE: trim() returns a dataclass", "major"),
        ("docs(guide): add the extension guide (#87)", "", "none"),
        ("ci: bump actions", "", "none"),
        ("build: bump the python group (#98)", "", "none"),
        ("Merge pull request #84 from guilyx/feat/demos", "", "none"),
    ],
)
def test_each_commit_type_maps_to_its_bump(subject, body, level):
    assert commit(subject, body).level == level


def test_breaking_only_counts_as_a_footer():
    """Prose that mentions breaking changes must not cut a major release."""
    body = "fix -> patch, feat -> minor, `!`/BREAKING CHANGE -> major. On each push"
    assert commit("ci(release): automate releases (#93)", body).level == "none"


def test_the_largest_bump_since_the_last_tag_wins():
    commits = [commit("docs: typo"), commit("fix: off-by-one"), commit("feat: new planner")]
    assert nv.release_level(commits) == "minor"
    assert nv.bump("minor", (2, 0, 0)) == (2, 1, 0)
    assert nv.bump("patch", (2, 1, 0)) == (2, 1, 1)
    assert nv.bump("major", (2, 1, 3)) == (3, 0, 0)


def test_nothing_releasable_means_no_release():
    assert nv.release_level([commit("docs: typo"), commit("ci: cache")]) == "none"
    assert nv.bump("none", (2, 0, 0)) is None
    assert nv.release_level([]) == "none"


def test_notes_group_by_type_and_link_pull_requests():
    notes = nv.render_notes(
        "2.1.0",
        [
            commit("feat(typing): ship py.typed (#88)"),
            commit("fix: stop the leak (#89)"),
            commit("ci: bump actions (#90)"),
            commit("feat!: drop python 3.11"),
        ],
        "guilyx/flybots",
        date(2026, 11, 3),
    )
    assert notes.startswith("## 2.1.0 (2026-11-03)")
    assert "### Breaking changes\n\n- drop python 3.11" in notes
    link = "https://github.com/guilyx/flybots/pull/88"
    assert f"- **typing:** ship py.typed ([#88]({link}))" in notes
    assert "### Fixed" in notes
    assert "bump actions" not in notes  # ci is not user-facing
    assert notes.index("### Breaking") < notes.index("### Added") < notes.index("### Fixed")


def test_hand_written_changelog_section_wins(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n## [2.1.0] - 2026-11-03\n\n### Added\n\n- curated\n\n"
        "## [2.0.0] - 2026-08-27\n\n- old\n"
    )
    assert nv.changelog_section(changelog, "2.1.0") == "### Added\n\n- curated\n"
    assert nv.changelog_section(changelog, "2.2.0") is None


def _git(repo: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603  # nosec B603
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def test_end_to_end_against_a_real_repository(tmp_path, monkeypatch, capsys):
    """Tags and first-parent history are read the way the workflow reads them."""
    _git(tmp_path, "init", "-q", "-b", "main")
    for subject in ("feat: first", "fix: second"):
        _git(tmp_path, "commit", "-q", "--allow-empty", "-m", subject)
    _git(tmp_path, "tag", "v1.4.2")
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "docs: words (#1)")
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "fix(cli): crash (#2)")
    monkeypatch.chdir(tmp_path)

    notes = tmp_path / "notes.md"
    assert nv.main(["--notes", str(notes), "--repo", "o/r"]) == 0
    assert capsys.readouterr().out.strip() == "version=1.4.3"
    assert "**cli:** crash ([#2](https://github.com/o/r/pull/2))" in notes.read_text()

    _git(tmp_path, "tag", "v1.4.3")
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "chore: tidy")
    assert nv.main([]) == 0
    assert capsys.readouterr().out.strip() == "version="
