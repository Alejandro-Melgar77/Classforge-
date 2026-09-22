export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  timestamp?: string;
}

/** Matches backend StandardResponse { success, data: { access_token, refresh_token, user } } */
export interface AuthResponseData {
  access_token: string;
  refresh_token: string;
  user: UserProfile;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  /** Backend stores a single role string: 'admin' | 'scrum_master' | 'dev' */
  role: 'admin' | 'scrum_master' | 'dev';
  avatar_url?: string | null;
  team_ids?: string[];
}

/** Kept for backwards compat but now mapped correctly */
export type AuthResponse = ApiResponse<AuthResponseData>;

