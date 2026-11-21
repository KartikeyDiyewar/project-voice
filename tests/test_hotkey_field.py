"""The key field must only save on the tick, never on a bare keypress."""
import pytest
from pynput import keyboard as kb

from ui import theme
from ui.hotkey_field import HotkeyField, _canonical, pretty

# One Tk root for the whole module: CustomTkinter cannot reliably create a new
# root after an earlier one was destroyed in the same process.
_ROOT = None


def _root():
    global _ROOT
    if _ROOT is None:
        import customtkinter as ctk
        _ROOT = ctk.CTk()
        _ROOT.withdraw()
    return _ROOT


@pytest.fixture
def field():
    theme.set_mode("light")
    root = _root()
    saves = []
    f = HotkeyField(root, "ctrl+space", saves.append, bg=theme.t("canvas"))
    f.pack()
    root.update()
    yield f, saves, root
    try:
        f.cancel_capture()
    except Exception:
        pass
    f.destroy()
    root.update()


def _press(field, key):
    """Feeds a key event the way pynput's listener would."""
    field._handle("down", key)


def test_pressing_a_key_does_not_save(field):
    f, saves, _ = field
    f.start_capture()
    _press(f, kb.Key.ctrl_l)
    _press(f, kb.Key.space)
    assert saves == [], "a keypress saved the binding without confirmation"
    assert f.chord == "ctrl+space"


def test_tick_saves_the_captured_chord(field):
    f, saves, _ = field
    f.start_capture()
    _press(f, kb.Key.ctrl_l)
    _press(f, kb.Key.space)
    assert f._confirm_state() == "normal"
    f.confirm()
    assert saves == ["ctrl+space"]
    assert f.chord == "ctrl+space"
    assert f._capturing is False


def test_single_key_can_be_bound(field):
    f, saves, _ = field
    f.start_capture()
    _press(f, kb.Key.f8)
    f.confirm()
    assert saves == ["f8"]


def test_modifier_alone_cannot_be_confirmed(field):
    f, saves, _ = field
    f.start_capture()
    _press(f, kb.Key.ctrl_l)
    assert f._confirm_state() == "disabled"
    f.confirm()
    assert saves == []


def test_risky_single_key_needs_a_modifier(field):
    f, saves, _ = field
    f.start_capture()
    _press(f, kb.Key.enter)
    assert f._confirm_state() == "disabled"
    _press(f, kb.Key.ctrl_l)
    assert f._confirm_state() == "normal"


def test_escape_cancels_without_saving(field):
    f, saves, _ = field
    f.start_capture()
    _press(f, kb.Key.shift_l)
    _press(f, kb.Key.esc)
    assert saves == []
    assert f._capturing is False
    assert f.chord == "ctrl+space"


def test_retry_replaces_the_base_key(field):
    f, saves, _ = field
    f.start_capture()
    _press(f, kb.Key.ctrl_l)
    _press(f, kb.Key.space)
    _press(f, kb.Key.f9)          # changed their mind
    f.confirm()
    assert saves == ["ctrl+f9"], f"got {saves}"


def test_canonical_orders_modifiers():
    assert _canonical(["space", "shift", "ctrl"]) == "ctrl+shift+space"
    assert _canonical(["f8"]) == "f8"


def test_chord_is_saved_even_when_unchanged(field):
    """Pressing the tick is an explicit action and must be acknowledged."""
    f, saves, _ = field
    f.chord = "ctrl+space"
    f.start_capture()
    _press(f, kb.Key.ctrl_l)
    _press(f, kb.Key.space)
    f.confirm()
    assert saves == ["ctrl+space"]
