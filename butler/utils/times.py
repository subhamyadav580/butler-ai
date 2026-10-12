"""Date/time helpers shared by integrations (Calendar, Todos, …).

Parse the LLM's date strings in the user's time zone, format them for
people, and convert to/from Google Calendar's start/end fields.
"""

from datetime import date, datetime, timedelta

from butler.config import local_tz


def parse_when(value):
    """'2026-10-14' → date (all-day); '2026-10-14T15:30' → aware datetime.

    Times without an offset are taken as the user's local time.
    """
    value = value.strip()
    if len(value) == 10:
        return date.fromisoformat(value)
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=local_tz())
    return moment


def to_google(when):
    """date → {"date": ...}; datetime → {"dateTime": ...} for the Calendar API."""
    if isinstance(when, datetime):
        return {"dateTime": when.isoformat()}
    return {"date": when.isoformat()}


def from_google(field):
    """A Calendar API start/end field → date or aware datetime."""
    if "dateTime" in field:
        return datetime.fromisoformat(field["dateTime"].replace("Z", "+00:00")).astimezone(local_tz())
    return date.fromisoformat(field["date"])


def default_end(start):
    """1 hour for timed events; the same day for all-day events."""
    if isinstance(start, datetime):
        return start + timedelta(hours=1)
    return start + timedelta(days=1)   # Google's all-day end date is exclusive


def human(when):
    if isinstance(when, datetime):
        return when.strftime("%a %d %b %Y, %I:%M %p").replace(" 0", " ")
    return when.strftime("%a %d %b %Y") + " (all day)"


def day_bounds(day):
    tz = local_tz()
    start = datetime.combine(day, datetime.min.time(), tzinfo=tz)
    return start, start + timedelta(days=1)
