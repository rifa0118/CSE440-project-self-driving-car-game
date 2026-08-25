from __future__ import annotations

import logging

from game.app import SelfDrivingCarApp


class _FailingTrainer:
    def save_now(self) -> None:
        raise OSError("disk full")


class _SavingTrainer:
    def __init__(self) -> None:
        self.saved = False

    def save_now(self) -> None:
        self.saved = True


def _app_without_pygame(trainer):
    app = object.__new__(SelfDrivingCarApp)
    app.live_trainer = trainer
    app.mode = "training"
    app.running = True
    app.shutdown_error = None
    return app


def test_shutdown_saves_live_training_checkpoint() -> None:
    trainer = _SavingTrainer()
    app = _app_without_pygame(trainer)

    app._shutdown()

    assert trainer.saved is True
    assert app.shutdown_error is None
    assert app.running is False


def test_shutdown_surfaces_save_failure_in_log_and_state(caplog) -> None:
    app = _app_without_pygame(_FailingTrainer())

    with caplog.at_level(logging.ERROR, logger="game.app"):
        app._shutdown()

    assert app.running is False
    assert app.shutdown_error == "OSError: disk full"
    assert "Failed to save the live-training checkpoint during shutdown" in caplog.text
