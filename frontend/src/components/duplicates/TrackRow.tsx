/**
 * TrackRow — displays one track within a duplicate group.
 *
 * Shows a radio button (selected = this track will be KEPT),
 * the track name, artists, album, ISRC, and when it was added.
 */

import type { PlaylistTrack } from '../../types';
import styles from './TrackRow.module.css';

const PLACEHOLDER =
  'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="%23333"%3E%3Crect width="48" height="48"/%3E%3Ctext x="50%25" y="50%25" fill="%23666" font-size="20" text-anchor="middle" dominant-baseline="middle"%3E🎵%3C/text%3E%3C/svg%3E';

interface Props {
  track: PlaylistTrack;
  groupId: string;
  isKept: boolean;
  onKeep: (position: number) => void;
}

function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function TrackRow({ track, groupId, isKept, onKeep }: Props) {
  const inputId = `keep-${groupId}-${track.position}`;

  return (
    <label
      htmlFor={inputId}
      className={`${styles.row} ${isKept ? styles.kept : ''}`}
    >
      <input
        type="radio"
        id={inputId}
        name={`group-${groupId}`}
        checked={isKept}
        onChange={() => onKeep(track.position)}
        className={styles.radio}
      />

      <img
        src={track.image_url ?? PLACEHOLDER}
        alt=""
        className={styles.artwork}
        loading="lazy"
      />

      <div className={styles.info}>
        <span className={styles.name}>{track.name}</span>
        <span className={styles.artists}>{track.artists.join(', ')}</span>
        <span className={styles.album}>{track.album}</span>
      </div>

      <div className={styles.meta}>
        <span className={styles.duration}>{formatDuration(track.duration_ms)}</span>
        {track.isrc && <span className={styles.isrc}>{track.isrc}</span>}
        <span className={styles.addedAt}>Added {formatDate(track.added_at)}</span>
      </div>

      {isKept && <span className={styles.keepLabel}>KEEP</span>}
      {!isKept && <span className={styles.removeLabel}>REMOVE</span>}
    </label>
  );
}
