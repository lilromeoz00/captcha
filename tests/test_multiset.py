"""Unit tests for the decision core. No model, no GPU, no data files.

Run:  python -m unittest tests.test_multiset -v
"""

import unittest
from collections import Counter

from solver.multiset import (
    CLASSES,
    as_multiset,
    decide,
    match,
    rank,
)


class TestMatch(unittest.TestCase):
    def test_exact_match_is_zero_cost(self):
        key = as_multiset(["onion", "onion", "potato", "potato"])
        m = match(key, as_multiset(["onion", "onion", "potato", "potato"]))
        self.assertEqual((m.score, m.misses, m.extras), (0, 0, 0))
        self.assertTrue(m.exact)

    def test_order_does_not_matter(self):
        """A multiset, not a sequence: the same bag in any order scores the same."""
        a = as_multiset(["onion", "tomato", "corn", "radish"])
        b = as_multiset(["radish", "corn", "tomato", "onion"])
        self.assertEqual(match(a, b).score, 0)

    def test_one_missing_item_costs_ten(self):
        key = as_multiset(["onion", "onion", "potato", "potato"])
        m = match(key, as_multiset(["onion", "onion", "potato"]))
        self.assertEqual((m.score, m.misses, m.extras), (-10, 1, 0))
        self.assertFalse(m.exact)

    def test_one_surplus_item_costs_one(self):
        key = as_multiset(["onion", "onion", "potato", "potato"])
        m = match(key, as_multiset(["onion", "onion", "potato", "potato", "corn"]))
        self.assertEqual((m.score, m.misses, m.extras), (-1, 0, 1))
        self.assertFalse(m.exact)

    def test_missing_beats_surplus(self):
        """The 10:1 asymmetry is a design decision; assert it explicitly."""
        key = as_multiset(["onion", "onion", "potato", "potato"])
        missing = match(key, as_multiset(["onion", "onion", "potato"]))
        surplus = match(key, as_multiset(["onion", "onion", "potato", "potato", "corn"]))
        self.assertLess(missing.score, surplus.score)

    def test_wrong_class_is_both_a_miss_and_a_surplus(self):
        """Swapping a vegetable scores -11, not 0: it is one miss AND one extra."""
        key = as_multiset(["onion", "onion", "potato", "potato"])
        m = match(key, as_multiset(["onion", "onion", "potato", "carrot"]))
        self.assertEqual((m.score, m.misses, m.extras), (-11, 1, 1))

    def test_count_matters_not_just_presence(self):
        """Three onions where two were asked for is a surplus, not a match."""
        key = as_multiset(["onion", "onion", "potato", "potato"])
        m = match(key, as_multiset(["onion", "onion", "onion", "potato", "potato"]))
        self.assertEqual((m.misses, m.extras), (0, 1))

    def test_empty_basket(self):
        key = as_multiset(["onion", "potato", "corn", "radish"])
        m = match(key, Counter())
        self.assertEqual((m.score, m.misses, m.extras), (-40, 4, 0))

    def test_penalties_are_configurable(self):
        key = as_multiset(["onion", "potato"])
        self.assertEqual(match(key, as_multiset(["onion"]), miss_penalty=5).score, -5)


class TestRank(unittest.TestCase):
    def setUp(self):
        self.key = as_multiset(["onion", "onion", "potato", "potato"])

    def test_picks_the_exact_basket(self):
        baskets = {
            "0": as_multiset(["corn", "corn", "corn", "corn"]),
            "1": as_multiset(["onion", "onion", "potato", "potato"]),
            "2": as_multiset(["onion", "potato", "potato", "radish"]),
        }
        r = rank(self.key, baskets)
        self.assertEqual(r.best, "1")
        self.assertTrue(r.best_match.exact)
        self.assertGreater(r.margin, 0)

    def test_margin_is_the_gap_to_second_place(self):
        baskets = {
            "0": as_multiset(["onion", "onion", "potato", "potato"]),  # 0
            "1": as_multiset(["onion", "onion", "potato"]),  # -10
        }
        r = rank(self.key, baskets)
        self.assertEqual(r.margin, 10)

    def test_identical_baskets_tie(self):
        baskets = {"0": as_multiset(["onion", "corn"]), "1": as_multiset(["onion", "corn"])}
        r = rank(self.key, baskets)
        self.assertTrue(r.tie)
        self.assertEqual(r.margin, 0)

    def test_different_bags_can_still_tie(self):
        """Ties are about score, not about identical bags."""
        key = as_multiset(["onion", "onion"])
        baskets = {
            "0": as_multiset(["onion"]),  # -10
            "1": as_multiset(["onion", "onion", "onion", "onion", "onion", "onion",
                              "onion", "onion", "onion", "onion"]),  # -8
        }
        self.assertFalse(rank(key, baskets).tie)

    def test_requires_two_baskets(self):
        with self.assertRaises(ValueError):
            rank(self.key, {"0": as_multiset(["onion"])})

    def test_exact_baskets_lists_the_ceiling(self):
        baskets = {
            "0": as_multiset(["onion", "onion", "potato", "potato"]),
            "1": as_multiset(["onion", "onion", "potato", "potato"]),
            "2": as_multiset(["corn"]),
        }
        self.assertEqual(sorted(rank(self.key, baskets).exact_baskets), ["0", "1"])


class TestDecide(unittest.TestCase):
    def test_answers_when_margin_is_positive(self):
        key = as_multiset(["onion", "potato"])
        r = rank(key, {"0": as_multiset(["onion", "potato"]), "1": as_multiset(["corn"])})
        self.assertEqual(decide(r), ("answer", "0"))

    def test_recycles_on_a_tie(self):
        key = as_multiset(["onion", "potato"])
        r = rank(key, {"0": as_multiset(["corn"]), "1": as_multiset(["radish"])})
        self.assertTrue(r.tie)
        self.assertEqual(decide(r), ("recycle", None))

    def test_guess_policy_spends_the_attempt_anyway(self):
        key = as_multiset(["onion", "potato"])
        r = rank(key, {"0": as_multiset(["corn"]), "1": as_multiset(["radish"])})
        action, target = decide(r, on_tie="guess")
        self.assertEqual(action, "answer")
        self.assertIn(target, ("0", "1"))

    def test_rejects_bad_policy(self):
        key = as_multiset(["onion"])
        r = rank(key, {"0": as_multiset(["onion"]), "1": as_multiset(["corn"])})
        with self.assertRaises(ValueError):
            decide(r, on_tie="coinflip")


class TestVocabulary(unittest.TestCase):
    def test_vocabulary_is_fixed_and_unique(self):
        self.assertEqual(len(CLASSES), 9)
        self.assertEqual(len(set(CLASSES)), 9)

    def test_class_ids_are_stable(self):
        """YOLO class ids index this tuple; reordering would silently relabel boxes."""
        self.assertEqual(CLASSES[0], "onion")
        self.assertEqual(CLASSES[8], "carrot")


if __name__ == "__main__":
    unittest.main()
