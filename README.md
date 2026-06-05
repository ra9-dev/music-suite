# music-suite

A web app for managing Spotify playlists. Phase 1: **interactive duplicate removal**.

Future phases will add cross-service playlist migration (Apple Music, YouTube Music) and smart playlist splitting.

---

## Architecture

```
music-suite/
├── backend/    Python + FastAPI  (port 8000)
└── frontend/   React + Vite      (port 5173)
```

Both are independent repositories — the frontend proxies `/api/*` requests to the backend during development, so no CORS setup is needed.

---

## Quick start

### 1. Spotify Developer App

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. In the app settings, add this redirect URI: `http://127.0.0.1:8000/api/auth/callback`
   > ⚠️ Use `127.0.0.1`, not `localhost` — Spotify's OAuth rejects `localhost` as a redirect URI.
4. Copy your **Client ID** and **Client Secret**

### 2. Backend

```bash
cd backend
cp .env.example .env
# Fill in SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SESSION_SECRET in .env

poetry install
poetry run uvicorn app.main:app --reload --port 8000
```

The API will be live at http://127.0.0.1:8000. Visit http://127.0.0.1:8000/docs for the interactive Swagger UI.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be live at http://localhost:5173.

### Or run both at once (from the root):

```bash
make install   # first time only
make dev       # starts both servers
```

---

## How duplicate detection works

Three passes run in priority order. A track claimed by a higher-priority pass is excluded from lower ones.

| Pass | Method | What it catches |
|------|--------|-----------------|
| 1 | **URI equality** | Identical Spotify track URI added twice |
| 2 | **ISRC equality** | Same recording, different album edition (original vs. greatest hits, etc.) |
| 3 | **Fuzzy title + artist** | Same song but different versions: remasters, live recordings, deluxe editions, radio edits |

For fuzzy matching, both the title similarity (≥ 80%) and the first artist similarity (≥ 70%) must pass, which prevents short-title false positives like "Run" by two different artists matching.

---

## Running tests

```bash
cd backend
poetry run pytest tests/ -v
```

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, uvicorn |
| HTTP client | httpx (async) |
| Data processing | pandas |
| Fuzzy matching | rapidfuzz |
| Auth | PKCE Authorization Code Flow |
| Sessions | Starlette SessionMiddleware (signed cookie) |
| Frontend | React 18, Vite 5, TypeScript |
| Routing | react-router-dom v7 |
