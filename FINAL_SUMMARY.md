# Final submission summary

**Author:** Jordan Moore
**Repository:** https://github.com/lilromeoz00/captcha
**Submitted version:** https://github.com/lilromeoz00/captcha/tree/final
**Report:** `CS471_Final_Report.pdf` (5 pages, repository root)

---

## Summary

This submission comprises a working AI agent that solves an adversarial visual
access-control challenge, together with a complete experimental evaluation of its
performance.

**Algorithm.** The challenge is a single 1600×400 frame containing eight candidate
scenes and a grayscale silhouette of a different object set. Access is granted only
if the selected scene's object counts reproduce the silhouette's counts exactly. The
problem is therefore one of multiset matching rather than classification: a scene
containing three onions and one potato is incorrect when the key specifies two
onions and two potatoes, even though every object was correctly detected. Each
candidate is scored using an asymmetric penalty of 10 for an unaccounted key object
and 1 for a surplus object, and the agent abstains when the two highest scores are
equal.

**Baselines.** Six baselines were evaluated on identical cached detector output, so
that differences between systems reflect the decision rule rather than differences
in training. These are: random selection (12.5%, averaged over 1,000 trials),
invariant selection of the first candidate (18.8%), classical histogram matching
(12.5%), YOLO with a count-based rule (20.8%), YOLO with a confidence-based rule
(25.0%), and the complete pipeline with a symmetric penalty (100%).

**Quantitative results.**

| Metric | Value |
|---|---|
| Task accuracy, 48 hand-labelled challenges | 48/48 = 100%, Wilson 95% CI [92.6, 100.0] |
| Comparison with strongest non-matching baseline | 36 corrected, 0 regressed, McNemar p = 2.9×10⁻¹¹ |
| Object recall, 288 held-out tiles | 99.0% (1132/1143) |
| Object precision | 97.9% |
| mAP50 | 0.983 |
| Expected calibration error | 0.127 |
| Oracle ceiling exploited | 39/39 = 100% |
| Median localisation IoU | 0.895 |
| Accuracy at Gaussian blur, radius 2.0 | 64.6% |

**Analysis.** Accuracy was decomposed into an oracle ceiling, defined as the frames
on which some candidate exactly reproduced the key, and the proportion of that
ceiling realised by the ranking stage. The ranking stage realised 100%, so decision
making is not the limiting component. Two findings qualify the design and are
reported accordingly. The penalty asymmetry is not identifiable on this data: a
symmetric 1:1 penalty also achieves 48/48, so the value of 10 is justified by the
measured one-sided error distribution (99.0% recall against 2.1% false-positive
leakage) rather than by a measured optimum. The confidence threshold, by contrast,
is identifiable, with an interior optimum at 0.40. The dominant failure mode is
input degradation rather than adversarial imagery: Gaussian blur at radius 2.0
reduces accuracy to 64.6%, because fixed 200-pixel tiling mis-segments a degraded
frame without raising an error. The operational implication is that link quality and
relay compression, rather than the adversary's countermeasures, determine
reliability.

**Reproducibility.** The repository contains 80 automated tests, the trained
weights, and all evaluation data. The report is generated from
`results/experiments.json`, so it cannot diverge from the code. Four commands
regenerate every reported value; none requires training.

---

## Contributions

Solo submission. The author performed all work: problem definition and tactical
analysis; capture and curation of six dataset generations; annotation of all
grayscale key tiles; detector training and evaluation; error decomposition and
threshold selection; the scoring function, abstention policy and agent loop; the
experiment harness, all six baselines, the metrics implementation and the report
generator; the test suite; and the documentation.

## AI use

The code was developed with the assistance of an AI coding assistant. The author can
explain and defend every module. The algorithm, the measurement methodology and all
reported values derive from the author's own data and experiments. The report
distinguishes measured results from design intent, and Section 4.4 reports an
ablation that the data cannot identify rather than asserting a fit.

---

## Mapping to the grading criteria

| Criterion | Points | Location |
|---|---|---|
| Algorithmic correctness and understanding | 40 | `solver/multiset.py`, `docs/ALGORITHM.md`, report §2, 17 unit tests |
| Complete functional MVP | 25 | `solver/` command-line interface; annotated output |
| Experimental design and baseline | 25 | `experiments/baselines.py`, report §3, Table 1, Figure 1 |
| Quantitative performance analysis | 30 | report §4, Tables 2–3, Figures 2–7 |
| Testing and reproducibility | 15 | 80 tests, data included, four-command regeneration |
| Documentation and limitations | 15 | report §5, `README.md`, `PROGRESS.md`, `docs/` |
