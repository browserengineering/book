#!/usr/bin/env python3

import ast
import outlines
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count how many lines chapter has, after resolving imports")
    parser.add_argument("file", type=argparse.FileType(), nargs="+")
    args = parser.parse_args()

    for f in args.file:
        tree = ast.parse(f.read(), f.name)
        tree2 = outlines.ResolveImports().visit(tree)
        print(f.name, ast.unparse(ast.fix_missing_locations(tree2)).count("\n"), sep="\t")
