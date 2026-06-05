/**
 * Shared TypeScript types.
 *
 * These mirror the Pydantic models in backend/app/types.py exactly.
 * If you add a field on the backend, add it here too.
 */

export interface SpotifyUser {
  id: string;
  display_name: string;
  image_url: string | null;
}

export interface Playlist {
  id: string;
  name: string;
  description: string | null;
  track_count: number;
  owner_id: string;
  owner_name: string;
  image_url: string | null;
  /** True if the logged-in user owns this playlist */
  is_owner: boolean;
  /** True if anyone with the link can edit (collaborative playlist) */
  is_collaborative: boolean;
}

/** A single track entry in a Spotify playlist, including its exact position. */
export interface PlaylistTrack {
  /** 0-based index in the playlist — required for the Spotify DELETE API */
  position: number;
  /** e.g. "spotify:track:4uLU6hMCjMI75M1A2tKUQC" */
  uri: string;
  id: string;
  name: string;
  artists: string[];
  album: string;
  /** Album cover art URL from Spotify */
  image_url: string | null;
  duration_ms: number;
  /** International Standard Recording Code — uniquely identifies a recording */
  isrc: string | null;
  added_at: string | null;
  added_by: string | null;
}

/** How a duplicate group was detected */
export type MatchMethod = 'uri' | 'isrc' | 'fuzzy';

/** A set of 2+ tracks that are considered duplicates of each other */
export interface DuplicateGroup {
  group_id: string;
  match_method: MatchMethod;
  /** Similarity score 0–100, only set for fuzzy matches */
  fuzzy_score: number | null;
  tracks: PlaylistTrack[];
}

/** The user's decision for a single duplicate group */
export interface GroupDecision {
  /** Position of the track to keep (null = skip this group) */
  keep_position: number | null;
}
