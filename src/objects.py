# src/objects.py

import random

import pygame


class Tree:
    def __init__(self, offset_x: float):
        self.offset_x = offset_x
        self.BASE_W = 800
        self.BASE_H = 1200
        self._img = None
        self._load()

    def _load(self):
        try:
            tree_files = ["assets/tree_1.png", "assets/tree_2.png", "assets/tree_3.png"]
            raw = pygame.image.load(random.choice(tree_files))

            orig_w, orig_h = raw.get_size()
            scale_factor = 1200 / orig_h
            self.BASE_W = int(orig_w * scale_factor)
            self.BASE_H = 1200

            self._img = pygame.transform.scale(raw, (self.BASE_W, self.BASE_H))
        except Exception:  # noqa: BLE001
            self._img = None

    def draw(self, screen, sx: int, sy: int, scale: float):
        h = max(int(self.BASE_H * scale), 6)
        w = max(int(self.BASE_W * scale), 4)
        tw = max(int(9 * scale), 2)
        th = int(h * 0.48)
        cr = max(int(w * 0.46), 3)
        cy = sy - th - int(cr * 0.6)

        if self._img and w > 12:
            img = pygame.transform.scale(self._img, (w, h))
            screen.blit(img, (sx - w // 2, sy - h))
            return

        # Drop shadow (subtle dark ellipse on ground)
        shadow_rx = max(int(cr * 0.55), 2)
        shadow_ry = max(int(cr * 0.18), 1)
        pygame.draw.ellipse(
            screen,
            (60, 120, 30),
            (sx - shadow_rx, sy - shadow_ry, shadow_rx * 2, shadow_ry * 2),
        )

        # Trunk
        pygame.draw.rect(screen, (100, 70, 40), (sx - tw // 2, sy - th, tw, th))
        # Trunk highlight
        pygame.draw.rect(
            screen, (130, 95, 55), (sx - tw // 2 + 1, sy - th, max(tw // 3, 1), th)
        )

        # Dark underside of canopy
        pygame.draw.circle(
            screen, (60, 120, 40), (sx, cy + int(cr * 0.2)), int(cr * 0.85)
        )
        # Main canopy
        pygame.draw.circle(screen, (80, 160, 50), (sx, cy), cr)
        # Mid highlight
        pygame.draw.circle(
            screen,
            (110, 190, 70),
            (sx - int(cr * 0.2), cy - int(cr * 0.2)),
            int(cr * 0.6),
        )
        # Top specular
        pygame.draw.circle(
            screen,
            (150, 220, 90),
            (sx - int(cr * 0.3), cy - int(cr * 0.35)),
            int(cr * 0.3),
        )


class FlowerPatch:
    _COLOURS = [(220, 60, 40), (255, 180, 0), (200, 40, 180), (255, 100, 50)]  # noqa: RUF012

    def __init__(self, offset_x: float):
        self.offset_x = offset_x
        self._col = random.choice(self._COLOURS)

    def draw(self, screen, sx: int, sy: int, scale: float):
        w = max(int(90 * scale), 5)
        h = max(int(26 * scale), 2)
        bx = sx - w // 2
        by = sy - h
        pygame.draw.ellipse(screen, self._col, (bx, by, w, h))
        # Centre dots
        dot_r = max(int(4 * scale), 1)
        for dx in (-w // 4, 0, w // 4):
            pygame.draw.circle(screen, (255, 240, 60), (sx + dx, by + h // 2), dot_r)


class OverpassBridge:
    def __init__(self, offset_x: float = 0.0):
        self.offset_x = offset_x

    def draw(self, screen, sx: int, sy: int, scale: float):
        bx_l = sx - int(1100 * scale)
        bx_r = sx + int(1100 * scale)
        bh = int(440 * scale)
        deck_y = sy - int(220 * scale)
        top_y = sy - bh
        pw = max(int(48 * scale), 2)

        # Concrete pillars
        for bx in (bx_l, bx_r):
            pygame.draw.rect(
                screen, (100, 105, 118), (bx - pw // 2, deck_y, pw, sy - deck_y)
            )
            # Pillar cap
            pygame.draw.rect(
                screen,
                (130, 135, 148),
                (
                    bx - pw,
                    deck_y - max(int(8 * scale), 2),
                    pw * 2,
                    max(int(8 * scale), 2),
                ),
            )

        # Deck
        dh = max(int(28 * scale), 2)
        pygame.draw.rect(screen, (120, 125, 138), (bx_l, deck_y, bx_r - bx_l, dh))
        pygame.draw.rect(
            screen, (145, 150, 165), (bx_l, deck_y, bx_r - bx_l, max(dh // 3, 1))
        )

        if scale > 0.003:
            # Parabolic arch
            steps = 16
            pts = []
            for j in range(steps + 1):
                t = j / steps
                x = bx_l + t * (bx_r - bx_l)
                y = top_y + (deck_y - top_y) * ((2 * t - 1) ** 2)
                pts.append((int(x), int(y)))
            lw = max(int(12 * scale), 2)
            pygame.draw.lines(screen, (210, 40, 40), False, pts, width=lw)

            # Suspension cables
            for j in range(1, steps):
                t = j / steps
                x = bx_l + t * (bx_r - bx_l)
                y_arch = top_y + (deck_y - top_y) * ((2 * t - 1) ** 2)
                clw = max(int(1.5 * scale), 1)
                pygame.draw.line(
                    screen,
                    (190, 195, 210),
                    (int(x), int(y_arch)),
                    (int(x), deck_y),
                    width=clw,
                )


class Barricade:
    def __init__(self, offset_x: float):
        self.offset_x = offset_x
        self.BASE_W = 400
        self.BASE_H = 200
        self._img = None
        self._load()

    def _load(self):
        try:
            raw = pygame.image.load("assets/barricade.png")

            orig_w, orig_h = raw.get_size()
            scale_factor = 200 / orig_h
            self.BASE_W = int(orig_w * scale_factor)
            self.BASE_H = 200

            self._img = pygame.transform.scale(raw, (self.BASE_W, self.BASE_H))
        except Exception:  # noqa: BLE001
            self._img = None

    def draw(self, screen, sx: int, sy: int, scale: float):
        w = max(int(self.BASE_W * scale), 4)
        h = max(int(self.BASE_H * scale), 3)
        bx = sx - w // 2
        by = sy - h

        if self._img and w > 12:
            img = pygame.transform.scale(self._img, (w, h))
            screen.blit(img, (bx, by))
            return

        lw = max(int(6 * scale), 1)
        pygame.draw.rect(screen, (20, 20, 20), (bx + w // 5, by, lw, h))
        pygame.draw.rect(screen, (20, 20, 20), (bx + w * 4 // 5, by, lw, h))
        bh = max(h // 2, 2)
        pygame.draw.rect(
            screen, (255, 120, 0), (bx, by + h // 5, w, bh), border_radius=2
        )
        sw = max(int(14 * scale), 2)
        for i in range(4):
            px = bx + int(w * (0.12 + i * 0.22))
            pts = [
                (px, by + h // 5),
                (px + sw, by + h // 5),
                (px + sw - sw // 2, by + h // 5 + bh),
                (px - sw // 2, by + h // 5 + bh),
            ]
            pygame.draw.polygon(screen, (255, 255, 255), pts)
        pygame.draw.rect(
            screen,
            (0, 0, 0),
            (bx, by + h // 5, w, bh),
            width=max(int(scale), 1),
            border_radius=2,
        )


class TrafficCar:
    BASE_W = 400
    BASE_H = 250

    _PALETTES = [  # noqa: RUF012
        ((210, 210, 215), (170, 170, 175), (120, 160, 200)),
        ((30, 35, 40), (20, 25, 30), (100, 140, 180)),
        ((200, 40, 40), (150, 20, 20), (120, 160, 200)),
        ((40, 80, 180), (20, 50, 140), (120, 160, 200)),
        ((230, 200, 40), (180, 150, 20), (120, 160, 200)),
        ((70, 130, 80), (40, 90, 50), (120, 160, 200)),
        ((120, 120, 120), (90, 90, 90), (120, 160, 200)),
        ((140, 40, 60), (100, 20, 40), (120, 160, 200)),
    ]

    def __init__(self, z: float, offset_x: float, speed: float):
        self.z = z
        self.offset_x = offset_x
        self.speed = speed  # world-units / second
        self._nudge = 0.0  # lateral nudge velocity (world units/s)
        self._palette = random.choice(self._PALETTES)
        self.BASE_W = 400
        self.BASE_H = 250
        self._img = None
        self._load()

    def _load(self):
        try:
            car_files = [
                "assets/traffic_car_1.png",
                "assets/traffic_car_2.png",
                "assets/traffic_car_3.png",
                "assets/traffic_car_4.png",
            ]
            raw = pygame.image.load(random.choice(car_files))

            orig_w, orig_h = raw.get_size()
            scale_factor = 250 / orig_h
            self.BASE_W = int(orig_w * scale_factor)
            self.BASE_H = 250

            self._img = pygame.transform.scale(raw, (self.BASE_W, self.BASE_H))
        except Exception:  # noqa: BLE001
            self._img = None

    def update(self, dt: float, player_z: float, track_length: float):
        self.z = (self.z + self.speed * dt) % track_length

        # Apply and decay lateral nudge
        self.offset_x += self._nudge * dt
        self._nudge *= max(1.0 - 6.0 * dt, 0.0)  # friction damps it quickly

        # Clamp to road (don't let it fly into the grass permanently)
        self.offset_x = max(-0.85, min(0.85, self.offset_x))

        # Respawn far ahead if the player has passed this car
        rel = self.z - player_z
        if rel < -track_length / 2:
            rel += track_length
        elif rel > track_length / 2:
            rel -= track_length

        if rel < -800:
            self.z = (player_z + random.randint(2000, 8000)) % track_length
            self.offset_x = random.uniform(-0.8, 0.8)
            self.speed = random.uniform(30, 100)
            self._nudge = 0.0
            self._palette = random.choice(self._PALETTES)

    def apply_nudge(self, direction: float):
        self._nudge = direction * 1.8  # world units/s lateral kick

    def draw(self, screen, sx: int, sy: int, scale: float):
        w = max(int(self.BASE_W * scale), 6)
        h = max(int(self.BASE_H * scale), 4)
        bx = sx - w // 2
        by = sy - h

        if self._img and w > 12:
            img = pygame.transform.scale(self._img, (w, h))
            screen.blit(img, (bx, by))
            return

        body_col, roof_col, glass_col = self._palette

        # Ground shadow
        srx = max(w // 2, 3)
        sry = max(int(h * 0.07), 2)
        shadow_surf = pygame.Surface((srx * 2, sry * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 70), (0, 0, srx * 2, sry * 2))
        screen.blit(shadow_surf, (sx - srx, sy - sry))

        # Main body (lower half)
        body_rect = pygame.Rect(bx, by + h // 3, w, h * 2 // 3)
        pygame.draw.rect(
            screen, body_col, body_rect, border_radius=max(int(6 * scale), 1)
        )

        # Cabin (upper section, slightly narrower)
        cab_margin = max(int(w * 0.12), 2)
        cab_rect = pygame.Rect(bx + cab_margin, by, w - cab_margin * 2, h * 2 // 3)
        pygame.draw.rect(
            screen, roof_col, cab_rect, border_radius=max(int(8 * scale), 1)
        )

        # Windscreen (rear-facing, so player sees rear window)
        gw = max(int(w * 0.55), 3)
        gh = max(int(h * 0.28), 2)
        gx = sx - gw // 2
        gy = by + max(int(h * 0.06), 1)
        pygame.draw.rect(
            screen, glass_col, (gx, gy, gw, gh), border_radius=max(int(3 * scale), 1)
        )
        # Glass glare stripe
        pygame.draw.rect(
            screen,
            (220, 240, 255),
            (gx + max(gw // 5, 1), gy + max(gh // 6, 1), max(gw // 5, 1), gh // 2),
        )

        # Body highlight stripe along top of lower body
        pygame.draw.rect(
            screen,
            tuple(min(c + 40, 255) for c in body_col),
            (bx, by + h // 3, w, max(int(h * 0.06), 1)),
            border_radius=max(int(3 * scale), 1),
        )

        # Tail-lights (two red rectangles)
        tl_w = max(int(w * 0.16), 2)
        tl_h = max(int(h * 0.10), 1)
        tl_y = by + h * 3 // 4
        pygame.draw.rect(
            screen,
            (255, 50, 50),
            (bx + max(int(w * 0.04), 1), tl_y, tl_w, tl_h),
            border_radius=1,
        )
        pygame.draw.rect(
            screen,
            (255, 50, 50),
            (bx + w - max(int(w * 0.04), 1) - tl_w, tl_y, tl_w, tl_h),
            border_radius=1,
        )
        # Inner bright core of tail-lights
        pygame.draw.rect(
            screen,
            (255, 180, 180),
            (
                bx + max(int(w * 0.06), 1),
                tl_y + max(tl_h // 4, 1),
                max(tl_w // 2, 1),
                max(tl_h // 2, 1),
            ),
        )
        pygame.draw.rect(
            screen,
            (255, 180, 180),
            (
                bx + w - max(int(w * 0.06), 1) - max(tl_w // 2, 1),
                tl_y + max(tl_h // 4, 1),
                max(tl_w // 2, 1),
                max(tl_h // 2, 1),
            ),
        )

        # Rear bumper
        bmp_h = max(int(h * 0.08), 1)
        pygame.draw.rect(
            screen,
            (60, 60, 65),
            (bx, by + h - bmp_h, w, bmp_h),
            border_radius=max(int(3 * scale), 1),
        )

        # Licence plate
        if scale > 0.25:
            pl_w = max(int(w * 0.28), 4)
            pl_h = max(int(h * 0.07), 2)
            pl_x = sx - pl_w // 2
            pl_y = by + h - bmp_h - pl_h - 1
            pygame.draw.rect(screen, (240, 240, 180), (pl_x, pl_y, pl_w, pl_h))

        # Body outline for crispness
        pygame.draw.rect(
            screen,
            (20, 20, 25),
            body_rect,
            width=max(int(1.2 * scale), 1),
            border_radius=max(int(6 * scale), 1),
        )
        pygame.draw.rect(
            screen,
            (15, 15, 20),
            cab_rect,
            width=max(int(1.2 * scale), 1),
            border_radius=max(int(8 * scale), 1),
        )
