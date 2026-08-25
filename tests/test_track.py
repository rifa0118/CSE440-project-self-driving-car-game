from __future__ import annotations

import numpy as np
import pytest

from config import SimulationConfig, TRACK_CHOICES
from game.car import Car
from game.track import Track


@pytest.mark.parametrize("name", TRACK_CHOICES)
def test_track_assets_are_valid(name: str) -> None:
    config = SimulationConfig()
    track = Track.load(name, simulation_config=config)
    assert track.mask.shape == (config.height, config.width)
    assert track.display_image.size == (config.width, config.height)
    assert track.centerline.shape == (720, 2)
    assert len(track.checkpoint_indices) == config.checkpoint_count
    assert track.is_road(*track.start_position)
    assert not track.is_road(0, 0)

    car = Car(config)
    car.reset(track.start_position, track.start_angle_deg)
    assert track.points_are_on_road(car.collision_probe_points())


def test_local_nearest_index_does_not_jump_to_distant_track_section() -> None:
    track = Track.load("easy")
    hint = 100
    position = track.centerline[hint] + np.array([2.0, -1.0], dtype=np.float32)
    result = track.nearest_center_index(position, hint_index=hint, search_radius=10)
    delta = (result - hint + track.point_count // 2) % track.point_count - track.point_count // 2
    assert abs(delta) <= 10
