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


def test_citation_does_not_pin_a_version():
    """``CITATION.cff`` must not carry a version.

    The version is the git tag, read at build time; releases are cut on merge
    without committing anything to main. A version written in CITATION.cff
    would therefore be stale after the next release, and GitHub's "Cite this
    repository" would send readers to the wrong code. citing.md tells readers
    to cite the version they used instead.
    """
    from pathlib import Path

    cff = (Path(__file__).resolve().parents[1] / "CITATION.cff").read_text()
    pinned = [line for line in cff.splitlines() if line.startswith(("version:", "date-released:"))]
    assert not pinned, f"CITATION.cff pins {pinned}; the version lives in git tags only"


def test_ships_the_py_typed_marker():
    """PEP 561: without it, type checkers treat every flybots import as Any.

    pyproject.toml advertises ``Typing :: Typed``; this keeps that true.
    """
    from importlib.resources import files

    assert files("flybots").joinpath("py.typed").is_file()
