# Backup demonstration

Use this if the live machine fails. Everything below is committed to the
repository, so it can be shown from any machine with the repository checked out.

---

## A. The command that is run live

```powershell
python -m solver solve data\strips\strip_0000.jpg --annotate out.jpg
```

Expected runtime: approximately two seconds on CPU, under one second on GPU.

## B. Verbatim output (captured from the shipped checkpoint)

```
image      : data\strips\strip_0000.jpg
key (S)    : cucumberx1 eggplantx3
  basket 0 : cucumberx4                                   score=  -33
  basket 1 : cucumberx3 potatox1                          score=  -33
  basket 2 : cucumberx2 eggplantx2                        score=  -11
  basket 3 : cucumberx3 eggplantx1                        score=  -22
  basket 4 : cucumberx2 eggplantx3                        score=   -1 <-- ANSWER
  basket 5 : cucumberx3 tomatox1                          score=  -33
  basket 6 : cucumberx2 eggplantx1 tomatox1               score=  -22
  basket 7 : cucumberx2 eggplantx1 potatox1               score=  -22
decision   : answer basket 4   margin=10  misses=0 extras=1  tie=False
annotated  : out.jpg
```

## C. What to point at

| Element | What it demonstrates |
|---|---|
| `key (S)` | the agent read the grayscale silhouette and produced a multiset |
| `basket 4 ... score = -1` | one surplus detection, no missed object: the winning score |
| `basket 2 ... score = -11` | one missed object and one surplus: a miss costs ten times a surplus |
| `basket 0 ... score = -33` | three missed key objects: the penalty compounds as intended |
| `margin=10` | the decision is not marginal; the runner-up is a full miss behind |
| `out.jpg` | the annotated frame, selected scene bordered in green |

The score column is the whole argument in one screen: the ranking is produced by
the multiset comparison, not by the detector's confidence.

## D. Annotated frame

`presentation/demo_annotated.jpg` — the full pipeline output, 1600×600, showing
every tile bordered and scored, the key in cyan and the answer in green. This is
the image embedded on slide 6.

## E. If the model itself will not load

The decision layer runs without torch:

```powershell
python -m solver selftest
```

```
exact      : score=0 misses=0 extras=0
one miss   : score=-10
one extra  : score=-1
tiling     : 1600x400, 9 tiles
SELFTEST PASS
```

This demonstrates the scoring function and the tiling independently of the
network, which is the point worth making if the GPU is unavailable.

## F. If the whole repository is unavailable

Every number quoted in the presentation is present in
`results/experiments.json`, a plain text file that can be opened in any editor.
The headline values are:

| Measurement | Value |
|---|---|
| Task accuracy | 48/48 = 100%, Wilson 95% CI [92.6, 100.0] |
| Strongest non-matching baseline | 25.0% |
| Object recall, 288 held-out tiles | 99.0% (1132/1143) |
| mAP50 | 0.983 |
| Ceiling exploited | 39/39 |
| Blur r=2.0 accuracy | 31/48 = 64.6% |

## G. Pre-flight checklist

Run this ten minutes before presenting.

```powershell
cd <repository>
python tests\run_all.py            # expect: ran 80, failures 0
python -m solver solve data\strips\strip_0000.jpg
```

If either fails, use sections B and C above and do not debug in front of the
class.
