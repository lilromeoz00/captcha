import json

d = json.load(open('results/experiments.json'))
b = d['baselines']
print('BASELINES')
for k in ['random', 'majority', 'hist_match', 'yolo_count', 'yolo_confidence',
          'yolo_symmetric_1to1', 'yolo_asym_10to1']:
    r = b[k]
    print(f'  {k:22} {str(r["right"]):>6}/{r["n"]} = {r["accuracy"]*100:5.1f}%')
print('  random trials:', b['random'].get('trials'), 'sd', round(b['random'].get('sd', 0), 2))
print()
det = d['detection']
print('DETECTION mAP50=%.4f' % det['map50'], ' micro:', {k: round(v, 4) for k, v in det['micro'].items()})
print('  ECE=%.4f' % det['calibration']['ece'], 'n_det=', det['calibration']['n_detections'])
print('  loc:', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in det['localisation'].items()})
print('  raw:', det['_raw_counts'])
print('  per-class:')
for c, v in det['per_class'].items():
    print(f'    {c:13} P={v["precision"]:.3f} R={v["recall"]:.3f} F1={v["f1"]:.3f} AP50={v["ap50"]:.3f} n={v["n_gt"]}')
print()
print('CALIBRATION BINS')
for r in det['calibration']['bins']:
    if r['n']:
        print(f"  {r['lo']:.1f}-{r['hi']:.1f} n={r['n']:4} acc={r['accuracy']:.3f}")
print()
print('AGENT', d['agent'])
print()
print('MARGIN TABLE')
for r in d['agent']['margin_table']:
    print(' ', r)
print()
print('SIGNIFICANCE')
for k, v in b['_significance'].items():
    print(f'  {k:22} agent_only={v["agent_only"]:2} base_only={v["baseline_only"]:2} p={v["p"]:.3g}')
