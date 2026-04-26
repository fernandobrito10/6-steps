"""
Cache facade. Picks `cache_kv` (Upstash Redis) when `KV_REST_API_URL` is set
in the environment (Vercel auto-injects this); falls back to `cache_sqlite`
locally.

Both backends expose the same async interface. tmdb.py only imports this module.
"""
import os

if os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL"):
    from .cache_kv import (  # noqa: F401
        close,
        get_actor_by_id,
        get_actor_by_name,
        get_actor_movies,
        get_actor_search,
        get_movie_cast,
        get_movie_pt_title,
        init_db,
        set_actor,
        set_actor_by_name,
        set_actor_movies,
        set_actor_search,
        set_movie_cast,
        set_movie_pt_title,
    )
    BACKEND = "kv"
else:
    from .cache_sqlite import (  # noqa: F401
        close,
        get_actor_by_id,
        get_actor_by_name,
        get_actor_movies,
        get_actor_search,
        get_movie_cast,
        get_movie_pt_title,
        init_db,
        set_actor,
        set_actor_by_name,
        set_actor_movies,
        set_actor_search,
        set_movie_cast,
        set_movie_pt_title,
    )
    BACKEND = "sqlite"
