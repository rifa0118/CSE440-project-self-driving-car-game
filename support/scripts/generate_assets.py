"""Regenerate all deterministic track assets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import SimulationConfig, TRACKS_DIR  # noqa: E402
from game.track import ensure_track_assets  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite existing assets")
    args = parser.parse_args()
    ensure_track_assets(config=SimulationConfig(), tracks_dir=TRACKS_DIR, force=args.force)
    print(f"Track assets are ready in {TRACKS_DIR}")


if __name__ == "__main__":
    main()
