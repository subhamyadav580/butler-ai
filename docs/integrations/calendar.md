# Google Calendar

Butler can read your **primary Google Calendar**, find free time, and **add, move or cancel events**. Every change asks you to **Approve** first.

## What you can ask

```
What's on my calendar tomorrow?
When is my next meeting with Ankit?
Am I free on Friday afternoon?
Find me a free hour on Wednesday or Thursday
Block 30 minutes for a call on Friday at 4 pm             ← asks you to Approve
Add "Dentist" next Tuesday 10:30 at Apollo Clinic           ← asks you to Approve
Set up a 1-hour meeting with ankit@example.com tomorrow at 3 with a Meet link
Move my 3 pm meeting to 5 pm                                ← asks you to Approve
Cancel tomorrow's standup                                   ← asks you to Approve
```

| Tool | Does | Asks first? |
|---|---|---|
| `list_calendar_events` | Events in a date range, optionally matching a search | No |
| `get_calendar_event` | One event's full details | No |
| `find_free_time` | Free slots within working hours (09:00–18:00 by default) | No |
| `create_calendar_event` | New event: timed or all-day, location, guests, Google Meet link | ✅ |
| `update_calendar_event` | Change title, time, place or notes; invite more guests | ✅ |
| `delete_calendar_event` | Delete or cancel an event | ✅ |

## Setup

Calendar uses the **same Google OAuth client as Gmail**. If you've already set up Gmail, skip to step 2.

### 1. One-time Google setup

Follow the [Gmail guide](gmail.md#one-time-setup-create-your-google-oauth-client) to create a Google Cloud project, the consent screen (with yourself as a test user) and a **Desktop app** OAuth client saved as `secrets/google_client_secret.json`.

### 2. Enable the Calendar API

In the **same** Google Cloud project, open [Google Calendar API](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com) and click **Enable**.

### 3. Log in

```bash
python -m butler calendar-login
```

A browser opens:

1. Pick your Google account.
2. Click **Continue** on "Google hasn't verified this app" (it's your own app).
3. Allow **"See, edit, share, and permanently delete all the calendars you can access…"** for events.

The terminal prints `Google Calendar connected: you@gmail.com (time zone Asia/Kolkata)`, and the token is saved in `secrets/calendar_token.json`.

You can also click **Connect** next to Google Calendar on the web UI's **Integrations** page.

## How it handles…

**Time zones.** Butler uses your computer's time zone by default, so "tomorrow at 3" means 3 pm local time. If Butler runs somewhere else, such as a server in another region, set your zone in `.env`:

```
BUTLER_TIMEZONE=Asia/Kolkata
```

**Missing details.** With no end time, an event lasts 1 hour (30 minutes for a "call" or "quick" meeting). Butler doesn't ask for optional things like location or notes; it only asks if the date or start time is missing.

**Guests.** Adding a guest makes **Google email them an invitation**, and changing or cancelling an event you organise emails its guests too. The approval card warns you whenever that will happen. Butler only invites addresses you gave it. If you only give a name, it looks the address up in your Gmail or asks you; it never guesses.

**Which event to change.** "Move my 3 pm meeting" makes Butler look up events at that time first. If several match, it asks which one.

**Approvals.** The card shows exactly what will change:

```
⚠️ Add this event to your Google Calendar?
Title: Call with Ankit
When: Fri 16 Oct 2026, 4:00 PM → Fri 16 Oct 2026, 4:30 PM
Guests: ankit@example.com
⚠️ Google will email invitations to these guests.
                                             [Reject] [Approve]
```

Rejecting changes nothing.

## Good to know

- **Primary calendar only.** Events on other calendars (shared, subscribed or secondary) aren't read or changed yet.
- **Recurring events** are shown as individual occurrences. Changing one changes **that occurrence**, not the whole series.
- **Scope:** `calendar.events`, which allows reading and editing events but not calendar settings or sharing.
- **The login lasts about 7 days** while your Google app is in *Testing* mode, the same as Gmail. When Butler says the Calendar login has expired, run `python -m butler calendar-login` again, or publish the app (see the [Gmail guide](gmail.md#good-to-know)).
- **Disconnecting:** delete `secrets/calendar_token.json`. To revoke access completely, remove **Butler** at [myaccount.google.com/permissions](https://myaccount.google.com/permissions).
- **Where the code lives:** [`butler/integrations/calendar/`](../../butler/integrations/calendar/)
