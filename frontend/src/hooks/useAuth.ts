/**
 * Hook: useAuth
 *
 * Fetches the current user's profile from the backend on first render.
 * Used by App.tsx to decide whether to show the login page or the app.
 *
 * Returns:
 *   user       — SpotifyUser if logged in, null otherwise
 *   isLoggedIn — convenience boolean
 *   loading    — true while the initial /api/auth/me request is in-flight
 *
 * Why raw fetch instead of apiClient:
 *   A 401 from /api/auth/me simply means "not logged in yet" — it is the
 *   expected response on first visit. Using apiClient would trigger its
 *   global 401 → redirect-to-/ handler, causing an infinite reload loop.
 *   Here we handle 401 silently by setting user to null.
 */

import { useEffect, useState } from 'react';
import { API_BASE, getAuthHeaders } from '../api/client';
import type { SpotifyUser } from '../types';

interface AuthState {
  user: SpotifyUser | null;
  isLoggedIn: boolean;
  loading: boolean;
}

export function useAuth(): AuthState {
  const [user, setUser] = useState<SpotifyUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Use raw fetch (not apiClient) so a 401 is treated as "not logged in"
    // rather than triggering the global redirect-to-login handler.
    fetch(`${API_BASE}/api/auth/me`, { headers: getAuthHeaders() })
      .then((res) => (res.ok ? res.json() : null))
      .then((data: SpotifyUser | null) => setUser(data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  return { user, isLoggedIn: user !== null, loading };
}
