"""Build the submission-ready DOCX report and PPTX presentation.

The Markdown files remain the editable source of truth. This script creates
polished office documents with placeholders only for team-specific identity
information that was not supplied.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from pptx import Presentation
from pptx.dml.color import RGBColor as PptRGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches as PptInches, Pt as PptPt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SUBMISSION_DIR = PROJECT_ROOT / "submission"
IMAGES_DIR = PROJECT_ROOT / "docs" / "images"
RESULTS_DIR = PROJECT_ROOT / "results" / "pretrained_easy_300_episodes"
EVALUATION_PATH = PROJECT_ROOT / "results" / "easy_pretrained_evaluation_20.json"

NAVY = "203A5F"
BLUE = "3F88C5"
LIGHT_BLUE = "DCEAF7"
PALE = "F4F7FA"
DARK = "1B2738"
MUTED = "5F6F82"
WHITE = "FFFFFF"


def _set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def _set_cell_margins(cell, top=90, start=90, bottom=90, end=90) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def _set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def _set_row_cant_split(row) -> None:
    """Keep a table row together so images and small result tables do not tear."""

    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    cant_split.set(qn("w:val"), "true")
    tr_pr.append(cant_split)


def _set_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("Page ")
    run.font.name = "Liberation Sans"
    run.font.size = Pt(9)
    fld_char_1 = OxmlElement("w:fldChar")
    fld_char_1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char_2 = OxmlElement("w:fldChar")
    fld_char_2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char_1)
    run._r.append(instr_text)
    run._r.append(fld_char_2)


def _configure_doc_styles(doc: Document) -> None:
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Liberation Sans"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor.from_string(DARK)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.12

    for style_name, size, color in (
        ("Title", 26, NAVY),
        ("Subtitle", 13, MUTED),
        ("Heading 1", 17, NAVY),
        ("Heading 2", 13, BLUE),
        ("Heading 3", 11, DARK),
    ):
        style = styles[style_name]
        style.font.name = "Liberation Sans"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.font.bold = style_name != "Subtitle"
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_before = Pt(8)
        style.paragraph_format.space_after = Pt(4)

    styles["Caption"].font.name = "Liberation Sans"
    styles["Caption"].font.size = Pt(9)
    styles["Caption"].font.color.rgb = RGBColor.from_string(MUTED)
    styles["Caption"].font.italic = True


def _add_header_footer(doc: Document) -> None:
    for section in doc.sections:
        section.top_margin = Cm(1.7)
        section.bottom_margin = Cm(1.6)
        section.left_margin = Cm(1.8)
        section.right_margin = Cm(1.8)
        header = section.header
        p = header.paragraphs[0]
        p.text = "CSE440 - Self-Driving Car Racing Game"
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        for run in p.runs:
            run.font.name = "Liberation Sans"
            run.font.size = Pt(8.5)
            run.font.color.rgb = RGBColor.from_string(MUTED)
        _set_page_number(section.footer.paragraphs[0])


def _add_paragraph(doc: Document, text: str, *, bold_lead: str | None = None) -> None:
    p = doc.add_paragraph()
    if bold_lead and text.startswith(bold_lead):
        p.add_run(bold_lead).bold = True
        p.add_run(text[len(bold_lead) :])
    else:
        p.add_run(text)


def _add_bullets(doc: Document, items: list[str], level: int = 0) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
        p.add_run(item)


def _add_numbered(doc: Document, items: list[str]) -> None:
    # Manual numbering is deliberate: Word/LibreOffice otherwise continues the
    # numbering ID from earlier lists, which made later sections begin at 8.
    for index, item in enumerate(items, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.55)
        p.paragraph_format.first_line_indent = Cm(-0.55)
        p.add_run(f"{index}.\t{item}")


def _add_table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float] | None = None) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    header_row = table.rows[0]
    _set_repeat_table_header(header_row)
    _set_row_cant_split(header_row)
    for idx, header in enumerate(headers):
        cell = header_row.cells[idx]
        _set_cell_shading(cell, NAVY)
        _set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(header)
        run.bold = True
        run.font.name = "Liberation Sans"
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor.from_string(WHITE)
    for row_index, row_values in enumerate(rows):
        row = table.add_row()
        _set_row_cant_split(row)
        cells = row.cells
        for idx, value in enumerate(row_values):
            cell = cells[idx]
            if row_index % 2 == 1:
                _set_cell_shading(cell, PALE)
            _set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if idx > 0 else WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(str(value))
            run.font.name = "Liberation Sans"
            run.font.size = Pt(9)
        if widths:
            for idx, width in enumerate(widths):
                cells[idx].width = Inches(width)
    doc.add_paragraph()


def _add_image(doc: Document, path: Path, width_inches: float, caption: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(width_inches))
    cap = doc.add_paragraph(caption, style="Caption")
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER


def build_report() -> Path:
    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)
    doc = Document()
    core = doc.core_properties
    core.title = "CSE440 Self-Driving Car Racing Game - Project Report"
    core.subject = "Deep Q-Network reinforcement learning project"
    core.author = "CSE440 Project Team"
    core.last_modified_by = "CSE440 Project Team"
    core.keywords = "CSE440, artificial intelligence, reinforcement learning, DQN, Pygame, PyTorch"
    core.comments = "Generated from the completed project source and measured evaluation results."
    _configure_doc_styles(doc)
    _add_header_footer(doc)

    # Cover page
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(40)
    run = p.add_run("CSE440")
    run.bold = True
    run.font.name = "Liberation Sans"
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor.from_string(BLUE)

    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(18)
    title.add_run("Self-Driving Car Racing Game\nUsing Deep Q-Network Reinforcement Learning")

    subtitle = doc.add_paragraph(style="Subtitle")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run("Project Report")

    _add_image(doc, IMAGES_DIR / "architecture.png", 6.8, "Agent-environment training loop used by the project")

    identity = doc.add_table(rows=5, cols=2)
    identity.alignment = WD_TABLE_ALIGNMENT.CENTER
    identity.style = "Table Grid"
    labels = ["Course", "Students", "Section", "Faculty", "Submission date"]
    values = [
        "CSE440 - Introduction to Artificial Intelligence",
        "Add names and IDs",
        "Add section",
        "Add faculty name",
        "Add date",
    ]
    for i, (label, value) in enumerate(zip(labels, values, strict=True)):
        _set_cell_shading(identity.cell(i, 0), LIGHT_BLUE)
        for cell in identity.rows[i].cells:
            _set_cell_margins(cell, 110, 110, 110, 110)
        identity.cell(i, 0).paragraphs[0].add_run(label).bold = True
        identity.cell(i, 1).paragraphs[0].add_run(value)
    doc.add_page_break()

    doc.add_heading("Abstract", level=1)
    _add_paragraph(
        doc,
        "This project implements a two-dimensional racing game in which an artificial-intelligence agent learns to drive through interaction with a simulated environment. Pygame provides the interactive interface, Pillow and NumPy provide image-based tracks and collision masks, PyTorch implements a Deep Q-Network (DQN), and Matplotlib produces evaluation graphs. The agent observes five wall-distance sensor values and speed, then chooses turn left, turn right, go straight, or brake. It learns from rewards for forward progress, checkpoints, lap completion, collisions, backward movement, and standing still.",
    )
    _add_paragraph(
        doc,
        "The completed system includes manual driving, three track difficulties, live and headless training, experience replay, epsilon-greedy exploration, a target network, checkpoint saving/loading, deterministic evaluation, and automated tests. In the included 300-episode Easy run, 110 exploratory episodes completed a lap and the final-50 mean reward was 614.7. The selected model then completed 20 of 20 greedy evaluation episodes from the standard start position with no collision and a mean lap length of 295 simulation steps. The result demonstrates that a compact CPU-based DQN can learn a reproducible driving policy in this educational environment.",
    )

    doc.add_heading("1. Introduction", level=1)
    _add_paragraph(
        doc,
        "Reinforcement learning allows an agent to improve behavior from interaction and reward rather than from a correct action label for every situation. A racing game is an effective educational environment because the agent repeatedly senses the road, chooses an action, observes movement, receives a reward, and updates a policy.",
    )
    _add_paragraph(
        doc,
        "The project is intentionally not a complete driving simulator. Its purpose is to make agent-environment interaction, state/action design, reward engineering, exploration, value approximation, training, saving, and evaluation visible and explainable on a normal laptop.",
    )

    doc.add_heading("2. Objectives and Scope", level=1)
    _add_numbered(
        doc,
        [
            "Build a playable 2D racing game with simple vehicle physics.",
            "Use image masks for road collision and five ray-distance sensors.",
            "Represent the state as five sensor values plus speed.",
            "Implement four discrete actions and the specified reward table.",
            "Train a 6-64-64-4 DQN with replay memory and epsilon-greedy exploration.",
            "Save/load models, display live metrics, and generate evaluation graphs.",
            "Keep training CPU-friendly and verify behavior with automated tests.",
        ],
    )
    _add_paragraph(doc, "Included scope: one car, manual and AI modes, Easy/Medium/Hard tracks, three car colors, live/headless training, saved models, raw metrics, and tests.")
    _add_paragraph(doc, "Excluded scope: realistic tire/suspension physics, real-road perception, multiple competing cars, and safety-critical vehicle control.")

    # Keep the complete technology table together on a fresh page rather than
    # leaving a four-row continuation on an otherwise empty page.
    doc.add_page_break()
    doc.add_heading("3. Technology Selection", level=1)
    _add_table(
        doc,
        ["Part", "Technology", "Purpose"],
        [
            ["Language", "Python", "Main implementation"],
            ["Game interface", "Pygame", "Window, controls, drawing, live view"],
            ["Neural network", "PyTorch", "DQN, optimizer, checkpoint"],
            ["Numeric processing", "NumPy", "State arrays, geometry, sensors"],
            ["Track images", "Pillow", "Display PNG and collision mask"],
            ["Graphs", "Matplotlib", "Reward, lap time, collisions"],
            ["Testing", "Pytest", "Automated verification"],
        ],
    )

    doc.add_heading("4. System Architecture", level=1)
    _add_image(doc, IMAGES_DIR / "architecture.png", 7.0, "Figure 1. DQN agent-environment training loop")
    _add_numbered(
        doc,
        [
            "Reset the environment and spawn the car at the start line.",
            "Read five sensor distances and current speed.",
            "Choose a random or highest-Q action.",
            "Update speed, heading, and position.",
            "Check road pixels, progress, checkpoints, and lap completion.",
            "Calculate reward and store the transition in replay memory.",
            "Sample a random batch and update the policy network.",
            "Periodically synchronize the target network and repeat.",
        ],
    )

    doc.add_heading("5. Game Environment", level=1)
    doc.add_heading("5.1 Vehicle physics", level=2)
    _add_paragraph(doc, "The car stores position (x, y), heading angle, speed, and total distance. The screen uses positive x to the right and positive y downward.")
    eqs = [
        "x(t+1) = x(t) + cos(theta(t)) * v(t)",
        "y(t+1) = y(t) + sin(theta(t)) * v(t)",
        "theta(t+1) = theta(t) + steering * steering_rate",
        "v(t+1) = clip(v(t) + acceleration - braking - friction, 0, v_max)",
    ]
    for eq in eqs:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(eq)
        run.font.name = "Liberation Mono"
        run.font.size = Pt(10)
        run.bold = True

    # The three-track visual is a single semantic figure. Its table row is
    # marked as non-splittable, so it can safely flow after the physics text.
    doc.add_heading("5.2 Image-based tracks and collision", level=2)
    _add_paragraph(doc, "Each difficulty has a colored display PNG, a grayscale white-road/black-wall mask, and JSON metadata containing a 720-point centerline, twelve checkpoints, start pose, and road width. Nine probes around the rotated car body must remain on white road pixels.")
    track_table = doc.add_table(rows=1, cols=3)
    track_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    track_table.style = "Table Grid"
    _set_row_cant_split(track_table.rows[0])
    for i, name in enumerate(("Easy", "Medium", "Hard")):
        cell = track_table.rows[0].cells[i]
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(name)
        r.bold = True
        r.font.color.rgb = RGBColor.from_string(NAVY)
        p.add_run("\n").add_picture(
            str(PROJECT_ROOT / "assets" / "tracks" / f"{name.lower()}.png"),
            width=Inches(2.2),
        )
    doc.add_paragraph("Figure 2. Procedurally generated display tracks", style="Caption").alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_heading("5.3 Progress and checkpoints", level=2)
    _add_paragraph(doc, "The environment performs a local nearest-centerline search around the previous index. This prevents a collision near another section from producing an impossible progress jump. Ordered absolute checkpoint targets prevent repeated reward from oscillating across one line.")

    doc.add_page_break()
    doc.add_heading("6. State, Actions, and Rewards", level=1)
    doc.add_heading("6.1 State", level=2)
    _add_paragraph(doc, "Five rays are cast at -90, -45, 0, +45, and +90 degrees relative to the car. Each distance and the speed are normalized to [0, 1].")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("state = [left, front_left, front, front_right, right, speed]")
    run.font.name = "Liberation Mono"
    run.font.size = Pt(11)
    run.bold = True
    _add_image(doc, IMAGES_DIR / "gameplay.png", 7.1, "Figure 3. Trained car using five live distance sensors")

    doc.add_heading("6.2 Actions", level=2)
    _add_table(
        doc,
        ["Index", "Action", "Throttle", "Steering", "Brake"],
        [
            ["0", "Turn left", "1", "-1", "0"],
            ["1", "Turn right", "1", "+1", "0"],
            ["2", "Go straight", "1", "0", "0"],
            ["3", "Brake", "0", "0", "1"],
        ],
    )

    # Keep the reward table intact instead of splitting two rows onto one page
    # and the remaining rows onto the next.
    doc.add_page_break()
    doc.add_heading("6.3 Reward function", level=2)
    _add_table(
        doc,
        ["Situation", "Reward"],
        [
            ["Driving forward", "+1"],
            ["Passing a checkpoint", "+20"],
            ["Completing a lap", "+100"],
            ["Collision", "-100"],
            ["Driving backwards", "-10"],
            ["Standing still", "-2"],
        ],
    )
    _add_paragraph(doc, "Reward engineering provides both local guidance and long-term goals. Forward progress encourages movement, checkpoints reduce reward delay, lap completion represents success, and penalties discourage collision, reverse progress, and inactivity.")

    doc.add_heading("7. Deep Q-Network", level=1)
    _add_paragraph(doc, "The policy network has six inputs, two hidden ReLU layers of 64 units, and four Q-value outputs. A separate target network stabilizes the Bellman target.")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("6 inputs  ->  64 ReLU  ->  64 ReLU  ->  4 Q-values")
    r.bold = True
    r.font.name = "Liberation Mono"
    r.font.size = Pt(12)
    _add_paragraph(doc, "For transition (s, a, r, s', done), the target is:")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("y = r + gamma * (1 - done) * Q_target(s', argmax Q_policy(s', a'))").bold = True
    _add_bullets(
        doc,
        [
            "Experience replay stores transitions and trains from random mini-batches.",
            "Epsilon-greedy exploration decreases from 1.00 to 0.05.",
            "Smooth L1 (Huber) loss limits sensitivity to large temporal-difference errors.",
            "Adam updates the policy network and gradient norm is clipped.",
            "Target weights are synchronized periodically.",
        ],
    )

    doc.add_page_break()
    doc.add_heading("8. Training Configuration", level=1)
    _add_table(
        doc,
        ["Hyperparameter", "Value"],
        [
            ["Episodes", "300"],
            ["Discount factor", "0.99"],
            ["Learning rate", "0.001"],
            ["Batch size", "64"],
            ["Replay capacity", "50,000"],
            ["Replay warm-up", "500 transitions"],
            ["Target update", "600 environment steps"],
            ["Epsilon", "1.00 to 0.05"],
            ["Epsilon decay", "25,000 steps"],
            ["Device / seed", "CPU / 440"],
        ],
    )
    _add_paragraph(doc, "The exact run configuration is stored with the result data. Headless training uses the same environment as the Pygame interface but avoids rendering overhead.")

    doc.add_heading("9. Results", level=1)
    doc.add_heading("9.1 Training summary", level=2)
    _add_table(
        doc,
        ["Measurement", "Result"],
        [
            ["Training episodes", "300"],
            ["Exploratory lap completions", "110 (36.7%)"],
            ["Best exploratory reward", "653.0"],
            ["Final-50 mean reward", "614.7"],
            ["Mean completed training lap time", "4.51 s"],
            ["Training collisions", "190"],
        ],
    )
    _add_image(doc, RESULTS_DIR / "reward_per_episode.png", 7.1, "Figure 4. Reward per training episode with rolling average")

    doc.add_page_break()
    doc.add_heading("9.2 Lap time and collision behavior", level=2)
    _add_image(doc, RESULTS_DIR / "lap_time_per_episode.png", 6.9, "Figure 5. Lap time per completed training episode")
    _add_image(doc, RESULTS_DIR / "collision_count_per_episode.png", 6.9, "Figure 6. Collision count per training episode")

    # The two graphs fill the previous page. Begin evaluation on a clean page
    # so the result table is not split after its first row.
    doc.add_page_break()
    doc.add_heading("9.3 Greedy evaluation", level=2)
    _add_table(
        doc,
        ["Track", "Episodes / laps", "Success", "Collisions", "Mean reward", "Mean lap steps"],
        [
            ["Easy", "20 / 20", "100%", "0", "631.0", "295"],
            ["Medium", "20 / 20", "100%", "0", "576.0", "241"],
            ["Hard", "20 / 20", "100%", "0", "593.0", "259"],
        ],
    )
    _add_paragraph(doc, "Training success includes exploratory random actions, while evaluation uses epsilon = 0. Each packaged best checkpoint completed 20 of 20 deterministic episodes from its track's standard start with zero collisions. Medium and Hard use curriculum continuation from easier checkpoints, so these results do not claim independent from-scratch convergence, arbitrary-start generalization, or unseen-track generalization.")

    doc.add_heading("10. User Interface and Model Reuse", level=1)
    _add_bullets(
        doc,
        [
            "Main menu with Manual, Train, Watch, Evaluate, Settings, and Quit.",
            "Live episode, reward, lap, speed, epsilon, loss, and simulation speed.",
            "Pause/continue, training-speed adjustment, immediate save, sensor toggle, and reset.",
            "Selectable track difficulty and red/blue/green car colors.",
            "Best and latest .pth checkpoints for playback and resume.",
        ],
    )
    _add_paragraph(doc, "A checkpoint stores policy and target weights, optimizer state, architecture, training configuration, step counters, loss, and run metadata. A saved model can drive immediately without retraining.")

    doc.add_page_break()
    doc.add_heading("11. Testing and Reliability", level=1)
    _add_paragraph(doc, "Twenty automated tests cover tracks, masks, physics, sensors, state/action contracts, exact rewards, complete-lap behavior, network dimensions, replay sampling, optimization, checkpoint round trips, training output generation, the included model completing a lap without collision, and shutdown checkpoint-error handling.")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("20 passed")
    r.bold = True
    r.font.size = Pt(22)
    r.font.color.rgb = RGBColor.from_string(BLUE)

    doc.add_heading("12. Discussion", level=1)
    _add_paragraph(doc, "The packaged checkpoints produce repeatable standard-start policies on Easy, Medium, and Hard from compact sensor inputs. Easy was trained directly; Medium and Hard use curriculum continuation from easier checkpoints. Stability improved through local progress tracking, ordered checkpoints, experience replay, a target network, gradient clipping, and a deliberate separation between exploratory training and greedy evaluation. Raw CSV/JSON outputs make the reported results inspectable rather than merely asserted.")

    doc.add_heading("13. Limitations", level=1)
    _add_bullets(
        doc,
        [
            "Packaged checkpoint evaluation uses one standard start pose per track; random-start generalization is not established.",
            "Vehicle physics are educational rather than realistic.",
            "The state has no temporal memory or camera images.",
            "Medium and Hard use curriculum continuation from an easier checkpoint rather than independent from-scratch training.",
            "The system is not intended for real vehicle control.",
        ],
    )

    doc.add_heading("14. Future Work", level=1)
    _add_bullets(
        doc,
        [
            "Benchmark from-scratch versus curriculum training on Medium and Hard.",
            "Randomize start positions, speeds, and headings.",
            "Compare alternative curriculum schedules and prioritized replay.",
            "Compare DQN with PPO.",
            "Add obstacles, multiple cars, or camera-image input.",
            "Create richer model-comparison dashboards and training videos.",
        ],
    )

    doc.add_heading("15. Conclusion", level=1)
    _add_paragraph(doc, "The project connects the full reinforcement-learning pipeline - state, action, reward, replay, exploration, network update, checkpointing, and evaluation - to a visible Pygame racing application. The included Easy, Medium, and Hard checkpoints and raw evaluations provide reproducible evidence that the compact DQN can complete each packaged track from its standard start pose on CPU.")

    doc.add_heading("16. Team Contributions", level=1)
    _add_table(
        doc,
        ["Member", "ID", "Contributions"],
        [
            ["Add name", "Add ID", "Add truthful contribution"],
            ["Add name", "Add ID", "Add truthful contribution"],
            ["Add name", "Add ID", "Add truthful contribution"],
        ],
    )

    doc.add_heading("References", level=1)
    refs = [
        "V. Mnih et al., 'Human-level control through deep reinforcement learning,' Nature, 2015.",
        "R. S. Sutton and A. G. Barto, Reinforcement Learning: An Introduction, 2nd edition.",
        "PyTorch documentation: neural networks, optimization, and model serialization.",
        "Pygame documentation: display, event, keyboard, surface, and drawing modules.",
    ]
    for index, ref in enumerate(refs, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.65)
        p.paragraph_format.first_line_indent = Cm(-0.65)
        p.add_run(f"{index}.\t{ref}")

    doc.add_heading("Appendix A - Reproduction Commands", level=1)
    commands = [
        "python -m pip install -r requirements.txt",
        "python main.py gui",
        "python main.py train --track easy --episodes 500",
        "python main.py evaluate --track easy --model models/easy_best.pth --episodes 20",
        "pytest -q",
    ]
    for command in commands:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.6)
        run = p.add_run(command)
        run.font.name = "Liberation Mono"
        run.font.size = Pt(9.5)
        _set_cell_shading if False else None

    output = SUBMISSION_DIR / "CSE440_Self_Driving_Car_Project_Report.docx"
    doc.save(output)
    return output


# ---------- PowerPoint helpers ----------
SLIDE_W = 13.333
SLIDE_H = 7.5
PPT_NAVY = PptRGBColor(24, 43, 69)
PPT_BLUE = PptRGBColor(63, 136, 197)
PPT_LIGHT = PptRGBColor(236, 243, 249)
PPT_WHITE = PptRGBColor(255, 255, 255)
PPT_DARK = PptRGBColor(27, 39, 56)
PPT_MUTED = PptRGBColor(102, 119, 139)
PPT_GREEN = PptRGBColor(65, 164, 112)
PPT_RED = PptRGBColor(210, 74, 68)


def _ppt_text(slide, text, x, y, w, h, *, size=22, bold=False, color=PPT_DARK, align=PP_ALIGN.LEFT, font="Aptos", valign=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(PptInches(x), PptInches(y), PptInches(w), PptInches(h))
    frame = box.text_frame
    frame.clear()
    frame.margin_left = PptInches(0.05)
    frame.margin_right = PptInches(0.05)
    frame.margin_top = PptInches(0.02)
    frame.margin_bottom = PptInches(0.02)
    frame.vertical_anchor = valign
    p = frame.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = font
    run.font.size = PptPt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return box


def _ppt_bullets(slide, items, x, y, w, h, *, size=21, color=PPT_DARK):
    box = slide.shapes.add_textbox(PptInches(x), PptInches(y), PptInches(w), PptInches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = PptInches(0.12)
    tf.margin_right = PptInches(0.05)
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item
        p.level = 0
        p.font.name = "Aptos"
        p.font.size = PptPt(size)
        p.font.color.rgb = color
        p.space_after = PptPt(10)
        p.bullet = True
    return box


def _ppt_title(slide, title, subtitle=None, dark=False):
    color = PPT_WHITE if dark else PPT_NAVY
    _ppt_text(slide, title, 0.55, 0.28, 12.2, 0.55, size=28, bold=True, color=color)
    line = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, PptInches(0.58), PptInches(0.94), PptInches(1.15), PptInches(0.06))
    line.fill.solid(); line.fill.fore_color.rgb = PPT_BLUE; line.line.fill.background()
    if subtitle:
        _ppt_text(slide, subtitle, 1.9, 0.80, 10.4, 0.28, size=12, color=(PPT_LIGHT if dark else PPT_MUTED))


def _ppt_footer(slide, number):
    _ppt_text(slide, "CSE440 | Self-Driving Car Racing Game", 0.55, 7.12, 5.4, 0.22, size=9, color=PPT_MUTED)
    _ppt_text(slide, str(number), 12.25, 7.12, 0.45, 0.22, size=9, color=PPT_MUTED, align=PP_ALIGN.RIGHT)


def _ppt_card(slide, x, y, w, h, title, body, *, fill=PPT_LIGHT, accent=PPT_BLUE, title_size=18, body_size=13):
    shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, PptInches(x), PptInches(y), PptInches(w), PptInches(h))
    shape.fill.solid(); shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = PptRGBColor(201, 216, 229)
    accent_shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, PptInches(x), PptInches(y), PptInches(0.08), PptInches(h))
    accent_shape.fill.solid(); accent_shape.fill.fore_color.rgb = accent; accent_shape.line.fill.background()
    _ppt_text(slide, title, x + 0.22, y + 0.14, w - 0.35, 0.36, size=title_size, bold=True, color=PPT_NAVY)
    # Leave enough height for the last text line. The former 0.82-inch
    # subtraction produced zero-height body boxes in compact cards, which
    # clipped values below the rounded rectangle in LibreOffice rendering.
    _ppt_text(slide, body, x + 0.22, y + 0.55, w - 0.35, max(0.18, h - 0.62), size=body_size, color=PPT_MUTED)


def _ppt_add_image(slide, path: Path, x, y, w=None, h=None):
    kwargs = {"left": PptInches(x), "top": PptInches(y)}
    if w is not None: kwargs["width"] = PptInches(w)
    if h is not None: kwargs["height"] = PptInches(h)
    slide.shapes.add_picture(str(path), **kwargs)


def _ppt_blank(prs: Presentation, bg=PPT_WHITE):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    fill = slide.background.fill
    fill.solid(); fill.fore_color.rgb = bg
    return slide


def build_presentation() -> Path:
    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)
    prs = Presentation()
    core = prs.core_properties
    core.title = "CSE440 Self-Driving Car Racing Game - Presentation"
    core.subject = "Deep Q-Network reinforcement learning project"
    core.author = "CSE440 Project Team"
    core.last_modified_by = "CSE440 Project Team"
    core.keywords = "CSE440, artificial intelligence, reinforcement learning, DQN, Pygame, PyTorch"
    core.comments = "Generated from the completed project source and measured evaluation results."
    prs.slide_width = PptInches(SLIDE_W)
    prs.slide_height = PptInches(SLIDE_H)

    # 1. Title
    slide = _ppt_blank(prs, PPT_NAVY)
    _ppt_text(slide, "SELF-DRIVING CAR\nRACING GAME", 0.7, 0.85, 7.0, 1.45, size=36, bold=True, color=PPT_WHITE)
    _ppt_text(slide, "Deep Q-Network Reinforcement Learning", 0.75, 2.45, 6.6, 0.55, size=22, color=PptRGBColor(177, 213, 242))
    _ppt_text(slide, "CSE440 - Introduction to Artificial Intelligence", 0.75, 3.12, 6.8, 0.35, size=14, color=PPT_LIGHT)
    _ppt_text(slide, "Add team names and IDs", 0.75, 5.92, 5.3, 0.35, size=13, color=PptRGBColor(177, 190, 207))
    _ppt_add_image(slide, PROJECT_ROOT / "assets" / "tracks" / "easy.png", 7.5, 0.72, w=5.25, h=3.5)
    _ppt_add_image(slide, IMAGES_DIR / "architecture.png", 7.2, 4.45, w=5.75, h=2.0)

    # 2. Idea and scope
    slide = _ppt_blank(prs)
    _ppt_title(slide, "Project Idea and Scope", "A focused AI demonstration that runs on a normal laptop")
    cards = [
        ("Agent", "One AI-controlled car learns a policy from reward, not a scripted route."),
        ("Environment", "2D tracks, simple physics, image-mask collision, checkpoints, and laps."),
        ("Observation", "Five distance rays plus speed create a compact six-value state."),
        ("Learning", "DQN, replay memory, target network, and epsilon-greedy exploration."),
    ]
    positions = [(0.75, 1.45), (6.85, 1.45), (0.75, 4.02), (6.85, 4.02)]
    for (title, body), (x, y) in zip(cards, positions, strict=True):
        _ppt_card(slide, x, y, 5.72, 1.92, title, body, body_size=16)
    _ppt_footer(slide, 2)

    # 3. Architecture
    slide = _ppt_blank(prs)
    _ppt_title(slide, "Agent-Environment Training Loop", "Observe, act, reward, replay, update, repeat")
    _ppt_add_image(slide, IMAGES_DIR / "architecture.png", 0.5, 1.35, w=12.35, h=4.28)
    _ppt_card(slide, 1.0, 5.72, 3.5, 1.02, "State", "5 distances + speed", body_size=13)
    _ppt_card(slide, 4.9, 5.72, 3.5, 1.02, "Action", "left / right / straight / brake", body_size=13)
    _ppt_card(slide, 8.8, 5.72, 3.5, 1.02, "Learning", "reward -> replay -> DQN update", body_size=13)
    _ppt_footer(slide, 3)

    # 4. Tracks and physics
    slide = _ppt_blank(prs)
    _ppt_title(slide, "Game Environment", "Image-based tracks and intentionally simple vehicle physics")
    for i, name in enumerate(("easy", "medium", "hard")):
        x = 0.55 + i * 4.25
        _ppt_add_image(slide, PROJECT_ROOT / "assets" / "tracks" / f"{name}.png", x, 1.30, w=3.95, h=2.63)
        _ppt_text(slide, name.title(), x, 4.02, 3.95, 0.3, size=17, bold=True, color=PPT_NAVY, align=PP_ALIGN.CENTER)
    _ppt_bullets(slide, [
        "White road / black wall mask for collision and sensors",
        "Nine car-body probe points",
        "720 ordered centerline points and 12 checkpoints",
        "Position, speed, heading, steering, acceleration, braking, friction",
    ], 0.75, 4.60, 12.0, 1.85, size=17)
    _ppt_footer(slide, 4)

    # 5. Sensors/state
    slide = _ppt_blank(prs)
    _ppt_title(slide, "State Representation", "The neural network receives six normalized values")
    _ppt_add_image(slide, IMAGES_DIR / "gameplay.png", 0.55, 1.28, w=7.45, h=4.06)
    _ppt_card(slide, 8.35, 1.32, 4.35, 1.25, "Five ray angles", "-90°, -45°, 0°, +45°, +90°", body_size=18)
    _ppt_card(slide, 8.35, 2.82, 4.35, 1.25, "Normalization", "distance / maximum range\nspeed / maximum speed", body_size=17)
    _ppt_card(slide, 8.35, 4.32, 4.35, 1.25, "State vector", "[left, front_left, front,\nfront_right, right, speed]", body_size=16)
    _ppt_text(slide, "Small, interpretable, and CPU-friendly", 1.0, 5.78, 6.7, 0.4, size=20, bold=True, color=PPT_BLUE, align=PP_ALIGN.CENTER)
    _ppt_footer(slide, 5)

    # 6. Actions/reward
    slide = _ppt_blank(prs)
    _ppt_title(slide, "Actions and Reward Engineering", "DQN fits the four-action discrete control problem")
    actions = [("0", "Turn left"), ("1", "Turn right"), ("2", "Go straight"), ("3", "Brake")]
    for i, (idx, action) in enumerate(actions):
        x = 0.65 + i * 3.12
        shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, PptInches(x), PptInches(1.38), PptInches(2.65), PptInches(1.0))
        shape.fill.solid(); shape.fill.fore_color.rgb = PPT_NAVY
        shape.line.fill.background()
        _ppt_text(slide, idx, x + 0.12, 1.55, 0.45, 0.45, size=25, bold=True, color=PptRGBColor(151, 205, 246), align=PP_ALIGN.CENTER)
        _ppt_text(slide, action, x + 0.62, 1.60, 1.85, 0.35, size=18, bold=True, color=PPT_WHITE, align=PP_ALIGN.CENTER)
    rewards = [
        ("Driving forward", "+1", PPT_GREEN),
        ("Checkpoint", "+20", PPT_GREEN),
        ("Lap complete", "+100", PPT_GREEN),
        ("Collision", "-100", PPT_RED),
        ("Driving backwards", "-10", PPT_RED),
        ("Standing still", "-2", PPT_RED),
    ]
    for i, (label, value, accent) in enumerate(rewards):
        col = i % 2; row = i // 2
        x = 0.85 + col * 6.1; y = 2.85 + row * 1.06
        _ppt_card(slide, x, y, 5.55, 0.94, label, value, accent=accent, title_size=16, body_size=17)
    _ppt_text(slide, "Good rewards matter more than an unnecessarily complicated network.", 1.0, 6.25, 11.3, 0.42, size=20, bold=True, color=PPT_BLUE, align=PP_ALIGN.CENTER)
    _ppt_footer(slide, 6)

    # 7. DQN
    slide = _ppt_blank(prs)
    _ppt_title(slide, "Deep Q-Network", "A compact 6 -> 64 -> 64 -> 4 policy network")
    layer_data = [("Input", "6 values", PPT_BLUE), ("Hidden", "64 ReLU", PPT_NAVY), ("Hidden", "64 ReLU", PPT_NAVY), ("Output", "4 Q-values", PPT_BLUE)]
    xs = [0.75, 3.75, 6.75, 9.75]
    for i, ((label, detail, color), x) in enumerate(zip(layer_data, xs, strict=True)):
        shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, PptInches(x), PptInches(1.75), PptInches(2.35), PptInches(1.45))
        shape.fill.solid(); shape.fill.fore_color.rgb = color; shape.line.fill.background()
        _ppt_text(slide, label, x + 0.12, 2.03, 2.1, 0.35, size=20, bold=True, color=PPT_WHITE, align=PP_ALIGN.CENTER)
        _ppt_text(slide, detail, x + 0.12, 2.50, 2.1, 0.3, size=16, color=PptRGBColor(218, 235, 249), align=PP_ALIGN.CENTER)
        if i < 3:
            arrow = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.CHEVRON, PptInches(x + 2.48), PptInches(2.23), PptInches(0.55), PptInches(0.45))
            arrow.fill.solid(); arrow.fill.fore_color.rgb = PPT_MUTED; arrow.line.fill.background()
    _ppt_bullets(slide, [
        "Experience replay: random mini-batches from stored transitions",
        "Target network: slower-moving Bellman target",
        "Double DQN target selection by default",
        "Huber loss + Adam + gradient clipping",
        "Gamma = 0.99; epsilon 1.00 -> 0.05",
    ], 1.05, 3.75, 11.3, 2.25, size=19)
    _ppt_footer(slide, 7)

    # 8. Training interface
    slide = _ppt_blank(prs)
    _ppt_title(slide, "Training and Model Lifecycle", "Live controls for demonstration; headless mode for speed")
    _ppt_card(slide, 0.75, 1.30, 3.75, 1.28, "Live training", "Episode, reward, speed, epsilon, loss, sensors", body_size=15)
    _ppt_card(slide, 4.80, 1.30, 3.75, 1.28, "Controls", "Start, pause, continue, speed up, save", body_size=15)
    _ppt_card(slide, 8.85, 1.30, 3.75, 1.28, "Headless CLI", "Faster CPU training without rendering", body_size=15)
    _ppt_card(slide, 0.75, 3.02, 3.75, 1.28, "Best checkpoint", "Highest completed/reward score", body_size=15)
    _ppt_card(slide, 4.80, 3.02, 3.75, 1.28, "Latest checkpoint", "Resume optimizer and training state", body_size=15)
    _ppt_card(slide, 8.85, 3.02, 3.75, 1.28, "Results", "CSV, JSON, reward, lap, collision graphs", body_size=15)
    _ppt_text(slide, "Training behavior includes random exploration; evaluation uses epsilon = 0.", 0.85, 5.05, 11.7, 0.55, size=23, bold=True, color=PPT_BLUE, align=PP_ALIGN.CENTER)
    lifecycle_facts = [
        "300 Easy episodes",
        "CPU only",
        "Seed/config saved",
        "20 automated tests",
    ]
    for i, fact in enumerate(lifecycle_facts):
        x = 0.75 + i * 3.03
        shape = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            PptInches(x),
            PptInches(5.82),
            PptInches(2.72),
            PptInches(0.72),
        )
        shape.fill.solid(); shape.fill.fore_color.rgb = PPT_LIGHT
        shape.line.color.rgb = PptRGBColor(198, 216, 229)
        _ppt_text(
            slide,
            fact,
            x + 0.08,
            5.99,
            2.56,
            0.28,
            size=15,
            bold=True,
            color=PPT_NAVY,
            align=PP_ALIGN.CENTER,
            valign=MSO_ANCHOR.MIDDLE,
        )
    _ppt_footer(slide, 8)

    # 9. Reward results
    slide = _ppt_blank(prs)
    _ppt_title(slide, "Training Results", "The reward trend becomes strongly positive as laps are learned")
    _ppt_add_image(slide, RESULTS_DIR / "reward_per_episode.png", 0.55, 1.20, w=8.25, h=4.55)
    _ppt_card(slide, 9.05, 1.28, 3.55, 1.05, "300", "training episodes", body_size=16)
    _ppt_card(slide, 9.05, 2.57, 3.55, 1.05, "110", "exploratory lap completions", body_size=16)
    _ppt_card(slide, 9.05, 3.86, 3.55, 1.05, "614.7", "final-50 mean reward", body_size=16)
    _ppt_card(slide, 9.05, 5.15, 3.55, 1.05, "653.0", "best exploratory reward", body_size=16)
    _ppt_text(slide, "Noise remains because epsilon-greedy training intentionally keeps exploring.", 0.9, 6.25, 8.0, 0.4, size=16, color=PPT_MUTED, align=PP_ALIGN.CENTER)
    _ppt_footer(slide, 9)

    # 10. Evaluation
    slide = _ppt_blank(prs)
    _ppt_title(slide, "Greedy Evaluation", "Standard start position, epsilon = 0, 20 episodes per track")
    eval_rows = [
        ("Easy", "20 / 20", "0 collisions", "Reward 631.0", "295 mean lap steps"),
        ("Medium", "20 / 20", "0 collisions", "Reward 576.0", "241 mean lap steps"),
        ("Hard", "20 / 20", "0 collisions", "Reward 593.0", "259 mean lap steps"),
    ]
    for i, (track, laps, collisions, reward, steps) in enumerate(eval_rows):
        x = 0.72 + i * 4.18
        y = 1.52
        shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, PptInches(x), PptInches(y), PptInches(3.75), PptInches(3.78))
        shape.fill.solid(); shape.fill.fore_color.rgb = PPT_LIGHT
        shape.line.color.rgb = PptRGBColor(198, 216, 229)
        _ppt_text(slide, track, x + 0.18, y + 0.32, 3.39, 0.52, size=26, bold=True, color=PPT_NAVY, align=PP_ALIGN.CENTER)
        _ppt_text(slide, laps, x + 0.18, y + 1.00, 3.39, 0.55, size=30, bold=True, color=PPT_GREEN, align=PP_ALIGN.CENTER)
        _ppt_text(slide, "completed laps", x + 0.18, y + 1.58, 3.39, 0.32, size=15, color=PPT_MUTED, align=PP_ALIGN.CENTER)
        _ppt_text(slide, collisions, x + 0.18, y + 2.08, 3.39, 0.35, size=18, bold=True, color=PPT_GREEN, align=PP_ALIGN.CENTER)
        _ppt_text(slide, reward, x + 0.18, y + 2.58, 3.39, 0.35, size=17, color=PPT_BLUE, align=PP_ALIGN.CENTER)
        _ppt_text(slide, steps, x + 0.18, y + 3.03, 3.39, 0.34, size=15, color=PPT_MUTED, align=PP_ALIGN.CENTER)
    _ppt_text(slide, "All three packaged best checkpoints reached 100% success with zero collisions in deterministic standard-start evaluation. Medium and Hard use curriculum continuation; arbitrary-start and unseen-track generalization are not claimed.", 0.85, 5.66, 11.65, 0.88, size=16, color=PPT_NAVY, align=PP_ALIGN.CENTER)
    _ppt_footer(slide, 10)

    # 11. Interface
    slide = _ppt_blank(prs)
    _ppt_title(slide, "Complete Pygame Application", "Manual drive, live training, model playback, evaluation, and settings")
    _ppt_add_image(slide, IMAGES_DIR / "gameplay.png", 0.45, 1.18, w=9.0, h=4.91)
    _ppt_bullets(slide, [
        "Selectable track difficulty",
        "Red / blue / green car",
        "Live sensor rays",
        "Pause / continue / save",
        "Best/latest model loading",
        "Automatic evaluation JSON",
    ], 9.68, 1.45, 3.0, 3.95, size=16)
    _ppt_text(slide, "Same core environment in every mode", 9.72, 5.55, 2.85, 0.6, size=18, bold=True, color=PPT_BLUE, align=PP_ALIGN.CENTER)
    _ppt_footer(slide, 11)

    # 12. Reliability/limitations
    slide = _ppt_blank(prs)
    _ppt_title(slide, "Reliability, Limitations, and Future Work", "Measured claims and clear project boundaries")
    _ppt_card(slide, 0.65, 1.30, 4.0, 4.95, "Reliability", "20 automated tests\n\nAtomic checkpoint writes\n\nRaw CSV and JSON\n\nSaved seed/configuration\n\nIncluded model lap test", accent=PPT_GREEN, body_size=17)
    _ppt_card(slide, 4.68, 1.30, 4.0, 4.95, "Limitations", "Fixed evaluation start\n\nMedium/Hard use curriculum continuation\n\nSimple educational physics\n\nNo temporal memory\n\nNot real vehicle control", accent=PPT_RED, body_size=17)
    _ppt_card(slide, 8.71, 1.30, 4.0, 4.95, "Future work", "From-scratch vs curriculum benchmarks\n\nRandomized starts\n\nCurriculum comparison\n\nPPO comparison\n\nObstacles or camera input", accent=PPT_BLUE, body_size=17)
    _ppt_footer(slide, 12)

    # 13. Conclusion
    slide = _ppt_blank(prs, PPT_NAVY)
    _ppt_text(slide, "CONCLUSION", 0.75, 0.68, 5.2, 0.55, size=30, bold=True, color=PptRGBColor(151, 205, 246))
    _ppt_text(slide, "A complete, explainable, CPU-friendly\nreinforcement-learning project", 0.75, 1.55, 7.1, 1.25, size=31, bold=True, color=PPT_WHITE)
    _ppt_bullets(slide, [
        "Full state -> action -> reward -> replay -> update pipeline",
        "Validated checkpoints complete Easy, Medium, and Hard from their standard starts",
        "Interactive Pygame app plus headless training/evaluation",
        "Models, raw results, graphs, documentation, and tests included",
    ], 0.82, 3.15, 7.1, 2.45, size=19, color=PPT_LIGHT)
    _ppt_add_image(slide, PROJECT_ROOT / "assets" / "tracks" / "easy.png", 8.45, 1.22, w=4.25, h=2.83)
    _ppt_text(slide, "Questions?", 8.65, 4.72, 3.8, 0.7, size=32, bold=True, color=PPT_WHITE, align=PP_ALIGN.CENTER)
    _ppt_text(slide, "Add presenter names and IDs", 8.65, 5.62, 3.8, 0.35, size=13, color=PptRGBColor(177, 190, 207), align=PP_ALIGN.CENTER)

    output = SUBMISSION_DIR / "CSE440_Self_Driving_Car_Presentation.pptx"
    prs.save(output)
    return output


def main() -> None:
    report = build_report()
    deck = build_presentation()
    print(report)
    print(deck)


if __name__ == "__main__":
    main()
