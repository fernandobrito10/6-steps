import asyncio
import json
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

load_dotenv()

from . import bfs, cache, tmdb
from .config import MAX_DEPTH
from .models import Actor, Movie, Step

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.init_db()
    try:
        yield
    finally:
        await tmdb.close()
        await cache.close()


app = FastAPI(title="Connect The Stars", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _actor_dict(a: Actor) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "popularity": a.popularity,
        "profile_path": a.profile_path,
    }


def _movie_dict(m: Movie | None) -> dict | None:
    if m is None:
        return None
    return {
        "id": m.id,
        "title": m.title,
        "title_pt": m.title_pt,
        "year": m.year,
        "popularity": m.popularity,
        "poster_path": m.poster_path,
    }


def _step_dict(s: Step) -> dict:
    return {"actor": _actor_dict(s.actor), "via_movie": _movie_dict(s.via_movie)}


async def _attach_pt_titles(path: list[Step]) -> list[Step]:
    """Resolve Portuguese titles for the movies on the path in parallel and return new Steps with them."""
    movies_in_path = [(idx, s.via_movie) for idx, s in enumerate(path) if s.via_movie is not None]
    if not movies_in_path:
        return path

    pt_titles = await asyncio.gather(
        *(tmdb.get_movie_pt_title(m.id) for _, m in movies_in_path),
        return_exceptions=True,
    )

    out = list(path)
    for (idx, original), pt in zip(movies_in_path, pt_titles):
        if isinstance(pt, Exception) or not pt:
            continue
        new_movie = Movie(
            id=original.id,
            title=original.title,
            year=original.year,
            popularity=original.popularity,
            genre_ids=original.genre_ids,
            poster_path=original.poster_path,
            title_pt=pt,
        )
        out[idx] = Step(actor=path[idx].actor, via_movie=new_movie)
    return out


@app.get("/api/health")
async def health():
    return {"ok": True}


@app.get("/api/search")
async def search(q: str = Query(..., min_length=1), limit: int = 8):
    actors = await tmdb.search_actors_multi(q, limit=min(limit, 20))
    return {"results": [_actor_dict(a) for a in actors]}


@app.get("/api/connect/stream")
async def connect_stream(
    a_id: int = Query(...),
    b_id: int = Query(...),
    max_depth: int = Query(MAX_DEPTH, ge=1, le=10),
):
    queue: asyncio.Queue = asyncio.Queue()

    async def runner() -> None:
        try:
            await queue.put({"type": "resolving"})
            actor_a, actor_b = await asyncio.gather(
                tmdb.get_actor_by_id(a_id),
                tmdb.get_actor_by_id(b_id),
            )
            if actor_a is None:
                await queue.put({"type": "error", "message": f"Actor not found: id={a_id}"})
                return
            if actor_b is None:
                await queue.put({"type": "error", "message": f"Actor not found: id={b_id}"})
                return

            await queue.put(
                {
                    "type": "resolved",
                    "actor_a": _actor_dict(actor_a),
                    "actor_b": _actor_dict(actor_b),
                }
            )

            loop = asyncio.get_running_loop()

            def on_progress(side: str, frontier_size: int, next_depth: int) -> None:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {
                        "type": "expand",
                        "side": side,
                        "frontier_size": frontier_size,
                        "next_depth": next_depth,
                    },
                )

            path = await bfs.find_shortest_path(
                actor_a, actor_b, max_depth=max_depth, on_progress=on_progress
            )

            if path is None:
                await queue.put(
                    {
                        "type": "no_path",
                        "max_depth": max_depth,
                    }
                )
            else:
                path = await _attach_pt_titles(path)
                await queue.put(
                    {
                        "type": "result",
                        "path": [_step_dict(s) for s in path],
                        "hops": max(0, len(path) - 1),
                    }
                )
        except Exception as e:
            log.exception("connect_stream failed")
            await queue.put({"type": "error", "message": str(e)})
        finally:
            await queue.put(None)

    task = asyncio.create_task(runner())

    async def event_gen():
        try:
            await queue.put({"type": "start"})
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/connect")
async def connect(
    a_id: int = Query(...),
    b_id: int = Query(...),
    max_depth: int = Query(MAX_DEPTH, ge=1, le=10),
):
    actor_a, actor_b = await asyncio.gather(
        tmdb.get_actor_by_id(a_id),
        tmdb.get_actor_by_id(b_id),
    )
    if actor_a is None or actor_b is None:
        raise HTTPException(status_code=404, detail="Actor not found")

    path = await bfs.find_shortest_path(actor_a, actor_b, max_depth=max_depth)
    if path is None:
        return {"path": None, "hops": None, "max_depth": max_depth}
    path = await _attach_pt_titles(path)
    return {"path": [_step_dict(s) for s in path], "hops": max(0, len(path) - 1)}
