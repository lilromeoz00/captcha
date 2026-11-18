"""Render every figure in the final report from results/experiments.json.

    python experiments/figures.py

Figures are written to figures/ as 200-dpi PNGs. Nothing is drawn by hand: every
value comes from the JSON the experiments wrote, so the report cannot drift out
of sync with the measurements.
"""

from __future__ import annotations

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
FIG = os.path.join(ROOT, "figures")
RES = os.path.join(ROOT, "results", "experiments.json")

# Report-appropriate styling: serif text, no chartjunk, readable at print size.
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["DejaVu Serif", "Times New Roman"],
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.5,
        "figure.dpi": 200,
        "savefig.bbox": "tight",
    }
)

INK = "#1a1a1a"
ACCENT = "#1f6feb"
MUTED = "#9aa0a6"
WARN = "#c1440e"


def _save(fig, name):
    path = os.path.join(FIG, name)
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print(f"  wrote {name}")
    return path


# --------------------------------------------------------------------------


def fig_baselines(d):
    b = d["baselines"]
    order = [
        ("random", "Random\n(1/8 floor)"),
        ("majority", "Always\nbasket 0"),
        ("hist_match", "Classical CV\nhistogram"),
        ("yolo_count", "YOLO +\nmost objects"),
        ("yolo_confidence", "YOLO +\nmax confidence"),
        ("yolo_symmetric_1to1", "Full agent\nsymmetric 1:1"),
        ("yolo_asym_10to1", "Full agent\nSUBMITTED"),
    ]
    labels, accs, los, his, colours = [], [], [], [], []
    for key, lab in order:
        r = b[key]
        labels.append(lab)
        accs.append(r["accuracy"] * 100)
        los.append(max(0.0, (r["accuracy"] - r.get("wilson_lo", r["accuracy"])) * 100))
        his.append(max(0.0, (r.get("wilson_hi", r["accuracy"]) - r["accuracy"]) * 100))
        colours.append(ACCENT if key == "yolo_asym_10to1" else MUTED)

    fig, ax = plt.subplots(figsize=(6.6, 3.1))
    x = np.arange(len(labels))
    bars = ax.bar(x, accs, color=colours, width=0.66, edgecolor=INK, linewidth=0.6)
    ax.errorbar(
        x, accs, yerr=[los, his], fmt="none", ecolor=INK, elinewidth=0.9, capsize=2.5
    )
    for xi, a in zip(x, accs):
        ax.text(xi, a + 4.5, f"{a:.1f}%", ha="center", va="bottom", fontsize=7.6)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6.9)
    ax.set_ylabel("task accuracy (%)")
    ax.set_ylim(0, 120)
    ax.axhline(12.5, color=WARN, lw=0.8, ls="--")
    ax.annotate(
        "chance = 12.5%",
        xy=(0.02, 12.5),
        xycoords=("axes fraction", "data"),
        xytext=(0.02, 30),
        textcoords=("axes fraction", "data"),
        color=WARN,
        fontsize=6.8,
        arrowprops=dict(arrowstyle="->", lw=0.6, color=WARN),
    )
    ax.set_title("Baseline comparison on 48 hand-labelled challenges (95% Wilson CI)")
    fig.tight_layout()
    return _save(fig, "fig1_baselines.png")


def fig_convergence(d):
    c = d.get("convergence")
    if not c:
        return None
    rows = c["rows"]
    ep = [r["epoch"] for r in rows]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.8, 2.6))

    a1.plot(ep, [r["box_loss"] for r in rows], color=ACCENT, lw=1.1, label="train box loss")
    a1.plot(ep, [r["val_box_loss"] for r in rows], color=WARN, lw=1.1, label="val box loss")
    a1.plot(ep, [r["cls_loss"] for r in rows], color=MUTED, lw=1.0, ls="--", label="train cls loss")
    a1.set_xlabel("epoch")
    a1.set_ylabel("loss")
    a1.set_yscale("log")
    a1.legend(frameon=False, fontsize=7)
    a1.set_title("Training / validation loss")

    a2.plot(ep, [r["map50"] for r in rows], color=ACCENT, lw=1.2, label="mAP50")
    a2.plot(ep, [r["map50_95"] for r in rows], color=WARN, lw=1.2, label="mAP50-95")
    a2.plot(ep, [r["precision"] for r in rows], color=MUTED, lw=0.9, ls=":", label="precision")
    a2.plot(ep, [r["recall"] for r in rows], color=MUTED, lw=0.9, ls="-.", label="recall")
    best = c["best"]
    a2.axvline(best["epoch"], color=INK, lw=0.7, ls="--")
    a2.annotate(
        f"best mAP50-95 {best['map50_95']:.3f}\n@ epoch {best['epoch']}",
        xy=(best["epoch"], best["map50_95"]),
        xytext=(best["epoch"] - 62, 0.42),
        fontsize=7,
        arrowprops=dict(arrowstyle="->", lw=0.7, color=INK),
    )
    a2.set_xlabel("epoch")
    a2.set_ylabel("metric")
    a2.set_ylim(0, 1.02)
    a2.legend(frameon=False, fontsize=7, loc="lower right")
    a2.set_title(f"Validation metrics ({c['n_epochs']} epochs)")
    fig.tight_layout()
    return _save(fig, "fig2_convergence.png")


def fig_pr(d):
    det = d["detection"]
    curves = det.get("_curves") or {}
    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    cmap = plt.get_cmap("tab10")
    for i, (cls, (rec, prec)) in enumerate(curves.items()):
        if not rec:
            continue
        ap = det["per_class"][cls]["ap50"]
        ax.plot(rec, prec, lw=1.0, color=cmap(i % 10), label=f"{cls} ({ap:.3f})")
    ax.set_xlabel("recall")
    ax.set_ylabel("precision")
    ax.set_xlim(0, 1.01)
    ax.set_ylim(0, 1.05)
    ax.set_title(f"Per-class PR, IoU 0.5 (mAP50 = {det['map50']:.3f})", fontsize=8.5)
    ax.legend(frameon=False, fontsize=5.6, loc="lower left", ncol=1)
    return _save(fig, "fig3_pr_curves.png")


def fig_confusion(d):
    from solver.multiset import CLASSES

    m = np.array(d["detection"]["confusion"], dtype=float)
    # normalise by truth row so each row sums to 1 (recall per class)
    row = m.sum(axis=1, keepdims=True)
    mn = np.divide(m, row, out=np.zeros_like(m), where=row > 0)

    labels = list(CLASSES) + ["background"]
    fig, ax = plt.subplots(figsize=(4.6, 4.0))
    im = ax.imshow(mn, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=55, ha="right", fontsize=6.5)
    ax.set_yticklabels(labels, fontsize=6.5)
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    ax.grid(False)
    for i in range(len(labels)):
        for j in range(len(labels)):
            if mn[i, j] >= 0.01:
                ax.text(
                    j, i, f"{mn[i, j]*100:.0f}",
                    ha="center", va="center", fontsize=5.6,
                    color="white" if mn[i, j] > 0.55 else INK,
                )
    ax.set_title("Confusion matrix (% of true class), IoU 0.5", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
    return _save(fig, "fig4_confusion.png")


def fig_calibration(d):
    cal = d["detection"]["calibration"]
    bins = [b for b in cal["bins"] if b["n"] > 0]
    fig, ax = plt.subplots(figsize=(3.4, 3.0))
    ax.plot([0, 1], [0, 1], color=MUTED, lw=0.8, ls="--", label="perfect calibration")
    xs = [b["confidence"] for b in bins]
    ys = [b["accuracy"] for b in bins]
    ns = [b["n"] for b in bins]
    ax.plot(xs, ys, "o-", color=ACCENT, lw=1.1, ms=3.5, label="measured")
    for x, y, n in zip(xs, ys, ns):
        ax.annotate(f"n={n}", (x, y), textcoords="offset points", xytext=(3, -9), fontsize=5.8)
    ax.set_xlabel("predicted confidence")
    ax.set_ylabel("observed accuracy")
    ax.set_xlim(0.3, 1.02)
    ax.set_ylim(0, 1.05)
    ax.set_title(f"Reliability diagram (ECE = {cal['ece']:.3f})", fontsize=8.5)
    ax.legend(frameon=False, fontsize=6.5, loc="upper left")
    return _save(fig, "fig5_calibration.png")


def fig_robustness(d):
    rob = d.get("robustness") or []
    if not rob:
        return None
    groups = {"jpeg": [], "blur": [], "scale": []}
    for r in rob:
        if r["kind"] in groups:
            groups[r["kind"]].append(r)

    fig, axes = plt.subplots(1, 3, figsize=(6.8, 2.3), sharey=True)
    titles = {
        "jpeg": "JPEG recompression",
        "blur": "Gaussian blur (radius px)",
        "scale": "Downscale then restore",
    }
    xlabels = {"jpeg": "quality", "blur": "radius", "scale": "scale factor"}
    for ax, kind in zip(axes, ["jpeg", "blur", "scale"]):
        g = groups[kind]
        if not g:
            continue
        xs = [r["level"] for r in g]
        ys = [r["accuracy"] * 100 for r in g]
        ax.plot(xs, ys, "o-", color=ACCENT, lw=1.2, ms=4)
        for i, (x, y, r) in enumerate(zip(xs, ys, g)):
            if kind == "jpeg":
                dy = -13 if i == 0 else 7
            elif kind == "blur":
                dy = 7 if i < 2 else -13
            else:
                dy = 7 if i == 0 else -13
            ax.annotate(f"{r['right']}/{r['n']}", (x, y), textcoords="offset points",
                        xytext=(0, dy), fontsize=5.8, ha="center")
        ax.set_xlabel(xlabels[kind])
        ax.set_title(titles[kind], fontsize=8.5)
        ax.set_ylim(55, 110)
        if kind == "jpeg":
            ax.invert_xaxis()
        if kind == "scale":
            ax.set_xlim(0.4, 0.85)
    axes[0].set_ylabel("accuracy (%)")
    fig.suptitle("Robustness to sensor/transport degradation (48 strips)", fontsize=9, y=1.02)
    fig.tight_layout()
    return _save(fig, "fig6_robustness.png")


def fig_confidence_sweep(d):
    sw = d.get("confidence_sweep") or []
    if not sw:
        return None
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    xs = [r["conf"] for r in sw]
    ys = [r["accuracy"] * 100 for r in sw]
    ax.plot(xs, ys, "o-", color=ACCENT, lw=1.2, ms=4)
    best = max(sw, key=lambda r: r["accuracy"])
    ax.plot([best["conf"]], [best["accuracy"] * 100], "o", ms=8, mfc="none", mec=WARN, mew=1.3)
    ax.annotate(
        f"chosen: {best['conf']:.2f}",
        xy=(best["conf"], best["accuracy"] * 100),
        xytext=(best["conf"] + 0.04, best["accuracy"] * 100 - 4.2),
        fontsize=7,
        arrowprops=dict(arrowstyle="->", lw=0.7, color=WARN),
        color=WARN,
    )
    ax.set_xlabel("detection confidence floor")
    ax.set_ylabel("task accuracy (%)")
    ax.set_ylim(91, 101.5)
    ax.set_title("Confidence-floor sweep", fontsize=8.5)
    return _save(fig, "fig7_confidence_sweep.png")


def fig_penalty_sweep(d):
    sw = d.get("penalty_sweep") or []
    if not sw:
        return None
    fig, ax = plt.subplots(figsize=(3.4, 2.2))
    xs = [r["alpha"] for r in sw]
    ys = [r["accuracy"] * 100 for r in sw]
    ax.plot(xs, ys, "o-", color=ACCENT, lw=1.2, ms=4)
    ax.set_xscale("log")
    ax.set_xlabel(r"miss penalty $\alpha$ (surplus $\beta=1$)")
    ax.set_ylabel("task accuracy (%)")
    ax.set_ylim(88, 102)
    ax.set_title("Penalty ratio is NOT identifiable here", fontsize=8.5, color=WARN)
    ax.text(
        0.5, 0.06,
        "flat across 1:1 - 50:1: the 48-strip set saturates",
        transform=ax.transAxes, ha="center", fontsize=6.4, color=WARN,
    )
    return _save(fig, "fig8_penalty_sweep.png")


def fig_ceiling(d):
    a = d["agent"]
    fig, ax = plt.subplots(figsize=(3.2, 2.3))
    vals = [a["ceiling_rate"] * 100, a["exploit_rate"] * 100]
    labs = ["strips where an\nexact match existed", "of those, picked\nby the ranker"]
    bars = ax.bar(labs, vals, color=[MUTED, ACCENT], width=0.55, edgecolor=INK, linewidth=0.6)
    for b, v, extra in zip(bars, vals, [f"{a['ceiling_n']}/{a['n']}", f"{a['exploited']}/{a['ceiling_n']}"]):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.1f}%\n({extra})",
                ha="center", va="bottom", fontsize=7)
    ax.set_ylim(0, 122)
    ax.set_ylabel("%")
    ax.set_title("Oracle ceiling decomposition", fontsize=8.5)
    return _save(fig, "fig9_ceiling.png")


def main():
    os.makedirs(FIG, exist_ok=True)
    with open(RES, encoding="utf-8") as fh:
        d = json.load(fh)
    print("rendering figures ->", FIG)
    made = []
    for fn in (
        fig_baselines,
        fig_convergence,
        fig_pr,
        fig_confusion,
        fig_calibration,
        fig_robustness,
        fig_confidence_sweep,
        fig_penalty_sweep,
        fig_ceiling,
    ):
        p = fn(d)
        if p:
            made.append(p)
    print(f"{len(made)} figures written")


if __name__ == "__main__":
    main()
