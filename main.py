#!/usr/bin/env python3
"""Main entry point for Gmail Inbox Organizer."""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tui import main

if __name__ == "__main__":
    main()