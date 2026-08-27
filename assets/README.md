# Assets

Tracks are generated locally and deterministically by `scripts/generate_assets.py`.

For each difficulty:

- `<name>.png` is the coloured display track.
- `<name>_mask.png` is the white-road/black-wall collision and sensor mask.
- `<name>.json` stores the centre line, checkpoints, start pose, and road width.

No downloaded artwork is required.
