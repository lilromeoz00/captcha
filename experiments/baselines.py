"""Baselines -- the "simpler or established approach" this agent must beat.

Each baseline is a complete, honest attempt at the same task. They are ordered
from least to most informed, so the gap between adjacent rows attributes credit
to a specific design decision rather than to "deep learning" in general.

    random            no information at all
    hist_match        classical CV: histogram distance, no learning
    yolo_count        the same detector, but a naive decision rule
    yolo_symmetric    the same detector and the same scoring form, but the
                      penalty is symmetric (1:1) instead of asymmetric (10:1)
    yolo_asym_10to1   the submitted agent

Nothing here is a strawman. `hist_match` is what a competent engineer without a
labelled dataset would actually build first, and `yolo_count` is what you get if
you train the detector and then reach for the obvious heuristic.
"""

from __future__ import annotations

import collections
import math
import random
from typing import Dict, List, Mapping, Sequence

import numpy as np

from solver import geometry, multiset

# --------------------------------------------------------------------------
# 1. Random
# --------------------------------------------------------------------------


def random_baseline(strips: Sequence[str], truth: Mapping[str, int], trials: int = 1000):
    """Uniform over the eight baskets.

    Averaged over many trials rather than run once: a single draw from a
    binomial(48, 0.125) has a standard deviation of ~2.3 items, so one sample can
    read anywhere from 6% to 25% and is not a usable floor. The mean over 1000
    trials estimates the expectation, 1/8 = 12.5%.
    """
    ids = [s for s in strips if s in truth]
    n = len(ids)
    if n == 0:
        return {"right": 0, "n": 0, "accuracy": 0.0, "expected": 0.125}
    rng = random.Random(0)
    per_trial = [sum(rng.randrange(8) == truth[s] for s in ids) for _ in range(trials)]
    mean_right = sum(per_trial) / trials
    return {
        "right": round(mean_right, 3),
        "n": n,
        "accuracy": mean_right / n,
        "expected": 0.125,
        "trials": trials,
        "sd": float(np.std(per_trial)),
    }


def majority_baseline(strips: Sequence[str], truth: Mapping[str, int]):
    """Always answer basket 0 -- the floor any real system must clear."""
    n = sum(1 for s in strips if s in truth)
    right = sum(truth[s] == 0 for s in strips if s in truth)
    return {"right": right, "n": n, "accuracy": right / n if n else 0.0}


# --------------------------------------------------------------------------
# 2. Classical CV: histogram matching, no learning, no labels
# --------------------------------------------------------------------------

_HIST_BINS = 32
_EDGE_BINS = 8


def _tile_descriptor(tile) -> np.ndarray:
    """Intensity histogram + gradient-orientation histogram.

    Deliberately classical: no training, no labels, no parameters fitted to the
    data. Both halves are normalised so the descriptor is invariant to how many
    pixels are foreground.

    The intensity half captures "how much dark/light stuff is there"; the
    orientation half captures "what shapes are there". Together they are the
    standard pre-deep-learning recipe for texture/shape retrieval.
    """
    g = np.asarray(tile.convert("L").resize((100, 100)), dtype=np.float32)

    hist, _ = np.histogram(g, bins=_HIST_BINS, range=(0, 256))
    hist = hist.astype(np.float32)
    hist /= max(1.0, hist.sum())

    gy, gx = np.gradient(g)
    mag = np.hypot(gx, gy)
    ang = (np.arctan2(gy, gx) + math.pi) % (2 * math.pi)  # [0, 2pi)
    ohist, _ = np.histogram(ang, bins=_EDGE_BINS, range=(0, 2 * math.pi), weights=mag)
    ohist = ohist.astype(np.float32)
    ohist /= max(1e-6, ohist.sum())

    return np.concatenate([hist, ohist])


def _chi2(a: np.ndarray, b: np.ndarray) -> float:
    """Chi-square distance between two normalised histograms."""
    d = (a - b) ** 2
    s = a + b
    return float(np.sum(np.divide(d, s, out=np.zeros_like(d), where=s > 0)))


def hist_match_baseline(strips: Mapping[str, str], truth: Mapping[str, int]):
    """Pick the basket whose descriptor is closest to the key's descriptor.

    This is the honest no-ML approach, and it should fail for a reason worth
    reporting: the key is a *grayscale silhouette* and the baskets are *colour
    photographs of the same objects in different arrangements*, so a global
    descriptor cannot see object identity or, crucially, **count**.
    """
    rows = []
    for sid, path in strips.items():
        if sid not in truth:
            continue
        from PIL import Image

        with Image.open(path) as im:
            tiles = geometry.slice_strip(im.convert("RGB"))
        key = _tile_descriptor(tiles[geometry.KEY_ID])
        dists = {
            cid: _chi2(key, _tile_descriptor(tiles[cid]))
            for cid in geometry.cell_ids()
            if cid != geometry.KEY_ID
        }
        pick = min(dists, key=dists.get)  # closest descriptor wins
        rows.append(
            {
                "strip": sid,
                "pred": int(pick),
                "truth": truth[sid],
                "ok": int(pick) == truth[sid],
            }
        )
    right = sum(r["ok"] for r in rows)
    return {
        "right": right,
        "n": len(rows),
        "accuracy": right / len(rows) if rows else 0.0,
        "rows": rows,
    }


# --------------------------------------------------------------------------
# 3. Same detector, naive decisions
# --------------------------------------------------------------------------


def yolo_count_baseline(
    detections: Mapping[str, List[List[tuple]]],
    truth: Mapping[str, int],
):
    """Pick the basket containing the most detected objects.

    The obvious heuristic after training a detector, and the one a team without
    the matching layer would ship. It ignores the key entirely, which is exactly
    the information the task is built on.
    """
    rows = []
    for sid, per_tile in detections.items():
        if sid not in truth:
            continue
        counts = [len(per_tile[i]) for i in range(8)]
        pick = int(np.argmax(counts))
        rows.append(
            {"strip": sid, "pred": pick, "truth": truth[sid], "ok": pick == truth[sid]}
        )
    right = sum(r["ok"] for r in rows)
    return {
        "right": right,
        "n": len(rows),
        "accuracy": right / len(rows) if rows else 0.0,
        "rows": rows,
    }


def yolo_confidence_baseline(
    detections: Mapping[str, List[List[tuple]]],
    truth: Mapping[str, int],
):
    """Pick the basket with the highest total detection confidence."""
    rows = []
    for sid, per_tile in detections.items():
        if sid not in truth:
            continue
        conf = [sum(c for _cls, c in per_tile[i]) for i in range(8)]
        pick = int(np.argmax(conf))
        rows.append(
            {"strip": sid, "pred": pick, "truth": truth[sid], "ok": pick == truth[sid]}
        )
    right = sum(r["ok"] for r in rows)
    return {
        "right": right,
        "n": len(rows),
        "accuracy": right / len(rows) if rows else 0.0,
        "rows": rows,
    }


def yolo_symmetric_baseline(
    detections: Mapping[str, List[List[tuple]]],
    truth: Mapping[str, int],
    key_max: int = 4,
):
    """The full pipeline, but with a symmetric penalty (1 miss == 1 surplus).

    This isolates the contribution of the 10:1 asymmetry from the contribution
    of the matching layer as a whole.
    """
    rows = []
    for sid, per_tile in detections.items():
        if sid not in truth:
            continue
        key = dict(multiset.as_multiset(c for c, _ in per_tile[8][:key_max]))
        baskets = {
            str(i): dict(multiset.as_multiset(c for c, _ in per_tile[i])) for i in range(8)
        }
        scored = sorted(
            ((multiset.match(key, baskets[c], 1, 1).score, c) for c in baskets),
            key=lambda t: (-t[0], t[1]),
        )
        margin = scored[0][0] - scored[1][0]
        pick = None if margin == 0 else int(scored[0][1])
        rows.append(
            {
                "strip": sid,
                "pred": pick,
                "truth": truth[sid],
                "ok": pick == truth[sid],
                "margin": margin,
            }
        )
    right = sum(r["ok"] for r in rows)
    return {
        "right": right,
        "n": len(rows),
        "accuracy": right / len(rows) if rows else 0.0,
        "rows": rows,
    }


def yolo_asym_baseline(
    detections: Mapping[str, List[List[tuple]]],
    truth: Mapping[str, int],
    key_max: int = 4,
):
    """The submitted agent, run on cached detections (should reproduce 100%)."""
    rows = []
    for sid, per_tile in detections.items():
        if sid not in truth:
            continue
        key = dict(multiset.as_multiset(c for c, _ in per_tile[8][:key_max]))
        baskets = {
            str(i): dict(multiset.as_multiset(c for c, _ in per_tile[i])) for i in range(8)
        }
        scored = sorted(
            ((multiset.match(key, baskets[c]).score, c) for c in baskets),
            key=lambda t: (-t[0], t[1]),
        )
        margin = scored[0][0] - scored[1][0]
        pick = None if margin == 0 else int(scored[0][1])
        rows.append(
            {
                "strip": sid,
                "pred": pick,
                "truth": truth[sid],
                "ok": pick == truth[sid],
                "margin": margin,
            }
        )
    right = sum(r["ok"] for r in rows)
    return {
        "right": right,
        "n": len(rows),
        "accuracy": right / len(rows) if rows else 0.0,
        "rows": rows,
    }


# --------------------------------------------------------------------------
# Statistical comparison
# --------------------------------------------------------------------------


def mcnemar_exact(a_rows, b_rows):
    """Exact McNemar test between two systems scored on the same items.

    Returns (b_only, a_only, p). `b_only` = items only B got right; `a_only` =
    items only A got right. This is the correct paired test here -- comparing two
    accuracies measured on the same 48 strips -- and unlike a two-proportion test
    it does not ignore that the samples are paired.
    """
    a = {r["strip"]: r["ok"] for r in a_rows}
    b = {r["strip"]: r["ok"] for r in b_rows}
    common = set(a) & set(b)
    b_only = sum(1 for s in common if b[s] and not a[s])
    a_only = sum(1 for s in common if a[s] and not b[s])
    n = b_only + a_only
    if n == 0:
        return b_only, a_only, 1.0
    # exact two-sided binomial, p = 0.5
    k = min(b_only, a_only)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return b_only, a_only, min(1.0, 2 * tail)
