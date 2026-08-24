# ─── Display ──────────────────────────────────────────────────────────────────
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
FPS = 60

# ─── Pseudo-3D road parameters ───────────────────────────────────────────────
HORIZON_Y = 350
NSTRIPS = 180
SEG_LEN = 200
ROAD_SCALE = 80000
DEPTH_SCALE = 70000

# ─── Car physics ──────────────────────────────────────────────────────────────
MAX_SPEED = 500.0
ACCEL = 220.0
BRAKE = 320.0
STEER_SPD = 2.6
OFFROAD_SLOW = 0.97
CENTRIFUGAL = 0.0014

# ─── Health system ────────────────────────────────────────────────────────────
TRAIN_HEALTH = 3  # Survives a few collisions so the AI can learn from them
RACE_HEALTH = 100  # Race mode: takes damage but doesn't die instantly
MANUAL_HEALTH = 100  # Manual play: same as race

# ─── Track ────────────────────────────────────────────────────────────────────
TRACK_SEED = 42  # Deterministic barricade placement so AI can learn
WIN_LAPS = 3  # Number of laps to win a race

# ─── Colors ───────────────────────────────────────────────────────────────────
SKY_TOP = (40, 140, 240)
SKY_BOT = (180, 225, 255)
SAND_A = (65, 150, 45)
SAND_B = (55, 140, 35)
ROAD_A = (100, 105, 110)
ROAD_B = (95, 100, 105)
RUMBLE_A = (220, 30, 30)
RUMBLE_B = (240, 240, 240)
LANE_COL = (245, 245, 245)
