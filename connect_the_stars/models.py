from dataclasses import dataclass, field


@dataclass(frozen=True)
class Actor:
    id: int
    name: str
    popularity: float
    profile_path: str | None = None


@dataclass(frozen=True)
class Movie:
    id: int
    title: str
    year: int | None
    popularity: float
    genre_ids: tuple[int, ...] = field(default_factory=tuple)
    poster_path: str | None = None
    title_pt: str | None = None


@dataclass
class Step:
    actor: Actor
    via_movie: Movie | None
