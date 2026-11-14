# IntelliDesk Final Submission Checklist

## Project files and component roles

- [ ] `app.py` — Streamlit chat, conversation history, source references, and escalation flow.
- [ ] `src/` — document loading/chunking, manual NumPy TF-IDF and cosine similarity, Ollama client, SQLite access, ticket operations, and shared UI helpers.
- [ ] `pages/1_Admin_Dashboard.py` — ticket statistics, recent requests, filters, status updates, and charts.
- [ ] `pages/2_My_Tickets.py` — manual ticket submission, category selection, ticket details, search, and status/category filters.
- [ ] `pages/3_Knowledge_Base.py` — searchable supported source documents with sample/verified labels.
- [ ] `pages/4_Settings.py` — local model state and architecture information.
- [ ] `pages/5_Guided_Troubleshooting.py` — deterministic sample-only workflows, explicit outcome feedback, and local-ticket escalation with wizard context.
- [ ] `src/auth.py`, `create_admin.py`, and `src/ui.py` — local user authentication and separately provisioned administrator access.
- [ ] `src/troubleshooting.py` — guided steps grounded in sample knowledge-base files.
- [ ] `evaluation/` — local RAG cases and separate TechQA retrieval/refusal evaluation data.
- [ ] `data/THIRD_PARTY_NOTICES.md` — dataset attribution and license notes.
- [ ] `tests/test_accounts_and_context.py` — account isolation, migration, and outcome-statistics checks.
- [ ] `tests/test_auth_ui.py`, `tests/test_guided_workflow_ui.py`, and `tests/test_ticket_category_ui.py` — authentication, guided escalation, and category-correction AppTests.
- [ ] `docs/ARCHITECTURE.md`, `docs/PROJECT_VIVA.md`, `docs/DEMO_GUIDE.md`, `docs/PROJECT_PRESENTATION.md`, and this checklist.
- [x] `src/classifier.py`, `src/dataset_processor.py`, and `train_classifier.py` — separate supervised classifier; trained and evaluated.

## Dependencies and setup

- [ ] Use the project virtual environment and pinned packages from `requirements.txt`.
- [ ] Python 3.13 was used for the current validation.
- [ ] Ollama must be running locally with `qwen3:1.7b` available for generated answers.
- [ ] The RAG search index must exist under `data/index/`. Build it only if missing or intentionally updating knowledge documents.

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" list
if (-not (Test-Path .\data\index\chunks.json)) { .\venv\Scripts\python.exe build_index.py }
.\venv\Scripts\python.exe create_admin.py
.\venv\Scripts\python.exe -m streamlit run app.py
```

Provision the administrator once in a trusted terminal; do not share the password. Standard demo users register from the sign-in screen. The admin setup command can be skipped if a local admin account already exists.

## Data attribution and trust boundaries

- [ ] Mack IT Support v1 is attributed under MIT. Included troubleshooting records are sample information, not institutional procedures.
- [ ] TechQA-RAG-Eval is attributed under Apache-2.0 and used for evaluation only; it is not inserted into the application index.
- [ ] UmerSajid/IT-Troubleshooting-Dataset was excluded because no license was declared.
- [ ] The verified knowledge-base folder is currently empty. Do not describe sample documents as verified university policy.
- [ ] The 140 classifier examples have project-assigned labels; Mack did not provide these category labels.
- [ ] Use synthetic contact details for public demonstrations. Users see only their own account's tickets/conversations; administrator accounts can see the shared local IT queue.
- [ ] Chat-to-ticket escalation attaches a recent transcript and source metadata by default, but users may opt out. Guided-ticket context records completed sample steps.
- [ ] The admin queue is local to this SQLite database; no external helpdesk dispatch is configured.

## Test evidence from final integration QA

- [x] All six Streamlit pages rendered through AppTest; the admin queue rejects regular-user access.
- [x] Chat was exercised through the actual local index and Ollama/Qwen3; the supported Wi-Fi query returned `answered` with `wifi_troubleshooting_sample.txt` cited.
- [x] Unsupported-response escalation, manual category selection, ticket submission/persistence, dashboard statistics/charts/status updates, new chat, history restore, and unavailable-Ollama handling passed isolated AppTests.
- [x] Trained-category suggestion, manual correction, corrected ticket persistence, unseen-example predictions, and Settings/About trained state passed AppTests.
- [x] Responsive browser inspection at 1440, 1024, 768, and 390 CSS pixels found no horizontal overflow. Dashboard KPI cards used one row at desktop/laptop, two rows at tablet, and stacked at mobile.
- [x] RAG evaluation: 14/14 local retrieval/refusal, 12/12 TechQA supporting-source hits at hit@3, 8/8 impossible-question rejection, and 14/14 local Qwen status/ticket-offer cases.
- [x] Dashboard regression after removing the Pandas-dependent chart path: empty-state AppTest passed; populated SQLite AppTest showed correct KPIs and all three Plotly graph-object charts.
- [x] Classifier training: 140 records; grouped holdout 102/38; artifact reload/prediction check passed; held-out metrics and confusion matrix saved locally.
- [x] Python compilation, `pip check`, and `git diff --check` passed.
- [x] SQLite database and ticket manager self-checks use temporary databases and do not require deleting the existing database.
- [x] Focused account/context tests pass: account authentication, owner-only conversation/ticket access, rejection of cross-account conversation linking, explicit answer/guided/context feedback aggregation, and idempotent migration that preserves unowned legacy records.
- [x] Streamlit AppTests pass for sign-up/sign-in/sign-out, sample-guided resolved/unresolved paths, context-bearing local-ticket submission, user/admin page authorization, ticket listing, and predicted-category correction persistence.
- [ ] Screenshots are retained locally but excluded from the initial GitHub push because they are cropped and one still shows the pre-authentication ticket screen. Recapture the pages at presentation size before adding screenshots to the repository.

## Launch and live demonstration

1. Start IntelliDesk and register a regular demonstration account; use the pre-provisioned admin account only for the admin demo.
2. Show the authenticated welcome screen and workspace navigation.
3. Ask: “My Wi-Fi is connected but there is no internet.”
4. Explain the retrieved sample guide and show the **Sample · not official** source label.
5. Ask for the official campus Wi-Fi password; show the evidence-based refusal and ticket offer.
6. Submit a support ticket with synthetic contact details, review/adjust its category, and demonstrate the conversation-context opt-out.
7. Open **My Tickets** as the user; show only that account's ticket and its attached context.
8. Use **Guided troubleshooting** to report a sample step resolved the issue or continue to local ticket escalation with the completed steps attached.
9. Sign in as administrator and open the local **IT ticket queue**. Show KPIs, filters, status workflow, charts, and feedback-based metrics.
10. Open **Knowledge Base** and **Settings & About**; explain sample/verified boundaries and the local model/retriever.
11. Explain the separation: NumPy RAG retrieves, the separately trained Scikit-learn model suggests editable ticket categories, and local Qwen3 generates grounded answers.

## Classifier status and model evidence

- [x] The current environment imports PyArrow, SciPy, scikit-learn, and Pandas successfully; no Windows security settings were modified or bypassed.
- [x] Training generated the model artifact and metrics: accuracy 0.974, macro precision 0.978, macro recall 0.960, macro F1 0.966; 38 held-out records.
- [x] Manual category selection and correction remain available alongside editable classifier suggestions.
- [ ] Before submission, copy generated local model/metrics to another environment only through the institution's approved process; both artifacts are ignored by Git.

```powershell
.\venv\Scripts\python.exe train_classifier.py
```

## Known limitations

- [ ] Classifier metrics are based on one small grouped holdout from project-assigned labels and do not establish production accuracy.
- [ ] The verified institutional knowledge folder is empty; external and sample content is not university policy.
- [ ] Tickets have no priority/severity or staff assignment.
- [ ] There is no external ITSM/helpdesk dispatch; tickets remain in the local admin queue.
- [ ] Guided troubleshooting is fixed sample guidance, not an adaptive diagnostic system or official procedure.
- [ ] Resolution and context metrics are user-reported, not independently verified service outcomes.
- [ ] Local accounts do not include email verification, password reset, login rate limiting, or organization identity-provider integration.
- [ ] Legacy records with no owner remain unassigned; they are not automatically exposed as a new user's records.
- [ ] Large-corpus index size and retrieval performance have not been benchmarked; the dense NumPy index is intended for the included small demonstration corpus.
- [ ] Ollama must be available locally for generated answers. When it is not, the UI reports the error and offers ticket escalation.

## Final handoff

- [ ] Confirm the branch is `feature/rag-core`.
- [ ] Review all modified and untracked files before submission.
- [ ] Keep `.env`, the virtual environment, generated index, SQLite database, and model artifacts out of Git.
- [ ] Do not commit or push without explicit authorization.
