"""Activation modes: hold (push-to-talk) vs latch (press to start, press to stop)."""
from unittest.mock import MagicMock

import pytest

from config.settings import settings
from utils.hotkey_listener import HotkeyManager


@pytest.fixture
def manager(monkeypatch):
    monkeypatch.setitem(settings.data, "hotkey", "ctrl+space")
    monkeypatch.setitem(settings.data, "fallback_hotkey", "f8")
    start, stop = MagicMock(), MagicMock()
    mgr = HotkeyManager(on_start=start, on_stop=stop)

    # Bypass the real keyboard: pretend every chord token is physically down.
    monkeypatch.setattr(mgr, "_is_combination_down", lambda chord: True)
    return mgr, start, stop


def test_hold_mode_starts_on_press_and_stops_on_release(manager, monkeypatch):
    monkeypatch.setitem(settings.data, "activation_mode", "hold")
    mgr, start, stop = manager

    mgr._on_press("ctrl")
    assert mgr.is_active is True
    assert start.called

    # Nothing latched: releasing must end the take.
    monkeypatch.setattr(mgr, "_is_combination_down", lambda chord: False)
    mgr._on_release("ctrl")
    assert mgr.is_active is False
    assert stop.called


def test_latch_mode_keeps_recording_after_release(manager, monkeypatch):
    monkeypatch.setitem(settings.data, "activation_mode", "latch")
    mgr, start, stop = manager

    mgr._on_press("ctrl")
    assert mgr.is_active is True and mgr.latched is True

    # The whole point: letting go must NOT stop the take.
    monkeypatch.setattr(mgr, "_is_combination_down", lambda chord: False)
    mgr._on_release("ctrl")
    assert mgr.is_active is True, "latch mode stopped when the key was released"
    assert mgr.latched is True
    assert stop.called is False


def test_latch_mode_second_press_stops(manager, monkeypatch):
    monkeypatch.setitem(settings.data, "activation_mode", "latch")
    mgr, start, stop = manager

    mgr._on_press("ctrl")
    mgr._on_release("ctrl")
    # Second press ends it.
    mgr._on_press("ctrl")
    assert mgr.is_active is False
    assert mgr.latched is False
    assert stop.called


def test_latch_mode_ignores_keyboard_autorepeat(manager, monkeypatch):
    """Holding a key repeats press events; only the first may toggle."""
    monkeypatch.setitem(settings.data, "activation_mode", "latch")
    mgr, start, stop = manager

    mgr._on_press("ctrl")
    mgr._on_press("ctrl")   # auto-repeat, key already down
    mgr._on_press("ctrl")
    assert mgr.is_active is True, "auto-repeat toggled the recording off"
    assert start.call_count == 1
    assert stop.called is False


def test_force_stop_ends_latched_recording(manager, monkeypatch):
    monkeypatch.setitem(settings.data, "activation_mode", "latch")
    mgr, start, stop = manager

    mgr._on_press("ctrl")
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
