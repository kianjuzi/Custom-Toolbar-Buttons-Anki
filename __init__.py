"""
Custom Toolbar Buttons
======================
Adds a "＋" button at the end of the editor toolbar. Clicking it opens a dialog to create custom buttons.
• Type 1: Inserts custom content (text / HTML) at the cursor position on click
• Type 2: Wraps selected text with custom content on left and right sides
• Shortcut: Supports specifying custom shortcut key combinations for each button (e.g., Ctrl+Shift+B, F8)

Right-click any created button to edit or delete it.

Compatible with Anki 2.1.50+ (Qt6 / PyQt6), Windows 11 desktop.
"""

from __future__ import annotations

import json
import os
from typing import Any

from aqt import gui_hooks, mw
from aqt.editor import Editor
from aqt.qt import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QKeySequence,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QShortcut,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

_ADDON_DIR   = os.path.dirname(os.path.abspath(__file__))
_TOOLBAR_JS  = os.path.join(_ADDON_DIR, "toolbar.js")
_PLUS_CMD    = "ctb_add"        # pycmd fired when "＋" is clicked
_PLUS_BTN_ID = "ctb-plus-btn"  # DOM id assigned to the "＋" button

# ──────────────────────────────────────────────────────────────────────────────
# Config helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_buttons() -> list[dict]:
    """Return the persisted custom-button list (may be empty)."""
    cfg = mw.addonManager.getConfig(__name__) or {}
    return cfg.get("buttons", [])


def _save_buttons(buttons: list[dict]) -> None:
    """Persist the custom-button list."""
    cfg = mw.addonManager.getConfig(__name__) or {}
    cfg["buttons"] = buttons
    mw.addonManager.writeConfig(__name__, cfg)


# ──────────────────────────────────────────────────────────────────────────────
# Add / Edit dialog
# ──────────────────────────────────────────────────────────────────────────────

class _BtnDialog(QDialog):
    """Dialog for creating or editing a custom toolbar button."""

    def __init__(self, parent: QWidget, data: dict | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Custom Toolbar Buttons")
        self.setMinimumWidth(480)
        self._build(data or {})

    # ── layout ────────────────────────────────────────────────────────────────

    def _build(self, d: dict) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # ── icon/label & shortcut ─────────────────────────────────────────────
        fl = QFormLayout()
        self._icon = QLineEdit(d.get("icon", "★"))
        self._icon.setPlaceholderText("Text, Emoji, or short HTML, e.g., ★  🔴  [b]")
        self._icon.setMaxLength(20)
        fl.addRow("Button Icon / Label:", self._icon)

        self._shortcut = QLineEdit(d.get("shortcut", ""))
        self._shortcut.setPlaceholderText("e.g. Ctrl+Shift+1, F8, Alt+Z (optional)")
        fl.addRow("Shortcut Key:", self._shortcut)
        hint_sc = QLabel("Tip: Supports standard shortcuts like Ctrl+Shift+B, F8, Alt+1. Leave blank for none.")
        hint_sc.setWordWrap(True)
        hint_sc.setStyleSheet("color: gray; font-size: 11px;")
        fl.addRow("", hint_sc)

        root.addLayout(fl)

        # ── type radios ───────────────────────────────────────────────────────
        self._r1 = QRadioButton("Type 1  ──  Insert content at cursor position")
        self._r2 = QRadioButton("Type 2  ──  Wrap selected text with left/right content")
        root.addWidget(self._r1)
        root.addWidget(self._r2)

        # ── stacked content pages ─────────────────────────────────────────────
        self._stack = QStackedWidget()

        # page 0: type 1
        p1 = QWidget()
        fl1 = QFormLayout(p1)
        self._c1 = QLineEdit(d.get("content", ""))
        self._c1.setPlaceholderText("Text or HTML to insert, e.g., <b>bold</b> or {{c1::}}")
        fl1.addRow("Insert Content:", self._c1)
        hint1 = QLabel("Tip: Supports plain text and HTML tags.")
        hint1.setWordWrap(True)
        hint1.setStyleSheet("color: gray; font-size: 11px;")
        fl1.addRow("", hint1)
        self._stack.addWidget(p1)

        # page 1: type 2
        p2 = QWidget()
        fl2 = QFormLayout(p2)
        self._lft = QLineEdit(d.get("left", ""))
        self._rgt = QLineEdit(d.get("right", ""))
        self._lft.setPlaceholderText("Left side, e.g., <span style='color:red'>")
        self._rgt.setPlaceholderText("Right side, e.g., </span>")
        fl2.addRow("Left Content:", self._lft)
        fl2.addRow("Right Content:", self._rgt)
        hint2 = QLabel("Tip: When no text is selected, left and right content will be inserted together at cursor.")
        hint2.setWordWrap(True)
        hint2.setStyleSheet("color: gray; font-size: 11px;")
        fl2.addRow("", hint2)
        self._stack.addWidget(p2)

        root.addWidget(self._stack)

        # ── initial state ─────────────────────────────────────────────────────
        is2 = d.get("type", 1) == 2
        (self._r2 if is2 else self._r1).setChecked(True)
        self._stack.setCurrentIndex(1 if is2 else 0)

        self._r1.toggled.connect(lambda on: on and self._stack.setCurrentIndex(0))
        self._r2.toggled.connect(lambda on: on and self._stack.setCurrentIndex(1))

        # ── ok / cancel ───────────────────────────────────────────────────────
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    # ── validation ───────────────────────────────────────────────────────────

    def accept(self) -> None:
        sc_str = self._shortcut.text().strip()
        if sc_str:
            ks = QKeySequence(sc_str)
            if ks.isEmpty():
                QMessageBox.warning(
                    self,
                    "Invalid Shortcut Format",
                    f"Unrecognized shortcut combination: '{sc_str}'\n\nPlease use standard format, for example:\n• Ctrl+Shift+B\n• Alt+F1\n• F8\n• Ctrl+Alt+1",
                )
                self._shortcut.setFocus()
                return
        super().accept()

    # ── result ────────────────────────────────────────────────────────────────

    def get_data(self) -> dict:
        t = 2 if self._r2.isChecked() else 1
        result: dict = {
            "icon": self._icon.text().strip() or "★",
            "shortcut": self._shortcut.text().strip(),
            "type": t,
        }
        if t == 1:
            result["content"] = self._c1.text()
        else:
            result["left"]  = self._lft.text()
            result["right"] = self._rgt.text()
        return result


# ──────────────────────────────────────────────────────────────────────────────
# Active editor tracking & Shortcut management
# ──────────────────────────────────────────────────────────────────────────────

_active_editors: list[Editor] = []


def _get_valid_editors() -> list[Editor]:
    """Filter out closed or destroyed editor instances."""
    valid: list[Editor] = []
    for ed in list(_active_editors):
        try:
            _ = ed.widget.objectName()
            valid.append(ed)
        except Exception:
            pass
    _active_editors[:] = valid
    return valid


def _update_editor_shortcuts(editor: Editor) -> None:
    """Bind dynamic QShortcut objects for custom buttons to an editor instance."""
    # Clean up existing custom shortcuts on this editor instance
    old_shortcuts: list[QShortcut] = getattr(editor, "_ctb_shortcuts", [])
    for qsc in old_shortcuts:
        try:
            qsc.setEnabled(False)
            qsc.setParent(None)
            qsc.deleteLater()
        except Exception:
            pass
    editor._ctb_shortcuts = []

    new_shortcuts: list[QShortcut] = []
    buttons = _get_buttons()
    parent_widget = getattr(editor, "widget", None) or mw

    for btn in buttons:
        sc_str = btn.get("shortcut", "").strip()
        if not sc_str:
            continue
        ks = QKeySequence(sc_str)
        if ks.isEmpty():
            continue

        qsc = QShortcut(ks, parent_widget)
        qsc.activated.connect(lambda ed=editor, b=btn: _exec_button(ed, b))
        new_shortcuts.append(qsc)

    editor._ctb_shortcuts = new_shortcuts


def _push_buttons_to_all(buttons: list[dict]) -> None:
    """Broadcast latest button list and update hotkeys on every open editor."""
    payload = json.dumps(buttons, ensure_ascii=False)
    js = f"if (typeof _ctbRefresh === 'function') {{ _ctbRefresh({payload}); }}"
    for ed in _get_valid_editors():
        try:
            ed.web.eval(js)
            _update_editor_shortcuts(ed)
        except Exception:
            pass  # editor may have been closed


# ──────────────────────────────────────────────────────────────────────────────
# pycmd handler  (webview_did_receive_js_message)
# ──────────────────────────────────────────────────────────────────────────────

def _on_js_message(
    handled: tuple[bool, Any],
    msg: str,
    context: Any,
) -> tuple[bool, Any]:

    # Only intercept messages from an Editor context
    if not isinstance(context, Editor):
        return handled

    # ── add new button ────────────────────────────────────────────────────────
    if msg == _PLUS_CMD:
        dlg = _BtnDialog(mw)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            btns = _get_buttons()
            btns.append(dlg.get_data())
            _save_buttons(btns)
            _push_buttons_to_all(btns)
        return (True, None)

    # ── edit existing button ──────────────────────────────────────────────────
    if msg.startswith("ctb_edit:"):
        idx = int(msg.split(":", 1)[1])
        btns = _get_buttons()
        if 0 <= idx < len(btns):
            dlg = _BtnDialog(mw, btns[idx])
            if dlg.exec() == QDialog.DialogCode.Accepted:
                btns[idx] = dlg.get_data()
                _save_buttons(btns)
                _push_buttons_to_all(btns)
        return (True, None)

    # ── delete existing button ────────────────────────────────────────────────
    if msg.startswith("ctb_del:"):
        idx = int(msg.split(":", 1)[1])
        btns = _get_buttons()
        if 0 <= idx < len(btns):
            btns.pop(idx)
            _save_buttons(btns)
            _push_buttons_to_all(btns)
        return (True, None)

    # ── execute a custom button ───────────────────────────────────────────────
    if msg.startswith("ctb_run:"):
        data = json.loads(msg[8:])
        _exec_button(context, data)
        return (True, None)

    return handled


def _exec_button(editor: Editor, data: dict) -> None:
    """Perform the button's action in the editor webview."""
    t = data.get("type", 1)

    if t == 1:
        # ── type 1: insert at cursor ──────────────────────────────────────────
        html = json.dumps(data.get("content", ""))
        editor.web.eval(
            f"document.execCommand('insertHTML', false, {html});"
        )
    else:
        # ── type 2: wrap selection ────────────────────────────────────────────
        left  = json.dumps(data.get("left", ""))
        right = json.dumps(data.get("right", ""))
        editor.web.eval(
            f"""
(function () {{
    // Anki 2.1.50+ fields live inside Shadow DOM (<anki-editable>),
    // so window.getSelection() at the top document doesn't see the
    // real selection. Walk down through shadow roots to find it.
    function getDeepSelection(root) {{
        root = root || document;
        var active = root.activeElement;
        if (active && active.shadowRoot) {{
            if (typeof active.shadowRoot.getSelection === 'function') {{
                var s = active.shadowRoot.getSelection();
                if (s && s.rangeCount) {{ return s; }}
            }}
            return getDeepSelection(active.shadowRoot);
        }}
        return document.getSelection();
    }}

    var sel = getDeepSelection();
    if (!sel || !sel.rangeCount) {{
        // No selection: just concatenate left + right at cursor
        document.execCommand('insertHTML', false, {left} + {right});
        return;
    }}
    var range = sel.getRangeAt(0);
    // Clone selected content (preserves inner HTML formatting)
    var frag  = range.cloneContents();
    var tmp   = document.createElement('div');
    tmp.appendChild(frag);
    var inner = tmp.innerHTML || '';
    document.execCommand('insertHTML', false, {left} + inner + {right});
}})();
"""
        )


# ──────────────────────────────────────────────────────────────────────────────
# Hook callbacks
# ──────────────────────────────────────────────────────────────────────────────

def _on_editor_did_init(editor: Editor) -> None:
    """Track newly opened editors and set up custom shortcuts."""
    if editor not in _active_editors:
        _active_editors.append(editor)
    _update_editor_shortcuts(editor)


def _on_editor_did_init_buttons(buttons: list, editor: Editor) -> None:
    """Add the "＋" button to the toolbar via the official Anki API."""
    btn_html = editor.addButton(
        icon=None,
        cmd=_PLUS_CMD,
        func=lambda e: None,   # actual handling is in _on_js_message
        tip="Add Custom Toolbar Button",
        label="＋",
        id=_PLUS_BTN_ID,
    )
    buttons.append(btn_html)


def _on_editor_did_load_note(editor: Editor) -> None:
    """Inject toolbar.js, render saved custom buttons, and bind shortcuts each time a note loads."""
    try:
        with open(_TOOLBAR_JS, encoding="utf-8") as fh:
            js = fh.read()
    except FileNotFoundError:
        return

    payload = json.dumps(_get_buttons(), ensure_ascii=False)
    # Define _ctbRefresh, then immediately call it with saved data
    editor.web.eval(js + f"\n_ctbRefresh({payload});")
    _update_editor_shortcuts(editor)


# ──────────────────────────────────────────────────────────────────────────────
# Register hooks
# ──────────────────────────────────────────────────────────────────────────────

gui_hooks.editor_did_init.append(_on_editor_did_init)
gui_hooks.editor_did_init_buttons.append(_on_editor_did_init_buttons)
gui_hooks.editor_did_load_note.append(_on_editor_did_load_note)
gui_hooks.webview_did_receive_js_message.append(_on_js_message)

