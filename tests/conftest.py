import os
import sys

# Ensure project root is on sys.path so 'src' behaves as a package during tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
