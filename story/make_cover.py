"""Cover image for a story script.

Usage (from the repository root): python story/make_cover.py stories/<name>.txt output/<name>.thumbnail.png
Runs the shared thumb.py, but with the story parser, so directed scripts (lines starting with '>') are understood.
"""
import os, runpy, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.argv = ["thumb.py"] + sys.argv[1:]
runpy.run_path(os.path.join(ROOT, "thumb.py"), run_name="__main__")
