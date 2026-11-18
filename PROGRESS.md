# Team progress — Lesson 36 checkpoint / Lesson 41 final

## Team composition

**This is a solo submission.** Jordan Moore is the only team member; every component
listed below was authored by him. The contribution split is therefore 100% / 0%,
and there is no second member to attribute work to.

This section previously contained a `[Teammate]` placeholder from an earlier draft
that assumed a two-person team. That placeholder has been removed: an unfilled
placeholder in a graded "team accountability" section is worse than an honest
statement that the work was solo.

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
algorithm runs end to end on real data and produces a measured number, not a vibe.

**Working today**

- Full perceptual pipeline: 1600×400 frame → nine fixed tiles → one batched YOLO26s
  forward pass → nine class multisets.
- The core algorithm: asymmetric multiset scoring, ranking, margin computation and
  the abstain/recycle decision rule, all in pure Python.
- A CLI with three subcommands (`solve`, `eval`, `selftest`) and meaningful exit
  codes, so `eval --min-acc` works as a regression gate.
- Annotated visual output: the decision is drawn back onto the frame
  (`reports/demo_strip_0000.jpg`).
- **80 automated tests**, split so the algorithmic core is testable with no GPU and
  no weights.
- A complete experiment programme: six baselines, per-class detection metrics,
  calibration, confusion matrix, ablations, and a ten-condition robustness sweep.
- A generated 5-page technical report (`CS471_Final_Report.pdf`).

**Numbers that matter**

| measurement | value | how |
|---|---|---|
| task accuracy | 100% (48/48) | `python -m solver eval` |
| 95% confidence interval | [92.6%, 100%] | Wilson score interval |
| strongest non-matching baseline | 25.0% | YOLO + max confidence |
| perception recall | 99.0% (1132/1143) | vs human boxes, 288 held-out tiles |
| mAP50 | 0.983 | all-point AP, IoU 0.5 |
| ranker ceiling conversion | 100% (39/39) | oracle decomposition |
| dominant failure mode | 64.6% at blur r=2.0 | robustness sweep |

## What remains

Nothing required by the rubric. Work that would strengthen the analysis beyond the
submission:

1. **Evaluation at scale.** 48 strips gives a ±7-point interval; ~300 fresh strips
   would sharpen accuracy claims beyond "≥92%".
2. **A second, independent evaluation set** so the confidence floor can be selected
   without the test strips in view.
3. **Live-session integration** — the loop that fetches a challenge and submits an
   answer. Deliberately out of scope: the milestone grades the algorithm.
4. **Per-class AP for the two key classes that never appear** (green pepper,
   carrot), which needs new captures rather than more labels.

## Contributions

| member | contributions | share |
|---|---|---|
| **Jordan Moore** | Everything: problem framing and tactical analysis; capture and curation of six dataset generations; hand-labelling of all grayscale key tiles; detector training and evaluation; TIDE error decomposition and confidence-floor selection; the scoring function, abstain policy and agent loop; the experiment harness, all six baselines, the metrics implementation and the report generator; the test suite; both design documents. | 100% |

*Total effort: roughly 8 weeks of part-time work, most of it in data labelling and
in the four dataset rebuilds that each fixed one specific bug.*

## Challenges encountered (and what they cost)

1. **Object scale mismatch (v1).** Trained at `imgsz=1280` on whole frames;
   validation mAP50 was 0.991 and the model was useless in production, because
   inference on a 200×200 tile put every object far outside the learned size
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
   than the colour scenes. Splitting into 18 classes was considered and rejected on
   measurement: mAP50 of 0.958 on keys with a shared vocabulary beats what 9-class
   keys could learn from a sixth of the data. *Cost: a week of experiments to prove
   the negative.*
5. **Silent rescaling.** A resized input mis-slices every tile and degrades the
   answer with no error. **Fix:** a hard geometry assertion at the entry to the
   pipeline, plus a test that asserts it fires.
6. **Ambiguous inputs by construction.** Two candidates can legitimately score
   identically. Rather than tune the score until ties vanish, ties became an
   explicit, first-class action (`recycle`). *Cost: none — this one was a design
   win.*
7. **A negative result on the headline design claim.** The 10:1 penalty asymmetry
   turned out to be unidentifiable on the evaluation set: a symmetric 1:1 score also
   reaches 48/48. **Response:** reported as a finding (§4.4 of the report) rather
   than tuned away, and the asymmetry re-justified from the measured one-sided
   noise profile. *Cost: the loss of the project's most quotable result.*

## What was deliberately NOT done

- **No GUI.** The assignment allows terminal output, and a GUI would not
  demonstrate anything about the algorithm.
- **No tuning on the evaluation set.** The 0.4 confidence floor is the only value
  selected with those strips in view, and the report says so — the honest
  generalisation claim is "≥92.6%", not "100%".
- **No model ensembling.** A second model would add 20 MB and latency for a
  bottleneck the ceiling decomposition proves is not accuracy-limiting.
