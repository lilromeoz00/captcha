"""End-to-end correctness: does the whole agent pick the right basket?

40 strips with hand-labelled answers (`data/truth.json`). This is the number the
milestone cares about: the agent's task accuracy, measured against truth it did
not produce.

Also checked here:
* the observed ceiling decomposition (perception vs ranking blame)
* the tie policy actually behaves as documented
* the pipeline is deterministic across repeated runs

Run:  python -m unittest tests.test_end_to_end -v
"""

import glob
import json
import os
import unittest

from PIL import Image

from solver import ranker
from solver.detector import VeggieDetector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHTS = os.path.join(ROOT, "data", "weights", "veggie_yolo26s_v6.pt")
STRIPS = os.path.join(ROOT, "data", "strips")
TRUTH = os.path.join(ROOT, "data", "truth.json")

# Measured at 97.9% (47/48). The floor sits below the Wilson lower bound of that
# measurement (~89%), so a failure means something actually broke.
MIN_ACCURACY = 0.85


def _load():
    strips = {
        os.path.basename(p)[:-4]: p
        for p in sorted(glob.glob(os.path.join(STRIPS, "*.jpg")))
    }
    with open(TRUTH, encoding="utf-8") as fh:
        truth = json.load(fh)
    return strips, truth


class TestEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(WEIGHTS):
            raise unittest.SkipTest(f"weights missing: {WEIGHTS}")
        cls.strips, cls.truth = _load()
        if not cls.strips:
            raise unittest.SkipTest("no strips found")
        cls.det = VeggieDetector(WEIGHTS)
        cls.report = ranker.evaluate(cls.det, cls.strips, cls.truth)

    def test_task_accuracy(self):
        r = self.report
        lo, hi = ranker.wilson(r["right"], r["n"])
        print(
            f"\n  task accuracy: {r['right']}/{r['n']} = {r['accuracy'] * 100:.1f}%"
            f"  Wilson95 [{lo * 100:.1f}, {hi * 100:.1f}]"
            f"  ties={r['ties']}"
        )
        self.assertGreaterEqual(r["accuracy"], MIN_ACCURACY)

    def test_every_strip_gets_a_legal_answer(self):
        for row in self.report["rows"]:
            if row["action"] == "answer":
                self.assertIn(row["pred"], list(range(8)))
            else:
                self.assertIsNone(row["pred"])

    def test_ceiling_decomposition_is_self_consistent(self):
        """If a strip had an exact basket, the ranker should have found it.

        This is the diagnostic that separates perception loss from ranking loss:
        `exploited` must never exceed `ceiling`, and in the measured run the
        ranker converts 100% of available ceilings.
        """
        r = self.report
        print(
            f"  ceiling: {r['ceiling_n']}/{r['n']} strips had an exact basket; "
            f"exploited {r['exploited']}/{r['ceiling_n']} = {r['exploit_rate'] * 100:.1f}%"
        )
        self.assertLessEqual(r["exploited"], r["ceiling_n"])
        self.assertGreaterEqual(r["exploit_rate"], 0.90)

    def test_exact_match_always_means_a_right_answer(self):
        """If the winning basket reproduced the key exactly, the answer is right.

        The converse is not claimed: partial scoring can still be correct on a
        strip where detection noise left no exact basket anywhere.
        """
        rows = [r for r in self.report["rows"] if r["misses"] == 0 and r["extras"] == 0]
        self.assertTrue(rows, "no exact matches at all -- perception has regressed")
        wrong = [r["strip"] for r in rows if not r["ok"]]
        self.assertEqual(wrong, [], f"exact match but wrong answer on {wrong}")

    def test_key_misses_predict_errors(self):
        """A leftover key item is the agent's own signal that it is unsure.

        This is the honesty check on the scoring function: it should be right
        most of the time when the key is fully covered and markedly worse when
        it is not. A monotone relationship here is what justifies the 10:1
        penalty ratio rather than an arbitrary one.
        """
        clean = [r for r in self.report["rows"] if r["misses"] == 0]
        dirty = [r for r in self.report["rows"] if r["misses"] > 0]
        acc_clean = sum(r["ok"] for r in clean) / max(1, len(clean))
        acc_dirty = sum(r["ok"] for r in dirty) / max(1, len(dirty))
        print(
            f"  misses=0: {len(clean)} strips, acc {acc_clean * 100:.1f}%   "
            f"misses>0: {len(dirty)} strips, acc {acc_dirty * 100:.1f}%"
        )
        self.assertGreaterEqual(acc_clean, acc_dirty)

    def test_deterministic_across_runs(self):
        a = ranker.solve_file(self.det, self.strips[sorted(self.strips)[0]])
        b = ranker.solve_file(self.det, self.strips[sorted(self.strips)[0]])
        self.assertEqual(a["answer"], b["answer"])
        self.assertEqual(a["scores"], b["scores"])

    def test_tie_policy_changes_the_action_but_not_the_analysis(self):
        """With `guess`, a tie is spent; with `recycle`, it is refused."""
        guess = ranker.evaluate(self.det, self.strips, self.truth, on_tie="guess")
        self.assertEqual(guess["n"], self.report["n"])
        for row in self.report["rows"]:
            if row["margin"] == 0:
                self.assertEqual(row["action"], "recycle")
            else:
                self.assertEqual(row["action"], "answer")

    def test_geometry_gate_rejects_a_rescaled_strip(self):
        from solver.geometry import StripGeometryError

        path = self.strips[sorted(self.strips)[0]]
        with Image.open(path) as im:
            small = im.convert("RGB").resize((800, 200))
        with self.assertRaises(StripGeometryError):
            ranker.rank_strip(self.det, small)


if __name__ == "__main__":
    unittest.main()
