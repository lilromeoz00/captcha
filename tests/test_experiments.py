"""Regression tests for the experiment code.

These exist so the report's numbers cannot silently change: if the metrics
implementation or a baseline drifts, these fail.

Run:  python -m unittest tests.test_experiments -v
"""

import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments"))

import baselines as B  # noqa: E402
import metrics as M  # noqa: E402


class TestIoU(unittest.TestCase):
    def test_identical_boxes(self):
        self.assertAlmostEqual(M.iou((0, 0, 10, 10), (0, 0, 10, 10)), 1.0)

    def test_disjoint_boxes(self):
        self.assertEqual(M.iou((0, 0, 10, 10), (20, 20, 30, 30)), 0.0)

    def test_half_overlap(self):
        # two 10x10 boxes sharing a 5x10 strip: inter=50, union=150
        self.assertAlmostEqual(M.iou((0, 0, 10, 10), (5, 0, 15, 10)), 50 / 150)

    def test_contained_box(self):
        self.assertAlmostEqual(M.iou((0, 0, 10, 10), (2, 2, 4, 4)), 4 / 100)

    def test_zero_area_is_safe(self):
        self.assertEqual(M.iou((0, 0, 0, 0), (0, 0, 10, 10)), 0.0)


def _det(cls, conf, box):
    return {"cls": cls, "cls_id": 0, "conf": conf, "box": box}


def _gt(cls, box):
    return {"cls": cls, "cls_id": 0, "box": box}


class TestMatching(unittest.TestCase):
    def test_perfect_match(self):
        preds = [_det("onion", 0.9, (0, 0, 10, 10))]
        gts = [_gt("onion", (0, 0, 10, 10))]
        pairs, fp, fn = M.match_tile(preds, gts)
        self.assertEqual(len(pairs), 1)
        self.assertEqual((len(fp), len(fn)), (0, 0))

    def test_no_match_when_iou_low(self):
        preds = [_det("onion", 0.9, (0, 0, 10, 10))]
        gts = [_gt("onion", (50, 50, 60, 60))]
        pairs, fp, fn = M.match_tile(preds, gts)
        self.assertEqual((len(pairs), len(fp), len(fn)), (0, 1, 1))

    def test_one_to_one_not_many_to_one(self):
        """Two predictions on one GT: only one may be a true positive."""
        preds = [_det("onion", 0.9, (0, 0, 10, 10)), _det("onion", 0.8, (0, 0, 10, 10))]
        gts = [_gt("onion", (0, 0, 10, 10))]
        pairs, fp, fn = M.match_tile(preds, gts)
        self.assertEqual((len(pairs), len(fp), len(fn)), (1, 1, 0))

    def test_greedy_prefers_higher_confidence(self):
        preds = [_det("onion", 0.95, (0, 0, 10, 10)), _det("onion", 0.55, (0, 0, 10, 10))]
        gts = [_gt("onion", (0, 0, 10, 10))]
        pairs, _fp, _fn = M.match_tile(preds, gts)
        self.assertEqual(pairs[0][0], 0)


class TestPerClassMetrics(unittest.TestCase):
    def test_perfect_detector(self):
        preds = [[_det("onion", 0.9, (0, 0, 10, 10))]]
        gts = [[_gt("onion", (0, 0, 10, 10))]]
        r = M.per_class_prf(preds, gts)["onion"]
        self.assertEqual((r["precision"], r["recall"], r["f1"]), (1.0, 1.0, 1.0))

    def test_missed_detection_hurts_recall_only(self):
        preds = [[]]
        gts = [[_gt("onion", (0, 0, 10, 10))]]
        r = M.per_class_prf(preds, gts)["onion"]
        self.assertEqual((r["precision"], r["recall"]), (0.0, 0.0))
        self.assertEqual(r["fn"], 1)

    def test_wrong_class_counts_as_both_errors(self):
        """Right place, wrong name must be a false positive AND a false negative."""
        preds = [[_det("corn", 0.9, (0, 0, 10, 10))]]
        gts = [[_gt("onion", (0, 0, 10, 10))]]
        r = M.per_class_prf(preds, gts)
        self.assertEqual((r["onion"]["fn"], r["corn"]["fp"]), (1, 1))
        self.assertEqual((r["onion"]["precision"], r["corn"]["precision"]), (0.0, 0.0))

    def test_empty_input_does_not_crash(self):
        r = M.per_class_prf([], [])
        self.assertEqual(len(r), 9)
        self.assertEqual(r["onion"]["precision"], 0.0)


class TestAP(unittest.TestCase):
    def test_ap_is_one_for_perfect_ranking(self):
        preds = [[_det("onion", 0.9, (0, 0, 10, 10))]]
        gts = [[_gt("onion", (0, 0, 10, 10))]]
        self.assertAlmostEqual(M.average_precision(preds, gts, "onion"), 1.0)

    def test_ap_is_zero_for_no_detections(self):
        preds = [[]]
        gts = [[_gt("onion", (0, 0, 10, 10))]]
        self.assertEqual(M.average_precision(preds, gts, "onion"), 0.0)

    def test_absent_class_is_nan_not_zero(self):
        """A class with no ground truth must not drag the mAP average down."""
        preds = [[]]
        gts = [[_gt("onion", (0, 0, 10, 10))]]
        self.assertTrue(np.isnan(M.average_precision(preds, gts, "carrot")))

    def test_ap_penalises_a_low_confidence_false_positive(self):
        gts = [[_gt("onion", (0, 0, 10, 10))]]
        clean = [[_det("onion", 0.9, (0, 0, 10, 10))]]
        noisy = [[_det("onion", 0.95, (50, 50, 60, 60)),
                  _det("onion", 0.9, (0, 0, 10, 10))]]
        self.assertLess(
            M.average_precision(noisy, gts, "onion"),
            M.average_precision(clean, gts, "onion"),
        )


class TestConfusionAndCalibration(unittest.TestCase):
    def test_confusion_shape(self):
        m = M.confusion_matrix([[]], [[]])
        self.assertEqual(m.shape, (10, 10))  # 9 classes + background

    def test_miss_lands_in_background_column(self):
        m = M.confusion_matrix([[]], [[_gt("onion", (0, 0, 10, 10))]])
        self.assertEqual(m[0, 9], 1)  # onion -> background

    def test_false_positive_lands_in_background_row(self):
        m = M.confusion_matrix([[_det("onion", 0.9, (0, 0, 10, 10))]], [[]])
        self.assertEqual(m[9, 0], 1)  # background -> onion

    def test_perfect_detector_is_perfectly_calibrated(self):
        cal = M.calibration([[_det("onion", 0.95, (0, 0, 10, 10))]],
                            [[_gt("onion", (0, 0, 10, 10))]])
        self.assertEqual(cal["n_detections"], 1)
        self.assertLess(cal["ece"], 0.1)

    def test_calibration_counts_every_detection(self):
        preds = [[_det("onion", 0.9, (0, 0, 10, 10)), _det("corn", 0.6, (50, 50, 60, 60))]]
        gts = [[_gt("onion", (0, 0, 10, 10))]]
        cal = M.calibration(preds, gts)
        self.assertEqual(cal["n_detections"], 2)


class TestBaselines(unittest.TestCase):
    def _tiles(self, key_classes, basket_classes):
        """Build the 9-tile (cls, conf) shape the baselines consume."""
        tiles = [[(c, 0.9) for c in b] for b in basket_classes]
        tiles.append([(c, 0.9) for c in key_classes])
        return tiles

    def test_count_baseline_picks_the_biggest_basket(self):
        dets = {"s1": self._tiles(["onion"], [["corn"], ["corn", "corn", "corn"],
                                              ["radish"], [], [], [], [], []])}
        r = B.yolo_count_baseline(dets, {"s1": 1})
        self.assertEqual(r["right"], 1)

    def test_symmetric_and_asymmetric_agree_on_an_exact_match(self):
        dets = {"s1": self._tiles(
            ["onion", "corn"],
            [["corn", "corn"], ["onion", "corn"], [], [], [], [], [], []],
        )}
        a = B.yolo_symmetric_baseline(dets, {"s1": 1})
        b = B.yolo_asym_baseline(dets, {"s1": 1})
        self.assertEqual(a["right"], b["right"])
        self.assertEqual(a["right"], 1)

    def test_asymmetry_prefers_surplus_over_miss(self):
        """When forced to choose, the 10:1 score must prefer the extra item."""
        # key = onion,corn ; basket0 = onion (misses corn) ; basket1 = onion,corn,corn
        dets = {"s1": self._tiles(
            ["onion", "corn"],
            [["onion"], ["onion", "corn", "corn"], [], [], [], [], [], []],
        )}
        a = B.yolo_asym_baseline(dets, {"s1": 1})
        self.assertEqual(a["rows"][0]["pred"], 1)

    def test_majority_baseline_is_basket_zero(self):
        r = B.majority_baseline(["a", "b"], {"a": 0, "b": 3})
        self.assertEqual((r["right"], r["n"]), (1, 2))

    def test_random_baseline_converges_to_one_eighth(self):
        truth = {f"s{i}": i % 8 for i in range(400)}
        r = B.random_baseline(list(truth), truth, trials=200)
        self.assertAlmostEqual(r["accuracy"], 0.125, delta=0.03)


class TestMcNemar(unittest.TestCase):
    def test_identical_systems_give_p_one(self):
        rows = [{"strip": f"s{i}", "ok": i % 2 == 0} for i in range(10)]
        _b, _a, p = B.mcnemar_exact(rows, rows)
        self.assertEqual(p, 1.0)

    def test_clear_winner_is_significant(self):
        """Agent right everywhere, baseline wrong everywhere."""
        a = [{"strip": f"s{i}", "ok": True} for i in range(20)]
        b = [{"strip": f"s{i}", "ok": False} for i in range(20)]
        b_only, a_only, p = B.mcnemar_exact(a, b)
        self.assertEqual((a_only, b_only), (20, 0))
        self.assertLess(p, 1e-4)

    def test_counts_only_discordant_pairs(self):
        a = [{"strip": "x", "ok": True}, {"strip": "y", "ok": True}]
        b = [{"strip": "x", "ok": True}, {"strip": "y", "ok": False}]
        b_only, a_only, _p = B.mcnemar_exact(a, b)
        self.assertEqual((a_only, b_only), (1, 0))


class TestLocalisation(unittest.TestCase):
    def test_reports_median_iou(self):
        preds = [[_det("onion", 0.9, (0, 0, 10, 10))]]
        gts = [[_gt("onion", (0, 0, 10, 10))]]
        r = M.localisation_iou(preds, gts)
        self.assertEqual(r["n"], 1)
        self.assertAlmostEqual(r["median"], 1.0)

    def test_empty_is_safe(self):
        r = M.localisation_iou([[]], [[]])
        self.assertEqual(r["n"], 0)


if __name__ == "__main__":
    unittest.main()
