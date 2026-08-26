"""Independent release verifier for the CSE440 self-driving car project.

The verifier is deliberately separate from the test suite. It validates the
packaged files, model architecture/metadata, deterministic evaluation evidence,
launcher prerequisites, and (when available) a real Pygame dummy-display smoke
initialization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import torch
from PIL import Image

from ai.agent import DQNAgent
from ai.trainer import evaluate_agent
from game.environment import RacingEnv
from game.track import Track

TRACKS = ("easy", "medium", "hard")
EXPECTED_SHAPES = {
    "layers.0.weight": (64, 6),
    "layers.0.bias": (64,),
    "layers.2.weight": (64, 64),
    "layers.2.bias": (64,),
    "layers.4.weight": (4, 64),
    "layers.4.bias": (4,),
}


class VerificationFailure(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_paths() -> list[Path]:
    paths = [
        PROJECT_ROOT / "main.py",
        PROJECT_ROOT / "requirements.txt",
        PROJECT_ROOT / "setup_windows.bat",
        PROJECT_ROOT / "run_game.bat",
        PROJECT_ROOT / "verify_project.bat",
        PROJECT_ROOT / "ai" / "network.py",
        PROJECT_ROOT / "ai" / "agent.py",
        PROJECT_ROOT / "game" / "environment.py",
        PROJECT_ROOT / "game" / "renderer.py",
        PROJECT_ROOT / "tests",
        PROJECT_ROOT / "submission" / "CSE440_Self_Driving_Car_Project_Report.docx",
        PROJECT_ROOT / "submission" / "CSE440_Self_Driving_Car_Presentation.pptx",
    ]
    for track in TRACKS:
        paths.extend(
            [
                PROJECT_ROOT / "assets" / "tracks" / f"{track}.png",
                PROJECT_ROOT / "assets" / "tracks" / f"{track}_mask.png",
                PROJECT_ROOT / "assets" / "tracks" / f"{track}.json",
                PROJECT_ROOT / "models" / f"{track}_best.pth",
                PROJECT_ROOT / "results" / f"{track}_pretrained_evaluation_20.json",
            ]
        )
    return paths


def check_required_paths() -> dict[str, Any]:
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in _required_paths() if not path.exists()]
    if missing:
        raise VerificationFailure("Missing required release paths: " + ", ".join(missing))
    return {"required_paths": len(_required_paths())}


def check_source_completeness() -> dict[str, Any]:
    markers = re.compile(r"\b(TODO|FIXME|HACK|NotImplementedError)\b")
    findings: list[str] = []
    production_roots = [PROJECT_ROOT / "ai", PROJECT_ROOT / "game", PROJECT_ROOT / "utils"]
    production_files = [PROJECT_ROOT / "main.py", PROJECT_ROOT / "config.py"]
    for root in production_roots:
        production_files.extend(root.rglob("*.py"))
    for path in production_files:
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if markers.search(line):
                findings.append(f"{path.relative_to(PROJECT_ROOT)}:{line_no}: {line.strip()}")
    if findings:
        raise VerificationFailure("Unfinished-source markers found:\n" + "\n".join(findings))
    return {"python_files_scanned": len(production_files)}


def check_tracks() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for track_name in TRACKS:
        display = PROJECT_ROOT / "assets" / "tracks" / f"{track_name}.png"
        mask = PROJECT_ROOT / "assets" / "tracks" / f"{track_name}_mask.png"
        metadata = PROJECT_ROOT / "assets" / "tracks" / f"{track_name}.json"
        with Image.open(display) as image:
            image.verify()
        with Image.open(mask) as image:
            image.verify()
        payload = json.loads(metadata.read_text(encoding="utf-8"))
        if payload.get("name") != track_name:
            raise VerificationFailure(f"Track metadata name mismatch for {track_name}")
        track = Track.load(track_name)
        if track.point_count < 100:
            raise VerificationFailure(f"Track {track_name} centerline is unexpectedly short")
        if not track.is_road(float(track.start_position[0]), float(track.start_position[1])):
            raise VerificationFailure(f"Track {track_name} start position is not on-road")
        result[track_name] = {
            "points": track.point_count,
            "road_width": track.road_width,
            "start_index": track.start_index,
        }
    return result


def _load_checkpoint(track: str) -> dict[str, Any]:
    path = PROJECT_ROOT / "models" / f"{track}_best.pth"
    try:
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        checkpoint = torch.load(path, map_location="cpu")
    if int(checkpoint.get("format_version", 0)) != DQNAgent.CHECKPOINT_FORMAT_VERSION:
        raise VerificationFailure(f"Unsupported checkpoint format for {track}")
    if int(checkpoint.get("state_size", -1)) != 6 or int(checkpoint.get("action_size", -1)) != 4:
        raise VerificationFailure(f"Checkpoint dimensions are wrong for {track}")
    state = checkpoint.get("policy_state_dict", {})
    for key, expected_shape in EXPECTED_SHAPES.items():
        tensor = state.get(key)
        if tensor is None or tuple(tensor.shape) != expected_shape:
            raise VerificationFailure(f"{track}: {key} shape mismatch")
        if not torch.isfinite(tensor).all().item():
            raise VerificationFailure(f"{track}: {key} contains non-finite values")
    metadata = dict(checkpoint.get("metadata", {}))
    if metadata.get("track") != track:
        raise VerificationFailure(f"Checkpoint metadata track mismatch for {track}")
    return checkpoint


def check_models_and_evaluations(episodes: int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for track in TRACKS:
        checkpoint = _load_checkpoint(track)
        model_path = PROJECT_ROOT / "models" / f"{track}_best.pth"
        agent, metadata = DQNAgent.from_checkpoint(model_path, device="cpu")
        env = RacingEnv(track)
        summary = evaluate_agent(env, agent, episodes=episodes, verbose=False)
        if summary["success_rate"] != 1.0:
            raise VerificationFailure(
                f"{track}: packaged best checkpoint achieved only {summary['success_rate']:.1%} success"
            )
        if summary["total_collisions"] != 0:
            raise VerificationFailure(f"{track}: packaged best checkpoint collided during verification")
        evidence_path = PROJECT_ROOT / "results" / f"{track}_pretrained_evaluation_20.json"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        saved_summary = evidence.get("summary", {})
        if int(saved_summary.get("episodes", 0)) != 20:
            raise VerificationFailure(f"{track}: saved evaluation does not contain 20 episodes")
        if float(saved_summary.get("success_rate", 0.0)) != 1.0:
            raise VerificationFailure(f"{track}: saved evaluation is not 100% successful")
        if int(saved_summary.get("total_collisions", -1)) != 0:
            raise VerificationFailure(f"{track}: saved evaluation contains collisions")
        if not math.isclose(
            float(metadata.get("evaluation_success_rate", -1)), 1.0, abs_tol=1e-12
        ):
            raise VerificationFailure(f"{track}: checkpoint metadata lacks validated evaluation")
        out[track] = {
            "model_sha256": _sha256(model_path),
            "verified_episodes": episodes,
            "verified_success_rate": summary["success_rate"],
            "verified_collisions": summary["total_collisions"],
            "verified_mean_reward": summary["mean_reward"],
            "verified_mean_lap_steps": summary["mean_lap_steps"],
            "checkpoint_episode": checkpoint.get("metadata", {}).get("episode"),
            "training_type": checkpoint.get("metadata", {}).get("training_type", "unspecified"),
        }
    return out


def check_office_files() -> dict[str, Any]:
    files = [
        PROJECT_ROOT / "submission" / "CSE440_Self_Driving_Car_Project_Report.docx",
        PROJECT_ROOT / "submission" / "CSE440_Self_Driving_Car_Presentation.pptx",
    ]
    result = {}
    for path in files:
        if not zipfile.is_zipfile(path):
            raise VerificationFailure(f"Office file is not a valid ZIP container: {path.name}")
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                raise VerificationFailure(f"Corrupt Office member in {path.name}: {bad}")
        result[path.name] = _sha256(path)
    return result


def check_no_packaging_junk() -> dict[str, Any]:
    forbidden = []
    for path in PROJECT_ROOT.rglob("*"):
        parts = set(path.relative_to(PROJECT_ROOT).parts)
        if ".venv" in parts or "__pycache__" in parts or ".pytest_cache" in parts:
            forbidden.append(str(path.relative_to(PROJECT_ROOT)))
        if path.suffix in {".pyc", ".pyo"}:
            forbidden.append(str(path.relative_to(PROJECT_ROOT)))
    if forbidden:
        raise VerificationFailure("Release contains generated runtime junk: " + ", ".join(forbidden[:20]))
    return {"forbidden_entries": 0}


def check_manifest() -> dict[str, Any]:
    manifest = PROJECT_ROOT / "SHA256SUMS.txt"
    if not manifest.exists():
        return {"status": "NOT_PRESENT"}
    checked = 0
    for raw_line in manifest.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        digest, relative = line.split("  ", 1)
        path = PROJECT_ROOT / relative
        if not path.is_file():
            raise VerificationFailure(f"Manifest path missing: {relative}")
        if _sha256(path) != digest:
            raise VerificationFailure(f"Manifest hash mismatch: {relative}")
        checked += 1
    return {"files_checked": checked}


def check_pygame_runtime(strict: bool) -> dict[str, Any]:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    try:
        import pygame
    except ModuleNotFoundError as exc:
        if strict:
            raise VerificationFailure(
                "Pygame is not installed in this environment. Run setup_windows.bat or install requirements.txt."
            ) from exc
        return {"status": "ENVIRONMENT_BLOCKED", "reason": "pygame is not installed"}

    pygame.init()
    try:
        surface = pygame.display.set_mode((320, 200))
        surface.fill((20, 30, 40))
        pygame.draw.rect(surface, (220, 60, 60), (20, 20, 80, 40))
        pygame.display.flip()
        return {"status": "PASS", "pygame_version": pygame.version.ver}
    finally:
        pygame.quit()


def run(*, episodes: int, strict_pygame: bool) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    checks["required_paths"] = check_required_paths()
    checks["source_completeness"] = check_source_completeness()
    checks["tracks"] = check_tracks()
    checks["models"] = check_models_and_evaluations(episodes)
    checks["office_files"] = check_office_files()
    checks["packaging_junk"] = check_no_packaging_junk()
    checks["manifest"] = check_manifest()
    checks["pygame_runtime"] = check_pygame_runtime(strict_pygame)
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument(
        "--strict-pygame",
        action="store_true",
        help="fail instead of reporting ENVIRONMENT_BLOCKED when Pygame is unavailable",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.episodes <= 0:
        parser.error("--episodes must be positive")

    try:
        checks = run(episodes=args.episodes, strict_pygame=args.strict_pygame)
        payload = {"status": "PASS", "checks": checks}
        if checks["pygame_runtime"].get("status") == "ENVIRONMENT_BLOCKED":
            payload["status"] = "PASS_WITH_ENVIRONMENT_BLOCKER"
    except Exception as exc:
        payload = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
        if args.output:
            args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
