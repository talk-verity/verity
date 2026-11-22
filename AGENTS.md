# Verity Development Guidelines (Karpathy's Rules)

This repository follows Andrej Karpathy's engineering principles for AI-assisted software development:

## 1. Think Before Coding
- **State assumptions explicitly**: Never guess or implement ambiguous requirements blindly.
- **Truth over fiction**: Do not invent metrics or heuristics. In Verity, feedback must be grounded in observable transcript cues and cited research, not unvalidated numerical scores.
- **Understand operational bounds**: Respect limits (e.g. 4 MB / 120s voice limits on Vercel, bounded rate limits).

## 2. Simplicity First
- **Minimum code necessary**: Write the leanest implementation that solves the problem. No speculative features or premature abstractions for single-use code.
- **Zero bloat**: Keep dependencies minimal. Exclude local ONNX/PyTorch models and heavy asset packs from cloud deployments (use `pyproject.toml` and `.vercelignore`).
- **Lean repository**: Do not commit virtual environments, node modules, build caches, or temporary recordings.

## 3. Surgical Changes
- **Touch only what is necessary**: Avoid "while I'm here" refactorings of unrelated files.
- **Traceable diffs**: Every line changed must trace directly back to the objective.
- **Idempotency & safety**: Maintain transactional boundaries (`request_id` idempotency, PostgreSQL `SKIP LOCKED` job claims).

## 4. Goal-Driven Verification
- **Run the verification loop before concluding work**:
  - Backend: `cd backend && .venv/bin/python -m pytest tests -q` (119+ tests passing).
  - Frontend: `npm test --prefix frontend` (SSE streaming & audio hook tests).
  - Types & Lint: `cd frontend && npx tsc --noEmit && npm run lint`.
  - Health & Readiness: Verify `/live` and `/health` endpoints.
