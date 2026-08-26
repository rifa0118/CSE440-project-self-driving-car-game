"""Gym-like racing environment with no dependency on Gym or Pygame."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import numpy as np

from config import ACTION_NAMES, OBSTACLE_KINDS, RewardConfig, SimulationConfig
from game.car import Car
from game.geometry import wrapped_index_delta
from game.obstacles import Obstacle
from game.sensors import SensorReading, cast_sensors
from game.track import Track

# Four discrete actions required by the plan:
# left, right, straight, brake.
ACTION_CONTROLS: tuple[tuple[float, float, float], ...] = (
    (1.0, 0.0, -1.0),
    (1.0, 0.0, 1.0),
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
)


class RacingEnv:
    """A lightweight 2D car environment suitable for DQN training on CPU."""

    def __init__(
        self,
        track_name: str = "easy",
        *,
        simulation_config: SimulationConfig | None = None,
        reward_config: RewardConfig | None = None,
        terminate_on_lap: bool = True,
    ) -> None:
        self.config = simulation_config or SimulationConfig()
        self.reward_config = reward_config or RewardConfig()
        self.track = Track.load(track_name, simulation_config=self.config)
        self.terminate_on_lap = bool(terminate_on_lap)
        self.car = Car(self.config)
        self.obstacles: list[Obstacle] = []
        self._rng = np.random.default_rng()
        self.last_sensor_reading: SensorReading | None = None
        self.reset()

    @property
    def state_size(self) -> int:
        return self.config.state_size

    @property
    def action_size(self) -> int:
        return self.config.action_size

    def reset(
        self,
        *,
        seed: int | None = None,
        start_speed: float = 0.0,
        start_index: int | None = None,
    ) -> np.ndarray:
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        chosen_start = self.track.start_index if start_index is None else int(start_index)
        chosen_start %= self.track.point_count
        next_index = (chosen_start + 3) % self.track.point_count
        tangent = self.track.centerline[next_index] - self.track.centerline[chosen_start]
        angle = float(np.degrees(np.arctan2(tangent[1], tangent[0])))

        self.car.reset(self.track.centerline[chosen_start], angle, speed=start_speed)
        
        self.obstacles = []
        if self.config.obstacle_count > 0:
            for _ in range(self.config.obstacle_count):
                # Pick a random point that is at least 100 points away from start so we don't spawn on the player
                o_idx = (chosen_start + self._rng.integers(100, self.track.point_count - 20)) % self.track.point_count
                o_next = (o_idx + 3) % self.track.point_count
                o_tangent = self.track.centerline[o_next] - self.track.centerline[o_idx]
                o_tangent_norm = o_tangent / float(np.linalg.norm(o_tangent) + 1e-9)
                o_normal = np.array([-o_tangent_norm[1], o_tangent_norm[0]], dtype=np.float32)
                offset_mag = self._rng.uniform(-30.0, 30.0)
                o_pos = self.track.centerline[o_idx] + o_normal * offset_mag

                # Give each obstacle a random rotation and a random visual
                # kind so the track shows a varied mix rather than identical
                # fixed cars.
                o_angle = float(np.degrees(np.arctan2(o_tangent[1], o_tangent[0]))) + self._rng.uniform(-45.0, 45.0)
                o_kind = str(self._rng.choice(OBSTACLE_KINDS))
                self.obstacles.append(Obstacle(kind=o_kind, position=o_pos.astype(np.float32), angle_deg=o_angle))

        self.steps = 0
        self.episode_reward = 0.0
        self.collision_count = 0
        self.lap_count = 0
        self.stuck_steps = 0
        self.last_center_index = chosen_start
        self.start_center_index = chosen_start
        self.unwrapped_progress = 0.0
        self._checkpoint_spacing = self.track.point_count / float(self.config.checkpoint_count)
        self._next_checkpoint_progress = self._checkpoint_spacing
        self._next_lap_progress = float(self.track.point_count)
        self.last_reward_breakdown: dict[str, float] = {}
        return self._get_state()

    def step(
        self,
        action: int,
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if not 0 <= int(action) < len(ACTION_CONTROLS):
            raise ValueError(f"action must be in [0, {len(ACTION_CONTROLS) - 1}]")
        throttle, brake, steering = ACTION_CONTROLS[int(action)]
        return self.step_controls(
            throttle=throttle,
            brake=brake,
            steering=steering,
            action=int(action),
        )

    def step_controls(
        self,
        *,
        throttle: float,
        brake: float,
        steering: float,
        action: int | None = None,
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        """Advance one step using either AI action controls or keyboard input."""

        self.steps += 1
        previous_index = self.last_center_index
        self.car.update(throttle=throttle, brake=brake, steering=steering)

        new_index = self.track.nearest_center_index(
            self.car.position,
            hint_index=previous_index,
        )
        index_delta = wrapped_index_delta(
            new_index,
            previous_index,
            self.track.point_count,
        )
        # At this resolution one step cannot move more than a handful of
        # centre-line samples. Clamp any residual nearest-point ambiguity.
        maximum_plausible_delta = 8.0
        if abs(index_delta) > maximum_plausible_delta:
            index_delta = float(np.sign(index_delta) * maximum_plausible_delta)
        self.last_center_index = new_index
        self.unwrapped_progress += index_delta

        collision = not self.track.points_are_on_road(self.car.collision_probe_points())
        if not collision:
            for obstacle in self.obstacles:
                if np.linalg.norm(self.car.position - obstacle.position) < obstacle.radius:
                    collision = True
                    break
        checkpoint_passed = False
        lap_completed = False
        breakdown: dict[str, float] = {}

        if index_delta > 0.10 and self.car.speed >= self.config.stuck_speed_threshold:
            breakdown["driving_forward"] = self.reward_config.driving_forward
        elif index_delta < -0.10:
            breakdown["driving_backwards"] = self.reward_config.driving_backwards

        if self.car.speed < self.config.stuck_speed_threshold:
            self.stuck_steps += 1
            breakdown["standing_still"] = self.reward_config.standing_still
        else:
            self.stuck_steps = 0

        while self.unwrapped_progress >= self._next_checkpoint_progress:
            checkpoint_passed = True
            breakdown["checkpoint"] = breakdown.get("checkpoint", 0.0) + self.reward_config.checkpoint
            self._next_checkpoint_progress += self._checkpoint_spacing

        while self.unwrapped_progress >= self._next_lap_progress:
            lap_completed = True
            self.lap_count += 1
            breakdown["lap_complete"] = breakdown.get("lap_complete", 0.0) + self.reward_config.lap_complete
            self._next_lap_progress += float(self.track.point_count)

        if collision:
            self.collision_count += 1
            breakdown["collision"] = self.reward_config.collision

        reward = float(sum(breakdown.values()))
        self.episode_reward += reward
        self.last_reward_breakdown = breakdown

        terminated = collision or (
            self.terminate_on_lap and self.lap_count >= self.config.target_laps
        )
        truncated = self.steps >= self.config.max_steps or (
            self.stuck_steps >= self.config.stuck_step_limit
        )

        if collision:
            termination_reason = "collision"
        elif terminated:
            termination_reason = "lap_complete"
        elif self.stuck_steps >= self.config.stuck_step_limit:
            termination_reason = "stuck"
        elif self.steps >= self.config.max_steps:
            termination_reason = "time_limit"
        else:
            termination_reason = None

        state = self._get_state()
        info: dict[str, Any] = {
            "action": action,
            "action_name": ACTION_NAMES[action] if action is not None else "manual",
            "speed": self.car.speed,
            "step": self.steps,
            "episode_reward": self.episode_reward,
            "collision": collision,
            "checkpoint_passed": checkpoint_passed,
            "lap_completed": lap_completed,
            "lap_count": self.lap_count,
            "progress_index": self.last_center_index,
            "unwrapped_progress": self.unwrapped_progress,
            "progress_fraction": self.unwrapped_progress / self.track.point_count,
            "index_delta": index_delta,
            "reward_breakdown": breakdown.copy(),
            "termination_reason": termination_reason,
            "sensor_distances": self.last_sensor_reading.distances.copy(),
            "sensor_endpoints": self.last_sensor_reading.endpoints.copy(),
        }
        return state, reward, terminated, truncated, info

    def _get_state(self) -> np.ndarray:
        self.last_sensor_reading = cast_sensors(
            self.track,
            self.car.position,
            self.car.angle_deg,
            self.config,
            self.obstacles,
        )
        sensor_state = self.last_sensor_reading.normalised(self.config.sensor_max_distance)
        speed_state = np.array(
            [self.car.speed / self.config.max_speed],
            dtype=np.float32,
        )
        state = np.concatenate((sensor_state, speed_state)).astype(np.float32)
        if state.shape != (self.state_size,):  # defensive programming for config edits
            raise RuntimeError(f"Expected state shape {(self.state_size,)}, got {state.shape}")
        return state

    def describe(self) -> dict[str, Any]:
        return {
            "track": self.track.name,
            "state_size": self.state_size,
            "action_size": self.action_size,
            "simulation": asdict(self.config),
            "rewards": asdict(self.reward_config),
        }
