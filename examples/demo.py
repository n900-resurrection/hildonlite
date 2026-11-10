# Demo of hildonlite: a counter, a text field, a scrolling text and the application menu.
# make hildon-run APP=hildonlite SHOT=/project/build/shot.png
import os, sys
try:
    import hildonlite as hl
except ImportError:                       # not installed: use the copy next to the examples
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    import hildonlite as hl

if not hl.init():
    sys.exit("no X display")

win = hl.Window("hildonlite demo")
count = [0]

root = hl.VBox(spacing=8)
title = root.add(hl.Label("<b>Python 3 + Hildon</b>", markup=True))
entry = root.add(hl.Entry("type here"))
counter = hl.Button("Clicked: 0", "tap to count", size=hl.THUMB)
def clicked(_b):
    count[0] += 1
    counter.set_title("Clicked: %d" % count[0])
    counter.set_value("last text: " + entry.get_text())
counter.connect("clicked", clicked)
root.add(counter)

text = hl.TextView("Kinetic scrolling in a PannableArea.\n" + "\n".join("Line %d: žluťoučký kůň" % i for i in range(1, 40)), editable=False)
area = hl.PannableArea()
area.add(text)
root.add(area, expand=True)
root.add(hl.Button("Quit", on_clicked=lambda b: hl.quit()))
win.add(root)

menu = hl.AppMenu()
menu.add("Reset", lambda b: (count.__setitem__(0, 0), counter.set_title("Clicked: 0")))
menu.add("Quit", lambda b: hl.quit())
win.set_menu(menu)
win.show()

if os.environ.get("DEMO_TIMEOUT"):                  # DEMO_TIMEOUT=seconds: ends by itself (tests, screenshots)
    hl.timeout(int(os.environ["DEMO_TIMEOUT"]) * 1000, lambda: hl.quit() or False)
hl.main()
