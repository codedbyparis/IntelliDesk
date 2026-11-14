# IntelliDesk Demonstration Guide

## Before the demonstration

From PowerShell in the repository root:

```powershell
.\venv\Scripts\Activate.ps1
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" list
if (-not (Test-Path .\data\index\chunks.json)) { python build_index.py }
streamlit run app.py
```

Confirm `qwen3:1.7b` appears in the Ollama model list. The guarded index command only builds a missing index; `python build_index.py` overwrites the generated index, so do not run it when an index already exists unless intentionally rebuilding. The running application uses only the local Ollama API; it does not call a cloud LLM.

Provision an administrator before the demo if you need to show the IT queue:

```powershell
.\venv\Scripts\python.exe create_admin.py
```

Use the sign-in screen to create a regular demo account. Administrator accounts are not self-registered. Use synthetic contact details and demonstration data.

The supervised ticket classifier has been trained and evaluated. Its locally saved category prediction is a suggestion, and the requester can correct it before submission. Metrics are based on 140 project-labeled examples and a 38-record grouped holdout; present them as a small-dataset demonstration, not production performance.

## Demonstration script

### 1. Start the application

Open the Streamlit URL shown in PowerShell, usually `http://localhost:8501`. Show the IntelliDesk chat page and the sidebar's workspace navigation and recent conversations. If the index or Ollama is unavailable, the UI reports that local setup issue and does not fall back to a hosted model.

### 2. Ask a supported technical question

Enter:

> My Wi-Fi is connected but there is no internet. What should I check?

The answer should draw from the sample Wi-Fi guide. Point out the **Sample · not official** citation and explain that the source is demonstration content, not verified university policy.

### 3. View retrieved sources and conversation history

Expand or inspect the source captions under the assistant response. Show the source filename and sample label. Start **＋ New chat**, then return to the previous conversation from the sidebar to demonstrate persistence.

### 4. Ask an unsupported question

Enter:

> What is the official campus Wi-Fi password?

The knowledge base does not contain an approved password. IntelliDesk should not invent one; it should return an unsupported response and offer ticket escalation. Explain that the sample corpus contains no verified university procedures.

### 5. Demonstrate guided troubleshooting and create a support ticket

Open **Guided troubleshooting**, select an issue such as Wi-Fi, and continue through the sample steps. Select **This resolved my issue** to submit an explicit positive outcome, or complete the steps and select **Still not resolved — create a ticket**. The steps and source filename are labeled sample/not official. If submitting, complete the contact form and show that the workflow context is attached to the local ticket.

Alternatively, after an unanswered chat response, use the offered ticket form. The recent transcript and sources are attached by default; demonstrate that the requester can clear the checkbox to opt out.

Use the **My Tickets** page to submit a standalone support request, or use the ticket form offered after an unanswered chat response. In either form:

1. Enter a demonstration requester name and contact address/number.
2. Keep the issue description or edit it to clarify the problem.
3. Review the predicted category and model probability. The category selector defaults to that suggestion, but can be changed to any configured category.
4. Submit the ticket and show the ticket confirmation.

Use synthetic demonstration contact details; do not enter real personal data during a public demo.

### 6. Correct the ticket category

The category field is editable. Use an issue that produces a prediction, then choose a different category before submitting to demonstrate the correction path. Explain that the suggestion comes from a small project-labeled training set.

### 7. View tickets and administrator queue

Use **My Tickets** to show the signed-in user's ticket, status, search, and filters. If the ticket has attached context, show the transcript and its sample source citation and optionally report whether it helped. Sign in with the separately provisioned administrator account and open **Dashboard**. Show the local IT queue, total/open/in-progress/resolved metrics, filters, charts, and user-reported outcome counts. Explain that this queue does not dispatch tickets to an external helpdesk and the feedback metrics are not verified IT resolution rates.

### 8. Browse project information

Open **Knowledge Base** and show the sample/verified labels. Point out that the generated search index is not exposed as a user document and that sample content is not official university policy. Open **Settings & About** to show Qwen3/Ollama, the manual NumPy retrieval approach, and the classifier availability state.

## Points to emphasize

- RAG retrieval, ticket classification, and LLM generation are distinct components.
- The RAG retriever is custom NumPy TF-IDF and cosine similarity; the classifier does not replace it.
- Qwen3 runs locally through Ollama and was not trained by this project.
- Citations distinguish sample data from verified documents. No verified university policy documents are currently indexed.
- The classifier was trained with project-assigned labels that do not come from Mack's original dataset. Its small holdout score is not a production accuracy guarantee; manual category selection remains available.
- Standard accounts are self-registered; admin accounts are provisioned with `create_admin.py`. Ticket and conversation visibility is scoped to the signed-in account; admins can view the local shared queue.
- Guided troubleshooting and its source documents are samples, not official university IT procedures.
- Chat context can be attached to a ticket by default, but users can opt out. No external ITSM integration is configured.
