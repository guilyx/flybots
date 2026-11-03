#!/usr/bin/env python3
# Erwin Lejeune - 2026-11-03
"""Decide the next flybots release from the commits merged since the last tag.

Pull requests are squash-merged and their titles are Conventional Commits
(``pr-title.yml`` enforces it), so each merge is one commit on ``main`` whose
subject says what kind of change it is:

    fix: / perf:                      -> patch   2.0.0 -> 2.0.1
    feat:                             -> minor   2.0.0 -> 2.1.0
    feat!: / a "BREAKING CHANGE:" footer -> major 2.0.0 -> 3.0.0
    docs: test: ci: build: chore: ... -> no release on their own

The bump is the largest one among every commit since the last ``vX.Y.Z`` tag,
so a docs-only merge releases nothing and the next ``fix`` releases both.

The version is never written into the repository: it is the git tag, and the
package reads it at build time (hatch-vcs). That is what lets a release happen
on merge without pushing a commit to the protected ``main`` branch.

Usage, from a checkout with full history and tags::

    python3 scripts/release/next_version.py --notes release-notes.md

prints ``version=X.Y.Z`` (empty when nothing is releasable) for
``$GITHUB_OUTPUT`` and writes the release notes to the given file.
Stdlib only, so it runs before any dependency is installed.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
SUBJECT = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?: (?P<text>.+)$")
BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE: ", re.MULTILINE)
PR_SUFFIX = re.compile(r"\s*\(#(\d+)\)$")

PATCH_TYPES = {"fix", "perf"}
MINOR_TYPES = {"feat"}
LEVELS = {"none": 0, "patch": 1, "minor": 2, "major": 3}

#: Release-note sections, in order. Types not listed never appear in notes.
SECTIONS = (
    ("Breaking changes", None),
    ("Added", "feat"),
    ("Fixed", "fix"),
    ("Performance", "perf"),
    ("Documentation", "docs"),
)


@dataclass(frozen=True)
class Commit:
    sha: str
    subject: str
    body: str

    @property
    def parsed(self) -> re.Match[str] | None:
        return SUBJECT.match(self.subject)

    @property
    def breaking(self) -> bool:
        match = self.parsed
        return bool(match and match["bang"]) or bool(BREAKING_FOOTER.search(self.body))

    @property
    def level(self) -> str:
        match = self.parsed
        if match is None:
            return "none"
        if self.breaking:
            return "major"
        if match["type"] in MINOR_TYPES:
            return "minor"
        if match["type"] in PATCH_TYPES:
            return "patch"
        return "none"


def bump(level: str, current: tuple[int, int, int]) -> tuple[int, int, int] | None:
    """Apply a bump level to ``(major, minor, patch)``; ``None`` when ``level`` is none."""
    major, minor, patch = current
    if level == "major":
        return major + 1, 0, 0
    if level == "minor":
        return major, minor + 1, 0
    if level == "patch":
        return major, minor, patch + 1
    return None


def release_level(commits: list[Commit]) -> str:
    """The largest bump any of ``commits`` asks for."""
    return max((c.level for c in commits), key=LEVELS.__getitem__, default="none")


def render_notes(version: str, commits: list[Commit], repo: str | None, today: date) -> str:
    """Group conventional commits into Keep-a-Changelog style release notes."""
    lines = [f"## {version} ({today.isoformat()})", ""]
    for title, wanted in SECTIONS:
        entries = []
        for commit in commits:
            match = commit.parsed
            if match is None:
                continue
            if wanted is None and not commit.breaking:
                continue
            if wanted is not None and (match["type"] != wanted or commit.breaking):
                continue
            text = match["text"]
            if match["scope"]:
                text = f"**{match['scope']}:** {text}"
            pr = PR_SUFFIX.search(text)
            if pr and repo:
                link = f"https://github.com/{repo}/pull/{pr[1]}"
                text = PR_SUFFIX.sub(f" ([#{pr[1]}]({link}))", text)
            entries.append(f"- {text}")
        if entries:
            lines += [f"### {title}", "", *entries, ""]
    return "\n".join(lines).rstrip() + "\n"


def changelog_section(changelog: Path, version: str) -> str | None:
    """Hand-written notes for ``version`` in CHANGELOG.md, if a maintainer wrote any."""
    if not changelog.is_file():
        return None
    text = changelog.read_text()
    heading = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n", text, re.MULTILINE)
    if heading is None:
        return None
    rest = text[heading.end() :]
    following = re.search(r"^## \[", rest, re.MULTILINE)
    body = rest[: following.start()] if following else rest
    return body.strip() + "\n" if body.strip() else None


# -- git ------------------------------------------------------------------------------


def _git(*args: str) -> str:
    # Resolved to an absolute path so the command cannot be shadowed through
    # the working directory; the arguments are fixed by this module.
    git = shutil.which("git")
    if git is None:
        raise SystemExit("git is not on PATH")
    return subprocess.run(  # noqa: S603  # nosec B603
        [git, *args], check=True, capture_output=True, text=True
    ).stdout


def latest_tag() -> tuple[str, tuple[int, int, int]] | None:
    """The highest ``vX.Y.Z`` tag reachable from HEAD."""
    tags = _git("tag", "--merged", "HEAD", "--list", "v*").split()
    versions = [(t, tuple(map(int, m.groups()))) for t in tags if (m := TAG_PATTERN.match(t))]
    return max(versions, key=lambda item: item[1]) if versions else None  # type: ignore[return-value]


def commits_since(tag: str | None) -> list[Commit]:
    """Commits on the first-parent line of HEAD since ``tag``, oldest first."""
    span = f"{tag}..HEAD" if tag else "HEAD"
    raw = _git("log", "--first-parent", "--reverse", "--format=%H%x1f%s%x1f%b%x1e", span)
    commits = []
    for record in raw.split("\x1e"):
        if record.strip():
            sha, subject, body = record.strip("\n").split("\x1f")
            commits.append(Commit(sha, subject.strip(), body))
    return commits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--notes", type=Path, help="write release notes here")
    parser.add_argument("--repo", help="owner/name, for pull request links")
    parser.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    args = parser.parse_args(argv)

    found = latest_tag()
    tag, current = found if found else (None, (0, 0, 0))
    commits = commits_since(tag)
    level = release_level(commits)
    nxt = bump(level, current)

    summary = f"last release: {tag or 'none'}; commits since: {len(commits)}; bump: {level}"
    print(summary, file=sys.stderr)
    version = ".".join(map(str, nxt)) if nxt else ""
    print(f"version={version}")

    if args.notes and version:
        notes = changelog_section(args.changelog, version) or render_notes(
            version, commits, args.repo, date.today()
        )
        args.notes.write_text(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
