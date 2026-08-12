# src/car.py
import math
import pygame
from src.config import (MAX_SPEED, ACCEL, BRAKE, FRICTION,
                         OFFROAD_SLOW, STEER_SPD, CENTRIFUGAL,
                         SCREEN_WIDTH, SCREEN_HEIGHT)

CAR_W = 200
CAR_H = 125
CAR_X = SCREEN_WIDTH  // 2
CAR_Y = SCREEN_HEIGHT - 80


class Car:
    def __init__(self):
        self.speed    = 0.0
        self.player_x = 0.0   # road offset: 0=centre, ±1=edges
        self.player_z = 0.0   # distance along track
        self.lean     = 0.0   # visual tilt degrees
        self._img     = None
        self._load()

    def _load(self):
        try:
            raw       = pygame.image.load("assets/car.png")
            self._img = pygame.transform.scale(raw, (CAR_W, CAR_H))
        except Exception:
            self._img = None

    def update(self, dt: float, curve: float, action=None):

    # action:
    # 0 = nothing
    # 1 = left
    # 2 = right
    # 3 = accelerate
    # 4 = brake

        if action is None:
            keys = pygame.key.get_pressed()
            left  = keys[pygame.K_LEFT] or keys[pygame.K_a]
            right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
            accel = keys[pygame.K_UP] or keys[pygame.K_w]
            brake = keys[pygame.K_DOWN] or keys[pygame.K_s]
        else:
            left  = action == 1
            right = action == 2
            accel = action == 3
            brake = action == 4

        # ── Throttle / brake ─────────────────────────────────────────────────
        if accel or keys[pygame.K_UP] or keys[pygame.K_w]:
            self.speed = min(self.speed + ACCEL * dt, MAX_SPEED)
        elif brake or keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.speed = max(self.speed - BRAKE * dt, -MAX_SPEED * 0.25)
        else:
            drag = FRICTION * dt
            self.speed += -drag if self.speed > 0 else (drag if self.speed < 0 else 0)
            if abs(self.speed) < drag:
                self.speed = 0.0

        # ── Steering ─────────────────────────────────────────────────────────
        steer = 0.0
        ratio = abs(self.speed) / MAX_SPEED
        if self.speed != 0:
            rate = STEER_SPD * ratio * dt
            if left or keys[pygame.K_LEFT] or keys[pygame.K_a]:
                steer      = -rate
                self.lean  = max(self.lean - 2.2, -13)
            elif right or keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                steer      = rate
                self.lean  = min(self.lean + 2.2,  13)
        if steer == 0:
            self.lean *= 0.82   # snap back

        self.player_x += steer

        # Centrifugal push on bends
        self.player_x -= curve * CENTRIFUGAL * self.speed * dt

        # Off-road penalty
        if abs(self.player_x) > 1.0:
            self.speed *= OFFROAD_SLOW
        self.player_x = max(-2.8, min(2.8, self.player_x))

        # Advance along track
        self.player_z += self.speed * dt
    

    def draw(self, screen: pygame.Surface):
        if self._img:
            rot  = pygame.transform.rotate(self._img, -self.lean)
            rect = rot.get_rect(center=(CAR_X, CAR_Y))
            screen.blit(rot, rect)
        else:
            self._fallback(screen)

    def _fallback(self, screen: pygame.Surface):
        """Rich procedural player car drawn when asset is missing."""
        surf = pygame.Surface((CAR_W, CAR_H), pygame.SRCALPHA)

        # Body
        pygame.draw.rect(surf, (210, 35, 35),
                         (0, CAR_H // 3, CAR_W, CAR_H * 2 // 3),
                         border_radius=10)
        # Cabin
        cab_m = int(CAR_W * 0.12)
        pygame.draw.rect(surf, (160, 20, 20),
                         (cab_m, 0, CAR_W - cab_m * 2, CAR_H * 2 // 3),
                         border_radius=12)
        # Windscreen
        gw = int(CAR_W * 0.56)
        gh = int(CAR_H * 0.30)
        gx = (CAR_W - gw) // 2
        pygame.draw.rect(surf, (180, 225, 255),
                         (gx, int(CAR_H * 0.06), gw, gh), border_radius=5)
        pygame.draw.rect(surf, (220, 242, 255),
                         (gx + gw // 5, int(CAR_H * 0.09), gw // 5, gh // 2))

        # Highlight stripe
        pygame.draw.rect(surf, (245, 70, 70),
                         (0, CAR_H // 3, CAR_W, int(CAR_H * 0.07)),
                         border_radius=5)

        # Tail-lights
        tl_w, tl_h = int(CAR_W * 0.18), int(CAR_H * 0.10)
        tl_y = int(CAR_H * 0.75)
        pygame.draw.rect(surf, (255, 60, 0),  (int(CAR_W*0.04), tl_y, tl_w, tl_h), border_radius=2)
        pygame.draw.rect(surf, (255, 60, 0),  (CAR_W - int(CAR_W*0.04) - tl_w, tl_y, tl_w, tl_h), border_radius=2)
        # Bright cores
        pygame.draw.rect(surf, (255, 190, 150),
                         (int(CAR_W*0.06), tl_y + tl_h//4, tl_w//2, tl_h//2))
        pygame.draw.rect(surf, (255, 190, 150),
                         (CAR_W - int(CAR_W*0.06) - tl_w//2, tl_y + tl_h//4, tl_w//2, tl_h//2))

        # Bumper
        pygame.draw.rect(surf, (50, 50, 55),
                         (0, CAR_H - int(CAR_H*0.09), CAR_W, int(CAR_H*0.09)),
                         border_radius=6)

        # Licence plate
        pl_w, pl_h = int(CAR_W * 0.30), int(CAR_H * 0.08)
        pygame.draw.rect(surf, (240, 240, 180),
                         ((CAR_W - pl_w) // 2, CAR_H - int(CAR_H*0.09) - pl_h - 1,
                          pl_w, pl_h))

        # Outline
        pygame.draw.rect(surf, (20, 20, 25),
                         (0, CAR_H // 3, CAR_W, CAR_H * 2 // 3),
                         width=2, border_radius=10)
        pygame.draw.rect(surf, (15, 15, 20),
                         (cab_m, 0, CAR_W - cab_m * 2, CAR_H * 2 // 3),
                         width=2, border_radius=12)

        rot  = pygame.transform.rotate(surf, -self.lean)
        rect = rot.get_rect(center=(CAR_X, CAR_Y))
        screen.blit(rot, rect)
