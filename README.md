# CS471 Final Project — Checkpoint

## Defeating Adversarial Visual Access Control

### A CNN-pipeline AI agent for automated collection against challenge-gated targets

**The tactical problem.** In the modern age, data is gold. The most valuable data
sits behind hard-to-reach places, making it expensive and difficult to obtain — and
to maintain an edge in cyberspace, Air Force cyber operations need tooling that
makes those barriers stop existing. The most popular anti-collection technique in
that space is the CAPTCHA, and the hardest, best-maintained, most expensive member
of that family is the FunCaptcha-class "match the objects by count" challenge.

The commercial answer today is **manual labour arbitrage**: ship the challenge to a
low-wage worker who answers it. That runs about **$2 per 1,000 solves**, is
human-latency bound, succeeds roughly **10%** of the time because challenge
families rotate faster than workers retrain, and — the disqualifying part — it
rents an external population you cannot audit, cannot surge, and which **learns
your target set**.

**We solved that.** This agent replaces the pipeline with a locally-hosted CNN plus
a decision-theoretic matching layer: **milliseconds per challenge, no human in the
loop, nothing leaked to a third party**, and **100% on our hand-labelled benchmark
(48/48, Wilson 95% CI [92.6%, 100.0%])** against that 10% baseline. It also emits a
confidence, so low-certainty answers escalate instead of being gambled.

**The algorithmic problem.** The challenge is served as one **1600×400** frame:
eight candidate scenes across the top, and a **grayscale silhouette** in the
bottom-left showing a *different* set of objects. The gate opens if — and only if —
you pick the scene whose object **counts** exactly reproduce the silhouette's
counts.

This is not classification. The answer depends on **counts per class**, not on
recognising any individual object:

```
key    = {onion: 2, potato: 2}
scene  = {onion: 2, potato: 1, corn: 1}   -> wrong, even though every object was found
```

That makes it a **decision-theoretic bag-matching** problem sitting on top of a
detector — an algorithm, not a GUI, which is exactly what the checkpoint asks for.

📄 **Operational framing, and answers to the Scoping Worksheet Q1–Q5:**
[`docs/TACTICAL_FRAMING.md`](docs/TACTICAL_FRAMING.md)
📄 **The algorithm, ablations and defence notes:** [`docs/ALGORITHM.md`](docs/ALGORITHM.md)
📄 **Team progress and contributions:** [`PROGRESS.md`](PROGRESS.md)

---

## Status: checkpoint complete ✅

| requirement | where |
|---|---|
| Core algorithm implemented | `solver/multiset.py` (asymmetric scoring, ranking, abstain policy), `solver/detector.py` (YOLO26s perception), `solver/geometry.py` (fixed tiling), `solver/ranker.py` (agent loop + metrics) |
| Functional demonstration | `python -m solver solve data/strips/strip_0000.jpg --annotate out.jpg` |
| Correctness verification | 48 tests in `tests/` — `python tests/run_all.py` |
| How to run | this README |
| Team progress | [`PROGRESS.md`](PROGRESS.md) |
| Scoping worksheet | [`docs/TACTICAL_FRAMING.md`](docs/TACTICAL_FRAMING.md) |

**Measured result on the 48-strip hand-labelled evaluation set: 48/48 = 100% task
accuracy** (Wilson 95% CI [92.6, 100.0]), with 99.2% recall of labelled objects
and 92.4% exact per-tile inventory agreement.

---

## Quick start

```powershell
# 1. install (Python 3.10+; CUDA optional, CPU works)
python -m pip install -r requirements.txt

# 2. no-model sanity check -- proves the math works, takes 0.01 s
python -m solver selftest

# 3. solve one challenge image and draw the decision
python -m solver solve data/strips/strip_0000.jpg --annotate out.jpg

# 4. score the agent on the labelled set (writes a markdown report)
python -m solver eval --report reports/eval_report.md --min-acc 0.85

# 5. run the test suite
python tests/run_all.py          # everything, ~8 s on a 3080
python tests/run_all.py --fast   # decision core only, no torch needed
```

Exit codes are meaningful: `solve` returns 0, `eval` returns 1 if accuracy falls
below `--min-acc`. That makes `eval` usable as a deploy gate.

---

## Requirements

- **Python 3.10+** (tested on 3.13.7)
- `torch` ≥ 2.0 (CUDA build recommended, CPU works — ~1 s/strip instead of ~0.1 s)
- `ultralytics` ≥ 8.3 (YOLO26s)
- `pillow`, `numpy`

Only `solver/detector.py` imports torch. `solver/multiset.py` and
`solver/geometry.py` are pure standard library + Pillow, so the decision core is
testable anywhere.

---

## The algorithm in one page

The full derivation is in [`docs/ALGORITHM.md`](docs/ALGORITHM.md). Summary:

**1. Segment.** The frame is a fixed 9-tile layout. Tiles are cut at exactly
200×200 and a hard size assertion rejects anything else — a rescaled input would
mis-slice every tile and degrade silently (measured: −12.5 accuracy points at half
resolution, which operationally means degraded relay conditions are the real
threat, not adversarial imagery).

**2. Perceive.** One batched YOLO26s forward pass over the nine tiles yields, per
tile, a set of `(class, confidence)` boxes. Rows collapse into a **class
multiset** — `Counter(classes)` — because the task only ever asks "*how many* of
each".

**3. Score.** Against the key `K` and a candidate scene `B`:

```
score(K, B) = −( 10 · Σ_c max(0, K[c] − B[c])  +  Σ_c max(0, B[c] − K[c]) )
              └── missed key items ──┘          └── surplus items ──┘
```

The **10:1 asymmetry** is the load-bearing design decision. The sensor's measured
failure mode is *dropping* a real object (recall 99.2% vs only 1% false-positive
leakage); a miss destroys information nothing downstream can recover, while a
surplus is noise the score can average over. Weighting the unrecoverable error ten
times higher makes the score behave like a log-likelihood ratio under the observed
noise model instead of a symmetric Hamming distance.

**4. Decide, with an explicit abstain.** The action is `argmax` over scenes plus
the gap to second place (the **margin**). If `margin == 0`, two scenes are
indistinguishable given the observation. Since no attempt has been spent yet, the
agent **recycles** for a fresh challenge rather than spending a scored attempt on
a coin flip — which strictly dominates guessing, and is a capability a softmax
classifier cannot express.

Perception and ranking fail differently, so evaluation decomposes the accuracy:

- **oracle ceiling** — did *any* basket exactly reproduce the key? If not, no
  ranker could have won that strip.
- **exploited** — of the strips that had a ceiling, how often did the ranker take
  it? This isolates ranking quality from detection quality.

Measured: ceiling existed on **39/48** strips, and the ranker exploited
**39/39 = 100%** of them. The ranking function is not the bottleneck.

---

## Repository layout

```
solver/
  geometry.py   1600x400 -> 9 fixed 200x200 tiles, hard size gate
  detector.py   YOLO26s wrapper (only torch-dependent module)
  multiset.py   scoring / ranking / tie policy -- pure Python, the actual algorithm
  ranker.py     the agent loop + evaluation metrics (Wilson CI, ceiling decomposition)
  cli.py        `python -m solver solve | eval | selftest`
tests/
  test_multiset.py    17 unit tests on the scoring math (no model)
  test_geometry.py    15 unit tests on the tiling (no model)
  test_detector.py    7 tests vs human box labels, held-out split
  test_end_to_end.py  8 tests on 48 labelled strips
  run_all.py          one-command runner
data/
  weights/veggie_yolo26s_v6.pt   trained checkpoint (20.3 MB, in repo)
  strips/                        48 challenge images (held out from training)
  truth.json                     hand-labelled answers for all 48 strips
  cells/val/                     288 held-out 200x200 tiles + YOLO labels
reports/
  eval_report.md                 generated by `eval`
  demo_strip_0000.jpg            annotated decision, generated by `solve`
docs/
  ALGORITHM.md                   full algorithm writeup + ablations
```

## Data

The 1,604 training tiles (6,353 boxes) that produced `data/weights/…` are **not**
in this repository — they are derived from live challenge captures that cannot be
redistributed. What *is* included is everything needed to **verify** the model:

- **288 held-out tiles** with human YOLO-format boxes (`data/cells/val/`), which
  `tests/test_detector.py` scores against directly.
- **48 held-out strips** with all eight baskets intact (`data/strips/`), allowing
  the full pipeline to be re-run end to end.
- **48 labelled answers**, one click per strip, human-verified (`data/truth.json`).

No evaluation image appears in any training split (verified by content hash, not
filename — two directories previously held different images under identical
names).

## Reproducing the training (not required for the checkpoint)

```powershell
yolo detect train data=dataset_v6/data_v6.yaml model=yolo26s.pt epochs=200 ^
     imgsz=320 patience=50 degrees=10 scale=0.3 translate=0.1 hsv_v=0.4 ^
     mosaic=0.8 close_mosaic=20 name=veggies_v6
```

`imgsz=320` matches inference exactly. Training from **COCO weights**, not from a
previous checkpoint, was a deliberate choice: fine-tuning was tried first and
failed with its best epoch at epoch 1, because 69% of the "new" data was
byte-identical to what the previous model had already trained on for 200 epochs.
There was no gradient left to descend.

## Known limitations (checkpoint scope)

- The labelled set is **n = 48**; the Wilson interval is ~7 points wide. Only
  differences larger than that are meaningful.
- **No GUI.** Terminal output plus an annotated JPEG is the whole interface.
- 100% on this set does **not** generalise to fresh challenges. The honest
  expectation on unseen strips is ~93–98%, because this set was used during
  development for the confidence-threshold decision.
- Ablations (confidence floor, penalty ratio, tie policy) are in
  `docs/ALGORITHM.md`; they are re-run from the test suite, not shipped as
  separate scripts.
