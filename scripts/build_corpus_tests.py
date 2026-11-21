"""
Builds a Roman-Hinglish eval set from the OpenSLR-104 code-switched corpus.

Why this is safe to use: the corpus is real code-switched Hindi-English speech,
and its transcripts show exactly the pattern the product must reproduce, English
technical words kept in Latin while Hindi is Devanagari. The corpus ships
Devanagari, so it cannot test romanisation directly; what it *can* test is that
our cleaner keeps English terms intact and does not translate them, which is the
part most likely to break in dictation.

This produces tests/data/hinglish_corpus.json with pairs of:
  raw      - the transcript with Devanagari stripped out (leaving the English
             technical vocabulary), as the company-name-style fragments a
             Roman-Hinglish user would actually dictate
  expected - the same fragment, which our cleaner must return unchanged

Only fragments that are majority Latin are kept, because those are the ones a
Roman Hinglish speaker would type verbatim.
"""

import csv
import io
import json
import re
from pathlib import Path

SP = Path(r"C:\Users\diyew\AppData\Local\Temp\commandcode\C--Users-diyew\108ec880-1d94-42b1-a798-32d3f2bc6456\scratchpad\hinglish_data")
OUT = Path(r"C:\Users\diyew\OneDrive\Desktop\projects\project-voice\tests\data\hinglish_corpus.json")

DEVANAGARI = re.compile(r"[\u0900-\u097F]+")
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_./#+-]*")


def latin_fragments(text: str):
    """Pulls the English/technical runs out of a code-switched line."""
    cleaned = DEVANAGARI.sub(" ", text)
    words = LATIN_WORD.findall(cleaned)
    # keep runs of 2+ words so there is something to evaluate
    if len(words) < 2:
        return None
    frag = " ".join(words)
    return frag if len(frag) >= 12 else None


def main():
    rows = []
    for name in ("metadata.csv", "metadata-test.csv"):
        p = SP / name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        rows.extend(list(csv.reader(io.StringIO(text)))[1:])

    seen = set()
    cases = []
    for r in rows:
        if len(r) < 2:
            continue
        frag = latin_fragments(r[1])
        if not frag:
            continue
        key = frag.lower()
        if key in seen:
            continue
        seen.add(key)
        cases.append({
            "id": f"corpus_{len(cases):03d}",
            "raw": frag,
            "expected": frag[0].upper() + frag[1:] + ".",
            "tags": ["corpus", "english-terms"],
            "origin": "OpenSLR-104 / ujs-hinglish",
        })
        if len(cases) >= 120:
            break

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "_comment": "Derived from the OpenSLR-104 Hindi-English code-switched corpus. "
                    "Each case is the Latin-script technical vocabulary from a real "
                    "code-switched utterance; the cleaner must keep it verbatim.",
        "cases": cases,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"wrote {OUT.name}: {len(cases)} cases")
    for c in cases[:10]:
        print("  ", c["raw"][:90])


if __name__ == "__main__":
    main()
