# music-suite — Claude Context

## What this project is

A full-stack web app for Spotify playlist management.
**Phase 1 (current):** Interactive duplicate removal from any playlist, including Liked Songs.
**Future phases:** Cross-service migration (Apple Music, YouTube Music), smart playlist splitting.

---

## Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.13 + FastAPI + uvicorn |
| HTTP client | httpx (async) |
| Data / duplicate detection | pandas + rapidfuzz |
| Auth | Spotify PKCE OAuth 2.0 |
| Session | Server-side dict (`SessionStore`) + `Authorization: Bearer` header |
| Frontend | React 18 + Vite 5 + TypeScript |
| Routing | react-router-dom v7 |
| Styles | CSS Modules (no UI library) |

---

## Running the project

```bash
# First time
make install

# Both servers
make dev        # backend on 127.0.0.1:8000, frontend on localhost:5173

# Backend only
make dev-backend

# Tests
make test
```

Backend interactive docs: http://127.0.0.1:8000/docs

---

## Critical architecture decisions

### Why 127.0.0.1 instead of localhost
Spotify's OAuth rejects `localhost` as a redirect URI. Use `http://127.0.0.1:8000/api/auth/callback` in the Spotify Developer Dashboard.

### Why Bearer token instead of cookies
The frontend (`localhost:5173`) and backend (`127.0.0.1:8000`) are different origins.
`SameSite=Lax` cookies (browser default) are blocked on cross-origin fetch requests, so cookie-based sessions silently fail — `cookie=<none>` on every request.

**How it works instead:**
1. After OAuth, backend creates a session in `SessionStore` (in-memory dict)
2. Redirects browser to `localhost:5173/playlists?sid=<session_id>`
3. `App.tsx` reads `?sid=`, saves to `localStorage`, cleans the URL
4. All API calls include `Authorization: Bearer <session_id>` header
5. Backend reads the header and looks up the session

### Why PKCE state is stored server-side (`_pkce_store`)
The `/login` endpoint is called via the browser navigating to `127.0.0.1:8000` directly. If it went through any proxy, cookies set during login wouldn't be sent on the Spotify callback (different origin). Storing `state → verifier` in a server-side dict avoids this entirely.

### Why no Vite proxy
Previously the project used the Vite proxy (`/api → 127.0.0.1:8000`), but cookies set by the direct Spotify callback (`127.0.0.1:8000`) weren't sent on proxied requests (`localhost:5173`). The proxy is removed; all API calls go directly to `127.0.0.1:8000`.

### Liked Songs
Not a real Spotify playlist — lives at `GET /me/tracks`. Uses sentinel ID `"liked_songs"`.
Removal uses `DELETE /me/library?uris=...` with Spotify URIs (not IDs), batched at 40/request.
Injected as the first item in the playlists list on every fetch.

---

## Project structure

```
music-suite/
├── backend/
│   └── app/
│       ├── main.py              # FastAPI app + CORS middleware
│       ├── config.py            # pydantic-settings (reads .env)
│       ├── types.py             # Pydantic models
│       ├── dependencies.py      # get_current_user(), get_access_token()
│       ├── routers/
│       │   ├── auth.py          # PKCE OAuth + session management
│       │   ├── playlists.py     # List playlists, fetch tracks
│       │   └── duplicates.py    # Detect + remove (supports dry_run)
│       ├── services/
│       │   ├── spotify.py       # Spotify API wrapper (httpx, paginated)
│       │   ├── duplicates.py    # 3-pass detection: URI → ISRC → fuzzy
│       │   └── session_store.py # In-memory session dict
│       └── utils/
│           ├── pkce.py          # code_verifier + code_challenge
│           ├── normalize.py     # Strip remaster/live/feat for fuzzy matching
│           └── paginate.py      # Async generator for Spotify pagination
├── frontend/
│   └── src/
│       ├── api/client.ts        # fetch wrapper; adds Authorization header
│       ├── hooks/               # useAuth, usePlaylists, useDuplicates
│       ├── pages/               # LoginPage, PlaylistsPage, DuplicatesPage, SuccessPage
│       └── components/          # layout/, playlist/, duplicates/
└── tests/
    ├── test_duplicates.py       # Unit tests for detection algorithm (16 tests)
    └── test_routes.py           # Route tests with mocked Spotify (11 tests)
```

---

## Testing

### Run all tests
```bash
cd backend && poetry run pytest tests/ -v
```

### Test without touching real Spotify playlists
Add `?dry_run=true` to the remove endpoint:
```bash
curl -X POST "http://127.0.0.1:8000/api/duplicates/remove?dry_run=true" \
  -H "Authorization: Bearer <sid>" \
  -H "Content-Type: application/json" \
  -d '{"playlist_id":"...", "removals":[...]}'
```
Returns `{ "dry_run": true, "removed_count": N, ... }` — Spotify is never called.

### Route tests (mocked Spotify)
`tests/test_routes.py` uses `unittest.mock.AsyncMock` to patch `SpotifyService` methods and FastAPI dependency overrides to skip real auth. All 27 tests run offline.

---

## UI testing (recommended setup)

### Component / hook tests — Vitest + React Testing Library
```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/user-event @testing-library/jest-dom jsdom
```
Good for: testing hooks (`useDuplicates` state machine), component rendering, user interactions.

### API mocking in frontend tests — MSW (Mock Service Worker)
```bash
npm install -D msw
```
Intercepts `fetch` calls in tests and returns fixture data. Lets you test the full component tree without a running backend.

### End-to-end tests — Playwright
```bash
npm install -D @playwright/test
npx playwright install
```
Good for: testing the full login → scan → review → remove flow in a real browser.
Pair with a dedicated Spotify test account and test playlist to avoid touching real data.

---

## Environment variables

### Backend (`backend/.env`)
```
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
REDIRECT_URI=http://127.0.0.1:8000/api/auth/callback
SESSION_SECRET=<32-byte hex — python -c "import secrets; print(secrets.token_hex(32))">
FRONTEND_URL=http://localhost:5173
```

### Frontend (`frontend/.env`, optional)
```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## Common issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `state_mismatch` after Spotify login | PKCE state expired or was replayed | Log out and log in again |
| `401` on all `/api/auth/me` calls | `?sid=` not captured from URL, or localStorage cleared | Check App.tsx useEffect runs before useAuth; inspect localStorage |
| `403` fetching playlist tracks | Spotify `fields` filter rejected for this playlist type | Already fixed — fields param removed |
| `KeyError: 'tracks'` on playlist list | Podcast/non-music item in playlist response | Already fixed — uses `.get()` |
| `int_from_float` Pydantic error | `fuzz.ratio()` returns float, `fuzzy_score` typed as `int` | Already fixed — `round()` applied |
| New OAuth scopes not working | Existing session doesn't have new scopes | Log out and log in again to re-consent |
