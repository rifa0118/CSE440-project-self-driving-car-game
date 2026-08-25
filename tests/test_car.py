from __future__ import annotations

import numpy as np

from config import SimulationConfig
from game.car import Car


def test_car_accelerates_and_moves_straight() -> None:
    car = Car(SimulationConfig())
    car.reset(np.array([100.0, 100.0], dtype=np.float32), angle_deg=0.0)
    for _ in range(10):
        car.update(throttle=1.0, brake=0.0, steering=0.0)
    assert car.speed > 0.0
    assert car.position[0] > 100.0
    assert abs(float(car.position[1]) - 100.0) < 1.0e-5


def test_car_steers_and_brakes() -> None:
    car = Car(SimulationConfig())
    car.reset(np.array([100.0, 100.0], dtype=np.float32), angle_deg=0.0, speed=4.0)
    car.update(throttle=0.0, brake=0.0, steering=1.0)
    assert car.angle_deg > 0.0
    speed_before_brake = car.speed
    car.update(throttle=0.0, brake=1.0, steering=0.0)
    assert car.speed < speed_before_brake
    assert car.corners().shape == (4, 2)
    assert car.collision_probe_points().shape == (9, 2)
