# NexusIQ — Production Deployment Guide

> **All 4 known deployment traps are already fixed in this codebase.**
> This guide sequences steps to avoid every one of them.

---

## Architecture

```
Vercel (frontend)  →  Railway (backend)  →  Neon (Postgres)
                                         →  Upstash (Redis)
                                         →  Qdrant Cloud (vector)
                                         →  Supabase (file storage)
```

All services are **free tier**. No credit card required for any of them.

---

## Step 1 — Free Services (15 min)

### Postgres — Neon
1. https://neon.tech → Sign up → New Project → name it `nexusiq`
2. Copy the **Connection string** — it will look like:
   ```
   postgresql://user:pass@host.neon.tech/nexusiq?sslmode=require
   ```
   **Do not change the format.** The app auto-converts it to `asyncpg` internally.

### Redis — Upstash
1. https://upstash.com → Create Database → copy **Redis URL** (starts with `rediss://`)

### Vector DB — Qdrant Cloud
1. https://cloud.qdrant.io → Create Cluster (Free) → copy **URL** and **API Key**

### Storage — Supabase
1. https://supabase.com → New Project
2. Settings → API → copy:
   - **Project URL** → `SUPABASE_URL`
   - **service_role** key → `SUPABASE_KEY` ← must be service_role, NOT anon
3. Storage → New Bucket → name: `nexusiq-submissions` → Public: **No**

---

## Step 2 — LLM API Keys

You need **at least one key** from any tier. Get a Gemini key first — it's instant.

| Tier | Provider | Free Limit | Get Key |
|------|----------|-----------|---------|
| 1 | Cerebras | 1M tokens/day | https://cloud.cerebras.ai |
| 2 | Gemini | 60 req/min | https://aistudio.google.com/app/apikey |
| 3 | Groq | 6k tokens/min | https://console.groq.com |

> **DEMO_MODE users:** You can skip LLM keys entirely. Set `DEMO_MODE=true` and the
> app uses pre-cached responses. No API calls, no rate limits.
> RAG/course-generation features will be disabled but all interactive flows work.

---

## Step 3 — Backend on Railway

### ⚠️ CORS Bootstrap Order (Issue 3 Fix)
Railway must be deployed **before** Vercel, because Vercel needs the backend URL.
Set `CORS_ORIGINS=*` initially — update it once you have the Vercel URL.

1. https://railway.app → New Project → Deploy from GitHub
2. Point to the repo root — Railway will detect `backend/Dockerfile` automatically.
   - If it doesn't: set **Root Directory** to `backend` in Railway settings.
3. Add environment variables in Railway dashboard:

```env
DATABASE_URL=postgresql://user:pass@host.neon.tech/nexusiq?sslmode=require
REDIS_URL=rediss://default:pass@host.upstash.io:6380
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
JWT_SECRET=<run: python -c "import secrets; print(secrets.token_hex(32))">
ENVIRONMENT=production
CORS_ORIGINS=*
GEMINI_API_KEY_1=AIza...
PORT=8000
```

4. Deploy. Railway builds the Docker image and runs `./start.sh` which:
   - Runs `alembic upgrade head` (migrations) → then starts `uvicorn`
   - **No manual shell access needed.** Migrations happen automatically on every deploy.

5. Copy the Railway URL: `https://nexusiq-backend-xxxx.up.railway.app`

### Verify backend is live
```bash
curl https://nexusiq-backend-xxxx.up.railway.app/health
# → {"status":"ok","demo_mode":false}
```

---

## Step 4 — Frontend on Vercel

1. https://vercel.com → Import Git Repository → select this repo
2. **Root Directory:** `frontend`
3. Framework: Next.js (auto-detected)
4. Add environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://nexusiq-backend-xxxx.up.railway.app
   ```
5. Deploy → copy the Vercel URL: `https://nexusiq-xxxx.vercel.app`

---

## Step 5 — Tighten CORS (Issue 3 Final Step)

Now that you have both URLs, update Railway's `CORS_ORIGINS`:
```
CORS_ORIGINS=https://nexusiq-xxxx.vercel.app,http://localhost:3000
```
Railway will redeploy automatically. The `*` wildcard is gone.

---

## Step 6 — First User

Create a manager account to log in:
```bash
curl -X POST https://nexusiq-backend-xxxx.up.railway.app/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"manager@company.com","password":"SecurePass123","name":"Demo Manager","role":"manager"}'
```

Then open the Vercel URL and log in.

---

## Local Development

```bash
git clone https://github.com/your-org/nexusiq
cd nexusiq
cp .env.example .env   # fill in values from steps 1-2

# Start local infra
docker-compose up postgres redis qdrant -d

# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head      # run migrations
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## Environment Variables Reference

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | ✅ | Any postgres:// format — auto-converted to asyncpg |
| `REDIS_URL` | ✅ | Upstash gives rediss:// (TLS) — works as-is |
| `QDRANT_URL` | ✅ | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | ✅ | Qdrant Cloud API key |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_KEY` | ✅ | Must be **service_role** key, not anon |
| `JWT_SECRET` | ✅ | Unique random string — use `secrets.token_hex(32)` |
| `ENVIRONMENT` | ✅ | `dev` or `production` |
| `CORS_ORIGINS` | ✅ | Use `*` during bootstrap, then set to Vercel URL |
| `CEREBRAS_API_KEY_1` | ⚠️ | At least one LLM key OR `DEMO_MODE=true` |
| `GEMINI_API_KEY_1` | ⚠️ | Required for RAG/course-gen; not needed in DEMO_MODE |
| `GROQ_API_KEY` | ➖ | Optional emergency fallback |
| `DEMO_MODE` | ➖ | `true` = cached responses, no LLM keys needed |
| `PORT` | ✅ Railway | Set to `8000` in Railway env vars |

---

## Production Checklist

- [ ] `JWT_SECRET` is a unique random value (not the placeholder)
- [ ] `ENVIRONMENT=production` is set
- [ ] `CORS_ORIGINS` updated from `*` to your actual Vercel URL
- [ ] `SUPABASE_KEY` is the **service_role** key (not anon)
- [ ] Supabase bucket `nexusiq-submissions` created and set to private
- [ ] `/health` endpoint returns `{"status":"ok"}`
- [ ] Can register + login as manager
- [ ] At least one LLM key set (or `DEMO_MODE=true`)

---

## Troubleshooting

**`alembic upgrade head` fails with connection error**
- The URL is auto-normalized by `alembic/env.py` — check the Neon connection string is correct
- Neon requires `?sslmode=require` at the end of the URL

**Storage uploads fail**
- Verify `SUPABASE_KEY` is the `service_role` secret, not the `anon` public key
- Bucket `nexusiq-submissions` must exist before first upload

**All LLM calls fail**
- Check at least one key is set: `CEREBRAS_API_KEY_1`, `GEMINI_API_KEY_1`, or `GROQ_API_KEY`
- Or set `DEMO_MODE=true` to bypass all LLM calls

**Railway crashloops on first deploy**
- Check logs: if it's a migration error, fix `DATABASE_URL` format
- `start.sh` runs migrations first — any migration failure will prevent startup
- Check Railway → Logs tab for the exact error line

**Frontend shows CORS error**
- Backend `CORS_ORIGINS` must include the exact Vercel URL (no trailing slash)
- Temporarily set `CORS_ORIGINS=*` to verify connectivity, then tighten
