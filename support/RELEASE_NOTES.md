# Release Notes - Version 1.0.0

Release date: 2026-08-25

## Completed scope

- Full Python/Pygame racing application with Manual Drive, live DQN training, trained-model playback, evaluation, settings, and clean error messages.
- Easy, Medium, and Hard image-based tracks with collision masks, checkpoints, and deterministic metadata.
- Five distance sensors plus normalized speed as a six-value state.
- Four actions: turn left, turn right, go straight, and brake.
- PyTorch DQN with a 6 -> 64 -> 64 -> 4 architecture, experience replay, target network, epsilon-greedy exploration, gradient clipping, optional Double DQN targets, and atomic checkpoints.
- CPU-friendly headless training and deterministic evaluation commands.
- Included validated trained checkpoints for Easy, Medium, and Hard, with training evidence and 20-episode deterministic evaluation JSON for each track.
- Windows setup/run/train/evaluate scripts.
- Automated tests and GitHub Actions workflow.
- Editable DOCX report, editable PPTX presentation, technical documentation, demo script, and viva preparation.

## Release validation

- Python source compilation: passed.
- Automated tests: 20 passed.
- Greedy evaluation: Easy 20/20, Medium 20/20, and Hard 20/20 completed laps; 0 collisions on all three standard-start evaluations.
- DOCX visual QA: 12 rendered pages checked with no clipping or overlap.
- PPTX visual QA: 13 rendered slides checked with no clipping or overlap.

## Information still required from the team

The report and presentation intentionally retain placeholders for student names and IDs, section, faculty name, submission date, presenter details, and truthful member contributions. Those facts were not supplied and should be completed before submission.

## Scope boundary

Validated best checkpoints are included for Easy, Medium, and Hard. Each completed 20/20 deterministic greedy evaluation episodes from its standard start position with zero collisions. Medium and Hard were trained by curriculum continuation from easier checkpoints; these results do not claim random-start generalization or real-world driving capability. The project is an educational 2D reinforcement-learning environment and is not intended for real vehicle control.
