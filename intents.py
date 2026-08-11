import re
from datetime import datetime, timedelta
import dateutil.parser

def parse_relative_time(token):
    token = token.lower().strip()
    now = datetime.now()
    if token.startswith("in "):
        m = re.search(r"in\s+(\d+)\s*(minute|minutes|min|hour|hours|day|days)", token)
        if m:
            val = int(m.group(1))
            unit = m.group(2)
            if unit.startswith("min"):
                return now + timedelta(minutes=val)
            if unit.startswith("hour"):
                return now + timedelta(hours=val)
            if unit.startswith("day"):
                return now + timedelta(days=val)
    if token in ("today", "tonight"):
        return now
    if token == "tomorrow":
        return now + timedelta(days=1)
    try:
        return dateutil.parser.parse(token, fuzzy=True)
    except Exception:
        return None

def parse_intent(text, config=None):
    text = (text or "").strip().lower()
    if not text:
        return {"type": "unknown"}

    if any(w in text for w in ["exit", "quit", "shutdown"]):
        return {"type": "exit"}

    if text in ("help", "what can you do"):
        return {"type": "help"}

    if "what's next" in text or "whats next" in text or "next task" in text:
        return {"type": "next_task"}

    if "summarize" in text and ("day" in text or "work" in text):
        return {"type": "summary"}

    if "list" in text and "task" in text:
        return {"type": "list_tasks"}

    m = re.search(r"delete (task )?(\d+)", text)
    if m:
        return {"type": "delete_task", "task_id": int(m.group(2))}

    m = re.search(r"(mark|set) (task )?(\d+) (done|complete|completed)", text)
    if m:
        return {"type": "mark_done", "task_id": int(m.group(3))}

    # snooze (with or without task id — no id means "the one that just fired")
    m = re.search(r"snooze( (task )?(\d+))?( for)? ?(\d+)?\s*(minutes|minute|min|hours|hour)?", text)
    if m and "snooze" in text:
        tid = int(m.group(3)) if m.group(3) else None
        val = int(m.group(5)) if m.group(5) else 10
        unit = m.group(6) or "minutes"
        minutes = val * (60 if unit.startswith("hour") else 1)
        return {"type": "snooze", "task_id": tid, "minutes": minutes}

    # open website: "open github" / "open linkedin" / "open <site>"
    m = re.search(r"open (my )?([a-zA-Z0-9\.\- ]+)", text)
    if m and "task" not in text:
        return {"type": "open_site", "site": m.group(2).strip()}

    # play on youtube: "play <query> on youtube"
    m = re.search(r"play (.+?) on youtube", text)
    if m:
        return {"type": "play_youtube", "query": m.group(1).strip()}

    quick_prefix = (config or {}).get("quick_add_prefix", "quick")
    if quick_prefix and text.startswith(quick_prefix):
        text = text[len(quick_prefix):].strip()

    # recurring: "remind me to X every day at 9am" / "every week"
    m = re.search(r"(remind me to|remember to|add task|set reminder to)\s+(.*?)\s+every\s+(day|week)\s*(at\s+(.*))?$", text)
    if m:
        task_part = m.group(2).strip()
        freq = m.group(3)
        time_part = m.group(5).strip() if m.group(5) else "09:00"
        dt = parse_relative_time(time_part)
        if dt is None:
            try:
                dt = dateutil.parser.parse(time_part, fuzzy=True)
            except Exception:
                dt = datetime.now() + timedelta(minutes=1)
        return {
            "type": "create_task", "task": task_part,
            "time": dt.isoformat(), "recurring": freq
        }

    # normal one-off create
    m = re.search(r"(remind me to|remember to|add task|create reminder|set reminder to)\s+(.*)", text)
    if m:
        rest = m.group(2).strip()
        time_part = None
        task_part = rest
        if " at " in rest:
            parts = rest.rsplit(" at ", 1)
            task_part, time_part = parts[0].strip(), parts[1].strip()
        elif " on " in rest:
            parts = rest.rsplit(" on ", 1)
            task_part, time_part = parts[0].strip(), parts[1].strip()
        else:
            for kw in (" tomorrow", " today", " tonight", " in "):
                if kw in rest:
                    idx = rest.find(kw)
                    task_part = rest[:idx].strip()
                    time_part = rest[idx+1:].strip()
                    break

        if not time_part:
            return {"type": "unknown"}

        dt = parse_relative_time(time_part)
        if dt is None:
            try:
                dt = dateutil.parser.parse(time_part, fuzzy=True)
            except Exception:
                dt = None
        if dt is None:
            return {"type": "unknown"}

        return {"type": "create_task", "task": task_part, "time": dt.isoformat(), "recurring": None}

    return {"type": "unknown"}