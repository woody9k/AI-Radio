# AI-Radio Coding Standards

## Enforced Tools
- Python: Black (format), Ruff (lint), optional MyPy (types)
- JS/React: Prettier (format), ESLint (lint)

## Python Rules
- Line length 100; Black formatting enforced.
- No print statements; use logging.
- No bare `except:`; catch specific exceptions.
- Functions should be small; extract helpers.
- Public functions/classes should include docstrings.

## JS/React Rules
- Use functional components and hooks.
- Keep props simple; avoid deep prop drilling.
- Prefer small components; extract UI helpers.
- ESLint errors must be zero before merge.

## Commits & Branches
- Branch names: `feat/*`, `fix/*`, `chore/*`, `docs/*`, `refactor/*`.
- Commits: imperative mood, concise; scope prefixes encouraged.
- PR checklist: build scripts run, lint/format clean, updated docs, tested happy path.

## API Contracts
- All endpoints return `{ success, ... }`; include `error` on failure.
- Use 2xx/4xx/5xx appropriately; validate inputs.

## Dependencies
- Avoid unused deps; pin majors as needed.
- Do not commit secrets; provide `.env.example`.

## CI (future)
- Run ruff, black --check, eslint, and optional mypy on PRs.
