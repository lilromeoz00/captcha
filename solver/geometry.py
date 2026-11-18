"""geometry.py -- how the agent segments its observation into fixed tiles.

The challenge image is a single 1600x400 JPEG that is really nine 200x200 tiles
in a known layout:

    y=0   .. 200 : baskets 0 1 2 3 4 5 6 7   (8 candidate scenes, left to right)
    y=200 .. 400 : the key tile, in the bottom-left corner; the rest is blank

Two properties matter and both are enforced here rather than trusted:

1. **Tile size is fixed.** The detector is trained exclusively on 200x200
   crops. Feeding it a rescaled strip would silently mis-slice every tile and
   degrade the answer with no error message (measured: half-resolution input
   costs ~12.5 accuracy points). So `validate` is a hard gate, not a warning.
2. **The tiling is a partition.** Cells must not overlap, or a vegetable on a
   boundary would be counted twice and corrupt the multiset.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

CELL: int = 200
N_BASKETS: int = 8
KEY_ID: str = "S"

STRIP_W: int = CELL * N_BASKETS
STRIP_H: int = CELL * 2

Box = Tuple[int, int, int, int]  # x0, y0, x1, y1


class StripGeometryError(ValueError):
    """Raised when an input image is not a 1600x400 challenge strip."""


def cell_ids() -> List[str]:
    """All tile ids: the eight baskets, then the key tile last."""
    return [str(i) for i in range(N_BASKETS)] + [KEY_ID]


def cell_box(cell_id: str) -> Box:
    """Pixel bounds of one tile, half-open in x1/y1."""
    if cell_id == KEY_ID:
        x0, y0 = 0, CELL
    else:
        i = int(cell_id)
        if not 0 <= i < N_BASKETS:
            raise KeyError(f"no such basket cell: {cell_id!r}")
        x0, y0 = i * CELL, 0
    return (x0, y0, x0 + CELL, y0 + CELL)


def validate(size: Tuple[int, int]) -> None:
    """Reject anything that is not exactly 1600x400."""
    if tuple(size) != (STRIP_W, STRIP_H):
        raise StripGeometryError(
            f"expected a {STRIP_W}x{STRIP_H} strip, got {size[0]}x{size[1]} "
            f"-- rescale before ranking, never inside the tile slicer"
        )


def slice_strip(img) -> Dict[str, object]:
    """Cut a PIL image into its nine tiles, keyed by cell id."""
    validate(img.size)
    return {cid: img.crop(cell_box(cid)) for cid in cell_ids()}
