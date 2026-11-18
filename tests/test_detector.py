"""Detector correctness: does the network turn a tile into the right multiset?

This is the perception half of the agent tested on its own, against human
ground truth (YOLO-format boxes in `data/cells/val/labels`). `data/cells/val` is
a held-out split -- these images never appear in training.

Two questions, because they fail differently:

* **Recall** -- of the vegetables actually present, how many did the model find?
  A miss destroys information the ranker can never recover.
* **Exact agreement** -- on how many tiles does the detected multiset equal the
  labelled multiset exactly? That is precisely the unit the ranker consumes.

Run:  python -m unittest tests.test_detector -v
"""

import collections
import glob
import os
import unittest

from PIL import Image

from solver.detector import VeggieDetector
from solver.multiset import CLASSES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHTS = os.path.join(ROOT, "data", "weights", "veggie_yolo26s_v6.pt")
VAL_IMAGES = os.path.join(ROOT, "data", "cells", "val", "images")
VAL_LABELS = os.path.join(ROOT, "data", "cells", "val", "labels")

# Thresholds are set BELOW the measured values (92.4% / 99.2%) with headroom for
# fp16 vs fp32 and GPU vs CPU nondeterminism, so the test catches regressions
# rather than flaking.
MIN_EXACT_AGREEMENT = 0.88
MIN_GT_RECALL = 0.97
MAX_EXTRA_RATE = 0.05


def _gt_bag(label_path):
    bag = collections.Counter()
    with open(label_path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                bag[CLASSES[int(line.split()[0])]] += 1
    return bag


class TestDetectorMultisets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(WEIGHTS):
            raise unittest.SkipTest(f"weights missing: {WEIGHTS}")
        cls.files = sorted(glob.glob(os.path.join(VAL_IMAGES, "*.jpg")))
        if not cls.files:
            raise unittest.SkipTest("no validation cells found -- run the data fetch")
        images = []
        for f in cls.files:
            with Image.open(f) as im:
                images.append(im.convert("RGB"))
        cls.det = VeggieDetector(WEIGHTS)
        cls.bags = cls.det.detect_counts(images)
        cls.gt = [
            _gt_bag(os.path.join(VAL_LABELS, os.path.basename(f)[:-4] + ".txt"))
            for f in cls.files
        ]

    def test_every_cell_produces_a_bag(self):
        self.assertEqual(len(self.bags), len(self.files))
        for bag in self.bags:
            self.assertIsInstance(bag, dict)

    def test_only_known_classes_are_emitted(self):
        for bag in self.bags:
            for cls in bag:
                self.assertIn(cls, CLASSES)

    def test_ground_truth_recall(self):
        hit = sum(min(n, bag.get(c, 0)) for bag, gt in zip(self.bags, self.gt)
                  for c, n in gt.items())
        total = sum(sum(gt.values()) for gt in self.gt)
        recall = hit / total
        print(f"\n  GT recall: {hit}/{total} = {recall * 100:.2f}%")
        self.assertGreaterEqual(recall, MIN_GT_RECALL)

    def test_exact_multiset_agreement(self):
        exact = sum(1 for bag, gt in zip(self.bags, self.gt) if dict(bag) == dict(gt))
        rate = exact / len(self.gt)
        print(f"  exact multiset agreement: {exact}/{len(self.gt)} = {rate * 100:.1f}%")
        self.assertGreaterEqual(rate, MIN_EXACT_AGREEMENT)

    def test_false_positive_rate_is_bounded(self):
        pred = sum(sum(b.values()) for b in self.bags)
        true = sum(sum(g.values()) for g in self.gt)
        extra = max(0, pred - true) / true
        print(f"  predicted {pred} vs labelled {true} (+{extra * 100:.1f}%)")
        self.assertLessEqual(extra, MAX_EXTRA_RATE)

    def test_confidence_threshold_is_respected(self):
        """Nothing below the configured floor may reach the ranker."""
        dets = self.det.detect([
            Image.open(self.files[0]).convert("RGB")
        ])[0]
        for _cls, conf in dets:
            self.assertGreaterEqual(conf, self.det.conf - 1e-6)

    def test_detections_are_sorted_by_confidence(self):
        dets = self.det.detect([Image.open(f).convert("RGB") for f in self.files[:4]])
        for tile in dets:
            confs = [c for _cls, c in tile]
            self.assertEqual(confs, sorted(confs, reverse=True))


class TestDeterminism(unittest.TestCase):
    def test_same_input_same_output(self):
        """The ranker must not be stochastic; a coin-flip agent cannot be graded."""
        if not os.path.exists(WEIGHTS):
            self.skipTest("weights missing")
        files = sorted(glob.glob(os.path.join(VAL_IMAGES, "*.jpg")))[:3]
        det = VeggieDetector(WEIGHTS)
        imgs = []
        for f in files:
            with Image.open(f) as im:
                imgs.append(im.convert("RGB"))
        self.assertEqual(det.detect_counts(imgs), det.detect_counts(imgs))


if __name__ == "__main__":
    unittest.main()
