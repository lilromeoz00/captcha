# Checkpoint progress summary

**CS471 Final Project — Lesson 36 (Ugly but Functional)**

**Repository:** https://github.com/lilromeoz00/captcha  ·  **Submitted version:** https://github.com/lilromeoz00/captcha/tree/checkpoint

## What is complete

In the modern age, data is gold. The best data sits behind hard-to-reach places,
making it expensive and difficult to obtain — and one of the most popular
anti-collection techniques defending it is the CAPTCHA. The hardest, best
maintained, and most expensive member of that family is the FunCaptcha-class
"match the objects by count" challenge. Today it is beaten by manual labour
arbitrage: roughly **$2 per 1,000 solves**, human-latency bound, about **10%**
reliable because families rotate faster than workers retrain, and dependent on an
external population that learns your target set. Nothing automated, nothing fast.

We automated it and measured the result. The challenge is one 1600×400 frame —
eight candidate scenes plus a grayscale silhouette of a *different* object set —
and the gate opens only if you pick the scene whose object **counts** exactly
reproduce the silhouette's. That is decision-theoretic bag matching, not
classification: a scene with three onions and one potato is wrong when the key asks
for two and two, even though every object was detected correctly. We implement it
as a YOLO26s detector feeding an asymmetric multiset score (10:1 penalty on missing
key items versus surplus ones), with an explicit **abstain** action when the top
two candidates tie — recycling for a fresh challenge strictly dominates a
coin-flip guess, which is a behaviour a softmax classifier cannot express.

**Measured:** **48/48 = 100%** task accuracy on 48 hand-labelled challenges
(Wilson 95% CI [92.6, 100.0]) against the 10% human baseline; **99.2%** object
recall against human boxes on 288 held-out tiles; and an oracle decomposition
showing the decision rule exploits **39/39** available exact matches, which proves
the algorithm — not merely the model — is correct. 48 automated tests pass, and the
core math runs with no GPU.

## Remaining work

Scale evaluation to ~300 challenges to narrow the interval; add confusion matrix,
PR curves, and training convergence plots; robustness sweep (preliminary:
half-resolution costs −12.5 points, making degraded relay conditions the real
threat); wire the solver to a live session loop; build the tactical analysis
section for the Lesson 41 defence.

## Contributions

**Solo submission.** Jordan Moore is the only team member; every component below was
authored by him, so the split is 100% / 0%.

**Jordan Moore** — problem framing and tactical analysis; capture and curation of six
dataset generations; hand-labelling of all grayscale key tiles; detector training and
evaluation; TIDE error decomposition and confidence-floor selection; the scoring
function, abstain policy and agent loop; the test suite; both design documents.

**Challenges.** Three are worth naming. (1) A model trained at `imgsz=1280` on
whole frames reported val mAP50 of 0.991 and was useless in production, because
inference on a 200×200 tile put every object outside the learned scale
distribution. (2) Fine-tuning failed outright — best epoch was epoch 1 — because
MD5 showed 69% of the "new" images were byte-identical to what the previous model
had already trained on for 200 epochs. (3) An annotation tool that wrote crops
without recording their source coordinates made 332 finished labels unusable; we
recovered them exactly by normalised cross-correlation template matching (787
crops, all ≥0.998).

**AI use disclosure.** Per the assignment's AI policy: the code was developed with
the assistance of an AI coding assistant, and we can explain and defend every
module. The algorithm, the measurement methodology, and every number reported above
come from our own data and experiments; the write-ups distinguish measured results
from design intent, and §7.2 of `docs/ALGORITHM.md` explicitly reports an ablation
our data *cannot* identify rather than claiming a fit.
