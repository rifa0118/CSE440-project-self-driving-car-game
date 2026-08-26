"""Small geometry helpers shared by the simulator and renderer."""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np


def angle_to_unit_vector(angle_deg: float) -> np.ndarray:
    """Return a 2D unit vector for screen coordinates (positive y is down)."""

    radians = math.radians(angle_deg)
    return np.array([math.cos(radians), math.sin(radians)], dtype=np.float32)


def rotate_local_points(
    position: np.ndarray,
    angle_deg: float,
    local_points: Iterable[tuple[float, float]],
) -> np.ndarray:
    """Rotate car-local points into world/screen coordinates."""

    radians = math.radians(angle_deg)
    cos_a = math.cos(radians)
    sin_a = math.sin(radians)
    rotation = np.array([[cos_a, -sin_a], [sin_a, cos_a]], dtype=np.float32)
    local = np.asarray(tuple(local_points), dtype=np.float32)
    return local @ rotation.T + np.asarray(position, dtype=np.float32)


def wrapped_index_delta(new_index: int, old_index: int, total: int) -> float:
    """Shortest signed index change on a circular sequence."""

    if total <= 0:
        raise ValueError("total must be positive")
    return float((new_index - old_index + total / 2.0) % total - total / 2.0)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
