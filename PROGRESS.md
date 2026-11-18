# Project status and contributions

**Author:** Jordan Moore
**Scope:** solo submission. All work described below was carried out by the author.

---

## 1. Objective

To implement and evaluate an AI agent that solves an adversarial visual
access-control challenge, and to quantify its performance against established
baselines on hand-labelled data. The tactical motivation and the responses to the
project design worksheet are given in [`docs/TACTICAL_FRAMING.md`](docs/TACTICAL_FRAMING.md).

## 2. Completed work

- Perception pipeline: frame segmentation into nine fixed tiles, batched detector
  inference, and reduction of each tile to a class multiset.
- Decision layer: asymmetric multiset scoring, ranking, margin computation, and an
  abstention policy. Implemented without third-party dependencies.
- Command-line interface with three subcommands (`solve`, `eval`, `selftest`) and
  meaningful exit codes.
- Annotated output: the selected scene and per-scene scores are rendered onto the
  source frame.
- Evaluation programme: six baselines, per-class detection metrics, calibration
  analysis, confusion matrix, two hyperparameter ablations, and a ten-condition
  robustness sweep.
- Test suite of 80 automated tests, of which 64 require neither a GPU nor the model
  weights.
- Technical report of five pages, generated programmatically from the experiment
  output.

## 3. Results

| Measurement | Value |
|---|---|
| Task accuracy, 48 hand-labelled challenges | 48/48 = 100%, Wilson 95% CI [92.6, 100.0] |
| Strongest baseline without the matching layer | 25.0% |
| Classical computer-vision baseline | 12.5% |
| Object recall, 288 held-out tiles | 99.0% (1132/1143) |
| Object precision | 97.9% |
| mAP50 | 0.983 |
| Expected calibration error | 0.127 |
| Oracle ceiling exploited | 39/39 = 100% |
| Accuracy at Gaussian blur, radius 2.0 | 64.6% |

The decision layer converts all available information: on the 39 frames where some
scene exactly reproduced the key, the correct scene was selected 39 times. Residual
error is attributable to perception rather than to ranking.

## 4. Work not completed

The following were considered and deliberately excluded, or remain open:

1. **Larger evaluation set.** At n = 48 the confidence interval spans approximately
   seven percentage points. A set of roughly 300 frames would permit narrower claims.
2. **Independent test set.** The confidence threshold was selected with the current
   evaluation frames in view, so the reported accuracy is optimistic. An independent
   set would allow an unbiased estimate.
3. **Live-session integration.** The agent operates on saved frames. The loop that
   retrieves a challenge and submits an answer is outside the scope of this
   submission, so end-to-end latency and any rate-limiting behaviour are unmeasured.
4. **Coverage of two classes.** Green pepper and carrot do not appear as key classes
   in the evaluation set, so behaviour on keys containing them is untested.

## 5. Contributions

Solo submission. The author carried out all of the following:

problem definition and tactical analysis; capture and curation of six dataset
generations; hand-annotation of all grayscale key tiles; detector training and
evaluation; error decomposition and threshold selection; the scoring function,
abstention policy and agent loop; the experiment harness, all six baselines, the
metrics implementation and the report generator; the test suite; and the
documentation.

## 6. Issues encountered

1. **Object scale mismatch.** An early model trained on whole frames at high
   resolution reported validation mAP50 of 0.991 but performed poorly in
   deployment, because inference on a 200×200 tile placed objects outside the
   learned scale distribution. The tile size is now fixed at both training and
   inference time, and a size assertion rejects non-conforming input.
2. **Ineffective fine-tuning.** Fine-tuning from a previous checkpoint terminated
   with its best score at epoch 1. Inspection by file hash showed that 798 of 1,150
   training images were byte-identical to images the previous model had already
   trained on for 200 epochs. The final model was trained from COCO weights.
3. **Lost annotation provenance.** The annotation tool stored tight per-class crops
   without recording their source coordinates, rendering 332 completed annotations
   unusable for detector training. The coordinates were recovered exactly by
   normalised cross-correlation template matching; 787 crops matched at a score of
   at least 0.998.
4. **Two visual domains.** The grayscale key is rendered in a materially different
   style from the colour scenes. Separate class spaces were evaluated and rejected:
   a shared nine-class vocabulary achieved AP50 of 0.958 on the key domain, which a
   split vocabulary trained on one sixth of the data would be unlikely to match.
5. **Ambiguous input.** Two candidates can receive identical scores by construction.
   Rather than tune the scoring function until such cases disappear, abstention was
   made an explicit action.
6. **Unsupported design claim.** The 10:1 penalty asymmetry proved unidentifiable on
   the evaluation set, since a symmetric penalty also achieves 48/48. The result is
   reported in Section 4.4 of the report and the asymmetry is justified by the
   measured one-sided error distribution rather than by a measured optimum.

## 7. Excluded by design

- No graphical interface. The assignment permits terminal output, and an interface
  would not demonstrate anything about the algorithm.
- No tuning against the evaluation set beyond the confidence threshold, which is
  disclosed in the report.
- No model ensemble. The error decomposition shows that perception, not capacity, is
  the limiting factor, so a second model would add cost without addressing it.
