import asyncio
import logging
import random

import httpx

from . import cache
from .config import (
    EXCLUDED_GENRES,
    HTTP_BACKOFF_BASE,
    HTTP_MAX_RETRIES,
    HTTP_TIMEOUT,
    MAX_BILLING_ORDER,
    MAX_CONCURRENCY,
    MIN_ACTOR_POPULARITY,
    MIN_MOVIE_POPULARITY,
    MIN_VOTE_COUNT,
    TMDB_API_KEY,
    TMDB_BASE_URL,
)
from .models import Actor, Movie

log = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None
_semaphore: asyncio.Semaphore | None = None
_client_lock: asyncio.Lock | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    return _semaphore


async def _get_client() -> httpx.AsyncClient:
    global _client, _client_lock
    if _client_lock is None:
        _client_lock = asyncio.Lock()
    async with _client_lock:
        if _client is None:
            if not TMDB_API_KEY:
                raise RuntimeError(
                    "TMDB_API_KEY is not set. Add it to .env or export it as an environment variable."
                )
            _client = httpx.AsyncClient(
                base_url=TMDB_BASE_URL,
                timeout=HTTP_TIMEOUT,
                params={"api_key": TMDB_API_KEY},
                headers={"Accept": "application/json"},
            )
        return _client


async def _request(path: str, params: dict | None = None) -> dict:
    client = await _get_client()
    sem = _get_semaphore()
    last_exc: Exception | None = None

    for attempt in range(HTTP_MAX_RETRIES + 1):
        try:
            async with sem:
                resp = await client.get(path, params=params)
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last_exc = e
            if attempt >= HTTP_MAX_RETRIES:
                raise
            await asyncio.sleep(_backoff(attempt))
            continue

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", "1"))
            log.warning("TMDB rate-limited; sleeping %.1fs (attempt %d)", retry_after, attempt)
            await asyncio.sleep(retry_after + random.uniform(0.0, 0.5))
            continue

        if 500 <= resp.status_code < 600:
            if attempt >= HTTP_MAX_RETRIES:
                resp.raise_for_status()
            await asyncio.sleep(_backoff(attempt))
            continue

        if resp.status_code == 404:
            return {}

        resp.raise_for_status()
        return resp.json()

    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"Exhausted retries for {path}")


def _backoff(attempt: int) -> float:
    return HTTP_BACKOFF_BASE * (2**attempt) + random.uniform(0.0, 0.25)


def _parse_year(release_date: str | None) -> int | None:
    if not release_date or len(release_date) < 4:
        return None
    try:
        return int(release_date[:4])
    except ValueError:
        return None


async def search_actor(name: str) -> Actor | None:
    cached = await cache.get_actor_by_name(name)
    if cached is not None:
        return cached

    data = await _request("/search/person", params={"query": name, "include_adult": "false"})
    results = data.get("results", []) if data else []

    best: Actor | None = None
    for r in results:
        if r.get("known_for_department") and r["known_for_department"] != "Acting":
            continue
        popularity = float(r.get("popularity", 0.0))
        if popularity < MIN_ACTOR_POPULARITY:
            continue
        best = Actor(
            id=r["id"],
            name=r["name"],
            popularity=popularity,
            profile_path=r.get("profile_path"),
        )
        break

    await cache.set_actor_by_name(name, best)
    return best


async def search_actors_multi(name: str, limit: int = 8) -> list[Actor]:
    name = name.strip()
    if not name:
        return []

    cached = await cache.get_actor_search(name)
    if cached is not None:
        return cached[:limit]

    data = await _request("/search/person", params={"query": name, "include_adult": "false"})
    results = data.get("results", []) if data else []

    out: list[Actor] = []
    for r in results:
        if r.get("known_for_department") and r["known_for_department"] != "Acting":
            continue
        popularity = float(r.get("popularity", 0.0))
        out.append(
            Actor(
                id=r["id"],
                name=r["name"],
                popularity=popularity,
                profile_path=r.get("profile_path"),
            )
        )
        if len(out) >= limit:
            break

    await cache.set_actor_search(name, out)
    return out


async def get_actor_by_id(actor_id: int) -> Actor | None:
    cached = await cache.get_actor_by_id(actor_id)
    if cached is not None:
        return cached

    data = await _request(f"/person/{actor_id}")
    if not data or not data.get("id"):
        return None
    actor = Actor(
        id=data["id"],
        name=data.get("name", ""),
        popularity=float(data.get("popularity", 0.0)),
        profile_path=data.get("profile_path"),
    )
    await cache.set_actor(actor)
    return actor


async def get_actor_movies(actor_id: int) -> list[Movie]:
    cached = await cache.get_actor_movies(actor_id)
    if cached is not None:
        return [m for m in cached if m.id != 0]

    data = await _request(f"/person/{actor_id}/movie_credits")
    cast = data.get("cast", []) if data else []

    movies: list[Movie] = []
    seen: set[int] = set()
    for c in cast:
        movie_id = c.get("id")
        if movie_id is None or movie_id in seen:
            continue
        if c.get("order") is not None and c["order"] >= MAX_BILLING_ORDER:
            continue
        vote_count = int(c.get("vote_count", 0) or 0)
        popularity = float(c.get("popularity", 0.0) or 0.0)
        if vote_count < MIN_VOTE_COUNT:
            continue
        if popularity < MIN_MOVIE_POPULARITY:
            continue
        genre_ids = tuple(int(g) for g in (c.get("genre_ids") or ()))
        if EXCLUDED_GENRES.intersection(genre_ids):
            continue
        seen.add(movie_id)
        movies.append(
            Movie(
                id=movie_id,
                title=c.get("title") or c.get("original_title") or "",
                year=_parse_year(c.get("release_date")),
                popularity=popularity,
                genre_ids=genre_ids,
                poster_path=c.get("poster_path"),
            )
        )

    await cache.set_actor_movies(actor_id, movies)
    return movies


async def get_movie_cast(movie_id: int) -> list[tuple[Actor, int]]:
    cached = await cache.get_movie_cast(movie_id)
    if cached is not None:
        return [(a, o) for (a, o) in cached if a.id != 0]

    data = await _request(f"/movie/{movie_id}/credits")
    cast_raw = data.get("cast", []) if data else []

    out: list[tuple[Actor, int]] = []
    for c in cast_raw:
        actor_id = c.get("id")
        if actor_id is None:
            continue
        order = c.get("order")
        if order is None or order >= MAX_BILLING_ORDER:
            continue
        popularity = float(c.get("popularity", 0.0) or 0.0)
        if popularity < MIN_ACTOR_POPULARITY:
            continue
        actor = Actor(
            id=actor_id,
            name=c.get("name") or "",
            popularity=popularity,
            profile_path=c.get("profile_path"),
        )
        out.append((actor, order))

    await cache.set_movie_cast(movie_id, out)
    return out


async def get_movie_pt_title(movie_id: int) -> str | None:
    cached = await cache.get_movie_pt_title(movie_id)
    if cached:
        return cached

    data = await _request(f"/movie/{movie_id}", params={"language": "pt-BR"})
    if not data:
        return None
    title = data.get("title") or data.get("original_title")
    if title:
        await cache.set_movie_pt_title(movie_id, title)
    return title


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
