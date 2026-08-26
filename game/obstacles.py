"""Static obstacles scattered on the track during training/manual/watch modes.

These are intentionally lightweight (position + angle + kind) rather than
full ``Car`` instances: obstacles never move, so they don't need physics,
only a place to stand and a visual "kind" so the renderer can draw several
different obstacle designs instead of a row of identical parked cars.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Approximate collision/sensor radius (in world units) for each obstacle kind.
# Smaller objects (cones) are easier to graze past than a wide barrier.
OBSTACLE_RADII: dict[str, float] = {
    "cone": 14.0,
    "barrel": 17.0,
    "barrier": 24.0,
    "rock": 19.0,
    "crate": 18.0,
}
DEFAULT_OBSTACLE_RADIUS = 20.0


@dataclass(slots=True)
class Obstacle:
    """A single static obstacle placed somewhere on the track."""

    kind: str
    position: np.ndarray
    angle_deg: float = 0.0

    @property
    def radius(self) -> float:
        return OBSTACLE_RADII.get(self.kind, DEFAULT_OBSTACLE_RADIUS)
