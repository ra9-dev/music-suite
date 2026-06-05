# music-suite — Frontend

React + Vite + TypeScript frontend for the music-suite playlist management app.

## Stack

- **React 18**
- **Vite 5** — build tool and dev server
- **TypeScript**
- **react-router-dom v7** — client-side routing
- **CSS Modules** — scoped component styles (no CSS framework)

## Project layout

```
frontend/src/
├── types/index.ts          # TypeScript types (mirrors backend Pydantic models)
├── api/client.ts           # Typed fetch wrapper; handles 401 → redirect to /
├── hooks/
│   ├── useAuth.ts          # Fetches current user; determines login state
│   ├── usePlaylists.ts     # Fetches all playlists
│   └── useDuplicates.ts    # Orchestrates the full detect → review → remove flow
├── pages/
│   ├── LoginPage.tsx       # Landing page with "Connect Spotify" button
│   ├── PlaylistsPage.tsx   # Grid of playlist cards
│   ├── DuplicatesPage.tsx  # Interactive duplicate review for one playlist
│   └── SuccessPage.tsx     # Confirmation after successful removal
├── components/
│   ├── layout/
│   │   ├── Header.tsx          # Top nav bar (user avatar + logout)
│   │   └── LoadingSpinner.tsx  # Centered spinner with optional message
│   ├── playlist/
│   │   ├── PlaylistCard.tsx    # Single playlist card with scan button
│   │   └── PlaylistGrid.tsx    # Responsive grid of PlaylistCards
│   └── duplicates/
│       ├── DuplicateList.tsx   # Scrollable list with sticky submit button
│       ├── DuplicateGroup.tsx  # One duplicate group card with skip option
│       ├── TrackRow.tsx        # Single track with radio button (keep/remove)
│       └── MatchBadge.tsx      # Coloured pill: "Exact Duplicate" / "Same Recording" / "Similar 87%"
└── App.tsx                 # Router + AuthGuard
```

## Setup

```bash
npm install
npm run dev
```

The app runs at http://localhost:5173. All API calls go directly to `http://127.0.0.1:8000` (the backend must be running).

## Page flow

```
/ (LoginPage)
  → "Connect Spotify" → http://127.0.0.1:8000/api/auth/login → Spotify → /playlists

/playlists (PlaylistsPage)
  → click "Scan for Duplicates" → /playlists/:id/duplicates

/playlists/:id/duplicates (DuplicatesPage)
  Phase 1: fetch tracks  GET /api/playlists/:id/tracks
  Phase 2: detect dupes  POST /api/duplicates/detect
  Phase 3: user reviews and picks which copy to keep
  Phase 4: submit        POST /api/duplicates/remove
  → /success

/success (SuccessPage)
  → "Back to Playlists"
```

## Key design decisions

- **No UI library** — all styles are hand-rolled CSS Modules with a dark Spotify-inspired theme
- **Direct backend URL** — all API calls go to `http://127.0.0.1:8000` directly (no Vite proxy). Spotify's OAuth callback sets the session cookie for `127.0.0.1`, so all requests must use the same origin to send that cookie. CORS on the backend allows `localhost:5173` with credentials.
- **useDuplicates hook** — all state for the three-phase review flow lives in one hook, making `DuplicatesPage` a pure render layer
- **Default decisions** — when groups are loaded, each group defaults to keeping the earliest-added track (lowest position), so the user can submit immediately if they agree with all defaults
