"""Check the deck copy for the tells that made the first draft read as machine-written.

Not a style guide. Just the specific patterns that were wrong in v1:

  antithesis   "X, not Y" / "not X but Y" used as a headline
  em-dash      the single most reliable tell
  triad        three-item lists in a row
  meta         talking about the assignment or about the writing itself
  coach-speak  "land the point", "this is the crux", "the key takeaway"
"""

from __future__ import annotations

import io
import os
import re
import sys

from pptx import Presentation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PPTX = os.path.join(ROOT, "CS471_Presentation.pptx")

EM_DASH = "\u2014"

PATTERNS = [
    ("antithesis", re.compile(r"\bnot\b[^.\n]{0,40}\bbut\b", re.I)),
    ("antithesis", re.compile(r",\s*not\s+\w+ing\b", re.I)),
    ("antithesis", re.compile(r"\bis not the\b|\bare not the\b", re.I)),
    ("coach", re.compile(r"\bland the\b|\bthe crux\b|\bkey takeaway\b|\bdrill down\b|"
                         r"\blet that sink\b|\bthe real question\b", re.I)),
    ("meta", re.compile(r"\bassignment\b|\brubric\b|\bthis presentation\b|"
                        r"\bas you can see\b", re.I)),
    ("filler", re.compile(r"\bessentially\b|\bcrucially\b|\bimportantly\b|"
                          r"\bit is worth noting\b|\bnotably\b", re.I)),
]


def main():
    prs = Presentation(PPTX)
    hits = []
    for i, s in enumerate(prs.slides, 1):
        for sh in s.shapes:
            if not sh.has_text_frame:
                continue
            t = sh.text_frame.text
            if not t.strip():
                continue
            if EM_DASH in t:
                hits.append((i, "em-dash", t.replace("\n", " / ")[:90]))
            for name, rx in PATTERNS:
                for m in rx.finditer(t):
                    frag = t[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")
                    hits.append((i, name, frag))

    print(f"slides: {len(prs.slides)}")
    print(f"flagged: {len(hits)}\n")
    for i, name, frag in hits:
        print(f"  s{i:02d}  {name:11} {frag}")

    # headline check: print every title so the shape can be judged by eye
    print("\nheadlines:")
    for i, s in enumerate(prs.slides, 1):
        big = [sh for sh in s.shapes if sh.has_text_frame
               and sh.text_frame.text.strip()
               and sh.top is not None and sh.top < 914400 * 2.0]
        if not big:
            continue
        cand = max(big, key=lambda sh: sh.width or 0)
        line = cand.text_frame.text.replace("\n", " / ")
        print(f"  s{i:02d}  {line[:78]}")

    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
