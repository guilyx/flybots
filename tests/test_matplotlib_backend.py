"""flybots must never change the caller's matplotlib backend.

The backend is process-wide state that belongs to whoever imported the
library. ``flybots.visualization`` used to call ``matplotlib.use("Agg")`` at
import time, and the gym's render helpers did it on every call. In a
notebook that silently stopped inline plots and ``plt.show()`` for the rest
of the session -- including ``plot_trajectory(..., show=True)`` from this
very package -- the moment anything visual was imported.

Every check runs in a fresh interpreter with the backend preset to ``svg``.
The backend is global, and the simulation tests in this suite select Agg on
purpose, so an in-process check would pass or fail depending on test order.
``svg`` stands in for a user's own choice: it is not Agg, and it needs no
display.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import pytest

_USER_BACKEND = "svg"


def _run(code: str) -> str:
    """Run ``code`` in a fresh interpreter under the user's backend.

    Returns the last line of stdout, which each snippet uses to report the
    backend -- some of the code under test prints progress before it.
    """
    env = {**os.environ, "MPLBACKEND": _USER_BACKEND}
    result = subprocess.run(  # noqa: S603  # nosec B603
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip().splitlines()[-1]


@pytest.mark.parametrize(
    "module",
    [
        "flybots",
        "flybots.visualization",
        "flybots.visualization.animator",
        "flybots.visualization.plotting",
        "flybots.visualization.three_panel",
        "flybots.visualization.costmap_viz",
        "flybots.visualization.sensor_viz",
        "flybots.visualization.vehicle_artists",
        "flybots.visualization.data_panel",
        "flybots.gym",
        "flybots.gym.render",
    ],
)
def test_importing_leaves_the_backend_alone(module: str) -> None:
    backend = _run(
        f"""
        import matplotlib
        import {module}
        print(matplotlib.get_backend())
        """
    )
    assert backend.lower() == _USER_BACKEND


def test_render_learning_curve_leaves_the_backend_alone(tmp_path) -> None:
    out = tmp_path / "curve.png"
    backend = _run(
        f"""
        import matplotlib
        from flybots.gym.render import render_learning_curve
        history = [
            {{"generation": g, "mean_return": g, "elite_return": g + 1.0,
              "mean_policy_return": g + 0.5}}
            for g in range(5)
        ]
        render_learning_curve(history, {str(out)!r})
        print(matplotlib.get_backend())
        """
    )
    assert backend.lower() == _USER_BACKEND
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_episode_leaves_the_backend_alone(tmp_path) -> None:
    out = tmp_path / "episode.gif"
    backend = _run(
        f"""
        import matplotlib
        import numpy as np
        from types import SimpleNamespace
        from flybots.gym.render import render_episode
        t = np.linspace(0.0, 1.0, 12)[:, None]
        trajectories = [np.hstack([t, t, 1.0 + t]), np.hstack([-t, t, 1.0 + t])]
        render_episode(SimpleNamespace(goal=np.array([1.0, 1.0, 2.0])),
                       trajectories, {str(out)!r}, fps=10)
        print(matplotlib.get_backend())
        """
    )
    assert backend.lower() == _USER_BACKEND
    assert out.read_bytes()[:6] in (b"GIF87a", b"GIF89a")


def test_sim_animator_saves_without_forcing_agg(tmp_path) -> None:
    """The animator used to force Agg to *be able* to save. It does not need to.

    Saving goes through Pillow's writer, which rasterises each frame itself,
    so a GIF comes out under a non-raster backend too.
    """
    backend = _run(
        f"""
        import matplotlib
        from pathlib import Path
        from flybots.visualization import SimAnimator
        anim = SimAnimator("backend_probe", out_dir=Path({str(tmp_path)!r}))
        fig, ax = anim.figure_3d("probe")
        (line,) = ax.plot([], [], [])
        def draw(frame):
            line.set_data([0, frame], [0, frame])
            line.set_3d_properties([0, frame])
        anim.animate(draw, n_frames=4)
        anim.save()
        print(matplotlib.get_backend())
        """
    )
    assert backend.lower() == _USER_BACKEND
    gifs = list(tmp_path.glob("backend_probe*.gif"))
    assert gifs, "SimAnimator did not write a GIF"
    assert gifs[0].read_bytes()[:6] in (b"GIF87a", b"GIF89a")
