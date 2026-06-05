/**
 * MatchBadge — coloured pill explaining how a duplicate group was detected.
 *
 * uri   → "Exact Duplicate"   (red)
 * isrc  → "Same Recording"    (orange)
 * fuzzy → "Similar 87%"       (yellow)
 */

import type { MatchMethod } from '../../types';
import styles from './MatchBadge.module.css';

interface Props {
  method: MatchMethod;
  score?: number | null;
}

const LABELS: Record<MatchMethod, string> = {
  uri: 'Exact Duplicate',
  isrc: 'Same Recording',
  fuzzy: 'Similar',
};

export function MatchBadge({ method, score }: Props) {
  const label =
    method === 'fuzzy' && score != null
      ? `${LABELS.fuzzy} ${score}%`
      : LABELS[method];

  return (
    <span className={`${styles.badge} ${styles[method]}`}>
      {label}
    </span>
  );
}
