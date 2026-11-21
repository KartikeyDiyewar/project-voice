"""
Scores the Hinglish cleanup stage against a golden set.

This is an evaluation harness, not training: Groq serves the model, so accuracy
comes from prompt rules plus this measurement loop. Run it after changing
SYSTEM_PROMPT or the phonetic rules to see what improved and what regressed.

Usage:
    python scripts/eval_hinglish.py                # full run
    python scripts/eval_hinglish.py --tag phonetic # only matching tags
    python scripts/eval_hinglish.py --show-fail    # print every failure
"""

import argparse
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.settings import settings
from core.llm_cleaner import LLMFormatter

GOLDEN = ROOT / "tests" / "data" / "hinglish_golden.json"
CORPUS = ROOT / "tests" / "data" / "hinglish_corpus.json"
DEVANAGARI = re.compile(r"[\u0900-\u097F]")


def normalise(text: str) -> str:
    """Compares wording and casing, ignoring punctuation differences."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def score_one(raw: str, expected: str, actual: str) -> dict:
    a, e = normalise(actual), normalise(expected)
    similarity = SequenceMatcher(None, e, a).ratio()
    return {
        "similarity": similarity,
        "exact": a == e,
        "devanagari": bool(DEVANAGARI.search(actual)),
        "translated": _looks_translated(a, e),
        "empty": not a,
        "actual": actual,
    }


def _looks_translated(actual: str, expected: str) -> bool:
    """Flags output that swapped Hindi for English or vice versa wholesale."""
    hindi_markers = {"hai", "hoon", "nahi", "kya", "aur", "mein", "ko", "ka", "ki"}
    exp_hindi = len(hindi_markers & set(expected.split()))
    act_hindi = len(hindi_markers & set(actual.split()))
    return abs(exp_hindi - act_hindi) >= 3


def run(tag_filter=None, show_fail=False, threshold=0.85, corpus=False):
    source = CORPUS if corpus else GOLDEN
    data = json.loads(source.read_text(encoding="utf-8"))
    cases = data["cases"]
    if tag_filter:
        cases = [c for c in cases if any(tag_filter in t for t in c.get("tags", []))]

    if not settings.groq_api_key:
        print("No GROQ_API_KEY configured - cannot evaluate.")
        return 2

    formatter = LLMFormatter()
    if not formatter.client:
        print("Groq client unavailable - check the API key.")
        return 2

    results = []
    print(f"Evaluating {len(cases)} cases against {settings.llm_model}\n")
    print(f"{'case':24s} {'sim':>6s}  {'verdict':8s} notes")
    print("-" * 74)

    for case in cases:
        actual, ms = formatter.format(case["raw"])
        verdict = score_one(case["raw"], case["expected"], actual)
        verdict["id"] = case["id"]
        verdict["ms"] = ms
        verdict["expected"] = case["expected"]
        verdict["raw"] = case["raw"]
        results.append(verdict)

        notes = []
        if verdict["devanagari"]:
            notes.append("DEVANAGARI")
        if verdict["translated"]:
            notes.append("TRANSLATED")
        if verdict["empty"]:
            notes.append("EMPTY")
        status = "PASS" if verdict["similarity"] >= threshold else "FAIL"
        print(f"{case['id']:24s} {verdict['similarity']*100:5.1f}%  {status:8s} {' '.join(notes)}")

        if show_fail and status == "FAIL":
            print(f"    raw      : {verdict['raw']}")
            print(f"    expected : {verdict['expected']}")
            print(f"    actual   : {verdict['actual']}")

    total = len(results)
    passed = sum(1 for r in results if r["similarity"] >= threshold)
    exact = sum(1 for r in results if r["exact"])
    avg = sum(r["similarity"] for r in results) / total
    dev = sum(1 for r in results if r["devanagari"])
    trans = sum(1 for r in results if r["translated"])
    avg_ms = sum(r["ms"] for r in results) / total

    print("-" * 74)
    print(f"cases           : {total}")
    print(f"pass (>= {threshold:.0%})   : {passed}/{total}  ({passed/total:.0%})")
    print(f"exact match     : {exact}/{total}")
    print(f"mean similarity : {avg*100:.1f}%")
    print(f"devanagari leak : {dev}")
    print(f"translation slip: {trans}")
    print(f"mean latency    : {avg_ms:.0f} ms")

    worst = sorted(results, key=lambda r: r["similarity"])[:5]
    print("\nweakest cases:")
    for r in worst:
        print(f"  {r['id']:24s} {r['similarity']*100:5.1f}%")
        print(f"     expected: {r['expected']}")
        print(f"     actual  : {r['actual']}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=None, help="only cases whose tags contain this")
    ap.add_argument("--show-fail", action="store_true")
    ap.add_argument("--threshold", type=float, default=0.85)
    ap.add_argument("--corpus", action="store_true",
                    help="use the OpenSLR-104 derived cases instead of the golden set")
    args = ap.parse_args()
    sys.exit(run(args.tag, args.show_fail, args.threshold, args.corpus))
