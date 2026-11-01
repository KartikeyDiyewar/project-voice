import pytest
from unittest.mock import MagicMock
from utils.hotkey_listener import HotkeyManager
from pynput import keyboard

def test_hotkey_manager_reload_safety():
    """PV-013: reload_keys() while active must trigger stop callback to prevent runaway recording."""
    stop_mock = MagicMock()
    start_mock = MagicMock()
    manager = HotkeyManager(on_start=start_mock, on_stop=stop_mock)
    manager.is_active = True

    manager.reload_keys()
    assert manager.is_active is False
    stop_mock.assert_called_once()

def test_hotkey_manager_combination_matching():
    """PV-005: Hotkey parser must correctly identify tokens in hotkey combinations."""
    manager = HotkeyManager(on_start=MagicMock(), on_stop=MagicMock())
    
    # Test helper matching functions
    assert manager._matches_ctrl(keyboard.Key.ctrl)
    assert manager._matches_ctrl(keyboard.Key.ctrl_l)
    assert manager._matches_ctrl(keyboard.Key.ctrl_r)
    assert manager._matches_space(keyboard.Key.space)
    assert manager._matches_f8(keyboard.Key.f8)
    assert manager._matches_shift(keyboard.Key.shift_l)
    assert manager._matches_alt(keyboard.Key.alt_r)
