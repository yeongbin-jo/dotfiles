#!/usr/bin/env python3
"""One status-line segment answering "is this session's loop actually moving?".

Usage: loop-status.py <session-id>

State lives at ~/.claude/loop-state/<session-id>.json and is written by the loop that is running:

    {"note": "/abs/path/to/control-note.md",   # the loop's durable control state
     "label": "channel",                       # fallback name when no milestone is ACTIVE
     "visibleWithinSeconds": 600,              # after this long with no write, DRIVE is not moving
     "nextWakeAt": 1787400000}                 # optional: epoch seconds of a scheduled continuation

Scoped to ONE session on purpose. The first version keyed nothing and lived at a single global path,
so every other Claude Code session on the machine rendered this session's loop — measured, not
theorised: a status-line render arrived from session 3a8803a5 while the loop belonged to b765781e.

Three states, because "idle between iterations" and "not running at all" are different facts and the
first version showed them identically:

    ⏵  driving      the note was written moments ago; work is happening now
    ⏱  idle         nothing written lately, but a continuation is scheduled — still a live loop
    ⏸  held         blocked on a person; shown however old, because forgetting it is worse
    (nothing)       no pending wake and nothing written lately: the loop is not running

Presence is the signal. A stopped loop shows nothing at all rather than a grey badge, so there is no
colour to interpret. Prints nothing when the session has no state file, which is every session that
is not driving a loop.
"""
import json
import os
import re
import sys
import time

C = lambda code, s: "\x1b[%sm%s\x1b[0m" % (code, s)


def age(seconds):
    seconds = max(0, int(seconds))
    if seconds < 90:
        return "%ds" % seconds
    if seconds < 5400:
        return "%dm" % (seconds // 60)
    return "%dh" % (seconds // 3600)


def active_milestone(body):
    """The first milestone marked ACTIVE, by its leading token (M2b, M4, …).

    Line-by-line rather than one dotall regex: such a pattern happily spans from one numbered list
    into a `Status:` line belonging to something else, and the wrong milestone on screen is worse
    than none at all.
    """
    lines = body.splitlines()
    for i, line in enumerate(lines):
        head = re.match(r"^\s*\d+\.\s+(\S+)", line)
        if not head:
            continue
        for nxt in lines[i + 1:i + 4]:
            if re.match(r"^\s*-\s*Status:\s*ACTIVE\b", nxt):
                return head.group(1)
            if re.match(r"^\s*\d+\.\s", nxt):
                break
    return None


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        return
    path = os.path.join(os.path.expanduser("~/.claude/loop-state"), sys.argv[1].strip() + ".json")
    try:
        with open(path) as fh:
            cfg = json.load(fh)
        body = open(cfg["note"], encoding="utf-8").read()
        since = time.time() - os.path.getmtime(cfg["note"])
    except Exception:
        return

    state = (re.search(r"^- controllerState:\s*(\S+)", body, re.M) or [None, "?"])[1]
    rev = (re.search(r"^- stateRevision:\s*(\d+)", body, re.M) or [None, "?"])[1]
    where = active_milestone(body) or cfg.get("label") or "loop"

    fresh = since <= float(cfg.get("visibleWithinSeconds", 600))
    wake_in = float(cfg.get("nextWakeAt", 0)) - time.time()

    # Deliberately NOT the branch colour — the two sit side by side and a reader should never have to
    # work out which is which.
    if state == "HOLD":
        icon, col, tail = "⏸", "38;5;214", age(since)
    elif state == "DRIVE" and fresh:
        icon, col, tail = "⏵", "38;5;177", age(since)
    elif state == "DRIVE" and wake_in > 0:
        # Idle, but a continuation is scheduled: the loop is alive and this is the gap between
        # iterations, not a stop. Dimmer than driving, and it says when it comes back.
        icon, col, tail = "⏱", "38;5;146", "↻" + age(wake_in)
    else:
        return

    sys.stdout.write(C(col, "%s %s r%s %s" % (icon, where, rev, tail)))


if __name__ == "__main__":
    main()
