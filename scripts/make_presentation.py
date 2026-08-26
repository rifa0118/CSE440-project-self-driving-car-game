"""
Generate CSE440 Self-Driving Car Presentation as a PPTX file.
Run from the project root: python make_pptx.py
"""

import sys
import os
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Cm
    import pptx.oxml.ns as ns
    from lxml import etree
except ImportError:
    print("ERROR: python-pptx not installed.")
    sys.exit(1)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT = Path(r"e:\Selfdrivingcar")
OUT  = ROOT / "CSE440_Presentation_v2.pptx"
GAMEPLAY_IMG    = ROOT / "docs" / "images" / "gameplay.png"
ARCH_IMG        = ROOT / "docs" / "images" / "architecture.png"
REWARD_CHART    = ROOT / "results" / "easy_20260825T154803Z" / "reward_per_episode.png"
LAPTIME_CHART   = ROOT / "results" / "easy_20260825T154803Z" / "lap_time_per_episode.png"

# ── Colour palette (white-background scheme) ──────────────────────────────
C_BG        = RGBColor(0xff, 0xff, 0xff)   # white background
C_CARD      = RGBColor(0xf1, 0xf5, 0xf9)   # light grey card
C_BLUE      = RGBColor(0x1d, 0x4e, 0xd8)   # strong blue
C_CYAN      = RGBColor(0x02, 0x84, 0xc1)   # teal/cyan
C_PURPLE    = RGBColor(0x6d, 0x28, 0xd9)   # purple
C_GREEN     = RGBColor(0x05, 0x8a, 0x4f)   # dark green
C_AMBER     = RGBColor(0xb4, 0x5a, 0x09)   # dark amber
C_RED       = RGBColor(0xb9, 0x1c, 0x1c)   # dark red
C_TEXT      = RGBColor(0x1e, 0x29, 0x3b)   # near-black text
C_MUTED     = RGBColor(0x47, 0x55, 0x69)   # slate grey
C_WHITE     = RGBColor(0xff, 0xff, 0xff)

# ── Slide size: widescreen 16:9 ────────────────────────────────────────────
W = Inches(13.333)
H = Inches(7.5)

prs = Presentation()
prs.slide_width  = W
prs.slide_height = H

blank_layout = prs.slide_layouts[6]   # completely blank

# ── Helper functions ───────────────────────────────────────────────────────

def add_slide():
    return prs.slides.add_slide(blank_layout)

def bg(slide, color=C_BG):
    """Fill slide background with solid colour."""
    bg_fill = slide.background.fill
    bg_fill.solid()
    bg_fill.fore_color.rgb = color

def rect(slide, l, t, w, h, fill=C_CARD, alpha=None, line_color=None, line_w=Pt(0.5), radius=None):
    """Add a filled rectangle (card)."""
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        l, t, w, h
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line_color:
        shape.line.color.rgb = line_color
        shape.line.width = line_w
    else:
        shape.line.fill.background()
    if radius is not None:
        # Set rounded corners via XML
        sp = shape._element
        sp_pr = sp.find(ns.qn('p:spPr'))
        prstGeom = sp_pr.find(ns.qn('a:prstGeom'))
        if prstGeom is not None:
            prstGeom.set('prst', 'roundRect')
            avLst = prstGeom.find(ns.qn('a:avLst'))
            if avLst is None:
                avLst = etree.SubElement(prstGeom, ns.qn('a:avLst'))
            gd = avLst.find(ns.qn('a:gd'))
            if gd is None:
                gd = etree.SubElement(avLst, ns.qn('a:gd'))
            gd.set('name', 'adj')
            gd.set('fmla', f'val {radius}')
    return shape

def txt(slide, text, l, t, w, h, size=18, bold=False, color=C_TEXT,
        align=PP_ALIGN.LEFT, italic=False, wrap=True):
    """Add a text box."""
    txBox = slide.shapes.add_textbox(l, t, w, h)
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = "Calibri"
    return txBox

def mtxt(slide, lines, l, t, w, h, size=16, bold=False, color=C_TEXT,
         align=PP_ALIGN.LEFT, line_spacing=None):
    """Add multiline text box. lines = list of (text, bold, color, size)."""
    txBox = slide.shapes.add_textbox(l, t, w, h)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, line_def in enumerate(lines):
        if isinstance(line_def, str):
            text, b, c, s = line_def, bold, color, size
        else:
            text = line_def.get('t', '')
            b    = line_def.get('bold', bold)
            c    = line_def.get('color', color)
            s    = line_def.get('size', size)
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        run = p.add_run()
        run.text = text
        run.font.size = Pt(s)
        run.font.bold = b
        run.font.color.rgb = c
        run.font.name = "Calibri"
        if line_spacing and i > 0:
            p.space_before = Pt(line_spacing)
    return txBox

def add_image(slide, path, l, t, w, h=None):
    """Add an image; scale to w if h is None."""
    if not Path(path).exists():
        return None
    try:
        if h:
            return slide.shapes.add_picture(str(path), l, t, w, h)
        else:
            return slide.shapes.add_picture(str(path), l, t, w)
    except Exception as e:
        print(f"  [WARN] Could not add image {path}: {e}")
        return None

def progress_bar(slide, current, total, t=Inches(7.3)):
    """Thin progress bar at bottom of slide."""
    bar_w = W * current / total
    rect(slide, 0, t, W, Inches(0.2), fill=RGBColor(0xe2,0xe8,0xf0))
    rect(slide, 0, t, bar_w, Inches(0.2), fill=C_BLUE)

def slide_header(slide, tagline, title, subtitle=None, title_color=C_BLUE):
    """Common slide header block."""
    # Top accent strip
    rect(slide, 0, 0, W, Inches(0.18), fill=C_BLUE)
    # Tagline
    txt(slide, tagline.upper(), Inches(0.6), Inches(0.28), Inches(12), Inches(0.3),
        size=10, bold=True, color=C_CYAN)
    # Title
    txt(slide, title, Inches(0.6), Inches(0.58), Inches(12), Inches(0.85),
        size=30, bold=True, color=title_color)
    # Accent bar
    rect(slide, Inches(0.6), Inches(1.45), Inches(0.7), Inches(0.06), fill=C_BLUE)
    if subtitle:
        txt(slide, subtitle, Inches(0.6), Inches(1.58), Inches(12), Inches(0.5),
            size=13, color=C_MUTED)

def chip_box(slide, text, l, t, color_fill, color_text):
    """Small badge/chip."""
    cw = Inches(1.1)
    ch = Inches(0.28)
    r = rect(slide, l, t, cw, ch, fill=color_fill, line_color=color_text, line_w=Pt(0.75))
    txt(slide, text, l + Inches(0.05), t + Inches(0.02), cw - Inches(0.1), ch,
        size=9, bold=True, color=color_text, align=PP_ALIGN.CENTER)

def divider_line(slide, t):
    """Thin horizontal rule."""
    rect(slide, Inches(0.6), t, W - Inches(1.2), Inches(0.012),
         fill=RGBColor(0xcb,0xd5,0xe1))

def card_block(slide, l, t, w, h, title, title_color, lines, line_size=13):
    """A card with title and bullet lines."""
    rect(slide, l, t, w, h, fill=C_CARD, line_color=RGBColor(0x3b,0x82,0xf6), line_w=Pt(0.5))
    # Title
    txt(slide, title, l + Inches(0.18), t + Inches(0.12), w - Inches(0.3), Inches(0.32),
        size=14, bold=True, color=title_color)
    # Lines
    line_defs = [{'t': ln, 'size': line_size, 'color': C_MUTED if not ln.startswith('  ') else C_TEXT} for ln in lines]
    mtxt(slide, line_defs, l + Inches(0.18), t + Inches(0.46), w - Inches(0.3), h - Inches(0.55),
         size=line_size, color=C_MUTED, line_spacing=3)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — TITLE
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide()
bg(sl)
progress_bar(sl, 1, 11)
# Top accent strip on title slide
rect(sl, 0, 0, W, Inches(0.18), fill=C_BLUE)

# Left gradient accent strip
rect(sl, 0, 0, Inches(0.08), H, fill=C_BLUE)

# Course badge
txt(sl, "● CSE440 — INTELLIGENT SYSTEMS ●", Inches(1.0), Inches(0.8), Inches(11), Inches(0.4),
    size=11, bold=True, color=C_CYAN, align=PP_ALIGN.CENTER)

# Main title
txt(sl, "Autonomous Self-Driving Car", Inches(0.5), Inches(1.3), Inches(12.3), Inches(1.0),
    size=48, bold=True, color=C_BLUE, align=PP_ALIGN.CENTER)
txt(sl, "with Deep Q-Learning (DQN)", Inches(0.5), Inches(2.2), Inches(12.3), Inches(0.7),
    size=32, bold=True, color=C_TEXT, align=PP_ALIGN.CENTER)

# Subtitle
txt(sl, "A Pygame-based 2D racing simulation where a Deep Q-Network agent learns\nto navigate racetracks, avoid obstacles, and complete laps from scratch.",
    Inches(1.5), Inches(3.05), Inches(10.3), Inches(0.9),
    size=15, color=C_MUTED, align=PP_ALIGN.CENTER)

divider_line(sl, Inches(3.95))

# Team cards row
team = ["Rifa", "Abir", "Istiaque", "Miel"]
for i, name in enumerate(team):
    x = Inches(2.0 + i * 2.35)
    rect(sl, x, Inches(4.1), Inches(2.1), Inches(0.42), fill=C_CARD,
         line_color=C_BLUE, line_w=Pt(0.6))
    txt(sl, name, x + Inches(0.1), Inches(4.14), Inches(1.9), Inches(0.38),
        size=13, bold=True, color=C_TEXT, align=PP_ALIGN.CENTER)

# Tech chips
chips = [("Python 3.13", C_BLUE), ("PyTorch", C_CYAN), ("Pygame 2.6", C_PURPLE),
         ("Double DQN", C_GREEN), ("NumPy", C_AMBER)]
for i, (label, col) in enumerate(chips):
    x = Inches(1.5 + i * 2.1)
    chip_box(sl, label, x, Inches(4.8), C_CARD, col)

# Bottom tagline
txt(sl, "Course Project  |  Brac University  |  2026",
    Inches(0.5), Inches(5.5), Inches(12.3), Inches(0.4),
    size=11, color=C_MUTED, align=PP_ALIGN.CENTER)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — PROBLEM STATEMENT
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide()
bg(sl)
progress_bar(sl, 2, 11)
slide_header(sl, "Problem Statement", "What Problem Are We Solving?")

# Three problem cards
problems = [
    ("🎯  Autonomous Navigation",   C_BLUE,
     "How can a vehicle learn to navigate an unknown track without any hardcoded rules or human input?"),
    ("🚧  Obstacle Avoidance",      C_CYAN,
     "How can the car detect & respond to both static track walls and dynamic moving traffic vehicles?"),
    ("🧠  Learning from Reward",    C_PURPLE,
     "Can a neural network learn an optimal driving policy using only numerical reward signals?"),
]
for i, (title, col, body) in enumerate(problems):
    x = Inches(0.4 + i * 4.32)
    rect(sl, x, Inches(1.9), Inches(4.1), Inches(2.8), fill=C_CARD,
         line_color=col, line_w=Pt(1.0))
    txt(sl, title, x + Inches(0.2), Inches(2.05), Inches(3.7), Inches(0.45),
        size=14, bold=True, color=col)
    txt(sl, body, x + Inches(0.2), Inches(2.55), Inches(3.7), Inches(1.9),
        size=13, color=C_MUTED, wrap=True)

# Approach box
rect(sl, Inches(0.6), Inches(4.95), Inches(12.1), Inches(0.95), fill=C_CARD,
     line_color=C_CYAN, line_w=Pt(0.8))
txt(sl, "Our Approach: ",
    Inches(0.8), Inches(5.05), Inches(2.0), Inches(0.4),
    size=14, bold=True, color=C_CYAN)
txt(sl, "Apply Deep Q-Network (DQN) Reinforcement Learning — the same algorithm that mastered Atari games — to train"
        " a car agent that drives itself around a racetrack with zero human-provided rules.",
    Inches(2.6), Inches(5.05), Inches(9.9), Inches(0.7),
    size=13, color=C_TEXT)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — SYSTEM ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide()
bg(sl)
progress_bar(sl, 3, 11)
slide_header(sl, "System Architecture", "How the System Works")

modules = [
    ("🎮  Game Engine",  "game/",    C_BLUE,
     ["2D Physics & Kinematics", "Track Generation (3 Levels)", "Raycasting Sensors",
      "Pygame Rendering & HUD", "Traffic Cars & Collision"]),
    ("🧠  DQN Agent",    "ai/",      C_PURPLE,
     ["MLP Q-Network (6→64→64→4)", "Experience Replay Buffer", "Double-DQN Loss",
      "ε-Greedy Exploration", "Target Network Sync"]),
    ("⚙️  Config & Utils", "",       C_GREEN,
     ["Central config.py", "Reward shaping", "Training hyperparams",
      "Metric logging & plots", "Reproducible seeding"]),
    ("🖥️  Modes",        "main.py",  C_AMBER,
     ["Pygame Interactive GUI", "Headless Training Loop", "Evaluation / Testing",
      "Live In-Game Training", "Manual Player Drive"]),
]
for i, (title, sub, col, items) in enumerate(modules):
    x = Inches(0.3 + i * 3.27)
    rect(sl, x, Inches(1.85), Inches(3.1), Inches(3.5), fill=C_CARD,
         line_color=col, line_w=Pt(0.8))
    txt(sl, title, x + Inches(0.15), Inches(1.98), Inches(2.8), Inches(0.38),
        size=13, bold=True, color=col)
    if sub:
        txt(sl, sub, x + Inches(0.15), Inches(2.35), Inches(2.8), Inches(0.3),
            size=10, color=C_MUTED, italic=True)
    for j, item in enumerate(items):
        txt(sl, f"→  {item}", x + Inches(0.15), Inches(2.65 + j * 0.42), Inches(2.8), Inches(0.42),
            size=11, color=C_MUTED)

# CLI commands
rect(sl, Inches(0.3), Inches(5.5), Inches(12.7), Inches(0.75), fill=C_CARD,
     line_color=C_BLUE, line_w=Pt(0.5))
cmds = [("main.py gui", "→ Interactive Pygame window"),
        ("main.py train", "→ Headless training"),
        ("main.py evaluate", "→ Run pretrained model"),
        ("main.py describe", "→ Print config JSON")]
for i, (cmd, desc) in enumerate(cmds):
    x = Inches(0.55 + i * 3.18)
    txt(sl, cmd,  x, Inches(5.6),  Inches(1.4), Inches(0.3), size=10, bold=True, color=C_CYAN)
    txt(sl, desc, x + Inches(1.1), Inches(5.6), Inches(1.9), Inches(0.3), size=10, color=C_MUTED)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — SENSORS & STATE SPACE
# ══════════════════════════════════════════════════════════════════════════════
# ============================================================================
# SLIDE 4 — SYSTEM ARCHITECTURE DIAGRAM
# ============================================================================
sl = add_slide()
bg(sl)
progress_bar(sl, 4, 11)
slide_header(sl, "System Architecture", "Agent-Environment Training Loop")

# Architecture image (full width, centered)
add_image(sl, ARCH_IMG, Inches(0.9), Inches(1.75), Inches(11.5))

# Description boxes below image
arch_items = [
    ("Read State",    "5 ray distances + speed",      C_BLUE),
    ("DQN Agent",     "Q-Network 6 -> 64 -> 64 -> 4", C_PURPLE),
    ("Choose Action", "left / right / straight / brake", C_CYAN),
    ("Car Physics",   "position, speed, angle",       C_GREEN),
    ("Reward + Replay","store transition & update net", C_AMBER),
]
for i, (title, desc, col) in enumerate(arch_items):
    x = Inches(0.25 + i * 2.62)
    rect(sl, x, Inches(6.0), Inches(2.45), Inches(1.1), fill=C_CARD,
         line_color=col, line_w=Pt(0.8))
    txt(sl, title, x + Inches(0.12), Inches(6.1), Inches(2.2), Inches(0.35),
        size=12, bold=True, color=col)
    txt(sl, desc,  x + Inches(0.12), Inches(6.48), Inches(2.2), Inches(0.5),
        size=10, color=C_MUTED)

txt(sl, "Repeat for thousands of steps until the driving policy converges",
    Inches(2.0), Inches(7.12), Inches(9.0), Inches(0.25),
    size=11, color=C_MUTED, italic=True, align=PP_ALIGN.CENTER)

# ============================================================================
# SLIDE 5 — SENSORS & STATE SPACE
# ============================================================================
sl = add_slide()
bg(sl)
progress_bar(sl, 5, 11)
slide_header(sl, "Perception System", "Sensors & State Representation")

# Left card — sensors
rect(sl, Inches(0.35), Inches(1.85), Inches(6.1), Inches(4.2), fill=C_CARD,
     line_color=C_BLUE, line_w=Pt(0.8))
txt(sl, "🔦  Raycasting Lidar — 5 Sensors", Inches(0.55), Inches(1.98), Inches(5.7), Inches(0.4),
    size=14, bold=True, color=C_CYAN)
txt(sl, "Five rays cast from the car's front bumper at fixed angles.\nEach returns a normalized distance to the nearest wall or traffic car.",
    Inches(0.55), Inches(2.4), Inches(5.7), Inches(0.7), size=12, color=C_MUTED)
sensors = [("−90°", "Left side sensor"),
           ("−45°", "Front-left diagonal"),
           ("  0°", "Forward sensor (main)"),
           ("+45°", "Front-right diagonal"),
           ("+90°", "Right side sensor"),
           ("speed", "Normalized car speed v / v_max")]
for i, (angle, desc) in enumerate(sensors):
    col = C_CYAN if angle.strip() == "0°" else (C_GREEN if "speed" in angle else C_BLUE)
    rect(sl, Inches(0.55), Inches(3.18 + i * 0.38), Inches(0.7), Inches(0.3), fill=col, line_color=col)
    txt(sl, angle, Inches(0.58), Inches(3.19 + i * 0.38), Inches(0.65), Inches(0.3),
        size=10, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    txt(sl, desc, Inches(1.35), Inches(3.19 + i * 0.38), Inches(4.7), Inches(0.3),
        size=12, color=C_MUTED)

# Right card — state vector
rect(sl, Inches(6.65), Inches(1.85), Inches(6.3), Inches(4.2), fill=C_CARD,
     line_color=C_PURPLE, line_w=Pt(0.8))
txt(sl, "📐  State Vector: 6 Dimensions", Inches(6.85), Inches(1.98), Inches(5.9), Inches(0.4),
    size=14, bold=True, color=C_PURPLE)
code_lines = [
    "state = [",
    "    d_-90°,   # left wall distance ∈ [0, 1]",
    "    d_-45°,   # front-left dist ∈ [0, 1]",
    "    d_0°,     # forward dist ∈ [0, 1]",
    "    d_+45°,   # front-right dist ∈ [0, 1]",
    "    d_+90°,   # right wall dist ∈ [0, 1]",
    "    v/v_max   # normalized speed ∈ [0, 1]",
    "]",
]
rect(sl, Inches(6.85), Inches(2.42), Inches(5.9), Inches(2.85), fill=RGBColor(0x06,0x0f,0x1e),
     line_color=RGBColor(0x1e,0x3a,0x5f), line_w=Pt(0.5))
for i, line in enumerate(code_lines):
    col = C_CYAN if line.startswith("state") or line == "]" else C_TEXT
    txt(sl, line, Inches(7.0), Inches(2.5 + i * 0.33), Inches(5.5), Inches(0.33),
        size=11, color=col)

txt(sl, "⚡ Sensors also detect moving traffic cars (proximity < 23px triggers hit)",
    Inches(6.85), Inches(5.35), Inches(5.9), Inches(0.5), size=12, color=C_GREEN)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — DQN ALGORITHM
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide()
bg(sl)
progress_bar(sl, 6, 11)
slide_header(sl, "RL Algorithm", "Deep Q-Network (Double DQN)")

# Neural network diagram (simple boxes)
layers = [("Input\n6", C_BLUE), ("Hidden\n64 (ReLU)", C_PURPLE),
          ("Hidden\n64 (ReLU)", C_PURPLE), ("Output\n4 Actions", C_GREEN)]
layer_x = [Inches(0.5), Inches(2.3), Inches(3.9), Inches(5.5)]
for i, ((label, col), lx) in enumerate(zip(layers, layer_x)):
    rect(sl, lx, Inches(1.9), Inches(1.5), Inches(1.4), fill=C_CARD,
         line_color=col, line_w=Pt(1.2))
    txt(sl, label, lx + Inches(0.05), Inches(2.1), Inches(1.4), Inches(1.0),
        size=13, bold=True, color=col, align=PP_ALIGN.CENTER)
    if i < 3:
        txt(sl, "→", lx + Inches(1.5), Inches(2.35), Inches(0.4), Inches(0.5),
            size=22, bold=True, color=C_MUTED, align=PP_ALIGN.CENTER)

# Double-DQN formula card
rect(sl, Inches(0.4), Inches(3.55), Inches(6.8), Inches(1.85), fill=C_CARD,
     line_color=C_CYAN, line_w=Pt(0.8))
txt(sl, "⚡  Double-DQN Update Rule", Inches(0.6), Inches(3.65), Inches(6.4), Inches(0.38),
    size=14, bold=True, color=C_CYAN)
formulas = [
    ("a* = argmax_a  Q_policy(s', a)",        C_AMBER),
    ("y  = r + γ · Q_target(s', a*)",         C_TEXT),
    ("𝓛  = ( Q_policy(s, a) − y )²",          C_TEXT),
]
for i, (formula, col) in enumerate(formulas):
    rect(sl, Inches(0.6), Inches(4.1 + i * 0.38), Inches(6.4), Inches(0.35),
         fill=RGBColor(0x06,0x0f,0x1e), line_color=C_CARD)
    txt(sl, formula, Inches(0.72), Inches(4.12 + i * 0.38), Inches(6.2), Inches(0.34),
        size=12, color=col)

# Hyperparameters card
rect(sl, Inches(7.35), Inches(1.85), Inches(5.6), Inches(3.55), fill=C_CARD,
     line_color=C_GREEN, line_w=Pt(0.8))
txt(sl, "💾  Hyperparameters", Inches(7.55), Inches(1.98), Inches(5.2), Inches(0.38),
    size=14, bold=True, color=C_GREEN)
hparams = [
    ("Learning Rate", "1 × 10⁻³"),
    ("Discount γ",    "0.99"),
    ("Batch Size",    "64"),
    ("Replay Buffer", "50,000"),
    ("Target Sync",   "Every 600 steps"),
    ("Gradient Clip", "10.0"),
    ("ε Start → End", "1.0 → 0.05"),
    ("ε Decay Steps", "45,000"),
    ("Hidden Size",   "64 neurons"),
    ("Optimizer",     "Adam"),
]
for i, (k, v) in enumerate(hparams):
    row_t = Inches(2.42 + i * 0.3)
    txt(sl, k, Inches(7.55), row_t, Inches(2.6), Inches(0.3), size=11, color=C_MUTED)
    txt(sl, v, Inches(10.35), row_t, Inches(2.4), Inches(0.3), size=11, bold=True, color=C_CYAN)

# ε-greedy decay
rect(sl, Inches(7.35), Inches(5.55), Inches(5.6), Inches(0.85), fill=C_CARD,
     line_color=C_AMBER, line_w=Pt(0.6))
txt(sl, "🎲  ε-Greedy:  1.0 (ep 0)  →  0.50 (ep ~150)  →  0.05 (ep ~350+)",
    Inches(7.5), Inches(5.68), Inches(5.3), Inches(0.55), size=12, color=C_AMBER)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — ACTIONS & REWARD FUNCTION
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide()
bg(sl)
progress_bar(sl, 7, 11)
slide_header(sl, "Agent Design", "Actions & Reward Function")

# Action boxes
actions = [
    ("A[0]", "⬅  Turn Left",    "Full Throttle + Steer Left",  C_BLUE),
    ("A[1]", "➡  Turn Right",   "Full Throttle + Steer Right", C_CYAN),
    ("A[2]", "⬆  Straight",     "Full Throttle, no steer",     C_GREEN),
    ("A[3]", "🛑  Brake",        "Zero Throttle, Full Brake",   C_RED),
]
txt(sl, "🕹️  Action Space — 4 Discrete Actions", Inches(0.4), Inches(1.9), Inches(6.1), Inches(0.38),
    size=14, bold=True, color=C_BLUE)
for i, (idx, name, desc, col) in enumerate(actions):
    x = Inches(0.4 + (i % 2) * 3.05)
    y = Inches(2.35 + (i // 2) * 0.9)
    rect(sl, x, y, Inches(2.85), Inches(0.78), fill=C_CARD, line_color=col, line_w=Pt(0.8))
    txt(sl, idx,  x + Inches(0.1), y + Inches(0.05), Inches(0.5), Inches(0.32),
        size=10, bold=True, color=col)
    txt(sl, name, x + Inches(0.1), y + Inches(0.36), Inches(2.6), Inches(0.34),
        size=13, bold=True, color=C_TEXT)

# Physics mini-card
rect(sl, Inches(0.4), Inches(4.35), Inches(6.0), Inches(1.5), fill=C_CARD,
     line_color=C_AMBER, line_w=Pt(0.6))
txt(sl, "🚗  Vehicle Physics", Inches(0.6), Inches(4.45), Inches(5.6), Inches(0.35),
    size=13, bold=True, color=C_AMBER)
phy = [("Max Speed", "7.0 px/frame"), ("Acceleration", "0.20 px/f²"),
       ("Brake Power", "0.34"), ("Friction", "0.035/frame"),
       ("Steer Rate", "4.2°/frame"), ("Max Steps", "1,800")]
for i, (k, v) in enumerate(phy):
    x = Inches(0.6 + (i % 2) * 2.9)
    y = Inches(4.82 + (i // 2) * 0.3)
    txt(sl, f"{k}: ", x, y, Inches(1.3), Inches(0.28), size=11, color=C_MUTED)
    txt(sl, v, x + Inches(1.2), y, Inches(1.5), Inches(0.28), size=11, bold=True, color=C_AMBER)

# Reward table
rect(sl, Inches(6.6), Inches(1.85), Inches(6.4), Inches(4.0), fill=C_CARD,
     line_color=C_GREEN, line_w=Pt(0.8))
txt(sl, "🏆  Reward Function", Inches(6.8), Inches(1.98), Inches(6.0), Inches(0.38),
    size=14, bold=True, color=C_GREEN)
rewards = [
    ("🟢  Forward driving (per speed ratio)",   "+1.0 / step",  C_GREEN),
    ("🏁  Checkpoint progress",                  "+20.0",        C_GREEN),
    ("🎉  Full lap completed",                   "+100.0",       C_GREEN),
    ("💥  Wall / traffic collision",             "−100.0",       C_RED),
    ("⬅️  Driving backwards",                    "−10.0",        C_RED),
    ("😴  Standing still / stuck",               "−2.0 / step",  C_RED),
    ("🔄  Rapid L↔R oscillation chatter",        "−0.25",        C_RED),
]
rect(sl, Inches(6.8), Inches(2.42), Inches(6.0), Inches(0.28),
     fill=RGBColor(0x0a, 0x14, 0x24), line_color=C_CARD)
txt(sl, "  Event",   Inches(6.85), Inches(2.44), Inches(4.5), Inches(0.25), size=10, bold=True, color=C_MUTED)
txt(sl, "Reward",    Inches(11.45), Inches(2.44), Inches(1.2), Inches(0.25), size=10, bold=True, color=C_MUTED)
for i, (event, reward, col) in enumerate(rewards):
    y = Inches(2.75 + i * 0.38)
    if i % 2 == 0:
        rect(sl, Inches(6.8), y, Inches(6.0), Inches(0.36),
             fill=RGBColor(0x0d, 0x1b, 0x2e), line_color=C_CARD)
    txt(sl, event,  Inches(6.85), y + Inches(0.03), Inches(4.5), Inches(0.34), size=12, color=C_TEXT)
    txt(sl, reward, Inches(11.35), y + Inches(0.03), Inches(1.35), Inches(0.34),
        size=12, bold=True, color=col, align=PP_ALIGN.RIGHT)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — TRACK DESIGN
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide()
bg(sl)
progress_bar(sl, 8, 11)
slide_header(sl, "Track Design", "3 Procedurally Generated Racetracks")

tracks = [
    ("🟢  Easy Track",   C_GREEN,  "Oval Ellipse",
     "Simple oval — wide road (116 px),\nconstant-radius turns.\nPerfect for initial learning.",
     "Centerline: 500 × 320 px"),
    ("🟡  Medium Track", C_AMBER,  "Wavy Ellipse",
     "Deformed ellipse with harmonic\nradial variations — sinusoidal\ncurves challenge smooth steering.",
     "Road width: 98 px | Radial mod: 10%"),
    ("🔴  Hard Track",   C_RED,    "Complex Curve",
     "Biaxial radial distortions — narrow\nroad (84 px), twisty circuit.\nDemands precise timing.",
     "Road width: 84 px | Dual-axis mod"),
]
for i, (title, col, badge, desc, spec) in enumerate(tracks):
    x = Inches(0.35 + i * 4.33)
    rect(sl, x, Inches(1.85), Inches(4.1), Inches(3.3), fill=C_CARD,
         line_color=col, line_w=Pt(1.0))
    txt(sl, title, x + Inches(0.2), Inches(1.98), Inches(3.7), Inches(0.4),
        size=15, bold=True, color=col)
    chip_box(sl, badge, x + Inches(0.2), Inches(2.42), C_CARD, col)
    txt(sl, desc, x + Inches(0.2), Inches(2.82), Inches(3.7), Inches(1.4),
        size=13, color=C_TEXT, wrap=True)
    txt(sl, spec, x + Inches(0.2), Inches(4.28), Inches(3.7), Inches(0.3),
        size=10, color=C_MUTED, italic=True)

# Pipeline card
rect(sl, Inches(0.35), Inches(5.3), Inches(12.9), Inches(0.9), fill=C_CARD,
     line_color=C_CYAN, line_w=Pt(0.6))
txt(sl, "🗺️  Track Asset Generation Pipeline:", Inches(0.55), Inches(5.42), Inches(3.4), Inches(0.35),
    size=13, bold=True, color=C_CYAN)
pipeline = ["Spline Centerline", "Boundaries", "Grass (PIL)", "Asphalt + Curbs",
            "Checkerboard Start", "Dashed Line", "PNG + Mask + JSON ✓"]
col_arr = [C_MUTED]*6 + [C_GREEN]
for i, (step, col) in enumerate(zip(pipeline, col_arr)):
    x = Inches(3.8 + i * 1.38)
    txt(sl, ("→  " if i > 0 else "") + step, x, Inches(5.5), Inches(1.55), Inches(0.35),
        size=11, bold=(col == C_GREEN), color=col)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — GAMEPLAY SCREENSHOT
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide()
bg(sl)
progress_bar(sl, 9, 11)
slide_header(sl, "Live Demo", "The Game in Action")

# Gameplay image
add_image(sl, GAMEPLAY_IMG, Inches(0.35), Inches(1.85), Inches(7.6))

# Mode cards on right
modes = [
    ("🕹️  Manual Drive",      "Arrow key control of the car"),
    ("🤖  Watch Trained AI",  "Greedy ε = 0 policy, no exploration"),
    ("📈  Train AI (Live)",   "Observe the car learn in real-time"),
    ("📊  Evaluate AI",       "Benchmark statistics & metrics"),
    ("⚙️  Settings",          "Change track layout & car colour"),
]
txt(sl, "🎮  Interactive Modes", Inches(8.15), Inches(1.88), Inches(5.0), Inches(0.38),
    size=13, bold=True, color=C_BLUE)
for i, (mode, desc) in enumerate(modes):
    y = Inches(2.3 + i * 0.72)
    rect(sl, Inches(8.15), y, Inches(4.95), Inches(0.62), fill=C_CARD,
         line_color=C_BLUE, line_w=Pt(0.5))
    txt(sl, mode, Inches(8.3), y + Inches(0.04), Inches(4.6), Inches(0.28),
        size=12, bold=True, color=C_TEXT)
    txt(sl, desc, Inches(8.3), y + Inches(0.32), Inches(4.6), Inches(0.26),
        size=11, color=C_MUTED)

# Traffic info
rect(sl, Inches(8.15), Inches(6.05), Inches(4.95), Inches(0.65), fill=C_CARD,
     line_color=C_GREEN, line_w=Pt(0.6))
txt(sl, "🚦  Traffic: 3 cars at 2.0 px/frame — sensors detect them within 23 px",
    Inches(8.3), Inches(6.15), Inches(4.7), Inches(0.45), size=11, color=C_GREEN)

# Caption
txt(sl, "Pretrained DQN agent — Easy track, sensors visible (blue rays), reward = 204",
    Inches(0.35), Inches(6.95), Inches(7.6), Inches(0.3), size=10, color=C_MUTED,
    align=PP_ALIGN.CENTER, italic=True)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — TRAINING RESULTS
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide()
bg(sl)
progress_bar(sl, 10, 11)
slide_header(sl, "Experimental Results", "Training Performance & Results")

# Reward chart
add_image(sl, REWARD_CHART, Inches(0.35), Inches(1.85), Inches(6.15))
txt(sl, "Reward per Episode — agent clearly improves from episode ~200 onwards",
    Inches(0.35), Inches(5.85), Inches(6.15), Inches(0.35), size=10, color=C_MUTED,
    align=PP_ALIGN.CENTER, italic=True)

# Lap time chart
add_image(sl, LAPTIME_CHART, Inches(6.75), Inches(1.85), Inches(6.2))
txt(sl, "Lap Time — converging from ~6.2 s toward ~5.2 s optimal",
    Inches(6.75), Inches(5.85), Inches(6.2), Inches(0.35), size=10, color=C_MUTED,
    align=PP_ALIGN.CENTER, italic=True)

# Stat row
stats = [("500+", "Training Episodes", C_BLUE),
         ("~5.2 s", "Best Lap Time", C_GREEN),
         ("700+", "Peak Episode Reward", C_PURPLE),
         ("3", "Difficulty Levels", C_AMBER)]
for i, (num, label, col) in enumerate(stats):
    x = Inches(0.5 + i * 3.22)
    rect(sl, x, Inches(6.3), Inches(2.95), Inches(0.85), fill=C_CARD,
         line_color=col, line_w=Pt(0.8))
    txt(sl, num,   x + Inches(0.1), Inches(6.36), Inches(1.3), Inches(0.42),
        size=28, bold=True, color=col, align=PP_ALIGN.CENTER)
    txt(sl, label, x + Inches(1.4), Inches(6.45), Inches(1.45), Inches(0.4),
        size=11, color=C_MUTED)

# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — CONCLUSION
# ══════════════════════════════════════════════════════════════════════════════
sl = add_slide()
bg(sl)
progress_bar(sl, 11, 11)
slide_header(sl, "Summary", "Conclusions & Future Work")

# Achievements
rect(sl, Inches(0.35), Inches(1.85), Inches(6.0), Inches(3.8), fill=C_CARD,
     line_color=C_GREEN, line_w=Pt(0.8))
txt(sl, "✅  What We Achieved", Inches(0.55), Inches(1.98), Inches(5.6), Inches(0.38),
    size=14, bold=True, color=C_GREEN)
achievements = [
    "DQN agent successfully learns autonomous lap completion",
    "Real-time traffic avoidance with dynamic sensor detection",
    "3 track difficulty levels with procedural generation",
    "Full Pygame interactive GUI with 4 operating modes",
    "Modular testable Python codebase (12 test modules)",
    "Pre-trained models for Easy, Medium & Hard tracks",
    "Comprehensive documentation & academic report",
]
for i, ach in enumerate(achievements):
    txt(sl, f"✓  {ach}", Inches(0.55), Inches(2.45 + i * 0.42), Inches(5.6), Inches(0.4),
        size=12, color=C_TEXT)

# Future work
rect(sl, Inches(0.35), Inches(5.85), Inches(6.0), Inches(1.35), fill=C_CARD,
     line_color=C_AMBER, line_w=Pt(0.8))
txt(sl, "🔮  Future Improvements", Inches(0.55), Inches(5.98), Inches(5.6), Inches(0.38),
    size=14, bold=True, color=C_AMBER)
future = ["Prioritized Experience Replay (PER)  •  Dueling DQN",
          "PPO / A2C continuous action space",
          "Multi-agent competitive racing  •  Visual pixel input"]
for i, fut in enumerate(future):
    txt(sl, f"→  {fut}", Inches(0.55), Inches(6.44 + i * 0.3), Inches(5.6), Inches(0.28),
        size=11, color=C_MUTED)

# Architecture image
add_image(sl, ARCH_IMG, Inches(6.55), Inches(1.85), Inches(6.4))

# Repo card
rect(sl, Inches(6.55), Inches(5.7), Inches(6.4), Inches(1.5), fill=C_CARD,
     line_color=C_BLUE, line_w=Pt(0.6))
txt(sl, "Repository", Inches(6.75), Inches(5.82), Inches(6.0), Inches(0.35),
    size=13, bold=True, color=C_TEXT)
txt(sl, "github.com/rifa0118/CSE440-project-self-driving-car-game",
    Inches(6.75), Inches(6.18), Inches(6.0), Inches(0.35),
    size=12, color=C_CYAN)
chips_row = [("PyTorch 2.2", C_BLUE), ("Pygame 2.6", C_CYAN),
             ("Python 3.13", C_PURPLE), ("Double DQN", C_GREEN)]
for i, (label, col) in enumerate(chips_row):
    chip_box(sl, label, Inches(6.75 + i * 1.55), Inches(6.65), C_CARD, col)

# Thank you
txt(sl, "Thank You! -- Questions welcome.",
    Inches(0.35), Inches(7.1), Inches(12.6), Inches(0.25),
    size=13, bold=True, color=C_MUTED, align=PP_ALIGN.CENTER)

# ============================================================================
# SAVE
# ============================================================================
prs.save(str(OUT))
print("DONE: " + str(OUT))
