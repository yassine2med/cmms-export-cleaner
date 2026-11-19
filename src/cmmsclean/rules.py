"""Value normalizers. Each returns the clean value, or None when it cannot decide."""
from __future__ import annotations

import re
from datetime import datetime

DATE_FORMATS = (
    "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y",
    "%d-%b-%Y", "%d %b %Y", "%b %d, %Y", "%B %d, %Y", "%b %d %Y",
)
DAY_FIRST_FORMATS = ("%d/%m/%Y", "%d-%m-%Y")

STATUS_WORDS = {
    "Open": {"open", "new", "opened", "submitted", "requested", "unassigned"},
    "In Progress": {"in progress", "inprogress", "wip", "assigned", "started", "working", "in work"},
    "On Hold": {"on hold", "hold", "waiting", "waiting on parts", "pending", "deferred"},
    "Closed": {"closed", "complete", "completed", "done", "resolved", "finished"},
    "Cancelled": {"cancelled", "canceled", "void", "voided", "withdrawn"},
}
STATUS_LOOKUP = {word: label for label, words in STATUS_WORDS.items() for word in words}

PRIORITY_WORDS = {
    "Emergency": {"emergency", "p1", "1", "urgent", "critical", "asap"},
    "High": {"high", "p2", "2"},
    "Medium": {"medium", "med", "normal", "p3", "3", "routine"},
    "Low": {"low", "p4", "4", "minor", "when possible"},
}
PRIORITY_LOOKUP = {word: label for label, words in PRIORITY_WORDS.items() for word in words}

LOCATION_RE = re.compile(
    r"^(?P<kind>bldg|bld|building|annex)\.?[\s\-#_]*(?P<site>[a-z0-9]+)"
    r"(?:[\s,/\-#_]*(?:rm|room|suite|ste)?\.?[\s,/\-#_]*(?P<room>[a-z0-9][a-z0-9\-]*))?$",
    re.IGNORECASE,
)
SHORT_LOCATION_RE = re.compile(r"^(?P<site>[a-z])[\s\-/_]+(?P<room>\d[a-z0-9\-]*)$", re.IGNORECASE)


def _key(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower().replace("_", " "))


def normalize_date(text: str) -> str | None:
    """Return an ISO date (YYYY-MM-DD) or None.

    Slash dates are read month first (US). If the first number is above 12 the date
    is read day first. A trailing time such as '14:22' is dropped.
    """
    value = re.split(r"[T ](?=\d{1,2}:\d{2})", text.strip())[0].strip()
    if not value:
        return None
    for fmt in DATE_FORMATS + DAY_FIRST_FORMATS:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_status(text: str) -> str | None:
    """Map a status word to Open, In Progress, On Hold, Closed or Cancelled."""
    return STATUS_LOOKUP.get(_key(text))


def normalize_priority(text: str) -> str | None:
    """Map a priority word or code to Emergency, High, Medium or Low."""
    return PRIORITY_LOOKUP.get(_key(text))


def normalize_location(text: str) -> str | None:
    """Return 'Building A, Room 101' style text, or None when the pattern is unknown."""
    value = text.strip()
    match = LOCATION_RE.match(value)
    if match:
        kind = "Annex" if match["kind"].lower() == "annex" else "Building"
        site, room = match["site"].upper(), match["room"]
    else:
        match = SHORT_LOCATION_RE.match(value)
        if not match:
            return None
        kind, site, room = "Building", match["site"].upper(), match["room"]
    name = f"{kind} {site}"
    return f"{name}, Room {room.upper()}" if room else name


def clean_text(text: str) -> str:
    """Collapse runs of whitespace and trim."""
    return re.sub(r"\s+", " ", text).strip()
