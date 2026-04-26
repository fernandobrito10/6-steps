"""
Upstash Redis-backed cache (HTTP/REST). Used on Vercel where the filesystem is
ephemeral and SQLite cannot persist between invocations.

Detected automatically by `cache.py` when `KV_REST_API_URL` is set in the
environment (Vercel auto-injects this when a KV/Upstash integration is linked).

Schema is flat key/value with TTL. Keys are namespaced:
    actor:by_name:<query>          -> JSON Actor or "null"
    actor:by_id:<id>               -> JSON Actor
    actor:search:<query>           -> JSON list[Actor]
    actor:movies:<id>              -> JSON list[Movie]
    movie:cast:<id>                -> JSON list[[Actor, billing_order]]
    movie:pt_title:<id>            -> raw string (no TTL — titles are stable)
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any

from .config import CACHE_TTL_DAYS
from .models import Actor, Movie

_TTL_SECONDS = CACHE_TTL_DAYS * 24 * 3600

_redis: Any = None  # upstash_redis.asyncio.Redis instance


def _get_redis():
    global _redis
    if _redis is not None:
        return _redis

    from upstash_redis.asyncio import Redis

    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        raise RuntimeError(
            "Upstash KV configured but KV_REST_API_URL / KV_REST_API_TOKEN not found in env."
        )
    _redis = Redis(url=url, token=token)
    return _redis


def _norm(query: str) -> str:
    return query.lower().strip()


def _actor_to_json(a: Actor) -> str:
    return json.dumps(asdict(a))


def _actor_from_json(raw: str | None) -> Actor | None:
    if raw is None or raw == "null":
        return None
    d = json.loads(raw)
    return Actor(
        id=d["id"],
        name=d["name"],
        popularity=d["popularity"],
        profile_path=d.get("profile_path"),
    )


def _movie_to_dict(m: Movie) -> dict:
    return {
        "id": m.id,
        "title": m.title,
        "year": m.year,
        "popularity": m.popularity,
        "genre_ids": list(m.genre_ids),
        "poster_path": m.poster_path,
        "title_pt": m.title_pt,
    }


def _movie_from_dict(d: dict) -> Movie:
    return Movie(
        id=d["id"],
        title=d["title"],
        year=d.get("year"),
        popularity=d["popularity"],
        genre_ids=tuple(d.get("genre_ids", [])),
        poster_path=d.get("poster_path"),
        title_pt=d.get("title_pt"),
    )


# ---- public API (mirrors cache_sqlite.py) ----


async def init_db(path: str | None = None) -> None:
    # No-op: Redis schema-less; just probe the client to fail fast on bad creds.
    _get_redis()


async def get_actor_by_name(query: str) -> Actor | None:
    r = _get_redis()
    raw = await r.get(f"actor:by_name:{_norm(query)}")
    return _actor_from_json(raw)


async def set_actor_by_name(query: str, actor: Actor | None) -> None:
    r = _get_redis()
    payload = _actor_to_json(actor) if actor is not None else "null"
    await r.set(f"actor:by_name:{_norm(query)}", payload, ex=_TTL_SECONDS)
    if actor is not None:
        await r.set(f"actor:by_id:{actor.id}", _actor_to_json(actor), ex=_TTL_SECONDS)


async def set_actor(actor: Actor) -> None:
    r = _get_redis()
    await r.set(f"actor:by_id:{actor.id}", _actor_to_json(actor), ex=_TTL_SECONDS)


async def get_actor_by_id(actor_id: int) -> Actor | None:
    r = _get_redis()
    raw = await r.get(f"actor:by_id:{actor_id}")
    return _actor_from_json(raw)


async def get_actor_search(query: str) -> list[Actor] | None:
    r = _get_redis()
    raw = await r.get(f"actor:search:{_norm(query)}")
    if raw is None:
        return None
    items = json.loads(raw)
    return [
        Actor(id=d["id"], name=d["name"], popularity=d["popularity"], profile_path=d.get("profile_path"))
        for d in items
    ]


async def set_actor_search(query: str, actors: list[Actor]) -> None:
    r = _get_redis()
    payload = json.dumps([asdict(a) for a in actors])
    await r.set(f"actor:search:{_norm(query)}", payload, ex=_TTL_SECONDS)
    # Also pin individual actor lookups so subsequent get_actor_by_id is a hit.
    for a in actors:
        await r.set(f"actor:by_id:{a.id}", _actor_to_json(a), ex=_TTL_SECONDS)


async def get_actor_movies(actor_id: int) -> list[Movie] | None:
    r = _get_redis()
    raw = await r.get(f"actor:movies:{actor_id}")
    if raw is None:
        return None
    items = json.loads(raw)
    return [_movie_from_dict(d) for d in items]


async def set_actor_movies(actor_id: int, movies: list[Movie]) -> None:
    r = _get_redis()
    # Preserve existing pt titles when overwriting (mirrors the SQLite UPSERT behaviour).
    existing_pt: dict[int, str] = {}
    if movies:
        keys = [f"movie:pt_title:{m.id}" for m in movies]
        results = await r.mget(*keys)
        for m, pt in zip(movies, results):
            if pt:
                existing_pt[m.id] = pt
    enriched = []
    for m in movies:
        if m.title_pt is None and m.id in existing_pt:
            m = Movie(
                id=m.id,
                title=m.title,
                year=m.year,
                popularity=m.popularity,
                genre_ids=m.genre_ids,
                poster_path=m.poster_path,
                title_pt=existing_pt[m.id],
            )
        enriched.append(_movie_to_dict(m))
    payload = json.dumps(enriched)
    await r.set(f"actor:movies:{actor_id}", payload, ex=_TTL_SECONDS)


async def get_movie_cast(movie_id: int) -> list[tuple[Actor, int]] | None:
    r = _get_redis()
    raw = await r.get(f"movie:cast:{movie_id}")
    if raw is None:
        return None
    items = json.loads(raw)
    return [
        (
            Actor(
                id=d["actor"]["id"],
                name=d["actor"]["name"],
                popularity=d["actor"]["popularity"],
                profile_path=d["actor"].get("profile_path"),
            ),
            d["billing_order"],
        )
        for d in items
    ]


async def set_movie_cast(movie_id: int, cast: list[tuple[Actor, int]]) -> None:
    r = _get_redis()
    payload = json.dumps(
        [{"actor": asdict(a), "billing_order": order} for a, order in cast]
    )
    await r.set(f"movie:cast:{movie_id}", payload, ex=_TTL_SECONDS)


async def get_movie_pt_title(movie_id: int) -> str | None:
    r = _get_redis()
    return await r.get(f"movie:pt_title:{movie_id}")


async def set_movie_pt_title(movie_id: int, title_pt: str | None) -> None:
    r = _get_redis()
    if not title_pt:
        return
    # Movie titles are stable; no TTL needed.
    await r.set(f"movie:pt_title:{movie_id}", title_pt)


async def close() -> None:
    global _redis
    if _redis is not None:
        try:
            close_fn = getattr(_redis, "close", None)
            if close_fn is not None:
                result = close_fn()
                if hasattr(result, "__await__"):
                    await result
        except Exception:
            pass
        _redis = None
