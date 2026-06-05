/**
 * Header — top navigation bar shown on all authenticated pages.
 *
 * Shows the user's Spotify display name and avatar on the right side.
 * Logout button clears the session and sends the user back to /.
 */

import { API_BASE, SID_KEY, getAuthHeaders } from '../../api/client';
import type { SpotifyUser } from '../../types';
import styles from './Header.module.css';

interface Props {
  user: SpotifyUser;
}

export function Header({ user }: Props) {
  async function handleLogout() {
    await fetch(`${API_BASE}/api/auth/logout`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    localStorage.removeItem(SID_KEY);
    window.location.href = '/';
  }

  return (
    <header className={styles.header}>
      <a href="/playlists" className={styles.logo}>
        🎵 music-suite
      </a>

      <div className={styles.userSection}>
        {user.image_url && (
          <img
            src={user.image_url}
            alt={user.display_name}
            className={styles.avatar}
          />
        )}
        <span className={styles.displayName}>{user.display_name}</span>
        <button className={styles.logoutBtn} onClick={handleLogout}>
          Log out
        </button>
      </div>
    </header>
  );
}
