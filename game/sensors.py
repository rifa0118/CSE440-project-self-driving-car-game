"""Five ray-based distance sensors for the reinforcement-learning state."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import SimulationConfig
from game.geometry import angle_to_unit_vector
from game.track import Track


@dataclass(frozen=True, slots=True)
class SensorReading:
    distances: np.ndarray
    endpoints: np.ndarray

    def normalised(self, max_distance: float) -> np.ndarray:
        return np.clip(self.distances / max_distance, 0.0, 1.0).astype(np.float32)


def cast_sensors(
    track: Track,
    position: np.ndarray,
    car_angle_deg: float,
    config: SimulationConfig,
) -> SensorReading:
    """Cast all configured rays until each one reaches a wall or max range."""

    distances_to_test = np.arange(
        config.sensor_step,
        config.sensor_max_distance + config.sensor_step,
        config.sensor_step,
        dtype=np.float32,
    )
    distances = np.empty(len(config.sensor_angles_deg), dtype=np.float32)
    endpoints = np.empty((len(config.sensor_angles_deg), 2), dtype=np.float32)
    origin = np.asarray(position, dtype=np.float32)

    for sensor_index, relative_angle in enumerate(config.sensor_angles_deg):
        direction = angle_to_unit_vector(car_angle_deg + relative_angle)
        points = origin[None, :] + distances_to_test[:, None] * direction[None, :]
        xs = np.rint(points[:, 0]).astype(np.int32)
        ys = np.rint(points[:, 1]).astype(np.int32)

        in_bounds = (
            (xs >= 0)
            & (ys >= 0)
            & (xs < track.width)
            & (ys < track.height)
        )
        on_road = np.zeros_like(in_bounds)
        valid_indices = np.flatnonzero(in_bounds)
        if valid_indices.size:
            on_road[valid_indices] = track.mask[ys[valid_indices], xs[valid_indices]]

        wall_hits = np.flatnonzero(~on_road)
        if wall_hits.size:
            distance = float(distances_to_test[int(wall_hits[0])])
        else:
            distance = float(config.sensor_max_distance)

        distances[sensor_index] = distance
        endpoints[sensor_index] = origin + direction * distance

    return SensorReading(distances=distances, endpoints=endpoints)
