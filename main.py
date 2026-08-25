"""Command-line entry point for the CSE440 self-driving car project."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from ai.agent import DQNAgent
from ai.trainer import Trainer, evaluate_agent
from config import MODELS_DIR, TRACK_CHOICES, TrainingConfig
from game.environment import RacingEnv
from game.track import ensure_track_assets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="2D self-driving car game using DQN reinforcement learning",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("gui", help="open the complete Pygame application")

    train = subparsers.add_parser("train", help="train a DQN agent without opening a window")
    train.add_argument("--track", choices=TRACK_CHOICES, default="easy")
    train.add_argument("--episodes", type=int, default=500)
    train.add_argument("--seed", type=int, default=440)
    train.add_argument("--device", default="cpu", help="cpu, cuda, cuda:0, or auto")
    train.add_argument("--resume", type=Path, help="resume network/optimizer from a checkpoint")
    train.add_argument("--run-dir", type=Path, help="custom results directory")
    train.add_argument("--quiet", action="store_true")
    train.add_argument("--no-plots", action="store_true")

    evaluate = subparsers.add_parser("evaluate", help="evaluate a trained model greedily")
    evaluate.add_argument("--track", choices=TRACK_CHOICES, default="easy")
    evaluate.add_argument("--model", type=Path, help="checkpoint path; defaults to <track>_best.pth")
    evaluate.add_argument("--episodes", type=int, default=20)
    evaluate.add_argument("--device", default="cpu")
    evaluate.add_argument("--output", type=Path, help="optional JSON output path")

    assets = subparsers.add_parser("generate-assets", help="regenerate track PNG/JSON files")
    assets.add_argument("--force", action="store_true")

    subparsers.add_parser("describe", help="print environment/state/action details as JSON")

    return parser


def command_train(args: argparse.Namespace) -> int:
    if args.episodes <= 0:
        raise ValueError("--episodes must be positive")
    environment = RacingEnv(args.track)
    training_config = TrainingConfig(
        episodes=args.episodes,
        seed=args.seed,
        device=args.device,
    )
    agent = DQNAgent(environment.state_size, environment.action_size, training_config)
    start_episode = 1
    if args.resume is not None:
        metadata = agent.load(args.resume, load_optimizer=True)
        start_episode = int(metadata.get("episode", 0)) + 1
        print(f"Resumed {args.resume} from episode {start_episode - 1}")

    trainer = Trainer(
        environment,
        agent,
        training_config=training_config,
        run_dir=args.run_dir,
    )
    metrics = trainer.train(
        episodes=args.episodes,
        start_episode=start_episode,
        verbose=not args.quiet,
        generate_plots=not args.no_plots,
    )
    final_episode = start_episode + args.episodes - 1
    final_path = trainer.save_final(final_episode)
    print(json.dumps(metrics.summary(), indent=2))
    print(f"Best model:   {trainer.best_model_path}")
    print(f"Latest model: {final_path}")
    print(f"Results:      {trainer.run_dir}")
    return 0


def command_evaluate(args: argparse.Namespace) -> int:
    model_path = args.model or (MODELS_DIR / f"{args.track}_best.pth")
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found: {model_path}. Train it with: "
            f"python main.py train --track {args.track}"
        )
    agent, metadata = DQNAgent.from_checkpoint(model_path, device=args.device)
    environment = RacingEnv(args.track)
    if agent.state_size != environment.state_size or agent.action_size != environment.action_size:
        raise ValueError("The model architecture does not match the selected environment")
    summary = evaluate_agent(environment, agent, episodes=args.episodes, verbose=True)
    payload = {
        "track": args.track,
        "model": str(model_path),
        "metadata": metadata,
        "summary": summary,
    }
    print(json.dumps(payload, indent=2))
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Saved evaluation to {args.output}")
    return 0


def command_gui() -> int:
    from game.app import launch_gui

    return launch_gui()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "gui"

    try:
        if command == "gui":
            return command_gui()
        if command == "train":
            return command_train(args)
        if command == "evaluate":
            return command_evaluate(args)
        if command == "generate-assets":
            ensure_track_assets(force=args.force)
            print("Track assets generated successfully.")
            return 0
        if command == "describe":
            print(json.dumps(RacingEnv("easy").describe(), indent=2))
            return 0
        parser.error(f"Unknown command: {command}")
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
