#!/bin/bash
# Pure Python, nothing to compile: only check that the sources compile (syntax) with the Python of the Workshop.
set -euo pipefail
cd /project/apps/hildonlite
python3 -I -m py_compile hildonlite/__init__.py examples/demo.py examples/demo_list.py tests/test_hildonlite.py
find . -name __pycache__ -prune -exec rm -rf {} +
echo "hildonlite: sources compile"
