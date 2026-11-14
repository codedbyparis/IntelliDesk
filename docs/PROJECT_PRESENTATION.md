# IntelliDesk Project Presentation

## Slide 1 — Project title and introduction

- **IntelliDesk: Local AI-Powered IT Helpdesk**
- A Streamlit demonstration that retrieves support information, cites its source, and escalates unanswered questions.
- Sample dataset material is explicitly distinguished from approved university procedures.

## Slide 2 — Problem statement

- IT users need relevant guidance and a way to verify where it came from.
- Unanchored chatbot answers can be plausible but unsupported.
- Unresolved issues need a structured support-ticket path.

## Slide 3 — Objectives

- Demonstrate manual, inspectable RAG retrieval.
- Generate answers from local retrieved context and show source attribution.
- Refuse unsupported questions and offer ticket escalation.
- Track conversations/tickets with SQLite and show useful admin statistics.
- Keep category classification separate from retrieval.

## Slide 4 — Proposed solution

- Search a local knowledge base before answering.
- Use a similarity threshold and direct-evidence checks to reduce unsupported responses.
- Use local Qwen3 through Ollama; no cloud LLM API.
- Save conversations and tickets locally in SQLite.
- Add account-scoped user conversations/tickets, sample guided steps, and feedback-based outcome reporting.
- Provide editable predicted ticket categories while retaining manual selection.

## Slide 5 — System architecture

- **RAG:** document loader → cleaner → chunker → NumPy TF-IDF → cosine similarity → thresholded sources.
- **Generation:** retrieved context → prompt builder → Ollama API → Qwen3 answer/refusal.
- **Tickets:** account-scoped Streamlit form → optional transcript context → editable classifier suggestion or manual category → SQLite local admin queue.
- **Guidance:** sample-only deterministic troubleshooting steps → explicit outcome report → optional context-bearing local ticket.
- The three components have separate responsibilities.

## Slide 6 — Manual RAG implementation

- Supported knowledge-base formats: PDF, TXT, and normalized JSONL.
- 120-word chunks with 30-word overlap.
- Custom NumPy TF-IDF and cosine similarity; top 3 results and current threshold `0.28`.
- Current sample corpus: 24 documents, 28 chunks, 393-term vocabulary.
- Sources are labeled Sample or Verified; the current verified folder is empty.

## Slide 7 — Supervised ML ticket classifier

- Scikit-learn TF-IDF + balanced Logistic Regression, saved with Joblib.
- 140 Mack issue descriptions, project-labeled across five categories (28 each); labels are not supplied by Mack.
- Exact duplicate rejection and near-duplicate grouping; grouped holdout uses 102 training and 38 test records.
- Held-out metrics: accuracy **0.974**, macro precision **0.978**, macro recall **0.960**, macro F1 **0.966**.
- Predictions are editable suggestions. Metrics describe this small project-labeled sample, not production accuracy.

## Slide 8 — Qwen3 and Ollama integration

- Qwen3 1.7B is served locally by Ollama through its local HTTP API.
- Retrieved context is supplied to the model; the project did not train Qwen3.
- Unsupported responses and local model failures offer ticket escalation.
- No cloud model endpoint is used.

## Slide 9 — Database and Streamlit interface

- Responsive Streamlit shell with sign-in, chat/history, guided troubleshooting, My Tickets, Knowledge Base, Settings & About, and an admin-only dashboard.
- SQLite stores local accounts, account-scoped conversations/tickets, message sources, and explicit answer/guided/context feedback.
- User accounts are locally registered; admin accounts are created separately. Users see only their own conversations/tickets, while admins can review the shared local queue.
- Chat escalations may include a recent transcript and sources; users can opt out. Guided issue outcomes and ticket-context ratings are explicit user reports.
- Tickets support editable manual category selection, search, category/status filters, and status updates.
- Dashboard includes ticket KPIs, recent ticket cards, and Plotly category/status/trend charts.
- Sample/verified source labels remain visible; generated index files are not exposed as documents.

## Slide 10 — Testing and evaluation

- Local retrieval/refusal: **14/14** passed.
- TechQA supporting-context retrieval: **12/12** source hits at hit@3.
- Impossible questions against local KB: **8/8** rejected.
- Local Qwen status/ticket-offer cases: **14/14** passed (9 answered, 3 not found, 2 out of scope).
- Isolated end-to-end Streamlit journey passed, including SQLite persistence across a fresh app session.
- The classifier generated held-out accuracy/precision/recall/F1 and a confusion matrix; results are for the small grouped holdout only.
- Measured locally: server HTTP 200 in 2.21 s after telemetry was disabled, temporary index build in 0.071 s, warm retrieval median 0.053 ms/p95 0.101 ms, one Qwen answer in 2.62 s.

## Slide 11 — Limitations and future scope

- Sample-only knowledge base; no verified university policy documents are indexed.
- The classifier uses 140 project-labeled examples across five categories; independently labeled real tickets are needed to establish generalization.
- Full Mack source and large-corpus performance are not included or benchmarked; dense manual TF-IDF is designed for the current small demo.
- Tickets remain in a local queue, with no external helpdesk dispatch, priority/severity, or staff assignment.
- Guided steps use sample documents, not approved university procedures; reported outcomes are not independently verified.
- Future scope: approved institutional documents, independently reviewed labels, classifier evaluation on unseen tickets, and ticket assignment/priority workflows.

## Slide 12 — Conclusion

- IntelliDesk demonstrates source-attributed local RAG, local LLM generation, persistent ticket management, and refusal behavior.
- Retrieval, classification, and generation remain separate.
- The application and manual ticket flow are demonstrable now.
- The classifier was trained and evaluated, but the holdout is small and labels were assigned for this project rather than supplied by Mack.
- Suggested closing demo: register/sign in, ask a supported Wi-Fi question and show its sample source, request the official Wi-Fi password to show refusal, run sample guided troubleshooting, submit a context-bearing ticket with a corrected category, then show My Tickets and the admin local queue.
