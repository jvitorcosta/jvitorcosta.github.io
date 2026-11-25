from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Song:
    title: str
    artist: str
    cover: str
    url: str
    playing: bool


@dataclass(frozen=True)
class Film:
    title: str
    year: str
    rating: float | None
    liked: bool
    watched: str  # ISO date
    review: str
    poster: str
    url: str


@dataclass(frozen=True)
class Book:
    title: str
    author: str
    cover: str
    url: str
    page: int | None
    pages: int | None
    finished: bool = False


@dataclass(frozen=True)
class Anime:
    title: str
    cover: str
    url: str
    watching: bool  # else the latest one finished
    episode: int
    episodes: int  # 0 while unknown (still airing)
    score: int | None
    date: str  # ISO date of the last list update


@dataclass(frozen=True)
class Activity:
    sport: str
    emoji: str
    title: str
    distance_km: float | None
    moving_min: int
    detail: str
    date: str
    url: str


@dataclass(frozen=True)
class AboutFact:
    id: str
    source: str
    text: str


@dataclass(frozen=True)
class Repo:
    name: str
    description: str
    url: str
    homepage: str
    pushed: str


@dataclass(frozen=True)
class LiveData:
    song: Song | None
    film: Film | None
    book: Book | None
    activity: Activity | None
    anime: Anime | None = None


def to_dict(obj: Any) -> dict:
    return asdict(obj)


def from_dict(cls: type[T], d: dict) -> T:
    return cls(**{f.name: d[f.name] for f in fields(cls) if f.name in d})
