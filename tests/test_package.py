# Erwin Lejeune - 2026-02-16
"""Smoke test: verify the package is importable and reports its version."""

from importlib.metadata import version


def test_import():
    import flybots

    assert flybots.__version__


def test_version_matches_the_installed_distribution():
    """``__version__`` has to be the version that was actually installed.

    It used to be a literal repeated in `pyproject.toml`, here, and in this
    test, so the test compared one hard-coded string to another and could
    not notice them drifting apart. A `v1.0.0` tag against a pyproject
    still reading 0.2.0 is what that drift costs at release time.
    """
    import flybots

    assert flybots.__version__ == version("flybots")


def test_citation_version_matches_the_package():
    """``CITATION.cff`` is the one other place the version has to live.

    GitHub's "Cite this repository" button and every reference manager read
    it, so a citation pinned to an old version sends readers to code that
    no longer matches what they are citing. It cannot be derived at build
    time the way ``__version__`` is, so this test is what keeps it honest.
    """
    from pathlib import Path

    cff = (Path(__file__).resolve().parents[1] / "CITATION.cff").read_text()
    cited = next(
        # release-please bumps the line it finds the x-release-please-version
        # marker on, so the value carries a trailing YAML comment.
        line.split(":", 1)[1].split("#", 1)[0].strip()
        for line in cff.splitlines()
        if line.startswith("version:")
    )
    assert cited == version("flybots"), (
        f"CITATION.cff says {cited}, the package is {version('flybots')}: "
        "release-please bumps both; if they disagree, check the "
        "x-release-please-version marker in CITATION.cff."
    )


def test_ships_the_py_typed_marker():
    """PEP 561: without it, type checkers treat every flybots import as Any.

    pyproject.toml advertises ``Typing :: Typed``; this keeps that true.
    """
    from importlib.resources import files

    assert files("flybots").joinpath("py.typed").is_file()
