# CSE440 Project Plan Compliance Matrix

Authority: `docs/reference/Original_Self_Driving_Car_Project_Plan_CSE440.docx`.

| Plan requirement | Production implementation | Verification |
|---|---|---|
| Python | `main.py`, project modules | compile + pytest |
| Pygame UI | `game/app.py`, `game/renderer.py` | strict runtime smoke on a machine with Pygame; setup script installs it |
| PyTorch DQN | `ai/network.py`, `ai/agent.py` | architecture + finite-tensor checks |
| CPU-capable | default `device=cpu`, one Torch thread | all packaged evaluation runs on CPU |
| Image-based 2D tracks | `assets/tracks/*.png`, masks + metadata | image integrity + `Track.load()` |
| Manual keyboard game | GUI Manual Drive mode | Pygame application path |
| Simple car physics | `game/car.py` | physics tests |
| White-road/black-wall collision mask | `assets/tracks/*_mask.png`, `game/track.py` | track/mask tests |
| Five rays | `game/sensors.py` | sensor tests |
| State = five rays + speed | `game/environment.py` | state-size test (=6) |
| 4 actions | `ACTION_CONTROLS` | action-size test (=4) |
| Required reward table | `RewardConfig` | exact reward tests |
| DQN 6-64-64-4 | `ai/network.py` | network + checkpoint tensor-shape tests |
| Experience replay | `ai/replay_buffer.py` | replay-buffer tests |
| Epsilon-greedy | `DQNAgent.select_action()` | agent tests |
| Target network | `DQNAgent.target_net` | agent optimization tests |
| Save/load model | atomic `.pth` checkpoints | checkpoint round-trip tests |
| Car colours | red/blue/green settings | GUI settings |
| Easy/Medium/Hard | three generated track assets | all three load + packaged best models |
| Training start/pause/continue | `LiveTrainer` + GUI controls | live-training implementation and tests |
| Live episode/reward/lap/speed | GUI training/watch statistics | renderer/application wiring |
| Reward graph | `reward_per_episode.png` | packaged graph files |
| Lap-time graph | `lap_time_per_episode.png` | packaged graph files |
| Collision graph | `collision_count_per_episode.png` | packaged graph files |
| Training/evaluation evidence | `results/` | Easy/Medium/Hard 20-episode greedy JSON |
| Final report/presentation | `submission/` | DOCX/PPTX container integrity + visual render QA |

## Packaged model evidence

Each `models/<track>_best.pth` checkpoint was re-evaluated greedily for 20 episodes from that track's standard start position:

| Track | Success | Collisions | Mean reward | Mean lap steps |
|---|---:|---:|---:|---:|
| Easy | 20/20 | 0 | 631.0 | 295 |
| Medium | 20/20 | 0 | 576.0 | 241 |
| Hard | 20/20 | 0 | 593.0 | 259 |

Medium and Hard were obtained through curriculum continuation from the previous difficulty. These figures do not establish random-start generalization.
