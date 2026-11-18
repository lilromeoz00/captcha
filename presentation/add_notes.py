"""Add speaker notes to the deck, and write the backup demonstration sheet.

    python presentation/add_notes.py

Notes live in the PPTX notes pane, so the script travels with the submitted file.
Written the way I would actually scribble them: what to say, what to point at,
and what to skip if time runs out.
"""

from __future__ import annotations

import os

from pptx import Presentation

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PPTX = os.path.join(ROOT, "CS471_Presentation.pptx")

# One entry per slide, in order.
NOTES = [
    # 1 title
    "Skip the small talk. Open with the number.\n\n"
    "\"This is a solver for a count-based image challenge. It gets 48 out of 48 on "
    "hand-labelled frames, and I'll show where that number stops being trustworthy.\"\n\n"
    "Then move on. The title slide is not the place to explain anything.",

    # 2 problem
    "Point at the three cards as you say each number.\n\n"
    "The first two are the commercial reality: two dollars per thousand, ten percent "
    "reliable. Nobody argues with those.\n\n"
    "Spend your time on the third. We are renting people who can see what we are "
    "collecting. If someone asks why the Air Force would care about a captcha, that "
    "is the answer, and it has nothing to do with the two dollars.",

    # 3 multiset
    "This slide does one job: prove the task is not classification.\n\n"
    "Read the two cards out loud. Key wants two onions and two potatoes. Scene 4 has "
    "two onions, one potato, one corn. Every object in scene 4 was detected. Scene 4 "
    "is still wrong.\n\n"
    "If they push back on why we did not just use a classifier: 73% for crop and "
    "classify, 83% for joint detection, same data, and the detector actually used less "
    "training data.",

    # 4 algorithm
    "Move left to right, do not linger on any box.\n\n"
    "The one thing to land is the split: everything up to the multisets is learned, "
    "everything after is arithmetic. That is the answer if anyone asks why this is an "
    "AI project and not a scripting project.\n\n"
    "Read the formula once. Point at the 10 and the 1. The next slide explains them, "
    "so do not defend them yet.",

    # 5 design decisions
    "Two cards, one argument each.\n\n"
    "Left: we measured how the detector fails. 99% recall, 2% false positives. The "
    "error only goes one way, so pricing a miss ten times higher follows from that.\n\n"
    "Right: when the margin is zero, nothing has been submitted yet. Asking for a new "
    "challenge is free and guessing is a coin flip. That is the whole argument.\n\n"
    "If asked whether a softmax could do this: no, because a softmax always outputs a "
    "winner. It has no way to say it does not know.",

    # 6 demo
    "Run it live. Two seconds on CPU.\n\n"
    "Point at the green border, then the score printed on each tile, then the margin "
    "on the last line. Do not narrate the terminal output line by line, it is on the "
    "slide.\n\n"
    "If it fails, stay on this slide. The frame is the real output and the text is "
    "verbatim from the same command. Say so and keep going.",

    # 7 baselines
    "Lead with the method, not the bars.\n\n"
    "All six baselines ran on the same cached detections. That means the differences "
    "come from the decision rule, not from one model being better trained. This is the "
    "part a grader is listening for.\n\n"
    "Then the two that ignore the key. Twenty percent and twenty-five percent. Knowing "
    "where the vegetables are does not help if you never compare counts.",

    # 8 perception
    "Two numbers, then the interesting one.\n\n"
    "Recall 99%, mAP50 0.983. Fine. Nobody will argue.\n\n"
    "The right-hand card is the point. On 39 frames there was a scene that matched the "
    "key exactly, and it picked that scene 39 times out of 39. The other nine frames "
    "had no exact match because the detector lost something, and it still answered all "
    "nine correctly. That separates a perception failure from a decision failure, and "
    "it says the decision half is not what is costing us.",

    # 9 negative result
    "Bring this up yourself. Do not wait to be caught.\n\n"
    "A flat 1:1 penalty also scores 48 out of 48. Every frame is already answered, so "
    "the weighting has nothing left to change. Forty-eight frames cannot separate the "
    "two, and McNemar says p equals one.\n\n"
    "The honest line: ten is justified by how the detector fails and by unit tests that "
    "force a miss to rank below a surplus. It is not justified by a measured optimum, "
    "because this data has none.\n\n"
    "If someone asks whether that undermines the design, say no, it bounds the claim. "
    "We know what we showed and what we did not.",

    # 10 failure
    "Blur, not adversarial imagery.\n\n"
    "Radius 2.0 drops it to 31 out of 48. The reason is boring: the pipeline cuts fixed "
    "200-pixel tiles, so a soft frame gets cut in the wrong places and nothing throws "
    "an error. The answer just gets quietly worse.\n\n"
    "Compression it handles fine. So the practical constraint is the link, not the "
    "defender. That is where the next engineer should spend their time.",

    # 11 implications
    "One sentence per row. Do not read the paragraphs.\n\n"
    "Rows one and two are why this matters. Rows three and four are what we would do "
    "next.\n\n"
    "The fourth row is the one worth remembering: missed detections are essentially "
    "zero, so the limit is labels. The answer to this system is not a harder puzzle, "
    "it is one whose rendering changes faster than labels can be collected.",

    # 12 defence
    "Hold this slide back. Only show it if the questions start and you want to steer "
    "them.\n\n"
    "The four answers cover what has actually been asked. Section 4.4 of the report has "
    "the longer version of the second one if it turns into an argument.\n\n"
    "Closing line if you need one: the algorithm works and is measured, and the one "
    "claim the data does not support is written down in the report rather than left out.",
]


def main():
    prs = Presentation(PPTX)
    n = len(prs.slides)
    if len(NOTES) != n:
        raise SystemExit(f"have {len(NOTES)} notes for {n} slides")

    for slide, note in zip(prs.slides, NOTES):
        slide.notes_slide.notes_text_frame.text = note

    prs.save(PPTX)
    words = sum(len(x.split()) for x in NOTES)
    print(f"added speaker notes to {n} slides (~{words} words)")


if __name__ == "__main__":
    main()
