"""Simple car kinematics used by both manual and AI driving."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from config import SimulationConfig
from game.geometry import angle_to_unit_vector, clamp, rotate_local_points


@dataclass(slots=True)
class Car:
    config: SimulationConfig
    position: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=np.float32))
    angle_deg: float = 0.0
    speed: float = 0.0
    distance_travelled: float = 0.0

    def reset(self, position: np.ndarray, angle_deg: float, speed: float = 0.0) -> None:
        self.position = np.asarray(position, dtype=np.float32).copy()
        self.angle_deg = float(angle_deg) % 360.0
        self.speed = clamp(float(speed), 0.0, self.config.max_speed)
        self.distance_travelled = 0.0

    def update(self, *, throttle: float, brake: float, steering: float) -> None:
        """Advance one simulation step with intentionally simple physics."""

        throttle = clamp(float(throttle), 0.0, 1.0)
        brake = clamp(float(brake), 0.0, 1.0)
        steering = clamp(float(steering), -1.0, 1.0)

        self.speed += throttle * self.config.acceleration
        self.speed -= brake * self.config.brake_power

        # Rolling resistance keeps the car from moving forever without input.
        if throttle <= 0.0:
            self.speed -= self.config.friction
        else:
            self.speed -= self.config.friction * 0.18
        self.speed = clamp(self.speed, 0.0, self.config.max_speed)

        if self.speed > 0.02 and abs(steering) > 1.0e-9:
            speed_ratio = self.speed / self.config.max_speed
            steering_scale = 0.38 + 0.62 * speed_ratio
            self.angle_deg = (
                self.angle_deg
                + steering * self.config.steering_rate_deg * steering_scale
            ) % 360.0

        displacement = angle_to_unit_vector(self.angle_deg) * self.speed
        self.position += displacement
        self.distance_travelled += float(np.linalg.norm(displacement))

    def corners(self, margin: float = 0.0) -> np.ndarray:
        half_length = max(1.0, self.config.car_length / 2.0 - margin)
        half_width = max(1.0, self.config.car_width / 2.0 - margin)
        local_points = (
            (half_length, half_width),
            (half_length, -half_width),
            (-half_length, -half_width),
            (-half_length, half_width),
        )
        return rotate_local_points(self.position, self.angle_deg, local_points)

    def collision_probe_points(self) -> np.ndarray:
        """Corners plus side midpoints make pixel-mask collision reliable."""

        half_length = self.config.car_length / 2.0
        half_width = self.config.car_width / 2.0
        local_points = (
            (half_length, half_width),
            (half_length, 0.0),
            (half_length, -half_width),
            (0.0, -half_width),
            (-half_length, -half_width),
            (-half_length, 0.0),
            (-half_length, half_width),
            (0.0, half_width),
            (0.0, 0.0),
        )
        return rotate_local_points(self.position, self.angle_deg, local_points)

    @property
    def heading_vector(self) -> np.ndarray:
        return angle_to_unit_vector(self.angle_deg)
