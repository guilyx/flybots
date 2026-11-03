# Build on flybots

flybots is meant to be built on. The vehicles, sensors, estimators and
controllers are there so that the next algorithm — the one you are reading
a paper about — takes an afternoon to try instead of a week, and so that
what you end up with is something another person can run, watch and
understand.

This page walks through adding one algorithm end to end: the
implementation, the tests, a runnable simulation that `flybots run`
discovers, and the docs page. The example is deliberately small, an
altitude-hold controller, so that what you see is the framework rather
than the algorithm.

## Two ways to build on it

**In your own project.** `pip install flybots` and import what you need.
Every vehicle steps the same way, so a controller is a function from state
to command, and a simulation is a loop:

```python
import numpy as np
from flybots.vehicles.multirotor.quadrotor import Quadrotor

quad = Quadrotor()
quad.reset(position=np.zeros(3))
for _ in range(2000):
    wrench = my_controller(quad.state)   # [thrust, tau_x, tau_y, tau_z]
    quad.step(wrench, dt=0.005)
```

That is all you need to experiment. Nothing below is required for it.

**As a contribution.** If you want the algorithm to join the
[atlas](/simulations/), to be listed by `flybots list` and to run with
`flybots run`, it lives in this repository and follows the steps below.
They are the same steps the existing 40-odd simulations follow, and the
test suite checks most of them for you.

## 1. The algorithm

Put it in the package for its area — `path_tracking/`, `estimation/`,
`path_planning/`, … (the [architecture](./architecture) page lists them).
Keep it pure numerics: it takes arrays and returns arrays. No plotting, no
file output, no imports from `flybots.simulations` or
`flybots.visualization`. Layers only depend downward, which is what lets
someone reuse your controller in a project of their own.

The module docstring says what the algorithm does and where it comes from:

```python
# src/flybots/path_tracking/altitude_hold.py
"""Altitude hold: a PD law on height with gravity feed-forward.

The commanded collective thrust is

    T = m (g + kp (z_ref - z) - kd z_dot)

which, with the attitude held level, makes height a damped second-order
system with natural frequency sqrt(kp) and damping kd / (2 sqrt(kp)).

Reference: R. Mahony, V. Kumar and P. Corke, "Multirotor Aerial Vehicles:
Modeling, Estimation, and Control of Quadrotor," IEEE Robotics & Automation
Magazine 19(3), 2012.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

__all__ = ["AltitudeHold"]


@dataclass
class AltitudeHold:
    """Collective-thrust altitude controller for a multirotor."""

    mass: float
    gravity: float = 9.81
    kp: float = 4.0
    kd: float = 4.0

    def wrench(self, state: NDArray[np.floating], z_ref: float) -> NDArray[np.floating]:
        """Return ``[T, 0, 0, 0]`` for a 12-element multirotor state."""
        z, z_dot = state[2], state[8]
        accel = self.kp * (z_ref - z) - self.kd * z_dot
        return np.array([self.mass * (self.gravity + accel), 0.0, 0.0, 0.0])
```

Write it from scratch. Wrapping an external solver hides exactly the part
a reader came to see.

::: tip State layout
A multirotor state is `[x, y, z, φ, θ, ψ, vx, vy, vz, p, q, r]` in ENU,
and the command is the body wrench `[T, τx, τy, τz]`. The
[conventions](./conventions) page has the frames for every vehicle.
:::

## 2. Tests that pin the behaviour

A test is worth having if it would fail on a wrong implementation. For a
controller, that means asserting on what the aircraft does, not on the
shape of what the function returns:

```python
# tests/test_altitude_hold.py
import numpy as np
import pytest

from flybots.path_tracking.altitude_hold import AltitudeHold
from flybots.vehicles.multirotor.quadrotor import Quadrotor


def _fly(controller, quad, z_ref, seconds, dt=0.005):
    heights = []
    for _ in range(int(seconds / dt)):
        quad.step(controller.wrench(quad.state, z_ref), dt)
        heights.append(quad.state[2])
    return np.array(heights)


def test_settles_on_the_reference_without_overshoot():
    """kp = kd = 4 is critically damped: it must arrive, and not overshoot."""
    quad = Quadrotor()
    quad.reset(position=np.zeros(3))
    controller = AltitudeHold(mass=quad.params.mass, gravity=quad.params.gravity)
    heights = _fly(controller, quad, z_ref=5.0, seconds=8.0)
    assert heights[-1] == pytest.approx(5.0, abs=0.02)
    assert heights.max() < 5.0 + 0.05


def test_lower_damping_overshoots():
    """The damping gain is not decorative: lower it and the climb overshoots."""
    quad = Quadrotor()
    quad.reset(position=np.zeros(3))
    controller = AltitudeHold(mass=quad.params.mass, gravity=quad.params.gravity, kd=1.0)
    heights = _fly(controller, quad, z_ref=5.0, seconds=8.0)
    assert heights.max() > 5.0 + 0.5
```

The second test is the one people skip. If a parameter can change without
any test noticing, nobody knows whether it does anything.
[CONTRIBUTING](https://github.com/guilyx/flybots/blob/main/CONTRIBUTING.md#what-tests-that-pin-the-behaviour-means)
has more on this.

## 3. A runnable simulation

A simulation is a small package under
`src/flybots/simulations/<category>/<name>/`:

```text
src/flybots/simulations/path_tracking/altitude_hold/
├── __init__.py      empty
├── __main__.py      makes `python -m flybots.simulations.…` work
├── run.py           the simulation, exposing main()
└── README.md        what it shows, the key equation, the reference
```

`__main__.py` is two lines and the same everywhere:

```python
from .run import main

main()
```

`run.py` flies the scenario, logs the numbers that matter and records a
GIF. **The first line of its docstring is the summary `flybots list`
shows**, so make it say what you will see:

```python
# src/flybots/simulations/path_tracking/altitude_hold/run.py
"""Altitude hold: climb to 5 m on a PD thrust law and stay there.

Reference: R. Mahony, V. Kumar and P. Corke, IEEE RAM 19(3), 2012.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from flybots.logging import SimLogger
from flybots.path_tracking.altitude_hold import AltitudeHold
from flybots.simulations.common import frame_indices
from flybots.vehicles.multirotor.quadrotor import Quadrotor
from flybots.visualization import SimAnimator

OUT = Path(__file__).parent
Z_REF = 5.0
DT = 0.005
DURATION = 8.0


def main() -> None:
    quad = Quadrotor()
    quad.reset(position=np.zeros(3))
    controller = AltitudeHold(mass=quad.params.mass, gravity=quad.params.gravity)

    steps = int(DURATION / DT)
    times = np.arange(steps) * DT
    heights = np.empty(steps)
    for k in range(steps):
        quad.step(controller.wrench(quad.state, Z_REF), DT)
        heights[k] = quad.state[2]

    # The numbers a reviewer will ask about, written next to the GIF.
    logger = SimLogger("altitude_hold", out_dir=OUT)
    logger.log_metadata("algorithm", "PD altitude hold")
    logger.log_metadata("dt", DT)
    for t, z in zip(times, heights):
        logger.log_step(t=t, z=z)
    logger.log_summary("overshoot_m", float(heights.max() - Z_REF))
    logger.log_summary("final_error_m", float(abs(heights[-1] - Z_REF)))
    logger.save()

    # Any matplotlib figure works; SimAnimator records it frame by frame.
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.axhline(Z_REF, color="tab:green", ls="--", lw=1, label="reference")
    (line,) = ax.plot([], [], lw=1.5, label="height")
    ax.set(xlim=(0, DURATION), ylim=(0, Z_REF * 1.3), xlabel="t [s]", ylabel="z [m]")
    ax.legend(loc="lower right")

    anim = SimAnimator("altitude_hold", out_dir=OUT, figure=fig)
    idx = frame_indices(steps)  # caps the GIF at a sensible frame count

    def update(f: int) -> None:
        k = idx[f]
        line.set_data(times[: k + 1], heights[: k + 1])

    anim.animate(update, len(idx))
    anim.save()


if __name__ == "__main__":
    main()
```

Simulate first, then draw. Keeping the two apart means the physics never
depends on the frame rate, and the logged numbers are the ones the GIF
shows.

For a richer view, `ThreePanelViz` gives the 3D, top-down and data panels
most of the atlas uses — pass `figure=viz.fig` to `SimAnimator`. Shared
scenarios (`default_world()`, the figure-8 reference in
`flybots.simulations.common`, mission timings in
`flybots.simulations.standards`) keep new simulations comparable with the
existing ones; reuse them when they fit.

## 4. Check that flybots finds it

Nothing is registered by hand. Any `simulations/<category>/<name>/run.py`
is in the catalogue:

```console
$ uv run flybots list | grep altitude
altitude_hold          -  Altitude hold: climb to 5 m on a PD thrust law and stay there.

$ uv run flybots info altitude_hold
path_tracking/altitude_hold
───────────────────────────
  summary  Altitude hold: climb to 5 m on a PD thrust law and stay there.
  module   flybots.simulations.path_tracking.altitude_hold.run
  command  python -m flybots.simulations.path_tracking.altitude_hold

$ uv run flybots run altitude_hold
running path_tracking/altitude_hold
  wrote src/flybots/simulations/path_tracking/altitude_hold/altitude_hold.gif
```

Iterating on the physics and don't need the GIF each time? Set
`FLYBOTS_SKIP_GIF=1`: the simulation runs and logs as usual, and the
GIF is not written.

`tests/test_cli.py` checks every simulation in the catalogue has the four
files above and a docstring summary, so a missing `__main__.py` fails
`uv run pytest` rather than surprising someone later.

## 5. The docs page

Each simulation has a page in the atlas at
`docs/simulations/<category>/<name>.md`, with dashes instead of
underscores (`docs/simulations/path-tracking/altitude-hold.md`). The
existing pages share one outline — copy one from the same chapter and
keep the headings:

1. **Problem statement** — what goes wrong without this algorithm.
2. **Model and formulation** — the equations, in LaTeX (`$$ … $$`).
3. **Algorithm procedure** — the steps, in the order the code does them.
4. **Tuning guidance** — which knob does what.
5. **Failure modes and diagnostics** — how it breaks, and how to tell.
6. **Implementation and execution** — the `python -m` command.
7. **Evidence** — the GIF.
8. **References** and **related algorithms**.

Then link the page from its chapter's `index.md` and add it to the
`/simulations/` sidebar in `docs/.vitepress/config.ts`. Preview with:

```bash
cd docs && npm ci && npm run dev
```

::: info About the GIF
Simulation GIFs are stored in Git LFS (`git lfs install` once), and the
docs link them through `media.githubusercontent.com/media/guilyx/flybots/main/…`.
That URL only resolves once your branch is merged, so the image will be
missing from the preview until then. That is expected.
:::

## Explaining, not only implementing

The atlas exists so that someone can understand an algorithm by watching
it. A few habits make that work:

- **Show the interesting part.** For a controller that is the transient,
  not thirty seconds of steady state. For a planner it is the search, not
  only the final path.
- **Show it failing too.** "Lower the damping and it overshoots" teaches
  more than the tuned case alone; the failure-modes section is the place.
- **Name the quantity that matters** with `log_summary`, so a reader can
  compare your algorithm with its neighbours in numbers, not only by eye.
- **Cite the source you implemented**, and say where you departed from it.

## Before opening the pull request

```bash
uv run pytest                      # including the catalogue checks
pre-commit run --all-files         # ruff, formatting, file hygiene
uv run flybots run <name>          # the simulation you added
cd docs && npm run build           # the page builds, links resolve
```

The full checklist, commit conventions and review expectations are in
[CONTRIBUTING](https://github.com/guilyx/flybots/blob/main/CONTRIBUTING.md).
If you are unsure whether an algorithm fits, or want to talk through an
approach first, open a
[discussion](https://github.com/guilyx/flybots/discussions) — that is
what it is for.
