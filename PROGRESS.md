# Team progress — Lesson 36 checkpoint

## Operational problem, in one paragraph

Collection against a defended target stops at the adversary's visual challenge
layer, not at its cryptography. The state of the art for defeating that layer is
manual labour arbitrage — ~$2 per 1,000 solves, human-latency bound, ~10%
reliable, and dependent on an external population that leaks the target set. This
project replaces that dependency with a locally-hosted CNN-plus-decision-theory
agent. Full framing and the Scoping Worksheet answers (Q1–Q5) are in
[`docs/TACTICAL_FRAMING.md`](docs/TACTICAL_FRAMING.md).

## Where we are

The checkpoint requirement was: *"demonstrate that your selected AI algorithm
works on a simplified version of your proposed problem."* That is done — the
algorithm runs end to end on real data and produces a measured number, not a
vibe.

**Working today**

- Full perceptual pipeline: 1600×400 strip → nine fixed tiles → one batched YOLO26s
  forward pass → nine class multisets.
- The core algorithm: asymmetric multiset scoring, ranking, margin computation and
  the tie/recycle decision rule, all in pure Python.
- A CLI with three subcommands (`solve`, `eval`, `selftest`) and meaningful exit
  codes, so `eval --min-acc` works as a regression gate.
- Annotated visual output: the decision is drawn back onto the strip
  (`reports/demo_strip_0000.jpg`).
- **48 automated tests**, split so the algorithmic core is testable with no GPU
  and no weights.
- A measured evaluation: **48/48 = 100%** task accuracy on 48 hand-labelled
  strips (Wilson 95% CI [92.6, 100.0]), with 99.2% vegetable recall and a ceiling
  decomposition showing the ranker exploits 39/39 available exact matches.

**Numbers that matter for the final**

| measurement | value | how |
|---|---|---|
| task accuracy | 100% (48/48) | `python -m solver eval` |
| 95% confidence interval | [92.6%, 100%] | Wilson score interval |
| perception recall | 99.2% (1134/1143) | vs human boxes, 288 held-out tiles |
| exact tile agreement | 92.4% (266/288) | detected multiset == labelled multiset |
| ranker ceiling conversion | 100% (39/39) | oracle decomposition |

## What remains for Lesson 41 (the Defence)

1. **Evaluation at scale.** 48 strips gives a ±7-point interval. We need ~300
   fresh strips to make accuracy claims sharper than "≥92%".
2. **Confusion matrix / PR curves** across the nine classes, including the
   sparse ones (cucumber n=56, eggplant n=53) where the estimate is currently
   noisy.
3. **Convergence evidence from training.** Loss curves and val mAP per epoch for
   the shipped checkpoint, plotted rather than quoted.
4. **Robustness sweep as a graph.** JPEG quality and resolution vs accuracy
   (preliminary: half resolution is the dominant failure mode, −12.5 points).
5. **Live session integration.** The solver currently runs on saved images; the
   final version reads challenges from a session and submits an answer. This is
   the "wrap it in a loop" step, and it is deliberately deferred — the checkpoint
   grades the algorithm, not the plumbing.
6. **Tactical analysis section** for the presentation: what the accuracy curve
   implies about where human-labour defences actually break.

## Contributions

> **ACTION ITEM — fill in the bracketed names before submitting.** The structure
> below reflects who did what; replace `[Teammate]` with real names and adjust if
> the split was different.

| member | contributions | share |
|---|---|---|
| **[Jordan Moore]** | Problem framing and scoping. Captured and curated the training data across six dataset generations, hand-labelled all grayscale key cells, trained and evaluated the YOLO26s detector, ran the TIDE error decomposition and selected the 0.4 confidence floor from calibration. Wrote the scoring function, the tie policy, and `docs/ALGORITHM.md`. | ~65% |
| **[Teammate]** | Built the test harness (`tests/run_all.py`, 48 tests) and the geometry/validation layer with its hard 1600×400 gate. Wrote the evaluation reporting (Wilson intervals, ceiling decomposition, margin tables) and the CLI's annotated output. Ran the confidence and penalty-ratio ablations and did the literature check on domain transfer. | ~35% |

*Total effort: roughly 6 weeks of part-time work, most of it in data labelling and
in the four dataset rebuilds that each fixed one specific bug.*

## Challenges encountered (and what they cost us)

1. **Object scale mismatch (v1).** Trained at `imgsz=1280` on whole strips;
   validation mAP50 was 0.991 and the model was useless in production, because
   inference on a 200×200 crop put every object far outside the learned size
   distribution. **Fix:** decide the inference tile size first, then train only on
   that tile size. *Cost: ~1 week.*
2. **Fine-tuning was a dead end (v5).** Early stopping at epoch 51 with the best
   score at **epoch 1**. Diagnosis by MD5: 798 of 1,150 "new" training images were
   byte-identical to files the previous model had already seen for 200 epochs —
   there was no gradient left to descend. **Fix:** retrain from COCO weights.
   *Cost: 2 days, plus the realisation that "more data" was a lie.*
3. **Lost annotation provenance.** The labelling tool wrote tight per-class crops
   but not their source coordinates, making 332 finished annotations unusable for
   detector training. **Fix:** recovered them exactly by normalised
   cross-correlation template matching (787 crops, all ≥0.998, 4 s).
   *Cost: 3 days.*
4. **Two visual domains in one image.** The grayscale key is materially harder
   than the color baskets. Splitting into 18 classes was considered and rejected:
   measured mAP50 of 0.958 on keys with a shared vocabulary beats what 9-class keys
   could learn from a sixth of the data. *Cost: a week of experiments to prove the
   negative.*
5. **Silent rescaling.** A resized input mis-slices every tile and degrades the
   answer with no error. **Fix:** a hard geometry assertion at the entry to the
   pipeline, plus a test that asserts it fires.
6. **Ambiguous inputs by construction.** Two baskets can legitimately score
   identically. Rather than tune the score until ties vanish, we made ties an
   explicit, first-class action (`recycle`). *Cost: none — this one was a design
   win.*

## What we deliberately did NOT do

- **No GUI.** The assignment allows terminal output, and a GUI would not
  demonstrate anything about the algorithm.
- **No attempt to raise accuracy by tuning on the evaluation set.** The 0.4
  confidence floor is the only value selected with the evaluation set in view, and
  it is reported as such — the honest generalisation claim is "≥92.6%", not
  "100%".
- **No model ensembling.** A second model would add 20 MB and latency for a
  bottleneck that the ceiling decomposition proves is not the accuracy-limiting
  stage.
