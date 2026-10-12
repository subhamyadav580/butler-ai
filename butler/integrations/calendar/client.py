import threading

from .auth import get_calendar_service
from .config import CALENDAR_ID


class Calendar:
    """Thin wrapper over the Google Calendar API (primary calendar)."""

    def __init__(self, interactive=False):
        self.interactive = interactive
        self._local = threading.local()

    @property
    def service(self):
        # One client per thread: httplib2 isn't thread-safe, and LangGraph
        # runs parallel tool calls in threads
        if getattr(self._local, "service", None) is None:
            self._local.service = get_calendar_service(interactive=self.interactive)
        return self._local.service

    def list_events(self, time_min, time_max, query=None, limit=20):
        params = {
            "calendarId": CALENDAR_ID,
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "singleEvents": True,          # expand recurring events
            "orderBy": "startTime",
            "maxResults": limit,
        }
        if query:
            params["q"] = query
        return self.service.events().list(**params).execute().get("items", [])

    def get_event(self, event_id):
        return self.service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()

    def create_event(self, body, send_updates="none", with_meet=False):
        return self.service.events().insert(
            calendarId=CALENDAR_ID,
            body=body,
            sendUpdates=send_updates,
            conferenceDataVersion=1 if with_meet else 0,
        ).execute()

    def update_event(self, event_id, patch, send_updates="none"):
        return self.service.events().patch(
            calendarId=CALENDAR_ID, eventId=event_id, body=patch, sendUpdates=send_updates
        ).execute()

    def delete_event(self, event_id, send_updates="none"):
        self.service.events().delete(
            calendarId=CALENDAR_ID, eventId=event_id, sendUpdates=send_updates
        ).execute()

    def profile(self):
        """The calendar's id (the account email) and time zone."""
        cal = self.service.events().list(calendarId=CALENDAR_ID, maxResults=1).execute()
        return {"calendar": cal.get("summary"), "timeZone": cal.get("timeZone")}
