"""CS471 checkpoint agent: adversarial visual challenge solving.

Public surface:

    geometry  -- strip -> fixed 200x200 tiles (with a hard size gate)
    detector  -- YOLO26s wrapper (the only torch-dependent module)
    multiset  -- scoring / ranking / tie policy (pure Python)
    ranker    -- the end-to-end agent and its evaluation metrics
"""

from . import detector, geometry, multiset, ranker  # noqa: F401
from .detector import VeggieDetector  # noqa: F401
from .multiset import CLASSES, Match, Ranking, decide, match, rank  # noqa: F401
from .ranker import evaluate, rank_strip, solve_file  # noqa: F401

__all__ = [
    "CLASSES",
    "Match",
    "Ranking",
    "VeggieDetector",
    "decide",
    "detector",
    "evaluate",
    "geometry",
    "match",
    "multiset",
    "rank",
    "rank_strip",
    "ranker",
    "solve_file",
]
__version__ = "0.1.0-checkpoint"
