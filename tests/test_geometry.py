"""Geometry tests: the tiling must be a partition of a 1600x400 strip.

Run:  python -m unittest tests.test_geometry -v
"""

import unittest

from PIL import Image

from solver import geometry


class TestCellBoxes(unittest.TestCase):
    def test_nine_tiles(self):
        self.assertEqual(len(geometry.cell_ids()), 9)
        self.assertEqual(geometry.cell_ids(), ["0", "1", "2", "3", "4", "5", "6", "7", "S"])

    def test_baskets_run_left_to_right_on_the_top_row(self):
        for i in range(8):
            x0, y0, x1, y1 = geometry.cell_box(str(i))
            self.assertEqual((x0, y0), (i * 200, 0))
            self.assertEqual((x1 - x0, y1 - y0), (200, 200))

    def test_key_is_bottom_left(self):
        self.assertEqual(geometry.cell_box("S"), (0, 200, 200, 400))

    def test_baskets_tile_the_top_row_exactly(self):
        spans = [geometry.cell_box(str(i)) for i in range(8)]
        self.assertEqual(spans[0][0], 0)
        self.assertEqual(spans[-1][2], geometry.STRIP_W)
        for a, b in zip(spans, spans[1:]):
            self.assertEqual(a[2], b[0], "gap or overlap between adjacent baskets")

    def test_tiles_are_disjoint(self):
        """Overlapping tiles would count a boundary vegetable twice."""
        boxes = [geometry.cell_box(c) for c in geometry.cell_ids()]
        for i, (ax0, ay0, ax1, ay1) in enumerate(boxes):
            for bx0, by0, bx1, by1 in boxes[i + 1:]:
                overlap = ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1
                self.assertFalse(overlap)

    def test_bad_cell_id(self):
        with self.assertRaises(KeyError):
            geometry.cell_box("8")
        with self.assertRaises(KeyError):
            geometry.cell_box("-1")


class TestValidation(unittest.TestCase):
    def test_accepts_the_expected_size(self):
        geometry.validate((1600, 400))

    def test_rejects_rescaled_input(self):
        with self.assertRaises(geometry.StripGeometryError):
            geometry.validate((800, 200))

    def test_rejects_full_strip_shape_from_an_older_pipeline(self):
        with self.assertRaises(geometry.StripGeometryError):
            geometry.validate((1000, 400))


class TestSliceStrip(unittest.TestCase):
    def _strip(self):
        """Nine tiles, each painted a unique flat colour, so slicing is checkable."""
        img = Image.new("RGB", (1600, 400), (0, 0, 0))
        for cid in geometry.cell_ids():
            x0, y0, x1, y1 = geometry.cell_box(cid)
            colour = (int(cid) + 1, 0, 0) if cid != "S" else (0, 0, 255)
            img.paste(colour, (x0, y0, x1, y1))
        return img

    def test_each_tile_keeps_its_own_pixels(self):
        tiles = geometry.slice_strip(self._strip())
        self.assertEqual(set(tiles), set(geometry.cell_ids()))
        for cid, tile in tiles.items():
            self.assertEqual(tile.size, (200, 200))
            expect = (0, 0, 255) if cid == "S" else (int(cid) + 1, 0, 0)
            self.assertEqual(tile.getpixel((100, 100)), expect, f"tile {cid} mis-sliced")

    def test_rejects_a_non_strip(self):
        with self.assertRaises(geometry.StripGeometryError):
            geometry.slice_strip(Image.new("RGB", (400, 400)))


if __name__ == "__main__":
    unittest.main()
