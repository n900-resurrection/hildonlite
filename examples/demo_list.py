# Demo of the list, entry completion and dialogs of hildonlite. With DEMO_CHECK=1 it also checks the API without a human (exit code 1 on a failure).
# make hildon-run SCRIPT=apps/hildonlite/examples/demo_list.py SHOT=/project/build/shot.png
import os, sys
try:
    import hildonlite as hl
except ImportError:                       # not installed: use the copy next to the examples
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    import hildonlite as hl

if not hl.init():
    sys.exit("no X display")
win = hl.Window("Contacts (demo)")
store = hl.ListStore(2)
for name, phone in (("Alice Example", "+420 555 010 001"), ("Bob Sample", "+420 555 010 002"), ("Carol Test", "+420 555 010 003"),
                    ("Dan Demo", "+420 555 010 004"), ("Eve Fictional", "+420 555 010 005")):
    store.append([name, phone])
lv = hl.ListView(store)
area = hl.PannableArea(); area.add(lv)
entry = hl.Entry("Al")
entry.set_completion([r[0] for r in store.rows()])
status = hl.Label("tap a row")
lv.connect("row-activated", lambda w: status.set_text("selected: %s" % (lv.selected() or ["-"])[0]))
root = hl.VBox(spacing=6)
root.add(entry); root.add(area, expand=True); root.add(status)
root.add(hl.Button("Delete all...", on_clicked=lambda b: hl.confirm(win, "Delete all contacts?") and store.clear()))
win.add(root); win.show()

fails = []
def check():
    def ok(cond, what):
        print(("ok    " if cond else "FAIL  ") + what)
        if not cond: fails.append(what)
    ok(store.rows()[1] == ["Bob Sample", "+420 555 010 002"], "ListStore.rows() returns the strings that were appended")
    lv.select(2)
    ok(lv.selected() == ["Carol Test", "+420 555 010 003"], "ListView.select()/selected() round trip")
    lv.activate(4)
    ok(lv.selected() == ["Eve Fictional", "+420 555 010 005"] and status.get_text() == "selected: Eve Fictional", "a tap (row-activated) makes the row current and calls the handler")
    # a dialog answers itself: the response is sent from a timer while the nested main loop of run() is active
    d = hl.Dialog("Name", win); e = hl.Entry("typed"); d.body.add(e); d.add_button("OK", hl.OK); d.add_button("Cancel", hl.CANCEL)
    hl.timeout(300, lambda: (ctypes_emit(d, hl.OK), False)[1])
    r = d.run()
    ok(r == hl.OK and e.get_text() == "typed", "Dialog.run() returns the response of a button")
    d.destroy()
    store.clear()
    ok(store.rows() == [], "ListStore.clear()")
    hl.quit(); return False

def ctypes_emit(dialog, response):
    import ctypes
    f = hl._fn("gtk", "gtk_dialog_response", None, ctypes.c_void_p, ctypes.c_int); f(dialog.ptr, response)

if os.environ.get("DEMO_CHECK"):
    hl.timeout(1500, check)
if os.environ.get("DEMO_TIMEOUT"):
    hl.timeout(int(os.environ["DEMO_TIMEOUT"]) * 1000, lambda: hl.quit() or False)
hl.main()
sys.exit(1 if fails else 0)
