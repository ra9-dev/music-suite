/**
 * Hook: useDuplicates
 *
 * Orchestrates the full duplicate detection and removal flow for one playlist:
 *   1. Fetch all tracks via GET /api/playlists/:id/tracks
 *   2. Detect duplicates via POST /api/duplicates/detect
 *   3. Remove chosen duplicates via POST /api/duplicates/remove
 *
 * Returns state + action functions that DuplicatesPage uses directly.
 */

import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { DuplicateGroup, GroupDecision, PlaylistTrack } from '../types';

export type Phase = 'loading' | 'detecting' | 'reviewing' | 'removing' | 'empty' | 'error';

interface DuplicatesState {
  phase: Phase;
  playlistName: string;
  tracks: PlaylistTrack[];
  groups: DuplicateGroup[];
  /** Map from group_id → position of the track to keep (null = skip group) */
  decisions: Map<string, GroupDecision>;
  error: string | null;
  /** Number of tracks that will be removed given current decisions */
  removalCount: number;
  /** True when every group is skipped (nothing will be removed) */
  allSkipped: boolean;
  /** True when every group keeps its default (first) track */
  isDefault: boolean;
}

interface DuplicatesActions {
  setDecision: (groupId: string, keepPosition: number | null) => void;
  skipAll: () => void;
  resetDecisions: () => void;
  submitRemovals: () => Promise<{ removed_count: number; playlist_id: string }>;
}

export function useDuplicates(playlistId: string): DuplicatesState & DuplicatesActions {
  const [phase, setPhase] = useState<Phase>('loading');
  const [playlistName, setPlaylistName] = useState('');
  const [tracks, setTracks] = useState<PlaylistTrack[]>([]);
  const [groups, setGroups] = useState<DuplicateGroup[]>([]);
  const [decisions, setDecisions] = useState<Map<string, GroupDecision>>(new Map());
  const [error, setError] = useState<string | null>(null);

  // Step 1 + 2: fetch tracks then detect duplicates
  useEffect(() => {
    if (!playlistId) return;

    let cancelled = false;

    async function load() {
      try {
        setPhase('loading');
        const tracksData = await apiClient.get<{
          playlist_id: string;
          playlist_name: string;
          tracks: PlaylistTrack[];
        }>(`/api/playlists/${playlistId}/tracks`);

        if (cancelled) return;
        setTracks(tracksData.tracks);
        setPlaylistName(tracksData.playlist_name);

        setPhase('detecting');
        const detectData = await apiClient.post<{
          duplicate_groups: DuplicateGroup[];
          total_duplicates: number;
        }>('/api/duplicates/detect', {
          playlist_id: playlistId,
          tracks: tracksData.tracks,
        });

        if (cancelled) return;

        if (detectData.duplicate_groups.length === 0) {
          setPhase('empty');
          return;
        }

        // Default decision: keep the first (earliest-added) track in each group
        const defaultDecisions = new Map<string, GroupDecision>(
          detectData.duplicate_groups.map((g) => [
            g.group_id,
            { keep_position: g.tracks[0].position },
          ]),
        );

        setGroups(detectData.duplicate_groups);
        setDecisions(defaultDecisions);
        setPhase('reviewing');
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Something went wrong');
          setPhase('error');
        }
      }
    }

    load();
    return () => { cancelled = true; };
  }, [playlistId]);

  // Update decision for a single group
  function setDecision(groupId: string, keepPosition: number | null) {
    setDecisions((prev) => {
      const next = new Map(prev);
      next.set(groupId, { keep_position: keepPosition });
      return next;
    });
  }

  function skipAll() {
    setDecisions(
      new Map(groups.map((g) => [g.group_id, { keep_position: null }])),
    );
  }

  function resetDecisions() {
    setDecisions(
      new Map(
        groups.map((g) => [g.group_id, { keep_position: g.tracks[0].position }]),
      ),
    );
  }

  // Step 3: submit removals to the backend
  async function submitRemovals() {
    setPhase('removing');
    setError(null);

    const uriPositions = new Map<string, number[]>();

    for (const group of groups) {
      const decision = decisions.get(group.group_id);
      if (!decision || decision.keep_position === null) continue;

      for (const track of group.tracks) {
        if (track.position === decision.keep_position) continue;
        const existing = uriPositions.get(track.uri) ?? [];
        uriPositions.set(track.uri, [...existing, track.position]);
      }
    }

    const removals = Array.from(uriPositions.entries()).map(([uri, positions]) => ({
      uri,
      positions,
    }));

    try {
      const result = await apiClient.post<{
        ok: boolean;
        removed_count: number;
        playlist_id: string;
        snapshot_id: string;
      }>('/api/duplicates/remove', {
        playlist_id: playlistId,
        removals,
      });
      return result;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Removal failed');
      setPhase('error');
      throw err;
    }
  }

  // Compute how many tracks will be removed given current decisions
  const removalCount = groups.reduce((total, group) => {
    const decision = decisions.get(group.group_id);
    if (!decision || decision.keep_position === null) return total;
    return total + group.tracks.filter((t) => t.position !== decision.keep_position).length;
  }, 0);

  const allSkipped = groups.every((g) => decisions.get(g.group_id)?.keep_position === null);

  const isDefault = groups.every(
    (g) => decisions.get(g.group_id)?.keep_position === g.tracks[0].position,
  );

  return {
    phase,
    playlistName,
    tracks,
    groups,
    decisions,
    error,
    removalCount,
    allSkipped,
    isDefault,
    setDecision,
    skipAll,
    resetDecisions,
    submitRemovals,
  };
}
