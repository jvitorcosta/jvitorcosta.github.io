from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, TypeVar

from homepage.model import from_dict, to_dict

T = TypeVar("T")


def load_state(path: Path) -> dict[str, dict]:
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def refresh(
    name: str,
    fetch: Callable[[], T | list[T] | None],
    state: dict,
    cls: type[T],
) -> T | list[T] | None:
    try:
        result = fetch()
        reason = "no data" if result is None else None
    except Exception as exc:  # a failing source must never fail the job
        result, reason = None, str(exc)
    if reason is None:
        state[name] = (
            [to_dict(r) for r in result] if isinstance(result, list) else to_dict(result)
        )
        return result
    print(f"::warning::{name} not updated: {reason}")
    stored = state.get(name)
    if stored is None:
        return None
    if isinstance(stored, list):
        return [from_dict(cls, d) for d in stored]
    return from_dict(cls, stored)
