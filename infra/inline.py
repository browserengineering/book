#!/usr/bin/env python3

import asttools
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count how many lines chapter has, after resolving imports")
    parser.add_argument("file", type=argparse.FileType(), nargs="+")
    args = parser.parse_args()

    for f in args.file:
        tree = asttools.parse(f.read(), f.name)
        tree = asttools.inline(tree)
        print(asttools.unparse(tree))
