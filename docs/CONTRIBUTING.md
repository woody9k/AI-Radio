# Contributing to AI-Radio

## Workflow
1. Create a branch: `feat/*`, `fix/*`, `chore/*`, `docs/*`, or `refactor/*`.
2. Write code following the Style Guide and Coding Standards.
3. Run session checks: `scripts/session_init.sh --no-start --fix`.
4. Update docs when APIs or behavior changes.
5. Open a PR with a clear title, description, and testing notes.

## PR Checklist
- [ ] Lint/format clean (Python + JS)
- [ ] Tests or manual steps documented
- [ ] Docs updated (API/USER_GUIDE/etc.)
- [ ] No secrets or large binaries committed

## Commit Messages
- Imperative mood; short and descriptive.
- Scope prefixes encouraged: `scripts:`, `backend:`, `frontend:`, `docs:`.
