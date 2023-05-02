#!/usr/bin/env python

import doctest
import os, sys
import json
import compare
import importlib
from unittest import mock
from pathlib import Path

try:
    from blessings import Terminal
except ImportError:
    class Terminal:
        def bold(self, s): return s
        def red(self, s): return s
        def green(self, s): return s

IGNORE_FILES = [
    "LICENSE",
    "__pycache__",
    "*.hints",
    "test*.py",
    "Broken_Image.png",
    ".*",
    "wbetools.py",

    # These are from the old reflow chapter---to be deleted once ch16 is mostly done
    "test10.js",
    "test10.html",
]

def test_compare(chapter, value, language, fname):
    with open("../book/" + chapter) as book, open(value) as code:
        return compare.compare_files(book, code, language, fname)

def run_tests(chapter, file_name):
    failure, count = doctest.testfile(os.path.abspath(file_name), module_relative=False)

    # This ugly code reloads all of our modules from scratch, in case
    # a test makes a mutation to a global for some reason
    src_dir = os.path.split(os.path.realpath(file_name))[0]
    for name, mod in list(sys.modules.items()):
        if hasattr(mod, "__file__") and mod.__file__ and \
           os.path.realpath(mod.__file__).startswith(src_dir) and \
           mod.__file__.endswith("py"):
            importlib.reload(mod)
    mock.patch.stopall()
        
    return failure, count

if __name__ == "__main__":
    import sys, argparse
    argparser = argparse.ArgumentParser(description="Compare book blocks to teacher's copy")
    argparser.add_argument("config", type=str)
    argparser.add_argument("--chapter", type=str)
    argparser.add_argument("--key", type=str)
    args = argparser.parse_args()

    with open(args.config) as f:
        data = json.load(f)
        chapters = data["chapters"]

    src_path = os.path.abspath("src/")
    os.chdir(src_path)
    sys.path.insert(0, src_path)

    t = Terminal()
    results = {}
    for chapter, metadata in data["chapters"].items():
        if args.chapter and args.chapter != "all" and chapter != args.chapter: continue
        print(f"{t.bold(chapter)}: Running comparisons and tests")
        for key, value in metadata.items():
            if key == "disabled": continue
            if args.key and key != args.key: continue

            if key == "tests":
                print(f"  {t.bold(value)}: Testing {chapter}...", end=" ")
                results[value] = run_tests(chapter, value)
                if not results[value][0]: print(t.green("pass"))
            elif key == "lab":
                print(f"  {t.bold(value)}: Comparing {chapter}'s python...", end=" ")
                results[value] = test_compare(chapter, value, "python", None)
                if not results[value][0]: print(t.green("pass"))
            elif key == "stylesheet":
                print(f"  {t.bold(value)}: Comparing {chapter}'s CSS...", end=" ")
                results[value] = test_compare(chapter, value, "css", None)
                if not results[value][0]: print(t.green("pass"))
            elif key == "runtime":
                print(f"  {t.bold(value)}: Comparing {chapter}'s JS...", end=" ")
                results[value] = test_compare(chapter, value, "javascript", None)
                if not results[value][0]: print(t.green("pass"))
            elif isinstance(value, str) and ".py" in value:
                fn = key.split(".")[0]
                print(f"  {t.bold(value)}: Comparing {chapter}'s {fn}...", end=" ")
                results[value] = test_compare(chapter, value, "python", fn)
                if not results[value][0]: print(t.green("pass"))
            elif isinstance(value, str) and ".js" in value:
                fn = key.split(".")[0]
                print(f"  {t.bold(value)}: Comparing {chapter}'s {fn}...", end=" ")
                results[value] = test_compare(chapter, value, "javascript", fn)
                if not results[value][0]: print(t.green("pass"))
            elif isinstance(value, str) and ".css" in value:
                fn = key.split(".")[0]
                print(f"  {t.bold(value)}: Comparing {chapter}'s {fn}...", end=" ")
                results[value] = test_compare(chapter, value, "css", fn)
                if not results[value][0]: print(t.green("pass"))

    if not results:
        if args.chapter:
            print(f"Could not find chapter {args.chapter}")
            print("  Extant chapters:", ", ".join(data["chapters"].keys()))
        elif args.key:
            print(f"Could not find key {args.key}")
            key_sets = [set(list(metadata.keys())) for chapter, metadata in data["chapters"].items()]
            keys = set([]).union(*key_sets) - set(["disabled"])
            print("  Extant chapters:", ", ".join(keys))
        sys.exit(-1)

    if not args.chapter or args.chapter == "all":
        p = Path(".")
        all_files = set(p.iterdir())
        all_files -= set([Path(p) for p in results.keys()])
        for glob in IGNORE_FILES:
            all_files -= set(p.glob(glob))

        if all_files:
            print("Did not test these files:")
            for file in all_files:
                print("\t", file)
            sys.exit(-1)
            
    sys.exit(sum([failures for failures, count in results.values()]))
