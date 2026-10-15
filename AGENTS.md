# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project Overview

Website (frontend and backend) for the Genotype-phenotype Map (GPMap).

- `app/` — FastAPI backend
  - `app/api/v1/endpoints/` — API endpoints
  - `app/db/` — database access (DuckDB queries)
  - `app/models/schemas.py` — Pydantic models
- `frontend/` — Vite + Alpine.js + Bulma frontend
  - `*.html` — one page per view (gene, variant, trait, region, ...)
  - `alpine-components/` — Alpine.js components backing each page
  - `web-components/` — shared web components
- `tests/` — pytest suites (`unit/`, `integration/`, `test_data/`)

## Environment Setup

For things that you are running in the background, don't clog up port 8000, or keep it open.  That is the port that the local server accepts requests on.

Python tooling (`ruff`, `pytest`, `uvicorn`) is installed in the project virtualenv. Activate it first:

```
source .venv/bin/activate
```

Node/npm is managed by nvm and is **not** provided by the virtualenv. Load it with:

```
source ~/.nvm/nvm.sh
```

## Linting, Formatting, and Tests

Run these before finishing a change. CI runs the same checks.

Python (from the repo root, with the venv active):

- `ruff format` — format code (config in `ruff.toml`)
- `ruff check` — lint
- `pytest` — run tests

JavaScript (from `frontend/`, with nvm loaded):

- `npm run lint` — ESLint (`eslint.config.js`) and Prettier check
- `npm run format` — ESLint autofix and Prettier write

## Coding Guidelines

- Keep in mind that the API is publicly available, and is also used by the public R package gpmapr
- Try to avoid breaking changes to the API if possible.  If a breaking change is made to the API, please explicity state it, as we need to mitigate and version bump the API.
- Make minimal changes; do not refactor, extract, or reorganize files unless asked.
- Follow the conventions and libraries already used in the file or repository.
- Do not add a private helper with only one call site; inline it instead.
- Never delete existing comments unless the associated code is also deleted.
- Favor readable, explicit code over clever one-liners.
- Ensure changes do not cause unrelated regressions.
