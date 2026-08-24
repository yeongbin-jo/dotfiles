#!/usr/bin/env python3
"""One status-line segment answering "is this session's loop actually moving?".

Usage: loop-status.py <session-id>

Detection needs no cooperation from the loop. A self-paced `/loop` records every iteration as a
`ScheduleWakeup` tool call in the session transcript — the one place the schedule is written to disk —
so the segment reads that: the last call's timestamp plus its `delaySeconds` is when the loop comes
back, and `stop: true` is the loop ending. Any session running `/loop` therefore lights up, including
ones that have never heard of this script.

Optional enrichment: if ~/.claude/loop-state/<session-id>.json exists and names a control note, the
segment shows the loop's own milestone and revision instead of a generic label.

    {"note": "/abs/path/to/control-note.md", "label": "channel"}

Three live states, because "idle between iterations" and "not running at all" are different facts:

    ⏵  driving   the session is working right now
    ⏱  idle      quiet, but a continuation is scheduled — shows ↻ when it returns
    ⏸  held      the control note says HOLD: blocked on a person, shown however old
    (nothing)    no scheduled continuation, or the deadline passed with nothing happening

Presence is the signal. A stopped loop shows nothing at all rather than a grey badge, so there is no
colour to interpret, and a dead schedule does not get to look alive.
"""
import calendar
import glob
import json
import os
import re
import sys
import time

C = lambda code, s: "\x1b[%sm%s\x1b[0m" % (code, s)
TAIL_BYTES = 262144          # the last ScheduleWakeup of an active loop sits at the end
DRIVING_WITHIN = 90          # transcript written this recently → the session is working
OVERDUE_GRACE = 180          # past the deadline by this much with no new call → not running


def age(seconds):
    seconds = max(0, int(seconds))
    if seconds < 90:
        return "%ds" % seconds
    if seconds < 5400:
        return "%dm" % (seconds // 60)
    return "%dh" % (seconds // 3600)


def transcript(session_id):
    hits = glob.glob(os.path.expanduser("~/.claude/projects/*/%s.jsonl" % session_id))
    return hits[0] if hits else None


def last_wakeup(path):
    """(scheduled_epoch, stopped) from the most recent ScheduleWakeup call, or None."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            fh.seek(max(0, size - TAIL_BYTES))
            tail = fh.read().decode("utf-8", "ignore")
    except Exception:
        return None
    for line in reversed(tail.split("\n")):
        if '"ScheduleWakeup"' not in line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue          # a truncated first line from the byte-offset read
        for block in (rec.get("message") or {}).get("content") or []:
            if not isinstance(block, dict) or block.get("name") != "ScheduleWakeup":
                continue
            args = block.get("input") or {}
            if args.get("stop"):
                return (0.0, True)
            try:
                # timegm, not mktime-minus-timezone: the transcript stamp is UTC and that
                # subtraction is off by an hour wherever DST applies.
                ts = calendar.timegm(time.strptime(rec["timestamp"][:19], "%Y-%m-%dT%H:%M:%S"))
                return (ts + float(args.get("delaySeconds") or 0), False)
            except Exception:
                return None
    return None


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


def enrichment(session_id):
    """(label, controller_state) from the optional control note."""
    path = os.path.join(os.path.expanduser("~/.claude/loop-state"), session_id + ".json")
    try:
        cfg = json.load(open(path))
        body = open(cfg["note"], encoding="utf-8").read()
    except Exception:
        return ("loop", None)
    state = (re.search(r"^- controllerState:\s*(\S+)", body, re.M) or [None, None])[1]
    rev = (re.search(r"^- stateRevision:\s*(\d+)", body, re.M) or [None, None])[1]
    label = active_milestone(body) or cfg.get("label") or "loop"
    return (label + (" r%s" % rev if rev else ""), state)


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        return
    sid = sys.argv[1].strip()
    label, state = enrichment(sid)

    # HOLD is shown however old: it is blocked on a person, and forgetting it is worse than
    # forgetting a parked loop. Deliberately NOT the branch colour — the two sit side by side.
    if state == "HOLD":
        path = transcript(sid)
        seen = time.time() - os.path.getmtime(path) if path else 0
        sys.stdout.write(C("38;5;214", "⏸ %s %s" % (label, age(seen))))
        return

    path = transcript(sid)
    if not path:
        return
    wake = last_wakeup(path)
    if not wake:
        return
    scheduled, stopped = wake
    if stopped:
        return

    now = time.time()
    if now > scheduled + OVERDUE_GRACE:
        return          # the deadline passed and nothing scheduled another: not running
    since = now - os.path.getmtime(path)
    if since <= DRIVING_WITHIN:
        sys.stdout.write(C("38;5;177", "⏵ %s %s" % (label, age(since))))
    else:
        sys.stdout.write(C("38;5;146", "⏱ %s ↻%s" % (label, age(scheduled - now))))


if __name__ == "__main__":
    main()
