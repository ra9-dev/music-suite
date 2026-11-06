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

  const owned = playlists.filter((p) => p.is_owner);
  const following = playlists.filter((p) => !p.is_owner);

  return (
    <div className={styles.page}>
      <Header user={user} />

      <main className={styles.main}>
        {loading && <LoadingSpinner message="Loading your playlists…" />}

        {error && (
          <div className={styles.error}>
            Failed to load playlists: {error}
          </div>
        )}

        {!loading && !error && playlists.length === 0 && (
          <p className={styles.empty}>No playlists found.</p>
        )}

        {!loading && !error && owned.length > 0 && (
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.heading}>Your Library</h2>
              <span className={styles.count}>{owned.length}</span>
            </div>
            <PlaylistGrid playlists={owned} />
          </section>
        )}

        {!loading && !error && following.length > 0 && (
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.heading}>Following</h2>
              <span className={styles.count}>{following.length}</span>
            </div>
            <PlaylistGrid playlists={following} following />
          </section>
        )}
      </main>
    </div>
  );
}
