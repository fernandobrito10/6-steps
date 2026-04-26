import os
from pathlib import Path

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

MAX_DEPTH = 6
MAX_CONCURRENCY = 30
HTTP_TIMEOUT = 15.0
HTTP_MAX_RETRIES = 4
HTTP_BACKOFF_BASE = 0.5

MIN_VOTE_COUNT = 50
MIN_MOVIE_POPULARITY = 5.0
MIN_ACTOR_POPULARITY = 1.0
MAX_BILLING_ORDER = 15

EXCLUDED_GENRES = frozenset({99, 10767, 10763})

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DB_PATH = str(_PROJECT_ROOT / "connect_the_stars.db")
CACHE_TTL_DAYS = 7
