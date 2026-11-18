# CS471 Final Submission — summary for Blackboard

**Repository:** https://github.com/lilromeoz00/captcha
**Submitted version:** https://github.com/lilromeoz00/captcha/tree/final  (tag `final`)
**Report:** `CS471_Final_Report.pdf` (5 pages, in the repository root)

---

## What we submitted

A working AI agent that defeats an adversarial visual access-control challenge, plus
a full experimental analysis of it. The agent is a single-stage CNN detector feeding
a decision-theoretic multiset-matching layer with an explicit abstain action.

**Algorithm.** The challenge is one 1600×400 frame: eight candidate scenes plus a
grayscale silhouette of a *different* object set. The gate opens only if you pick the
scene whose object **counts** exactly reproduce the silhouette's. That is bag
matching, not classification — a scene with three onions and one potato is wrong when
the key asks for two and two, even though every object was detected correctly. We
score each candidate with an asymmetric penalty (α=10 for a key object left
unaccounted for, β=1 for a surplus object), rank, and **abstain** when the top two
tie, because recycling for a fresh challenge strictly dominates a coin flip.

**Baseline comparison.** Six baselines on identical cached detector output, so
differences attribute to the decision rule rather than to a differently trained
model: random (12.5%, 1,000 trials), always-basket-0 (18.8%), classical CV histogram
matching (12.5%), YOLO + most objects (20.8%), YOLO + max confidence (25.0%), and the
full pipeline with a symmetric 1:1 penalty (100%).

**Quantitative results.**

| metric | value |
|---|---|
| Task accuracy, 48 hand-labelled challenges | **48/48 = 100%**, Wilson 95% CI [92.6, 100.0] |
| vs strongest non-matching baseline | 36 fixed, 0 broken, exact McNemar p = 2.9e-11 |
| Object recall, 288 held-out tiles | 99.0% (1132/1143), precision 97.9% |
| mAP50 | 0.983 |
| Expected Calibration Error | 0.127 (0.4–0.5 band is 25% accurate → justifies the 0.4 floor) |
| Oracle ceiling exploited by the ranker | 39/39 = 100% |
| Median localisation IoU on true positives | 0.895 |

**Analysis and limitations.** We decomposed accuracy into an oracle ceiling
(strips where an exact match existed at all) and exploitation (whether the ranker
took it): the ranker converts 100% of available information, so the decision layer is
not the bottleneck. Two findings cut against our own design and are reported as such.
First, the **penalty asymmetry is not identifiable** on this data — a symmetric 1:1
score also reaches 48/48, so we justify α=10 by the measured one-sided noise profile
(99.0% recall vs 2.1% false-positive leakage) rather than by a measured optimum. The
confidence floor *is* identifiable, with a genuine interior optimum at 0.40. Second,
the dominant failure mode is **input degradation, not adversarial imagery**: Gaussian
blur at radius 2.0 drops accuracy to 64.6%, because fixed 200-pixel tiling mis-slices
a degraded frame silently. Operationally that means link quality and relay
compression are the binding constraint, which is more actionable than a higher
benchmark number would have been.

**Reproducibility.** 80 automated tests (32 of which need no GPU and no weights),
weights and all evaluation data in the repository, and the report PDF is *generated*
from `results/experiments.json` so it cannot drift from the code. Five commands
regenerate everything; none requires training.

---

## Grading rubric map

| criterion | pts | where |
|---|---|---|
| Algorithmic correctness & understanding | 40 | `solver/multiset.py` (the algorithm, pure Python), `docs/ALGORITHM.md`, report §2, 17 unit tests |
| Complete functional MVP | 25 | `solver/` CLI: `solve`, `eval`, `selftest`; annotated visual output |
| Experimental design & baseline | 25 | `experiments/baselines.py`, report §3, Table 1, Figure 1 |
| Quantitative performance analysis | 30 | report §4 (Tables 2–3, Figures 2–7), ceiling decomposition, ablations, McNemar tests |
| Testing & reproducibility | 15 | 80 tests, data in repo, 5-command regeneration |
| Documentation & limitations | 15 | report §5, `README.md`, `PROGRESS.md`, `docs/` |

## Contributions

**[TEAMMATE NAME]** — test suite (80 tests) and the geometry/validation layer with
its hard 1600×400 gate; evaluation reporting (Wilson intervals, ceiling
decomposition, margin tables); CLI annotated output; ran the confidence and penalty
ablations.

**Jordan Moore** — problem framing and tactical analysis; captured and curated six
dataset generations and hand-labelled all grayscale key tiles; trained and evaluated
the detector; TIDE error decomposition and confidence-floor selection; authored the
scoring function, abstain policy, the experiment harness, and the report.

**AI use disclosure.** The code was developed with the assistance of an AI coding
assistant, and we can explain and defend every module. The algorithm, measurement
methodology, and every reported number come from our own data and experiments. The
report distinguishes measured results from design intent, and §4.4 explicitly reports
an ablation our data *cannot* identify rather than claiming a fit.
