"""Orcanium CLI — python -m orcanium.cli [subcommand] [options]"""

import sys
import os

# Ensure the parent package is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orcanium.cli.main import main

if __name__ == "__main__":
    main()
