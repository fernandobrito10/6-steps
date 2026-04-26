# Connect the Stars

Find the shortest connection path between any two actors via shared movies, using the TMDB filmography graph and bidirectional BFS.

## Stack

- **Backend**: Python 3.10+, FastAPI, httpx (async)
- **Cache**: SQLite locally, Upstash Redis on Vercel (auto-detected via env var)
- **Algorithm**: Bidirectional BFS, level-by-level, popularity tiebreaker
- **Frontend**: Vite + React + TypeScript + Tailwind + Framer Motion
- **Live progress** via Server-Sent Events

## Local dev

You need **Python 3.10+** and **Node 18+**. Two processes — backend on `:8000`, frontend dev server on `:5173` (with proxy for `/api`).

```bash
# Terminal 1 — backend (uses SQLite, persisted to connect_the_stars.db)
pip install -r requirements.txt
uvicorn connect_the_stars.api:app --reload --port 8000

# Terminal 2 — frontend
cd web && npm install && npm run dev
```

Open http://localhost:5173.

## Deploying to Vercel

The whole project (frontend static + Python serverless API) ships in one Vercel project. The cache backend auto-switches from SQLite to Upstash Redis when `KV_REST_API_URL` is set.

### 1. Provision a Redis store

In your Vercel project: **Storage → Marketplace → Upstash for Redis → Create**. Vercel auto-injects these env vars on deploys:

- `KV_REST_API_URL`
- `KV_REST_API_TOKEN`

### 2. Add your TMDB key

Project **Settings → Environment Variables**:

- `TMDB_API_KEY` = `<your v3 key>`

### 3. Deploy

```bash
npm i -g vercel
vercel              # link/create project
vercel --prod       # deploy
```

Vercel will:
- Build the React app via the `buildCommand` in `vercel.json` (output: `web/dist/`)
- Bundle `api/index.py` as a Python serverless function (deps from `requirements.txt`)
- Route `/api/*` → ASGI FastAPI app via the rewrite

### Tier notes

- **Hobby plan**: function timeout caps at 60s. Cold-cache BFS for unpopular pairs may exceed this. Hot cache is sub-second.
- **Pro plan**: `maxDuration: 300` in `vercel.json` allows up to 5 min. Recommended.
- **Without Upstash**: the API will fall back to SQLite, but `/tmp` is ephemeral on Vercel — every cold start starts with empty cache. Useless in practice, hence the integration step above.

## CLI (still works locally)

```bash
python -m connect_the_stars "Kevin Bacon" "Meryl Streep" --verbose
```

## Layout

```
6 Steps 2.0/
├── api/
│   └── index.py            # Vercel entrypoint (re-exports FastAPI app)
├── connect_the_stars/
│   ├── api.py              # FastAPI app
│   ├── bfs.py              # Bidirectional BFS
│   ├── cache.py            # Facade — picks impl by env
│   ├── cache_sqlite.py     # Local backend
│   ├── cache_kv.py         # Upstash Redis backend
│   ├── config.py
│   ├── main.py             # CLI entry
│   ├── models.py
│   └── tmdb.py             # TMDB client (async + retry)
├── web/                    # React frontend (Vite)
├── vercel.json
├── requirements.txt
└── .env                    # TMDB_API_KEY (gitignored, local only)
```

## API endpoints

- `GET /api/health` — liveness
- `GET /api/search?q={name}&limit=8` — TMDB people autocomplete
- `GET /api/connect/stream?a_id={n}&b_id={n}&max_depth=6` — SSE stream of progress + final path
- `GET /api/connect?a_id={n}&b_id={n}&max_depth=6` — non-streaming variant
