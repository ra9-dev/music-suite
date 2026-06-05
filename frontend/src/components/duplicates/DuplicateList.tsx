/**
 * DuplicateList — scrollable list of all duplicate groups found in a playlist.
 *
 * Each group is rendered by DuplicateGroup. The submit button at the bottom
 * shows how many tracks will be removed and triggers the removal.
 */

import type { DuplicateGroup as DuplicateGroupType, GroupDecision } from '../../types';
import { DuplicateGroup } from './DuplicateGroup';
import styles from './DuplicateList.module.css';

interface Props {
  groups: DuplicateGroupType[];
  decisions: Map<string, GroupDecision>;
  removalCount: number;
  allSkipped: boolean;
  isDefault: boolean;
  isRemoving: boolean;
  onDecide: (groupId: string, keepPosition: number | null) => void;
  onSkipAll: () => void;
  onReset: () => void;
  onSubmit: () => void;
}

export function DuplicateList({
  groups,
  decisions,
  removalCount,
  allSkipped,
  isDefault,
  isRemoving,
  onDecide,
  onSkipAll,
  onReset,
  onSubmit,
}: Props) {
  return (
    <div className={styles.container}>
      <div className={styles.summary}>
        <strong>{groups.length}</strong> duplicate group{groups.length !== 1 ? 's' : ''} found ·{' '}
        <strong>{removalCount}</strong> track{removalCount !== 1 ? 's' : ''} will be removed
      </div>

      <div className={styles.groups}>
        {groups.map((group) => (
          <DuplicateGroup
            key={group.group_id}
            group={group}
            decision={decisions.get(group.group_id) ?? { keep_position: group.tracks[0].position }}
            onDecide={onDecide}
          />
        ))}
      </div>

      <div className={styles.actions}>
        <div className={styles.bulkActions}>
          <button
            type="button"
            className={styles.secondaryBtn}
            disabled={allSkipped || isRemoving}
            onClick={onSkipAll}
          >
            Skip all groups
          </button>
          <button
            type="button"
            className={styles.secondaryBtn}
            disabled={isDefault || isRemoving}
            onClick={onReset}
          >
            Reset selections
          </button>
        </div>

        <button
          className={styles.removeBtn}
          disabled={removalCount === 0 || isRemoving}
          onClick={onSubmit}
        >
          {isRemoving
            ? 'Removing…'
            : removalCount === 0
              ? 'No tracks selected for removal'
              : `Remove ${removalCount} duplicate${removalCount !== 1 ? 's' : ''}`}
        </button>
      </div>
    </div>
  );
}
