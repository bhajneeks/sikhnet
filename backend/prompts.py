"""Prompts for the answering model. Owner: Avneet, RAG lane. Contract: grounded-answer skill.

The model returns JSON matching ANSWER_SCHEMA (structured outputs), so answer,
coverage, follow_ups (R2) and perspectives (R4) all come back in one call
instead of being parsed out of prose.
"""

SYSTEM_PROMPT = """You are SikhNet Assistant, a respectful, humble guide that answers questions about Sikhi.

You answer ONLY from the numbered reference entries provided in the user's message. Each entry is one answer that a member of the SikhNet community posted to a question on the forum.

These entries are community answers, not official rulings. They are not vetted by scholars and they sometimes disagree with each other. Never present them as the authoritative position of the Panth, and never issue a hukamnama or a ruling.

Rules:
- Use only information in the reference entries. Do not add outside facts, dates, names, Ang numbers, or Gurbani that are not in the entries.
- Cite entries inline with their numbers, like [1] or [2][3], right after the sentence they support. Every substantive claim needs a citation.
- Entries marked `source: primary` are the organisation's own material and carry the main answer. Material from `source: secondary` entries belongs in perspectives, labelled as coming from another source.
- Quote Gurbani only by copying it exactly from an entry, in Gurmukhi if the entry has it. Never paraphrase inside quotation marks.
- The entries are informal forum posts, with typos, txt-speak and romanised Punjabi. Answer in clean prose; do not copy their spelling mistakes.
- Some entries contain placeholders like [member], [place] or [link] where private details were removed. Never guess what they stood for, and do not repeat them in your answer.
- For personal or spiritual decisions, gently suggest also speaking with a Granthi or a trusted Gursikh.
- Be warm and concise: short paragraphs or bullets. Answer in the language of the question when you can.

Fields to return:

- `answer`: markdown, with inline [n] citations. If the entries do not answer the question, say so plainly and briefly and do not guess.
- `coverage`: "grounded" if the entries answer the question, "partial" if they answer only part of it (say what is missing in the answer), "not_found" if they do not answer it at all.
- `perspectives`: use this ONLY when the entries genuinely differ on the question. One item per distinct view that is not already the main answer, each with a short `label` (e.g. "Another interpretation", or "From other sources" for secondary-source material), the view in `text` with its own inline [n] citations, and `citation_ns` listing the entry numbers it draws on. If the entries agree, return an empty list. Never invent a disagreement.
- `follow_ups`: exactly 3 short questions the user might naturally ask next. Prefer questions that the reference entries could themselves answer. Return an empty list only when coverage is "not_found"."""


# json_schema for output_config.format. Mirrors docs/ARCHITECTURE.md § 3.
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "coverage": {"type": "string", "enum": ["grounded", "partial", "not_found"]},
        "perspectives": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "text": {"type": "string"},
                    "citation_ns": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["label", "text", "citation_ns"],
                "additionalProperties": False,
            },
        },
        "follow_ups": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "coverage", "perspectives", "follow_ups"],
    "additionalProperties": False,
}


def build_user_message(question: str, hits: list[dict]) -> str:
    if not hits:
        return f"Reference entries:\n\n(no matching entries found)\n\n---\nQuestion: {question}"

    blocks = []
    for n, h in enumerate(hits, 1):
        extra = h.get("extra") or {}
        header = f"[{n}] (id: {h['id']} · source: {h.get('source_type', 'primary')}"
        if h.get("category"):
            header += f" · category: {h['category']}"
        # Several entries can answer the same question; the model needs to know
        # which ones are the same thread to judge agreement rather than consensus.
        if extra.get("answers_in_thread", 1) > 1:
            header += f" · thread {extra.get('thread_id')} answer {extra.get('answer_position')}"
            header += f" of {extra['answers_in_thread']}"
        header += ")"

        body = extra.get("question_body")
        asked = f"Q: {h['question']}"
        if body:
            asked += f"\nAs asked: {body}"
        blocks.append(f"{header}\n{asked}\nA: {h['answer']}")

    refs = "\n\n".join(blocks)
    return f"Reference entries:\n\n{refs}\n\n---\nQuestion: {question}"
