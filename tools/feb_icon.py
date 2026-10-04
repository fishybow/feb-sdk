#!/usr/bin/env python3
"""
feb_icon.py - Flashiibo FEB App Icon Tool (Entrypoint alias for make_icon.py)
"""
import sys
import os

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS_DIR)

import make_icon

if __name__ == "__main__":
    make_icon.main()
