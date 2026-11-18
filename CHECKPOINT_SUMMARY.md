# Checkpoint submission summary

**Author:** Jordan Moore
**Repository:** https://github.com/lilromeoz00/captcha
**Submitted version:** https://github.com/lilromeoz00/captcha/tree/checkpoint

---

## Completed functionality

The project addresses a limitation on automated data collection: access to defended
services is frequently gated by a visual challenge rather than by cryptographic
controls. The challenge family examined here presents eight candidate scenes and a
grayscale silhouette of a different object set, and requires selection of the scene
whose object counts reproduce the silhouette exactly. The prevailing commercial
solution distributes these challenges to low-wage workers at approximately $2 per
1,000 items, with human latency, an approximate 10% success rate, and a dependency
on an external population to which the target set is disclosed.

The agent implemented here replaces that pipeline with a local computation. A
single-stage object detector (YOLO26s) processes nine fixed 200×200 tiles and
reduces each to a class multiset. Each candidate scene is then scored against the
key using an asymmetric penalty that weights an unaccounted key object ten times
more heavily than a surplus object, reflecting the measured one-sided error
distribution of the detector. The agent selects the highest-scoring scene, and
abstains when the two highest scores are equal, since no observation distinguishes
them and a new challenge can be requested at no cost.

Results on 48 hand-labelled challenges are 48/48, or 100%, with a Wilson 95%
confidence interval of [92.6, 100.0]. Object recall on 288 held-out tiles is 99.0%
and mAP50 is 0.983. An oracle decomposition shows that on the 39 frames containing a
scene that exactly reproduced the key, the ranking stage selected it 39 times,
indicating that residual error originates in perception rather than in decision
making. The test suite contains 48 automated tests at this stage, of which the
majority require neither a GPU nor the model weights.

## Remaining work

Evaluation at larger scale, to narrow the confidence interval; an independent test
set, since the confidence threshold was selected with the current frames in view; a
confusion matrix and per-class precision-recall analysis; a robustness sweep;
integration with a live session loop; and preparation of the final report.

## Contributions

Solo submission. The author performed all work: problem definition; capture and
curation of six dataset generations; annotation of all grayscale key tiles; detector
training and evaluation; error decomposition and threshold selection; the scoring
function, abstention policy and agent loop; the test suite; and the documentation.

## Issues encountered

Three are material. First, a model trained on whole frames at high resolution
reported validation mAP50 of 0.991 but performed poorly in deployment, because
inference on a 200×200 tile placed objects outside the learned scale distribution.
Second, fine-tuning from a previous checkpoint terminated with its best score at
epoch 1; inspection by file hash showed that 798 of 1,150 training images were
byte-identical to images the previous model had already trained on. Third, the
annotation tool stored crops without source coordinates, rendering 332 completed
annotations unusable; the coordinates were recovered exactly by normalised
cross-correlation template matching.

## AI use

The code was developed with the assistance of an AI coding assistant. The author can
explain and defend every module. The algorithm, the measurement methodology and all
reported values derive from the author's own data and experiments. The documentation
distinguishes measured results from design intent.
