"""
FastAPI dependencies shared across routers.

Auth mechanism:
    After OAuth login the backend issues a random session ID, which the frontend
    stores in localStorage and sends on every request as:

        Authorization: Bearer <session_id>

    These dependencies read that header and look up the session in SessionStore.
    This avoids cookie/SameSite issues that arise when the frontend and backend
    are on different origins (localhost:5173 vs 127.0.0.1:8000) in dev.

Usage in a route:
    @router.get("/example")
    async def example(
        user: SpotifyUser = Depends(get_current_user),
        access_token: str = Depends(get_access_token),
    ):
        ...
"""

import time

import httpx
from fastapi import HTTPException, Request, status

from app.config import settings
from app.services.session_store import session_store
from app.types import SpotifyUser

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


def _extract_session_id(request: Request) -> str | None:
    """Pull the session ID out of the Authorization: Bearer header."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        sid = auth[len("Bearer "):].strip()
        return sid or None
    return None


async def get_current_user(request: Request) -> SpotifyUser:
    """
    Resolve the authenticated Spotify user from the session store.

    Raises HTTP 401 if the Authorization header is missing or the
    session ID is not found in the store.
    """
    session_id = _extract_session_id(request)
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Please log in.",
        )

    data = session_store.get(session_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or expired. Please log in again.",
        )

    return SpotifyUser(
        id=data["user_id"],
        display_name=data["display_name"],
        image_url=data["image_url"],
    )


async def get_access_token(request: Request) -> str:
    """
    Return a valid Spotify access token, refreshing it silently if needed.

    Tokens expire after 1 hour. Refreshes proactively when fewer than
    60 seconds remain to avoid expiry mid-request.

    Raises:
        HTTP 401 if no session exists.
        HTTP 401 if the refresh token is rejected (user revoked access).
    """
    session_id = _extract_session_id(request)
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )

    data = session_store.get(session_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or expired. Please log in again.",
        )

    if time.time() > data["expires_at"] - 60:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SPOTIFY_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": data["refresh_token"],
                    "client_id": settings.spotify_client_id,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if resp.status_code != 200:
            session_store.delete(session_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please log in again.",
            )

        token_data = resp.json()
        updates: dict = {
            "access_token": token_data["access_token"],
            "expires_at": time.time() + token_data["expires_in"],
        }
        if "refresh_token" in token_data:
            updates["refresh_token"] = token_data["refresh_token"]
        session_store.update(session_id, updates)

        return token_data["access_token"]

    return data["access_token"]
