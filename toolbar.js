/**
 * toolbar.js — injected into the Anki editor webview on every note load.
 *
 * Exports a single global function:
 *   _ctbRefresh(buttons)   – re-renders the custom button strip
 *
 * The strip is inserted immediately before the "＋" button that was
 * added by editor_did_init_buttons.  Right-clicking any custom button
 * shows an edit / delete context menu.
 */

(function () {
    'use strict';

    /* ── IDs used in the DOM ─────────────────────────────────────────── */
    var STRIP_ID   = 'ctb-strip';       // <span> container for custom buttons
    var PLUS_ID    = 'ctb-plus-btn';    // id given to the "＋" button in Python
    var MENU_ID    = 'ctb-ctx-menu';

    /* ── Main refresh entry-point (called by Python) ─────────────────── */

    /**
     * Re-render all custom buttons.
     * @param {Array<Object>} buttons  Saved button descriptors from Python.
     */
    window._ctbRefresh = function (buttons) {
        var plusBtn = _findPlus();

        if (!plusBtn) {
            // Toolbar not in DOM yet (can happen on first load) — retry once.
            setTimeout(function () { window._ctbRefresh(buttons); }, 300);
            return;
        }

        /* Locate or create the strip that lives just before "＋" */
        var strip = document.getElementById(STRIP_ID);
        if (!strip) {
            strip = document.createElement('span');
            strip.id = STRIP_ID;
            strip.style.cssText = [
                'display: inline-flex',
                'align-items: center',
                'gap: 2px',
                'margin-right: 2px',
            ].join('; ');

            var parent = plusBtn.parentNode;
            if (!parent) {
                setTimeout(function () { window._ctbRefresh(buttons); }, 300);
                return;
            }
            parent.insertBefore(strip, plusBtn);
        }

        /* Clear and rebuild */
        strip.innerHTML = '';
        buttons.forEach(function (data, idx) {
            strip.appendChild(_makeButton(data, idx));
        });
    };

    /* ── Button factory ──────────────────────────────────────────────── */

    function _makeButton(data, idx) {
        var btn = document.createElement('button');
        btn.textContent = data.icon || '★';
        var titleText = 'Left-click: execute  |  Right-click: edit / delete';
        if (data.shortcut && data.shortcut.trim()) {
            titleText = 'Shortcut: ' + data.shortcut.trim() + '  |  ' + titleText;
        }
        btn.title       = titleText;
        btn.tabIndex    = -1;
        btn.style.cssText = [
            'font-size: 13px',
            'padding: 2px 7px',
            'cursor: pointer',
            'border: 1px solid var(--border-subtle, var(--border, #c8c8d0))',
            'border-radius: 4px',
            'background: var(--button-bg, #f4f4ff)',
            'color: var(--fg, inherit)',
            'line-height: 1.5',
            'font-family: system-ui, "Segoe UI Emoji", sans-serif',
            'transition: background-color 0.15s ease, border-color 0.15s ease',
        ].join('; ');

        btn.addEventListener('mouseenter', function () {
            btn.style.background = 'var(--button-hover, var(--selected-bg, #e4e4ff))';
        });
        btn.addEventListener('mouseleave', function () {
            btn.style.background = 'var(--button-bg, #f4f4ff)';
        });

        /*
         * Prevent mousedown from stealing focus / collapsing the selection.
         * This is critical for type-2 (wrap) buttons so the selection
         * survives until the click handler fires.
         */
        btn.addEventListener('mousedown', function (e) {
            e.preventDefault();
        });

        /* Left-click → execute */
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            pycmd('ctb_run:' + JSON.stringify(data));
        });

        /* Right-click → context menu */
        btn.addEventListener('contextmenu', function (e) {
            e.preventDefault();
            e.stopPropagation();
            _showContextMenu(e, idx);
        });

        return btn;
    }

    /* ── Context menu ────────────────────────────────────────────────── */

    function _showContextMenu(e, idx) {
        _clearMenu();

        var menu = document.createElement('div');
        menu.id = MENU_ID;
        menu.style.cssText = [
            'position: fixed',
            'left: '   + e.clientX + 'px',
            'top: '    + e.clientY + 'px',
            'background: var(--canvas-overlay, var(--canvas-elevated, var(--canvas, #ffffff)))',
            'color: var(--fg, #222222)',
            'border: 1px solid var(--border-subtle, var(--border, #d0d0d8))',
            'border-radius: 8px',
            'box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25)',
            'z-index: 99999',
            'overflow: hidden',
            'font-size: 13px',
            'min-width: 120px',
            'font-family: system-ui, "Segoe UI", sans-serif',
            'user-select: none',
        ].join('; ');

        menu.appendChild(
            _menuItem('✏️  Edit', 'var(--fg, #222222)', function () {
                pycmd('ctb_edit:' + idx);
            })
        );
        menu.appendChild(
            _menuItem('🗑️  Delete', 'var(--accent-danger, var(--flag-1, #cc0000))', function () {
                pycmd('ctb_del:' + idx);
            })
        );

        document.body.appendChild(menu);

        /*
         * Close the menu when the user clicks anywhere else.
         * Use a short timeout so the current mousedown doesn't
         * immediately trigger the outside-click handler.
         */
        setTimeout(function () {
            document.addEventListener('mousedown', _onOutsideClick);
        }, 50);
    }

    function _menuItem(text, color, action) {
        var el = document.createElement('div');
        el.textContent = text;
        el.style.cssText = [
            'padding: 8px 16px',
            'cursor: pointer',
            'color: ' + color,
        ].join('; ');

        el.addEventListener('mouseenter', function () {
            el.style.background = 'var(--selected-bg, var(--button-hover, #f0f0f5))';
        });
        el.addEventListener('mouseleave', function () {
            el.style.background = '';
        });
        el.addEventListener('mousedown', function (e) {
            e.preventDefault();
            e.stopPropagation();
            _clearMenu();
            action();
        });
        return el;
    }

    function _clearMenu() {
        var m = document.getElementById(MENU_ID);
        if (m) { m.remove(); }
        document.removeEventListener('mousedown', _onOutsideClick);
    }

    function _onOutsideClick() { _clearMenu(); }

    /* ── Locate the "＋" button ──────────────────────────────────────── */

    function _findPlus() {
        /* Try the id assigned in Python first */
        var el = document.getElementById(PLUS_ID);
        if (el) { return el; }

        /* Fallback: scan all buttons for matching label text */
        var all = document.querySelectorAll('button');
        for (var i = 0; i < all.length; i++) {
            if (all[i].textContent.trim() === '＋') {
                return all[i];
            }
        }
        return null;
    }

})();
