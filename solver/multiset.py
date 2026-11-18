"""multiset.py -- the decision-theoretic core of the agent.

This module is pure Python (no torch, no PIL) so the mathematics can be tested
in isolation and read on its own. Everything the agent *decides* happens here;
the neural network only supplies the evidence.

The problem is a multiset (bag) matching problem, not classification:

    key      = the vegetables shown in the challenge key   {onion: 2, potato: 2}
    basket_i = the vegetables the detector found in scene i {onion: 2, potato: 1, corn: 1}

The answer is the basket whose bag of vegetables equals the key's bag. Two bags
are compared by an asymmetric penalty:

    score(key, basket) = -(MISS_PENALTY * missed + EXTRA_PENALTY * surplus)

where `missed` counts key items the basket failed to account for and `surplus`
counts items in the basket that the key did not ask for.

Why 10:1 asymmetry. A missed item usually means the detector *dropped* a real
vegetable (a recall failure on the degraded grayscale key). A surplus item is
usually a duplicate or background false positive. Dropping is the more
informative error, so it costs ten times as much. This single constant is what
makes the scoring function behave like a likelihood ratio instead of a Hamming
distance; see `docs/ALGORITHM.md` for the derivation and the ablation.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Tuple

#: Fixed, ordered class vocabulary. Index == YOLO class id, so do not reorder.
CLASSES: Tuple[str, ...] = (
    "onion",
    "potato",
    "tomato",
    "eggplant",
    "green-pepper",
    "corn",
    "cucumber",
    "radish",
    "carrot",
)

MISS_PENALTY: int = 10
EXTRA_PENALTY: int = 1


def as_multiset(items: Iterable[str]) -> Counter:
    """Collapse an iterable of class names into a bag of counts."""
    return Counter(items)


@dataclass(frozen=True)
class Match:
    """Score of one candidate basket against the key."""

    score: int
    misses: int
    extras: int

    @property
    def exact(self) -> bool:
        """True when the basket reproduces the key exactly."""
        return self.misses == 0 and self.extras == 0


def match(
    key: Mapping[str, int],
    basket: Mapping[str, int],
    miss_penalty: int = MISS_PENALTY,
    extra_penalty: int = EXTRA_PENALTY,
) -> Match:
    """Score one basket against the key.

    Greedy subtraction is exact here because the cost is linear in the counts:
    for each class, the number of key items satisfied is `min(key, basket)`.
    """
    pool = Counter(basket)
    misses = 0
    for cls, n in key.items():
        take = min(n, pool[cls])
        pool[cls] -= take
        misses += n - take
    extras = sum(pool.values())
    return Match(-(misses * miss_penalty + extras * extra_penalty), misses, extras)


@dataclass
class Ranking:
    """Full ordering of the candidate baskets, best first."""

    order: List[Tuple[str, Match]]

    @property
    def best(self) -> str:
        return self.order[0][0]

    @property
    def best_match(self) -> Match:
        return self.order[0][1]

    @property
    def runner_up(self) -> str:
        return self.order[1][0]

    @property
    def margin(self) -> int:
        """Score gap between the best and second-best basket."""
        return self.order[0][1].score - self.order[1][1].score

    @property
    def tie(self) -> bool:
        return self.margin == 0

    @property
    def exact_baskets(self) -> List[str]:
        """Every basket that reproduces the key exactly (the oracle ceiling)."""
        return [cid for cid, m in self.order if m.exact]


def rank(key: Mapping[str, int], baskets: Mapping[str, Mapping[str, int]]) -> Ranking:
    """Order candidate baskets by score.

    Ties are broken by cell id purely so the function is deterministic; the
    tie is still *reported* via `Ranking.tie`, and the policy layer refuses to
    spend an attempt on it.
    """
    if len(baskets) < 2:
        raise ValueError(f"need at least 2 candidate baskets, got {len(baskets)}")
    scored = [(cid, match(key, bag)) for cid, bag in baskets.items()]
    scored.sort(key=lambda t: (-t[1].score, t[0]))
    return Ranking(scored)


def decide(ranking: Ranking, on_tie: str = "recycle") -> Tuple[str, str | None]:
    """Turn a ranking into an action.

    Returns ``("answer", cell_id)`` or ``("recycle", None)``.

    A tie is a coin flip by construction: two baskets scored identically, so
    nothing in the observation distinguishes them. Since the answer has not
    been submitted yet, requesting a fresh challenge strictly dominates a 50/50
    guess -- it costs the same one attempt but carries a full strip's worth of
    information instead of a coin's.
    """
    if on_tie not in ("recycle", "guess"):
        raise ValueError("on_tie must be 'recycle' or 'guess'")
    if ranking.tie and on_tie == "recycle":
        return "recycle", None
    return "answer", ranking.best
