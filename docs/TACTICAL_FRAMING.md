# Project design: operational framing and worksheet responses

**Author:** Jordan Moore

This document records the operational motivation for the project and answers
questions 1–5 of the project design worksheet. The technical content is identical to
that of [`ALGORITHM.md`](ALGORITHM.md); only the framing differs.

---

## Operational context

Data collection against defended network services is constrained less by
cryptographic controls than by interactive challenges that distinguish human from
automated clients. The most widely deployed of these is the visual challenge, in
which a client must correctly interpret an image before access is granted. The
challenge family examined in this project is among the more robust variants in
current use and among the more expensive to defeat commercially.

The prevailing commercial approach is manual labour arbitrage: challenges are
distributed to low-wage workers for solution at approximately $2 per 1,000 items.
This approach has three deficiencies that limit its military utility.

| Property | Current practice | Operational consequence |
|---|---|---|
| Latency | human-bound, seconds to minutes | unsuitable for time-sensitive collection |
| Reliability | approximately 10% | not a dependable capability |
| Dependency | an external workforce that cannot be audited or scaled on demand | the target set is disclosed to a third party |

The third deficiency is the most significant and is a security property rather than
a cost consideration. A locally hosted model removes it.

## Alignment with the project archetype

The project corresponds to the Deep Learning (CNNs) row of the ideation matrix, in
the intelligence, surveillance and reconnaissance application area:

> A convolutional neural network trained to classify overhead satellite imagery,
> with emphasis on preventing false positives.

The structural correspondence is close. In both cases a convolutional network must
convert degraded, non-cooperative imagery into a discrete inventory of objects, and
in both cases the operationally costly error is the false positive rather than the
missed target. The project substitutes challenge tiles for overhead imagery and
object counting for vehicle counting. The measurement problem, namely the
relationship between precision and recall and the relative cost of each error,
carries over directly and is quantified in Sections 4 and 7 of
[`ALGORITHM.md`](ALGORITHM.md).

---

## Question 1: the operational problem

Automated collection against a defended target terminates at the adversary's
challenge layer. The specific challenge is served as a single 1600×400 image
containing eight candidate scenes across the upper region and a grayscale silhouette
in the lower left. The silhouette depicts a different set of objects. Access is
granted if and only if the client selects the scene whose object counts exactly
reproduce those of the silhouette.

The difficulty is that the answer depends on counts per class rather than on
recognition of individual objects:

```
key    = {onion: 2, potato: 2}
scene  = {onion: 2, potato: 1, corn: 1}    # incorrect; every object detected correctly
```

A classifier with high per-object accuracy can therefore perform poorly on the
composite task, because errors accumulate across four objects and eight candidates.
This was measured: a two-stage pipeline of cropping and classification achieved 73%
accuracy, whereas a single detector reasoning jointly achieved 83% on the same data
with less training data.

The operational requirement is to defeat this control without depending on an
external workforce to which the collection target would be disclosed.

## Question 2: the environment model

**Observation.** A single 1600×400 image, partitioned by construction into nine
fixed tiles:

```
tiles 0..7  (upper row)     eight candidate scenes, 200x200 each, four objects each
tile  S     (lower left)    the key: grayscale silhouette of four objects
```

The observation is partially informative because the detector is imperfect, and the
imperfection is asymmetric. On 288 held-out tiles, recall is 99.0% while
false-positive leakage is approximately 1%. The environment therefore removes objects
from the observation considerably more often than it introduces them, and the
decision layer is constructed around this measured asymmetry.

**State.** The state is the pair (K, B₀…B₇) of multisets over a fixed nine-class
vocabulary, each containing at most four items. It is fully observed given the
detector, so all uncertainty is perceptual. This is why the evaluation separates
perception error from decision error rather than reporting a single combined
accuracy.

**Actions.** The action space is selection of one of the eight candidates, or
abstention, which abandons the current challenge and requests a new one without
submitting an answer.

**Reward.** One for a correct answer, zero for an incorrect answer, and zero for
abstention. The last value is the load-bearing design choice: because abstention
consumes no attempt, it strictly dominates an indeterminate guess, which carries the
same downside. The agent is therefore rewarded for recognising its own uncertainty, a
property a classifier with a softmax output cannot express.

**Output.** A selected index and a machine-readable confidence value, namely the
difference between the highest and second-highest scores. This permits the system to
be operated in a precision-oriented mode, in which high-confidence answers are
accepted automatically and the remainder are escalated.

## Question 3: the algorithm

The system has two stages, distinguished here because a reviewer will ask which
component is learned.

**Learned perception.** A single-stage convolutional detector (YOLO26s,
approximately 9.5M parameters) trained from COCO weights on 1,604 hand-labelled
200×200 tiles containing 6,353 bounding boxes. Six source sets are fully annotated
grayscale silhouette tiles. The two visual domains deliberately share one nine-class
vocabulary, so that the more abundant colour data can supply shape priors that the
scarce silhouette data could not support alone. The measured result is AP50 of 0.958
on the silhouette domain and 1.000 on the colour domain from a single shared label
space. A split 18-class vocabulary was evaluated and rejected on this evidence.

**Decision theory over multisets.** For key K and candidate B, both multisets over
the nine classes:

```
score(K, B) = −( 10 · Σc max(0, K[c] − B[c])  +  Σc max(0, B[c] − K[c]) )
```

- **Asymmetric penalty.** The coefficient 10 weights an unaccounted key object, the
  error the detector actually makes at a rate of 0.8%, ten times more heavily than a
  surplus object, the error it makes at a rate of approximately 1%. This makes the
  score a log-likelihood ratio under the measured noise model rather than a
  symmetric distance.
- **Exact greedy solution.** Because the cost is linear in counts, the number of key
  objects satisfied by a candidate is min(K[c], B[c]) per class. No assignment
  problem arises. The cost is O(9) per candidate.
- **Marginal policy with abstention.**

```
a* = argmax_i score(K, B_i)   if margin > 0
a* = abstain                  if margin = 0
```

**Why not end-to-end reinforcement learning.** The generative process of the
environment is known and inexpensive to model: nine multisets of four items. The
optimal decision rule therefore has a closed form. Learning a policy would introduce
variance, remove interpretability, and make the abstention behaviour unprovable,
which is the one behaviour most in need of proof. The design learns the component
with irreducible uncertainty and derives the component without it.

## Question 4: the baseline

A terminal application with no graphical interface and no network dependency. This
checkpoint submission comprises three commands:

```powershell
python -m solver selftest
python -m solver solve data/strips/strip_0000.jpg --annotate out.jpg
python -m solver eval --report reports/eval_report.md --min-acc 0.85
```

| Command | What it establishes |
|---|---|
| `selftest` | the scoring function is correct independently of the model: an exact match scores 0, one missing object −10, one surplus object −1 |
| `solve` | the pipeline executes end to end on a representative scenario and produces observable output, including an annotated image |
| `eval` | the agent is scored against 48 hand-labelled challenges and returns a non-zero exit code if accuracy falls below a threshold |

The deliverable is intentionally minimal. The assessment concerns the algorithm
rather than the interface.

## Question 5: the evaluation metric

Four measurements, each addressing a distinct question.

**1. Task accuracy with a confidence interval.** 48/48, or 100%, with a Wilson 95%
confidence interval of [92.6, 100.0], against a 10% human-labour baseline. The
interval is reported because n = 48 is small. The defensible claim is that accuracy
is at least 92.6% with 95% confidence, and the expected accuracy on previously
unseen challenges is approximately 93% to 98% rather than 100%.

**2. Object-level recall.** 1134 of 1143, or 99.2%, of annotated objects detected on
288 held-out tiles. This measures the detector independently of the decision layer.

**3. Oracle ceiling decomposition.** This separates the two failure modes.

| Quantity | Measured | Interpretation |
|---|---|---|
| Ceiling available | 39/48 = 81.2% | frames on which some candidate exactly reproduced the key |
| Ceiling exploited | 39/39 = 100% | proportion of those frames on which the policy selected correctly |

A low ceiling indicates that perception is limiting. A high ceiling with low
exploitation indicates that the decision rule is limiting. The measured result is
that the decision rule converts all available information, which establishes that
the algorithm, and not merely the model, operates as intended.

**4. Ablation.** The confidence threshold exhibits an interior optimum.

| Threshold | 0.20 | 0.30 | 0.40 | 0.50 | 0.60 |
|---|---|---|---|---|---|
| Accuracy | 97.9% | 97.9% | 100% | 97.9% | 93.8% |

Accuracy decreases on both sides of the optimum, which is characteristic of a genuine
effect. A lower threshold admits background texture into the multiset; a higher
threshold removes dim but genuine objects from the key.

Additional measurements planned for the final submission comprise a nine-class
confusion matrix and per-class precision-recall curves, training convergence curves,
and a robustness sweep. Preliminary robustness results show that half-resolution
input reduces accuracy by 12.5 percentage points, indicating that degraded transport
conditions rather than adversarial imagery constitute the principal practical risk.

## Operational implications

1. The 10% human baseline is a delay rather than a capability. A pipeline costing
   $2 per 1,000 items, operating at human latency and succeeding at 10%, is
   restricted to bulk collection where minutes are immaterial. Automation at
   benchmark accuracy and millisecond latency changes the range of missions the
   capability can support, not merely its unit cost.
2. The external dependency is the principal vulnerability. Renting human solvers
   discloses the target set to a third party. A locally hosted model does not, and
   this is a security property rather than an economic one.
3. Confidence gating enables safe automation. Because the agent reports a margin, it
   can be configured for precision and the escalation rate can be computed before
   deployment. A system that cannot abstain cannot be operated unattended.
4. The measured limitation is not model capacity, since missed detections are
   negligible, but the availability of labels in the degraded visual domain. The
   effective counter to a system of this kind is therefore not a more difficult
   puzzle but one whose rendering changes faster than labels can be collected.

## Scope

This is a research exercise against a challenge family. It is not directed at any
live target. All evaluation imagery was collected and annotated by the author. The
repository contains no credentials, session material, or live-endpoint code; the
agent operates on saved frames only. The contribution assessed here is the
decision-theoretic layer and its measurement methodology, both of which are
domain-general: the same asymmetric scoring and abstention structure applies to any
noisy sensor supplying a discrete inventory task.
