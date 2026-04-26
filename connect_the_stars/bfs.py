import asyncio
import logging
from typing import Callable

from . import tmdb
from .config import MAX_DEPTH
from .models import Actor, Movie, Step

log = logging.getLogger(__name__)

# parent_map[actor_id] = (prev_actor_id_or_None, via_movie_or_None)
ParentMap = dict[int, tuple[int | None, Movie | None]]


async def find_shortest_path(
    actor_a: Actor,
    actor_b: Actor,
    max_depth: int = MAX_DEPTH,
    on_progress: Callable[[str, int, int], None] | None = None,
) -> list[Step] | None:
    if actor_a.id == actor_b.id:
        return [Step(actor=actor_a, via_movie=None)]

    parent_a: ParentMap = {actor_a.id: (None, None)}
    parent_b: ParentMap = {actor_b.id: (None, None)}
    actor_lookup: dict[int, Actor] = {actor_a.id: actor_a, actor_b.id: actor_b}
    depth_a: dict[int, int] = {actor_a.id: 0}
    depth_b: dict[int, int] = {actor_b.id: 0}

    frontier_a: list[Actor] = [actor_a]
    frontier_b: list[Actor] = [actor_b]

    while frontier_a and frontier_b:
        cur_a_depth = max(depth_a.values())
        cur_b_depth = max(depth_b.values())
        if cur_a_depth + cur_b_depth >= max_depth:
            log.debug(
                "Max depth reached (a=%d, b=%d, max=%d)", cur_a_depth, cur_b_depth, max_depth
            )
            return None

        if len(frontier_a) <= len(frontier_b):
            side = "A"
            frontier = frontier_a
            parent_map = parent_a
            depth_map = depth_a
            other_parent = parent_b
            other_depth = depth_b
        else:
            side = "B"
            frontier = frontier_b
            parent_map = parent_b
            depth_map = depth_b
            other_parent = parent_a
            other_depth = depth_a

        frontier_sorted = sorted(frontier, key=lambda a: a.popularity, reverse=True)
        next_depth = max(depth_map[a.id] for a in frontier_sorted) + 1

        if on_progress:
            on_progress(side, len(frontier_sorted), next_depth)

        next_frontier_dict = await _expand_level(
            frontier_sorted, parent_map, depth_map, actor_lookup, next_depth
        )

        meet_ids = [aid for aid in next_frontier_dict if aid in other_parent]
        if meet_ids:
            best = min(meet_ids, key=lambda aid: depth_map[aid] + other_depth[aid])
            log.debug(
                "Meet at actor_id=%d depth_a=%d depth_b=%d",
                best,
                depth_a.get(best, -1),
                depth_b.get(best, -1),
            )
            return _reconstruct(best, parent_a, parent_b, actor_lookup)

        next_frontier = list(next_frontier_dict.values())
        if side == "A":
            frontier_a = next_frontier
        else:
            frontier_b = next_frontier

    return None


async def _expand_level(
    frontier: list[Actor],
    parent_map: ParentMap,
    depth_map: dict[int, int],
    actor_lookup: dict[int, Actor],
    next_depth: int,
) -> dict[int, Actor]:
    movies_per_actor = await asyncio.gather(
        *(tmdb.get_actor_movies(a.id) for a in frontier)
    )

    all_movies: dict[int, Movie] = {}
    for movies in movies_per_actor:
        for m in movies:
            all_movies.setdefault(m.id, m)

    movie_ids = list(all_movies.keys())
    casts_list = await asyncio.gather(
        *(tmdb.get_movie_cast(mid) for mid in movie_ids)
    )
    cast_by_movie: dict[int, list[tuple[Actor, int]]] = dict(zip(movie_ids, casts_list))

    next_frontier: dict[int, Actor] = {}

    for actor, movies in zip(frontier, movies_per_actor):
        for movie in movies:
            for cast_actor, _order in cast_by_movie.get(movie.id, ()):
                if cast_actor.id == actor.id:
                    continue
                if cast_actor.id in parent_map:
                    continue
                parent_map[cast_actor.id] = (actor.id, movie)
                depth_map[cast_actor.id] = next_depth
                actor_lookup[cast_actor.id] = cast_actor
                next_frontier[cast_actor.id] = cast_actor

    return next_frontier


def _reconstruct(
    meet_id: int,
    parent_a: ParentMap,
    parent_b: ParentMap,
    actor_lookup: dict[int, Actor],
) -> list[Step]:
    a_steps: list[Step] = []
    cur: int | None = meet_id
    while cur is not None:
        prev, via = parent_a[cur]
        a_steps.append(Step(actor=actor_lookup[cur], via_movie=via))
        cur = prev
    a_steps.reverse()

    b_steps: list[Step] = []
    next_id, via_for_next = parent_b[meet_id]
    while next_id is not None:
        b_steps.append(Step(actor=actor_lookup[next_id], via_movie=via_for_next))
        prev, via_for_next = parent_b[next_id]
        next_id = prev

    return a_steps + b_steps
