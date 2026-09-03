# Django Multi-Agent Code Generator

A LangChain/LangGraph pipeline of four Gemini-backed agents — **Planner**,
**Coder**, **Tester**, **Reviewer** — that turns a natural-language feature
request into a real, running Django app.

The key design decision: the Tester agent doesn't ask the LLM whether the
code "looks correct." It writes the generated files to disk into an actual
Django project and runs `manage.py check`, `manage.py makemigrations
--check`, and `manage.py test` as real subprocesses. Failures go back to the
Coder as concrete feedback. That loop is what makes the output *running*
software rather than plausible-looking code.

## Architecture

```
            ┌─────────┐
   spec ──► │ Planner │  produces a structured file-by-file plan
            └────┬────┘
                 ▼
            ┌─────────┐
      ┌───► │  Coder  │  writes/rewrites complete file contents
      │     └────┬────┘
      │          ▼
      │     ┌─────────┐
      │     │ Tester  │  writes files to disk, runs manage.py check/test
      │     └────┬────┘
      │          ▼
      │     ┌──────────┐
      │     │ Reviewer │  LLM review: security, correctness, N+1s, etc.
      │     └────┬─────┘
      │          ▼
      │   tests pass AND review approved? ──► done
      └── no, and iterations remain ◄────────┘
                 │
                 ▼ (out of iterations)
                done (reports outstanding issues)
```

Orchestration is a `langgraph.graph.StateGraph`: `planner -> coder -> tester
-> reviewer -> (conditional: done | revise -> coder | give_up)`. All agent
outputs are Pydantic-typed (`src/schemas.py`), parsed via LangChain's
`PydanticOutputParser`, so every agent hands the next one structured data,
never free text to re-parse.

## Project layout

```
main.py                   CLI entry point; bootstraps the Django project
src/config.py              env-driven config (API key, model, iterations)
src/schemas.py             Pydantic contracts between agents
src/graph.py                LangGraph wiring + revise/give-up routing
src/agents/planner.py       spec -> ProjectPlan
src/agents/coder.py         plan (+feedback) -> file contents
src/agents/tester.py        writes files, runs real manage.py commands
src/agents/reviewer.py      security/quality review -> approve or block
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and set GOOGLE_API_KEY (https://aistudio.google.com/apikey)
```

## Usage

```bash
python main.py "Build a task management feature: a Task model with title, \
description, due_date, and a status field (todo/in_progress/done), a list \
view, a detail view, and a form to create/update tasks." --app-name tasks
```

This will:
1. Run `django-admin startproject config .` and `manage.py startapp tasks`
   into `./generated_project` (configurable via `--project-dir` or
   `PROJECT_OUTPUT_DIR`), and register the app in `INSTALLED_APPS`.
2. Run the Planner -> Coder -> Tester -> Reviewer loop, up to
   `MAX_ITERATIONS` revision passes (default 3).
3. Print a run log and summary, e.g.:

```
Tests:  PASSED
Review: APPROVED
Project written to: /home/you/project/generated_project
Run it with: cd generated_project && python manage.py runserver
```

At that point the app is a real Django project — migrate and run it:

```bash
cd generated_project
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

## Notes / things to extend

- **Migrations**: the Tester only checks migration *consistency*
  (`--check --dry-run`), it doesn't apply them, since a fresh SQLite DB
  isn't created per run. Add a `manage.py migrate` step in
  `src/agents/tester.py` if you want the test suite to run against a live
  schema (it already will inside `manage.py test`, which uses its own test DB).
- **Iteration budget**: bump `MAX_ITERATIONS` in `.env` for gnarlier specs;
  each iteration is a full Coder + Tester + Reviewer round trip.
- **Model choice**: `GEMINI_MODEL` in `.env` — `gemini-2.5-flash` is a good
  default for cost/latency; swap to a stronger model for complex specs.
- **DRF support**: the Planner is told to avoid DRF unless the spec asks for
  it. If you want API endpoints by default, add that to the Planner's system
  prompt and `djangorestframework` to `requirements.txt`.
- **Human approval gate**: matches the pattern from your incident-response
  pipeline — you could add a `human_review` node before `done` that pauses
  for sign-off on generated code, the same way your Redis Streams pipeline
  gates on human approval before remediation.
