"""
Python wrap for running unittest and exit with error code.
"""

import sys
import unittest


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("Path to module like epcore/filemanager must be specified")

    loader = unittest.TestLoader()
    suite = loader.discover(sys.argv[1])

    runner = unittest.TextTestRunner()
    if runner.run(suite).errors:
        exit(-1)
