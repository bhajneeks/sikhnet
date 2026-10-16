# Avneet — RAG engine
updated: 2026-10-16
branch: avneet/rag

## Now
Not started — pick up the first item under Next.

## Done
- (nothing yet)

## Next
- Ingest the real dataset (data/raw → qa.jsonl) and fix column mapping
- Add ANTHROPIC_API_KEY to .env and confirm llm mode works
- R2/R4: return follow_ups (3) and perspectives from /api/ask (structured output)
- Improve retrieval (synonyms like started/founded, Punjabi terms, maybe embeddings)

## Blocked on / needs from others
- nothing

## Files I'm touching
- ingest/, backend/retrieval.py, backend/prompts.py, backend/llm.py, backend/app.py, data/
