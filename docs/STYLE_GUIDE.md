# AI-Radio Style Guide

## General Principles
- Prefer clarity over cleverness. Short functions, explicit names, early returns.
- Keep modules focused; avoid deep nesting; extract helpers.
- Comments only for rationale, invariants, or non-obvious context.

## Python (Backend)
- Language: Python 3.12+.
- Formatting: Black (line length 100). Linting: Ruff. Types: optional, but annotate public APIs.
- Naming: snake_case for functions/vars, PascalCase for classes, UPPER_SNAKE for constants.
- Imports: standard, third-party, local (grouped). Absolute imports within `backend.*`.
- Error handling: catch only specific exceptions; log with context using `logger.exception` when needed.
- Logging: use module logger. No print. INFO for normal ops, WARNING for recoverable, ERROR for failures.
- Structure: `backend/app.py` only wires routes; heavy logic in modules under `backend/*`.

## JavaScript/React (Frontend)
- Framework: React 18 + Vite.
- Formatting: Prettier (default), Linting: ESLint (react, hooks).
- Naming: PascalCase for components, camelCase for functions/vars, UPPER_SNAKE for constants.
- Components: functional components with hooks; co-locate small helpers; lift state minimally.
- JSX: wrap adjacent siblings in fragments; keep props clear; avoid inline complex lambdas.
- State: prefer local state; avoid unnecessary context/global state.
- Networking: fetch/axios via thin API modules under `src/api/`.

## API Design
- JSON responses: always include `success` boolean; `error` string on failure.
- Validate and sanitize inputs; enforce bounds (frequencies, rates).
- Use 2xx for success, 4xx for client errors, 5xx for server errors.

## Security & Privacy
- Do not log secrets. Mask API keys in responses.
- Bind dev server to 0.0.0.0 only when needed; document network exposure.
- CORS: restrict in production; `*` allowed in dev.

## Tests & Diagnostics
- Prefer deterministic unit tests for pure utilities.
- Provide CLI/test scripts for hardware boundaries.


