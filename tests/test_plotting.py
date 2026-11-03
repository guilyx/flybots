"""Tests for the public plotting helpers.

These are only drawn by the simulations otherwise, so a broken helper
surfaced as a failed GIF render rather than a failed test.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.patches import Circle, Wedge

from flybots.visualization import draw_camera_fov_top, draw_lidar2d_fov_top
from flybots.visualization.plotting import (
    plot_quadrotor_3d,
    plot_state_history,
    plot_trajectory_3d,
)
from flybots.visualization.sensor_viz import draw_camera_frustum_3d


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def _helix(n: int = 50) -> np.ndarray:
    t = np.linspace(0.0, 2 * np.pi, n)
    return np.column_stack([np.cos(t), np.sin(t), t])


def test_trajectory_plot_draws_the_path_and_the_reference():
    path, ref = _helix(), _helix() + 0.1
    _, ax = plot_trajectory_3d(path, reference=ref, show=False)
    lines = ax.get_lines()
    assert [line.get_label() for line in lines[:2]] == ["Actual", "Reference"]
    x, y = lines[0].get_data()
    np.testing.assert_allclose(x, path[:, 0])
    np.testing.assert_allclose(y, path[:, 1])


def test_trajectory_plot_without_reference_draws_one_path():
    _, ax = plot_trajectory_3d(_helix(), show=False)
    assert [line.get_label() for line in ax.get_lines()][:1] == ["Actual"]
    assert "Reference" not in [line.get_label() for line in ax.get_lines()]


def test_state_history_plots_against_time():
    times = np.linspace(0.0, 1.0, 20)
    states = np.random.default_rng(0).normal(size=(20, 12))
    fig = plot_state_history(times, states, show=False)
    assert len(fig.axes) == 4
    for axes in fig.axes:
        assert axes.get_lines(), "every panel should carry data"
        np.testing.assert_allclose(axes.get_lines()[0].get_xdata(), times)


def test_quadrotor_glyph_is_centred_on_the_vehicle():
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    position = np.array([3.0, -2.0, 5.0])
    plot_quadrotor_3d(ax, position, np.zeros(3))
    assert ax.get_lines()
    xs = np.concatenate([line.get_data_3d()[0] for line in ax.get_lines()])
    zs = np.concatenate([line.get_data_3d()[2] for line in ax.get_lines()])
    assert np.mean(xs) == pytest.approx(position[0], abs=1.0)
    assert np.mean(zs) == pytest.approx(position[2], abs=1.0)


def test_full_circle_lidar_is_a_circle_and_a_sector_is_a_wedge():
    _, ax = plt.subplots()
    full = draw_lidar2d_fov_top(ax, np.zeros(2), yaw=0.0, max_range=10.0)
    assert any(isinstance(a, Circle) and a.get_radius() == 10.0 for a in full)
    sector = draw_lidar2d_fov_top(ax, np.zeros(2), yaw=0.0, fov=np.pi / 2, max_range=10.0)
    assert any(isinstance(a, Wedge) for a in sector)


def test_camera_wedge_points_where_the_camera_looks():
    _, ax = plt.subplots()
    yaw, fov = np.pi / 2, np.radians(60.0)
    arts = draw_camera_fov_top(ax, np.zeros(2), yaw=yaw, h_fov=fov, max_depth=8.0)
    wedge = next(a for a in arts if isinstance(a, Wedge))
    centre = (wedge.theta1 + wedge.theta2) / 2
    assert centre == pytest.approx(90.0)
    assert wedge.theta2 - wedge.theta1 == pytest.approx(60.0)
    assert wedge.r == 8.0


def test_camera_frustum_adds_artists_to_the_axes():
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    arts = draw_camera_frustum_3d(
        ax, np.zeros(3), np.eye(3), h_fov=np.radians(60), v_fov=np.radians(45)
    )
    assert arts
    assert all(a.axes is ax for a in arts)


def test_duplicate_payload_gimbal_is_deprecated():
    """There were two gimbal models; only flybots.sensors.gimbal is used."""
    import importlib
    import sys

    sys.modules.pop("flybots.vehicles.payloads.gimbal", None)
    with pytest.warns(DeprecationWarning, match="flybots.sensors.gimbal"):
        importlib.import_module("flybots.vehicles.payloads.gimbal")
