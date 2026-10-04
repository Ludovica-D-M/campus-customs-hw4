"""Append-only audit trail for the agent loop.

Every agent run writes one `run` entry and one `tool_call` entry per tool it
used, to `output/audit_trail.json`. Entries share a `run_id` so a run and its
tool calls can be read back together.

The file stays a single valid JSON array, but is never rewritten: appending
truncates the trailing `]`, writes `,<entry>\n]`, and leaves every earlier byte
exactly where it was. Previous runs therefore survive a restart, and a crash
mid-append can at worst lose the closing bracket of the last entry rather than
the history before it.

What is deliberately *not* recorded: the customer's name or email, the full
text of an answer, and the full tool payloads. The trail is for seeing what the
agent did, not for keeping a copy of the shop's conversations.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HW4_DIR = Path(__file__).resolve().parent.parent
AUDIT_PATH = HW4_DIR / "output" / "audit_trail.json"

# Arguments and results are summaries, not copies.
MAX_FIELD = 220
MAX_MESSAGE = 160

_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def shorten(value: Any, limit: int = MAX_FIELD) -> str:
    """One-line, length-capped rendering of anything."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            text = str(value)
    else:
        text = str(value)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _append(entry: dict[str, Any]) -> None:
    """Add one entry without rewriting the entries already on disk."""
    blob = json.dumps(entry, ensure_ascii=False, default=str)
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)

        if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
            AUDIT_PATH.write_text(f"[\n{blob}\n]\n", encoding="utf-8")
            return

        with open(AUDIT_PATH, "r+", encoding="utf-8") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()

            # Walk back over the trailing whitespace to find the closing
            # bracket, then write from there. Everything before it is untouched.
            pos = size
            while pos > 0:
                pos -= 1
                handle.seek(pos)
                char = handle.read(1)
                if not char.isspace():
                    break

            if char != "]":
                # Not a shape we recognise (hand-edited, or a crash mid-write).
                # Start a fresh array rather than corrupting it further; the old
                # file is kept beside it so nothing is lost.
                handle.close()
                AUDIT_PATH.rename(AUDIT_PATH.with_suffix(".json.broken"))
                AUDIT_PATH.write_text(f"[\n{blob}\n]\n", encoding="utf-8")
                return

            handle.seek(pos)
            handle.write(f",\n{blob}\n]\n")
            handle.truncate()


def record_tool_call(run_id: str, tool: str, args: Any, result: Any) -> None:
    _append(
        {
            "timestamp": now(),
            "run_id": run_id,
            "kind": "tool_call",
            "tool": tool,
            "args": shorten(args),
            "result": shorten(result),
        }
    )


def record_run(
    run_id: str,
    *,
    message: str,
    stop_reason: str,
    tools_used: list[str],
    products_returned: int = 0,
    signed_in: bool = False,
    user_id: int | None = None,
    page_product: str | None = None,
    duration_ms: int | None = None,
    usage: Any = None,
    detail: str | None = None,
) -> None:
    """One entry per turn of conversation, written after the run finishes."""
    entry: dict[str, Any] = {
        "timestamp": now(),
        "run_id": run_id,
        "kind": "run",
        "message": shorten(message, MAX_MESSAGE),
        "signed_in": signed_in,
        "user_id": user_id,
        "page_product": page_product,
        "tool_calls": len(tools_used),
        "tools_used": tools_used,
        "products_returned": products_returned,
        "stop_reason": stop_reason,
    }
    if duration_ms is not None:
        entry["duration_ms"] = duration_ms
    if usage is not None:
        entry["usage"] = shorten(usage, 160)
    if detail:
        entry["detail"] = shorten(detail, 160)
    _append(entry)


def read_entries() -> list[dict[str, Any]]:
    """The trail so far. Used by the tests and for inspection."""
    if not AUDIT_PATH.exists():
        return []
    try:
        return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
