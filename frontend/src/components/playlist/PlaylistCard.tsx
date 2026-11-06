/**
 * PlaylistCard — displays a single Spotify playlist.
 *
 * The "Scan for Duplicates" button is disabled for playlists the user
 * doesn't own and can't edit (non-collaborative playlists owned by others).
 */

import { useNavigate } from 'react-router-dom';
import type { Playlist } from '../../types';
import styles from './PlaylistCard.module.css';

interface Props {
  playlist: Playlist;
  following?: boolean;
}

const PLACEHOLDER = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200" fill="%23333"%3E%3Crect width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" fill="%23666" font-size="48" text-anchor="middle" dominant-baseline="middle"%3E🎵%3C/text%3E%3C/svg%3E';

export function PlaylistCard({ playlist, following = false }: Props) {
  const navigate = useNavigate();
  const canEdit = playlist.is_owner || playlist.is_collaborative;

  return (
    <div className={`${styles.card} ${following ? styles.followingCard : ''}`}>
      <div className={styles.imageWrapper}>
        <img
          src={playlist.image_url ?? PLACEHOLDER}
          alt={playlist.name}
          className={styles.image}
        />
        {following && (
          <span className={styles.followingBadge}>Following</span>
        )}
      </div>
      <div className={styles.body}>
        <h3 className={styles.name} title={playlist.name}>
          {playlist.name}
        </h3>
        <p className={styles.meta}>
          {playlist.track_count} tracks
          {!playlist.is_owner && (
            <span className={styles.owner}> · by {playlist.owner_name}</span>
          )}
        </p>
        <button
          className={styles.scanBtn}
          disabled={!canEdit}
          title={canEdit ? 'Scan for duplicates' : "You can't edit this playlist"}
          onClick={() => navigate(`/playlists/${playlist.id}/duplicates`)}
        >
          Scan for Duplicates
        </button>
      </div>
    </div>
  );
}
