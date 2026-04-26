# Connect the Stars

Find the shortest connection path between any two actors via shared movies, using the TMDB filmography graph and bidirectional BFS.

## Stack

- **Backend**: Python 3.10+, FastAPI, httpx (async), SQLite cache
- **Algorithm**: Bidirectional BFS, level-by-level, popularity tiebreaker
- **Frontend**: Vite + React + TypeScript + Tailwind + Framer Motion
- **Live progress** via Server-Sent Events

## Run

You need **Python 3.10+** and **Node 18+**. Two processes — backend on `:8000`, frontend dev server on `:5173` (with proxy for `/api`).

### 1. Backend

```bash
pip install -r requirements.txt
uvicorn connect_the_stars.api:app --reload --port 8000
```

The first run creates `connect_the_stars.db` next to the package. The `.env` file with your `TMDB_API_KEY` is loaded automatically.

### 2. Frontend

In another terminal:

```bash
cd web
npm install
npm run dev
```

Open http://localhost:5173.

## CLI (still works)

The original CLI remains available:

```bash
python -m connect_the_stars "Kevin Bacon" "Meryl Streep" --verbose
```

## Layout

```
6 Steps 2.0/
├── connect_the_stars/      # Python package
│   ├── api.py              # FastAPI app (NEW)
│   ├── bfs.py              # Bidirectional BFS
│   ├── cache.py            # SQLite layer
│   ├── config.py
│   ├── main.py             # CLI
│   ├── models.py
│   └── tmdb.py             # TMDB client (async + retry)
├── web/                    # React frontend
│   └── src/
│       ├── App.tsx
│       ├── api.ts
│       ├── components/
│       │   ├── ActorAutocomplete.tsx
│       │   ├── PathView.tsx
│       │   └── ProgressView.tsx
│       └── types.ts
├── .env                    # TMDB_API_KEY (gitignored)
└── requirements.txt
```

## API endpoints

- `GET /api/health` — liveness
- `GET /api/search?q={name}&limit=8` — TMDB people autocomplete
- `GET /api/connect/stream?a_id={n}&b_id={n}&max_depth=6` — SSE stream of progress + final path
- `GET /api/connect?a_id={n}&b_id={n}&max_depth=6` — non-streaming variant
