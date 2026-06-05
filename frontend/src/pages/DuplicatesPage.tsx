/**
 * DuplicatesPage — the core interactive duplicate review page.
 *
 * Flow:
 *  1. "loading"   — fetching all tracks from Spotify
 *  2. "detecting" — running the detection algorithm on the backend
 *  3. "reviewing" — user reviews groups and picks which copy to keep
 *  4. "removing"  — removals submitted to Spotify
 *  5. "empty"     — no duplicates found, all good!
 *  6. "error"     — something went wrong
 *
 * All state is managed by the useDuplicates hook.
 */

import { useNavigate, useParams } from 'react-router-dom';
import type { SpotifyUser } from '../types';
import { useDuplicates } from '../hooks/useDuplicates';
import { Header } from '../components/layout/Header';
import { LoadingSpinner } from '../components/layout/LoadingSpinner';
import { DuplicateList } from '../components/duplicates/DuplicateList';
import styles from './DuplicatesPage.module.css';

interface Props {
  user: SpotifyUser;
}

export function DuplicatesPage({ user }: Props) {
  const { playlistId } = useParams<{ playlistId: string }>();
  const navigate = useNavigate();

  const {
    phase,
    playlistName,
    groups,
    decisions,
    error,
    removalCount,
    allSkipped,
    isDefault,
    setDecision,
    skipAll,
    resetDecisions,
    submitRemovals,
  } = useDuplicates(playlistId ?? '');

  async function handleSubmit() {
    try {
      const result = await submitRemovals();
      navigate('/success', {
        state: {
          removedCount: result.removed_count,
          playlistName,
          playlistId,
        },
      });
    } catch (err: unknown) {
      // Error state is handled inside the hook; we just catch to prevent unhandled rejection
      console.error('Removal failed:', err);
    }
  }

  return (
    <div className={styles.page}>
      <Header user={user} />

      <main className={styles.main}>
        {/* Breadcrumb */}
        <nav className={styles.breadcrumb}>
          <a href="/playlists" className={styles.breadcrumbLink}>Playlists</a>
          <span className={styles.separator}>›</span>
          <span className={styles.current}>{playlistName || 'Loading…'}</span>
        </nav>

        {/* Loading tracks */}
        {phase === 'loading' && (
          <LoadingSpinner message="Fetching playlist tracks…" />
        )}

        {/* Detecting duplicates */}
        {phase === 'detecting' && (
          <LoadingSpinner message="Scanning for duplicates…" />
        )}

        {/* Removing */}
        {phase === 'removing' && (
          <LoadingSpinner message="Removing selected duplicates from Spotify…" />
        )}

        {/* No duplicates */}
        {phase === 'empty' && (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>✅</div>
            <h2>No duplicates found!</h2>
            <p>"{playlistName}" is clean — every track is unique.</p>
            <a href="/playlists" className={styles.backLink}>
              ← Back to Playlists
            </a>
          </div>
        )}

        {/* Error */}
        {phase === 'error' && (
          <div className={styles.errorState}>
            <div className={styles.emptyIcon}>⚠️</div>
            <h2>Something went wrong</h2>
            <p>{error}</p>
            <a href="/playlists" className={styles.backLink}>
              ← Back to Playlists
            </a>
          </div>
        )}

        {/* Review mode */}
        {phase === 'reviewing' && (
          <>
            <div className={styles.pageHeader}>
              <h2 className={styles.heading}>
                Duplicate Review — {playlistName}
              </h2>
              <p className={styles.hint}>
                Select which copy to keep in each group, or skip groups you are unsure about.
                Use &ldquo;Skip all&rdquo; to keep every track unchanged.
              </p>
            </div>

            <DuplicateList
              groups={groups}
              decisions={decisions}
              removalCount={removalCount}
              allSkipped={allSkipped}
              isDefault={isDefault}
              isRemoving={false}
              onDecide={setDecision}
              onSkipAll={skipAll}
              onReset={resetDecisions}
              onSubmit={handleSubmit}
            />
          </>
        )}
      </main>
    </div>
  );
}
