"""Add speaker notes to the deck, and write the backup demonstration sheet.

    python presentation/add_notes.py

Notes are stored in the PPTX itself (PowerPoint's Notes pane), so the presenter
has the script in the same file that gets submitted. The backup sheet is a
separate markdown file for the case where the live machine fails.
"""

from __future__ import annotations

import os

from pptx import Presentation

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PPTX = os.path.join(ROOT, "CS471_Presentation.pptx")
BACKUP = os.path.join(HERE, "BACKUP_DEMO.md")

# One entry per slide, in order. Written to be spoken, not read aloud verbatim.
NOTES = [
    # 1 title
    "0:00  Open with the operational claim, not the technology. One sentence: access to "
    "defended services is gated by a visual challenge, the commercial answer is rented "
    "human labour, and this project replaces that with a local computation. "
    "State the headline result early: 48 of 48 with a defensible lower bound of 92.6%.",

    # 2 problem
    "0:45  Three numbers carry this slide: $2 per 1,000, about 10% reliable, and "
    "human latency. Land the third point hard, because it is the one that matters for a "
    "military use case: the operator rents a population it cannot audit, cannot surge, "
    "and which learns the target set. That is a security problem, not a cost problem.",

    # 3 multiset
    "1:30  This is the slide that establishes the problem is not classification. Read the "
    "two cards: the key asks for two onions and two potatoes; scene 4 has two onions, one "
    "potato and one corn. Every object in scene 4 was detected correctly, and scene 4 is "
    "still wrong. If asked, the measured evidence is 73% for a crop-and-classify pipeline "
    "versus 83% for joint detection on the same data.",

    # 4 algorithm
    "2:15  Walk the pipeline left to right. Emphasise the split: the detector is the only "
    "learned component, and everything after it is closed-form arithmetic. Then read the "
    "scoring function and point at the 10 and the 1. Do not over-explain the formula; the "
    "next slide justifies the asymmetry. Mention that min(K,B) per class is exact, so there "
    "is no assignment problem to solve.",

    # 5 design decisions
    "3:15  Two decisions, each with a justification. Left: the asymmetry is justified by the "
    "measured error profile, 99.0% recall against 2.1% false-positive leakage, so the error "
    "is one-sided. Right: abstention. The key argument is that a tie is a coin toss and a new "
    "challenge costs nothing, so abstaining weakly dominates guessing. Note that a softmax "
    "cannot express this, which is why the decision layer is separate from the network.",

    # 6 demo
    "4:00  Run the live command. It takes about two seconds. Point at the green border, then "
    "at the score printed on each tile, then at the margin on the last line. If the machine "
    "fails, switch to this slide: the frame shown is the actual output, and the terminal text "
    "is verbatim. The backup sheet in presentation/BACKUP_DEMO.md has the same material.",

    # 7 baselines
    "5:00  The methodological point first: all six baselines consume identical cached detector "
    "output, so the differences are attributable to the decision rule. Then read the numbers. "
    "The two that disregard the key stay at chance, which proves localisation alone is not "
    "enough. The McNemar result is 36 corrected and 0 regressed, p = 2.9e-11.",

    # 8 perception
    "5:45  Perception is not the bottleneck. Recall 99.0%, mAP50 0.983. Then the ceiling "
    "decomposition, which is the most important analysis in the project: on 39 of 48 frames "
    "an exact candidate existed, and the ranker took it 39 times. The remaining nine were "
    "answered correctly by partial scoring. If asked why this matters, it separates a "
    "perception failure from a decision failure.",

    # 9 negative result
    "6:30  Volunteer this. The 10:1 asymmetry is not identifiable: a symmetric 1:1 penalty "
    "also scores 48 of 48, so McNemar returns p = 1. The set is saturated. The honest position "
    "is that 10 is justified by mechanism and by unit tests, not by a measured optimum. "
    "Expect a question here; answering it well is worth more than the result itself.",

    # 10 failure
    "7:15  The dominant failure is blur, not adversarial imagery. At radius 2.0 accuracy falls "
    "to 31 of 48, because fixed tiling mis-segments a degraded frame silently. Recompression is "
    "tolerated comparatively well. Operational reading: link quality and relay compression "
    "determine reliability, which tells you where engineering effort should go.",

    # 11 implications
    "8:00  Four points, one sentence each. Do not rush the fourth: the measured constraint is "
    "labels, not capacity, so the effective counter to a system like this is a puzzle whose "
    "rendering changes faster than labels can be collected. That is the finding worth briefing.",

    # 12 defence
    "8:45  Hold this slide in reserve for questions rather than presenting it. The four answers "
    "cover the most likely challenges. If time is short, skip to the closing line: the algorithm "
    "is correct and measured, and the one design claim the data do not support is reported "
    "rather than hidden.",
]


def main():
    prs = Presentation(PPTX)
    n = len(prs.slides)
    if len(NOTES) != n:
        raise SystemExit(f"have {len(NOTES)} notes for {n} slides")

    for slide, note in zip(prs.slides, NOTES):
        slide.notes_slide.notes_text_frame.text = note

    prs.save(PPTX)
    print(f"added speaker notes to {n} slides")

    total = 0
    for note in NOTES:
        # crude word count of the spoken guidance
        total += len(note.split())
    print(f"notes total ~{total} words; the timings assume 5-7 minutes of speech")


if __name__ == "__main__":
    main()
