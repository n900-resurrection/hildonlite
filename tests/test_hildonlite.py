"""Tests of hildonlite (unittest, runs in Python 3 with the real GTK 2 / Hildon libraries, needs an X display).
Emulator (in the main repository N900):  make hildon-test
Phone (as user, in the Hildon session):   DISPLAY=:0 python3 tests/test_hildonlite.py
"""
import ctypes, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))      # the copy in this repository, not an installed one
import hildonlite as hl


def pump(ms=100):
    """Run the main loop for a while (signals, redraws) without blocking the test."""
    done = []
    hl.timeout(ms, lambda: (done.append(1), False)[1])
    it = hl._fn("gtk", "gtk_main_iteration_do", ctypes.c_int, ctypes.c_int)
    pending = hl._fn("gtk", "gtk_events_pending", ctypes.c_int)
    import time
    end = time.time() + ms / 1000 + 2
    while not done and time.time() < end:
        it(0) if pending() else time.sleep(0.01)


def setUpModule():
    if not hl.init():
        raise unittest.SkipTest("no X display")


class Widgets(unittest.TestCase):
    def test_scale_value_and_signal(self):
        seen = []
        s = hl.Scale(0, 10, 1, value=3, on_changed=lambda w: seen.append(w.get_value()))
        self.assertEqual(s.get_value(), 3)
        s.set_value(7)
        self.assertEqual(s.get_value(), 7)
        self.assertEqual(seen, [7])

    def test_picker_button_choice_and_signal(self):
        seen = []
        p = hl.PickerButton("Layout", ["Czech", "US", "Raw"], active=1, on_changed=lambda w: seen.append(w.get_active()))
        self.assertEqual(p.get_active(), 1)
        p.set_active(2)
        self.assertEqual(p.get_active(), 2)
        self.assertEqual(seen, [2])

    def test_check_button_toggle_and_signal(self):
        seen = []
        c = hl.CheckButton("Visible", active=True, on_toggled=lambda w: seen.append(w.get_active()))
        self.assertTrue(c.get_active())
        c.set_active(False)
        self.assertFalse(c.get_active())
        self.assertEqual(seen, [False])

    def test_entry_text(self):
        e = hl.Entry("abc")
        self.assertEqual(e.get_text(), "abc")
        e.set_text("žluťoučký")
        self.assertEqual(e.get_text(), "žluťoučký")

    def test_entry_changed_signal(self):
        seen = []
        e = hl.Entry("", on_changed=lambda w: seen.append(w.get_text()))
        e.set_text("x")
        self.assertEqual(seen[-1], "x")

    def test_label(self):
        l = hl.Label("one")
        self.assertEqual(l.get_text(), "one")
        l.set_text("two")
        self.assertEqual(l.get_text(), "two")

    def test_textview_roundtrip(self):
        t = hl.TextView("řádek 1\nline 2")
        self.assertEqual(t.get_text(), "řádek 1\nline 2")
        t.set_text("")
        self.assertEqual(t.get_text(), "")

    def test_button_clicked_signal(self):
        n = []
        b = hl.Button("Go", on_clicked=lambda w: n.append(w))
        hl._fn("gtk", "gtk_button_clicked", None, ctypes.c_void_p)(b.ptr)
        self.assertEqual(n, [b])                      # the handler gets the same Python object back

    def test_image_button_with_missing_file_falls_back_to_a_label(self):
        n = []
        b = hl.ImageButton("/nonexistent/x.png", on_clicked=lambda w: n.append(1), width=64, label="x")
        hl._fn("gtk", "gtk_button_clicked", None, ctypes.c_void_p)(b.ptr)
        self.assertEqual(n, [1])

    def test_handler_exception_does_not_kill_the_loop(self):
        b = hl.Button("Boom", on_clicked=lambda w: 1 / 0)
        hl._fn("gtk", "gtk_button_clicked", None, ctypes.c_void_p)(b.ptr)   # printed to stderr, no crash

    def test_completion_is_attached(self):
        e = hl.Entry()
        e.set_completion(["alpha", "beta"])
        comp = hl._fn("gtk", "gtk_entry_get_completion", ctypes.c_void_p, ctypes.c_void_p)(e.ptr)
        self.assertTrue(comp)


class Containers(unittest.TestCase):
    def test_drawing_area_has_an_x_window(self):
        w = hl.Window("t", quit_on_close=False)
        d = hl.DrawingArea(100, 80)
        w.add(d)
        w.show()
        pump(50)
        self.assertGreater(d.xid(), 0)
        w.destroy()

    def test_window_with_box_shows(self):
        w = hl.Window("t", quit_on_close=False)
        box = hl.VBox(spacing=4)
        box.add(hl.Label("x"))
        box.add(hl.HBox())
        w.add(box)
        menu = hl.AppMenu()
        menu.add("Item", lambda b: None)
        w.set_menu(menu)
        w.show()
        pump(50)
        w.destroy()


class Lists(unittest.TestCase):
    def setUp(self):
        self.store = hl.ListStore(2)
        for r in (["Alice Example", "1"], ["Bob Sample", "2"], ["Carol Test", "3"]):
            self.store.append(r)
        self.view = hl.ListView(self.store)

    def test_rows(self):
        self.assertEqual(self.store.rows()[1], ["Bob Sample", "2"])

    def test_non_ascii_rows(self):
        self.store.append(["Žofie Příklad", "ěščř"])
        self.assertEqual(self.store.rows()[-1], ["Žofie Příklad", "ěščř"])

    def test_select(self):
        self.assertIsNone(self.view.selected())
        self.view.select(2)
        self.assertEqual(self.view.selected(), ["Carol Test", "3"])

    def test_tap_activates_row(self):
        got = []
        self.view.connect("row-activated", lambda w: got.append(w.selected()))
        self.view.activate(1)
        self.assertEqual(got, [["Bob Sample", "2"]])      # the row is current before the handler runs

    def test_clear(self):
        self.store.clear()
        self.assertEqual(self.store.rows(), [])
        self.assertIsNone(self.view.selected())


class Dialogs(unittest.TestCase):
    def respond_later(self, dialog, response, ms=200):
        f = hl._fn("gtk", "gtk_dialog_response", None, ctypes.c_void_p, ctypes.c_int)
        hl.timeout(ms, lambda: (f(dialog.ptr, response), False)[1])

    def test_dialog_ok_keeps_content(self):
        d = hl.Dialog("Name")
        e = hl.Entry("typed")
        d.body.add(e)
        d.add_button("OK", hl.OK)
        d.add_button("Cancel", hl.CANCEL)
        self.respond_later(d, hl.OK)
        self.assertEqual(d.run(), hl.OK)
        self.assertEqual(e.get_text(), "typed")           # run() only hides the dialog
        d.destroy()

    def test_dialog_cancel(self):
        d = hl.Dialog("Name")
        d.add_button("Cancel", hl.CANCEL)
        self.respond_later(d, hl.CANCEL)
        self.assertEqual(d.run(), hl.CANCEL)
        d.destroy()


class Timers(unittest.TestCase):
    def test_flush_runs_pending_idle_handlers(self):
        n = []
        hl.idle(lambda: (n.append(1), False)[1])
        hl.flush()
        self.assertEqual(n, [1])

    def test_timeout_repeats_until_false(self):
        n = []
        hl.timeout(20, lambda: (n.append(1), len(n) < 3)[1])
        pump(400)
        self.assertEqual(len(n), 3)

    def test_exception_in_timer_stops_it(self):
        n = []
        hl.timeout(20, lambda: (n.append(1), 1 / 0)[1])
        pump(200)
        self.assertEqual(len(n), 1)

    def test_idle(self):
        n = []
        hl.idle(lambda: (n.append(1), False)[1])
        pump(100)
        self.assertEqual(n, [1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
