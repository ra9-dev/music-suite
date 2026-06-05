/**
 * SuccessPage — shown after a successful duplicate removal.
 *
 * Receives { removedCount, playlistName, playlistId } via React Router state.
 * Falls back gracefully if navigated to directly.
 */

import { useLocation, useNavigate } from 'react-router-dom';
import styles from './SuccessPage.module.css';

export function SuccessPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { removedCount, playlistName, playlistId } = (location.state as {
    removedCount?: number;
    playlistName?: string;
    playlistId?: string;
  }) ?? {};

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.icon}>🎉</div>
        <h1 className={styles.title}>All clean!</h1>

        {removedCount != null ? (
          <p className={styles.message}>
            Removed <strong>{removedCount}</strong> duplicate track
            {removedCount !== 1 ? 's' : ''} from
            {playlistName ? <> "<strong>{playlistName}</strong>"</> : ' your playlist'}.
          </p>
        ) : (
          <p className={styles.message}>Duplicates removed successfully.</p>
        )}

        <div className={styles.actions}>
          {playlistId && (
            <button
              className={styles.scanAgainBtn}
              onClick={() => navigate(`/playlists/${playlistId}/duplicates`)}
            >
              Scan again
            </button>
          )}
          <button
            className={styles.backBtn}
            onClick={() => navigate('/playlists')}
          >
            Back to Playlists
          </button>
        </div>
      </div>
    </div>
  );
}
