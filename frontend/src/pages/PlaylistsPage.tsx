/**
 * PlaylistsPage — shows all the user's Spotify playlists.
 *
 * Uses the usePlaylists hook to fetch playlists on mount.
 * Hands off to DuplicatesPage when the user clicks "Scan for Duplicates"
 * on a playlist card.
 */

import type { SpotifyUser } from '../types';
import { usePlaylists } from '../hooks/usePlaylists';
import { Header } from '../components/layout/Header';
import { LoadingSpinner } from '../components/layout/LoadingSpinner';
import { PlaylistGrid } from '../components/playlist/PlaylistGrid';
import styles from './PlaylistsPage.module.css';

interface Props {
  user: SpotifyUser;
}

export function PlaylistsPage({ user }: Props) {
  const { playlists, loading, error } = usePlaylists();

  return (
    <div className={styles.page}>
      <Header user={user} />

      <main className={styles.main}>
        <h2 className={styles.heading}>Your Playlists</h2>

        {loading && <LoadingSpinner message="Loading your playlists…" />}

        {error && (
          <div className={styles.error}>
            Failed to load playlists: {error}
          </div>
        )}

        {!loading && !error && playlists.length === 0 && (
          <p className={styles.empty}>No playlists found.</p>
        )}

        {!loading && !error && playlists.length > 0 && (
          <PlaylistGrid playlists={playlists} />
        )}
      </main>
    </div>
  );
}
