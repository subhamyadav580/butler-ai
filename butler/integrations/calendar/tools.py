from datetime import datetime, time, timedelta
from typing import Optional

from langchain_core.tools import tool
from langgraph.types import interrupt

from butler.config import local_tz

from .client import Calendar
from butler.utils.times import default_end, from_google, human, parse_when, to_google

MAX_DESCRIPTION_CHARS = 500

_calendar = None


def _client():
    # Share one client (one API connection per thread) across tool calls
    global _calendar
    if _calendar is None:
        _calendar = Calendar()
    return _calendar


def _compact(event):
    start, end = from_google(event["start"]), from_google(event["end"])
    return {
        "id": event["id"],
        "title": event.get("summary", "(no title)"),
        "start": human(start),
        "end": human(end),
        "all_day": "date" in event["start"],
        "location": event.get("location"),
        "description": (event.get("description") or "")[:MAX_DESCRIPTION_CHARS] or None,
        "attendees": [
            {"email": a["email"], "response": a.get("responseStatus")}
            for a in event.get("attendees", [])
        ] or None,
        "meet_link": event.get("hangoutLink"),
        "organizer_is_me": event.get("organizer", {}).get("self", False),
        "status": event.get("status"),
    }


def _summary(title, start, end, location=None, attendees=None, meet=False):
    lines = [f"Title: {title}", f"When: {human(start)} → {human(end)}"]
    if location:
        lines.append(f"Where: {location}")
    if meet:
        lines.append("Google Meet link: will be added")
    if attendees:
        lines.append(f"Guests: {', '.join(attendees)}")
        lines.append("⚠️ Google will email invitations to these guests.")
    return "\n".join(lines)


def _approve(question, tool_name, args, details):
    # Pause the graph for the user's Approve/Reject. On resume the tool runs
    # again from the top, so everything before this call must be read-only.
    answer = interrupt({
        "type": "confirm_action",
        "question": question,
        "tool": tool_name,
        "args": args,
        "details": details,
    })
    return bool((answer or {}).get("approved"))


REJECTED = "The user rejected this. Nothing was changed in the calendar. Ask what they would like instead."


def _slot(start, end):
    return {"start": human(start), "end": human(end),
            "minutes": int((end - start).total_seconds() // 60)}


# ----------------------------------------------------------------------
# Read
# ----------------------------------------------------------------------

@tool
def list_calendar_events(
    start: Optional[str] = None,
    end: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """List events on the user's Google Calendar, earliest first.

    Args:
        start: From this date or time ("2026-10-14" or "2026-10-14T09:00"),
            in the user's time zone. Defaults to now.
        end: Until this date or time. Defaults to 7 days after start. A date
            means the end of that day.
        query: Optional free-text search (title, description, location, guests).
        limit: Maximum events to return (1-50).
    """
    tz = local_tz()
    start_at = parse_when(start) if start else datetime.now(tz)
    if not isinstance(start_at, datetime):
        start_at = datetime.combine(start_at, time.min, tzinfo=tz)
    if end:
        end_at = parse_when(end)
        if not isinstance(end_at, datetime):
            end_at = datetime.combine(end_at, time.min, tzinfo=tz) + timedelta(days=1)
    else:
        end_at = start_at + timedelta(days=7)

    events = _client().list_events(start_at, end_at, query, max(1, min(limit, 50)))
    return [_compact(e) for e in events]


@tool
def get_calendar_event(event_id: str) -> dict:
    """Full details of one calendar event. Use an id from list_calendar_events."""
    return _compact(_client().get_event(event_id))


@tool
def find_free_time(
    start: str,
    end: str,
    duration_minutes: int = 30,
    day_start: str = "09:00",
    day_end: str = "18:00",
) -> list[dict]:
    """Find free slots in the user's calendar, within working hours.

    Args:
        start: First day to search ("2026-10-14").
        end: Last day to search, inclusive ("2026-10-16").
        duration_minutes: Minimum length of a free slot.
        day_start: Start of the working day, "HH:MM" local time.
        day_end: End of the working day, "HH:MM" local time.
    """
    tz = local_tz()
    first, last = parse_when(start[:10]), parse_when(end[:10])
    need = timedelta(minutes=max(5, duration_minutes))
    open_at, close_at = time.fromisoformat(day_start), time.fromisoformat(day_end)

    window_start = datetime.combine(first, time.min, tzinfo=tz)
    window_end = datetime.combine(last, time.min, tzinfo=tz) + timedelta(days=1)
    busy = []
    for event in _client().list_events(window_start, window_end, limit=250):
        if event.get("transparency") == "transparent":       # marked "free"
            continue
        me = next((a for a in event.get("attendees", []) if a.get("self")), None)
        if me and me.get("responseStatus") == "declined":
            continue
        s, e = from_google(event["start"]), from_google(event["end"])
        if not isinstance(s, datetime):                     # all-day event
            s = datetime.combine(s, time.min, tzinfo=tz)
            e = datetime.combine(e, time.min, tzinfo=tz)
        busy.append((s, e))
    busy.sort()

    slots, now, day = [], datetime.now(tz), first
    while day <= last and len(slots) < 20:
        cursor = max(datetime.combine(day, open_at, tzinfo=tz), now)
        close = datetime.combine(day, close_at, tzinfo=tz)
        for s, e in busy:                       # sorted by start
            if cursor >= close or s >= close:
                break
            if e <= cursor:
                continue
            if s - cursor >= need:              # gap before this event
                slots.append(_slot(cursor, s))
            cursor = max(cursor, e)
        if close - cursor >= need:              # gap after the last event
            slots.append(_slot(cursor, close))
        day += timedelta(days=1)
    return slots


# ----------------------------------------------------------------------
# Write (each asks the user to approve first)
# ----------------------------------------------------------------------

@tool
def create_calendar_event(
    title: str,
    start: str,
    end: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[list[str]] = None,
    add_meet_link: bool = False,
) -> dict:
    """Create an event on the user's Google Calendar. Asks the user to approve first.

    Args:
        title: Event title.
        start: "2026-10-14T15:00" for a timed event, or "2026-10-14" for all-day.
        end: Same format. Defaults to 1 hour after start (or the same day if all-day).
        description: Optional notes.
        location: Optional place or address.
        attendees: Optional guest EMAIL addresses. Google emails them an invitation.
        add_meet_link: Add a Google Meet video link.
    """
    start_at = parse_when(start)
    end_at = parse_when(end) if end else default_end(start_at)
    if not isinstance(start_at, datetime) and not isinstance(end_at, datetime) and end_at <= start_at:
        end_at = default_end(start_at)
    guests = [a.strip() for a in (attendees or []) if a.strip()]

    details = _summary(title, start_at, end_at, location, guests, add_meet_link)
    args = {"title": title, "start": start, "end": end, "attendees": guests}
    if not _approve("Add this event to your Google Calendar?", "create_calendar_event", args, details):
        return {"status": "rejected", "message": REJECTED}

    body = {"summary": title, "start": to_google(start_at), "end": to_google(end_at)}
    if description:
        body["description"] = description
    if location:
        body["location"] = location
    if guests:
        body["attendees"] = [{"email": g} for g in guests]
    if add_meet_link:
        body["conferenceData"] = {"createRequest": {
            "requestId": f"butler-{datetime.now().timestamp():.0f}",
            "conferenceSolutionKey": {"type": "hangoutsMeet"},
        }}

    event = _client().create_event(body, "all" if guests else "none", add_meet_link)
    return {"status": "created", "event": _compact(event)}


@tool
def update_calendar_event(
    event_id: str,
    title: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    add_attendees: Optional[list[str]] = None,
) -> dict:
    """Change an existing calendar event. Only the given fields change. Asks to approve first.

    Args:
        event_id: From list_calendar_events.
        title, description, location: New values.
        start, end: New times, same format as create_calendar_event. If only
            start is given, the event keeps its length.
        add_attendees: Guest emails to invite (Google emails them).
    """
    current = _client().get_event(event_id)
    old_start, old_end = from_google(current["start"]), from_google(current["end"])

    patch, changes = {}, []
    if title:
        patch["summary"] = title
        changes.append(f"Title: {current.get('summary')} → {title}")
    if start or end:
        new_start = parse_when(start) if start else old_start
        new_end = parse_when(end) if end else new_start + (old_end - old_start)
        patch["start"], patch["end"] = to_google(new_start), to_google(new_end)
        changes.append(f"When: was {human(old_start)}, now {human(new_start)} until {human(new_end)}")
    if description is not None:
        patch["description"] = description
        changes.append("Description: updated")
    if location is not None:
        patch["location"] = location
        changes.append(f"Where: {current.get('location') or '—'} → {location}")
    guests = [a.strip() for a in (add_attendees or []) if a.strip()]
    if guests:
        existing = current.get("attendees", [])
        patch["attendees"] = existing + [{"email": g} for g in guests]
        changes.append(f"New guests: {', '.join(guests)} (Google emails them)")
    if not patch:
        return {"status": "unchanged", "message": "Nothing to change was given."}

    has_guests = bool(patch.get("attendees") or current.get("attendees"))
    if has_guests:
        changes.append("⚠️ Guests will be emailed about this change.")
    details = f"Event: {current.get('summary')} ({human(old_start)})\n" + "\n".join(changes)
    if not _approve("Change this calendar event?", "update_calendar_event", {"event_id": event_id}, details):
        return {"status": "rejected", "message": REJECTED}

    event = _client().update_event(event_id, patch, "all" if has_guests else "none")
    return {"status": "updated", "event": _compact(event)}


@tool
def delete_calendar_event(event_id: str) -> dict:
    """Delete (cancel) a calendar event. Asks the user to approve first.

    Args:
        event_id: From list_calendar_events.
    """
    current = _client().get_event(event_id)
    start = from_google(current["start"])
    notify = bool(current.get("attendees")) and current.get("organizer", {}).get("self", False)

    details = f"Event: {current.get('summary', '(no title)')}\nWhen: {human(start)}"
    if notify:
        details += "\n⚠️ Guests will be emailed that it's cancelled."
    if not _approve("Delete this event from your Google Calendar?", "delete_calendar_event",
                    {"event_id": event_id}, details):
        return {"status": "rejected", "message": REJECTED}

    _client().delete_event(event_id, "all" if notify else "none")
    return {"status": "deleted", "title": current.get("summary")}


CALENDAR_TOOLS = [
    list_calendar_events,
    get_calendar_event,
    find_free_time,
    create_calendar_event,
    update_calendar_event,
    delete_calendar_event,
]
