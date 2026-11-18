"""Verify the generated PPTX: structure, no off-slide shapes, no empty slides."""
import os
import sys

from pptx import Presentation
from pptx.util import Emu

p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'CS471_Presentation.pptx')
prs = Presentation(p)

W = prs.slide_width
H = prs.slide_height
print('slide size: %.2f x %.2f in' % (W / 914400, H / 914400))
print('slides:', len(prs.slides))

bad = []
for i, s in enumerate(prs.slides, 1):
    n = len(s.shapes)
    if n < 5:
        bad.append('slide %d has only %d shapes' % (i, n))
    for sh in s.shapes:
        try:
            l, t, w, h = sh.left, sh.top, sh.width, sh.height
        except Exception:
            continue
        if l is None:
            continue
        if l < -Emu(9144) or t < -Emu(9144):
            bad.append('slide %d: shape off top/left (%s)' % (i, sh.shape_type))
        if l + w > W + Emu(18288) or t + h > H + Emu(18288):
            bad.append('slide %d: shape overflows (%s at %.2f,%.2f)' %
                       (i, sh.shape_type, l / 914400, t / 914400))

print('problems:', len(bad))
for b in bad:
    print('  ' + b)

# text coverage: make sure no slide is effectively empty
for i, s in enumerate(prs.slides, 1):
    chars = 0
    for sh in s.shapes:
        if sh.has_text_frame:
            chars += len(sh.text_frame.text)
    print('  slide %2d: %2d shapes, %4d chars' % (i, len(s.shapes), chars))

sys.exit(1 if bad else 0)
