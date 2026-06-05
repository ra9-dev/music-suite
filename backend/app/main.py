"""
FastAPI application entry point.

Auth approach:
    Sessions are stored server-side in SessionStore (app/services/session_store.py).
    After OAuth the backend passes a session ID to the frontend via ?sid= in the
    redirect URL. The frontend saves it to localStorage and sends it as:
        Authorization: Bearer <session_id>
    This sidesteps the SameSite=Lax cookie restriction that blocks cross-origin
    requests between localhost:5173 (frontend) and 127.0.0.1:8000 (backend).

Run with:
    poetry run uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, duplicates, playlists

app = FastAPI(
    title="music-suite API",
    description="Spotify playlist management — duplicate removal and more.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# CORS — allows the Vite dev server to make credentialed cross-origin requests.
# allow_headers must include "Authorization" so the Bearer token is accepted.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(playlists.router)
app.include_router(duplicates.router)

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Quick liveness check — returns 200 if the server is up."""
    return {"status": "ok"}
