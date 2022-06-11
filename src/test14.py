from test12 import *
import threading

def print_display_list_skip_noops(display_list):
		for item in display_list:
				print_tree_skip_nooops(item)

def print_tree_skip_nooops(node, indent=0):
    if node.__repr__().find("no-op") >= 0:
        extra = 0
    else:
        print(" " * indent, node)
        extra = 2
    for child in node.children:
        print_tree_skip_nooops(child, indent + extra)
