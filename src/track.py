# src/track.py
import random

from src.config import (
    ROAD_A,
    ROAD_B,
    RUMBLE_A,
    RUMBLE_B,
    SAND_A,
    SAND_B,
    SEG_LEN,
    TRACK_SEED,
)
from src.objects import Barricade, FlowerPatch, OverpassBridge, Tree


class Segment:
    __slots__ = ("colors", "curve", "index", "objects", "world_x")

    def __init__(self, index, curve, colors):
        self.index = index
        self.curve = curve
        self.world_x = 0.0
        self.colors = colors
        self.objects = []


class Track:
    def __init__(self):
        self.seg_len = SEG_LEN
        self.segments = []
        self._build()

    def _build(self):
        layout = [
            (100, 0.0),
            (40, 0.9),
            (60, 0.0),
            (35, -1.4),
            (80, 0.0),
            (30, 2.0),
            (50, 0.0),
            (40, -2.1),
            (90, 0.0),
            (37, 1.0),
            (65, 0.0),
        ]
        idx = 0
        for length, curve in layout:
            for _ in range(length):
                even = (idx // 3) % 2 == 0
                colors = {
                    "sand": SAND_A if even else SAND_B,
                    "road": ROAD_A if even else ROAD_B,
                    "rumble": RUMBLE_A if even else RUMBLE_B,
                    "lane": even,
                }
                self.segments.append(Segment(idx, curve, colors))
                idx += 1

        wx = 0.0
        for seg in self.segments:
            wx += seg.curve * 8.0
            seg.world_x = wx

        # Use a seeded RNG for deterministic barricade placement
        # so the AI trains on a consistent track layout.
        rng = random.Random(TRACK_SEED)

        barricade_cooldown = 0
        for i, seg in enumerate(self.segments):
            if barricade_cooldown > 0:
                barricade_cooldown -= 1

            if i % 12 == 0:
                seg.objects.append(Tree(-2.5))
            elif i % 12 == 3:
                seg.objects.append(FlowerPatch(-3.2))
            elif i % 12 == 6:
                seg.objects.append(Tree(2.5))
            elif i % 12 == 9:
                seg.objects.append(FlowerPatch(3.2))

            if i > 50 and i % 150 == 0:
                seg.objects.append(OverpassBridge())

            if i > 5 and barricade_cooldown == 0 and rng.random() < 0.005:
                # Deterministic barricade placement anywhere on the road
                lane = rng.uniform(-0.8, 0.8)
                seg.objects.append(Barricade(lane))
                barricade_cooldown = 30  # Prevent another barricade for 30 segments

    @property
    def total_length(self):
        return len(self.segments) * self.seg_len

    def get_seg(self, world_z: float) -> Segment:
        idx = int(world_z / self.seg_len) % len(self.segments)
        return self.segments[idx]
