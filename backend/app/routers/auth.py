"""
Authentication routes — Spotify PKCE OAuth 2.0 flow.

Why no cookies:
    The frontend (localhost:5173) and backend (127.0.0.1:8000) are on different
    origins. SameSite=Lax cookies — the browser default — are blocked on
    cross-origin fetch requests, so cookie-based sessions never work here.

    Instead, after a successful OAuth callback the backend:
      1. Creates a session entry in SessionStore keyed by a random session ID
      2. Redirects the browser to the frontend with ?sid=<session_id> in the URL

    The frontend reads ?sid= from the URL, saves it to localStorage, and sends it
    on every API request as:  Authorization: Bearer <session_id>

Flow:
    1.  GET /api/auth/login
        → Generates PKCE verifier + challenge + state
        → Stores verifier + state in httpOnly cookies (same origin as callback)
        → Redirects browser to accounts.spotify.com/authorize

    2.  Spotify redirects to GET /api/auth/callback?code=...&state=...
        → Validates state query param against the oauth_state cookie (CSRF)
        → Reads code_verifier from the oauth_verifier cookie
        → Exchanges code for tokens via Spotify token endpoint
        → Fetches user profile
        → Creates session in SessionStore
        → Redirects browser to {frontend_url}/playlists?sid=<session_id>

    3.  Frontend saves sid to localStorage, removes it from the URL
        → All API calls include  Authorization: Bearer <session_id>
"""

import logging
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.config import settings
from app.services.session_store import SessionData, session_store
from app.services.spotify import SpotifyService
from app.utils.pkce import generate_code_challenge, generate_code_verifier, generate_state

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

SPOTIFY_SCOPES = " ".join([
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-private",
    "playlist-modify-public",
    "user-read-private",
    "user-read-email",
    "user-library-read",    # read Liked Songs
    "user-library-modify",  # remove tracks from Liked Songs
])

# Maps state → code_verifier. Consumed on first use (replay protection).
# Server-side storage is used instead of cookies because the /login endpoint
# is navigated to directly (127.0.0.1:8000), and the SameSite cookie behaviour
# across the Spotify consent page redirect is unreliable in some browsers.
_pkce_store: dict[str, str] = {}


def _redirect_with_error(error: str) -> RedirectResponse:
    return RedirectResponse(f"{settings.frontend_url}/?error={error}")


@router.get("/login", summary="Initiate Spotify OAuth login")
async def login() -> RedirectResponse:
    """
    Start the PKCE authorization flow.
    Stores the code_verifier server-side (not in a cookie) to avoid
    SameSite/domain issues between the proxy and the direct callback URL.
    """
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    state = generate_state()

    log.info("login: generated state=%s", state[:8])

    params = urlencode({
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.redirect_uri,
        "scope": SPOTIFY_SCOPES,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "state": state,
        "show_dialog": "true",
    })

    _pkce_store[state] = verifier
    return RedirectResponse(f"{SPOTIFY_AUTH_URL}?{params}")


@router.get("/callback", summary="Spotify OAuth callback")
async def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """
    Spotify redirects here after the user approves (or denies) access.

    On success: creates a server-side session, redirects to the frontend
                with ?sid=<session_id> in the URL.
    On failure: redirects to the frontend with ?error=<reason>.
    """
    if error:
        log.warning("callback: Spotify returned error=%s", error)
        return _redirect_with_error(error)

    if not state:
        log.warning("callback: missing state param")
        return _redirect_with_error("state_mismatch")

    verifier = _pkce_store.pop(state, None)
    if not verifier:
        log.warning("callback: state not found in pkce_store (state=%s...)", state[:8])
        return _redirect_with_error("state_mismatch")

    # Exchange authorization code for tokens
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.redirect_uri,
                "client_id": settings.spotify_client_id,
                "code_verifier": verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        log.error("callback: token exchange failed — %s %s", resp.status_code, resp.text)
        return _redirect_with_error("token_exchange_failed")

    token_data = resp.json()

    # Fetch user profile
    try:
        spotify = SpotifyService(token_data["access_token"])
        user = await spotify.get_current_user()
    except Exception as exc:
        log.error("callback: failed to fetch Spotify profile — %s", exc)
        return _redirect_with_error("profile_fetch_failed")

    log.warning("callback: granted scopes=%s", token_data.get("scope", "<none>"))

    # Create server-side session
    session_id = session_store.create(SessionData(
        user_id=user.id,
        display_name=user.display_name,
        image_url=user.image_url,
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_at=time.time() + token_data["expires_in"],
    ))

    log.info("callback: session created for user_id=%s sid=%s...", user.id, session_id[:8])

    # Pass the session ID to the frontend via URL param.
    # The frontend saves it to localStorage and removes it from the URL.
    return RedirectResponse(f"{settings.frontend_url}/playlists?sid={session_id}")


@router.get("/me", summary="Get current authenticated user")
async def me(request: Request) -> dict:
    """
    Return the current user's profile.
    Reads the session ID from the Authorization: Bearer header.
    Returns 401 if the header is missing or the session is not found.
    """
    auth_header = request.headers.get("Authorization", "<none>")
    sid = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else None

    if not sid:
        log.warning("me: 401 — no Authorization header")
        raise HTTPException(status_code=401, detail="Not authenticated")

    data = session_store.get(sid)
    if not data:
        log.warning("me: 401 — sid not found in session_store (sid=%s...)", sid[:8])
        raise HTTPException(status_code=401, detail="Not authenticated")

    log.info("me: 200 — user_id=%s", data["user_id"])
    return {
        "id": data["user_id"],
        "display_name": data["display_name"],
        "image_url": data["image_url"],
    }


@router.post("/logout", summary="Log out")
async def logout(request: Request) -> dict:
    """Delete the server-side session."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        sid = auth[len("Bearer "):].strip()
        session_store.delete(sid)
        log.info("logout: session deleted sid=%s...", sid[:8])
    return {"ok": True}
