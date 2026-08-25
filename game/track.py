"""Image-based racing tracks and track asset generation.

Each track has two PNG files:

* ``<name>_mask.png``: white road on a black background, used for collision
  and sensor ray-casting exactly as described in the project plan.
* ``<name>.png``: a presentation-friendly coloured version used by Pygame.

A JSON metadata file stores the centre line, checkpoints, road width, and start
pose. Assets are generated deterministically, so the project works without
third-party artwork or downloads.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from config import TRACKS_DIR, TRACK_CHOICES, SimulationConfig

TRACK_POINT_COUNT: Final[int] = 720


@dataclass(slots=True)
class Track:
    name: str
    width: int
    height: int
    road_width: float
    mask: np.ndarray
    display_image: Image.Image
    centerline: np.ndarray
    checkpoint_indices: tuple[int, ...]
    start_index: int
    start_position: np.ndarray
    start_angle_deg: float

    @classmethod
    def load(
        cls,
        name: str,
        tracks_dir: Path = TRACKS_DIR,
        simulation_config: SimulationConfig | None = None,
    ) -> "Track":
        if name not in TRACK_CHOICES:
            raise ValueError(f"Unknown track {name!r}; choose from {TRACK_CHOICES}")

        config = simulation_config or SimulationConfig()
        ensure_track_assets(config=config, tracks_dir=tracks_dir)

        mask_path = tracks_dir / f"{name}_mask.png"
        display_path = tracks_dir / f"{name}.png"
        metadata_path = tracks_dir / f"{name}.json"

        with metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        mask_image = Image.open(mask_path).convert("L")
        display_image = Image.open(display_path).convert("RGB")
        mask = np.asarray(mask_image, dtype=np.uint8) >= 128
        centerline = np.asarray(metadata["centerline"], dtype=np.float32)
        start_index = int(metadata["start_index"])

        return cls(
            name=name,
            width=int(metadata["width"]),
            height=int(metadata["height"]),
            road_width=float(metadata["road_width"]),
            mask=mask,
            display_image=display_image,
            centerline=centerline,
            checkpoint_indices=tuple(int(i) for i in metadata["checkpoint_indices"]),
            start_index=start_index,
            start_position=centerline[start_index].copy(),
            start_angle_deg=float(metadata["start_angle_deg"]),
        )

    @property
    def point_count(self) -> int:
        return int(self.centerline.shape[0])

    def is_road(self, x: float, y: float) -> bool:
        ix = int(round(x))
        iy = int(round(y))
        if ix < 0 or iy < 0 or ix >= self.width or iy >= self.height:
            return False
        return bool(self.mask[iy, ix])

    def points_are_on_road(self, points: np.ndarray) -> bool:
        return all(self.is_road(float(x), float(y)) for x, y in points)

    def nearest_center_index(
        self,
        position: np.ndarray,
        *,
        hint_index: int | None = None,
        search_radius: int = 28,
    ) -> int:
        """Find the nearest centre-line point.

        During simulation a local search around the previous index prevents a
        collision near another section of track from creating impossible
        progress jumps or checkpoint rewards. A global search remains useful
        for one-off inspection and tests.
        """

        point = np.asarray(position, dtype=np.float32)
        if hint_index is None:
            delta = self.centerline - point
            return int(np.argmin(np.einsum("ij,ij->i", delta, delta)))

        offsets = np.arange(-search_radius, search_radius + 1, dtype=np.int32)
        indices = (int(hint_index) + offsets) % self.point_count
        candidates = self.centerline[indices]
        delta = candidates - point
        local = int(np.argmin(np.einsum("ij,ij->i", delta, delta)))
        return int(indices[local])

    def distance_to_centerline(self, position: np.ndarray) -> float:
        index = self.nearest_center_index(position)
        return float(np.linalg.norm(self.centerline[index] - position))

    def checkpoint_positions(self) -> np.ndarray:
        return self.centerline[np.asarray(self.checkpoint_indices, dtype=np.int32)]


def _make_centerline(name: str, width: int, height: int) -> tuple[np.ndarray, int]:
    t = np.linspace(0.0, 2.0 * math.pi, TRACK_POINT_COUNT, endpoint=False, dtype=np.float64)
    cx = width / 2.0
    cy = height / 2.0

    if name == "easy":
        x = cx + 330.0 * np.cos(t)
        y = cy + 210.0 * np.sin(t)
        road_width = 116
    elif name == "medium":
        radial = 1.0 + 0.10 * np.sin(3.0 * t + 0.25) + 0.035 * np.cos(5.0 * t)
        x = cx + 310.0 * radial * np.cos(t)
        y = cy + 195.0 * (1.0 + 0.11 * np.cos(2.0 * t - 0.4)) * np.sin(t)
        road_width = 98
    elif name == "hard":
        radial_x = 1.0 + 0.14 * np.sin(3.0 * t + 0.45) + 0.055 * np.sin(5.0 * t)
        radial_y = 1.0 + 0.13 * np.cos(4.0 * t - 0.25) - 0.035 * np.sin(2.0 * t)
        x = cx + 292.0 * radial_x * np.cos(t)
        y = cy + 188.0 * radial_y * np.sin(t)
        road_width = 84
    else:  # pragma: no cover - caller validates names
        raise ValueError(name)

    return np.column_stack((x, y)).astype(np.float32), road_width


def _closed_line_points(centerline: np.ndarray) -> list[tuple[float, float]]:
    points = [(float(x), float(y)) for x, y in centerline]
    points.append(points[0])
    return points


def _draw_smoothed_closed_line(
    draw: ImageDraw.ImageDraw,
    centerline: np.ndarray,
    *,
    fill: int | tuple[int, ...],
    width: int,
) -> None:
    points = _closed_line_points(centerline)
    draw.line(points, fill=fill, width=width, joint="curve")
    radius = width / 2.0
    # Circles at sparse points remove any platform-specific line-joint gaps.
    for x, y in centerline[::8]:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)


def _draw_dashed_centerline(draw: ImageDraw.ImageDraw, centerline: np.ndarray) -> None:
    points = np.vstack((centerline, centerline[0]))
    dash_on = 16.0
    dash_off = 14.0
    phase = 0.0
    drawing = True

    for start, end in zip(points[:-1], points[1:], strict=True):
        vector = end - start
        length = float(np.linalg.norm(vector))
        if length <= 1.0e-9:
            continue
        direction = vector / length
        travelled = 0.0
        while travelled < length:
            remaining_in_phase = (dash_on if drawing else dash_off) - phase
            segment_length = min(remaining_in_phase, length - travelled)
            if drawing and segment_length > 0.0:
                a = start + direction * travelled
                b = start + direction * (travelled + segment_length)
                draw.line((tuple(a), tuple(b)), fill=(235, 225, 155), width=3)
            travelled += segment_length
            phase += segment_length
            phase_limit = dash_on if drawing else dash_off
            if phase >= phase_limit - 1.0e-6:
                phase = 0.0
                drawing = not drawing


def _draw_start_line(
    draw: ImageDraw.ImageDraw,
    centerline: np.ndarray,
    road_width: int,
    start_index: int,
) -> None:
    point = centerline[start_index]
    next_point = centerline[(start_index + 3) % len(centerline)]
    tangent = next_point - point
    tangent = tangent / max(float(np.linalg.norm(tangent)), 1.0e-9)
    normal = np.array([-tangent[1], tangent[0]], dtype=np.float32)

    half_width = road_width * 0.46
    tile_width = (half_width * 2.0) / 10.0
    stripe_depth = 14.0
    for row in range(2):
        for column in range(10):
            colour = (240, 240, 240) if (row + column) % 2 == 0 else (25, 28, 32)
            across_0 = -half_width + column * tile_width
            across_1 = across_0 + tile_width
            along_0 = -stripe_depth + row * stripe_depth
            along_1 = along_0 + stripe_depth
            corners = [
                point + normal * across_0 + tangent * along_0,
                point + normal * across_1 + tangent * along_0,
                point + normal * across_1 + tangent * along_1,
                point + normal * across_0 + tangent * along_1,
            ]
            draw.polygon([tuple(corner) for corner in corners], fill=colour)


def _background(width: int, height: int, seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    base = Image.new("RGB", (width, height), (37, 92, 59))
    draw = ImageDraw.Draw(base)

    # Deterministic low-contrast grass patches make the game look finished
    # without requiring external art assets.
    for _ in range(240):
        x = int(rng.integers(0, width))
        y = int(rng.integers(0, height))
        radius = int(rng.integers(2, 8))
        tone = int(rng.integers(-13, 14))
        colour = (max(18, 37 + tone), max(55, 92 + tone), max(32, 59 + tone))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=colour)

    return base.filter(ImageFilter.GaussianBlur(radius=0.7))


def generate_track_asset(
    name: str,
    *,
    config: SimulationConfig,
    tracks_dir: Path = TRACKS_DIR,
) -> None:
    tracks_dir.mkdir(parents=True, exist_ok=True)
    centerline, road_width = _make_centerline(name, config.width, config.height)
    start_index = 0
    tangent = centerline[(start_index + 3) % len(centerline)] - centerline[start_index]
    start_angle_deg = math.degrees(math.atan2(float(tangent[1]), float(tangent[0])))

    mask_image = Image.new("L", (config.width, config.height), 0)
    mask_draw = ImageDraw.Draw(mask_image)
    _draw_smoothed_closed_line(mask_draw, centerline, fill=255, width=road_width)

    display = _background(config.width, config.height, seed={"easy": 101, "medium": 202, "hard": 303}[name])
    display_draw = ImageDraw.Draw(display)
    _draw_smoothed_closed_line(
        display_draw,
        centerline,
        fill=(198, 202, 204),
        width=road_width + 14,
    )
    _draw_smoothed_closed_line(
        display_draw,
        centerline,
        fill=(65, 69, 75),
        width=road_width,
    )
    _draw_dashed_centerline(display_draw, centerline)
    _draw_start_line(display_draw, centerline, road_width, start_index)

    checkpoint_indices = tuple(
        int((start_index + i * len(centerline) / config.checkpoint_count) % len(centerline))
        for i in range(1, config.checkpoint_count + 1)
    )

    metadata = {
        "name": name,
        "width": config.width,
        "height": config.height,
        "road_width": road_width,
        "start_index": start_index,
        "start_angle_deg": start_angle_deg,
        "checkpoint_indices": checkpoint_indices,
        "centerline": np.round(centerline, 3).tolist(),
    }

    mask_image.save(tracks_dir / f"{name}_mask.png", optimize=True)
    display.save(tracks_dir / f"{name}.png", optimize=True)
    with (tracks_dir / f"{name}.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
        handle.write("\n")


def ensure_track_assets(
    *,
    config: SimulationConfig | None = None,
    tracks_dir: Path = TRACKS_DIR,
    force: bool = False,
) -> None:
    config = config or SimulationConfig()
    expected = [
        tracks_dir / f"{name}{suffix}"
        for name in TRACK_CHOICES
        for suffix in (".png", "_mask.png", ".json")
    ]
    if force or not all(path.exists() for path in expected):
        for name in TRACK_CHOICES:
            generate_track_asset(name, config=config, tracks_dir=tracks_dir)
