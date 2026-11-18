"""detector.py -- the perception half of the agent.

Wraps the trained YOLO26s detector. This is the *only* module that touches
torch, so the decision logic can be imported and tested on a machine with no
GPU and no weights.

The detector is a single-stage object detector used purely as a class-conditional
counting device: given a 200x200 tile it returns boxes with class ids and
confidences, which the ranker collapses into a multiset of vegetable names.
Localisation precision is therefore close to irrelevant to the task -- only
"did it find the object, and did it name it right" matters.
"""

from __future__ import annotations

import os
from typing import Dict, List, Sequence, Tuple

from .multiset import CLASSES

Detection = Tuple[str, float]  # (class name, confidence)


class VeggieDetector:
    """Thin, deterministic wrapper around Ultralytics YOLO.

    Parameters
    ----------
    weights : path to a .pt checkpoint
    conf    : confidence floor. 0.4 is not a default -- calibration measured
              that boxes in the 0.3-0.5 band are right only 17-25% of the time
              (they are ground-clover texture), and raising 0.3 -> 0.4 moved
              task accuracy from 47/48 to 48/48.
    imgsz   : inference tile size; must match training (320).
    device  : "cpu", "cuda:0", or None to let Ultralytics choose.
    """

    def __init__(
        self,
        weights: str,
        conf: float = 0.4,
        imgsz: int = 320,
        device: str | None = None,
    ) -> None:
        self.weights = weights
        self.conf = conf
        self.imgsz = imgsz
        self.device = device
        self._model = None

    def _load(self):
        if self._model is None:
            if not os.path.exists(self.weights):
                raise FileNotFoundError(f"weights not found: {self.weights}")
            from ultralytics import YOLO  # imported lazily: keeps the core testable

            self._model = YOLO(self.weights)
        return self._model

    def detect(self, crops: Sequence) -> List[List[Detection]]:
        """Run one batched forward pass over a list of tiles.

        Returns, per tile, a list of (class_name, confidence) sorted by
        descending confidence. Nothing is capped here -- trimming is a ranking
        policy, so it lives in `ranker`.
        """
        model = self._load()
        if not crops:
            return []
        results = model.predict(
            list(crops),
            imgsz=self.imgsz,
            conf=self.conf,
            verbose=False,
            device=self.device,
        )
        out: List[List[Detection]] = []
        for r in results:
            dets = [
                (CLASSES[int(b.cls)], float(b.conf))
                for b in r.boxes
                if 0 <= int(b.cls) < len(CLASSES)
            ]
            dets.sort(key=lambda t: -t[1])
            out.append(dets)
        return out

    def detect_counts(self, crops: Sequence) -> List[Dict[str, int]]:
        """Per-tile multiset of detected classes."""
        bags: List[Dict[str, int]] = []
        for dets in self.detect(crops):
            bag: Dict[str, int] = {}
            for cls, _conf in dets:
                bag[cls] = bag.get(cls, 0) + 1
            bags.append(bag)
        return bags
