import argparse
import asyncio
import logging
import sys
import time

from dotenv import load_dotenv


def cli_entry() -> None:
    load_dotenv()
    asyncio.run(_async_main())


async def _async_main() -> None:
    parser = argparse.ArgumentParser(
        prog="connect_the_stars",
        description="Find the shortest movie-connection path between two actors via TMDB.",
    )
    parser.add_argument("actor_a", help="First actor (e.g. \"Tom Hanks\")")
    parser.add_argument("actor_b", help="Second actor (e.g. \"Lupita Nyong'o\")")
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum total path length (default: 6).",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print BFS progress.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    from . import bfs, cache, tmdb
    from .config import MAX_DEPTH

    max_depth = args.max_depth if args.max_depth is not None else MAX_DEPTH

    cache.init_db()

    try:
        if args.verbose:
            print(f"Searching for actors...", file=sys.stderr)

        actor_a, actor_b = await asyncio.gather(
            tmdb.search_actor(args.actor_a),
            tmdb.search_actor(args.actor_b),
        )

        if not actor_a:
            print(f"Actor not found: {args.actor_a!r}", file=sys.stderr)
            sys.exit(2)
        if not actor_b:
            print(f"Actor not found: {args.actor_b!r}", file=sys.stderr)
            sys.exit(2)

        if args.verbose:
            print(
                f"Found: {actor_a.name} (id={actor_a.id}) and {actor_b.name} (id={actor_b.id})",
                file=sys.stderr,
            )
            print(f"Running bidirectional BFS (max_depth={max_depth})...", file=sys.stderr)

        def progress(side: str, frontier_size: int, next_depth: int) -> None:
            print(
                f"  [side {side}] expanding {frontier_size} actor(s) -> depth {next_depth}",
                file=sys.stderr,
            )

        start = time.monotonic()
        path = await bfs.find_shortest_path(
            actor_a,
            actor_b,
            max_depth=max_depth,
            on_progress=progress if args.verbose else None,
        )
        elapsed = time.monotonic() - start

        if args.verbose:
            print(f"BFS finished in {elapsed:.1f}s", file=sys.stderr)

        if not path:
            print(
                f"No connection found between {actor_a.name} and {actor_b.name} within depth {max_depth}."
            )
            sys.exit(1)

        _print_path(path)

    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    finally:
        await tmdb.close()
        cache.close()


def _print_path(path: list) -> None:
    hops = max(0, len(path) - 1)
    print(f"\nFound a path with {hops} hop(s):\n")
    for i, step in enumerate(path):
        if i > 0 and step.via_movie is not None:
            year = f" ({step.via_movie.year})" if step.via_movie.year else ""
            print(f"  via [{step.via_movie.title}{year}]")
        print(f"{step.actor.name}")


if __name__ == "__main__":
    cli_entry()
