"""Tests for the GIF recorder every simulation uses."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from flybots.visualization import SimAnimator


@pytest.fixture
def figure():
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.plot([0, 1], [0, 1])
    yield fig
    plt.close(fig)


def _record(anim: SimAnimator) -> None:
    anim.animate(lambda _frame: None, n_frames=3)


def test_adopts_a_figure_passed_to_the_constructor(tmp_path, figure):
    anim = SimAnimator("ctor", out_dir=tmp_path, figure=figure)
    assert anim.figure is figure
    _record(anim)
    assert anim.save().read_bytes()[:6] == b"GIF89a"


def test_adopts_a_figure_assigned_after_construction(tmp_path, figure):
    anim = SimAnimator("setter", out_dir=tmp_path)
    anim.figure = figure
    _record(anim)
    assert anim.save().read_bytes()[:6] == b"GIF89a"


def test_animating_without_a_figure_says_how_to_provide_one(tmp_path):
    anim = SimAnimator("none", out_dir=tmp_path)
    with pytest.raises(RuntimeError, match="figure="):
        _record(anim)


@pytest.mark.parametrize("variable", ["FLYBOTS_SKIP_GIF", "UAV_SIM_SKIP_GIF"])
def test_skip_switch_writes_nothing(tmp_path, figure, monkeypatch, variable):
    monkeypatch.delenv("FLYBOTS_SKIP_GIF", raising=False)
    monkeypatch.delenv("UAV_SIM_SKIP_GIF", raising=False)
    monkeypatch.setenv(variable, "1")
    anim = SimAnimator("skipped", out_dir=tmp_path, figure=figure)
    _record(anim)
    out = anim.save()
    assert out == tmp_path / "skipped.gif"
    assert not out.exists()
