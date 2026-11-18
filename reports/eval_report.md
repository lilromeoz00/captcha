# Checkpoint evaluation report

- weights: `veggie_yolo26s_v6.pt`
- conf: 0.4  imgsz: 320  tie policy: recycle
- strips: 48

## Headline

| metric | value |
|---|---|
| task accuracy | **48/48 = 100.0%** (Wilson 95% CI [92.6, 100.0]) |
| ties (margin = 0) | 0 |
| oracle ceiling (a basket exactly matched the key) | 39/48 = 81.2% |
| ceiling exploited by the ranker | 39/39 = 100.0% |

## Accuracy vs decision margin

The margin is the agent's own confidence: score(best) - score(second).

| margin band | n | correct | accuracy |
|---|---|---|---|
| 1-3 | 2 | 2 | 100.0% |
| 8+ | 46 | 46 | 100.0% |

## Class frequency in the keys

| class | key instances |
|---|---|
| onion | 21 |
| potato | 24 |
| tomato | 44 |
| eggplant | 24 |
| green-pepper | 0 |
| corn | 17 |
| cucumber | 18 |
| radish | 41 |
| carrot | 0 |

## Per-strip decisions

| strip | pred | truth | ok | margin | key |
|---|---|---|---|---|---|
| strip_0000 | 4 | 4 | yes | 10 | cucumberx1 eggplantx3 |
| strip_0001 | 7 | 7 | yes | 11 | cornx2 potatox1 tomatox1 |
| strip_0002 | 0 | 0 | yes | 22 | cornx1 radishx2 tomatox1 |
| strip_0003 | 5 | 5 | yes | 22 | onionx1 radishx3 |
| strip_0004 | 7 | 7 | yes | 11 | cucumberx4 |
| strip_0005 | 3 | 3 | yes | 23 | radishx1 tomatox3 |
| strip_0006 | 0 | 0 | yes | 11 | cucumberx1 onionx3 |
| strip_0007 | 7 | 7 | yes | 22 | eggplantx1 radishx1 tomatox2 |
| strip_0008 | 4 | 4 | yes | 12 | radishx3 |
| strip_0009 | 2 | 2 | yes | 11 | cornx1 radishx2 tomatox1 |
| strip_0010 | 4 | 4 | yes | 12 | radishx1 tomatox3 |
| strip_0011 | 6 | 6 | yes | 11 | onionx3 tomatox1 |
| strip_0012 | 2 | 2 | yes | 10 | eggplantx2 radishx2 |
| strip_0013 | 2 | 2 | yes | 1 | eggplantx1 radishx2 tomatox1 |
| strip_0014 | 1 | 1 | yes | 11 | cornx1 eggplantx3 |
| strip_0015 | 1 | 1 | yes | 11 | cornx2 onionx1 potatox1 |
| strip_0016 | 0 | 0 | yes | 10 | onionx1 tomatox2 |
| strip_0017 | 6 | 6 | yes | 22 | cucumberx1 radishx3 |
| strip_0018 | 2 | 2 | yes | 22 | eggplantx1 tomatox3 |
| strip_0019 | 0 | 0 | yes | 11 | onionx1 potatox1 radishx2 |
| strip_0020 | 1 | 1 | yes | 22 | eggplantx1 potatox3 |
| strip_0021 | 4 | 4 | yes | 11 | eggplantx2 potatox1 tomatox1 |
| strip_0022 | 3 | 3 | yes | 22 | potatox1 tomatox3 |
| strip_0023 | 7 | 7 | yes | 11 | cornx1 eggplantx1 tomatox2 |
| strip_0024 | 5 | 5 | yes | 11 | cucumberx1 onionx3 |
| strip_0025 | 4 | 4 | yes | 22 | potatox3 radishx1 |
| strip_0026 | 0 | 0 | yes | 22 | tomatox4 |
| strip_0027 | 3 | 3 | yes | 22 | radishx1 tomatox3 |
| strip_0028 | 7 | 7 | yes | 11 | eggplantx4 |
| strip_0029 | 2 | 2 | yes | 22 | onionx3 potatox1 |
| strip_0030 | 6 | 6 | yes | 11 | onionx1 potatox2 |
| strip_0031 | 1 | 1 | yes | 22 | onionx2 radishx2 |
| strip_0032 | 1 | 1 | yes | 11 | cucumberx2 potatox1 tomatox1 |
| strip_0033 | 0 | 0 | yes | 11 | eggplantx2 radishx2 |
| strip_0034 | 0 | 0 | yes | 11 | cucumberx1 onionx1 radishx2 |
| strip_0035 | 2 | 2 | yes | 11 | cucumberx3 onionx1 |
| strip_0036 | 0 | 0 | yes | 11 | cornx1 potatox3 |
| strip_0037 | 4 | 4 | yes | 11 | cornx4 |
| strip_0038 | 1 | 1 | yes | 11 | cucumberx3 tomatox1 |
| strip_0039 | 3 | 3 | yes | 10 | cucumberx1 radishx1 tomatox2 |
| strip_0040 | 1 | 1 | yes | 22 | radishx4 |
| strip_0041 | 1 | 1 | yes | 22 | radishx2 tomatox2 |
| strip_0042 | 2 | 2 | yes | 11 | potatox2 tomatox2 |
| strip_0043 | 0 | 0 | yes | 11 | potatox4 |
| strip_0044 | 1 | 1 | yes | 11 | cornx2 tomatox2 |
| strip_0045 | 3 | 3 | yes | 11 | cornx1 tomatox3 |
| strip_0046 | 4 | 4 | yes | 11 | eggplantx3 radishx1 |
| strip_0047 | 3 | 3 | yes | 1 | cornx1 radishx3 |
