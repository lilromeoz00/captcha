# Operational framing — Scoping Worksheet Q1–Q5

*The pitch, in our own words, with the measurements backing it.*

---

## The premise: data is gold, and the good data is walled off

In the modern age, **data is gold**. The most valuable data — the kind that decides
who wins an engagement before a shot is fired — does not sit in open APIs. It sits
behind hard-to-reach places: authenticated portals, rate-limited endpoints,
session-gated services. Collecting it is expensive, slow, and often illegal to do
by hand at scale.

To maintain an edge in cyberspace, Air Force cyber operations need tooling that
makes those barriers **non-problems** — not barriers that are merely expensive to
cross, but barriers that stop existing as barriers.

The single most popular anti-collection technique in that space is the **CAPTCHA**,
and its modern form is not a distorted word. It is a visual reasoning task served
as a gate: answer it, or no session. It is popular precisely because it is cheap to
serve and hard to automate — it exploits the one gap between machine perception and
human perception that is still wide enough to stand in.

**The strongest member of that family right now** — the hardest, the best
maintained, and the most expensive on the open market — is the FunCaptcha-class
challenge, in the "match the objects by count" configuration. If you can beat that
one, you can beat the rest of the family, because every weaker variant is a
degenerate case of it.

**How it is done today: with people.** The commercial answer is manual labour
arbitrage. A challenge is shipped to a low-wage human worker who answers it for a
fraction of a cent, at roughly **$2 per 1,000 solves**. That model has three
properties, and all three are disqualifying for a military application:

| property | reality | why it matters operationally |
|---|---|---|
| **speed** | human-latency, seconds to minutes | unusable for time-sensitive collection; this is a delay, not a capability |
| **reliability** | **~10%** correct, because challenge families rotate faster than workers retrain | a 90% failure rate is not a tool, it is a lottery ticket with a service contract |
| **dependency** | you are renting an external population you cannot audit, cannot surge, and which **learns your target set** | that is an OPSEC leak priced as a subscription |

Nothing about that pipeline is automated. Nothing about it is fast. And it stops
working the moment the adversary changes the picture.

**We solved it.** This project replaces that pipeline with a locally-hosted CNN
plus a decision-theoretic matching layer that runs in **milliseconds per
challenge**, requires **no human in the loop**, leaks nothing to a third party, and
measures **100% on our hand-labelled benchmark** (48/48, Wilson 95% CI
[92.6%, 100.0%]) — against a 10% human-labour baseline. Section Q5 gives every
number and its error bar.

---

## Archetype alignment (Ideation Matrix)

This sits on the **Deep Learning (CNNs) — ISR** row, adapted to cyber:

> *"A Convolutional Neural Network trained to classify overhead satellite imagery,
> focusing on preventing False Positives."*

The structural similarity is exact, not a stretch. In both cases a CNN must
convert degraded, non-cooperative imagery into a **discrete inventory of objects**,
and in both cases the operationally expensive error is the **false positive**, not
the missed target. We swap overhead imagery for a challenge tile and "count the
vehicles" for "count the objects". The measurement problem — precision against
recall, and which error actually costs the mission — carries over unchanged, and
§6–7 of [`ALGORITHM.md`](ALGORITHM.md) measure exactly that, including the
false-positive leak that turned out to be the thing to fix.

---

## Q1. The Operational Problem

Automated collection against a defended target stops at the adversary's challenge
layer, not at its cryptography. The challenge family we target is served as a
single **1600×400** image: eight candidate scenes across the top, and a
**grayscale silhouette** in the bottom-left showing a *different* set of objects.
The gate opens if — and only if — you pick the one scene whose object **counts**
exactly reproduce the silhouette's counts.

That last sentence is the whole difficulty, and it is why the naive solution
fails. The answer depends on **counts per class**, not on recognising objects:

```
key    = {onion: 2, potato: 2}
scene  = {onion: 2, potato: 1, corn: 1}    -> WRONG, and every object was detected correctly
```

A classifier that is 97% accurate per object can still be 60% accurate at the gate,
because the errors compound across four objects and eight candidates. We measured
this: a two-classifier crop-and-classify pipeline scored **73%**; a single detector
that reasons jointly scored **83%** on the same set with *less* training data.

**The warfighter's problem, stated plainly:** we need this gate to stop being a
gate, without renting a foreign workforce that tells the adversary what we are
collecting.

---

## Q2. The Environment Model

**Observation.** One 1600×400 image, partitioned by construction into a fixed
nine-tile layout:

```
tiles 0..7  (top row)      eight candidate scenes, 200x200 each, four objects each
tile  S     (bottom left)  the key: grayscale silhouette of four objects
```

The observation is **partially informative** because the sensor (the CNN) is
imperfect — and, critically, **asymmetrically** imperfect. Measured on 288
held-out tiles against human boxes: recall **99.2%**, false-positive leakage only
**~1%**. The environment can hurt us by *dropping* an object far more often than
by *inventing* one, and the entire decision layer is built around that measured
asymmetry rather than an assumed one.

**State.** `s = (K, B₀…B₇)`, nine bags over a fixed nine-class vocabulary, each
holding at most four items. Fully observed *given the detector*, so all uncertainty
is perceptual — which is exactly why the evaluation separates perception error from
decision error instead of reporting one blended accuracy number.

**Actions.** `a ∈ { answer(0) … answer(7), recycle }`, where `recycle` abandons the
current challenge and requests a fresh one **without submitting**.

**Reward.** +1 correct, 0 incorrect, and **0 for recycle**. That last zero is the
load-bearing choice: because recycling spends no attempt, it strictly dominates a
coin-flip guess with the same downside. The agent is therefore rewarded for
**knowing when it does not know** — a property no softmax classifier can give you,
and the thing that makes an automated system safe to leave running unattended.

**Output.** A cell index plus a machine-readable confidence (`margin`), so results
can be gated: high-margin answers fire automatically, low-margin ones escalate to
a human. In a contested environment that escalation path is the difference between
an auditable system and an opaque one.

---

## Q3. The Algorithm

Two stages. Stated separately, because a reviewer will ask which part is learned
and which part is derived.

**1. Learned perception — YOLO26s.** Single-stage CNN detector, ~9.5 M parameters,
20.8 GFLOPs, trained from COCO weights on **1,604 hand-labelled 200×200 tiles**
(6,353 boxes). Six of those sources are 100% hand-annotated grayscale silhouette
tiles — the two visual domains deliberately share **one nine-class vocabulary**, so
abundant color data teaches shape priors the scarce silhouette data could never
learn alone. Measured effect: mAP50 **0.958** on the silhouette domain and
**1.000** on color, from one shared label space. Splitting into 18 classes was
considered and rejected on measurement, not taste.

**2. The algorithm proper — decision theory over multisets.** This is the CS471
contribution, and the part that makes this an agent rather than an image
classifier:

```
score(K, B) = −( 10 · Σ_c max(0, K[c] − B[c])  +  Σ_c max(0, B[c] − K[c]) )
                └── missed key items ──┘         └── surplus items ──┘
```

- **Asymmetric penalty, 10:1.** It weights the error the sensor actually makes
  (dropping a real object, 0.8% of the time) ten times higher than the error it
  rarely makes (inventing one, ~1% leakage). This turns the score into a
  log-likelihood ratio under the *measured* noise model instead of a symmetric
  Hamming distance chosen for convenience.
- **Exact greedy solution.** Because cost is linear in counts, the number of key
  items a candidate satisfies is `min(K[c], B[c])` per class — no assignment
  problem, no Hungarian algorithm, O(9) per candidate.
- **Marginal policy with an abstain action.**

$$a^* = \begin{cases}\arg\max_i \text{score}(K,B_i) & \text{if margin} > 0\\ \text{recycle} & \text{if margin} = 0\end{cases}$$

**Why not end-to-end RL?** Because the environment's generative process is known
and cheap to model — nine bags of four items. The optimal decision rule has a
closed form here. Learning a policy would add variance, destroy interpretability,
and make the abstain behaviour unprovable, which is the one behaviour we most need
to be able to prove. Learn the part with irreducible uncertainty; derive the part
without it.

---

## Q4. The Baseline — the four-lesson MVP

Terminal-only, no GUI, no network. Three commands, which is what this checkpoint
ships:

```powershell
python -m solver selftest                                        # the scoring math, 0.01 s
python -m solver solve data/strips/strip_0000.jpg --annotate out.jpg
python -m solver eval --report reports/eval_report.md --min-acc 0.85
```

| command | what it proves |
|---|---|
| `selftest` | the scoring function is correct **independent of the model**: exact = 0, one miss = −10, one surplus = −1. The algorithm exists on its own. |
| `solve` | the pipeline runs a representative scenario end to end and shows its work — decision plus an annotated image of *why*. |
| `eval` | the agent is scored against 48 human-labelled challenges and exits non-zero if accuracy drops. That is a correctness check, not a demo. |

The deliverable is deliberately ugly: stdout, an exit code, a JPEG. The milestone
grades the algorithm.

---

## Q5. The Evaluation Metric

Four measurements, each answering a different question a reviewer will ask.

**1. Task accuracy, with a confidence interval.** **48/48 = 100%**, Wilson 95% CI
**[92.6%, 100.0%]** against a 10% human baseline. We report the interval because
n = 48 is small: the defensible claim is *"≥92.6% with 95% confidence, versus 10%
for the commercial human pipeline"* — and the honest expectation on fresh,
unseen challenges is ~93–98%, not 100%. A point estimate without an interval is
not a result.

**2. Object-level recall.** **1134/1143 = 99.2%** of hand-labelled objects found on
288 held-out tiles. This measures the sensor independently of the decision layer.

**3. Oracle ceiling decomposition — the decisive one.** This separates the two ways
the agent can fail:

| quantity | measured | meaning |
|---|---|---|
| ceiling available | 39/48 = 81.2% | strips where *some* candidate exactly reproduced the key |
| **ceiling exploited** | **39/39 = 100%** | of those, how many the policy actually picked |

Low ceiling means perception is the bottleneck. High ceiling but low exploitation
means the decision rule is. Measured: **the decision rule converts every available
signal perfectly** — which is what proves the *algorithm* works, not merely that a
model was trained.

**4. Ablation curve, one of which is genuinely identifiable.**

| confidence floor | 0.20 | 0.30 | **0.40** | 0.50 | 0.60 |
|---|---|---|---|---|---|
| accuracy | 97.9% | 97.9% | **100%** | 97.9% | 93.8% |

An interior optimum degrading on both sides — the signature of a real effect rather
than noise. Too low: background texture enters the inventory. Too high: a dim but
real object vanishes from the key.

**For Lesson 41 we add:** a nine-class confusion matrix and PR curves (sparse
classes are currently noisy), training convergence curves, and a robustness sweep.
Preliminary robustness: half-resolution input costs **−12.5 points** — meaning
**degraded relay conditions, not adversarial imagery, are the real threat to plan
around.** That is a tactically useful finding, not a limitation to apologise for.

---

## Tactical implications

1. **The 10% human baseline is not a capability, it is a delay.** A $2/1000,
   human-latency, 10%-reliable pipeline can only serve bulk scraping where minutes
   do not matter. Automating to benchmark-100% at milliseconds per challenge does
   not just cut unit cost — it changes **what the capability can be used for**.
2. **The external dependency is the real vulnerability.** Renting human solvers
   leaks the target set to a third-party population. A locally hosted model leaks
   nothing. That is a security property, and the more important one.
3. **Confidence gating is a force multiplier.** Because the agent emits a margin,
   it can be tuned toward precision — auto-fire high-margin answers, escalate the
   rest — and the escalation rate is computable **before deployment**. Systems that
   cannot abstain cannot be safely automated.
4. **Where this defence actually breaks.** Measured: not model capacity (missed
   detections are effectively zero, TIDE Missed-GT = 0) but **label scarcity in the
   degraded visual domain**. The counter to a system like this is not a harder
   puzzle — it is a puzzle whose *rendering* shifts faster than labels can be
   collected. That is the finding worth briefing.

---

## Scope and handling notes

This is a **research exercise against a challenge family, not a system pointed at
any live target.** Every evaluation image was collected by us and labelled by us;
the repository contains no credentials, no session material, and no live-endpoint
code — the agent runs on saved frames and nothing else. The contribution being
graded is the decision-theoretic layer and its measurement methodology, both
domain-general: the same asymmetric-score-plus-abstain structure applies to any
noisy sensor feeding a discrete inventory task, which is the actual transferable
result.

**One practical note for the public repo:** vendor names are useful in the Blackboard
write-up and in the presentation Q&A, and they stay in this document. If the public
GitHub repo is going to be linked anywhere persistent, consider whether you want
`docs/` shipped as-is or trimmed to "a commercial challenge family" — the
algorithmic argument does not depend on the name either way. Your call; the code
contains no vendor references at all.
