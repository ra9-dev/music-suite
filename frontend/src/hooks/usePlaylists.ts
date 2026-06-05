/**
 * Hook: usePlaylists
 *
 * Fetches all Spotify playlists for the logged-in user.
 * Triggers on mount.
 *
 * Returns:
 *   playlists  — array of Playlist objects (empty while loading)
 *   loading    — true while the request is in-flight
 *   error      — error message string if the request failed, null otherwise
 */

import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { Playlist } from '../types';

interface PlaylistsState {
  playlists: Playlist[];
  loading: boolean;
  error: string | null;
}

export function usePlaylists(): PlaylistsState {
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient
      .get<{ playlists: Playlist[] }>('/api/playlists')
      .then((data) => setPlaylists(data.playlists))
      .catch((err) => setError(err.message ?? 'Failed to load playlists'))
      .finally(() => setLoading(false));
  }, []);

  return { playlists, loading, error };
}
