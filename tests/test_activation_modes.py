"""Activation modes: hold (push-to-talk) vs latch (press to start, press to stop)."""
from unittest.mock import MagicMock

import pytest
from pynput import keyboard as kb

from config.settings import settings
from utils.hotkey_listener import HotkeyManager


class FakeChar:
    def __init__(self, ch):
        self.char = ch
        self.name = None


@pytest.fixture
def manager(monkeypatch):
    monkeypatch.setitem(settings.data, "hotkey", "ctrl+space")
    monkeypatch.setitem(settings.data, "fallback_hotkey", "")
    start, stop = MagicMock(), MagicMock()
    mgr = HotkeyManager(on_start=start, on_stop=stop)

    # The chord counts as complete whenever we ask about it.
    monkeypatch.setattr(mgr, "_is_combination_down", lambda chord: True)
    # Modifiers report as physically down.
    import utils.hotkey_listener as hl
    monkeypatch.setattr(hl, "is_physical_key_down", lambda vk: True)
    return mgr, start, stop


def _press(mgr, *keys):
    for k in keys:
        mgr._on_press(k)


def test_hold_mode_starts_on_press_and_stops_on_release(manager, monkeypatch):
    monkeypatch.setitem(settings.data, "activation_mode", "hold")
    mgr, start, stop = manager

    _press(mgr, kb.Key.ctrl_l, kb.Key.space)
    assert mgr.is_active is True
    assert start.called

    # Nothing latched: releasing the base key must end the take.
    monkeypatch.setattr(mgr, "_is_combination_down", lambda chord: False)
    mgr._on_release(kb.Key.space)
    assert mgr.is_active is False
    assert stop.called


def test_latch_mode_keeps_recording_after_release(manager, monkeypatch):
    monkeypatch.setitem(settings.data, "activation_mode", "latch")
    mgr, start, stop = manager

    _press(mgr, kb.Key.ctrl_l, kb.Key.space)
    assert mgr.is_active is True and mgr.latched is True

    # The whole point: letting go must NOT stop the take.
    monkeypatch.setattr(mgr, "_is_combination_down", lambda chord: False)
    mgr._on_release(kb.Key.space)
    assert mgr.is_active is True, "latch mode stopped when the key was released"
    assert mgr.latched is True
    assert stop.called is False


def test_latch_mode_second_press_stops(manager, monkeypatch):
    monkeypatch.setitem(settings.data, "activation_mode", "latch")
    mgr, start, stop = manager

    _press(mgr, kb.Key.ctrl_l, kb.Key.space)
    mgr._on_release(kb.Key.space)
    mgr._on_release(kb.Key.ctrl_l)
    # Second press ends it.
    _press(mgr, kb.Key.ctrl_l, kb.Key.space)
    assert mgr.is_active is False
    assert mgr.latched is False
    assert stop.called


def test_latch_mode_ignores_keyboard_autorepeat(manager, monkeypatch):
    """Holding a key repeats press events; only the first may toggle."""
    monkeypatch.setitem(settings.data, "activation_mode", "latch")
    mgr, start, stop = manager

    _press(mgr, kb.Key.ctrl_l, kb.Key.space)
    _press(mgr, kb.Key.space)   # auto-repeat, key already down
    _press(mgr, kb.Key.space)
    assert mgr.is_active is True, "auto-repeat toggled the recording off"
    assert start.call_count == 1
    assert stop.called is False


def test_force_stop_ends_latched_recording(manager, monkeypatch):
    monkeypatch.setitem(settings.data, "activation_mode", "latch")
    mgr, start, stop = manager

    _press(mgr, kb.Key.ctrl_l, kb.Key.space)
    mgr.force_stop()
    assert mgr.is_active is False
    assert mgr.latched is False
    assert stop.called


def test_force_stop_is_safe_when_idle(manager):
    mgr, start, stop = manager
    mgr.force_stop()   # must not raise or fire the stop callback
    assert stop.called is False


def test_unknown_activation_mode_falls_back_to_hold():
    assert settings.__class__.activation_mode.fget.__doc__ is not None
    data = dict(settings.data)
    try:
        settings.data["activation_mode"] = "sideways"
        assert settings.activation_mode == "hold"
    finally:
        settings.data.clear()
        settings.data.update(data)
