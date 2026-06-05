# music-suite — Backend

Python + FastAPI backend for the music-suite playlist management app.

## Stack

- **Python 3.13**
- **FastAPI** — web framework
- **uvicorn** — ASGI server
- **httpx** — async HTTP client for Spotify API calls
- **pandas** — duplicate detection (groupby on URI / ISRC)
- **rapidfuzz** — fast fuzzy string matching for Pass 3 detection
- **pydantic-settings** — config loading + validation
- **Starlette SessionMiddleware** — signed cookie sessions via `itsdangerous`

## Project layout

```
backend/
├── app/
│   ├── main.py           # FastAPI app, middleware, router mounts
│   ├── config.py         # Settings loaded from .env
│   ├── types.py          # Shared Pydantic models
│   ├── dependencies.py   # get_current_user(), get_access_token() FastAPI deps
│   ├── routers/
│   │   ├── auth.py       # /api/auth/*  — PKCE OAuth flow
│   │   ├── playlists.py  # /api/playlists/*
│   │   └── duplicates.py # /api/duplicates/*
│   ├── services/
│   │   ├── spotify.py    # Spotify API wrapper (paginated, token-refresh)
│   │   └── duplicates.py # Three-pass detection algorithm
│   └── utils/
│       ├── pkce.py       # PKCE code_verifier / code_challenge helpers
│       ├── normalize.py  # Text normalization for fuzzy matching
│       └── paginate.py   # Async generator for Spotify pagination
└── tests/
    └── test_duplicates.py
```

## Setup

```bash
# 1. Copy and fill in the env file
cp .env.example .env

# 2. Install dependencies
poetry install

# 3. Run the dev server
poetry run uvicorn app.main:app --reload --port 8000
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SPOTIFY_CLIENT_ID` | ✅ | From the Spotify Developer Dashboard |
| `SPOTIFY_CLIENT_SECRET` | ✅ | From the Spotify Developer Dashboard |
| `REDIRECT_URI` | ✅ | Must match what's registered on Spotify (`http://127.0.0.1:8000/api/auth/callback`) — use `127.0.0.1`, not `localhost` |
| `SESSION_SECRET` | ✅ | Long random string — `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FRONTEND_URL` | optional | Default: `http://localhost:5173` |
| `PORT` | optional | Default: `8000` |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/auth/login` | Redirect to Spotify authorization page |
| GET | `/api/auth/callback` | Handle Spotify callback, store tokens |
| GET | `/api/auth/me` | Return current user info (or 401) |
| POST | `/api/auth/logout` | Clear session |
| GET | `/api/playlists` | List all user playlists |
| GET | `/api/playlists/{id}/tracks` | Fetch all tracks with positions |
| POST | `/api/duplicates/detect` | Run duplicate detection on a track list |
| POST | `/api/duplicates/remove` | Remove specific positions from a playlist |
| GET | `/health` | Liveness check |

Interactive docs: http://127.0.0.1:8000/docs

## Running tests

```bash
poetry run pytest tests/ -v
```
