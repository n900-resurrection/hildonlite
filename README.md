# hildonlite

Hildon and GTK 2 windows from **Python 3** on the Nokia N900 (Maemo 5). There are no PyGTK (Python 2 only) and no PyGObject bindings (no
GObject Introspection data for GTK 2 and Hildon), so this module calls the libraries (`libgtk-x11-2.0`, `libhildon-1`, `libgobject-2.0`) through
`ctypes` and hides the details: argument types, return values, callbacks that must not be garbage collected.
Pure Python, no dependencies, one file.

```python
import hildonlite as hl

hl.init()
win = hl.Window("Hello")
box = hl.VBox(spacing=8)
box.add(hl.Label("Python 3 + Hildon"), expand=True)
box.add(hl.Button("Quit", "closes the window", on_clicked=lambda b: hl.quit()))
win.add(box)
win.show()
hl.main()
```

## What is in it
| | |
|---|---|
| `Window` | `HildonStackableWindow`, `set_title`, `set_menu(AppMenu)` |
| `Box`, `VBox`, `HBox` | `add(widget, expand=, fill=, padding=)` |
| `Label`, `Button` | `HildonButton` with title and value (`size=THUMB` finger-sized, default; `FINGER` is thinner) |
| `Entry`, `TextView` | `get_text`/`set_text`; `Entry.set_completion(words)` is an `EntryCompletion` |
| `PannableArea` | kinetic scrolling (`add` for widgets that scroll by themselves, `add_viewport` for the others) |
| `AppMenu`, `Banner` | the menu of the title bar, the grey information banner |
| `ListStore`, `ListView` | a text list (`HildonTreeView`): `append`, `rows`, `clear`, `selected`, `activate` |
| `Dialog`, `confirm`, `info` | dialogs, Hildon notes |
| `timeout`, `idle`, `main`, `quit` | main loop and timers |

Signals: `widget.connect("clicked", fn)`; `fn` gets the widget object. An exception in a handler is printed and does not stop the main loop.
Anything the layer does not cover can be called the same way through `hildonlite._fn("gtk" | "hil" | "gobj" | "glib", "c_function_name", restype, *argtypes)`.

## Install
On the phone (needs our Python 3.11, package `python3.11` from the apt repository of this project):
```
apt-get install python3-hildonlite                     # the .deb of the project repository, installs into /opt/python3/.../site-packages
python3 -m pip install git+https://github.com/n900-resurrection/hildonlite    # or with pip (pure Python, builds on the phone)
```
Examples are in `examples/` (the .deb puts them to `/opt/python3/share/doc/python3-hildonlite/examples`). Run as user inside the Hildon session (`DISPLAY=:0`).

## Development and tests
The repository is a submodule of [N900](https://github.com/elPytel/N900) (the cross-build environment). There, without a phone:
```
make hildon-run APP=hildonlite VNC=1     # the demo on the emulated desktop
make hildon-test                         # unittest suite (tests/test_hildonlite.py) with the real GTK 2 / Hildon libraries under qemu-user
make debs APP=hildonlite                 # build/deb/python3-hildonlite_*_armel.deb
```
On the phone: `DISPLAY=:0 python3 tests/test_hildonlite.py` (opens and closes a few windows).

Known behaviour: with the Hildon theme the selection of a `HildonTreeView` stays empty (a tap only activates a row), so `ListView.selected()`
returns the row of the last `row-activated` (or the one set by `select()`).

License: MIT.
