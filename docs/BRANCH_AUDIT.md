# Original Repository Branch Audit

This release was designed after auditing all five branches in `rifa0118/CSE440-project-self-driving-car-game`.

## Branches inspected

| Branch | Observed role | Decision |
|---|---|---|
| `main` | Initial README-only tree | Historical baseline only |
| `Abir` | Same initial README-era baseline | Historical baseline only |
| `rifa` | Separate pseudo-3D arcade racer with manual controls, traffic, collisions, scenery, HUD, and custom assets | Useful gameplay/visual exploration, but its pseudo-3D architecture does not match the supplied course plan's image-based 2D track + five-ray state contract |
| `istiaque` | Substantive pseudo-3D AI implementation | Same substantive tree as `Miel` at the audited snapshot |
| `Miel` | Substantive Dueling-DQN implementation with replay, training/evaluation, race mode, traffic, UI, and assets | Strong implementation work, but its 18-value state and larger Dueling-DQN architecture conflict with the explicit 6-value, 6-64-64-4 DQN course plan |

## Final architecture decision

The supplied CSE440 project plan is the source of truth for the submission. It explicitly asks for:

- Python + Pygame + PyTorch;
- simple 2D image-based tracks;
- five wall-distance rays plus speed as the six-value state;
- four actions;
- the stated reward table;
- a small 6 -> 64 -> 64 -> 4 DQN;
- experience replay;
- epsilon-greedy exploration;
- model save/load;
- Easy/Medium/Hard difficulty selection;
- live metrics and the three training graphs.

Because the strongest historical branch implementations materially diverged from those contracts, the final submission does **not** activate both architectures at once or retain a second competing production implementation. It uses one plan-compliant source of truth in `game/` + `ai/` and incorporates lessons from the branch work without creating duplicate runtime authority.

Historical branch code is intentionally not bundled into the release ZIP because it would create a second, incompatible game/AI stack inside the submission and make the production entry point ambiguous. The GitHub repository remains the historical source for those branches.


## Release provenance policy

Historical branches are intentionally not copied into the runnable release tree because they contain incompatible architectures and would create duplicate production entry points. The team GitHub repository remains the authoritative history; this release records the audit and uses one project-plan-compliant runtime source of truth.
