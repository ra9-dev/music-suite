/**
 * App — root component.
 *
 * On startup, calls GET /api/auth/me to determine whether the user is
 * logged in. While checking, shows a full-screen spinner.
 *
 * Routing:
 *   /                          → LoginPage (always accessible)
 *   /playlists                 → PlaylistsPage (requires auth)
 *   /playlists/:id/duplicates  → DuplicatesPage (requires auth)
 *   /success                   → SuccessPage (requires auth)
 *   *                          → redirect to /
 *
 * AuthGuard protects all authenticated routes — if the user isn't logged in,
 * they're redirected to /.
 */

import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import type { ReactNode } from 'react';
import { SID_KEY } from './api/client';
import { useAuth } from './hooks/useAuth';
import { LoginPage } from './pages/LoginPage';
import { PlaylistsPage } from './pages/PlaylistsPage';
import { DuplicatesPage } from './pages/DuplicatesPage';
import { SuccessPage } from './pages/SuccessPage';
import { LoadingSpinner } from './components/layout/LoadingSpinner';
import type { SpotifyUser } from './types';

interface AuthGuardProps {
  user: SpotifyUser | null;
  children: ReactNode;
}

/** Redirect unauthenticated users to the login page. */
function AuthGuard({ user, children }: AuthGuardProps) {
  if (user === null) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  // After the Spotify OAuth callback, the backend redirects here with
  // ?sid=<session_id> in the URL. Save it to localStorage immediately
  // (before useAuth runs) then remove it from the URL bar.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sid = params.get('sid');
    if (sid) {
      localStorage.setItem(SID_KEY, sid);
      params.delete('sid');
      const newSearch = params.toString();
      const cleanUrl = window.location.pathname + (newSearch ? `?${newSearch}` : '');
      window.history.replaceState({}, '', cleanUrl);
    }
  }, []);

  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingSpinner message="Starting up…" />;
  }

  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />

      <Route
        path="/playlists"
        element={
          <AuthGuard user={user}>
            <PlaylistsPage user={user!} />
          </AuthGuard>
        }
      />

      <Route
        path="/playlists/:playlistId/duplicates"
        element={
          <AuthGuard user={user}>
            <DuplicatesPage user={user!} />
          </AuthGuard>
        }
      />

      <Route
        path="/success"
        element={
          <AuthGuard user={user}>
            <SuccessPage />
          </AuthGuard>
        }
      />

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
