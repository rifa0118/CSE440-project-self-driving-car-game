# Final Verification Report

**Release status in this container:** `PASS_WITH_ENVIRONMENT_BLOCKER`  
**Date:** 2026-08-25

## Scope

Final verification of the CSE440 2D self-driving car project against the supplied project plan and the release's own runtime contracts. The runnable release has one project-plan-compliant source of truth; historical GitHub branches are documented in `docs/BRANCH_AUDIT.md` rather than copied into the runtime tree.

## Implemented project-plan contracts

- Python + Pygame user interface and PyTorch DQN.
- Image-based 2D tracks with white-road/black-wall collision masks.
- Five ray sensors plus speed = six-value state.
- Four actions: left, right, straight, brake.
- Reward shaping for forward progress/checkpoints/lap/collision/stationary behavior.
- 6 -> 64 -> 64 -> 4 DQN, replay memory, target network, epsilon-greedy exploration.
- Manual driving, live training, pause/continue/save, trained-policy playback, evaluation, Easy/Medium/Hard, car colours, graphs, checkpoints.

## Static/build verification

- Python compilation: **PASS**.
- Automated pytest suite: **PASS — 20/20**.
- Independent release verifier: **PASS except Pygame runtime is environment-blocked**.
- Unfinished production markers (`TODO`, `FIXME`, `HACK`, `NotImplementedError`): **none**.
- Generated cache/junk in release tree: **none at verification time**.
- Security-sensitive source scan: no shell/subprocess/eval/exec/network-command path found in production source; no embedded credential assignment found.
- Ruff lint: **ENVIRONMENT_BLOCKED** because Ruff is not installed in this container and outbound package installation is unavailable. The project pins Ruff in `requirements-dev.txt` for the isolated Windows setup.
- Host `pip check`: **PRE-EXISTING ENVIRONMENT CONFLICT** (`moviepy` expects Pillow <12 while the host has Pillow 12.3). This is outside this project; `setup_windows.bat` creates an isolated virtual environment before installing project dependencies.

## Runtime / model verification

The independent verifier reloaded every packaged best checkpoint, validated the exact 6 -> 64 -> 64 -> 4 tensor shapes and finite tensors, and ran 20 deterministic greedy episodes per track:

| Track | Episodes | Completed | Success | Collisions | Mean reward | Mean lap steps |
|---|---:|---:|---:|---:|---:|---:|
| Easy | 20 | 20 | 100% | 0 | 631.0 | 295 |
| Medium | 20 | 20 | 100% | 0 | 576.0 | 241 |
| Hard | 20 | 20 | 100% | 0 | 593.0 | 259 |

Production CLI paths also passed for `describe` and `evaluate` on Easy, Medium, and Hard. Medium and Hard use curriculum continuation from easier checkpoints; no claim is made for independent from-scratch convergence, arbitrary-start generalization, or unseen tracks.

## Pygame GUI runtime boundary

Actual Pygame display initialization is **ENVIRONMENT_BLOCKED** in this container because the `pygame` package is not installed and the container cannot download packages. This was not converted to PASS. `setup_windows.bat` installs the runtime into an isolated `.venv`, and `verify_project.bat` then runs the verifier with `--strict-pygame`, so the destination Windows PC must pass a real Pygame dummy-display initialization before presentation use.

## Adversarial verification

The verifier was attacked with three deliberately broken release copies and correctly failed each one:

1. Missing Hard track image — rejected.
2. Corrupt Easy model checkpoint — rejected.
3. Malformed Easy evaluation JSON — rejected.

Evidence is recorded in `verification/adversarial_verification.json`.

## Office artifacts

- Editable DOCX report: valid Office ZIP and rendered successfully to 12 pages.
- Editable PPTX presentation: valid Office ZIP and rendered successfully to 13 slides.
- Updated evaluation evidence presents Easy, Medium, and Hard together and states the curriculum/generalization limitation.
- Team identity fields remain deliberately blank because they were not supplied; see `submission/TEAM_DETAILS_REQUIRED.md`.

## Remaining external/manual items

These are not software defects and cannot be truthfully completed without external information/hardware:

1. Fill real student names/IDs, section, faculty, submission date, presenter details, and truthful contribution breakdown.
2. On the presentation Windows PC, run `setup_windows.bat`, then `verify_project.bat`.
3. Open Manual Drive and Watch Trained AI once on that PC to verify the real graphics/input/audio-driver stack.

## Final classification

**PASS_WITH_ENVIRONMENT_BLOCKER** in this container. No known locally reproducible code, model, asset, documentation, or package-integrity defect remains. A strict GUI-runtime PASS requires the destination machine because Pygame is unavailable here.
