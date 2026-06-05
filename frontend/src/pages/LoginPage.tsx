/**
 * LoginPage — the landing page for unauthenticated users.
 *
 * Shows an error message if Spotify redirected back with ?error=...
 * (e.g. user denied access, state mismatch, token exchange failure).
 */

import { useSearchParams } from 'react-router-dom';
import styles from './LoginPage.module.css';

const ERROR_MESSAGES: Record<string, string> = {
  access_denied: 'You declined access to Spotify. Please try again.',
  state_mismatch: 'Login failed due to a security check. Please try again.',
  token_exchange_failed: 'Could not connect to Spotify. Please try again.',
  profile_fetch_failed: 'Connected but could not fetch your profile. Please try again.',
};

export function LoginPage() {
  const [params] = useSearchParams();
  const error = params.get('error');

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.icon}>🎵</div>
        <h1 className={styles.title}>music-suite</h1>
        <p className={styles.subtitle}>
          Clean up your Spotify playlists. Remove duplicates, keep only what you love.
        </p>

        {error && (
          <div className={styles.error}>
            {ERROR_MESSAGES[error] ?? `Login error: ${error}`}
          </div>
        )}

        <a href="http://127.0.0.1:8000/api/auth/login" className={styles.spotifyBtn}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.441 17.329c-.215.354-.674.465-1.028.25-2.815-1.72-6.356-2.109-10.523-1.154-.4.09-.8-.155-.891-.555s.156-.8.556-.89c4.563-1.043 8.478-.594 11.635 1.32.354.217.465.676.25 1.03zm1.448-3.223c-.27.437-.843.574-1.28.303-3.22-1.978-8.131-2.55-11.933-1.396-.497.148-1.021-.135-1.17-.631-.148-.497.135-1.02.631-1.169 4.35-1.32 9.75-.68 13.44 1.587.44.27.575.843.304 1.278l.008.028zm.124-3.353c-3.857-2.29-10.216-2.501-13.898-1.382-.593.176-1.22-.158-1.395-.75s.158-1.22.751-1.396c4.228-1.283 11.248-1.034 15.684 1.598.533.316.707 1.003.39 1.536-.313.534-1.001.707-1.532.39v.004z"/>
          </svg>
          Connect with Spotify
        </a>
      </div>
    </div>
  );
}
