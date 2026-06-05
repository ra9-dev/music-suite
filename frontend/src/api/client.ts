/**
 * Typed API client.
 *
 * Auth mechanism:
 *   After OAuth, the backend redirects to the frontend with ?sid=<session_id>.
 *   App.tsx saves it to localStorage under SID_KEY. Every request then includes:
 *       Authorization: Bearer <session_id>
 *   This avoids cookie/SameSite issues between localhost:5173 and 127.0.0.1:8000.
 *
 * Usage:
 *   const data = await apiClient.get<SpotifyUser>('/api/auth/me');
 *   const result = await apiClient.post<DetectResponse>('/api/duplicates/detect', body);
 */

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://127.0.0.1:8000';

/** localStorage key for the session ID. Exported so App.tsx and Header can use it. */
export const SID_KEY = 'music_suite_sid';

/** Returns the Authorization header if a session ID is stored, otherwise {}. */
export function getAuthHeaders(): Record<string, string> {
  const sid = localStorage.getItem(SID_KEY);
  return sid ? { Authorization: `Bearer ${sid}` } : {};
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options.headers,
    },
  });

  if (res.status === 401) {
    // Session expired or revoked — clear stored sid and go to login.
    // Guard against redirecting from '/' to avoid a reload loop.
    if (window.location.pathname !== '/') {
      localStorage.removeItem(SID_KEY);
      window.location.href = '/';
    }
    throw new ApiError(401, 'Not authenticated');
  }

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body.detail || message;
    } catch {
      // ignore JSON parse errors
    }
    throw new ApiError(res.status, message);
  }

  return res.json() as Promise<T>;
}

export const apiClient = {
  get<T>(path: string): Promise<T> {
    return request<T>(path);
  },

  post<T>(path: string, body: unknown): Promise<T> {
    return request<T>(path, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },
};

export { ApiError };
