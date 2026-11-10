#!/bin/bash
# Package hildonlite as a .deb for Maemo 5: make -C apps/hildonlite deb
# The module goes to the site-packages of our Python 3.11 (/opt/python3), so `import hildonlite` works for every program, like after pip install.
# Output: /project/build/deb/python3-hildonlite_<VERSION>-<REV>_armel.deb
set -euo pipefail
PROJ=/project
. "$PROJ/scripts/debpack.sh"

PKG=python3-hildonlite
VERSION="${VERSION:-0.1.0}"
STAGE="$PROJ/build/deb/stage-$PKG"
HERE="$PROJ/apps/hildonlite"
SP=opt/python3/lib/python3.11/site-packages

rm -rf "$STAGE"
mkdir -p "$STAGE/$SP/hildonlite" "$STAGE/opt/python3/share/doc/python3-hildonlite/examples"
install -m 644 "$HERE/hildonlite/__init__.py" "$STAGE/$SP/hildonlite/__init__.py"
install -m 644 "$HERE/examples/"*.py "$STAGE/opt/python3/share/doc/python3-hildonlite/examples/"
install -m 644 "$HERE/README.md" "$HERE/LICENSE" "$STAGE/opt/python3/share/doc/python3-hildonlite/"

SECTION=user/development
DEPENDS="python3.11"
DISPLAY_NAME="hildonlite (Python 3)"
SHORT_DESC="Hildon and GTK 2 windows from Python 3 (ctypes layer)"
LONG_DESC="Python module hildonlite: Window, Box, Label, Button, Entry (with completion), TextView, PannableArea, AppMenu, lists, dialogs and timers over GTK 2 and Hildon,
called through ctypes, because PyGTK exists only for Python 2 and PyGObject has no GTK 2 / Hildon typelibs.
Use: import hildonlite as hl. Examples: /opt/python3/share/doc/python3-hildonlite/examples. The same source installs with pip (pip install git+https://github.com/n900-resurrection/hildonlite)."
debpack_build
