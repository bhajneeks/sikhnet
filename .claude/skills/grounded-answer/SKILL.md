---
name: grounded-answer
description: The answering contract for the Sikhi Q&A bot — every answer is grounded in retrieved dataset entries, cites their ids, and says plainly when the dataset does not cover the question. Use when writing or changing the system prompt, retrieval, or answer formatting in backend/, or when the user asks "how should the bot answer", "why did it say that", "it's hallucinating".
---

# Grounded Answer

Adapted from gbrain's `query` skill contract. For a religious-guidance bot, a
confident wrong answer is worse than "I don't know". This contract is what the
backend prompt (`backend/prompts.py`) and evals (`evals/`) enforce.

## Contract

1. **Grounded:** the answer uses only the retrieved Q&A entries passed in
   context. No outside facts, no invented Gurbani quotes, Ang numbers, or
   historical dates.
2. **Cited:** every substantive claim maps to one or more entry ids, returned in
   `citations`. The UI shows them so users can read the original answer.
3. **Gap-flagged:** if no retrieved entry answers the question, say so and set
   `coverage: "not_found"`. If partly answered, `coverage: "partial"` and say
   what's missing.
4. **Conflicts surfaced:** if two entries disagree, present both with citations
   rather than picking one.
5. **Respectful and humble tone:** suggest consulting a Granthi or trusted
   Gursikh for personal/spiritual decisions; never issue hukamnamas or rulings
   on behalf of the Panth.
6. **Gurbani verbatim:** quotes of Gurbani must be copied exactly from an entry,
   in Gurmukhi if the entry has it, never paraphrased inside quote marks.

## Procedure when changing answering behavior

1. Read `backend/prompts.py` and `docs/ARCHITECTURE.md` § API contract.
2. Make the change.
3. Run `python3 evals/run_evals.py` (owned by evals lane) before and after.
   No merging a prompt change that lowers the grounded/cited scores — this is
   gbrain's no-regression rule from `skillify`.
4. Record notable prompt decisions with `capture-decision`.
