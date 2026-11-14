# IntelliDesk

An AI-powered IT Helpdesk and Technical Support chatbot using a manually implemented RAG pipeline and a local LLM for intelligent, context-aware responses.

IntelliDesk is a Streamlit demonstration application for finding support information, citing its source, and escalating unanswered issues as SQLite tickets. Sample and third-party material is clearly distinguished from verified university procedures.

## Problem statement and objectives

IT helpdesk users often need a quick answer, a trustworthy source, and a way to escalate problems that cannot be resolved from available documentation. IntelliDesk demonstrates a local, source-attributed support workflow while clearly separating sample information from approved university policy.

Project objectives:

1. Retrieve relevant local support passages with a transparent, manually implemented RAG pipeline.
2. Generate answers only from retrieved context using a locally hosted language model.
3. Retain conversation history and provide citations and an unanswered-question ticket path.
4. Provide a separate supervised ticket-category classifier, without coupling it to RAG retrieval.
5. Demonstrate ticket tracking and basic administrator reporting without representing sample documents as official procedures.

## Features

- Search local PDF, TXT, and normalized JSONL knowledge-base documents.
- Manual word-based chunking, NumPy TF-IDF, cosine similarity, and a configurable relevance threshold.
- Editable supervised ticket-category suggestions, with manual category selection retained.
- Local answer generation using Qwen3 1.7B through Ollama; no cloud LLM API.
- Source citations marked **Sample · not official** or **Verified**.
- Persistent conversations, messages, source metadata, and support tickets in SQLite.
- Local user registration and sign-in; user conversations and tickets are scoped to that account, with separately provisioned administrator access.
- Sample-labeled guided troubleshooting workflows with explicit resolution feedback and optional escalation to the local IT queue.
- Chat-to-ticket escalation can attach a recent conversation snapshot and its sources; the requester can opt out.
- Responsive multi-page shell with chat history, ticket tracking/submission, knowledge documents, guided troubleshooting, and settings/about.
- Ticket search and status/category filters; the admin dashboard adds KPI cards, status updates, and charts.
- Dashboard outcome metrics use explicit user-reported feedback and identify their response counts; ticket handling remains local, with no external helpdesk integration.
- The knowledge-base page lists only supported source documents, with sample/verified labels; generated index files remain internal.
- Separate retrieval fixtures for local helpdesk cases and TechQA supporting passages.

## Architecture

```text
Knowledge-base documents -> loader -> cleaner -> chunker
                                              |
                         manual NumPy TF-IDF + cosine similarity
                                              |
                                         local RAG index
                                              |
Chat question -> Streamlit -> RAG pipeline -> retrieved context -> local Ollama / Qwen3

Ticket issue -> Streamlit -> manual category selection -> ticket manager -> SQLite
                         \-> optional trained TF-IDF + Logistic Regression suggestion
                             (trained suggestion remains editable)
```

The RAG retriever remains manually implemented with NumPy TF-IDF and cosine similarity. Scikit-learn is used only for the independent ticket-category classifier; it does not replace or feed the RAG retrieval index. The checked-in training data has been used to train and evaluate a separate local classifier. Its predictions are editable suggestions, and manual category selection remains available. Qwen3 is used only for grounded answer generation through local Ollama. The application does not use LangChain, LlamaIndex, ChromaDB, Gemini, OpenAI, or cloud model APIs.

The initial relevance threshold is `0.28`, selected between the measured lowest in-scope score (`0.326`) and highest out-of-scope score (`0.225`) in the included tuning/evaluation questions. Re-run the retrieval tuning report after changing the knowledge base.

See the [architecture document](./docs/ARCHITECTURE.md) for module responsibilities, data flows, runtime boundaries, and measured scale.

## Technology stack

- Python 3.13, Streamlit, SQLite, NumPy, PyMuPDF, Requests, Pandas, and Plotly.
- Manual RAG retrieval: text cleaning/tokenization, word-based chunking, a custom TF-IDF vectorizer, cosine similarity, and a configurable similarity threshold.
- Separate trained classifier: Scikit-learn `TfidfVectorizer` and `LogisticRegression`, with Joblib persistence.
- Local generation: Qwen3 1.7B through the Ollama HTTP API.

### Manual RAG implementation

Knowledge-base documents are loaded with provenance and a `sample` or `verified` label, cleaned, and divided into overlapping word chunks. IntelliDesk builds its own vocabulary and TF-IDF matrix with NumPy, transforms the query using that same vocabulary, computes cosine similarity against indexed chunks, and returns top results only when they meet the configured threshold. Retrieved passages and source metadata are provided to Qwen3; the response is refused/escalated when evidence is insufficient. The classifier's Scikit-learn vectorizer is a separate model and is never used by the retriever.

### Supervised ticket classifier

The training data contains 140 Mack IT Support issue descriptions with project-assigned labels in five categories; Mack does not supply ticket-category labels. Exact duplicates are rejected, and near-duplicates with character-sequence similarity of at least `0.85` are grouped to prevent leakage across the stratified four-fold split. Training uses Scikit-learn TF-IDF with unigrams/bigrams and balanced Logistic Regression. The selected grouped holdout contained 102 training and 38 test records. Measured held-out results: accuracy `0.974`, macro precision `0.978`, macro recall `0.960`, and macro F1 `0.966`. The confusion matrix and metrics are saved under `data/models/`; the training command reloads the model and verifies prediction and saved metrics. These results describe a small, project-labeled sample, not expected production accuracy.

The app loads a classifier only when it needs to render the ticket category suggestion. If the artifact is missing or its required imports cannot load, users can still submit a ticket using manual category selection; there is no classifier dependency in app startup, chat, or RAG retrieval.

## Datasets and attribution

External records are labeled **sample** and must not be presented as official LPU or university policy.

- **Mack IT Support Dataset v1**: [Hugging Face dataset](https://huggingface.co/datasets/benjaminmacklin/IT_Support), MIT license. The repository has seven JSONL files; `B_troubleshooting.jsonl` has `instruction` and `output` fields and 19,610 records, including 1,450 exact duplicate question/answer pairs in the inspected snapshot. IntelliDesk includes 16 selected, non-empty records, identified by source-file line number, in `data/knowledge_base/sample/mack_support_subset.jsonl`.
- The classifier training data contains 140 distinct Mack issue descriptions in `data/training/mack_ticket_categories.jsonl` (28 each for Wi-Fi, University Email, Computer Lab, Software Installation, and Account Security). Mack does not provide ticket-category labels: these labels were assigned for this project by manual review of each issue description and are not represented as original dataset annotations. Labels outside those five classes remain available for the user to select in the ticket form.
- **Mack IT Support Dataset V2**: [Hugging Face dataset](https://huggingface.co/datasets/benjaminmacklin/IT_Support_V2), MIT license. Its card describes 100,000+ synthetic conversations; the repository contains a 27 MB JSONL and a 9.4 MB Parquet file. V1 was selected for its smaller troubleshooting subset and more directly usable `instruction`/`output` records.
- **TechQA-RAG-Eval**: [NVIDIA dataset](https://huggingface.co/datasets/nvidia/TechQA-RAG-Eval), Apache-2.0. The inspected `train.json` contains 910 rows (the card says 908), including 300 impossible questions, 610 rows with contexts, and 20 duplicate questions. The checked-in evaluation fixtures use `id`, `question`, `answer`, `contexts`, and `is_impossible` for TechQA; the separate local fixtures use `id`, `question`, `expected_source`, `expected_status`, and `expected_ticket`. A subset of 12 answerable and 8 impossible examples is kept in `evaluation/test_questions.json`. These questions, answers, and passages are evaluation-only and are never added to the application index.
- **UmerSajid IT Troubleshooting Dataset**: [Hugging Face dataset](https://huggingface.co/datasets/UmerSajid/IT-Troubleshooting-Dataset). It was inspected but excluded because its dataset card and README do not declare a license.

See [data/THIRD_PARTY_NOTICES.md](./data/THIRD_PARTY_NOTICES.md) for notices. The `verified` knowledge-base folder is reserved for genuinely approved university documents; external dataset records and the included demonstration guides are not verified.

### Dataset quality and evaluation isolation

The checked-in classifier subset has 140 non-empty issue descriptions, five labels with 28 records each, complete Mack source/license/line attribution, and no exact normalized duplicate questions. Each training JSONL row contains `question`, `category`, `source_dataset`, `source_url`, `source_file`, `source_line`, `license`, and `labeling_note`. Similarity groups are reserved for leakage-safe splitting. TechQA examples are held only in evaluation fixtures and are not indexed; the application index contains sample knowledge-base documents only. The Mack source itself includes exact duplicate Q/A pairs, so only a selected subset was used. UmerSajid records remain excluded because no license was declared. All third-party troubleshooting guidance is sample information, not LPU/university policy.

## Requirements

- Windows, macOS, or Linux.
- Python 3.13 (the pinned versions in `requirements.txt` were tested on Python 3.13).
- Scikit-learn and Joblib for training and loading the separate ticket classifier.
- [Ollama](https://ollama.com/download) with the local `qwen3:1.7b` model for generated answers.

## Setup on Windows PowerShell

Run these commands from the IntelliDesk project folder:

```powershell
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
ollama pull qwen3:1.7b
```

If `ollama` is not recognized in the current PowerShell session, use the per-user executable directly:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull qwen3:1.7b
```

If PowerShell prevents script activation, use the environment's interpreter directly:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Ollama and Qwen3 run locally. IntelliDesk does not fall back to a hosted model.
Streamlit usage-statistics collection is disabled in `.streamlit/config.toml`; the application's only runtime model API is the local Ollama endpoint.

## Build and run

From the project root, activate `venv` and run:

```powershell
if (-not (Test-Path .\data\index\chunks.json)) { python build_index.py }
streamlit run app.py
```

`python build_index.py` creates or overwrites the generated index under `data/index/` (ignored by Git). Run it only when the index is missing or after intentionally changing knowledge-base documents; do not run it just to start the application. The admin dashboard is available from Streamlit's page navigation as **IntelliDesk Admin Dashboard**.

The app initializes the SQLite database automatically at `data/intellidesk.db`. If the index or Ollama is unavailable, the interface reports the issue and offers ticket escalation.

The locally trained classifier artifact is written to `data/models/ticket_category_classifier.joblib` and ignored by Git. In ticket escalation, a model prediction is only a suggestion and the requester can change it before submission.

## Accounts, privacy, and ticket queue

Users can register a local account from the sign-in screen. Administrator privileges cannot be self-registered; provision an administrator from a trusted project terminal:

```powershell
.\venv\Scripts\python.exe create_admin.py
```

The script prompts for an admin username and password and does not provide a default credential. Conversations and tickets created after login are scoped to their owner. Administrators can review and update tickets in the in-app local queue. Existing records from before account ownership was added remain unassigned; they are not automatically attached to a new account.

When a user escalates a chat issue, the recent transcript and source references are attached by default, with a checkbox to opt out. Guided troubleshooting uses deterministic steps from the existing sample documents and shows that they are not official university procedures. Neither workflow dispatches tickets to an external ITSM/helpdesk system. Dashboard resolution and context metrics count only explicit user feedback and ticket records; they do not measure independently verified IT resolution quality.

## Ticket classifier status and training

Classifier training and held-out evaluation have completed in the current Python environment. The app loads the local artifact lazily for ticket suggestions; it does not require the artifact for startup, RAG retrieval, or manual category selection. Category predictions remain editable and users can select any configured category.

The latest classifier dependency probe successfully imported `pyarrow.lib`, SciPy, scikit-learn, and Pandas. No Windows security settings were modified or bypassed. If a future environment blocks a required dependency, keep manual category selection and ask an authorized administrator to review the relevant Application Control event or provide an approved environment.

The training command can be rerun after intentionally changing the labeled dataset:

```powershell
.\venv\Scripts\python.exe train_classifier.py
```

The workflow creates a stratified, near-duplicate-grouped holdout, reports accuracy, macro precision/recall/F1 and a confusion matrix, trains on all labeled records, and saves the model and evaluation JSON under `data/models/`. It reloads the model and checks prediction and saved metrics. The model and metrics are generated local artifacts and are excluded from Git.

## Evaluation and self-checks

Ensure the existing index is present; build it only if missing or intentionally updating it. Then run:

```powershell
python -m src.config
python -m src.document_loader
python -m src.chunker
python -m src.text_cleaner
python -m src.tfidf_vectorizer
python -m src.similarity
python -m src.index_store
python -m src.database
python -m src.ticket_manager
python -m src.auth
python -m src.prompt_builder
python -m src.llm_client
python -m src.retriever
python -m src.rag_pipeline
python -m evaluation.run_evaluation
python -m unittest discover -s tests -v
```

The database and index-store self-checks use temporary files. Retrieval and RAG checks require the generated index; answer-generation checks also require Ollama and Qwen3. The evaluation runner reports local expected-source/refusal results and a separate TechQA context source hit rate, and skips model-dependent answer evaluation when the local model is unavailable. The trained classifier's saved metrics are summarized above.

The evaluation runner checks source retrieval/refusal against 14 local cases, manual retrieval over 12 answerable TechQA contexts, and rejection of 8 impossible TechQA questions against the application index. The latest run in this development phase passed 14/14 local cases, 12/12 TechQA context source hits at `hit@3`, 8/8 impossible questions, and 14/14 local Qwen answer-status checks (9 answered, 3 not found, 2 out of scope). A complete isolated Streamlit journey also passed through chat, refusal, corrected ticket submission, app restart/history restore, and dashboard filtering.

On the current Windows/Python 3.13 environment, a temporary build of the 24-document sample knowledge base (28 chunks, 393-word vocabulary) took 0.071 seconds. The generated index occupied 121,953 bytes, including an 88,032-byte dense NumPy matrix. Across 50 warm queries, retrieval median was 0.053 ms and p95 was 0.101 ms. After disabling Streamlit telemetry, a live server returned HTTP 200 in 2.21 seconds; one local Qwen answer took 2.62 seconds. These are single-run local measurements, not performance guarantees. The traced Python allocation peak during index building was 435,639 bytes and excludes NumPy native buffers. The full 19,610-row Mack source is not checked in, so large-corpus scaling has not been benchmarked; the dense TF-IDF matrix is intended for this small demonstration corpus.

## Project structure

```text
IntelliDesk/
├── .streamlit/
│   └── config.toml
├── app.py
├── build_index.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PROJECT_VIVA.md
│   ├── DEMO_GUIDE.md
│   ├── PROJECT_PRESENTATION.md
│   └── FINAL_SUBMISSION_CHECKLIST.md
├── pages/
│   ├── 1_Admin_Dashboard.py
│   ├── 2_My_Tickets.py
│   ├── 3_Knowledge_Base.py
│   ├── 4_Settings.py
│   └── 5_Guided_Troubleshooting.py
├── create_admin.py
├── train_classifier.py
├── src/
│   ├── config.py
│   ├── auth.py
│   ├── dataset_processor.py
│   ├── classifier.py
│   ├── document_loader.py
│   ├── chunker.py
│   ├── text_cleaner.py
│   ├── tfidf_vectorizer.py
│   ├── similarity.py
│   ├── index_store.py
│   ├── retriever.py
│   ├── prompt_builder.py
│   ├── llm_client.py
│   ├── rag_pipeline.py
│   ├── database.py
│   ├── ticket_manager.py
│   ├── troubleshooting.py
│   └── ui.py
├── data/
│   ├── knowledge_base/
│   │   ├── sample/
│   │   └── verified/
│   ├── training/
│   └── THIRD_PARTY_NOTICES.md
├── evaluation/
    ├── run_evaluation.py
    └── test_questions.json
└── tests/
    ├── test_accounts_and_context.py
    ├── test_auth_ui.py
    ├── test_guided_workflow_ui.py
    └── test_ticket_category_ui.py
```

Generated index files, SQLite databases, virtual environments, and local secrets are excluded by `.gitignore`.

## Limitations and future improvements

- Classifier results come from a small project-labeled dataset and a single grouped holdout; they do not establish production accuracy or generalization. Manual category selection remains available.
- The classifier labels are project-assigned and the data is small, balanced, and limited to five of the application's eight ticket categories. Results will not establish production performance.
- The knowledge base contains sample guides and selected third-party records; it has no verified university policy documents. Always verify institutional procedures with an authorized source.
- Qwen3 runs locally and may still produce errors or unsupported content; the RAG pipeline uses evidence checks, source attribution, and refusal/ticket escalation.
- Guided troubleshooting is a fixed sample workflow, not an adaptive diagnostic system or official institutional procedure.
- Tickets are stored in the local SQLite queue; there is no external helpdesk dispatch, staff assignment, priority/severity, or service-level workflow.
- Outcome rates are self-reported feedback, not verified resolution rates or escalation-quality measurements.
- Local accounts do not include email verification, password reset, login rate limiting, or organization identity-provider integration; protect the machine and local database appropriately.
- Future work may include administrator-approved institutional documents, expanded and reviewed labels, classifier validation on independently collected tickets, stronger account recovery/privacy controls, and helpdesk assignment/integration.

## Credits

IntelliDesk is developed by the project team. No individual team-member names were present in the repository, so none are inferred. Dataset creators and license details are listed above and in the third-party notices.

Project handoff documents: [viva guide](./docs/PROJECT_VIVA.md), [demo guide](./docs/DEMO_GUIDE.md), and [presentation outline](./docs/PROJECT_PRESENTATION.md).
