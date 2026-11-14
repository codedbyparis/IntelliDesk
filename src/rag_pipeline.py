"""
rag_pipeline.py - The full question -> answer flow (the "brain" of IntelliDesk).

answer_question(question, history) returns ONE result dictionary:
    status              "answered", "out_of_scope", "not_found" or "error"
    answer              text to show the user
    sources             [{"source", "page", "label", "score"}, ...] (only when answered)
    best_score          the best retrieval score found (useful for tuning)
    uses_sample_content True if any source is sample demonstration material
    offer_ticket        True whenever the chatbot could not answer reliably
    error               technical detail when status is "error", else None

Flow: retrieve -> scope check -> prompt -> local LLM -> not-found check -> result
"""

import re

from src import config
from src.llm_client import LLMError, generate_answer
from src.prompt_builder import NOT_FOUND_MARKER, build_messages
from src.retriever import relevant_results, retrieve
from src.text_cleaner import tokenize

OUT_OF_SCOPE_MESSAGE = (
    "I couldn't find information about this in the approved IT support documents, "
    "so I can't answer it reliably. I can create a support ticket so the IT team "
    "can help you."
)
NOT_FOUND_MESSAGE = (
    "The IT support documents I have don't contain a reliable answer to this "
    "question. I can create a support ticket so the IT team can help you."
)
ERROR_MESSAGE = (
    "I can't generate an answer right now because the AI model is unavailable. "
    "I can create a support ticket so the IT team can help you."
)

TECH_SUPPORT_TERMS = {
    "account",
    "application",
    "browser",
    "camera",
    "computer",
    "database",
    "device",
    "driver",
    "email",
    "hardware",
    "install",
    "installation",
    "internet",
    "lab",
    "login",
    "lms",
    "m365",
    "microsoft",
    "network",
    "outlook",
    "password",
    "portal",
    "printer",
    "security",
    "server",
    "software",
    "system",
    "teams",
    "vpn",
    "wifi",
    "wireless",
}


def _collect_sources(chunks):
    """List each (file, page) once, with its label and best score."""
    sources = []
    seen = set()
    for chunk in chunks:
        key = (chunk["source"], chunk["page"])
        if key in seen:
            continue
        seen.add(key)
        source = {
            "source": chunk["source"],
            "page": chunk["page"],
            "label": chunk["label"],
            "score": round(chunk["score"], 3),
        }
        if chunk.get("metadata"):
            source["metadata"] = chunk["metadata"]
        sources.append(source)
    return sources


def _is_not_found(answer):
    """True if the model replied with the not-found marker (in any spacing or case)."""
    normalized = answer.upper().replace("_", " ")
    return NOT_FOUND_MARKER.replace("_", " ") in normalized


def _is_technical_support_question(question):
    """Distinguish unsupported IT questions from unrelated questions."""
    return bool(TECH_SUPPORT_TERMS.intersection(tokenize(question)))


def _has_explicit_answer_evidence(question, chunks):
    """Require direct source evidence for credentials and contact details."""
    question_words = set(tokenize(question))
    context = "\n".join(chunk["text"] for chunk in chunks)

    if {"wifi", "password"} <= question_words and not re.search(
        r"\b(?:password|passphrase)\b", context, re.IGNORECASE
    ):
        return False
    if {"email", "address"} <= question_words and not re.search(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", context, re.IGNORECASE
    ):
        return False
    if {"phone", "number"} <= question_words and not re.search(
        r"\b(?:\+?\d[\d ()-]{7,}\d)\b", context
    ):
        return False
    if (
        {"opening", "hours"} <= question_words
        or {"closing", "hours"} <= question_words
        or "when" in question_words and "open" in question_words
    ) and not re.search(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b", context, re.IGNORECASE):
        return False
    if (
        {"url"} <= question_words
        or {"website", "address"} <= question_words
        or "link" in question_words
    ) and not re.search(r"https?://\S+", context, re.IGNORECASE):
        return False
    return True


def _result(status, answer, sources=None, best_score=0.0, error=None):
    sources = sources or []
    return {
        "status": status,
        "answer": answer,
        "sources": sources,
        "best_score": round(best_score, 3),
        "uses_sample_content": any(
            source["label"] == config.LABEL_SAMPLE for source in sources
        ),
        "offer_ticket": status != config.STATUS_ANSWERED,
        "error": error,
    }


def answer_question(question, history=None):
    """Answer one question using only the approved knowledge base."""
    question = question.strip()
    if not question:
        raise ValueError("The question is empty.")

    results = retrieve(question)
    best_score = results[0]["score"] if results else 0.0
    relevant = relevant_results(results)

    # Safety net 1: nothing in the documents matches -> do not call the LLM.
    if not relevant:
        if _is_technical_support_question(question):
            return _result(
                config.STATUS_NOT_FOUND, NOT_FOUND_MESSAGE, best_score=best_score
            )
        return _result(
            config.STATUS_OUT_OF_SCOPE, OUT_OF_SCOPE_MESSAGE, best_score=best_score
        )

    if not _has_explicit_answer_evidence(question, relevant):
        return _result(
            config.STATUS_NOT_FOUND, NOT_FOUND_MESSAGE, best_score=best_score
        )

    messages = build_messages(question, relevant, history)
    try:
        answer = generate_answer(messages)
    except LLMError as error:
        return _result(
            config.STATUS_ERROR, ERROR_MESSAGE, best_score=best_score, error=str(error)
        )

    # Safety net 2: the model says the context does not contain the answer.
    if _is_not_found(answer):
        return _result(
            config.STATUS_NOT_FOUND, NOT_FOUND_MESSAGE, best_score=best_score
        )

    return _result(
        config.STATUS_ANSWERED,
        answer,
        sources=_collect_sources(relevant),
        best_score=best_score,
    )


# ---------------------------------------------------------------------------
# Quick self-check: run with  python -m src.rag_pipeline
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tests = [
        ("My Wi-Fi is connected but there is no internet", config.STATUS_ANSWERED),
        ("I forgot my email password", config.STATUS_ANSWERED),
        ("How do I change my Wi-Fi password?", config.STATUS_NOT_FOUND),
        ("Who won the cricket match yesterday?", config.STATUS_OUT_OF_SCOPE),
        ("How do I install MATLAB on my laptop?", config.STATUS_NOT_FOUND),
    ]

    assert not _has_explicit_answer_evidence(
        "How do I change my Wi-Fi password?",
        [{"text": "Reconnect to the campus network with your credentials."}],
    )
    assert _has_explicit_answer_evidence(
        "I forgot my email password",
        [{"text": "Use the official password reset option."}],
    )
    print(f"Similarity threshold: {config.SIMILARITY_THRESHOLD}\n")
    for question, expected in tests:
        result = answer_question(question)
        verdict = "OK   " if result["status"] == expected else "CHECK"
        sources = [(s["source"], s["page"], s["label"]) for s in result["sources"]]
        print(f"[{verdict}] {question}")
        print(f"        status={result['status']} (expected {expected})  best_score={result['best_score']}")
        print(f"        sources={sources}")
        print(f"        offer_ticket={result['offer_ticket']}  uses_sample_content={result['uses_sample_content']}")
        print(f"        answer: {result['answer'][:250]!r}\n")

    # The LLM being unreachable must give status "error", not a crash.
    real_url = config.OLLAMA_BASE_URL
    config.OLLAMA_BASE_URL = "http://localhost:9"
    try:
        result = answer_question("My Wi-Fi is connected but there is no internet")
        print(f"LLM down -> status={result['status']}, offer_ticket={result['offer_ticket']}")
        assert result["status"] == config.STATUS_ERROR
        assert result["offer_ticket"] is True
    finally:
        config.OLLAMA_BASE_URL = real_url
    print("\nError handling check passed.")