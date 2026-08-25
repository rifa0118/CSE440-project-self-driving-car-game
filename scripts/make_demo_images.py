"""Create documentation images from the real simulator and trained model."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.agent import DQNAgent  # noqa: E402
from config import MODELS_DIR  # noqa: E402
from game.environment import RacingEnv  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "docs" / "images"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _draw_car(draw: ImageDraw.ImageDraw, env: RacingEnv, offset: tuple[int, int]) -> None:
    ox, oy = offset
    corners = [(float(x) + ox, float(y) + oy) for x, y in env.car.corners()]
    shadow = [(x + 3, y + 4) for x, y in corners]
    draw.polygon(shadow, fill=(16, 18, 22))
    draw.polygon(corners, fill=(224, 67, 54), outline=(248, 250, 253), width=2)

    heading = env.car.heading_vector
    normal = np.array([-heading[1], heading[0]], dtype=np.float32)
    center = env.car.position + heading * 4.0
    window = [
        center + heading * 4.0 + normal * 5.0,
        center + heading * 4.0 - normal * 5.0,
        center - heading * 3.0 - normal * 5.0,
        center - heading * 3.0 + normal * 5.0,
    ]
    draw.polygon(
        [(float(x) + ox, float(y) + oy) for x, y in window],
        fill=(126, 194, 229),
    )


def make_gameplay_image() -> Path:
    env = RacingEnv("easy")
    agent, _ = DQNAgent.from_checkpoint(MODELS_DIR / "easy_best.pth", device="cpu")
    state = env.reset(seed=440)
    for _ in range(128):
        action = agent.select_action(state, evaluate=True)
        state, _, terminated, truncated, _ = env.step(action)
        if terminated or truncated:
            break

    canvas = Image.new("RGB", (1320, 720), (17, 23, 33))
    draw = ImageDraw.Draw(canvas)
    track_offset = (20, 52)
    canvas.paste(env.track.display_image, track_offset)
    draw.rectangle((19, 51, 980, 693), outline=(105, 118, 136), width=1)
    draw.text((20, 13), "CSE440 • Watch Trained AI", font=_font(28, bold=True), fill=(238, 242, 248))

    assert env.last_sensor_reading is not None
    origin = (float(env.car.position[0]) + track_offset[0], float(env.car.position[1]) + track_offset[1])
    for endpoint, distance in zip(
        env.last_sensor_reading.endpoints,
        env.last_sensor_reading.distances,
        strict=True,
    ):
        end = (float(endpoint[0]) + track_offset[0], float(endpoint[1]) + track_offset[1])
        ratio = float(distance / env.config.sensor_max_distance)
        colour = (255, 181, 62) if ratio < 0.40 else (86, 205, 255)
        draw.line((origin, end), fill=colour, width=2)
        draw.ellipse((end[0] - 3, end[1] - 3, end[0] + 3, end[1] + 3), fill=colour)
    _draw_car(draw, env, track_offset)

    panel = (1000, 52, 1300, 692)
    draw.rounded_rectangle(panel, radius=12, fill=(24, 33, 47), outline=(61, 79, 104), width=1)
    draw.text((1020, 72), "Watch Trained AI", font=_font(28, bold=True), fill=(240, 244, 250))
    stats = [
        ("Track", "Easy"),
        ("Reward", f"{env.episode_reward:.0f}"),
        ("Lap", str(env.lap_count)),
        ("Speed", f"{env.car.speed:.2f}"),
        ("Progress", f"{env.unwrapped_progress / env.track.point_count * 100:.1f}%"),
        ("Policy", "Greedy (ε = 0)"),
        ("Sensors", "On"),
    ]
    y = 130
    for label, value in stats:
        draw.text((1020, y), label, font=_font(16), fill=(137, 154, 178))
        right = draw.textbbox((0, 0), value, font=_font(17))[2]
        draw.text((1280 - right, y), value, font=_font(17), fill=(236, 241, 248))
        y += 38

    controls_y = 445
    draw.text((1020, controls_y), "Controls", font=_font(20, bold=True), fill=(219, 229, 243))
    controls_y += 42
    for line in ("R reset AI car", "G sensor rays", "Esc main menu"):
        draw.text((1020, controls_y), line, font=_font(16), fill=(166, 181, 202))
        controls_y += 30

    status_box = (1016, 618, 1284, 674)
    draw.rounded_rectangle(status_box, radius=8, fill=(34, 50, 70))
    draw.text((1026, 630), "Included DQN model is driving", font=_font(14), fill=(199, 216, 239))
    draw.text((1026, 649), "using five live distance sensors.", font=_font(14), fill=(199, 216, 239))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / "gameplay.png"
    canvas.save(output, optimize=True)
    return output


def make_architecture_image() -> Path:
    canvas = Image.new("RGB", (1500, 520), (247, 249, 252))
    draw = ImageDraw.Draw(canvas)
    title_font = _font(30, bold=True)
    body_font = _font(20, bold=True)
    small_font = _font(16)
    draw.text((50, 28), "Self-Driving Car: Agent–Environment Training Loop", font=title_font, fill=(25, 36, 51))

    boxes = [
        ("Read State", "5 ray distances + speed"),
        ("DQN Agent", "6 → 64 → 64 → 4"),
        ("Choose Action", "left / right / straight / brake"),
        ("Car Physics", "position, speed, angle"),
        ("Reward + Replay", "store transition and update network"),
    ]
    x_positions = [50, 335, 620, 905, 1190]
    box_width = 245
    box_height = 150
    top = 170
    for index, ((heading, detail), x) in enumerate(zip(boxes, x_positions, strict=True)):
        fill = (36, 63, 101) if index in (1, 4) else (58, 126, 189)
        draw.rounded_rectangle((x, top, x + box_width, top + box_height), radius=18, fill=fill)
        heading_box = draw.textbbox((0, 0), heading, font=body_font)
        heading_width = heading_box[2] - heading_box[0]
        draw.text((x + (box_width - heading_width) / 2, top + 35), heading, font=body_font, fill=(255, 255, 255))
        # Simple word wrapping.
        words = detail.split()
        lines: list[str] = []
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if draw.textlength(candidate, font=small_font) < box_width - 28:
                line = candidate
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        yy = top + 78
        for line in lines:
            width = draw.textlength(line, font=small_font)
            draw.text((x + (box_width - width) / 2, yy), line, font=small_font, fill=(222, 235, 250))
            yy += 23

        if index < len(boxes) - 1:
            start = (x + box_width + 8, top + box_height / 2)
            end = (x_positions[index + 1] - 8, top + box_height / 2)
            draw.line((start, end), fill=(47, 69, 97), width=4)
            arrow = [(end[0], end[1]), (end[0] - 13, end[1] - 8), (end[0] - 13, end[1] + 8)]
            draw.polygon(arrow, fill=(47, 69, 97))

    draw.text((430, 390), "Repeat for thousands of steps until the driving policy improves", font=_font(22), fill=(60, 75, 96))
    # Return arrow under the boxes.
    draw.arc((170, 350, 1320, 485), start=5, end=175, fill=(73, 102, 139), width=4)
    draw.polygon([(173, 408), (189, 399), (188, 417)], fill=(73, 102, 139))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / "architecture.png"
    canvas.save(output, optimize=True)
    return output


def main() -> None:
    print(make_gameplay_image())
    print(make_architecture_image())


if __name__ == "__main__":
    main()
