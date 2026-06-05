/**
 * DuplicateGroup — one card in the duplicate review list.
 *
 * Shows:
 *  - The match method badge (Exact Duplicate / Same Recording / Similar X%)
 *  - A TrackRow for each track in the group
 *  - A "Skip this group" option (keeps all tracks, removes nothing)
 */

import type { DuplicateGroup as DuplicateGroupType, GroupDecision } from '../../types';
import { MatchBadge } from './MatchBadge';
import { TrackRow } from './TrackRow';
import styles from './DuplicateGroup.module.css';

interface Props {
  group: DuplicateGroupType;
  decision: GroupDecision;
  onDecide: (groupId: string, keepPosition: number | null) => void;
}

export function DuplicateGroup({ group, decision, onDecide }: Props) {
  const isSkipped = decision.keep_position === null;

  return (
    <div className={`${styles.card} ${isSkipped ? styles.skipped : ''}`}>
      <div className={styles.header}>
        <MatchBadge method={group.match_method} score={group.fuzzy_score} />
        <span className={styles.count}>{group.tracks.length} copies found</span>
      </div>

      <div className={styles.tracks}>
        {group.tracks.map((track) => (
          <TrackRow
            key={track.position}
            track={track}
            groupId={group.group_id}
            isKept={!isSkipped && decision.keep_position === track.position}
            onKeep={(pos) => onDecide(group.group_id, pos)}
          />
        ))}
      </div>

      <div className={styles.footer}>
        <label className={styles.skipLabel}>
          <input
            type="checkbox"
            checked={isSkipped}
            onChange={(e) =>
              onDecide(
                group.group_id,
                e.target.checked ? null : group.tracks[0].position,
              )
            }
          />
          Skip this group (keep all copies)
        </label>
      </div>
    </div>
  );
}
