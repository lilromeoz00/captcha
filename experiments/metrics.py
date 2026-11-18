"""Detection metrics: per-class precision/recall/F1/AP, confusion matrix, calibration.

Computed against human YOLO-format labels on the 288 held-out validation tiles.
Everything here is implemented directly rather than taken from Ultralytics' val
harness, for two reasons: the numbers must match the *shipped* pipeline exactly
(same tile size, same confidence floor, same class vocabulary), and the matching
rule has to be visible and testable.

Matching rule: greedy, descending confidence, one-to-one, IoU >= 0.5. Greedy
matching is what the PASCAL/mAP convention specifies; it is not optimal, which is
why AP is reported with the standard all-point interpolation rather than claimed
to be an upper bound.
"""

from __future__ import annotations

import collections
import glob
import os
from typing import Dict, List, Sequence, Tuple

import numpy as np

from solver.multiset import CLASSES

IOU_MATCH = 0.5


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------


def iou(a: Sequence[float], b: Sequence[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    ua = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / ua if ua > 0 else 0.0


# --------------------------------------------------------------------------
# Ground truth
# --------------------------------------------------------------------------


def load_gt(label_path: str, size: Tuple[int, int]) -> List[dict]:
    """Read YOLO normalised labels into pixel boxes."""
    w, h = size
    out = []
    if not os.path.exists(label_path):
        return out
    with open(label_path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) < 5:
                continue
            ci = int(parts[0])
            cx, cy, bw, bh = (float(v) for v in parts[1:5])
            out.append(
                {
                    "cls": CLASSES[ci],
                    "cls_id": ci,
                    "box": (
                        (cx - bw / 2) * w,
                        (cy - bh / 2) * h,
                        (cx + bw / 2) * w,
                        (cy + bh / 2) * h,
                    ),
                }
            )
    return out


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------


def match_tile(preds: List[dict], gts: List[dict], iou_thr: float = IOU_MATCH):
    """Greedy one-to-one matching, highest confidence first.

    Returns (matched_pairs, unmatched_pred_indices, unmatched_gt_indices) where
    matched_pairs are (pred_idx, gt_idx).
    """
    used_gt = set()
    pairs, fp = [], []
    for pi, p in enumerate(preds):
        best_gi, best_iou = -1, 0.0
        for gi, g in enumerate(gts):
            if gi in used_gt:
                continue
            v = iou(p["box"], g["box"])
            if v > best_iou:
                best_gi, best_iou = gi, v
        if best_gi >= 0 and best_iou >= iou_thr:
            used_gt.add(best_gi)
            pairs.append((pi, best_gi))
        else:
            fp.append(pi)
    fn = [gi for gi in range(len(gts)) if gi not in used_gt]
    return pairs, fp, fn


# --------------------------------------------------------------------------
# Per-class metrics
# --------------------------------------------------------------------------


def per_class_prf(tiles_pred: List[List[dict]], tiles_gt: List[List[dict]]) -> Dict[str, dict]:
    """Precision / recall / F1 per class at the configured confidence floor."""
    tp = collections.Counter()
    fp = collections.Counter()
    fn = collections.Counter()

    for preds, gts in zip(tiles_pred, tiles_gt):
        pairs, fpi, fni = match_tile(preds, gts)
        for pi, gi in pairs:
            if preds[pi]["cls"] == gts[gi]["cls"]:
                tp[preds[pi]["cls"]] += 1
            else:
                # right place, wrong name: a false positive AND a false negative
                fp[preds[pi]["cls"]] += 1
                fn[gts[gi]["cls"]] += 1
        for pi in fpi:
            fp[preds[pi]["cls"]] += 1
        for gi in fni:
            fn[gts[gi]["cls"]] += 1

    out = {}
    for c in CLASSES:
        t, p, n = tp[c], fp[c], fn[c]
        prec = t / (t + p) if (t + p) else 0.0
        rec = t / (t + n) if (t + n) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        out[c] = {
            "tp": t,
            "fp": p,
            "fn": n,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "n_gt": t + n,
        }
    return out


def average_precision(
    tiles_pred: List[List[dict]], tiles_gt: List[List[dict]], cls: str
) -> float:
    """AP for one class, all-point interpolation, IoU 0.5.

    Detections from ALL tiles are pooled and ranked by confidence, which is the
    correct construction -- per-tile AP would reward the model for the fact that
    each tile contains only a handful of objects.
    """
    n_gt = sum(1 for gts in tiles_gt for g in gts if g["cls"] == cls)
    if n_gt == 0:
        return float("nan")

    scored = []  # (conf, is_tp)
    for preds, gts in zip(tiles_pred, tiles_gt):
        cls_preds = [p for p in preds if p["cls"] == cls]
        cls_gts = [g for g in gts if g["cls"] == cls]
        pairs, fpi, _ = match_tile(cls_preds, cls_gts)
        tp_idx = {pi for pi, _gi in pairs}
        for pi, p in enumerate(cls_preds):
            scored.append((p["conf"], pi in tp_idx))

    scored.sort(key=lambda t: -t[0])
    if not scored:
        return 0.0

    tp_cum = np.cumsum([1 if t else 0 for _c, t in scored])
    fp_cum = np.cumsum([0 if t else 1 for _c, t in scored])
    recall = tp_cum / n_gt
    precision = tp_cum / np.maximum(tp_cum + fp_cum, 1)

    # all-point interpolation: precision envelope, then integrate over recall
    mrec = np.concatenate([[0.0], recall, [1.0]])
    mpre = np.concatenate([[0.0], precision, [0.0]])
    for i in range(len(mpre) - 2, -1, -1):
        mpre[i] = max(mpre[i], mpre[i + 1])
    idx = np.where(mrec[1:] != mrec[:-1])[0]
    return float(np.sum((mrec[idx + 1] - mrec[idx]) * mpre[idx + 1]))


def pr_curve(
    tiles_pred: List[List[dict]], tiles_gt: List[List[dict]], cls: str
) -> Tuple[List[float], List[float]]:
    """Recall/precision arrays for plotting one class's PR curve."""
    n_gt = sum(1 for gts in tiles_gt for g in gts if g["cls"] == cls)
    if n_gt == 0:
        return [], []
    scored = []
    for preds, gts in zip(tiles_pred, tiles_gt):
        cls_preds = [p for p in preds if p["cls"] == cls]
        cls_gts = [g for g in gts if g["cls"] == cls]
        pairs, _fpi, _ = match_tile(cls_preds, cls_gts)
        tp_idx = {pi for pi, _gi in pairs}
        for pi, p in enumerate(cls_preds):
            scored.append((p["conf"], pi in tp_idx))
    scored.sort(key=lambda t: -t[0])
    if not scored:
        return [], []
    tp_cum = np.cumsum([1 if t else 0 for _c, t in scored])
    fp_cum = np.cumsum([0 if t else 1 for _c, t in scored])
    return (tp_cum / n_gt).tolist(), (tp_cum / np.maximum(tp_cum + fp_cum, 1)).tolist()


# --------------------------------------------------------------------------
# Confusion matrix and calibration
# --------------------------------------------------------------------------


def confusion_matrix(tiles_pred: List[List[dict]], tiles_gt: List[List[dict]]):
    """(9+1) x (9+1) matrix: rows = truth, cols = prediction, last = background.

    Built from the SAME greedy matching as the PRF numbers so the two agree.
    Unmatched ground truth lands in the background column; unmatched predictions
    land in the background row.
    """
    k = len(CLASSES)
    m = np.zeros((k + 1, k + 1), dtype=int)
    for preds, gts in zip(tiles_pred, tiles_gt):
        pairs, fpi, fni = match_tile(preds, gts)
        for pi, gi in pairs:
            m[gts[gi]["cls_id"], preds[pi]["cls_id"]] += 1
        for gi in fni:
            m[gts[gi]["cls_id"], k] += 1
        for pi in fpi:
            m[k, preds[pi]["cls_id"]] += 1
    return m


def calibration(tiles_pred: List[List[dict]], tiles_gt: List[List[dict]], n_bins: int = 10):
    """Reliability table + Expected Calibration Error.

    For each confidence bin, what fraction of boxes in that bin were actually
    correct? A perfectly calibrated detector has accuracy == confidence in every
    bin. This is what justifies the confidence floor empirically rather than by
    taste.
    """
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    n = np.zeros(n_bins, dtype=int)
    correct = np.zeros(n_bins, dtype=int)

    for preds, gts in zip(tiles_pred, tiles_gt):
        pairs, fpi, _ = match_tile(preds, gts)
        tp_idx = {pi for pi, gi in pairs if preds[pi]["cls"] == gts[gi]["cls"]}
        for pi, p in enumerate(preds):
            b = min(n_bins - 1, int(np.digitize(p["conf"], edges) - 1))
            n[b] += 1
            correct[b] += 1 if pi in tp_idx else 0

    rows, ece, total = [], 0.0, int(n.sum())
    for b in range(n_bins):
        if n[b] == 0:
            rows.append(
                {
                    "lo": float(edges[b]),
                    "hi": float(edges[b + 1]),
                    "n": 0,
                    "accuracy": None,
                    "confidence": None,
                }
            )
            continue
        acc = correct[b] / n[b]
        mid = (edges[b] + edges[b + 1]) / 2
        ece += (n[b] / total) * abs(acc - mid)
        rows.append(
            {
                "lo": float(edges[b]),
                "hi": float(edges[b + 1]),
                "n": int(n[b]),
                "accuracy": float(acc),
                "confidence": float(mid),
            }
        )
    return {"bins": rows, "ece": float(ece), "n_detections": total}


def localisation_iou(tiles_pred: List[List[dict]], tiles_gt: List[List[dict]]):
    """IoU distribution over true positives -- box tightness, not detection."""
    vals = []
    for preds, gts in zip(tiles_pred, tiles_gt):
        pairs, _fpi, _ = match_tile(preds, gts)
        for pi, gi in pairs:
            if preds[pi]["cls"] == gts[gi]["cls"]:
                vals.append(iou(preds[pi]["box"], gts[gi]["box"]))
    if not vals:
        return {"n": 0, "median": 0.0, "mean": 0.0, "gt_090": 0.0}
    a = np.array(vals)
    return {
        "n": int(a.size),
        "median": float(np.median(a)),
        "mean": float(a.mean()),
        "gt_090": float((a > 0.90).mean()),
    }
