# CodePilot Ops

Multi-agent AI system that automates parts of the software development lifecycle: GitHub issue triage and PR review, grounded in a RAG pipeline over the actual codebase, orchestrated with LangGraph, gated behind human approval, and measured with a custom eval harness.

## What it does

CodePilot Ops listens for GitHub issue and pull request events via webhook. Each event is routed through a LangGraph supervisor to one of two specialized agents:

- **Triage Agent** — classifies incoming issues (bug / feature / question), assigns severity, and grounds its reasoning in code retrieved from the actual repository via semantic search.
- **Review Agent** — reviews PR diffs against retrieved architectural context from the same codebase, flagging issues a generic linter would miss (resource leaks, missing imports, inconsistency with existing patterns).

No agent output is ever applied automatically. Every result is written to a `pending_actions` table and requires explicit human approval via a CLI review flow before it's considered actionable.

## Architecture

GitHub (issue/PR) → Webhook (HMAC-verified) → LangGraph supervisor (conditional routing) → Triage Agent | Review Agent → RAG retrieval (pgvector, cosine similarity) → LLM (structured JSON output) → pending_actions (human-approval gate) → CLI review (approve / reject)

Every LLM call is traced via a self-hosted Langfuse instance, capturing full input/output, latency, and model metadata for every agent invocation.

## Tech stack

| Layer | Tech |
|---|---|
| API / webhooks | FastAPI, HMAC-SHA256 signature verification |
| Orchestration | LangGraph (conditional multi-agent routing) |
| Retrieval | pgvector, cosine similarity search |
| Chunking | Custom AST-based Python chunker (function/class-level, not naive text splitting) |
| Embeddings | OpenAI text-embedding-3-small |
| LLM | Provider-agnostic client (tested against ResetData/Gemma; also supports Anthropic, OpenAI-compatible endpoints) |
| Database | PostgreSQL + pgvector, SQLAlchemy, Alembic migrations |
| Observability | Langfuse (self-hosted via Docker) |
| Tunneling (dev) | ngrok |

## Why these design choices

**AST-based chunking over fixed-size text splitting.** Splitting code by function/class boundaries (using Python's built-in ast module) instead of arbitrary character counts means retrieved chunks are semantically complete and traceable back to a real symbol (UserService.authenticate) rather than an arbitrary text fragment. Each chunk also retains its enclosing class name, so retrieval results carry real context.

**Retrieval-grounded agents, not bare LLM calls.** Both agents embed their input and run a cosine-similarity search over the ingested codebase before calling the LLM, injecting the retrieved code as context. This is what allows the Review Agent to flag things like "this is inconsistent with the pattern in ingest.py" — a claim only possible because it actually retrieved ingest.py.

**Human-approval gate as a real mechanism, not a design note.** Agent outputs are written to a pending_actions table with status=pending. Nothing is treated as final until a reviewer explicitly approves or rejects it via scripts/review_pending.py. This mirrors how a real deployment would need to work — no LLM output should silently become a repo action.

**Defensive JSON parsing.** LLMs (especially smaller open models) don't always follow "no markdown fences" instructions perfectly. Both agents extract JSON via regex rather than trusting json.loads() on the raw response directly — a small but real production pattern.

**pgvector over a managed vector DB.** Chosen for infrastructure transparency and to demonstrate direct SQL/ORM-level control over the retrieval layer (SQLAlchemy + Alembic migrations), rather than treating retrieval as a black-box API call to a third-party service.

## Eval results

An automated eval harness scores the Triage Agent against a hand-labeled golden dataset (data/golden_dataset/triage_golden.json, 5 cases covering bug/feature/question classification with expected severity and expected relevant file).

Run it: `python -m app.eval.run_triage_eval`

Latest results:

| Metric | Score |
|---|---|
| Category accuracy | 100% |
| Severity exact-match accuracy | 80% |
| Severity adjacent accuracy (off by <=1 level) | 100% |
| Retrieval hit rate (expected file retrieved) | 80% |

## Known limitations

- **Retrieval miss on symptom-language issues.** One golden case (triage_004, describing a "Connection error" symptom) failed to retrieve its expected source file (app/core/embeddings.py). The issue text describes a symptom rather than the underlying mechanism, so semantic similarity to the actual fix location is weaker than for issues that reference implementation details directly. This is a known class of RAG limitation, not a bug — documented here rather than hidden.
- **LLM outputs can contain plausible-but-wrong specifics.** During manual testing, the Review Agent correctly identified a missing import but suggested an incorrect module path (app.models instead of the actual app.db.models). The reasoning was sound; the specific fact was hallucinated. This is exactly the kind of failure mode the eval harness and human-approval gate exist to catch — it's flagged here as a concrete, observed example rather than a hypothetical risk.
- **Golden dataset is small (5 cases).** Sufficient to demonstrate the eval methodology; would need meaningful expansion before being a statistically reliable accuracy measure.
- **Sandboxed execution caught a real LLM code-generation bug.** During testing, the Test-Gen Agent produced a test using pytest.approx(...) without importing pytest itself, causing a NameError -- 2 of 3 generated test functions were correct, one had this specific omission. Because generated tests are actually executed (not just visually inspected), this was caught immediately rather than silently entering the approval queue as a passing result. The system prompt was subsequently strengthened to explicitly require the pytest import, and the fix was verified by re-running the same case, which then produced 5 passing tests including coverage of Python's operator overloading behavior. This is included here as a concrete example of why sandboxed verification -- not just LLM output inspection -- matters for any agent that generates executable code.

## Setup

### Prerequisites
- Python 3.12
- Docker
- An OpenAI API key (embeddings)
- An LLM API key (any OpenAI-compatible or Anthropic-compatible provider)

### Install

    python3.12 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

### Configure

    cp .env.example .env

Fill in LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, EMBEDDING_API_KEY, GITHUB_TOKEN, GITHUB_WEBHOOK_SECRET.

### Database

    docker compose up -d
    docker exec -it codepilot_db psql -U codepilot -d codepilot -c "CREATE EXTENSION IF NOT EXISTS vector;"
    alembic upgrade head

### Ingest a codebase

    python scripts/run_ingestion.py --path . --repo-name codepilot-ops

### Run the server

    uvicorn app.api.main:app --reload --port 8001

### Expose for GitHub webhooks (local dev)

    ngrok http 8001

Add the forwarding URL + /webhooks/github as a webhook in your repo's Settings -> Webhooks, with events set to Issues and Pull requests.

### Review pending agent actions

    python scripts/review_pending.py list
    python scripts/review_pending.py approve <id>
    python scripts/review_pending.py reject <id>

### Run the eval harness

    python -m app.eval.run_triage_eval

## Observability

Trace every agent's LLM calls (self-hosted Langfuse):

    git clone https://github.com/langfuse/langfuse.git langfuse-selfhost
    cd langfuse-selfhost
    docker compose up -d

Dashboard at http://localhost:3000. Add the generated API keys to .env as LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST.

## Project structure

    app/
      agents/       # Triage, Review agents + LangGraph supervisor + approval gate
      api/          # FastAPI app, GitHub webhook endpoint
      core/         # config, LLM client, embeddings client, observability
      db/           # SQLAlchemy models, Alembic migrations
      eval/         # eval harness
      rag/          # chunker, ingestion pipeline, retrieval
    data/
      golden_dataset/  # hand-labeled eval data
    scripts/        # CLI entrypoints (ingestion, eval, review, test scripts)
