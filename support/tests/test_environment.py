from __future__ import annotations

import math

import numpy as np
import pytest

from game.environment import RacingEnv


def test_environment_state_and_action_contract() -> None:
    env = RacingEnv("easy")
    state = env.reset(seed=123)
    assert state.shape == (6,)
    assert state.dtype == np.float32
    assert np.all((state >= 0.0) & (state <= 1.0))

    next_state, reward, terminated, truncated, info = env.step(2)
    assert next_state.shape == (6,)
    assert isinstance(reward, float)
    assert not terminated
    assert not truncated
    assert info["action_name"] == "straight"

    with pytest.raises(ValueError):
        env.step(4)


def test_reward_configuration_is_applied_exactly() -> None:
    env = RacingEnv("easy")
    env.reset()
    # A stationary brake action receives the specified standing-still reward.
    _, reward, _, _, info = env.step(3)
    assert reward == env.reward_config.standing_still
    assert info["reward_breakdown"] == {"standing_still": -2.0}


def test_simple_centerline_controller_completes_easy_lap() -> None:
    env = RacingEnv("easy")
    env.reset()
    final_info = None
    for _ in range(600):
        target = env.track.centerline[(env.last_center_index + 18) % env.track.point_count]
        dx, dy = target - env.car.position
        desired_angle = math.degrees(math.atan2(float(dy), float(dx)))
        angle_error = (desired_angle - env.car.angle_deg + 180.0) % 360.0 - 180.0
        steering = max(-1.0, min(1.0, angle_error / 20.0))
        brake = 1.0 if abs(angle_error) > 45.0 and env.car.speed > 4.5 else 0.0
        throttle = 0.5 if brake else 1.0
        _, _, terminated, truncated, final_info = env.step_controls(
            throttle=throttle,
            brake=brake,
            steering=steering,
        )
        if terminated or truncated:
            break

    assert final_info is not None
    assert final_info["termination_reason"] == "lap_complete"
    assert env.lap_count == 1
    assert env.collision_count == 0
