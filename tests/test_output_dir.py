"""Where simulation output lands: the checkout, an override, never site-packages."""

from __future__ import annotations

from pathlib import Path

import pytest

from flybots._output import OUTPUT_DIR_ENV, resolve_output_dir
from flybots.logging import SimLogger
from flybots.visualization import SimAnimator


@pytest.fixture(autouse=True)
def _no_override(monkeypatch):
    monkeypatch.delenv(OUTPUT_DIR_ENV, raising=False)


def test_a_source_checkout_writes_next_to_the_simulation(tmp_path):
    sim = tmp_path / "src" / "flybots" / "simulations" / "x" / "pid_hover"
    assert resolve_output_dir(sim) == sim


def test_an_installed_copy_writes_under_the_working_directory(tmp_path, monkeypatch):
    sim = tmp_path / "lib" / "python3.12" / "site-packages" / "flybots" / "simulations" / "x"
    sim = sim / "pid_hover"
    monkeypatch.chdir(tmp_path)
    assert resolve_output_dir(sim) == tmp_path / "flybots-output" / "pid_hover"


def test_the_override_wins_and_keeps_one_folder_per_simulation(tmp_path, monkeypatch):
    monkeypatch.setenv(OUTPUT_DIR_ENV, str(tmp_path / "out"))
    assert resolve_output_dir(Path("/anything/pid_hover")) == tmp_path / "out" / "pid_hover"


def test_logger_and_animator_both_honour_it(tmp_path, monkeypatch):
    monkeypatch.setenv(OUTPUT_DIR_ENV, str(tmp_path))
    logger = SimLogger("demo", out_dir="/read-only/site-packages/demo")
    assert logger.save() == tmp_path / "demo" / "demo_log.json"
    assert SimAnimator("demo", out_dir="/elsewhere/demo").out_dir == tmp_path / "demo"


def test_cli_out_dir_redirects_a_real_run(tmp_path, monkeypatch, capsys):
    """`flybots run --out-dir` writes there, says so, and leaves the package alone."""
    from flybots.cli import catalogue
    from flybots.cli.main import main

    monkeypatch.setenv("FLYBOTS_SKIP_GIF", "1")
    # main() sets the variable in-process; registering it here first means
    # monkeypatch restores it afterwards instead of leaking it.
    monkeypatch.setenv(OUTPUT_DIR_ENV, "unset-by-test")
    entry = catalogue.resolve("visual_servoing_fixed")[0]
    package_log = entry.directory / "visual_servoing_fixed_log.json"
    before = package_log.stat().st_mtime_ns if package_log.exists() else None

    assert main(["run", "visual_servoing_fixed", "--out-dir", str(tmp_path)]) == 0
    assert (tmp_path / "visual_servoing_fixed" / "visual_servoing_fixed_log.json").is_file()
    after = package_log.stat().st_mtime_ns if package_log.exists() else None
    assert after == before
