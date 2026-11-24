# Vercel + Neon + Clerk

## Current deployment

- Frontend: https://delphi-web-azure.vercel.app
- API: https://delphi-api-roan.vercel.app
- Vercel workspace: `par-ms-projects`
- Projects: `delphi-web` and `delphi-api`
- Both local directories are linked for CLI deployments. To deploy reviewed
  changes, run `vercel deploy --prod` from the appropriate directory.
- These deployments were uploaded directly from the checkout; pushing GitHub
  changes alone does not establish automatic deployments.
- Production uses Neon and the existing Clerk development instance. Keep the
  Neon URL in the ignored `backend/.env.vercel` file and Vercel's sensitive
  environment variables. Do not commit it.

Use two Vercel Hobby projects from the same repository: `delphi-api` with root
`backend`, and `delphi-web` with root `frontend`. Hobby is for personal,
noncommercial use. Use each project's actual assigned URL in all configuration.
This guide prepares a fresh hosted database; it does not copy local conversations.

## 1. Neon

Create a Free project at https://console.neon.tech with PostgreSQL 17. Select a
region near your Vercel API region. In Connect, disable connection pooling and
copy the direct connection string. Keep all SSL parameters.

From the repository root run:

```sh
python3 scripts/migrate_neon.py
```

Paste the direct connection string at the hidden prompt. It is used only for
this command, not saved or printed. This runs the existing Alembic migrations
using your configured local backend environment. It leaves your local database
configuration untouched. Success ends with the migration upgrade completing.

For the API, select connection pooling in Neon, copy that URL, and replace only
`postgresql://` with `postgresql+psycopg://`. Save it in Vercel's DATABASE_URL.

## 2. Prepare the repository

Push the current reviewed application changes and deployment files to the GitHub
repository you will import. Do not commit `.env`, `.env.local`, downloaded model
assets, or virtual environments. Existing unrelated local changes should be
reviewed before committing. This preparation does not automatically commit or push.

## 3. Vercel API

At https://vercel.com/new import `talk-delphi/delphi`, name the project
`delphi-api` (or another available name), set Root Directory to `backend` and
Framework Preset to FastAPI. Keep default install/build settings. The deployment
uses pyproject.toml; .vercelignore excludes the large local requirements.txt and
model assets. Do not configure a build step that runs migrations against the
production database on every preview deployment.

Add the variables from backend/.env.vercel.example in the Vercel environment UI.
Replace placeholders with your Neon URL, existing Clerk domain, Groq key, and
the intended frontend origin. Copy CLERK_DOMAIN and GROQ_API_KEY privately from
backend/.env. The API verifies Clerk's JWTs with public signing keys and does not
need CLERK_SECRET_KEY. Keep CLERK_AUDIENCE unset unless you deliberately configured
an audience claim. Keep Pinecone, Gemini and R2 keys unset for the minimal setup.

Set variables for Production initially. Use separate databases for previews if
you enable those. Deploy and note the assigned API URL. Check `/live` and `/health`;
health must return 200 with database=true. It does not test the external AI or
speech services. If the API has Vercel Authentication protection enabled, remove
that protection for its production deployment so browsers can access it. Clerk
continues to protect authenticated API routes.

## 4. Vercel frontend

Import the same repository again, name the project `delphi-web`, select root
`frontend` and Next.js. Use Node 24, `npm ci`, and `npm run build`.

Set Production variables:

```dotenv
NEXT_PUBLIC_API_URL=https://YOUR_API.vercel.app/api/v1
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=YOUR_EXISTING_CLERK_PUBLISHABLE_KEY
CLERK_SECRET_KEY=YOUR_EXISTING_CLERK_SECRET_KEY
```

Copy Clerk keys privately from frontend/.env.local. The keys and backend Clerk
domain must belong to the same Clerk instance. Never put secret keys in a
NEXT_PUBLIC variable. Deploy and note the actual frontend URL.

## 5. Connect origins and login

Update the API's Production variables to the actual frontend origin (no trailing
slash or path), then redeploy the API:

```dotenv
BACKEND_CORS_ORIGINS=["https://YOUR_FRONTEND.vercel.app"]
CLERK_AUTHORIZED_PARTIES=["https://YOUR_FRONTEND.vercel.app"]
```

Development Clerk keys are suitable for the initial hosted test and will show
development branding. A public production launch requires a Clerk production
instance and its domain/DNS setup, followed by replacing the frontend keys and
backend domain together. Do not switch only one side.

## 6. Verify

Sign in; open a scenario; send text; record a short voice response; finish the
conversation; open its report and download the HTML. Reload and verify saved
conversations/reports still exist. Test sign-out and confirm protected content
requires login. Check Vercel API logs if any request fails.

On Vercel, opening a generating report processes one saved job during an
authenticated POST request. PostgreSQL locks prevent concurrent requests from
claiming the same job. Jobs persist after interruption and retry on a subsequent
page visit/poll; up to three failures are attempted. Reports are not generated
autonomously while nobody is opening the report page. The local deployment still
uses its separate worker by default.

Recordings are compressed where the browser supports it and capped at 4 MiB to
leave room below Vercel's 4.5 MB multipart request limit. FFmpeg ships via
imageio-ffmpeg. The hosted build excludes local speech models and research PDFs;
Groq handles conversation and transcription. Optional research retrieval is
skipped in this configuration. Edge speech output is best effort: failures still
deliver the saved text response. AI provider quotas and Vercel/Neon quotas apply.

## References

- https://vercel.com/docs/frameworks/backend/fastapi
- https://vercel.com/docs/functions/runtimes/python
- https://vercel.com/docs/functions/limitations
- https://vercel.com/docs/plans/hobby
- https://neon.com/docs/connect/connect-from-any-app
