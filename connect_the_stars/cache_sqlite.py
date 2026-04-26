import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

from .config import CACHE_DB_PATH, CACHE_TTL_DAYS
from .models import Actor, Movie

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()


async def init_db(path: str | None = None) -> None:
    global _conn
    db_path = path if path is not None else CACHE_DB_PATH
    _conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute("PRAGMA foreign_keys=ON")

    _conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS actors (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            popularity REAL NOT NULL,
            profile_path TEXT,
            fetched_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            year INTEGER,
            popularity REAL NOT NULL,
            genre_ids TEXT NOT NULL DEFAULT '[]',
            poster_path TEXT,
            title_pt TEXT
        );

        CREATE TABLE IF NOT EXISTS actor_movies (
            actor_id INTEGER NOT NULL,
            movie_id INTEGER NOT NULL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (actor_id, movie_id)
        );

        CREATE TABLE IF NOT EXISTS movie_cast (
            movie_id INTEGER NOT NULL,
            actor_id INTEGER NOT NULL,
            billing_order INTEGER NOT NULL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (movie_id, actor_id)
        );

        CREATE TABLE IF NOT EXISTS actor_name_lookup (
            query TEXT PRIMARY KEY,
            actor_id INTEGER,
            fetched_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS actor_search_lookup (
            query TEXT PRIMARY KEY,
            actor_ids TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_actor_movies_actor ON actor_movies(actor_id);
        CREATE INDEX IF NOT EXISTS idx_movie_cast_movie ON movie_cast(movie_id);
        """
    )

    # Idempotent column additions for legacy databases.
    _ensure_column("actors", "profile_path", "TEXT")
    _ensure_column("movies", "poster_path", "TEXT")
    _ensure_column("movies", "title_pt", "TEXT")


def _ensure_column(table: str, column: str, decl: str) -> None:
    assert _conn is not None
    cols = {row[1] for row in _conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        _conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def _get_conn() -> sqlite3.Connection:
    if _conn is None:
        raise RuntimeError("cache.init_db() must be called before any cache operation")
    return _conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_fresh(fetched_at: str) -> bool:
    try:
        ts = datetime.fromisoformat(fetched_at)
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - ts < timedelta(days=CACHE_TTL_DAYS)


async def get_actor_by_name(query: str) -> Actor | None:
    conn = _get_conn()
    with _lock:
        row = conn.execute(
            """
            SELECT a.id, a.name, a.popularity, a.profile_path, l.fetched_at
            FROM actor_name_lookup l
            LEFT JOIN actors a ON a.id = l.actor_id
            WHERE l.query = ?
            """,
            (query.lower().strip(),),
        ).fetchone()
    if row is None:
        return None
    actor_id, name, popularity, profile_path, fetched_at = row
    if not _is_fresh(fetched_at):
        return None
    if actor_id is None:
        return None
    return Actor(id=actor_id, name=name, popularity=popularity, profile_path=profile_path)


async def set_actor_by_name(query: str, actor: Actor | None) -> None:
    conn = _get_conn()
    now = _now_iso()
    with _lock:
        if actor is not None:
            conn.execute(
                "INSERT OR REPLACE INTO actors (id, name, popularity, profile_path, fetched_at) VALUES (?, ?, ?, ?, ?)",
                (actor.id, actor.name, actor.popularity, actor.profile_path, now),
            )
        conn.execute(
            "INSERT OR REPLACE INTO actor_name_lookup (query, actor_id, fetched_at) VALUES (?, ?, ?)",
            (query.lower().strip(), actor.id if actor else None, now),
        )


async def set_actor(actor: Actor) -> None:
    conn = _get_conn()
    with _lock:
        conn.execute(
            "INSERT OR REPLACE INTO actors (id, name, popularity, profile_path, fetched_at) VALUES (?, ?, ?, ?, ?)",
            (actor.id, actor.name, actor.popularity, actor.profile_path, _now_iso()),
        )


async def get_actor_by_id(actor_id: int) -> Actor | None:
    conn = _get_conn()
    with _lock:
        row = conn.execute(
            "SELECT id, name, popularity, profile_path, fetched_at FROM actors WHERE id = ?",
            (actor_id,),
        ).fetchone()
    if row is None:
        return None
    if not _is_fresh(row[4]):
        return None
    return Actor(id=row[0], name=row[1], popularity=row[2], profile_path=row[3])


async def get_actor_search(query: str) -> list[Actor] | None:
    conn = _get_conn()
    with _lock:
        row = conn.execute(
            "SELECT actor_ids, fetched_at FROM actor_search_lookup WHERE query = ?",
            (query.lower().strip(),),
        ).fetchone()
        if row is None or not _is_fresh(row[1]):
            return None
        ids = json.loads(row[0])
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        rows = conn.execute(
            f"SELECT id, name, popularity, profile_path FROM actors WHERE id IN ({placeholders})",
            ids,
        ).fetchall()
    by_id = {r[0]: Actor(id=r[0], name=r[1], popularity=r[2], profile_path=r[3]) for r in rows}
    return [by_id[i] for i in ids if i in by_id]


async def set_actor_search(query: str, actors: list[Actor]) -> None:
    conn = _get_conn()
    now = _now_iso()
    with _lock:
        for a in actors:
            conn.execute(
                "INSERT OR REPLACE INTO actors (id, name, popularity, profile_path, fetched_at) VALUES (?, ?, ?, ?, ?)",
                (a.id, a.name, a.popularity, a.profile_path, now),
            )
        conn.execute(
            "INSERT OR REPLACE INTO actor_search_lookup (query, actor_ids, fetched_at) VALUES (?, ?, ?)",
            (query.lower().strip(), json.dumps([a.id for a in actors]), now),
        )


async def get_actor_movies(actor_id: int) -> list[Movie] | None:
    conn = _get_conn()
    with _lock:
        link_rows = conn.execute(
            "SELECT movie_id, fetched_at FROM actor_movies WHERE actor_id = ?",
            (actor_id,),
        ).fetchall()
        if not link_rows:
            return None
        if not all(_is_fresh(r[1]) for r in link_rows):
            return None
        movie_ids = [r[0] for r in link_rows]
        placeholders = ",".join("?" * len(movie_ids))
        movie_rows = conn.execute(
            f"SELECT id, title, year, popularity, genre_ids, poster_path, title_pt FROM movies WHERE id IN ({placeholders})",
            movie_ids,
        ).fetchall()
    return [
        Movie(
            id=r[0],
            title=r[1],
            year=r[2],
            popularity=r[3],
            genre_ids=tuple(json.loads(r[4])),
            poster_path=r[5],
            title_pt=r[6],
        )
        for r in movie_rows
    ]


async def set_actor_movies(actor_id: int, movies: list[Movie]) -> None:
    conn = _get_conn()
    now = _now_iso()
    with _lock:
        conn.execute("BEGIN")
        try:
            conn.execute("DELETE FROM actor_movies WHERE actor_id = ?", (actor_id,))
            for m in movies:
                conn.execute(
                    """
                    INSERT INTO movies (id, title, year, popularity, genre_ids, poster_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        title=excluded.title,
                        year=excluded.year,
                        popularity=excluded.popularity,
                        genre_ids=excluded.genre_ids,
                        poster_path=excluded.poster_path
                    """,
                    (m.id, m.title, m.year, m.popularity, json.dumps(list(m.genre_ids)), m.poster_path),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO actor_movies (actor_id, movie_id, fetched_at) VALUES (?, ?, ?)",
                    (actor_id, m.id, now),
                )
            if not movies:
                conn.execute(
                    "INSERT OR REPLACE INTO actor_movies (actor_id, movie_id, fetched_at) VALUES (?, ?, ?)",
                    (actor_id, 0, now),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO movies (id, title, year, popularity, genre_ids, poster_path) VALUES (0, '', NULL, 0.0, '[]', NULL)"
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


async def get_movie_cast(movie_id: int) -> list[tuple[Actor, int]] | None:
    conn = _get_conn()
    with _lock:
        rows = conn.execute(
            """
            SELECT mc.actor_id, mc.billing_order, a.name, a.popularity, a.profile_path, mc.fetched_at
            FROM movie_cast mc
            JOIN actors a ON a.id = mc.actor_id
            WHERE mc.movie_id = ?
            """,
            (movie_id,),
        ).fetchall()
        sentinel = conn.execute(
            "SELECT 1 FROM movie_cast WHERE movie_id = ? AND actor_id = 0",
            (movie_id,),
        ).fetchone()
    if not rows and sentinel is None:
        return None
    if rows and not all(_is_fresh(r[5]) for r in rows):
        return None
    return [
        (Actor(id=r[0], name=r[2], popularity=r[3], profile_path=r[4]), r[1])
        for r in rows
    ]


async def set_movie_cast(movie_id: int, cast: list[tuple[Actor, int]]) -> None:
    conn = _get_conn()
    now = _now_iso()
    with _lock:
        conn.execute("BEGIN")
        try:
            conn.execute("DELETE FROM movie_cast WHERE movie_id = ?", (movie_id,))
            for actor, billing_order in cast:
                conn.execute(
                    "INSERT OR REPLACE INTO actors (id, name, popularity, profile_path, fetched_at) VALUES (?, ?, ?, ?, ?)",
                    (actor.id, actor.name, actor.popularity, actor.profile_path, now),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO movie_cast (movie_id, actor_id, billing_order, fetched_at) VALUES (?, ?, ?, ?)",
                    (movie_id, actor.id, billing_order, now),
                )
            if not cast:
                conn.execute(
                    "INSERT OR REPLACE INTO movie_cast (movie_id, actor_id, billing_order, fetched_at) VALUES (?, 0, 0, ?)",
                    (movie_id, now),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO actors (id, name, popularity, profile_path, fetched_at) VALUES (0, '', 0.0, NULL, ?)",
                    (now,),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


async def get_movie_pt_title(movie_id: int) -> str | None:
    conn = _get_conn()
    with _lock:
        row = conn.execute(
            "SELECT title_pt FROM movies WHERE id = ?", (movie_id,)
        ).fetchone()
    if row is None:
        return None
    return row[0]


async def set_movie_pt_title(movie_id: int, title_pt: str | None) -> None:
    conn = _get_conn()
    with _lock:
        conn.execute(
            """
            INSERT INTO movies (id, title, year, popularity, genre_ids, poster_path, title_pt)
            VALUES (?, '', NULL, 0.0, '[]', NULL, ?)
            ON CONFLICT(id) DO UPDATE SET title_pt = excluded.title_pt
            """,
            (movie_id, title_pt),
        )


async def close() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
