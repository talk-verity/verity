# Verity frontend

See the [project README](../README.md) for setup, configuration, deployment and verification.

Use Node 24+. Run `npm ci`, then `npm run dev`. Checks: `npm test`, `npm run lint`, `npx tsc --noEmit`, `npm run build`.

Voice recording is managed by `hooks/useVoiceRecorder.ts`; SSE frame parsing is in `lib/sse.ts`. Requests include stable retry IDs, and the displayed transcript is refreshed from the server after a response. Report pages poll while generation is pending and allow retrying failed generation.
