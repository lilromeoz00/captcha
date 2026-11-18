"""Build the CS471 presentation deck.

    python presentation/make_deck.py

Produces
    CS471_Presentation.pptx        the deliverable (editable PowerPoint)
    presentation/previews/pNN.png  a raster preview of every slide

The deck is described once as a list of slide specs using absolute inch
coordinates, then rendered twice: to PPTX via python-pptx, and to PNG via PIL.
Rendering twice is deliberate -- python-pptx cannot be rasterised on this machine
(no LibreOffice), so the PNG backend is how the layout gets visually verified.
Any element that would fall outside the slide is reported as an error.
"""

from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_PPTX = os.path.join(ROOT, "CS471_Presentation.pptx")
PREVIEW = os.path.join(HERE, "previews")

# ---------------------------------------------------------------- geometry
W, H = 13.333, 7.5          # inches, 16:9
DPI = 120                    # preview resolution
M = 0.80                     # side margin

# ---------------------------------------------------------------- palette
BG = "0A0E1A"
CARD = "141B2E"
CARD2 = "1B2438"
INK = "F2F5FA"
MUTED = "8A96AC"
DIM = "5C6880"
ACCENT = "4C8DFF"
AMBER = "F5A524"
RED = "EF4444"
GREEN = "34D399"
RULE = "25304A"

FONT_SANS = r"C:\Windows\Fonts\segoeui.ttf"
FONT_SEMI = r"C:\Windows\Fonts\seguisb.ttf"
FONT_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
FONT_MONO = r"C:\Windows\Fonts\consola.ttf"


# ============================================================ element helpers
def rect(x, y, w, h, fill=CARD, line=None, lw=1.0, radius=0.10):
    return dict(t="rect", x=x, y=y, w=w, h=h, fill=fill, line=line, lw=lw, radius=radius)


def text(x, y, w, s, size=16, color=INK, bold=False, align="l",
         font="sans", line_spacing=1.18, italic=False):
    return dict(t="text", x=x, y=y, w=w, s=s, size=size, color=color, bold=bold,
                align=align, font=font, ls=line_spacing, italic=italic)


def rule(x, y, w, color=ACCENT, lw=3.0):
    return dict(t="rule", x=x, y=y, w=w, color=color, lw=lw)


def bullets(x, y, w, items, size=15, color=INK, gap=0.40, mark=ACCENT):
    return dict(t="bullets", x=x, y=y, w=w, items=items, size=size, color=color,
                gap=gap, mark=mark)


def image(x, y, w, h, path):
    return dict(t="img", x=x, y=y, w=w, h=h, path=path)


def badge(x, y, size, glyph, color):
    """A tick or cross drawn as strokes, not a font glyph.

    Segoe UI has no U+2713/U+2717, so text glyphs render as tofu boxes in both the
    PPTX and the preview. Drawing the strokes avoids the dependency entirely.
    """
    return dict(t="badge", x=x, y=y, size=size, glyph=glyph, color=color)


def arrow(x, y, w, h, color=DIM):
    return dict(t="arrow", x=x, y=y, w=w, h=h, color=color)


# ============================================================ slide builders
def slide_title():
    return [
        rect(0, 0, W, H, fill=BG, radius=0),
        # accent bar
        rect(M, 2.30, 0.10, 2.05, fill=ACCENT, radius=0.02),
        text(M + 0.42, 2.22, 11.0, "CS471  \u00b7  FINAL PROJECT  \u00b7  LESSON 41",
             size=12, color=ACCENT, bold=True),
        text(M + 0.42, 2.62, 11.2, "Defeating Adversarial\nVisual Access Control",
             size=50, color=INK, bold=True, line_spacing=1.06),
        text(M + 0.42, 4.52, 10.6,
             "A convolutional detector and a multiset-matching decision layer\n"
             "for count-based challenge images",
             size=17, color=MUTED, line_spacing=1.35),
        rule(M + 0.42, 5.62, 2.2, color=RULE, lw=1.2),
        text(M + 0.42, 5.82, 6.0, "Jordan Moore", size=15, color=INK, bold=True),
        text(M + 0.42, 6.22, 8.0, "github.com/lilromeoz00/captcha  \u00b7  tag: final",
             size=11.5, color=MUTED, font="mono"),
    ]


def slide_problem():
    stats = [("$2 / 1,000", "cost of a human-solved\nchallenge batch", AMBER),
             ("~10%", "success rate, because the\nfamily rotates", RED),
             ("seconds\u2013minutes", "latency per item,\nhuman-bound", MUTED)]
    els = header("01", "OPERATIONAL PROBLEM",
                 "Collection stops at the challenge layer,\nnot at the cipher")
    x = M
    for big, cap, col in stats:
        els.append(rect(x, 2.72, 3.62, 1.62, fill=CARD))
        els.append(text(x + 0.30, 2.94, 3.1, big, size=27, color=col, bold=True))
        els.append(text(x + 0.30, 3.46, 3.2, cap, size=11.5, color=MUTED, line_spacing=1.28))
        x += 3.86

    els.append(text(M, 4.62, 11.7, "The prevailing commercial solution is manual labour arbitrage: "
                                    "each challenge is distributed to a low-wage worker.",
                    size=15, color=INK))
    els.append(bullets(M, 5.10, 11.6, [
        ("Latency", "human-bound, therefore incompatible with time-sensitive collection."),
        ("Reliability", "approximately 10%, because the challenge family is revised faster than a workforce adapts."),
        ("Dependency", "an external population that cannot be audited, scaled on demand, or trusted with the target set."),
    ], size=13.5, gap=0.42))
    els.append(text(M, 6.42, 11.6, "The third deficiency is a security property, not an economic one.",
                    size=13, color=ACCENT, bold=True))
    return els


def slide_multiset():
    els = header("02", "PROBLEM FORMULATION",
                 "The task is multiset matching, not recognition")

    # key card
    els.append(rect(M, 2.62, 3.30, 2.05, fill=CARD))
    els.append(text(M + 0.28, 2.80, 2.8, "KEY  (silhouette)", size=10.5, color=ACCENT, bold=True))
    els.append(text(M + 0.28, 3.14, 2.9, "onion \u00d7 2\npotato \u00d7 2", size=17, color=INK,
                    line_spacing=1.35))
    els.append(text(M + 0.28, 4.16, 2.9, "four objects, grayscale render", size=10, color=DIM))

    # arrow
    els.append(arrow(M + 3.46, 3.44, 0.52, 0.40, color=ACCENT))

    # wrong candidate
    els.append(rect(M + 4.12, 2.62, 3.30, 2.05, fill=CARD, line=RED, lw=1.4))
    els.append(text(M + 4.40, 2.80, 2.8, "SCENE 4", size=10.5, color=RED, bold=True))
    els.append(text(M + 4.40, 3.14, 2.9, "onion \u00d7 2\npotato \u00d7 1\ncorn \u00d7 1", size=15,
                    color=INK, line_spacing=1.30))
    els.append(badge(M + 6.62, 2.70, 0.42, "cross", RED))

    # correct candidate
    els.append(rect(M + 7.62, 2.62, 3.30, 2.05, fill=CARD, line=GREEN, lw=1.4))
    els.append(text(M + 7.90, 2.80, 2.8, "SCENE 6", size=10.5, color=GREEN, bold=True))
    els.append(text(M + 7.90, 3.14, 2.9, "onion \u00d7 2\npotato \u00d7 2", size=17, color=INK,
                    line_spacing=1.35))
    els.append(badge(M + 10.12, 2.70, 0.42, "tick", GREEN))

    els.append(text(M, 4.96, 11.7,
                    "Every object in scene 4 was detected correctly, and scene 4 is still the "
                    "wrong answer.", size=15, color=INK, bold=True))
    els.append(text(M, 5.40, 11.7,
                    "Accuracy therefore depends on counts per class. A detector with 97% per-object "
                    "accuracy can be far less accurate at the gate, because error compounds across "
                    "four objects and eight candidates. This is why the system is built as a scoring "
                    "rule over detector output rather than as a classifier.", size=13.5, color=MUTED,
                    line_spacing=1.34))
    return els


def slide_algorithm():
    els = header("03", "ALGORITHM",
                 "Learned perception, derived decision")
    # pipeline
    boxes = [("1600\u00d7400\nframe", "9 fixed tiles"),
             ("YOLO26s", "200\u00d7200 per tile"),
             ("9 multisets", "counts per class"),
             ("score", "asymmetric penalty"),
             ("select", "or abstain")]
    bw, gap = 2.16, 0.30
    x = M
    for i, (top, sub) in enumerate(boxes):
        fill = CARD2 if i in (1, 3) else CARD
        line = ACCENT if i in (1, 3) else None
        els.append(rect(x, 2.66, bw, 1.34, fill=fill, line=line, lw=1.3))
        els.append(text(x + 0.18, 2.86, bw - 0.36, top, size=13.5, color=INK, bold=True,
                        align="c", line_spacing=1.22))
        els.append(text(x + 0.12, 3.54, bw - 0.24, sub, size=9.5, color=MUTED, align="c"))
        if i < len(boxes) - 1:
            els.append(arrow(x + bw + 0.03, 3.24, gap - 0.06, 0.18, color=DIM))
        x += bw + gap

    els.append(text(M, 4.24, 11.7, "learned", size=10, color=ACCENT, bold=True))
    els.append(text(M, 4.42, 5.4,
                    "one batched forward pass over nine tiles; the only\n"
                    "component that depends on training data",
                    size=11.5, color=MUTED, line_spacing=1.30))
    els.append(text(M + 6.05, 4.24, 5.6, "derived", size=10, color=GREEN, bold=True))
    els.append(text(M + 6.05, 4.42, 5.6,
                    "closed-form scoring; 8 \u00d7 O(9) integer comparisons\n"
                    "per frame, no second model",
                    size=11.5, color=MUTED, line_spacing=1.30))

    # formula
    els.append(rect(M, 5.30, 11.73, 1.16, fill="0E1526", line=RULE, lw=1.0))
    els.append(text(M + 0.34, 5.48, 11.0,
                    "score(K, B) = \u2212( 10 \u00b7 \u03a3 max(0, K[c] \u2212 B[c])  +  "
                    "1 \u00b7 \u03a3 max(0, B[c] \u2212 K[c]) )",
                    size=17, color=INK, font="mono"))
    els.append(text(M + 2.55, 5.94, 4.0, "\u2191 missed key objects (\u00d710)",
                    size=10, color=AMBER, font="mono"))
    els.append(text(M + 7.35, 5.94, 4.2, "\u2191 surplus objects (\u00d71)",
                    size=10, color=MUTED, font="mono"))
    els.append(text(M, 6.62, 11.7,
                    "Because cost is linear in counts, min(K[c], B[c]) per class is exact \u2014 "
                    "no assignment problem.", size=11.5, color=MUTED))
    return els


def slide_decisions():
    els = header("04", "DESIGN",
                 "Two decisions that carry the system")

    els.append(rect(M, 2.46, 5.70, 3.18, fill=CARD))
    els.append(rect(M, 2.46, 0.07, 3.18, fill=ACCENT, radius=0.02))
    els.append(text(M + 0.38, 2.66, 5.0, "1  \u00b7  Asymmetric penalty", size=16, color=INK, bold=True))
    els.append(text(M + 0.38, 3.08, 5.05,
                    "Measured detector behaviour: 99.0% recall, 2.1% false-positive leakage. "
                    "The error is one-sided.", size=12.5, color=MUTED, line_spacing=1.34))
    els.append(text(M + 0.38, 3.96, 5.05,
                    "A missing object is unrecoverable downstream. A surplus object is noise the "
                    "score can absorb. Weighting the unrecoverable error ten times higher makes the "
                    "score approximate a likelihood ratio.", size=12.5, color=MUTED, line_spacing=1.34))
    els.append(text(M + 0.38, 5.22, 5.05, "justified by mechanism, not by tuning",
                    size=11, color=AMBER, bold=True))

    els.append(rect(M + 6.03, 2.46, 5.70, 3.18, fill=CARD))
    els.append(rect(M + 6.03, 2.46, 0.07, 3.18, fill=GREEN, radius=0.02))
    els.append(text(M + 6.41, 2.66, 5.0, "2  \u00b7  Abstain on a tie", size=16, color=INK, bold=True))
    els.append(text(M + 6.41, 3.08, 5.05,
                    "The margin is the gap between the highest and second-highest scores. "
                    "A margin of zero means two candidates are indistinguishable.",
                    size=12.5, color=MUTED, line_spacing=1.34))
    els.append(text(M + 6.41, 4.14, 5.05,
                    "Because no attempt has been consumed, requesting a new challenge weakly "
                    "dominates an indeterminate guess. A softmax classifier cannot express this.",
                    size=12.5, color=MUTED, line_spacing=1.34))
    els.append(text(M + 6.41, 5.22, 5.05, "enables unattended operation and escalation",
                    size=11, color=GREEN, bold=True))

    els.append(text(M, 5.92, 11.7,
                    "The margin is exported, so the system can be run in a precision-oriented mode: "
                    "high-confidence answers accepted automatically, the remainder escalated.",
                    size=12.5, color=MUTED))
    return els


def slide_demo():
    els = header("05", "LIVE DEMONSTRATION",
                 "One frame in, one decision out")

    # The real annotated output at full width. 1600x400 source, so 4:1.
    els.append(rect(M - 0.05, 2.33, 11.83, 3.03, fill="0E1526", line=RULE, lw=1.0))
    els.append(image(M, 2.38, 11.73, 2.93, os.path.join(HERE, "demo_crop.jpg")))
    # The source frame is genuinely black to the right of the key tile, so that
    # region is used for the annotation rather than left empty.
    els.append(text(M + 3.55, 3.96, 6.6, "WHAT THE FRAME SHOWS", size=9.5,
                    color=ACCENT, bold=True))
    els.append(bullets(M + 3.55, 4.28, 8.0, [
        "Green border: the selected scene. Cyan border: the key.",
        "Per-scene score printed on each tile, so the ranking is auditable.",
        "Basket 4 scores \u22121: one surplus detection, no missed object.",
    ], size=10.5, gap=0.34))

    # Verbatim terminal output.
    els.append(rect(M, 5.68, 11.73, 1.24, fill="0E1526", line=RULE, lw=1.0))
    els.append(text(M + 0.24, 5.80, 0.55, "PS>", size=9.5, color=ACCENT, bold=True, font="mono"))
    els.append(text(M + 0.78, 5.80, 10.6,
                    "python -m solver solve data\\strips\\strip_0000.jpg --annotate out.jpg",
                    size=9.5, color=INK, font="mono"))
    els.append(text(M + 0.24, 6.06, 11.3,
                    "key (S)    : cucumberx1 eggplantx3", size=9.5, color=MUTED, font="mono"))
    els.append(text(M + 0.24, 6.28, 11.3,
                    "  basket 4 : cucumberx2 eggplantx3          score=   -1  <-- ANSWER",
                    size=9.5, color=GREEN, font="mono"))
    els.append(text(M + 0.24, 6.50, 11.3,
                    "decision   : answer basket 4   margin=10  misses=0 extras=1  tie=False",
                    size=9.5, color=ACCENT, font="mono"))
    return els


def slide_baselines():
    els = header("06", "QUANTITATIVE RESULTS",
                 "Six baselines on identical evidence")
    els.append(rect(M, 2.30, 7.72, 3.62, fill="FFFFFF", radius=0.06))
    els.append(image(M + 0.16, 2.44, 7.40, 3.34, os.path.join(ROOT, "figures", "fig1_baselines.png")))

    els.append(text(M + 8.02, 2.36, 3.75, "Task accuracy, 48 frames", size=10, color=ACCENT, bold=True))
    rows = [("Random (1/8)", "12.5%", MUTED), ("Always basket 0", "18.8%", MUTED),
            ("Classical CV", "12.5%", MUTED), ("YOLO + count", "20.8%", MUTED),
            ("YOLO + confidence", "25.0%", MUTED), ("Full agent, 1:1", "100%", INK),
            ("Full agent", "100%", ACCENT)]
    y = 2.68
    for name, val, col in rows:
        els.append(text(M + 8.02, y, 2.55, name, size=10.5, color=MUTED))
        els.append(text(M + 10.62, y, 1.15, val, size=10.5, color=col, bold=True, align="r"))
        y += 0.31
    els.append(rule(M + 8.02, y + 0.02, 3.75, color=RULE, lw=1.0))

    els.append(text(M, 6.20, 11.7,
                    "36 frames corrected and 0 regressed against the strongest baseline lacking a "
                    "matching stage (McNemar p = 2.9\u00d710\u207b\u00b9\u00b9).", size=12.5, color=INK))
    els.append(text(M, 6.60, 11.7,
                    "Baselines that disregard the key remain within noise of chance: localisation "
                    "alone is insufficient without comparison of counts.",
                    size=11.5, color=MUTED))
    return els


def slide_perception():
    els = header("07", "QUANTITATIVE RESULTS",
                 "Perception is not the bottleneck")
    els.append(rect(M, 2.42, 5.55, 3.16, fill=CARD))
    els.append(text(M + 0.32, 2.58, 4.9, "DETECTOR, 288 HELD-OUT TILES", size=10, color=ACCENT, bold=True))
    rows = [("Recall", "1132 / 1143", "99.0%"), ("Precision", "\u2014", "97.9%"),
            ("mAP50", "\u2014", "0.983"), ("Calibration error", "\u2014", "0.127"),
            ("Median IoU", "\u2014", "0.895")]
    y = 2.94
    for a, b, c in rows:
        els.append(text(M + 0.32, y, 2.4, a, size=11.5, color=MUTED))
        els.append(text(M + 2.85, y, 1.3, b, size=11.5, color=DIM, align="r"))
        els.append(text(M + 4.30, y, 1.05, c, size=11.5, color=INK, bold=True, align="r"))
        y += 0.42

    els.append(rect(M + 5.90, 2.42, 5.83, 3.16, fill=CARD))
    els.append(text(M + 6.22, 2.58, 5.2, "ORACLE CEILING DECOMPOSITION", size=10, color=GREEN, bold=True))
    els.append(text(M + 6.22, 2.96, 2.2, "39 / 48", size=34, color=MUTED, bold=True))
    els.append(text(M + 6.22, 3.52, 2.3, "frames contained\na candidate that exactly\nmatched the key",
                    size=10.5, color=DIM, line_spacing=1.28))
    els.append(text(M + 8.72, 2.96, 2.2, "39 / 39", size=34, color=ACCENT, bold=True))
    els.append(text(M + 8.72, 3.52, 2.6, "of those, selected\ncorrectly by the\nranking stage",
                    size=10.5, color=DIM, line_spacing=1.28))
    els.append(text(M + 6.22, 4.72, 5.2, "The ranking stage converts all available information.",
                    size=11, color=GREEN, bold=True))

    els.append(text(M, 5.80, 11.7,
                    "The nine frames without an exact candidate were still answered correctly by "
                    "partial scoring, which indicates that the penalty structure orders candidates "
                    "correctly even when perception is lossy.", size=12, color=MUTED,
                    line_spacing=1.30))
    els.append(rule(M, 6.46, 11.7, color=RULE, lw=1.0))
    els.append(text(M, 6.58, 8.0, "48/48 = 100%", size=19, color=INK, bold=True))
    els.append(text(M + 2.75, 6.66, 8.5, "Wilson 95% CI [92.6, 100.0]",
                    size=11.5, color=MUTED))
    return els


def slide_negative():
    els = header("08", "NEGATIVE RESULT",
                 "The headline claim does not survive\nthe data", accent=AMBER)
    els.append(rect(M, 2.60, 5.90, 3.32, fill="FFFFFF", radius=0.06))
    els.append(image(M + 0.18, 2.74, 5.54, 3.04,
                     os.path.join(ROOT, "figures", "fig8_penalty_sweep.png")))

    els.append(rect(M + 6.24, 2.60, 5.49, 3.32, fill=CARD))
    els.append(text(M + 6.56, 2.78, 4.9, "PENALTY RATIO ABLATION", size=10, color=AMBER, bold=True))
    els.append(text(M + 6.56, 3.14, 4.9,
                    "Accuracy is 48/48 for every ratio from 1:1 to 50:1. A symmetric penalty "
                    "scores identically.", size=12.5, color=INK, line_spacing=1.34))
    els.append(text(M + 6.56, 3.96, 4.9,
                    "The evaluation set is saturated and cannot distinguish the asymmetric score "
                    "from a symmetric one. McNemar returns p = 1 with no discordant pairs.",
                    size=12, color=MUTED, line_spacing=1.34))
    els.append(text(M + 6.56, 4.94, 4.9, "Reported in \u00a74.4 rather than omitted.",
                    size=11, color=AMBER, bold=True))

    els.append(text(M, 6.14, 11.7,
                    "The value 10 is therefore justified by the measured one-sided error "
                    "distribution and by unit tests that fix the required ordering \u2014 not by a "
                    "measured optimum. A tuned value would not be defensible.",
                    size=12.5, color=MUTED, line_spacing=1.34))
    return els


def slide_failure():
    els = header("09", "FAILURE CASE",
                 "The binding constraint is the link,\nnot the adversary", accent=RED)
    els.append(rect(M, 2.60, 7.60, 3.24, fill="FFFFFF", radius=0.06))
    els.append(image(M + 0.16, 2.72, 7.28, 3.00,
                     os.path.join(ROOT, "figures", "fig6_robustness.png")))

    els.append(rect(M + 7.92, 2.60, 3.81, 3.24, fill=CARD))
    els.append(text(M + 8.20, 2.78, 3.3, "DEGRADATION SWEEP", size=10, color=RED, bold=True))
    rows = [("clean", "48/48", GREEN), ("JPEG q40", "40/48", MUTED),
            ("blur r=1.0", "45/48", MUTED), ("blur r=2.0", "31/48", RED)]
    y = 3.12
    for a, b, col in rows:
        els.append(text(M + 8.20, y, 2.0, a, size=11, color=MUTED))
        els.append(text(M + 10.30, y, 1.1, b, size=11, color=col, bold=True, align="r"))
        y += 0.40
    els.append(text(M + 8.20, 5.02, 3.3,
                    "Fixed 200-pixel tiling mis-segments a degraded frame without raising an error.",
                    size=10.5, color=DIM, line_spacing=1.30))

    els.append(text(M, 5.96, 11.7,
                    "Gaussian blur is the dominant failure mode; recompression is comparatively "
                    "well tolerated. Because the failure is silent, input quality must be checked "
                    "before the decision is trusted.", size=11.8, color=MUTED, line_spacing=1.30))
    els.append(text(M, 6.52, 11.7,
                    "Implication: link quality and relay compression determine reliability, not "
                    "the defender's countermeasures.", size=12, color=INK, bold=True))
    return els


def slide_implications():
    els = header("10", "TACTICAL IMPLICATIONS",
                 "What the results mean operationally")
    items = [
        ("01", "A delay, not a capability",
         "At $2 per 1,000 items, human latency and 10% reliability, the commercial pipeline is "
         "confined to bulk collection. Millisecond automation changes the missions the capability "
         "supports, not only its unit cost."),
        ("02", "Dependency is the vulnerability",
         "Renting solvers discloses the target set to a third party. A locally hosted model does "
         "not. This is the more significant of the two gains."),
        ("03", "Confidence gating enables autonomy",
         "Because the margin is exported, the escalation rate is computable before deployment. A "
         "system that cannot abstain cannot be operated unattended."),
        ("04", "Labels, not capacity, are the constraint",
         "Missed detections are negligible. The effective counter is not a harder puzzle but one "
         "whose rendering changes faster than labels can be collected."),
    ]
    y = 2.52
    for num, head, body in items:
        els.append(text(M, y + 0.02, 0.55, num, size=12, color=ACCENT, bold=True, font="mono"))
        els.append(text(M + 0.62, y, 3.55, head, size=14, color=INK, bold=True))
        els.append(text(M + 4.30, y - 0.02, 7.45, body, size=11.5, color=MUTED, line_spacing=1.30))
        y += 1.14
        if num != "04":
            els.append(rule(M + 0.62, y - 0.20, 11.0, color=RULE, lw=0.8))
    return els


def slide_defence():
    els = header("11", "TECHNICAL DEFENCE",
                 "Anticipated questions")
    qa = [
        ("Why a detector rather than a classifier?",
         "Measured 73% \u2192 83% on identical data with less training data, attributed to a "
         "shared class vocabulary across two visual domains."),
        ("Why is the penalty asymmetric, if 1:1 also scores 48/48?",
         "Recall failures are unrecoverable; precision failures are noise. The ratio is not "
         "identifiable on a saturated set, and \u00a74.4 says so."),
        ("Why abstain rather than guess on a tie?",
         "A tie is a coin toss. A new challenge costs no attempt, so it weakly dominates."),
        ("Why report 100% rather than a range?",
         "The figure is measured against 48 hand-labelled answers with a Wilson interval and an "
         "error decomposition. The defensible claim is \u2265 92.6% at 95% confidence."),
    ]
    y = 2.44
    for q, a in qa:
        els.append(rect(M, y, 0.06, 0.86, fill=ACCENT, radius=0.02))
        els.append(text(M + 0.30, y - 0.02, 11.2, q, size=12.8, color=INK, bold=True))
        els.append(text(M + 0.30, y + 0.32, 11.2, a, size=11.2, color=MUTED, line_spacing=1.26))
        y += 1.03
    els.append(text(M, 6.62, 11.7, "Full derivations: docs/ALGORITHM.md  \u00b7  CS471_Final_Report.pdf",
                    size=9.5, color=DIM, font="mono"))
    return els


def header(num, eyebrow, title, accent=ACCENT):
    """Standard slide furniture: background, eyebrow, title, accent rule."""
    els = [rect(0, 0, W, H, fill=BG, radius=0)]
    els.append(text(M, 0.50, 1.2, num, size=11, color=DIM, bold=True, font="mono"))
    els.append(text(M + 0.56, 0.50, 8.0, eyebrow, size=10.5, color=accent, bold=True))
    n_lines = title.count("\n") + 1
    els.append(text(M, 0.80, 11.8, title, size=27, color=INK, bold=True, line_spacing=1.14))
    rule_y = 0.80 + n_lines * 0.46 + 0.10
    els.append(rule(M, rule_y, 1.05, color=accent, lw=2.6))
    return els


def footer(n):
    return [
        text(M, 7.06, 6.0, "CS471  \u00b7  Defeating Adversarial Visual Access Control",
             size=9, color=DIM),
        text(W - M - 0.7, 7.06, 0.7, str(n), size=9, color=DIM, align="r"),
    ]


def build_slides():
    slides = [
        slide_title(),
        slide_problem(),
        slide_multiset(),
        slide_algorithm(),
        slide_decisions(),
        slide_demo(),
        slide_baselines(),
        slide_perception(),
        slide_negative(),
        slide_failure(),
        slide_implications(),
        slide_defence(),
    ]
    # furniture on every slide after the title
    out = [slides[0]]
    for i, s in enumerate(slides[1:], start=2):
        out.append(s + footer(i))
    return out


# ============================================================ validation
def validate(slides):
    problems = []
    for si, els in enumerate(slides, 1):
        for e in els:
            if e["t"] in ("rect", "img"):
                if e["x"] < -0.01 or e["y"] < -0.01:
                    problems.append(f"slide {si}: {e['t']} starts off-slide at ({e['x']:.2f},{e['y']:.2f})")
                if e["x"] + e["w"] > W + 0.02 or e["y"] + e["h"] > H + 0.02:
                    problems.append(
                        f"slide {si}: {e['t']} overflows to "
                        f"({e['x']+e['w']:.2f},{e['y']+e['h']:.2f})")
            if e["t"] == "text" and e["x"] + e["w"] > W + 0.02:
                problems.append(f"slide {si}: text box overflows right edge")
    return problems


# ============================================================ PPTX renderer
def render_pptx(slides, path):
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Emu, Inches, Pt

    def rgb(h):
        return RGBColor.from_string(h)

    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    blank = prs.slide_layouts[6]

    for els in slides:
        s = prs.slides.add_slide(blank)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = rgb(BG)

        for e in els:
            t = e["t"]
            if t == "rect":
                shp = s.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE if e["radius"] else MSO_SHAPE.RECTANGLE,
                    Inches(e["x"]), Inches(e["y"]), Inches(e["w"]), Inches(e["h"]))
                if e["radius"]:
                    try:
                        shp.adjustments[0] = min(0.5, e["radius"] / max(0.01, min(e["w"], e["h"])))
                    except Exception:
                        pass
                shp.fill.solid()
                shp.fill.fore_color.rgb = rgb(e["fill"])
                if e["line"]:
                    shp.line.color.rgb = rgb(e["line"])
                    shp.line.width = Pt(e["lw"])
                else:
                    shp.line.fill.background()
                shp.shadow.inherit = False

            elif t == "rule":
                shp = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(e["x"]), Inches(e["y"]),
                                         Inches(e["w"]), Pt(e["lw"]))
                shp.fill.solid()
                shp.fill.fore_color.rgb = rgb(e["color"])
                shp.line.fill.background()
                shp.shadow.inherit = False

            elif t == "arrow":
                shp = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(e["x"]), Inches(e["y"]),
                                         Inches(e["w"]), Inches(e["h"]))
                shp.fill.solid()
                shp.fill.fore_color.rgb = rgb(e["color"])
                shp.line.fill.background()
                shp.shadow.inherit = False

            elif t == "badge":
                # Ticks and crosses are drawn as strokes rather than font glyphs,
                # because Segoe UI has no U+2713 / U+2717 and renders tofu boxes.
                shp = s.shapes.add_shape(
                    MSO_SHAPE.OVAL, Inches(e["x"]), Inches(e["y"]),
                    Inches(e["size"]), Inches(e["size"]))
                shp.fill.background()
                shp.line.color.rgb = rgb(e["color"])
                shp.line.width = Pt(1.4)
                shp.shadow.inherit = False
                cx = e["x"] + e["size"] / 2
                cy = e["y"] + e["size"] / 2
                r = e["size"] * 0.20
                if e["glyph"] == "tick":
                    pts = [(cx - r, cy + r * 0.05), (cx - r * 0.2, cy + r * 0.8),
                           (cx + r * 1.1, cy - r * 0.85)]
                    fb = s.shapes.build_freeform(Inches(pts[0][0]), Inches(pts[0][1]))
                    fb.add_line_segments([(Inches(px), Inches(py)) for px, py in pts[1:]],
                                         close=False)
                    mk = fb.convert_to_shape()
                    mk.fill.background()
                    mk.line.color.rgb = rgb(e["color"])
                    mk.line.width = Pt(1.8)
                    mk.shadow.inherit = False
                else:
                    for a, b in (((-r, -r), (r, r)), ((-r, r), (r, -r))):
                        ln = s.shapes.add_connector(
                            2, Inches(cx + a[0]), Inches(cy + a[1]),
                            Inches(cx + b[0]), Inches(cy + b[1]))
                        ln.line.color.rgb = rgb(e["color"])
                        ln.line.width = Pt(1.8)

            elif t == "img":
                if os.path.exists(e["path"]):
                    s.shapes.add_picture(e["path"], Inches(e["x"]), Inches(e["y"]),
                                         Inches(e["w"]), Inches(e["h"]))

            elif t == "text":
                box = s.shapes.add_textbox(Inches(e["x"]), Inches(e["y"]),
                                           Inches(e["w"]), Inches(0.30))
                tf = box.text_frame
                tf.word_wrap = True
                tf.margin_left = 0
                tf.margin_right = 0
                tf.margin_top = 0
                tf.margin_bottom = 0
                tf.vertical_anchor = MSO_ANCHOR.TOP
                for i, line in enumerate(e["s"].split("\n")):
                    para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    para.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER,
                                      "r": PP_ALIGN.RIGHT}[e["align"]]
                    para.line_spacing = e["ls"]
                    run = para.add_run()
                    run.text = line
                    f = run.font
                    f.size = Pt(e["size"])
                    f.bold = e["bold"]
                    f.italic = e["italic"]
                    f.name = "Consolas" if e["font"] == "mono" else "Segoe UI"
                    f.color.rgb = rgb(e["color"])

            elif t == "bullets":
                box = s.shapes.add_textbox(Inches(e["x"]), Inches(e["y"]),
                                           Inches(e["w"]), Inches(e["gap"] * len(e["items"])))
                tf = box.text_frame
                tf.word_wrap = True
                tf.margin_left = 0
                tf.margin_right = 0
                tf.margin_top = 0
                tf.margin_bottom = 0
                for i, item in enumerate(e["items"]):
                    para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    para.line_spacing = 1.26
                    para.space_after = Pt(6)
                    head, body = item if isinstance(item, tuple) else (None, item)
                    dash = para.add_run()
                    dash.text = "\u2014   "
                    dash.font.size = Pt(e["size"])
                    dash.font.name = "Segoe UI"
                    dash.font.bold = True
                    dash.font.color.rgb = rgb(e["mark"])
                    if head:
                        r1 = para.add_run()
                        r1.text = head + "  "
                        r1.font.size = Pt(e["size"])
                        r1.font.name = "Segoe UI"
                        r1.font.bold = True
                        r1.font.color.rgb = rgb(e["color"])
                    r2 = para.add_run()
                    r2.text = body
                    r2.font.size = Pt(e["size"])
                    r2.font.name = "Segoe UI"
                    r2.font.color.rgb = rgb("A9B4C7" if head else e["color"])

    prs.save(path)
    return path


# ============================================================ PNG renderer
def _font(path, size_pt):
    return ImageFont.truetype(path, max(1, int(round(size_pt * DPI / 72))))


def _px(v):
    return int(round(v * DPI))


def _wrap(draw, s, font, max_px):
    out = []
    for block in s.split("\n"):
        if not block:
            out.append("")
            continue
        words, line = block.split(" "), ""
        for w in words:
            trial = (line + " " + w).strip()
            if draw.textlength(trial, font=font) <= max_px or not line:
                line = trial
            else:
                out.append(line)
                line = w
        out.append(line)
    return out


def render_preview(slides, outdir):
    os.makedirs(outdir, exist_ok=True)
    paths = []
    for si, els in enumerate(slides, 1):
        img = Image.new("RGB", (_px(W), _px(H)), "#" + BG)
        d = ImageDraw.Draw(img)

        for e in els:
            t = e["t"]
            if t == "rect":
                box = [_px(e["x"]), _px(e["y"]), _px(e["x"] + e["w"]), _px(e["y"] + e["h"])]
                r = _px(min(e["radius"], min(e["w"], e["h"]) / 2)) if e["radius"] else 0
                if r > 1:
                    d.rounded_rectangle(box, radius=r, fill="#" + e["fill"],
                                        outline=("#" + e["line"]) if e["line"] else None,
                                        width=max(1, int(e["lw"])))
                else:
                    d.rectangle(box, fill="#" + e["fill"],
                                outline=("#" + e["line"]) if e["line"] else None,
                                width=max(1, int(e["lw"])))

            elif t == "rule":
                d.rectangle([_px(e["x"]), _px(e["y"]),
                             _px(e["x"] + e["w"]), _px(e["y"]) + max(1, int(e["lw"]))],
                            fill="#" + e["color"])

            elif t == "arrow":
                x0, y0 = _px(e["x"]), _px(e["y"])
                x1, y1 = _px(e["x"] + e["w"]), _px(e["y"] + e["h"])
                mid = (y0 + y1) // 2
                head = (x1 - x0) * 0.45
                d.polygon([(x0, mid - (y1 - y0) // 3), (x1 - head, mid - (y1 - y0) // 3),
                           (x1 - head, y0), (x1, mid), (x1 - head, y1),
                           (x1 - head, mid + (y1 - y0) // 3), (x0, mid + (y1 - y0) // 3)],
                          fill="#" + e["color"])

            elif t == "badge":
                x0, y0 = _px(e["x"]), _px(e["y"])
                sz = _px(e["size"])
                cx, cy = x0 + sz // 2, y0 + sz // 2
                r = sz * 0.20
                wd = max(2, sz // 12)
                d.ellipse([x0, y0, x0 + sz, y0 + sz], outline="#" + e["color"], width=wd)
                if e["glyph"] == "tick":
                    d.line([(cx - r, cy + r * 0.05), (cx - r * 0.2, cy + r * 0.8),
                            (cx + r * 1.1, cy - r * 0.85)],
                           fill="#" + e["color"], width=wd, joint="curve")
                else:
                    d.line([(cx - r, cy - r), (cx + r, cy + r)],
                           fill="#" + e["color"], width=wd)
                    d.line([(cx - r, cy + r), (cx + r, cy - r)],
                           fill="#" + e["color"], width=wd)

            elif t == "img":
                if os.path.exists(e["path"]):
                    sub = Image.open(e["path"]).convert("RGB")
                    sub = sub.resize((_px(e["w"]), _px(e["h"])), Image.LANCZOS)
                    img.paste(sub, (_px(e["x"]), _px(e["y"])))

            elif t == "text":
                fp = FONT_MONO if e["font"] == "mono" else (
                    FONT_BOLD if e["bold"] else (FONT_SEMI if e["size"] > 20 else FONT_SANS))
                f = _font(fp, e["size"])
                maxw = _px(e["w"])
                y = _px(e["y"])
                lead = int(e["size"] * DPI / 72 * e["ls"])
                for line in _wrap(d, e["s"], f, maxw):
                    if e["align"] == "c":
                        d.text((_px(e["x"]) + maxw // 2, y), line, font=f,
                               fill="#" + e["color"], anchor="ma")
                    elif e["align"] == "r":
                        d.text((_px(e["x"] + e["w"]), y), line, font=f,
                               fill="#" + e["color"], anchor="ra")
                    else:
                        d.text((_px(e["x"]), y), line, font=f, fill="#" + e["color"])
                    y += lead

            elif t == "bullets":
                f = _font(FONT_SANS, e["size"])
                fb = _font(FONT_BOLD, e["size"])
                y = _px(e["y"])
                for item in e["items"]:
                    head, body = item if isinstance(item, tuple) else (None, item)
                    d.text((_px(e["x"]), y), "\u2014", font=fb, fill="#" + e["mark"])
                    cur = _px(e["x"]) + int(0.34 * DPI)
                    if head:
                        d.text((cur, y), head, font=fb, fill="#" + e["color"])
                        cur += int(d.textlength(head + "  ", font=fb))
                    words = body.split(" ")
                    line, lines = "", []
                    avail = _px(e["x"] + e["w"]) - cur
                    first = True
                    for w in words:
                        trial = (line + " " + w).strip()
                        lim = avail if first else _px(e["w"]) - int(0.34 * DPI)
                        if d.textlength(trial, font=f) <= lim or not line:
                            line = trial
                        else:
                            lines.append(line)
                            line = w
                            first = False
                    lines.append(line)
                    for i, ln in enumerate(lines):
                        x = cur if i == 0 else _px(e["x"]) + int(0.34 * DPI)
                        d.text((x, y), ln, font=f, fill="#" + ("A9B4C7" if head else e["color"]))
                        y += int(e["size"] * DPI / 72 * 1.26)
                    y += _px(0.06)

        p = os.path.join(outdir, f"p{si:02d}.png")
        img.save(p)
        paths.append(p)
    return paths


# ============================================================ main
def main():
    slides = build_slides()
    probs = validate(slides)
    if probs:
        print("LAYOUT PROBLEMS:")
        for p in probs:
            print("  " + p)
        sys.exit(1)

    render_pptx(slides, OUT_PPTX)
    print(f"wrote {OUT_PPTX}  ({len(slides)} slides)")
    paths = render_preview(slides, PREVIEW)
    print(f"wrote {len(paths)} previews to {PREVIEW}")


if __name__ == "__main__":
    main()
