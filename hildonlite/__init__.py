"""hildonlite: a thin layer over ctypes for GTK 2 / Hildon (Maemo 5) from Python 3.

There are no PyGTK or PyGObject bindings of GTK 2 + Hildon for Python 3, so the libraries are called directly. This module hides the ctypes
details (argument types, return types, callbacks that must not be garbage collected) behind a few classes:

    Window, Box (VBox, HBox), Label, Button, ImageButton, Entry (with completion), TextView, PannableArea, DrawingArea, AppMenu, Banner, ListStore + ListView
    (GtkTreeView), Dialog and the ready-made confirm()/info(), plus init(), main(), quit(), timeout(), idle().

Example:
    import hildonlite as hl
    hl.init()
    win = hl.Window("Hello")
    box = hl.VBox(spacing=8)
    box.add(hl.Label("Python 3 + Hildon"), expand=True)
    box.add(hl.Button("Quit", "closes the window", on_clicked=lambda b: hl.quit()))
    win.add(box)
    win.show()
    hl.main()

Signals: widget.connect("clicked", callback); callback gets the widget object (like PyGTK, without user data).
Everything is wrapped lazily, so importing the module on a machine without GTK 2 is fine; init() reports the failure.
"""
import ctypes, os
from ctypes import c_void_p, c_int, c_uint, c_char_p, c_double

__all__ = ["init", "main", "quit", "flush", "timeout", "idle", "Widget", "Window", "Box", "VBox", "HBox", "Label", "Button", "ImageButton", "Entry",
           "TextView", "PannableArea", "DrawingArea", "AppMenu", "Banner", "ListStore", "ListView", "Dialog", "confirm", "info", "OK", "CANCEL", "THUMB", "FINGER", "AUTO", "HORIZONTAL", "VERTICAL"]

# HildonSizeType (hildon-gtk.h) and HildonButtonArrangement
FINGER = 1 << 1                         # HILDON_SIZE_FINGER_HEIGHT
THUMB = 1 << 2                          # HILDON_SIZE_THUMB_HEIGHT
AUTO = 0
HORIZONTAL, VERTICAL = 0, 1

_gtk = _hil = _gobj = None
_ARGS = {}   # name -> configured function


def _load():
    global _gtk, _hil, _gobj
    if _gtk is None:
        _gtk = ctypes.CDLL("libgtk-x11-2.0.so.0")
        _hil = ctypes.CDLL("libhildon-1.so.0")
        _gobj = ctypes.CDLL("libgobject-2.0.so.0")
        _ARGS["glib"] = ctypes.CDLL("libglib-2.0.so.0")
        _ARGS["gdk"] = ctypes.CDLL("libgdk-x11-2.0.so.0")


def _fn(lib, name, restype=None, *argtypes):
    """The C function `name` of a library with its types set (cached)."""
    key = (lib, name)
    f = _ARGS.get(key)
    if f is None:
        _load()
        f = getattr(_ARGS[lib] if lib in ("glib", "gdk") else {"gtk": _gtk, "hil": _hil, "gobj": _gobj}[lib], name)
        f.restype = restype
        f.argtypes = list(argtypes) if argtypes else None
        _ARGS[key] = f
    return f


def _b(s):
    return s.encode("utf-8") if isinstance(s, str) else s


# ---- the main loop --------------------------------------------------------------------------------------------------------------------------

def init():
    """gtk_init_check(); returns True when the X display is usable."""
    _load()
    return bool(_fn("gtk", "gtk_init_check", c_int, c_void_p, c_void_p)(None, None))


def main():
    _fn("gtk", "gtk_main")()


def quit():
    _fn("gtk", "gtk_main_quit")()


def flush():
    """Handle the pending events (redraws, taps) without entering main(): call it before a long blocking job so that the window shows "Saving..." first."""
    pending, step = _fn("gtk", "gtk_events_pending", c_int), _fn("gtk", "gtk_main_iteration_do", c_int, c_int)
    for _ in range(200):
        if not pending():
            break
        step(0)


_CB_IDLE = ctypes.CFUNCTYPE(c_int, c_void_p)
_live = []   # timer callbacks that are still scheduled (ctypes frees a callback that nobody references)


def _schedule(add, ms, func, *args):
    def tick(_):
        try:
            again = func(*args)
        except Exception:
            import traceback; traceback.print_exc()
            again = False
        if not again:
            _live.remove(cb)
        return 1 if again else 0
    cb = _CB_IDLE(tick)
    _live.append(cb)
    return add(cb)


def timeout(ms, func, *args):
    """Call func(*args) every `ms` milliseconds while it returns True (like gobject.timeout_add). Returns the source id."""
    f = _fn("glib", "g_timeout_add", c_uint, c_uint, _CB_IDLE, c_void_p)
    return _schedule(lambda cb: f(ms, cb, None), ms, func, *args)


def idle(func, *args):
    """Call func(*args) when the loop is idle, until it returns False."""
    f = _fn("glib", "g_idle_add", c_uint, _CB_IDLE, c_void_p)
    return _schedule(lambda cb: f(cb, None), 0, func, *args)


# ---- widgets ----------------------------------------------------------------------------------------------------------------------------------

# a signal handler gets (instance, ...signal arguments..., user data); 4 pointer arguments cover every signal used here (extra ones are ignored)
_CB_SIGNAL = ctypes.CFUNCTYPE(None, c_void_p, c_void_p, c_void_p, c_void_p)
_by_ptr = {}   # address -> Widget, so that a signal handler gets the same Python object back


class Widget:
    """Base class: holds the GtkWidget pointer, signals and the common properties."""

    def __init__(self, ptr):
        self.ptr = c_void_p(ptr)
        self._cbs = []
        _by_ptr[self.ptr.value] = self

    def connect(self, signal, callback):
        """Connect callback(widget) to a signal ("clicked", "destroy", "changed", ...). Returns the handler id."""
        def thunk(_w, _a, _b2, _c):
            try:
                callback(self)
            except Exception:
                import traceback; traceback.print_exc()
        cb = _CB_SIGNAL(thunk)
        self._cbs.append(cb)          # as long as the widget lives, the callback lives
        return _fn("gobj", "g_signal_connect_data", ctypes.c_ulong, c_void_p, c_char_p, _CB_SIGNAL, c_void_p, c_void_p, c_int)(
            self.ptr, _b(signal), cb, None, None, 0)

    def show(self):
        _fn("gtk", "gtk_widget_show_all", None, c_void_p)(self.ptr)

    def hide(self):
        _fn("gtk", "gtk_widget_hide", None, c_void_p)(self.ptr)

    def destroy(self):
        _by_ptr.pop(self.ptr.value, None)
        _fn("gtk", "gtk_widget_destroy", None, c_void_p)(self.ptr)

    def set_sensitive(self, on=True):
        _fn("gtk", "gtk_widget_set_sensitive", None, c_void_p, c_int)(self.ptr, int(on))

    def set_size_request(self, width, height):
        _fn("gtk", "gtk_widget_set_size_request", None, c_void_p, c_int, c_int)(self.ptr, width, height)

    def add(self, child):
        """Container: add a single child (Window, PannableArea, ...)."""
        _fn("gtk", "gtk_container_add", None, c_void_p, c_void_p)(self.ptr, child.ptr)
        return child


class Window(Widget):
    """HildonStackableWindow: a view of the application with its own title, Back button and optional application menu."""

    def __init__(self, title="", on_destroy=None, quit_on_close=True):
        super().__init__(_fn("hil", "hildon_stackable_window_new", c_void_p)())
        self.set_title(title)
        if quit_on_close:
            self.connect("destroy", lambda w: quit())
        if on_destroy:
            self.connect("destroy", on_destroy)

    def set_title(self, title):
        _fn("gtk", "gtk_window_set_title", None, c_void_p, c_char_p)(self.ptr, _b(title))

    def set_menu(self, menu):
        """Attach an AppMenu (the drop-down of the title bar, F4 in the emulator)."""
        _fn("hil", "hildon_window_set_app_menu", None, c_void_p, c_void_p)(self.ptr, menu.ptr)
        self.menu = menu


class Box(Widget):
    def __init__(self, vertical=True, spacing=0, homogeneous=False):
        new = "gtk_vbox_new" if vertical else "gtk_hbox_new"
        super().__init__(_fn("gtk", new, c_void_p, c_int, c_int)(int(homogeneous), spacing))

    def add(self, child, expand=False, fill=None, padding=0):
        """Pack a widget at the end; expand takes the free space, fill (default: same as expand) makes the widget use it."""
        fill = expand if fill is None else fill
        _fn("gtk", "gtk_box_pack_start", None, c_void_p, c_void_p, c_int, c_int, c_uint)(self.ptr, child.ptr, int(expand), int(fill), padding)
        return child


def VBox(spacing=0, homogeneous=False):
    return Box(True, spacing, homogeneous)


def HBox(spacing=0, homogeneous=False):
    return Box(False, spacing, homogeneous)


class Label(Widget):
    def get_text(self):
        r = _fn("gtk", "gtk_label_get_text", c_char_p, c_void_p)(self.ptr)
        return r.decode("utf-8", "replace") if r else ""

    def __init__(self, text="", markup=False, wrap=False, xalign=0.5):
        super().__init__(_fn("gtk", "gtk_label_new", c_void_p, c_char_p)(None))
        self.set_text(text, markup)
        if wrap:
            _fn("gtk", "gtk_label_set_line_wrap", None, c_void_p, c_int)(self.ptr, 1)
        _fn("gtk", "gtk_misc_set_alignment", None, c_void_p, ctypes.c_float, ctypes.c_float)(self.ptr, xalign, 0.5)

    def set_text(self, text, markup=False):
        _fn("gtk", "gtk_label_set_markup" if markup else "gtk_label_set_text", None, c_void_p, c_char_p)(self.ptr, _b(text))


class Button(Widget):
    """HildonButton with a title and an optional second line (value). size: FINGER or THUMB (the height of the button)."""

    def __init__(self, title="", value=None, on_clicked=None, size=THUMB, arrangement=VERTICAL):
        super().__init__(_fn("hil", "hildon_button_new_with_text", c_void_p, c_int, c_int, c_char_p, c_char_p)(
            size, arrangement, _b(title), _b(value) if value is not None else None))
        if on_clicked:
            self.connect("clicked", on_clicked)

    def set_value(self, value):
        _fn("hil", "hildon_button_set_value", None, c_void_p, c_char_p)(self.ptr, _b(value))

    def set_title(self, title):
        _fn("hil", "hildon_button_set_title", None, c_void_p, c_char_p)(self.ptr, _b(title))


class ImageButton(Widget):
    """A finger-sized button with a picture instead of text (PNG file); falls back to `label` when the file cannot be loaded.
    width narrows it (Hildon buttons are as wide as the free space otherwise)."""

    def __init__(self, path, on_clicked=None, size=THUMB, width=-1, label=""):
        super().__init__(_fn("hil", "hildon_gtk_button_new", c_void_p, c_int)(size))
        if os.path.exists(path):
            image = _fn("gtk", "gtk_image_new_from_file", c_void_p, c_char_p)(_b(path))
            _fn("gtk", "gtk_button_set_image", None, c_void_p, c_void_p)(self.ptr, image)
        else:
            _fn("gtk", "gtk_button_set_label", None, c_void_p, c_char_p)(self.ptr, _b(label or os.path.basename(path)))
        if width > 0:
            self.set_size_request(width, -1)
        if on_clicked:
            self.connect("clicked", on_clicked)


class Entry(Widget):
    """Single-line text field (GtkEntry); signal "changed"."""

    def __init__(self, text="", on_changed=None):
        super().__init__(_fn("gtk", "gtk_entry_new", c_void_p)())
        self.set_text(text)
        if on_changed:
            self.connect("changed", on_changed)

    def set_text(self, text):
        _fn("gtk", "gtk_entry_set_text", None, c_void_p, c_char_p)(self.ptr, _b(text))

    def get_text(self):
        r = _fn("gtk", "gtk_entry_get_text", c_char_p, c_void_p)(self.ptr)
        return r.decode("utf-8", "replace") if r else ""

    def set_completion(self, words):
        """EntryCompletion: a pop-up of the words that start with what is typed (inline completion as well). words: list of str."""
        store = ListStore(1)
        for w in words:
            store.append([w])
        comp = _fn("gtk", "gtk_entry_completion_new", c_void_p)()
        _fn("gtk", "gtk_entry_completion_set_model", None, c_void_p, c_void_p)(comp, store.ptr)
        _fn("gtk", "gtk_entry_completion_set_text_column", None, c_void_p, c_int)(comp, 0)
        _fn("gtk", "gtk_entry_set_completion", None, c_void_p, c_void_p)(self.ptr, comp)
        self._completion = (comp, store)          # the store must outlive the entry's use of it


class TextView(Widget):
    """Multi-line text (GtkTextView), wrapped at words; editable unless editable=False."""

    def __init__(self, text="", editable=True, wrap=True):
        super().__init__(_fn("gtk", "gtk_text_view_new", c_void_p)())
        self._buf = _fn("gtk", "gtk_text_view_get_buffer", c_void_p, c_void_p)(self.ptr)
        if wrap:
            _fn("gtk", "gtk_text_view_set_wrap_mode", None, c_void_p, c_int)(self.ptr, 2)      # GTK_WRAP_WORD
        _fn("gtk", "gtk_text_view_set_editable", None, c_void_p, c_int)(self.ptr, int(editable))
        self.set_text(text)

    def set_text(self, text):
        _fn("gtk", "gtk_text_buffer_set_text", None, c_void_p, c_char_p, c_int)(self._buf, _b(text), -1)

    def get_text(self):
        start, end = ctypes.create_string_buffer(80), ctypes.create_string_buffer(80)       # GtkTextIter is a 80 byte struct
        _fn("gtk", "gtk_text_buffer_get_bounds", None, c_void_p, c_void_p, c_void_p)(self._buf, start, end)
        r = _fn("gtk", "gtk_text_buffer_get_text", ctypes.c_void_p, c_void_p, c_void_p, c_void_p, c_int)(self._buf, start, end, 0)
        try:
            return ctypes.string_at(r).decode("utf-8", "replace")
        finally:
            _fn("gobj", "g_free", None, c_void_p)(r)


class DrawingArea(Widget):
    """An empty widget that owns an X window: a place for a video sink (GStreamer xvimagesink / XOverlay) or for custom drawing.
    xid() is the X window id (the widget is realized first), e.g. for gst_x_overlay_set_xwindow_id()."""

    def __init__(self, width=-1, height=-1):
        super().__init__(_fn("gtk", "gtk_drawing_area_new", c_void_p)())
        self.set_size_request(width, height)
        _fn("gtk", "gtk_widget_set_double_buffered", None, c_void_p, c_int)(self.ptr, 0)      # the video sink draws itself

    def xid(self):
        _fn("gtk", "gtk_widget_realize", None, c_void_p)(self.ptr)
        win = _fn("gtk", "gtk_widget_get_window", c_void_p, c_void_p)(self.ptr)
        return _fn("gdk", "gdk_x11_drawable_get_xid", ctypes.c_ulong, c_void_p)(win)


class PannableArea(Widget):
    """HildonPannableArea: kinetic scrolling by finger. add(child) takes widgets that scroll by themselves (TextView), add_viewport() the others."""

    def __init__(self):
        super().__init__(_fn("hil", "hildon_pannable_area_new", c_void_p)())

    def add_viewport(self, child):
        _fn("hil", "hildon_pannable_area_add_with_viewport", None, c_void_p, c_void_p)(self.ptr, child.ptr)
        return child


class AppMenu(Widget):
    """HildonAppMenu: the menu of the title bar; add(label, callback) appends an item."""

    def __init__(self):
        super().__init__(_fn("hil", "hildon_app_menu_new", c_void_p)())

    def add(self, label, callback=None):
        item = Widget(_fn("gtk", "gtk_button_new_with_label", c_void_p, c_char_p)(_b(label)))
        if callback:
            item.connect("clicked", callback)
        _fn("hil", "hildon_app_menu_append", None, c_void_p, c_void_p)(self.ptr, item.ptr)
        item.show()
        return item


class Banner:
    """Information banner of Hildon (the grey note in the corner); disappears by itself."""

    def __init__(self, parent, text):
        _fn("hil", "hildon_banner_show_information", c_void_p, c_void_p, c_char_p, c_char_p)(parent.ptr, None, _b(text))


# ---- lists ------------------------------------------------------------------------------------------------------------------------------------

G_TYPE_STRING = 16 << 2


class ListStore:
    """GtkListStore with `columns` string columns (the model of a ListView or of an entry completion)."""

    def __init__(self, columns=1):
        self.columns = columns
        types = (ctypes.c_size_t * columns)(*([G_TYPE_STRING] * columns))
        self.ptr = c_void_p(_fn("gtk", "gtk_list_store_newv", c_void_p, c_int, c_void_p)(columns, types))

    def append(self, row):
        """Add a row (a list of str, one per column)."""
        it = ctypes.create_string_buffer(64)                 # GtkTreeIter
        _fn("gtk", "gtk_list_store_append", None, c_void_p, c_void_p)(self.ptr, it)
        for col, text in enumerate(row):
            # gtk_list_store_set() is variadic: no argtypes, explicit C types
            f = _fn("gtk", "gtk_list_store_set")
            f(self.ptr, it, c_int(col), c_char_p(_b(text)), c_int(-1))

    def clear(self):
        _fn("gtk", "gtk_list_store_clear", None, c_void_p)(self.ptr)

    def rows(self):
        """All rows as lists of str."""
        out = []
        it = ctypes.create_string_buffer(64)
        ok = _fn("gtk", "gtk_tree_model_get_iter_first", c_int, c_void_p, c_void_p)(self.ptr, it)
        while ok:
            out.append(_row(self.ptr, it, self.columns))
            ok = _fn("gtk", "gtk_tree_model_iter_next", c_int, c_void_p, c_void_p)(self.ptr, it)
        return out


def _row(model, it, columns):
    row = []
    for col in range(columns):
        val = ctypes.create_string_buffer(32)                # zeroed GValue
        _fn("gtk", "gtk_tree_model_get_value", None, c_void_p, c_void_p, c_int, c_void_p)(model, it, col, val)
        s = _fn("gobj", "g_value_get_string", c_char_p, c_void_p)(val)
        row.append(s.decode("utf-8", "replace") if s else "")
        _fn("gobj", "g_value_unset", None, c_void_p)(val)
    return row


class ListView(Widget):
    """HildonTreeView over a ListStore: one text column per store column, no headers. Put it into a PannableArea (add, not add_viewport).
    Signals: connect("row-activated", fn) is a tap on a row; selected() returns the row under the cursor."""

    def __init__(self, store, headers=None):
        super().__init__(_fn("hil", "hildon_gtk_tree_view_new", c_void_p, c_int)(0))          # HILDON_UI_MODE_NORMAL
        self.store = store
        _fn("gtk", "gtk_tree_view_set_model", None, c_void_p, c_void_p)(self.ptr, store.ptr)
        for col in range(store.columns):
            r = _fn("gtk", "gtk_cell_renderer_text_new", c_void_p)()
            c = _fn("gtk", "gtk_tree_view_column_new", c_void_p)()
            _fn("gtk", "gtk_tree_view_column_pack_start", None, c_void_p, c_void_p, c_int)(c, r, 1)
            _fn("gtk", "gtk_tree_view_column_add_attribute", None, c_void_p, c_void_p, c_char_p, c_int)(c, r, b"text", col)
            if headers:
                _fn("gtk", "gtk_tree_view_column_set_title", None, c_void_p, c_char_p)(c, _b(headers[col]))
            _fn("gtk", "gtk_tree_view_append_column", c_int, c_void_p, c_void_p)(self.ptr, c)
        _fn("gtk", "gtk_tree_view_set_headers_visible", None, c_void_p, c_int)(self.ptr, int(bool(headers)))
        _fn("gtk", "gtk_tree_selection_set_mode", None, c_void_p, c_int)(self._selection(), 1)       # GTK_SELECTION_SINGLE
        self._current = None
        self._raw = _CB_SIGNAL(self._remember)
        _fn("gobj", "g_signal_connect_data", ctypes.c_ulong, c_void_p, c_char_p, _CB_SIGNAL, c_void_p, c_void_p, c_int)(
            self.ptr, b"row-activated", self._raw, None, None, 0)

    def _selection(self):
        return _fn("gtk", "gtk_tree_view_get_selection", c_void_p, c_void_p)(self.ptr)

    def _remember(self, _w, path, _col, _data):
        """row-activated: remember the row of the tap (the Hildon theme can switch the selection off, so the cursor and selection stay empty)."""
        self._current = path_to_index(path)

    def select(self, index):
        """Select row number `index` (0 based) and make it the current row."""
        self._current = index
        path = _fn("gtk", "gtk_tree_path_new_from_indices", c_void_p, c_int, c_int)(index, -1)
        _fn("gtk", "gtk_tree_selection_select_path", None, c_void_p, c_void_p)(self._selection(), path)
        _fn("gtk", "gtk_tree_path_free", None, c_void_p)(path)

    def selected(self):
        """The current row (selected or last tapped) as a list of str, or None."""
        it = ctypes.create_string_buffer(64)
        model = c_void_p()
        if _fn("gtk", "gtk_tree_selection_get_selected", c_int, c_void_p, c_void_p, c_void_p)(self._selection(), ctypes.byref(model), it):
            return _row(self.store.ptr, it, self.store.columns)
        rows = self.store.rows()
        return rows[self._current] if self._current is not None and self._current < len(rows) else None

    def activate(self, index):
        """Emit row-activated for a row, as a tap does (tests, keyboard shortcuts)."""
        path = _fn("gtk", "gtk_tree_path_new_from_indices", c_void_p, c_int, c_int)(index, -1)
        _fn("gtk", "gtk_tree_view_row_activated", None, c_void_p, c_void_p, c_void_p)(self.ptr, path, None)
        _fn("gtk", "gtk_tree_path_free", None, c_void_p)(path)


def path_to_index(path):
    """Row number of a GtkTreePath of a flat list."""
    n = c_int()
    arr = _fn("gtk", "gtk_tree_path_get_indices", ctypes.POINTER(c_int), c_void_p)(path)
    return arr[0] if arr else None


# ---- dialogs ----------------------------------------------------------------------------------------------------------------------------------

OK, CANCEL = -5, -6           # GTK_RESPONSE_OK, GTK_RESPONSE_CANCEL


class Dialog(Widget):
    """GtkDialog: body (a Box) takes the content, add_button(label, response) the buttons; run() blocks until one is tapped and returns its response."""

    def __init__(self, title, parent=None):
        super().__init__(_fn("gtk", "gtk_dialog_new", c_void_p)())
        _fn("gtk", "gtk_window_set_title", None, c_void_p, c_char_p)(self.ptr, _b(title))
        if parent is not None:
            _fn("gtk", "gtk_window_set_transient_for", None, c_void_p, c_void_p)(self.ptr, parent.ptr)
        _fn("gtk", "gtk_window_set_modal", None, c_void_p, c_int)(self.ptr, 1)
        self.body = Widget(_fn("gtk", "gtk_dialog_get_content_area", c_void_p, c_void_p)(self.ptr))
        self.body.add = lambda child, expand=True, fill=None, padding=0: Box.add(self.body, child, expand, fill, padding)

    def add_button(self, label, response):
        _fn("gtk", "gtk_dialog_add_button", c_void_p, c_void_p, c_char_p, c_int)(self.ptr, _b(label), response)

    def run(self):
        """Show the dialog, wait for a button; the dialog is only hidden, so read the entries and then call destroy()."""
        r = _fn("gtk", "gtk_dialog_run", c_int, c_void_p)(self.ptr)
        self.hide()
        return r


def confirm(parent, text):
    """Hildon confirmation note with OK and Cancel; True when OK was tapped."""
    note = Widget(_fn("hil", "hildon_note_new_confirmation", c_void_p, c_void_p, c_char_p)(parent.ptr if parent else None, _b(text)))
    r = _fn("gtk", "gtk_dialog_run", c_int, c_void_p)(note.ptr)
    note.destroy()
    return r == OK


def info(parent, text):
    """Hildon information note with an OK button (blocks until it is tapped)."""
    note = Widget(_fn("hil", "hildon_note_new_information", c_void_p, c_void_p, c_char_p)(parent.ptr if parent else None, _b(text)))
    _fn("gtk", "gtk_dialog_run", c_int, c_void_p)(note.ptr)
    note.destroy()
