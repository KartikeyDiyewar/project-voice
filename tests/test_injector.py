"""Clipboard safety: a dictation must never be lost if the paste misses."""
import time

import pytest
import pyperclip

from core.injector import TextInjector, SETTLE_MS


@pytest.fixture
def injector():
    inj = TextInjector()
    original = pyperclip.paste()
    yield inj
    pyperclip.copy(original)


def _settle(extra=0.35):
    time.sleep(SETTLE_MS / 1000.0 + extra)


def test_dictation_stays_on_clipboard(injector):
    """The text must remain pasteable after injection, whatever the target did."""
    text = "yeh lamba dictation hai jo kho na jaye"
    injector.paste(text)
    _settle()
    assert pyperclip.paste() == text


def test_text_restored_when_clipboard_is_cleared(injector):
    """An app that clears the clipboard after pasting must not eat the dictation."""
    text = "doosra lamba sentence"
    pyperclip.copy("")
    injector.paste(text)
    _settle()
    assert pyperclip.paste() == text


def test_user_copy_is_not_overwritten(injector):
    """If the user copies something during the settle window, theirs wins."""
    injector.paste("teesra sentence")
    time.sleep(0.05)
    pyperclip.copy("MERI APNI COPY")
    _settle(0.4)
    assert pyperclip.paste() == "MERI APNI COPY"


def test_paste_does_not_block_the_pipeline(injector):
    """Injection returns immediately; the clipboard check happens off-thread."""
    start = time.perf_counter()
    injector.paste("speed check")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 200, f"paste() blocked for {elapsed_ms:.0f}ms"
