/**
 * PlaylistGrid — responsive grid of PlaylistCard components.
 */

import type { Playlist } from '../../types';
import { PlaylistCard } from './PlaylistCard';
import styles from './PlaylistGrid.module.css';

interface Props {
  playlists: Playlist[];
  following?: boolean;
}

export function PlaylistGrid({ playlists, following = false }: Props) {
  return (
    <div className={styles.grid}>
      {playlists.map((playlist) => (
        <PlaylistCard key={playlist.id} playlist={playlist} following={following} />
      ))}
    </div>
  );
}
