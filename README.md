# uniagent

UniAgent is an academic co-pilot that answers questions about university syllabi,
reference textbooks, and schedules using Retrieval-Augmented Generation (RAG).

The repository is split into two parts:

- `app.py` — the original Streamlit chat UI (direct Google Gemini integration).
- `backend/` — the RAG backend: PDF ingestion, document store, TF-IDF retrieval,
  the Gemini agent, and a conversation-state manager.

This README documents the `backend/` package and how to test it end to end.

---

## Repository layout

```
uniagent/
├── app.py                     # Streamlit chat UI (standalone)
├── requirements.txt           # Runtime dependencies for the streamlit app
├── data/                      # Sample documents (e.g. a C++ textbook PDF)
├── backend/                   # RAG backend package
│   ├── config.py              # Central configuration from env vars / .env
│   ├── models.py              # Dataclasses: Document, PageMetadata, SourceInfo, AgentResponse
│   ├── exceptions.py          # BackendError hierarchy
│   ├── document_processor.py  # PDF -> Document (pypdf)
│   ├── document_store.py      # In-memory store + JSON persistence
│   ├── retriever.py           # TF-IDF index and relevance retrieval (scikit-learn)
│   ├── agent.py               # Retrieval-augmented Gemini agent
│   ├── conversation.py        # Conversation state + ConversationManager
│   └── scratch/               # Helper scripts (sample PDF generator)
└── tests/                     # Unit tests + end-to-end smoke test
    ├── conftest.py            # Shared fixtures
    ├── test_*.py              # Unit tests
    └── e2e_sample_pdf.py      # End-to-end pipeline test
```

---

## Pipeline

The core flow is:

```
PDF → process_document() → Document → add_document() → document_store
                                                          │
Question ──→ Conversation.ask() ──→ ask_agent()          │
                                       │                  ▼
                                       │          retriever.retrieve()
                                       │          (TF-IDF cosine similarity)
                                       ▼                  │
                              Document snippets ──→ prompt
                                       │                  │
                                       ▼                  ▼
                              Gemini API ──→ AgentResponse(answer, sources, grounded)
                                       │
                                       ▼
                    reply stored in Conversation history
```

### Stage by stage

1. **Ingestion** — `process_document()` (`backend/document_processor.py`) reads a PDF
   with `pypdf`, producing a `Document` with one `PageMetadata` per page.
2. **Storage** — `add_document()` (`backend/document_store.py`) keeps documents in a
   module-level dict and persists them to a JSON file (`Config.STORE_PATH`) on every
   change. Call `load_documents()` once at startup to restore the persisted store.
3. **Indexing** — on first query, `retriever.py` lazily builds a TF-IDF matrix
   (English stop words removed) from all stored documents and answers a query by
   cosine similarity, returning `(Document, score)` pairs ordered best-first.
4. **Answering** — `ask_agent()` (`backend/agent.py`) sends the top documents'
   text (first 2000 chars each) plus the question to Gemini and returns an
   `AgentResponse`:
   - `answer` — the model text (stripped)
   - `sources` — document titles and page numbers
   - `grounded` — `False` when the answer contains "information not found"

   If no documents are retrieved, the agent returns the "Information not found."
   guardrail without calling the API.

---

## Requirements

Python 3.10+ (developed on 3.12).

**Runtime**

The `backend/` pipeline needs:

- `pypdf` — PDF extraction
- `scikit-learn` — TF-IDF retrieval
- `google-generativeai` — Gemini API
- `python-dotenv` — `.env` loading

**Tests**

- `pytest`
- `reportlab` (used in fixtures to generate tiny PDFs with known text)

---

## Configuration

Create a `.env` file in this directory (repo root) or export environment variables.
`backend/config.py` loads `.env` automatically.

| Variable                | Default                          | Purpose                                    |
| ----------------------- | -------------------------------- | ------------------------------------------ |
| `GEMINI_API_KEY`        | *(required for the LLM step)*    | Google Gemini API key                      |
| `GEMINI_MODEL`          | `gemini-1.5-flash`               | Model name used by the agent               |
| `SYSTEM_PROMPT`         | built-in "answer from context"   | System prompt for the agent                |
| `DOCUMENT_STORE_PATH`   | `document_store.json`            | Where the store persists                   |
| `RETRIEVAL_TOP_K`       | `5`                              | Default number of documents retrieved      |
| `CONFIDENCE_THRESHOLD`  | `0.7`                            | (Reserved) guardrail threshold             |

`Config.validate()` raises if `GEMINI_API_KEY` is missing.

---

## Using the conversation-state manager

`backend/conversation.py` exposes two classes:

### `Conversation`

Wraps a single conversation's message history and drives the agent.

```python
from backend.conversation import Conversation

conversation = Conversation()                  # auto-generates a UUID id
conversation.add_user_message("hello")
conversation.add_assistant_message("hi there")
response = conversation.ask("What is OOP?")    # sends full history to ask_agent

conversation.get_history()                     # [{'role': 'user', ...}, ...]
conversation.get_last_message()
len(conversation)                              # number of messages
conversation.clear()                           # wipe history
```

`ask()` appends your question to the history, hands the history to `ask_agent`,
stores the assistant's reply, and returns the `AgentResponse`. Empty messages
raise `ValidationError` and leave the history untouched.

### `ConversationManager`

Keeps multiple `Conversation` objects, one per session/user:

```python
from backend.conversation import ConversationManager

manager = ConversationManager()
conversation = manager.get_or_create("student-42")   # create if missing
manager.create("another-session")
manager.delete("another-session")
manager.list_ids()                                    # ['student-42']
manager.clear()                                       # drop all conversations
```

---

## Running the tests

From the repository root (`uniagent/`):

```bash
python -m pytest tests -q
```

The suite covers models, config, PDF processing, store persistence,
TF-IDF retrieval, the agent (with mocked Gemini), and the conversation-state
manager. It currently reports **51 passing tests**.

### End-to-end smoke test

`tests/e2e_sample_pdf.py` runs the whole pipeline against the bundled sample PDF
(`data/`):

```bash
# Retrieval-only (no API key required)
python tests/e2e_sample_pdf.py --no-gemini

# Full pipeline (requires GEMINI_API_KEY)
python tests/e2e_sample_pdf.py "What is C++ object-oriented programming?"
```

Without a key the script stops after retrieval and reports the top matching
document. With a key it also generates and prints the answer, sources, and
grounded flag, and shows the resulting conversation history.

---

## Notes

- The document store is a lightweight JSON persistence designed for a prototype;
  for production, swap in a real vector/graph store.
- `google-generativeai` is deprecated; the agent prints a `FutureWarning`
  recommending migration to the `google.genai` package.
- The Streamlit app (`app.py`) is a standalone UI with its own Gemini wiring;
  the `backend/` package is the shared pipeline this README covers.