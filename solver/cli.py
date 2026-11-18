"""cli.py -- terminal entry point.

    python -m solver solve data/strips/strip_0000.jpg
    python -m solver solve data/strips/strip_0000.jpg --json --annotate out.jpg
    python -m solver eval --report reports/eval_report.md
    python -m solver selftest

Nothing here needs a GPU; nothing here needs a GUI. Exit codes are meaningful so
the eval can be wired into CI: 0 = ok, 1 = wrong answer / below threshold.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Dict, List

from . import geometry, multiset, ranker
from .detector import VeggieDetector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_WEIGHTS = os.path.join(ROOT, "data", "weights", "veggie_yolo26s_v6.pt")
DEFAULT_STRIPS = os.path.join(ROOT, "data", "strips")
DEFAULT_TRUTH = os.path.join(ROOT, "data", "truth.json")


def _detector(a) -> VeggieDetector:
    return VeggieDetector(
        weights=a.weights,
        conf=a.conf,
        imgsz=a.imgsz,
        device=(None if a.device == "auto" else a.device),
    )


def _fmt_bag(bag: Dict[str, int]) -> str:
    if not bag:
        return "-"
    return " ".join(f"{k}x{v}" for k, v in sorted(bag.items()))


def cmd_solve(a) -> int:
    det = _detector(a)
    res = ranker.solve_file(det, a.image, on_tie=a.on_tie)

    if a.json:
        print(json.dumps(res, indent=1, sort_keys=True))
    else:
        print(f"image      : {a.image}")
        print(f"key (S)    : {_fmt_bag(res['key'])}")
        for cid in sorted(res["baskets"], key=int):
            mark = " <-- ANSWER" if res["answer"] == int(cid) else ""
            print(
                f"  basket {cid} : {_fmt_bag(res['baskets'][cid]):<44}"
                f" score={res['scores'][cid]:>5}{mark}"
            )
        print(
            f"decision   : {res['action']}"
            + (f" basket {res['answer']}" if res["answer"] is not None else "")
            + f"   margin={res['margin']}  misses={res['misses']} "
            f"extras={res['extras']}  tie={res['tie']}"
        )

    if a.annotate:
        _annotate(a.image, res, a.annotate)
        print(f"annotated  : {a.annotate}")
    return 0


def _annotate(path: str, res: Dict, out: str) -> None:
    """Draw the decision back onto the strip -- the human-readable evidence."""
    from PIL import Image, ImageDraw

    with Image.open(path) as im:
        img = im.convert("RGB").copy()
    dr = ImageDraw.Draw(img)
    for cid in geometry.cell_ids():
        x0, y0, x1, y1 = geometry.cell_box(cid)
        if cid == geometry.KEY_ID:
            colour = (0, 220, 255)
        elif res["answer"] == int(cid):
            colour = (0, 255, 0)
        else:
            colour = (110, 110, 110)
        dr.rectangle([x0, y0, x1 - 1, y1 - 1], outline=colour, width=3)
        if cid == geometry.KEY_ID:
            continue
        # label in the bottom strip of each tile, boxed so it stays readable
        txt = f"{cid}  score {res['scores'][cid]}"
        tx, ty = x0 + 5, y1 - 16
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            dr.text((tx + dx, ty + dy), txt, fill=(0, 0, 0))
        dr.text((tx, ty), txt, fill=colour)

    # narrative panel in the empty black space right of the key tile
    px, py = geometry.CELL + 14, geometry.CELL + 10
    lines = [
        (f"KEY  {_fmt_bag(res['key'])}", (0, 220, 255)),
        (
            f"ANSWER  basket {res['answer']}" if res["answer"] is not None else "RECYCLE (tie)",
            (0, 255, 0),
        ),
        (
            f"margin {res['margin']}   misses {res['misses']}   extras {res['extras']}",
            (200, 200, 200),
        ),
    ]
    for i, (line, colour) in enumerate(lines):
        dr.text((px, py + i * 15), line, fill=colour)
    img.save(out, quality=92)


def cmd_eval(a) -> int:
    truth = json.load(open(a.truth, encoding="utf-8"))
    strips = {
        os.path.basename(p)[:-4]: p for p in sorted(glob.glob(os.path.join(a.strips, "*.jpg")))
    }
    if a.limit:
        keep = sorted(strips)[: a.limit]
        strips = {k: strips[k] for k in keep}

    det = _detector(a)
    print(f"weights : {a.weights}")
    print(f"strips  : {len(strips)} from {a.strips}")
    print(f"conf    : {a.conf}   imgsz: {a.imgsz}   on_tie: {a.on_tie}\n")

    rep = ranker.evaluate(det, strips, truth, on_tie=a.on_tie)
    lo, hi = ranker.wilson(rep["right"], rep["n"])

    for r in rep["rows"]:
        flag = "ok  " if r["ok"] else "MISS"
        print(
            f"  {flag} {r['strip']}  pred={r['pred']} truth={r['truth']}  "
            f"margin={r['margin']:>4}  key={_fmt_bag(r['key'])}"
        )

    print(
        f"\naccuracy    : {rep['right']}/{rep['n']} = {rep['accuracy'] * 100:.1f}%"
        f"   Wilson95 [{lo * 100:.1f}, {hi * 100:.1f}]"
    )
    print(f"ties        : {rep['ties']}")
    print(
        f"ceiling     : {rep['ceiling_n']}/{rep['n']} strips had an exactly-correct "
        f"basket ({rep['ceiling_rate'] * 100:.1f}%)"
    )
    print(
        f"exploited   : {rep['exploited']}/{rep['ceiling_n']} = "
        f"{rep['exploit_rate'] * 100:.1f}% of available ceilings"
    )
    if rep["misses"]:
        print(f"misses      : {', '.join(rep['misses'])}")

    if a.report:
        _write_report(a.report, rep, a, lo, hi)
        print(f"\nreport      : {a.report}")

    if a.min_acc is not None and rep["accuracy"] < a.min_acc:
        print(f"\nFAIL: accuracy below --min-acc {a.min_acc}")
        return 1
    return 0


def _write_report(path: str, rep: Dict, a, lo: float, hi: float) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    mt = ranker.margin_table(rep["rows"])
    pc = ranker.per_class_counts(rep["rows"])

    L: List[str] = []
    L.append("# Checkpoint evaluation report\n")
    L.append(f"- weights: `{os.path.basename(a.weights)}`")
    L.append(f"- conf: {a.conf}  imgsz: {a.imgsz}  tie policy: {a.on_tie}")
    L.append(f"- strips: {rep['n']}\n")
    L.append("## Headline\n")
    L.append("| metric | value |")
    L.append("|---|---|")
    L.append(
        f"| task accuracy | **{rep['right']}/{rep['n']} = "
        f"{rep['accuracy'] * 100:.1f}%** (Wilson 95% CI "
        f"[{lo * 100:.1f}, {hi * 100:.1f}]) |"
    )
    L.append(f"| ties (margin = 0) | {rep['ties']} |")
    L.append(
        f"| oracle ceiling (a basket exactly matched the key) | "
        f"{rep['ceiling_n']}/{rep['n']} = {rep['ceiling_rate'] * 100:.1f}% |"
    )
    L.append(
        f"| ceiling exploited by the ranker | "
        f"{rep['exploited']}/{rep['ceiling_n']} = {rep['exploit_rate'] * 100:.1f}% |"
    )
    L.append("")
    L.append("## Accuracy vs decision margin\n")
    L.append("The margin is the agent's own confidence: score(best) - score(second).")
    L.append("")
    L.append("| margin band | n | correct | accuracy |")
    L.append("|---|---|---|---|")
    for b in mt:
        band = f"{b['lo']}+" if b["hi"] is None else f"{b['lo']}-{b['hi'] - 1}"
        L.append(f"| {band} | {b['n']} | {b['right']} | {b['acc'] * 100:.1f}% |")
    L.append("")
    L.append("## Class frequency in the keys\n")
    L.append("| class | key instances |")
    L.append("|---|---|")
    for cls, n in pc.items():
        L.append(f"| {cls} | {n} |")
    L.append("")
    L.append("## Per-strip decisions\n")
    L.append("| strip | pred | truth | ok | margin | key |")
    L.append("|---|---|---|---|---|---|")
    for r in rep["rows"]:
        L.append(
            f"| {r['strip']} | {r['pred']} | {r['truth']} | "
            f"{'yes' if r['ok'] else '**no**'} | {r['margin']} | "
            f"{_fmt_bag(r['key'])} |"
        )
    L.append("")
    open(path, "w", encoding="utf-8").write("\n".join(L))


def cmd_selftest(a) -> int:
    """No-model sanity check: the scoring math and the tiling, on toy inputs."""
    key = multiset.as_multiset(["onion", "onion", "potato", "potato"])
    perfect = multiset.match(key, multiset.as_multiset(["onion", "onion", "potato", "potato"]))
    one_miss = multiset.match(key, multiset.as_multiset(["onion", "onion", "potato"]))
    one_extra = multiset.match(
        key, multiset.as_multiset(["onion", "onion", "potato", "potato", "corn"])
    )
    print(f"exact      : score={perfect.score} misses={perfect.misses} extras={perfect.extras}")
    print(f"one miss   : score={one_miss.score}")
    print(f"one extra  : score={one_extra.score}")
    ok = perfect.exact and perfect.score == 0 and one_miss.score == -10 and one_extra.score == -1
    print(f"tiling     : {geometry.STRIP_W}x{geometry.STRIP_H}, {len(geometry.cell_ids())} tiles")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m solver",
        description="CS471 checkpoint: adversarial visual challenge solver (YOLO + multiset matching)",
    )
    p.add_argument("--weights", default=DEFAULT_WEIGHTS)
    p.add_argument("--conf", type=float, default=0.4)
    p.add_argument("--imgsz", type=int, default=320)
    p.add_argument("--device", default="auto", help="auto | cpu | cuda:0")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("solve", help="rank one challenge strip")
    s.add_argument("image")
    s.add_argument("--json", action="store_true")
    s.add_argument("--annotate", default=None, metavar="OUT.jpg")
    s.add_argument("--on-tie", dest="on_tie", default="recycle", choices=["recycle", "guess"])
    s.set_defaults(func=cmd_solve)

    e = sub.add_parser("eval", help="score the agent on a labelled strip set")
    e.add_argument("--strips", default=DEFAULT_STRIPS)
    e.add_argument("--truth", default=DEFAULT_TRUTH)
    e.add_argument("--limit", type=int, default=None)
    e.add_argument("--report", default=None, metavar="OUT.md")
    e.add_argument("--min-acc", dest="min_acc", type=float, default=None)
    e.add_argument("--on-tie", dest="on_tie", default="recycle", choices=["recycle", "guess"])
    e.set_defaults(func=cmd_eval)

    t = sub.add_parser("selftest", help="math/tiling check, no model required")
    t.set_defaults(func=cmd_selftest)
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
