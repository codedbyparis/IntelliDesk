# IntelliDesk Architecture

## Overview

IntelliDesk has three intentionally separate AI-related components:

1. **Manual RAG retrieval** finds existing support passages.
2. **Supervised ML classification** predicts ticket categories using a trained, locally saved model.
3. **Local LLM generation** uses retrieved context to form an answer.

```text
PDF / TXT / normalized JSONL
             |
  document_loader -> text_cleaner -> chunker
                                      |
                 manual NumPy TF-IDF vectorizer
                                      |
                      cosine similarity ranking
                                      |
                 top-3 results, threshold 0.28
                                      |
Chat input -> app.py -> rag_pipeline -> prompt_builder -> local Ollama / Qwen3
                  |          |                         |
                  |          +-> refusal/error          +-> grounded answer
                  |               and ticket offer            with sources
                  |
                  +-> account-scoped conversation and optional transcript context
                      -> database.py / ticket_manager.py -> SQLite
                  |
Ticket description -> optional classifier -> editable category
                    -> manual category selection always available

Sample guide -> guided troubleshooting page -> explicit user outcome
             -> optional context-bearing ticket -> local admin queue
```

The application has no cloud LLM integration. Streamlit usage-statistics collection is disabled in `.streamlit/config.toml`; the only runtime model HTTP requests are to the configured local Ollama API (`http://localhost:11434`).

## Knowledge ingestion and index

- `src/config.py` defines the project-relative data paths, supported formats, chunk parameters, top-k, similarity threshold, Ollama model, and ticket categories/statuses.
- `src/document_loader.py` reads PDF, UTF-8 TXT, and normalized JSONL records from the configured knowledge-base folders. It preserves source, page, label, and JSONL metadata. Malformed or unreadable files are warned about and skipped; raw external CSV/JSON datasets are not loaded directly.
- `src/text_cleaner.py` normalizes presentation text and tokenizes for search, normalizing common IT spellings and retaining meaningful negations.
- `src/chunker.py` splits pages into 120-word chunks with 30-word overlap and carries source metadata to each chunk.
- `src/tfidf_vectorizer.py` builds a vocabulary and smoothed IDF weights with NumPy. Each row is L2-normalized.
- `src/similarity.py` computes cosine similarity and stable top-k positions with NumPy.
- `src/index_store.py` stores `vectorizer.json`, `chunk_matrix.npy`, and `chunks.json` in `data/index/`. The directory is generated and Git-ignored.
- `src/retriever.py` loads the index lazily, returns up to three positive-score chunks, and applies the configured `0.28` relevance threshold.
- `build_index.py` rebuilds the generated index. It overwrites the current index; do not run it unless the index is missing or a rebuild is intentional.

There are currently 24 sample-only knowledge documents, producing 28 chunks and a 393-term vocabulary. The verified-document folder is empty. The TechQA evaluation corpus is kept outside the production index.

## Answer generation and refusal

`app.py` stores user/assistant messages and source metadata, calls `src.rag_pipeline.answer_question`, and displays source labels. `src.rag_pipeline`:

1. Retrieves relevant chunks.
2. Returns `not_found` for unsupported IT questions or `out_of_scope` for unrelated questions when there is no relevant evidence.
3. Requires direct source evidence for sensitive factual details such as passwords and contact information.
4. Calls `src.prompt_builder` and `src.llm_client` only when evidence is relevant.
5. Returns `error` with a ticket offer if the local model is unavailable or times out.

`src/prompt_builder.py` asks the model to answer only from retrieved context. `src/llm_client.py` calls local Ollama with `qwen3:1.7b`; the model is used for inference and was not trained by this project. Responses include the retrieved source filename/page and whether the source is sample or verified.

## Ticket classification

The classifier is independent of the RAG index:

- Training records: `data/training/mack_ticket_categories.jsonl`, 140 Mack issue descriptions with project-assigned labels across five categories (28 each).
- `src/dataset_processor.py` validates fields/attribution, rejects exact normalized duplicates, and groups near-duplicate issue descriptions at character similarity `>= 0.85`.
- `train_classifier.py` uses a stratified four-fold group split and refuses to fall back to a potentially leaking ungrouped split.
- `src/classifier.py` defines a Scikit-learn Pipeline using TF-IDF (unigrams/bigrams) and balanced Logistic Regression, with Joblib persistence.
- Generated local outputs: `data/models/ticket_category_classifier.joblib` and `data/models/ticket_category_metrics.json` (both ignored by Git).
- The training flow reports accuracy, macro precision/recall/F1 and a labeled confusion matrix, then verifies loading/prediction and reads the saved metrics back.

The classifier was trained and evaluated in the current Python environment. The grouped holdout used 102 training and 38 test records and measured accuracy `0.974`, macro precision `0.978`, macro recall `0.960`, and macro F1 `0.966`. The app loads the classifier lazily when rendering the ticket form; predictions are editable, and manual category selection remains available. These metrics are a small sample result, not production performance. Current checks import PyArrow and SciPy successfully; no Windows security settings were modified or bypassed.

## Application and database

- `src/auth.py` stores local usernames and PBKDF2-HMAC-SHA256 password hashes. Regular users self-register; administrator accounts are provisioned from the trusted terminal with `create_admin.py`.
- `src/ui.py` owns the shared theme, responsive layout, sign-in gate, account-aware navigation, history, and lazy classifier loading.
- `app.py` implements account-scoped chat, conversation navigation/history, source citations, explicit answer feedback, and ticket escalation. A recent transcript/source snapshot is attached by default when escalating, and the requester may opt out.
- `src/database.py` owns SQLite users, conversations, messages, feedback, guided outcomes, and non-destructive schema migrations. Older records with no account owner remain unassigned.
- `src/ticket_manager.py` owns ticket creation, account-filtered reads, status updates, attached context, and statistics. Tickets contain owner, requester/contact, category, description, optional conversation/context, status, and timestamps.
- `src/troubleshooting.py` holds deterministic step lists derived from the named sample guides; `pages/5_Guided_Troubleshooting.py` collects explicit resolved/unresolved outcomes and can submit unresolved issues to the local queue with wizard context.
- `pages/1_Admin_Dashboard.py` is restricted to administrators and displays the shared local IT queue, ticket KPIs, filters, status updates, recent tickets, Plotly charts, and explicitly self-reported outcome/context metrics.
- `pages/2_My_Tickets.py` provides owner-only ticket submission and listing, editable category suggestions when a trained model exists, ticket details, search, status/category filters, and context-helpfulness feedback.
- `pages/3_Knowledge_Base.py` lists supported documents from the sample and verified knowledge folders, without exposing generated index files.
- `pages/4_Settings.py` displays local model status, application information, component roles, and whether the trained classifier artifact is available.
- Resolution rates count explicit user votes only; context-attachment coverage is presence, and context usefulness is a user rating. These are not independently verified resolution or escalation-quality measures.
- Ticket queue state remains in local SQLite; there is no external helpdesk dispatch or ITSM integration. Priority/severity and staff assignment are not implemented.

SQL statements use parameter binding for user-supplied values. The user-facing app does not enable unsafe HTML rendering. Application paths come from `pathlib.Path` locations rooted at the project. `.env`, virtual environments, generated index/database, and model artifact directories are excluded by `.gitignore`.

## Dataset and trust boundaries

- Mack IT Support v1 declares MIT. The source uses `instruction`/`output`; IntelliDesk uses a selected 16-record sample subset and a separate 140-row, project-labeled classifier subset.
- TechQA-RAG-Eval declares Apache-2.0 and is used only for evaluation fixtures: 12 answerable supporting-context cases and 8 impossible questions.
- UmerSajid's troubleshooting dataset was inspected but excluded because no license was declared.
- External troubleshooting content and sample guides are not official LPU/university procedures. Only approved institutional documents should be labeled `verified`.
- See [THIRD_PARTY_NOTICES.md](../data/THIRD_PARTY_NOTICES.md) for dataset attribution and license notices.

## Validation and measured scale

The current fixtures pass 14/14 local retrieval/refusal cases, 12/12 TechQA context source hits at hit@3, 8/8 impossible-question checks, and 14/14 local Qwen status/ticket-offer cases. The full isolated Streamlit journey also passed through new chat, supported response/source display, unsupported refusal, category-corrected ticket submission, app-session restart/history restore, and dashboard filtering.

In the current Windows/Python 3.13 environment:

- Streamlit server returned HTTP 200 in 2.21 seconds after usage-statistics collection was disabled.
- Temporary index build for 24 documents/28 chunks took 0.071 seconds.
- Fifty warm retrievals measured 0.053 ms median and 0.101 ms p95.
- The dense NumPy matrix occupies 88,032 bytes; all generated index files occupy 121,953 bytes.
- One local Qwen answer took 2.62 seconds.

These are single-run local measurements, not guarantees. The dense matrix is appropriate for the included small corpus; the full 19,610-row Mack source is not included or benchmarked for indexing. Traced Python allocation peak during the index build was 435,639 bytes and does not include NumPy native buffers.
