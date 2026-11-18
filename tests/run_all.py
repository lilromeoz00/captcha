"""Run the whole suite with one command and a readable summary.

    python tests/run_all.py            # everything
    python tests/run_all.py --fast     # skip the model-dependent tests

`fast` mode is what you run while editing the scoring math on a laptop with no
GPU: it covers the decision core only and finishes in milliseconds.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)


def main(argv):
    fast = "--fast" in argv
    loader = unittest.TestLoader()
    if fast:
        names = ["test_multiset", "test_geometry"]
    else:
        names = ["test_multiset", "test_geometry", "test_detector", "test_end_to_end"]
    suite = loader.loadTestsFromNames(names)
    print(f"running {suite.countTestCases()} tests "
          f"({'fast: decision core only' if fast else 'full: includes real model'})\n")
    res = unittest.TextTestRunner(verbosity=2).run(suite)
    print("\n" + "=" * 60)
    print(f"ran {res.testsRun}  failures {len(res.failures)}  "
          f"errors {len(res.errors)}  skipped {len(res.skipped)}")
    print("PASS" if res.wasSuccessful() else "FAIL")
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
