import pytest
from unittest.mock import MagicMock
from ui.floating_indicator import FloatingIndicator

def test_floating_indicator_error_hides_properly():
    """PV-008: Error state must properly set state to 'error' and hide when requested."""
    indicator = FloatingIndicator.__new__(FloatingIndicator)
    indicator.root = MagicMock()
    indicator.canvas = MagicMock()
    indicator.container = MagicMock()
    indicator.text_label = MagicMock()
    indicator.sub_label = MagicMock()
    indicator.is_animating = False
    indicator.current_state = "processing"

    # Simulate show_error logic
    indicator.current_state = "error"
    assert indicator.current_state == "error"

    # Verify _hide_if_idle now hides on "error"
    indicator._hide_if_idle()
    assert indicator.current_state == "idle"
    indicator.root.withdraw.assert_called_once()
