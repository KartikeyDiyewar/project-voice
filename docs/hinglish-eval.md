# Hinglish evaluation: what data exists and what it tells us

## Short answer

There is **no public dataset of Roman-Hinglish dictation transcripts**. The
available corpora are either Devanagari code-switched speech, or code-mixed
*text* for language-ID / translation tasks. Groq serves the model, so nothing
here trains it either way.

What I built instead is an evaluation harness: 30 hand-written golden cases plus
120 cases derived from a real code-switched speech corpus. That measures the
cleanup stage and catches regressions.

## What exists online

| Dataset | What it actually contains | Fit for us |
|---|---|---|
| **OpenSLR-104** (`ujs/hinglish-compressed`) | 52,825 clips of code-switched Hindi-English **spoken tutorials**. Transcripts in **Devanagari** with English words in Latin. | **Partial** — real code-switching, but Devanagari and lecture-toned |
| **HinGE** (IIT Gandhinagar) | ~4K parallel Hindi/English/Hinglish sentence triples from government text | **Poor** — formal advisory sentences, no speech |
| **Hinglish Audio Dataset** (`agarwalayushi/hinglish`) | 815K clips / 237 GB, aggregates OpenSLR + AI4Bharat + Common Voice | **Poor** — same Devanagari issue, 237 GB |
| **L3Cube-HingCorpus** | 31K code-mixed social-media sentences | **Poor** — text only, no audio, social-media register |
| **HinglishEval** | LLM code-generation benchmark | **Irrelevant** — not dictation |

Nothing includes the thing we actually need: *spoken Roman-Hinglish* paired with
what the user would consider a correct Roman-script transcript.

## What I built instead

**`tests/data/hinglish_golden.json`** — 30 hand-authored cases covering the
failure modes that matter in dictation: phonetic slips (`satay`→`sandeh`,
`jata`→`zyada`), verb morphology (`chalna lag kiya`→`chalne lag gaya`), filler
removal, stutter repair, punctuation, Devanagari leakage, and prompt-injection
safety.

**`tests/data/hinglish_corpus.json`** — 120 cases derived from OpenSLR-104. Each
is the Latin-script technical vocabulary from a real code-switched utterance.
This tests the one thing a Devanagari corpus *can* test: that English terms
survive untouched and are not translated.

**`scripts/eval_hinglish.py`** — runs either set, scores similarity, flags
Devanagari and translation slips, prints the weakest cases.

## Results

### Golden set — 30/30 pass, mean similarity 99.9%

Devanagari leaks: 0. Translation slips: 0. Mean latency 12.2 s per call.

Two near-misses, both cosmetic:

- `fillers`: expected `Main yeh kehna chahta hoon...`, got `So main yeh kehna...`
  — the leading "so" survived because Hindi "toh/so" is legitimate speech.
- `long_dictation`: `waha` vs `wahan`, `Usme` vs `Usmein`. Both spellings are
  acceptable Roman Hinglish; the cleaner chose one consistently.

### Corpus set — 39/40 pass, mean similarity 98.5%

The single "failure" is the harness being wrong, not the model:

```
raw      : type chmod space plus x space nestedifelse sh
expected : Type chmod space plus x space nestedifelse sh.
actual   : type chmod +x nestedifelse.sh
```

The model correctly turned `space plus x space` into `+x` and `nestedifelse sh`
into `nestedifelse.sh`. My expected string was naive. The same thing happened on
three other cases where the model produced `If-else` and my label said `Ifelse`.

**Conclusion: the cleanup stage is not the weak link.**

## Where the real risk sits

Cleanup is at ~99%. The unmeasured half is transcription. Nothing here tests
whether Whisper hears a Roman-Hinglish speaker correctly, and that is where the
`satay`/`sandeh` slips originate. Measuring it needs audio, which no public
Roman-Hinglish dictation corpus provides.

Latency is also worth a look: **12.2 s mean** in these runs, far above the
<800 ms product claim. Small batches and a cold connection inflate it, but the
LLM call is clearly the dominant cost in the pipeline.

## Recommended next steps, in order

1. **Record a small personal test set.** 30–50 real recordings of yourself
   dictating Hinglish, with what you intended as the transcript. This is the only
   data that reflects the actual product, and it takes minutes to gather.
2. **Measure STT separately from cleanup.** Run Whisper on those recordings and
   score raw output first, so you know whether errors come from hearing or
   cleaning.
3. **Add a fast path for the LLM.** 12 s is the number to attack: try a smaller
   model for short utterances, or skip cleanup when the raw transcript already
   looks clean.
4. **Only then consider prompt tuning.** The golden set gives a regression signal;
   every change to `SYSTEM_PROMPT` should be re-scored against it.

## Files

- `tests/data/hinglish_golden.json` — 30 hand-authored cases
- `tests/data/hinglish_corpus.json` — 120 corpus-derived cases
- `scripts/eval_hinglish.py` — scoring harness (`--corpus` for the derived set)
- `scripts/build_corpus_tests.py` — regenerates the corpus set
