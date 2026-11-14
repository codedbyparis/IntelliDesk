# IntelliDesk Project Viva

## Project overview

IntelliDesk is a local AI-powered IT helpdesk demonstration. It searches a small knowledge base, displays retrieved source references, generates a grounded answer through Qwen3 running in Ollama, and offers SQLite ticket escalation when the available evidence is insufficient. All included guidance is sample information, not verified LPU or university procedure.

## Problem statement

Users may need quick IT guidance but cannot easily identify which information is relevant or where it came from. A chatbot can also invent plausible but unsupported steps. IntelliDesk demonstrates source-attributed retrieval, local answer generation, an explicit unsupported-answer path, ticket tracking, and a separately trained ticket-category classifier.

## Objectives

- Implement manual document cleaning, chunking, NumPy TF-IDF, cosine similarity, and thresholded retrieval.
- Provide answer generation using a local Ollama model and retrieved context only.
- Display source attribution and preserve conversation history.
- Escalate unsupported or failed questions through editable ticket submission.
- Provide a separate supervised classifier workflow without making application startup depend on a model artifact.
- Demonstrate ticket status tracking and administrator statistics.

## Architecture

```text
Documents -> loader -> cleaning -> chunking -> manual NumPy TF-IDF index
                                                     |
Question -> retrieval + threshold -> cited context -> local Ollama / Qwen3
                                                     |
                                    answer or refusal / ticket form
                                                     |
                            account-scoped conversations, messages, feedback,
                            guided outcomes, tickets -> SQLite

Ticket description -> optional separate Scikit-learn classifier -> editable suggestion
                    -> manual category selection always available
```

### Manual RAG retrieval

1. The loader reads PDF, TXT, and normalized JSONL records and carries their source and sample/verified label.
2. The cleaner normalizes whitespace and punctuation. The tokenizer lowercases text, normalizes common IT terms, removes low-information stop words, and deliberately retains negations such as "no" and "not".
3. The chunker splits documents into 120-word chunks with 30-word overlap.
4. The custom NumPy TF-IDF implementation builds a vocabulary and document frequency from the chunks. For term `t` in document `d`, the implementation uses `tf * (log((1 + N) / (1 + df)) + 1)` and L2-normalizes each row.
5. A query is transformed with the same vocabulary. NumPy cosine similarity ranks chunks; the current threshold is `0.28`, and up to three relevant results are returned.
6. Retrieved text and source metadata are passed to Qwen3. The pipeline requires evidence for requested factual details and refuses/escalates if it cannot support an answer.

### Why implement TF-IDF manually?

The project demonstrates the retrieval mechanics explicitly: vocabulary creation, document frequency, inverse document frequency, vector normalization, and ranking. This keeps the retrieval path small and inspectable and satisfies the manual RAG architecture. Scikit-learn TF-IDF is used only inside the independent ticket classifier; it does not replace this retriever.

### How cosine similarity works

For query vector `q` and document vector `d`, cosine similarity is:

`cos(q, d) = (q · d) / (||q|| ||d||)`

It compares the direction of the vectors rather than their raw length. A larger score means more overlap in the weighted terms. Zero vectors receive a score of zero. The threshold is a relevance cutoff, not a probability or confidence score.

### Supervised ticket classifier

The trained classifier is a Scikit-learn Pipeline containing `TfidfVectorizer` (lowercase, Unicode accent stripping, unigrams and bigrams, sublinear term frequency) and balanced `LogisticRegression`. The 140 Mack issue descriptions have project-assigned labels in five categories; Mack itself does not provide these ticket labels. Exact normalized duplicates are rejected, and descriptions with character-sequence similarity of at least `0.85` are grouped so related records cannot cross the stratified four-fold group holdout. The held-out split used 102 training and 38 test records.

Held-out metrics were accuracy `0.974`, macro precision `0.978`, macro recall `0.960`, and macro F1 `0.966`. The confusion matrix and metrics JSON were saved locally, then the model was reloaded and prediction verified. These scores describe one small, project-labeled holdout and do not establish production performance. Predictions remain editable and manual category selection remains available.

Confusion matrix (rows are actual; columns are predicted, ordered Account Security, Computer Lab, Software Installation, University Email, Wi-Fi):

| Actual \ Predicted | Account Security | Computer Lab | Software Installation | University Email | Wi-Fi |
|---|---:|---:|---:|---:|---:|
| Account Security | 4 | 0 | 1 | 0 | 0 |
| Computer Lab | 0 | 6 | 0 | 0 | 0 |
| Software Installation | 0 | 0 | 8 | 0 | 0 |
| University Email | 0 | 0 | 0 | 8 | 0 |
| Wi-Fi | 0 | 0 | 0 | 0 | 11 |

### Classification versus retrieval

- **Retrieval** ranks existing document chunks for a question and returns relevant source material. It does not assign a ticket label.
- **Classification** learns a mapping from labeled issue descriptions to one of the known ticket categories. It predicts a category but does not retrieve troubleshooting instructions.
- **Generation** uses Qwen3 to phrase a response grounded in retrieved passages. The model was not trained by this project.

### Local LLM and Ollama

Ollama serves the locally installed `qwen3:1.7b` model over its local HTTP API. The application supplies retrieved context and asks the model to answer only from it. No cloud AI API is used. If Ollama is unavailable, the application reports the local component error and allows ticket escalation.

## Datasets, labels, and licensing

- **Mack IT Support Dataset v1** (`benjaminmacklin/IT_Support`) declares MIT. The project includes 16 selected records in the sample knowledge base and 140 attributed issue descriptions for the classifier. The source has `instruction`/`output` data, not ticket categories; the five classifier labels were assigned by project review. Each training row records `question`, `category`, source dataset/URL/file/line, license, and a labeling note. The inspected source file contained exact duplicate question/answer pairs, so a subset was selected.
- **TechQA-RAG-Eval** (`nvidia/TechQA-RAG-Eval`) declares Apache-2.0. The checked-in evaluation fixtures use `id`, `question`, `answer`, `contexts`, and `is_impossible`; 12 answerable cases with supporting contexts and eight impossible cases are evaluation-only and are not added to the application index.
- **UmerSajid/IT-Troubleshooting-Dataset** was inspected but excluded because no license was declared.
- All included external support content and demonstration guides are sample information, not official LPU/university procedures. No verified university documents currently populate `data/knowledge_base/verified/`.

The project subset has 140 non-empty classifier records, 28 examples per each of five categories, complete source/license/line attribution, and no exact normalized duplicate questions. Near-duplicate issue descriptions are grouped for the proposed split. The subset is small and cannot establish production classifier accuracy.

## Database design

SQLite stores:

- `conversations`: conversation ID and creation time.
- `messages`: conversation foreign key, role, content, RAG status, source JSON, and creation time.
- `tickets`: optional conversation ID, requester name/contact, category, issue description, status, and timestamps.
- `users`: local username, per-user salt, PBKDF2 password hash, and role. Users self-register; administrators are provisioned separately from a trusted terminal.
- `message_feedback`, `guided_outcomes`, and `ticket_context_feedback`: explicit user-reported answer resolution, guided resolution, and attached-context usefulness.

Ticket status values are Open, In Progress, and Resolved. User conversations and tickets are scoped by account; the admin dashboard is an admin-only shared local queue. Existing unowned records are not automatically assigned to a new account. Chat escalation can attach a recent transcript and sources by default, with an opt-out checkbox. Ticket category and status can be filtered; the dashboard shows status/category totals and tickets per day. Priority/severity, staff assignment, and external helpdesk dispatch are not implemented. Database migration checks use temporary database files.

### Guided troubleshooting and evaluation

The guided troubleshooting page presents fixed, ordered steps derived from the existing sample Wi-Fi, portal, email, software, lab, LMS, booking, and account-security documents. Each session is clearly labeled as sample/not official. Users explicitly report whether the steps worked; unresolved sessions can create a ticket in the local queue with the completed steps and sample source attached.

The dashboard reports the number and rate of submitted answer/guided resolution votes, ticket context-attachment coverage, and user ratings of attached context. These are feedback indicators only: they do not establish independently verified resolution rates or escalation quality, and no ticket is dispatched to a real IT team.

## Evaluation metrics and current evidence

RAG evaluation uses expected-source retrieval and refusal checks, a separate TechQA supporting-context retrieval benchmark, impossible-question rejection, and (when Ollama is available) answer-status/ticket-offer expectations. These small fixtures are regression checks, not generalized accuracy guarantees.

The latest executed run passed 14/14 local retrieval/refusal cases, 12/12 answerable TechQA source hits at hit@3, 8/8 impossible-question rejection checks, and 14/14 local Qwen status/ticket-offer checks (9 answered, 3 not found, 2 out of scope).

Classifier metrics and their meaning:

- **Accuracy**: fraction of held-out examples assigned the exact correct category.
- **Precision**: among examples predicted as a category, how many truly belong to it. Macro precision averages categories equally.
- **Recall**: among examples truly in a category, how many are found. Macro recall averages categories equally.
- **F1-score**: harmonic mean of precision and recall; macro F1 averages each category's score equally.
- **Confusion matrix**: counts of actual vs. predicted categories, with row/column labels.

The current Python environment successfully imports `pyarrow.lib`, SciPy, scikit-learn, and Pandas. Classifier training completed without changing or bypassing Windows security settings. The held-out metrics are recorded above and in `data/models/ticket_category_metrics.json`.

The dashboard uses native ticket cards and Plotly Graph Objects charts; chart rendering does not require a Pandas dataframe. Ticket filtering, status updates, metrics, and charts were validated with empty and populated temporary databases.

Final QA measurements on this small local corpus: live Streamlit HTTP 200 in 2.21 seconds after disabling telemetry; temporary index build in 0.071 seconds; 50 warm retrievals had 0.053 ms median and 0.101 ms p95; one local Qwen answer took 2.62 seconds. The index used 88,032 bytes for its dense matrix and 121,953 bytes on disk. These are single-run measurements, not service-level guarantees. The full Mack source is not included, so large-corpus scaling is not measured.

## Limitations and future scope

- The knowledge base has sample documents only; official institutional procedures must be supplied and approved by the university.
- The classifier has five project-labeled classes and only 140 examples; its metrics may not generalize to real helpdesk tickets.
- Local model output may still be imperfect; evidence checks, citations, and ticket escalation reduce but do not eliminate risk.
- No ticket priority/severity or assignment workflow exists.
- There is no external helpdesk integration or institutional IT-team dispatch; the admin queue is local to this application database.
- Guided troubleshooting is deterministic sample guidance, not an adaptive diagnostic system or official university procedure.
- Resolution and context metrics are user-reported, not independently verified service outcomes.
- Local accounts do not include email verification, password reset, login rate limiting, or organization identity-provider integration.
- Future improvements include approved university documents, independently reviewed and expanded ticket labels, evaluation on unseen real tickets, privacy/retention controls, and staff assignment/priority management.

## Common viva questions

**Q: Why use RAG instead of asking the LLM from memory?**

A: Retrieval supplies current local passages and source metadata. The answer can be grounded in and cited to those passages; if evidence is missing, the system can refuse and offer a ticket.

**Q: What does the retrieval threshold mean?**

A: It is a minimum cosine similarity for accepting a retrieved chunk. It is not a probability. The current value is `0.28`; it should be retuned only against relevant evaluation cases if the knowledge base changes.

**Q: Why use TF-IDF?**

A: It weights terms by their usefulness across the corpus: a term frequent in one document but uncommon across documents receives more weight. The manual implementation exposes and demonstrates this calculation.

**Q: Why use cosine similarity?**

A: It compares the direction of normalized TF-IDF vectors and is insensitive to the raw length of a document vector.

**Q: What is the difference between retrieval and classification?**

A: Retrieval finds relevant passages from documents. Classification predicts a fixed category label for a ticket. They are separate components and use separate vectorizers.

**Q: Why Logistic Regression for ticket categories?**

A: It is a standard supervised text-classification baseline for sparse TF-IDF features, supports multiclass prediction, and provides class probabilities for an editable suggestion. The grouped holdout achieved 0.974 accuracy, but the small project-labeled data is not enough to claim production performance.

**Q: Has the classifier been trained?**

A: Yes. The model was trained on 140 project-labeled issue descriptions and verified after saving/reloading. Its 38-record grouped holdout achieved accuracy 0.974, macro precision 0.978, macro recall 0.960, and macro F1 0.966. Mack did not provide the labels, and manual category selection is still supported.

**Q: Was Qwen3 trained by this project?**

A: No. The project runs the existing Qwen3 1.7B model locally through Ollama for inference only.

**Q: How does the system respond when it cannot find evidence?**

A: It does not present unsupported content as an answer. It returns an unsupported/error status and offers a support ticket.

**Q: Are the included troubleshooting steps official university instructions?**

A: No. External dataset records and demonstration guides are explicitly marked sample/not official. Only approved institutional documents should be labeled verified.

**Q: What does the confusion matrix show?**

A: It displays the number of examples for each actual class against each predicted class, making class-specific errors visible.

**Q: What is data leakage and how is it reduced here?**

A: Leakage occurs when highly similar examples appear in both train and test splits, making evaluation overly optimistic. Exact duplicates are rejected, and near-duplicate descriptions are grouped before a stratified group split.

**Q: Which ticket fields are stored?**

A: Requester name/contact, category, issue description, conversation link if available, status, and timestamps. Priority and staff assignment are not implemented.
