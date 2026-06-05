/**
 * LoadingSpinner — centered spinner shown during async operations.
 *
 * Props:
 *   message — optional status text displayed below the spinner
 */

import styles from './LoadingSpinner.module.css';

interface Props {
  message?: string;
}

export function LoadingSpinner({ message }: Props) {
  return (
    <div className={styles.container}>
      <div className={styles.spinner} aria-label="Loading" />
      {message && <p className={styles.message}>{message}</p>}
    </div>
  );
}
