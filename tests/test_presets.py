# Erwin Lejeune - 2026-02-15
"""Tests for vehicle presets."""

import numpy as np
import pytest

from flybots.vehicles.presets import VehiclePreset, create_quadrotor, get_params


class TestCreateQuadrotor:
    @pytest.mark.parametrize(
        "preset",
        [
            VehiclePreset.CRAZYFLIE,
            VehiclePreset.DJI_MINI,
            VehiclePreset.RACING_250,
            VehiclePreset.DJI_MATRICE,
        ],
    )
    def test_all_presets_instantiate(self, preset: VehiclePreset):
        quad = create_quadrotor(preset)
        assert quad.state.shape == (12,)
        assert quad.params.mass > 0

    def test_crazyflie_is_lightweight(self):
        quad = create_quadrotor(VehiclePreset.CRAZYFLIE)
        assert quad.params.mass < 0.1

    def test_matrice_is_heavy(self):
        quad = create_quadrotor(VehiclePreset.DJI_MATRICE)
        assert quad.params.mass > 3.0

    def test_override_mass(self):
        quad = create_quadrotor(VehiclePreset.RACING_250, mass=2.0)
        assert quad.params.mass == 2.0
        assert quad.params.arm_length == 0.175  # unchanged

    def test_custom_preset(self):
        quad = create_quadrotor(VehiclePreset.CUSTOM, mass=0.5, arm_length=0.1)
        assert quad.params.mass == 0.5

    def test_hover_wrench_scales_with_mass(self):
        light = create_quadrotor(VehiclePreset.CRAZYFLIE)
        heavy = create_quadrotor(VehiclePreset.DJI_MATRICE)
        assert heavy.hover_wrench()[0] > light.hover_wrench()[0]


class TestGetParams:
    def test_returns_correct_mass(self):
        p = get_params(VehiclePreset.DJI_MINI)
        assert p.mass == pytest.approx(0.249)

    def test_inertia_is_diagonal(self):
        p = get_params(VehiclePreset.RACING_250)
        off_diag = p.inertia - np.diag(np.diag(p.inertia))
        np.testing.assert_allclose(off_diag, 0.0, atol=1e-12)


class TestPresetsCanFly:
    """Every preset has to be able to hold itself up.

    ``DJI_MINI`` shipped with ``k_thrust = 1.0e-7``, which put its four
    rotors at 1.296 N against 2.443 N of weight — 53 % of the thrust needed
    to hover. Hovering would have taken 2471 rad/s from motors limited to
    1800, so the airframe sank at full throttle and every simulation
    starting from that preset flew into the ground.
    """

    ALL = [
        VehiclePreset.CRAZYFLIE,
        VehiclePreset.DJI_MINI,
        VehiclePreset.RACING_250,
        VehiclePreset.DJI_MATRICE,
    ]

    @pytest.mark.parametrize("preset", ALL)
    def test_rotors_can_lift_the_airframe(self, preset: VehiclePreset):
        """Thrust-to-weight of at least 1.5, so there is authority to manoeuvre.

        A quadrotor at exactly 1.0 can hover and do nothing else: every
        newton is already spent holding altitude.
        """
        p = get_params(preset)
        max_thrust = 4.0 * p.k_thrust * p.omega_max**2
        assert max_thrust / (p.mass * p.gravity) >= 1.5

    @pytest.mark.parametrize("preset", ALL)
    def test_hover_speed_is_within_the_motor_envelope(self, preset: VehiclePreset):
        """The speed hover needs must be reachable, with headroom to spare."""
        p = get_params(preset)
        hover_omega = np.sqrt((p.mass * p.gravity / 4.0) / p.k_thrust)
        assert hover_omega <= 0.8 * p.omega_max

    @pytest.mark.parametrize("preset", ALL)
    def test_holds_altitude_on_its_own_hover_wrench(self, preset: VehiclePreset):
        """Open-loop hover: commanding `hover_wrench` must not lose altitude.

        This is the behavioural form of the two checks above — it goes
        through the mixer, the motor speed limit and the rigid body, so a
        preset that cannot reach hover speed shows up as a descent rather
        than as an inequality.
        """
        quad = create_quadrotor(preset)
        quad.reset(position=np.array([0.0, 0.0, 10.0]))
        hover = quad.hover_wrench()
        for motor in quad.motors:
            motor.reset(motor.thrust_to_omega(hover[0] / 4.0))

        for _ in range(400):
            quad.step(hover, 0.005)

        assert quad.state[2] == pytest.approx(10.0, abs=0.05)


class TestPresetsAreNotShared:
    """Changing one aircraft's parameters must not change the next one's.

    The preset tables are module-level. Handing them out directly meant a
    payload's mass or a damaged motor set on one vehicle silently applied to
    every vehicle built from the same preset afterwards.
    """

    @pytest.mark.parametrize("overrides", [{}, {"mass": 2.0}])
    def test_quadrotor_params_are_private(self, overrides):
        first = create_quadrotor(VehiclePreset.RACING_250, **overrides)
        first.params.mass = 9.0
        first.params.inertia[0, 0] = 99.0
        fresh = create_quadrotor(VehiclePreset.RACING_250)
        assert fresh.params.mass == pytest.approx(1.5)
        assert fresh.params.inertia[0, 0] == pytest.approx(0.0082)

    def test_multirotor_rotors_are_private(self):
        from flybots.vehicles.presets import create_multirotor

        first = create_multirotor(VehiclePreset.HEX_S550)
        first.params.rotors.pop()
        assert create_multirotor(VehiclePreset.HEX_S550).n_rotors == 6

    def test_get_params_returns_a_copy(self):
        get_params(VehiclePreset.CRAZYFLIE).mass = 50.0
        assert get_params(VehiclePreset.CRAZYFLIE).mass < 0.1

    @pytest.mark.parametrize("overrides", [{}, {"mass": 4.0}])
    def test_fixed_wing_params_are_private(self, overrides):
        from flybots.vehicles.fixed_wing.presets import (
            FixedWingPreset,
            create_fixed_wing,
            get_fixed_wing_params,
        )

        stock = get_fixed_wing_params(FixedWingPreset.AEROSONDE)
        mass, cl0 = stock.mass, stock.coeffs.CL0
        first = create_fixed_wing(FixedWingPreset.AEROSONDE, **overrides)
        first.fw_params.mass = 99.0
        first.fw_params.coeffs.CL0 += 1.0
        fresh = create_fixed_wing(FixedWingPreset.AEROSONDE).fw_params
        assert fresh.mass == pytest.approx(mass)
        assert fresh.coeffs.CL0 == pytest.approx(cl0)
