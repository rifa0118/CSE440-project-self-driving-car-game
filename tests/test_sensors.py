from __future__ import annotations

import numpy as np

from config import SimulationConfig
from game.sensors import cast_sensors
from game.track import Track


def test_five_sensors_return_bounded_distances() -> None:
    config = SimulationConfig()
    track = Track.load("easy", simulation_config=config)
    reading = cast_sensors(track, track.start_position, track.start_angle_deg, config)
    assert reading.distances.shape == (5,)
    assert reading.endpoints.shape == (5, 2)
    assert np.all(reading.distances > 0.0)
    assert np.all(reading.distances <= config.sensor_max_distance)
    normalised = reading.normalised(config.sensor_max_distance)
    assert normalised.dtype == np.float32
    assert np.all((normalised >= 0.0) & (normalised <= 1.0))
