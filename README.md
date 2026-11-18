# CS471 Final Project

## Automated Solution of an Adversarial Visual Access-Control Challenge

**Author:** Jordan Moore
**Submitted version:** tag `final`
**Report:** [`CS471_Final_Report.pdf`](CS471_Final_Report.pdf)

---

## 1. Problem statement

Automated collection against a defended network service is frequently limited not by
cryptographic controls but by a visual challenge presented as an access condition.
The challenge family addressed here is served as a single 1600×400 image containing
eight candidate scenes, each holding four objects, and a grayscale silhouette of a
different set of objects. Access is granted only if the correct scene is selected,
where "correct" means that the multiset of object classes in the scene is identical
to the multiset shown in the silhouette.

The commercial solution to this class of challenge is manual labour arbitrage:
challenges are distributed to low-wage workers who solve them for approximately
$2 per 1,000 items. That pipeline has three operational deficiencies. It is bound by
human latency and therefore unsuitable for time-sensitive collection. It is
unreliable, succeeding at roughly 10%, because challenge families are rotated faster
than a human workforce adapts. Finally, it depends on an external population that
cannot be audited or scaled on demand, and to which the target set is disclosed.

This project implements a local alternative.

## 2. Approach

The task is not classification. The correct answer depends on the count of each
class present, so a scene containing three onions and one potato is incorrect when
the key specifies two onions and two potatoes, even if every individual object was
correctly detected. The problem is therefore formulated as multiset matching over
detector output.

```
key    = {onion: 2, potato: 2}
scene  = {onion: 2, potato: 1, corn: 1}   # incorrect, all objects detected
```

The implementation has two stages:

1. **Perception.** A single-stage convolutional object detector (YOLO26s, 9.5M
   parameters) is applied to nine fixed 200×200 tiles cut from the frame. Each tile
   is reduced to a class multiset.
2. **Decision.** Each candidate scene is scored against the key using an asymmetric
   penalty, and the highest-scoring scene is selected. When the top two scores are
   equal, the agent abstains and requests a new challenge rather than spending a
   scored attempt on an indeterminate choice.

Section 4 of the report gives the scoring function, the ablation results, and an
explicit statement of which design choices the evaluation data does and does not
support.

## 3. Results

| Measurement | Value |
|---|---|
| Task accuracy, 48 hand-labelled challenges | 48/48 = 100%, Wilson 95% CI [92.6, 100.0] |
| Strongest baseline without the matching layer | 25.0% (YOLO + maximum confidence) |
| Classical computer-vision baseline | 12.5% (chance) |
| Object recall, 288 held-out tiles | 99.0% (1132/1143) |
| Object precision | 97.9% |
| mAP50 | 0.983 |
| Oracle ceiling exploited by the ranking stage | 39/39 = 100% |
| Accuracy at Gaussian blur, radius 2.0 | 64.6% |

The comparison against a symmetric penalty is reported as a negative result. A 1:1
penalty also achieves 48/48, so the 10:1 asymmetry used in the submitted system
cannot be distinguished from a symmetric score on this evaluation set. The report
states this directly in Section 4.4 rather than omitting the ablation.

## 4. Repository contents

```
solver/            the agent
  geometry.py      frame segmentation into nine fixed tiles, with size validation
  detector.py      YOLO26s wrapper (the only module depending on torch)
  multiset.py      scoring, ranking and abstention policy (standard library only)
  ranker.py        end-to-end agent and evaluation metrics
  cli.py           command-line interface

experiments/       the evaluation programme
  baselines.py     six baselines
  metrics.py       IoU, matching, per-class precision/recall, AP, calibration
  run_all.py       runs all experiments, writes results/experiments.json
  figures.py       renders the report figures from that file
  make_report.py   generates the report PDF from that file

tests/             80 automated tests
data/              trained weights and all evaluation data
results/           experiment output
figures/           report figures
docs/              algorithm documentation and worksheet responses
```

## 5. Requirements

- Python 3.10 or later (developed on 3.13.7)
- `torch` 2.0 or later; a CUDA build is recommended but not required
- `ultralytics` 8.3 or later
- `pillow`, `numpy`

Only `solver/detector.py` imports torch. The decision layer in `solver/multiset.py`
and the segmentation in `solver/geometry.py` use only the standard library and
Pillow, so the core algorithm can be tested without a GPU or the model weights.

## 6. Execution

```powershell
python -m pip install -r requirements.txt

python tests\run_all.py                # 80 tests
python -m solver selftest              # scoring function, no model required
python -m solver solve data\strips\strip_0000.jpg --annotate out.jpg
python -m solver eval --report reports\eval_report.md --min-acc 0.85

python experiments\run_all.py          # regenerates results\experiments.json
python experiments\figures.py          # regenerates figures\
python experiments\make_report.py      # rebuilds CS471_Final_Report.pdf
```

`solve` returns exit code 0. `eval` returns 1 if accuracy falls below `--min-acc`,
so it can be used as a regression gate.

The report is generated from `results/experiments.json`; no value in it is entered
manually. Re-running the four experiment commands reproduces the report exactly.

## 7. Data

The repository contains the trained weights (20.3 MB), all 48 evaluation frames, 288
held-out 200×200 tiles with human bounding-box annotations, the hand-labelled answer
key for all 48 frames, and the training convergence log. Training is not required to
reproduce any reported result.

The 1,604 training tiles that produced the shipped checkpoint are not included,
because they derive from captures that cannot be redistributed. No evaluation image
appears in any training split; this was verified by content hash rather than
filename.

## 8. Documentation

- [`docs/ALGORITHM.md`](docs/ALGORITHM.md) — scoring function, ablations, complexity
- [`docs/TACTICAL_FRAMING.md`](docs/TACTICAL_FRAMING.md) — responses to worksheet questions 1–5
- [`PROGRESS.md`](PROGRESS.md) — project status, contributions, issues encountered
- [`FINAL_SUMMARY.md`](FINAL_SUMMARY.md) — submission summary

## 9. Presentation

`CS471_Presentation.pptx` — 12 slides, 16:9, with speaker notes and timings in the
PowerPoint notes pane.

```powershell
python presentation\make_deck.py      # rebuild the deck from the figures
python presentation\add_notes.py      # re-attach speaker notes
python presentation\verify_deck.py    # assert no shape leaves the slide
```

The deck is generated from the same `figures/` and `results/experiments.json` as
the report, so a slide cannot disagree with a measured value. Slide 6 uses the
actual annotated output of `strip_0000` and its verbatim terminal text;
`presentation/BACKUP_DEMO.md` holds the same material for use if the live
demonstration fails.
