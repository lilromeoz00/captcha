"""Run every experiment and write results/experiments.json.

    python experiments/run_all.py            # everything (~2-3 min on a 3080)
    python experiments/run_all.py --quick    # skip the robustness sweep

Design notes
------------
* Detections are computed ONCE at the production setting and cached. Every
  baseline that consumes detector output reads that cache, so all the
  decision-level baselines are compared on identical evidence -- the only thing
  that varies between them is the decision rule. That is what makes the
  comparison meaningful rather than a comparison of two different models.
* The robustness sweep deliberately re-runs the network, because the whole point
  is how perception degrades.
* Every number written here is what the report quotes. Nothing is hand-typed.
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from PIL import Image, ImageFilter  # noqa: E402

from solver import geometry, ranker  # noqa: E402
from solver.detector import VeggieDetector  # noqa: E402

import baselines as B  # noqa: E402
import metrics as M  # noqa: E402

WEIGHTS = os.path.join(ROOT, "data", "weights", "veggie_yolo26s_v6.pt")
STRIPS_DIR = os.path.join(ROOT, "data", "strips")
TRUTH = os.path.join(ROOT, "data", "truth.json")
VAL_IMG = os.path.join(ROOT, "data", "cells", "val", "images")
VAL_LBL = os.path.join(ROOT, "data", "cells", "val", "labels")
OUT_DIR = os.path.join(ROOT, "results")
FIG_DIR = os.path.join(ROOT, "figures")
CACHE = os.path.join(OUT_DIR, "detections_cache.json")
CONF = 0.4
IMGSZ = 320


# --------------------------------------------------------------------------


def load_strips():
    strips = {
        os.path.basename(p)[:-4]: p for p in sorted(glob.glob(os.path.join(STRIPS_DIR, "*.jpg")))
    }
    with open(TRUTH, encoding="utf-8") as fh:
        truth = json.load(fh)
    return strips, truth


def detect_strips(det, strips, cache_path=None, use_cache=True):
    """Per strip: list of 9 detection lists (8 baskets then key)."""
    if use_cache and cache_path and os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as fh:
            return json.load(fh)

    ids = geometry.cell_ids()
    out = {}
    for n, (sid, path) in enumerate(strips.items(), 1):
        with Image.open(path) as im:
            tiles = geometry.slice_strip(im.convert("RGB"))
        boxes = det.detect_boxes([tiles[c] for c in ids])
        out[sid] = [
            [{"cls": b["cls"], "conf": b["conf"], "box": b["box"]} for b in tile]
            for tile in boxes
        ]
        if n % 12 == 0:
            print(f"    detections {n}/{len(strips)}", flush=True)

    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as fh:
            json.dump(out, fh)
    return out


def dets_as_pairs(dets):
    """Convert cached boxes -> the (cls, conf) shape the baselines expect."""
    return {sid: [[(b["cls"], b["conf"]) for b in tile] for tile in tiles]
            for sid, tiles in dets.items()}


# --------------------------------------------------------------------------


def exp_baselines(det, strips, truth, dets):
    print("\n[1/6] baseline comparison", flush=True)
    pairs = dets_as_pairs(dets)

    res = {}
    res["random"] = B.random_baseline(list(strips), truth, trials=1000)
    res["majority"] = B.majority_baseline(list(strips), truth)
    res["hist_match"] = B.hist_match_baseline(strips, truth)
    res["yolo_count"] = B.yolo_count_baseline(pairs, truth)
    res["yolo_confidence"] = B.yolo_confidence_baseline(pairs, truth)
    res["yolo_symmetric_1to1"] = B.yolo_symmetric_baseline(pairs, truth)
    res["yolo_asym_10to1"] = B.yolo_asym_baseline(pairs, truth)

    # cross-check: the submitted pipeline, run end to end, must agree
    full = ranker.evaluate(det, strips, truth)
    res["yolo_asym_10to1"]["pipeline_accuracy"] = full["accuracy"]

    for name, r in res.items():
        lo, hi = ranker.wilson(r["right"], r["n"])
        r["wilson_lo"], r["wilson_hi"] = lo, hi
        print(f"    {name:22} {r['right']}/{r['n']} = {r['accuracy']*100:5.1f}%"
              f"  CI [{lo*100:.1f}, {hi*100:.1f}]")

    # paired significance vs the submitted agent
    ours = res["yolo_asym_10to1"]["rows"]
    sig = {}
    for name, r in res.items():
        if name == "yolo_asym_10to1" or "rows" not in r:
            continue
        b_only, a_only, p = B.mcnemar_exact(ours, r["rows"])
        sig[name] = {"agent_only": a_only, "baseline_only": b_only, "p": p}
        print(f"    McNemar vs {name:20} agent-only={a_only:2} base-only={b_only:2} p={p:.4g}")
    res["_significance"] = sig
    return res


def exp_detection(det, truth_unused=None):
    print("\n[2/6] detection metrics on 288 held-out tiles", flush=True)
    files = sorted(glob.glob(os.path.join(VAL_IMG, "*.jpg")))
    preds, gts, sizes = [], [], []
    for f in files:
        with Image.open(f) as im:
            img = im.convert("RGB")
        sizes.append(img.size)
        preds.append(det.detect_boxes([img])[0])
        gts.append(
            M.load_gt(os.path.join(VAL_LBL, os.path.basename(f)[:-4] + ".txt"), img.size)
        )

    prf = M.per_class_prf(preds, gts)
    ap = {c: M.average_precision(preds, gts, c) for c in prf}
    for c in prf:
        prf[c]["ap50"] = ap[c]

    conf_mat = M.confusion_matrix(preds, gts)
    cal = M.calibration(preds, gts)
    loc = M.localisation_iou(preds, gts)

    micro_tp = sum(v["tp"] for v in prf.values())
    micro_fp = sum(v["fp"] for v in prf.values())
    micro_fn = sum(v["fn"] for v in prf.values())

    print(f"    micro P={micro_tp/(micro_tp+micro_fp):.4f} "
          f"R={micro_tp/(micro_tp+micro_fn):.4f}")
    print(f"    ECE={cal['ece']:.4f}  median IoU={loc['median']:.3f}")

    return {
        "n_tiles": len(files),
        "per_class": prf,
        "micro": {
            "tp": micro_tp,
            "fp": micro_fp,
            "fn": micro_fn,
            "precision": micro_tp / (micro_tp + micro_fp),
            "recall": micro_tp / (micro_tp + micro_fn),
        },
        "map50": float(np.nanmean([prf[c]["ap50"] for c in prf])),
        "confusion": conf_mat.tolist(),
        "calibration": cal,
        "localisation": loc,
        "_curves": {
            c: M.pr_curve(preds, gts, c) for c in prf
        },
        "_raw_counts": {
            "n_pred": sum(len(p) for p in preds),
            "n_gt": sum(len(g) for g in gts),
        },
    }


def _perturb(img, kind, level):
    if kind == "jpeg":
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=int(level))
        buf.seek(0)
        return Image.open(buf).convert("RGB")
    if kind == "blur":
        return img.filter(ImageFilter.GaussianBlur(radius=float(level)))
    if kind == "scale":
        w, h = img.size
        small = img.resize((int(w * level), int(h * level)), Image.BILINEAR)
        return small.resize((w, h), Image.BILINEAR)
    raise ValueError(kind)


def exp_robustness(det, strips, truth, cache_dir):
    print("\n[3/6] robustness sweep", flush=True)
    ids = geometry.cell_ids()
    conditions = (
        [("clean", None, None)]
        + [("jpeg", "jpeg", q) for q in (90, 80, 60, 40)]
        + [("blur", "blur", r) for r in (0.5, 1.0, 2.0)]
        + [("scale", "scale", s) for s in (0.75, 0.5)]
    )
    out = []
    for kind, ptype, level in conditions:
        label = "clean" if ptype is None else f"{ptype}={level}"
        cache = os.path.join(cache_dir, f"rob_{label.replace('=','_')}.json")
        right = n = 0
        n_resliced = 0
        for sid, path in strips.items():
            if sid not in truth:
                continue
            with Image.open(path) as im:
                img = im.convert("RGB")
            if ptype is not None:
                img = _perturb(img, ptype, level)
            # a rescaled frame is no longer 1600x400 -> geometry gate would fire.
            # For the *robustness* experiment we restore the size so the pipeline
            # can run; the gate is tested separately.
            if img.size != (geometry.STRIP_W, geometry.STRIP_H):
                n_resliced += 1
                img = img.resize((geometry.STRIP_W, geometry.STRIP_H), Image.BILINEAR)
            try:
                res = ranker.rank_strip(det, img)
            except Exception as exc:  # noqa: BLE001
                print(f"    {label} {sid} FAILED {type(exc).__name__}")
                n += 1
                continue
            n += 1
            right += res["answer"] == truth[sid]
        acc = right / n if n else 0.0
        out.append(
            {
                "condition": label,
                "kind": kind,
                "level": level,
                "right": right,
                "n": n,
                "accuracy": acc,
            }
        )
        print(f"    {label:12} {right}/{n} = {acc*100:5.1f}%", flush=True)
    return out


def exp_confidence_sweep(det, strips, truth):
    print("\n[4/6] confidence-floor sweep", flush=True)
    out = []
    ids = geometry.cell_ids()
    imgs = {}
    for sid, path in strips.items():
        with Image.open(path) as im:
            imgs[sid] = geometry.slice_strip(im.convert("RGB"))

    for conf in (0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60):
        right = n = 0
        for sid, tiles in imgs.items():
            if sid not in truth:
                continue
            boxes = det.detect_boxes([tiles[c] for c in ids], conf=conf)
            key = {}
            for b in boxes[8][:4]:
                key[b["cls"]] = key.get(b["cls"], 0) + 1
            scored = []
            for i in range(8):
                bag = {}
                for b in boxes[i]:
                    bag[b["cls"]] = bag.get(b["cls"], 0) + 1
                from solver.multiset import match

                scored.append((match(key, bag).score, str(i)))
            scored.sort(key=lambda t: (-t[0], t[1]))
            margin = scored[0][0] - scored[1][0]
            pred = None if margin == 0 else int(scored[0][1])
            n += 1
            right += pred == truth[sid]
        out.append({"conf": conf, "right": right, "n": n, "accuracy": right / n})
        print(f"    conf {conf:.2f} -> {right}/{n} = {right/n*100:5.1f}%", flush=True)
    return out


def exp_penalty_sweep(det, strips, truth):
    print("\n[5/6] penalty-ratio sweep", flush=True)
    from solver.multiset import match

    ids = geometry.cell_ids()
    dets = {}
    for sid, path in strips.items():
        with Image.open(path) as im:
            tiles = geometry.slice_strip(im.convert("RGB"))
        dets[sid] = det.detect_boxes([tiles[c] for c in ids])

    out = []
    for alpha in (1, 2, 3, 5, 8, 10, 15, 20, 50):
        right = n = 0
        for sid, boxes in dets.items():
            if sid not in truth:
                continue
            key = {}
            for b in boxes[8][:4]:
                key[b["cls"]] = key.get(b["cls"], 0) + 1
            scored = []
            for i in range(8):
                bag = {}
                for b in boxes[i]:
                    bag[b["cls"]] = bag.get(b["cls"], 0) + 1
                scored.append((match(key, bag, alpha, 1).score, str(i)))
            scored.sort(key=lambda t: (-t[0], t[1]))
            margin = scored[0][0] - scored[1][0]
            pred = None if margin == 0 else int(scored[0][1])
            n += 1
            right += pred == truth[sid]
        out.append({"alpha": alpha, "beta": 1, "right": right, "n": n,
                    "accuracy": right / n})
        print(f"    {alpha:2}:1 -> {right}/{n} = {right/n*100:5.1f}%", flush=True)
    return out


def exp_convergence():
    print("\n[6/6] training convergence", flush=True)
    src = os.path.join(ROOT, "data", "convergence.csv")
    if not os.path.exists(src):
        print("    data/convergence.csv missing -- skipped")
        return None
    import csv

    rows = []
    with open(src, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append(
                {
                    "epoch": int(float(r["epoch"])),
                    "box_loss": float(r["train/box_loss"]),
                    "cls_loss": float(r["train/cls_loss"]),
                    "precision": float(r["metrics/precision(B)"]),
                    "recall": float(r["metrics/recall(B)"]),
                    "map50": float(r["metrics/mAP50(B)"]),
                    "map50_95": float(r["metrics/mAP50-95(B)"]),
                    "val_box_loss": float(r["val/box_loss"]),
                }
            )
    best = max(rows, key=lambda r: r["map50_95"])
    print(f"    {len(rows)} epochs, best mAP50-95 {best['map50_95']:.4f} @ epoch {best['epoch']}")
    return {"rows": rows, "best": best, "n_epochs": len(rows)}


# --------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="skip the robustness sweep")
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)

    strips, truth = load_strips()
    print(f"weights : {WEIGHTS}")
    print(f"strips  : {len(strips)} ({len(truth)} labelled)")

    det = VeggieDetector(WEIGHTS, conf=CONF, imgsz=IMGSZ)

    t0 = time.time()
    print("\n[0/6] caching detections", flush=True)
    dets = detect_strips(det, strips, CACHE, use_cache=not a.no_cache)
    print(f"    cached {len(dets)} strips")

    results = {
        "meta": {
            "weights": os.path.basename(WEIGHTS),
            "conf": CONF,
            "imgsz": IMGSZ,
            "n_strips": len(strips),
            "n_labelled": len(truth),
            "generated": time.strftime("%Y-%m-%d %H:%M"),
        }
    }
    results["baselines"] = exp_baselines(det, strips, truth, dets)
    results["detection"] = exp_detection(det)
    results["confidence_sweep"] = exp_confidence_sweep(det, strips, truth)
    results["penalty_sweep"] = exp_penalty_sweep(det, strips, truth)
    results["convergence"] = exp_convergence()

    if a.quick:
        results["robustness"] = []
        print("\n[3/6] robustness SKIPPED (--quick)")
    else:
        results["robustness"] = exp_robustness(det, strips, truth, OUT_DIR)

    # headline agent result
    full = ranker.evaluate(det, strips, truth)
    lo, hi = ranker.wilson(full["right"], full["n"])
    results["agent"] = {
        "right": full["right"],
        "n": full["n"],
        "accuracy": full["accuracy"],
        "wilson_lo": lo,
        "wilson_hi": hi,
        "ties": full["ties"],
        "ceiling_n": full["ceiling_n"],
        "ceiling_rate": full["ceiling_rate"],
        "exploited": full["exploited"],
        "exploit_rate": full["exploit_rate"],
        "misses": full["misses"],
        "margin_table": ranker.margin_table(full["rows"]),
    }

    path = os.path.join(OUT_DIR, "experiments.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)
    print(f"\nwrote {path}   ({time.time() - t0:.1f}s)")
    print(f"agent: {full['right']}/{full['n']} = {full['accuracy']*100:.1f}% "
          f"CI [{lo*100:.1f}, {hi*100:.1f}]")


if __name__ == "__main__":
    main()
