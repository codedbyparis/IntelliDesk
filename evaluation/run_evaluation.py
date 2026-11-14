"""Evaluate IntelliDesk retrieval and the separate TechQA context benchmark."""

import json
from collections import Counter

from src import config
from src.chunker import chunk_documents
from src.index_store import index_exists
from src.llm_client import check_ollama
from src.rag_pipeline import answer_question
from src.retriever import relevant_results, retrieve
from src.similarity import cosine_similarity, top_k_indices
from src.text_cleaner import clean_text, tokenize
from src.tfidf_vectorizer import TfidfVectorizer

EVALUATION_FILE = config.EVALUATION_DIR / "test_questions.json"


def load_cases():
    """Load evaluation cases without adding them to the application index."""
    with EVALUATION_FILE.open(encoding="utf-8") as file:
        return json.load(file)


def _expected_source_hit(results, expected_source):
    """Check that the expected source appears among the retrieved results."""
    if not expected_source:
        return False
    return any(expected_source.casefold() in result["source"].casefold() for result in results)


def evaluate_local_retrieval(cases):
    """Measure expected-source retrieval and refusal behavior on local cases."""
    correct = 0
    totals = Counter()
    scored = []

    for case in cases:
        results = retrieve(case["question"])
        relevant = relevant_results(results)
        best_score = results[0]["score"] if results else 0.0
        expected_source = case.get("expected_source")

        if expected_source:
            passed = _expected_source_hit(relevant, expected_source)
            metric = "source"
        else:
            passed = not relevant
            metric = "refusal"

        totals[metric] += 1
        correct += int(passed)
        scored.append(
            {
                "id": case["id"],
                "best_score": best_score,
                "expected_relevant": bool(expected_source),
                "passed": passed,
            }
        )
        print(
            f"[{'PASS' if passed else 'FAIL'}] {case['id']}: "
            f"score={best_score:.3f}, expected={expected_source or 'no relevant source'}"
        )

    print(
        f"Local retrieval/refusal: {correct}/{len(cases)} "
        f"({100 * correct / len(cases):.1f}%) at threshold "
        f"{config.SIMILARITY_THRESHOLD:.3f}"
    )
    return all(item["passed"] for item in scored)


def evaluate_techqa_context_retrieval(cases):
    """Test manual retrieval against evaluation-only TechQA supporting passages."""
    documents_by_key = {}
    questions = []
    impossible_cases = []
    for case in cases:
        contexts = case.get("contexts", [])
        if case.get("is_impossible"):
            impossible_cases.append(case)
            continue
        if not contexts:
            continue
        expected_sources = set()
        for context in contexts:
            source = context["filename"]
            key = (source, context["text"])
            expected_sources.add(source)
            if key not in documents_by_key:
                documents_by_key[key] = {
                    "text": clean_text(context["text"]),
                    "source": source,
                    "page": None,
                    "label": config.LABEL_SAMPLE,
                }
        questions.append((case, expected_sources))

    if not questions:
        print("TechQA context retrieval: skipped (no answerable cases with contexts).")
        return True

    documents = list(documents_by_key.values())
    chunks = chunk_documents(documents)
    token_lists = [tokenize(chunk["text"]) for chunk in chunks]
    vectorizer = TfidfVectorizer().fit(token_lists)
    matrix = vectorizer.transform(token_lists)

    hits = 0
    all_passed = True
    for case, expected_sources in questions:
        query = vectorizer.transform_one(tokenize(case["question"]))
        scores = cosine_similarity(query, matrix)
        positions = top_k_indices(scores, config.TOP_K)
        retrieved_sources = {
            chunks[position]["source"]
            for position in positions
            if scores[position] > 0
        }
        passed = bool(expected_sources & retrieved_sources)
        all_passed = all_passed and passed
        hits += int(passed)
        print(
            f"[{'PASS' if passed else 'MISS'}] TechQA {case['id']}: "
            f"expected={', '.join(sorted(expected_sources))}; "
            f"retrieved={', '.join(sorted(retrieved_sources)) or 'none'}"
        )

    print(
        f"TechQA context source hit@{config.TOP_K}: {hits}/{len(questions)} "
        f"({100 * hits / len(questions):.1f}%). This is a separate evaluation corpus, "
        "not the application knowledge base."
    )

    if impossible_cases:
        rejected = 0
        for case in impossible_cases:
            results = relevant_results(retrieve(case["question"]))
            passed = not results
            all_passed = all_passed and passed
            rejected += int(passed)
            print(
                f"[{'PASS' if passed else 'FAIL'}] TechQA impossible {case['id']}: "
                f"{'no local evidence' if passed else 'local evidence matched'}"
            )
        print(
            f"TechQA impossible-question refusal at retrieval: "
            f"{rejected}/{len(impossible_cases)}"
        )
    return all_passed


def evaluate_pipeline(cases):
    """Run answer-status checks only when the local Ollama model is available."""
    available, message = check_ollama()
    if not available:
        print(f"RAG answer evaluation: skipped; {message}")
        return None

    statuses = Counter()
    all_passed = True
    for case in cases:
        result = answer_question(case["question"])
        status_ok = result["status"] == case["expected_status"]
        ticket_ok = result["offer_ticket"] == case["expected_ticket"]
        statuses[result["status"]] += 1
        passed = status_ok and ticket_ok
        all_passed = all_passed and passed
        print(
            f"[{'PASS' if passed else 'FAIL'}] {case['id']}: "
            f"status={result['status']} (expected {case['expected_status']}), "
            f"offer_ticket={result['offer_ticket']} "
            f"(expected {case['expected_ticket']})"
        )
    print(f"RAG status totals: {dict(statuses)}")
    return all_passed


def main():
    if not index_exists():
        raise FileNotFoundError(
            f"No application index found in {config.INDEX_DIR}; "
            "run 'python build_index.py' first."
        )

    evaluation = load_cases()
    print("=== IntelliDesk local retrieval and refusal cases ===")
    all_passed = evaluate_local_retrieval(evaluation["local_cases"])

    print("\n=== Separate TechQA context retrieval benchmark ===")
    techqa_cases = evaluation.get("techqa_cases", [])
    all_passed = evaluate_techqa_context_retrieval(techqa_cases) and all_passed

    print("\n=== Local Qwen RAG answer checks ===")
    pipeline_passed = evaluate_pipeline(evaluation["local_cases"])
    if pipeline_passed is False:
        all_passed = False

    if not all_passed:
        raise SystemExit("RAG evaluation failed; review the cases marked FAIL above.")


if __name__ == "__main__":
    main()