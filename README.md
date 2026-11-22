# Verity

Practice professional conversations, then review transcript observations and research suggestions. Feedback is **not a validated measure of confidence, clarity, or goal achievement**. Numerical heuristic scores are no longer displayed, including on legacy reports.

## Start this configured checkout

Open Docker Desktop, then run:

```sh
cd /Users/pmanj/Desktop/verity
python3 scripts/dev.py
```

Open http://localhost:3000. The launcher starts PostgreSQL, applies migrations, and runs the API, report worker, and frontend. Ctrl+C stops the app processes but leaves the database running. Use `docker compose stop` to stop the database without deleting data.

Local STT uses Parakeet via sherpa-onnx with the existing ONNX assets. It is preloaded before the API accepts requests. On the bundled 7.435-second sample, this checkout measured 0.41–0.58 seconds decoding after a 2.27-second load; this is a smoke benchmark, not an accuracy evaluation or universal latency guarantee.

## Run locally

For a hosted personal demo on Vercel with Neon and Clerk, follow
[DEPLOYMENT.md](DEPLOYMENT.md). The hosted configuration uses remote speech
providers and request-driven report jobs; local operation still uses the worker.

Requires Python 3.12+, Node 24+, PostgreSQL 17 and FFmpeg on PATH.

1. Start the local database: `docker compose up -d`.
2. Create `backend/.venv` using `python3.12 -m venv backend/.venv`, install `backend/requirements.txt`, and copy `backend/.env.example` to `backend/.env`. The example database URL matches Docker Compose.
3. Configure Clerk and a conversation provider. Set `CLERK_AUTHORIZED_PARTIES` to your frontend origins. `CLERK_AUDIENCE` is optional and is only needed if you have configured an audience claim. Do not put backend secrets in frontend environment variables.
4. From `backend`, run `.venv/bin/python -m alembic upgrade head`.
5. From `backend`, run `.venv/bin/python -m uvicorn app.main:app --reload`.
6. In another terminal in `backend`, run `.venv/bin/python -m app.feedback.worker`. **The report worker is required.** Run it under your process supervisor in deployment.
7. Copy `frontend/.env.example` to `frontend/.env.local`, configure Clerk and the API URL, then run `npm ci` and `npm run dev` from `frontend`.

For explicit local demos, set `DEMO_MODE=true`; this permits mock conversation/speech providers. Keep it false for real practice. Unknown or unconfigured providers do not silently fabricate responses. Local Parakeet/VibeVoice/Canary models require their respective optional runtimes and downloaded model assets; they are not included in the repository. Use the configured remote adapters if those runtimes are unavailable.

## Upgrade existing installations

Apply the Alembic migration before starting the updated API and worker. It adds durable report jobs and message request IDs, and queues existing reports stuck in `generating`. Existing reports and conversations are preserved. Older failed reports can be retried from their report page.

API clients must send a UUID `request_id` with text messages and multipart voice requests. Voice also requires a multipart `session_id`. Retrying a request with the same ID returns the original saved AI turn. Completion is idempotent and requires at least one user response. A conversation and its opening line, or a user message and AI response, are committed together.

The worker claims one PostgreSQL job with `FOR UPDATE SKIP LOCKED`. A worker crash releases the uncommitted claim, so another worker can resume it. Failed generation is retried up to three times with delays; rendering retries reuse saved structured content. Work may execute again after a crash, but it targets the same report and storage key. Do not configure a transaction timeout shorter than your maximum job duration.

## Verification

From `backend`: `.venv/bin/python -m pytest -q` runs isolated tests. SQLite foreign keys are enabled; provider credentials are overridden and report files go into temporary directories. PostgreSQL concurrency tests require an isolated migrated database:

```sh
DATABASE_URL=postgresql+psycopg://user:password@localhost/test_db .venv/bin/python -m alembic upgrade head
TEST_DATABASE_URL=postgresql+psycopg://user:password@localhost/test_db .venv/bin/python -m pytest -q
```

Never point `TEST_DATABASE_URL` at application data. The suite creates and removes its own users and sessions.

From `frontend`: `npm test`, `npm run lint`, `npx tsc --noEmit`, and `npm run build`. Tests cover arbitrary SSE chunk boundaries and microphone cleanup, timeout and permission races. The production build fetches the configured Google fonts.

## Operations and limits

- `/live` checks process liveness. `/health` checks database access and conversation-provider configuration; it is not a live test of external providers or model readiness.
- Voice uploads are limited to 10 MB and 120 seconds of decoded audio. The browser stops at 115 seconds. Blocking recognition, conversion and generation run off the event loop, with bounded voice concurrency per process.
- Messages are limited to 8,000 characters and sessions to 100 user responses. Authenticated requests have a per-process budget of 60 per minute per user. Configure shared rate limits and body limits at the ingress when running multiple API workers.
- Configure private R2 storage or a persistent local storage volume. Use authenticated report download routes, not public bucket URLs. Back up the database and report storage together.
- Monitor worker logs and pending/failed rows in `report_jobs`. Both the API and the worker must be supervised. Provider failures return recoverable errors; internal exceptions are logged with a correlation ID instead of returned to users.
- Signing keys are refreshed on expiry and unknown key IDs, with a short refresh cooldown. Token origin checks follow [Clerk's verification guidance](https://clerk.com/docs/guides/sessions/manual-jwt-verification).

## Feedback limitations

The scenario checklists find explicit text cues and show the exact user quote. They do not establish quality or success; missing cues are prompts for review, not proof of a weakness. Filler counts include only unambiguous vocalizations present in the transcript, which speech recognition may omit. Research retrieval is optional: a retrieval outage does not discard the feedback report.

Before reintroducing numerical assessments, build a consented, human-rated evaluation set spanning all scenarios and relevant speaking styles; measure agreement and failure cases; version the rubric; and disclose uncertainty. Code tests cannot substitute for that calibration.

Local Python 3.10 environments can fail importing SciPy native extensions on recent macOS. Use Python 3.12 and the pinned SciPy version; the upstream issue is documented [here](https://github.com/scipy/scipy/issues/25635).

For this local checkout, `backend/.venv` now points to the verified Python 3.12 environment at `.venv312`. The obsolete Python 3.10 backup was removed during the October 7, 2026 disk cleanup.

### Local VibeVoice speech output

After installing backend requirements, install the optional speech runtime from the backend directory:

```bash
.venv/bin/python -m pip install -e "vendor/VibeVoice[streamingtts]"
```

This requires the local VibeVoice model and voice assets. The unused model weights were removed during the October 7, 2026 disk cleanup; download them again into `backend/app/voice/vibevoice_assets/model/` before selecting this provider. The configured local provider is Kokoro. Restart the API after installation. The first synthesis loads the model and may download its tokenizer.

### Fast local speech with Kokoro

Install backend requirements, then download `kokoro-v1.0.onnx` and `voices-v1.0.bin` from https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1 into `backend/app/voice/kokoro_assets/`. Set `TTS_PROVIDER=kokoro` and optionally `KOKORO_VOICE=af_heart` in `backend/.env`. Restart the app. Kokoro loads at API startup and generates 24 kHz WAV audio locally. Model weights are Apache-2.0; the ONNX runtime wrapper is MIT.
