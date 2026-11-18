# Algorithm documentation

All values reported in this document are measured on the data included in this
repository. Each table can be regenerated using the commands in Section 9.

---

## 1. Problem formulation

The input is a single 1600×400 image with a fixed internal layout:

```
+--------+--------+--------+--------+--------+--------+--------+--------+
|scene 0 |scene 1 |scene 2 |scene 3 |scene 4 |scene 5 |scene 6 |scene 7 |   y = 0..200
+--------+--------+--------+--------+--------+--------+--------+--------+
|  KEY   |                (unused)                                      |   y = 200..400
+--------+--------+--------+--------+--------+--------+--------+--------+
```

Each scene contains exactly four objects. The key is a grayscale silhouette render
of four objects, presented in a different visual domain from the colour scenes.

The task is to select the scene whose object counts are identical to the key's:

```
K = {onion: 2, potato: 2}
B = {onion: 2, potato: 1, corn: 1}    # incorrect, although every object was detected
```

Because the answer depends on counts, the appropriate representation is a multiset
rather than a class label. This is the property that distinguishes the task from
classification.

## 2. State, action and reward

| Element | Definition |
|---|---|
| Observation | nine 200×200 tiles; each reduced to a multiset of detected classes |
| State | the nine multisets (K, B₀…B₇), each containing at most four items |
| Action | selection of one of the eight scenes, or abstention |
| Reward | +1 correct, 0 incorrect, 0 for abstention |
| Policy | deterministic argmax of the score, with abstention on a tie |

The state is fully observed given the detector, so uncertainty is entirely
perceptual. This motivates the decomposition described in Section 6.

## 3. Perception

**Architecture.** YOLO26s, a single-stage detector with approximately 9.5M
parameters and 20.8 GFLOPs, trained from COCO weights.

**Choice of detector over a classification pipeline.** An earlier two-stage
approach, cropping each object and classifying it with separate colour and grayscale
classifiers, achieved 73% task accuracy. A single detector performing localisation
and classification jointly achieved 83% on the same data with less training data.
Sharing one class vocabulary across two visual domains produced a better joint
representation than two narrow specialists.

**Fixed input scale.** The tile size is 200×200 at both training and inference, with
`imgsz=320`. An earlier version trained on whole frames at `imgsz=1280` and reported
validation mAP50 of 0.991 while performing poorly in deployment, because inference on
a 200×200 crop placed every object outside the learned scale distribution. Training
and inference tile size must be identical.

**Reduction to multisets.** Detected boxes are reduced to a count per class. The key
is truncated to its four most confident detections, since it provably contains four
objects and any additional detection is a duplicate or background response. Scenes
are not truncated, because surplus objects are genuine evidence against a candidate.

Measured perception quality on 288 held-out tiles against human annotations:

| Metric | Value |
|---|---|
| Recall | 1132/1143 = 99.0% |
| Precision | 97.9% |
| mAP50 | 0.983 |
| Expected calibration error | 0.127 |
| Median localisation IoU | 0.895 |

The residual error is predominantly surplus detections rather than missed objects,
which is the asymmetry the scoring function is designed to accommodate.

## 4. Scoring function

For key K and candidate B, both multisets over the nine classes:

```
score(K, B) = −( α · Σc max(0, K[c] − B[c])  +  β · Σc max(0, B[c] − K[c]) )
```

with α = 10 for an unaccounted key object and β = 1 for a surplus object.

| Case | Score |
|---|---|
| Exact match | 0 |
| One surplus object | −1 |
| One missing object | −10 |
| One class substituted for another | −11 |
| Empty candidate against a four-object key | −40 |

**Rationale for the asymmetry.** The two error types have different origins. A
missing object is a recall failure on the harder silhouette domain, and the
information it represents cannot be recovered downstream. A surplus object is
typically a duplicate detection or a background response, which the scoring function
can absorb. Weighting the unrecoverable error more heavily makes the score a
log-likelihood ratio under the measured noise model rather than a symmetric distance.

**Limitation.** On the evaluation set the accuracy is invariant across the full
range of ratios tested: 1:1 through 50:1 all achieve 48/48. The set is saturated and
therefore cannot identify the ratio. The value 10 is justified by the mechanism
described above and by unit tests that fix the required ordering, namely that a
missing object must rank below a surplus object. It is not justified by a measured
optimum, and Section 7.2 states this explicitly.

**Exactness of the greedy solution.** Because the cost is linear in counts, the
number of key objects satisfied by a candidate is min(K[c], B[c]) per class. No
assignment problem arises, and the cost is O(9) per candidate.

## 5. Decision rule

The eight candidates are ranked by score. The margin is the difference between the
highest and second-highest scores.

```
if margin > 0  ->  select the highest-scoring scene
if margin = 0  ->  abstain
```

**Rationale for abstention.** A margin of zero means that two candidates are
indistinguishable given the observation, so a selection is equivalent to a coin toss.
Because no attempt has been consumed, requesting a new challenge is weakly dominant.

Measured on the evaluation set: zero abstentions in 48 frames. The margin
distribution is concentrated at the values 11 and 22, corresponding to one and two
missing key objects.

| Margin | 1 | 10 | 11 | 12 | 22 | 23 |
|---|---|---|---|---|---|---|
| Frames | 2 | 4 | 25 | 2 | 14 | 1 |

## 6. Evaluation methodology

A single accuracy figure conflates two distinct failure modes, so the agent reports a
ceiling decomposition.

| Quantity | Definition |
|---|---|
| Ceiling | frames on which some candidate exactly reproduced the key; if none did, perception destroyed the information required |
| Exploitation | proportion of ceiling frames on which the ranking stage selected correctly |

Measured on 48 frames:

| Metric | Value |
|---|---|
| Task accuracy | 48/48 = 100%, Wilson 95% CI [92.6, 100.0] |
| Ceiling available | 39/48 = 81.2% |
| Ceiling exploited | 39/39 = 100% |
| Abstentions | 0 |

The ranking stage converts all available information. The nine frames without an
exact candidate were nonetheless answered correctly through partial scoring, which
indicates that the penalty structure produces a correct ordering even when
perception is lossy.

The confidence interval is reported because n = 48 is small. The appropriate reading
of 48/48 is that accuracy is at least 92.6% with 95% confidence.

## 7. Ablations

### 7.1 Confidence threshold

| Threshold | 0.20 | 0.25 | 0.30 | 0.35 | 0.40 | 0.45 | 0.50 | 0.55 | 0.60 |
|---|---|---|---|---|---|---|---|---|---|
| Accuracy | 97.9% | 97.9% | 97.9% | 97.9% | 100% | 97.9% | 97.9% | 97.9% | 93.8% |

A single interior optimum with degradation on both sides, which is characteristic of
a genuine effect. A lower threshold admits background texture; a higher threshold
removes dim but genuine objects from the key.

### 7.2 Penalty ratio

| Ratio (α:β) | 1:1 | 2:1 | 5:1 | 10:1 | 20:1 | 50:1 |
|---|---|---|---|---|---|---|
| Accuracy | 100% | 100% | 100% | 100% | 100% | 100% |

Accuracy is invariant across the range. The evaluation set cannot distinguish the
asymmetric score from a symmetric one, and no claim to the contrary is made. The
comparison with a symmetric penalty is therefore reported as a negative result in the
final report, Section 4.4.

### 7.3 Key truncation

| Maximum key objects | 3 | 4 | 5 | Unlimited |
|---|---|---|---|---|
| Accuracy | 47.9% | 100% | 97.9% | 97.9% |

Encoding the known cardinality of four is worth more than any tuning of the scoring
function. Truncating to three removes a genuine object; removing the truncation
admits a fifth low-confidence detection.

### 7.4 Abstention policy

Both policies are implemented and tested. With `recycle`, the agent abstains on a
tie; with `guess`, it selects the highest-scoring candidate. No tie occurs in the
evaluation set, so the two policies produce identical results there. The test suite
asserts that the switch alters the action without altering the analysis.

## 8. Complexity

Per frame: one batched forward pass over nine tiles, followed by 8 × O(9) integer
comparisons. Measured end to end on an NVIDIA RTX 3080: 48 frames in approximately
seven seconds including model load, corresponding to approximately ten frames per
second once loaded. The decision layer is negligible relative to perception, which is
why the algorithm is expressed as a scoring rule over detector output rather than as a
second learned model.

## 9. Reproducing the measurements

```powershell
python tests\run_all.py                                  # 80 tests
python -m solver eval --report reports\eval_report.md     # per-frame report
python -m solver selftest                                # scoring table, Section 4
python experiments\run_all.py                            # regenerates results\experiments.json
```

## 10. Anticipated questions

1. **Why a detector rather than a classifier?** Measured improvement from 73% to 83%
   on identical data with less training data, attributed to a shared class vocabulary
   across two visual domains.
2. **Why is the penalty asymmetric?** Recall failures are unrecoverable; precision
   failures are noise. The ratio itself is not identifiable on a saturated 48-frame
   set, and this is stated in Section 7.2.
3. **Why a confidence threshold of 0.40?** Interior optimum, Section 7.1.
4. **Why abstain rather than guess on a tie?** A tie is a coin toss; a new challenge
   is a strictly better use of an unspent attempt.
5. **Why report 100% rather than a range?** The figure is measured against 48
   hand-labelled answers, with a Wilson interval and an error decomposition. The
   defensible generalisation claim is at least 92.6% with 95% confidence.
6. **What remains?** The residual loss is localisation precision on the silhouette
   domain rather than recall. The next improvement requires additional annotated
   silhouette tiles, not a larger model.
