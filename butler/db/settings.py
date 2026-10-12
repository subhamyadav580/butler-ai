"""Small key → JSON value store for settings changed at runtime (from the UI).

Lives in data/butler.db, so the web server and the Telegram bot (separate
processes) see the same values without a restart.
"""

import json
import time

from .sqlite import get_database

SETTINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,          -- JSON
    updated_at  REAL NOT NULL
);
"""


class SettingsRepo:
    def __init__(self, db):
        self.db = db
        db.apply_schema(SETTINGS_SCHEMA)

    def get(self, key, default=None):
        row = self.db.query_one("SELECT value FROM settings WHERE key = ?", (key,))
        return json.loads(row["value"]) if row else default

    def set(self, key, value):
        self.db.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, json.dumps(value), time.time()),
        )


_settings = None


def get_settings():
    global _settings
    if _settings is None:
        _settings = SettingsRepo(get_database())
    return _settings
