"""
Server-side session store.

Why this exists instead of a session cookie:
    The frontend (localhost:5173) and backend (127.0.0.1:8000) are on different
    origins. SameSite=Lax cookies are not sent on cross-origin fetch/XHR requests,
    so cookie-based sessions silently break in this dev setup.

    Instead, after a successful OAuth callback the backend:
      1. Creates a session entry here keyed by a random session ID
      2. Redirects the browser to the frontend with ?sid=<session_id> in the URL

    The frontend saves the session ID to localStorage and sends it on every API
    request as an Authorization: Bearer header. The backend reads it from there.

    In production (same origin / HTTPS) you would switch back to HttpOnly cookies
    with SameSite=None; Secure.
"""

import secrets
from typing import TypedDict


class SessionData(TypedDict):
    user_id: str
    display_name: str
    image_url: str | None
    access_token: str
    refresh_token: str
    expires_at: float   # Unix timestamp — when the access token expires


class SessionStore:
    def __init__(self) -> None:
        self._store: dict[str, SessionData] = {}

    def create(self, data: SessionData) -> str:
        """Store session data and return a new random session ID."""
        session_id = secrets.token_urlsafe(32)
        self._store[session_id] = data
        return session_id

    def get(self, session_id: str) -> SessionData | None:
        """Return session data, or None if the session doesn't exist."""
        return self._store.get(session_id)

    def update(self, session_id: str, changes: dict) -> None:
        """Merge changes into an existing session (e.g. refreshed tokens)."""
        if session_id in self._store:
            self._store[session_id].update(changes)  # type: ignore[typeddict-item]

    def delete(self, session_id: str) -> None:
        """Remove a session (logout)."""
        self._store.pop(session_id, None)


# Single shared instance imported by routers and dependencies
session_store = SessionStore()
