#!/usr/bin/env python

import doctest
import os, sys
import json
import compare
import importlib
from unittest import mock

def test_compare(chapter, metadata, key, language, fname):
    value = metadata[key]
    print(f"Comparing chapter {chapter} with {key} {value}")
    with open("../book/" + chapter) as book, open(value) as code:
        failure, count = compare.compare_files(book, code, language, fname)
    if failure:
        print(f"  Differences in {failure} / {count} blocks")
    else:
        print(f"  Matched {count} blocks")
    return failure

def run_tests(chapter, file_name):
    print(f"Testing chapter {chapter} in {file_name}")
    failure, count = doctest.testfile(os.path.abspath(file_name), module_relative=False)
    if failure:
        print(f"  Failed {failure} / {count} tests")
    else:
        print(f"  Passed {count} tests")

    # This ugly code reloads all of our modules from scratch, in case
    # a test makes a mutation to a global for some reason
    src_dir = os.path.split(os.path.realpath(file_name))
    for name, mod in list(sys.modules.items()):
        if hasattr(mod, "__file__") and mod.__file__ and \
           os.path.realpath(mod.__file__).startswith(src_dir):
            importlib.reload(mod)
    mock.patch.stopall()
        
    return failure

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

    ran_one = False
    failure = 0
    for chapter, metadata in data["chapters"].items():
        if args.chapter and args.chapter != "all" and chapter != args.chapter: continue
        for key, value in metadata.items():
            if key == "disabled": continue
            if args.key and key != args.key: continue

            ran_one = True
            if key == "tests":
                failure += run_tests(chapter, value)
            elif key == "lab":
                failure += test_compare(chapter, metadata, "lab", "python", None)
            elif key == "stylesheet":
                failure += test_compare(chapter, metadata, "stylesheet", "css", None)
            elif key == "runtime":
                failure += test_compare(chapter, metadata, "runtime", "javascript", None)
            elif isinstance(value, str) and ".py" in value:
                failure += test_compare(chapter, metadata, key, "python", key)
            elif isinstance(value, str) and ".js" in value:
                failure += test_compare(chapter, metadata, key, "javascript", key)

    if not ran_one:
        if args.chapter:
            print(f"Could not find chapter {args.chapter}")
            print("  Extant chapters:", ", ".join(data["chapters"].keys()))
        elif args.key:
            print(f"Could not find key {args.key}")
            key_sets = [set(list(metadata.keys())) for chapter, metadata in data["chapters"].items()]
            keys = set([]).union(*key_sets) - set(["disabled"])
            print("  Extant chapters:", ", ".join(keys))
        failure = 1
            

    sys.exit(failure)
