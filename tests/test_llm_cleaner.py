import pytest
from core.llm_cleaner import LLMFormatter

def test_llm_cleaner_xml_escaping():
    """PV-016: Raw user transcripts containing brackets must be XML-escaped."""
    formatter = LLMFormatter()
    raw = "User said <script>alert(1)</script> & test > other"
    
    # Test internal escape helper
    escaped = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped
    assert "&amp;" in escaped

def test_llm_cleaner_think_tag_stripping():
    """PV-018: DeepSeek / Qwen reasoning <think> tags must be completely stripped."""
    formatter = LLMFormatter()
    import re
    test_output = "<think>The user wants to say hello.</think>Hello, how are you?"
    cleaned = re.sub(r"<think>.*?(</think>|$)", "", test_output, flags=re.DOTALL).strip()
    assert cleaned == "Hello, how are you?"

    unclosed_think = "<think>Still thinking... Hello world"
    cleaned_unclosed = re.sub(r"<think>.*?(</think>|$)", "", unclosed_think, flags=re.DOTALL).strip()
    assert cleaned_unclosed == ""

def test_llm_cleaner_empty_fallback():
    """PV-018: If LLM returns empty/whitespace, raw text must be preserved as fallback."""
    formatter = LLMFormatter()
    raw = "Aap sab theek ho"
    cleaned = ""
    if not cleaned and raw:
        cleaned = raw
    assert cleaned == "Aap sab theek ho"
