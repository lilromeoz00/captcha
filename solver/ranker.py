"""ranker.py -- the agent: observation in, action out.

    strip (1600x400)  ->  nine 200x200 tiles          (geometry)
                      ->  one batched YOLO forward     (detector)
                      ->  nine vegetable multisets
                      ->  score every basket vs the key (multiset)
                      ->  answer, or recycle on a tie

One strip costs exactly one forward pass over nine tiles. Everything above the
detector is integer arithmetic.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional

from . import geometry, multiset
from .detector import VeggieDetector

#: A key tile shows exactly four vegetables. Detections beyond the fourth are
#: duplicates/background, so the key is trimmed to its four most confident
#: boxes. Baskets are NOT trimmed -- surplus there is real evidence of a wrong
#: basket and the penalty is supposed to see it.
KEY_MAX: int = 4


def rank_strip(
    detector: VeggieDetector,
    image,
    key_max: int = KEY_MAX,
    on_tie: str = "recycle",
) -> Dict:
    """Full pipeline for one challenge strip. Returns a plain dict (JSON-safe)."""
    tiles = geometry.slice_strip(image)  # validates 1600x400
    ids = geometry.cell_ids()
    crops = [tiles[cid] for cid in ids]
    dets = detector.detect(crops)

    per_tile = dict(zip(ids, dets))
    key_dets = per_tile[geometry.KEY_ID][:key_max]
    key: Dict[str, int] = multiset.as_multiset(cls for cls, _ in key_dets)

    baskets: Dict[str, Dict[str, int]] = {}
    for cid in ids:
        if cid == geometry.KEY_ID:
            continue
        baskets[cid] = dict(multiset.as_multiset(cls for cls, _ in per_tile[cid]))

    ranking = multiset.rank(key, baskets)
    action, target = multiset.decide(ranking, on_tie=on_tie)

    return {
        "action": action,
        "answer": int(target) if target is not None else None,
        "margin": ranking.margin,
        "tie": ranking.tie,
        "key": key,
        "baskets": baskets,
        "scores": {cid: m.score for cid, m in ranking.order},
        "misses": ranking.best_match.misses,
        "extras": ranking.best_match.extras,
        "exact_baskets": ranking.exact_baskets,
        "order": [cid for cid, _ in ranking.order],
    }


def solve_file(detector: VeggieDetector, path: str, **kw) -> Dict:
    """Convenience wrapper: load a JPEG from disk and rank it."""
    from PIL import Image

    with Image.open(path) as img:
        return rank_strip(detector, img.convert("RGB"), **kw)


def evaluate(
    detector: VeggieDetector,
    strips: Mapping[str, str],
    truth: Mapping[str, int],
    on_tie: str = "recycle",
) -> Dict:
    """Score the agent on a labelled set and decompose the error.

    `strips` maps strip id -> file path, `truth` maps strip id -> correct cell.
    The decomposition separates the two failure modes that a bare accuracy
    number conflates:

    * **ceiling**  -- on how many strips did the detector's own multisets
      contain an exactly-correct basket at all? If none did, no ranker could
      have won that strip; the perception stage lost the information.
    * **exploited** -- of the strips that had an exact basket available, how
      often did the scoring function pick it? This isolates ranking quality.
    """
    rows: List[Dict] = []
    for sid in sorted(strips):
        r = solve_file(detector, strips[sid], on_tie=on_tie)
        correct = truth.get(sid)
        rows.append(
            {
                "strip": sid,
                "pred": r["answer"],
                "truth": correct,
                "ok": r["answer"] == correct,
                "margin": r["margin"],
                "action": r["action"],
                "n_exact": len(r["exact_baskets"]),
                "exact_has_truth": str(correct) in r["exact_baskets"],
                "key": r["key"],
                "misses": r["misses"],
                "extras": r["extras"],
            }
        )

    n = len(rows)
    right = sum(r["ok"] for r in rows)
    ceiling = [r for r in rows if r["exact_has_truth"]]
    exploited = [r for r in ceiling if r["ok"]]
    zero_margin = [r for r in rows if r["margin"] == 0]

    return {
        "n": n,
        "right": right,
        "accuracy": right / n if n else 0.0,
        "ties": len(zero_margin),
        "ceiling_n": len(ceiling),
        "ceiling_rate": len(ceiling) / n if n else 0.0,
        "exploited": len(exploited),
        "exploit_rate": len(exploited) / len(ceiling) if ceiling else 0.0,
        "misses": [r["strip"] for r in rows if not r["ok"]],
        "rows": rows,
    }


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval -- the honest error bar for a small test set."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    w = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return ((c - w) / d, (c + w) / d)


def margin_table(rows: List[Dict], edges=(0, 1, 4, 8, 10**9)) -> List[Dict]:
    """Accuracy as a function of decision margin -- the agent's own confidence."""
    out = []
    for lo, hi in zip(edges, edges[1:]):
        band = [r for r in rows if lo <= r["margin"] < hi]
        if not band:
            continue
        ok = sum(r["ok"] for r in band)
        out.append(
            {
                "lo": lo,
                "hi": None if hi == 10**9 else hi,
                "n": len(band),
                "right": ok,
                "acc": ok / len(band),
            }
        )
    return out


def per_class_counts(rows: List[Dict]) -> Dict[str, int]:
    """How often each class appeared in a key -- shows the class balance."""
    tally = {c: 0 for c in multiset.CLASSES}
    for r in rows:
        for cls, n in r["key"].items():
            tally[cls] = tally.get(cls, 0) + n
    return tally
