from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, TypeVar

from homepage.model import from_dict, to_dict

T = TypeVar("T")


def load_state(path: Path) -> dict[str, dict]:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:  # a broken file must never fail the job
        print(f"::warning::state file unreadable, starting empty: {exc}", file=sys.stderr)
        return {}
    if not isinstance(state, dict):
        print("::warning::state file is not a JSON object, starting empty", file=sys.stderr)
        return {}
    return state


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
    print(f"::warning::{name} not updated: {reason}", file=sys.stderr)
    stored = state.get(name)
    if stored is None:
        return None
    try:  # schema drift or a hand edit must not fail the job either
        if isinstance(stored, list):
            return [from_dict(cls, d) for d in stored]
        return from_dict(cls, stored)
    except Exception as exc:
        print(f"::warning::{name} stored value unreadable: {str(exc) or type(exc).__name__}",
              file=sys.stderr)
        return None
