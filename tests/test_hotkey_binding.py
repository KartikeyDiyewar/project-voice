"""Any single key or chord must actually fire, not just be storable."""
from unittest.mock import MagicMock

import pytest
from pynput import keyboard as kb

from config.settings import settings
from utils.hotkey_listener import HotkeyManager, key_matches_token, normalize_key


class FakeChar:
    """A printable key as pynput delivers it."""
    def __init__(self, ch):
        self.char = ch
        self.name = None


@pytest.fixture
def mgr(monkeypatch):
    monkeypatch.setitem(settings.data, "activation_mode", "hold")
    m = HotkeyManager(on_start=MagicMock(), on_stop=MagicMock())
    monkeypatch.setattr(m, "is_physical_key_down", lambda vk: True, raising=False)
    # Modifiers are reported as physically down.
    import utils.hotkey_listener as hl
    monkeypatch.setattr(hl, "is_physical_key_down", lambda vk: True)
    return m


def _bind(mgr, chord, monkeypatch):
    monkeypatch.setitem(settings.data, "hotkey", chord)
    monkeypatch.setitem(settings.data, "fallback_hotkey", "")
    mgr.reload_keys()


@pytest.mark.parametrize("chord,key", [
    ("f9", kb.Key.f9),
    ("enter", kb.Key.enter),
    ("page_up", kb.Key.page_up),
    ("up", kb.Key.up),
    ("tab", kb.Key.tab),
    ("q", FakeChar("q")),
    ("f12", kb.Key.f12),
])
def test_single_key_chord_fires(mgr, monkeypatch, chord, key):
    """Every single key the user binds must start recording."""
    _bind(mgr, chord, monkeypatch)
    mgr._on_press(key)
    assert mgr.is_active is True, f"single key '{chord}' did not fire"
    assert mgr.on_start_callback.called


def test_single_key_stops_on_release_in_hold_mode(mgr, monkeypatch):
    _bind(mgr, "f9", monkeypatch)
    mgr._on_press(kb.Key.f9)
    assert mgr.is_active is True
    mgr._on_release(kb.Key.f9)
    assert mgr.is_active is False
    assert mgr.on_stop_callback.called


def test_modifier_combination_still_works(mgr, monkeypatch):
    _bind(mgr, "ctrl+shift+d", monkeypatch)
    mgr._on_press(kb.Key.ctrl_l)
    mgr._on_press(kb.Key.shift_l)
    assert mgr.is_active is False
    mgr._on_press(FakeChar("d"))
    assert mgr.is_active is True


def test_unrelated_key_while_chord_held_does_not_fire(mgr, monkeypatch):
    """Holding Ctrl should not make every later keypress a trigger."""
    _bind(mgr, "ctrl+space", monkeypatch)
    mgr._on_press(kb.Key.ctrl_l)
    mgr._on_press(FakeChar("r"))
    assert mgr.is_active is False, "typing 'r' with Ctrl held wrongly triggered"
    mgr._on_press(kb.Key.space)
    assert mgr.is_active is True


def test_key_matches_token_normalises_names():
    assert key_matches_token(kb.Key.esc, "escape")
    assert key_matches_token(kb.Key.enter, "enter")
    assert key_matches_token(kb.Key.page_up, "page_up")
    assert not key_matches_token(kb.Key.f9, "f8")


def test_normalize_key_aliases():
    assert normalize_key("esc") == "escape"
    assert normalize_key("return") == "enter"
    assert normalize_key("control") == "ctrl"
    assert normalize_key("F9") == "f9"
