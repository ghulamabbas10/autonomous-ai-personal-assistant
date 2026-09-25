export interface User {
  id: string;
  email: string;
  display_name: string;
  timezone: string;
  created_at: string;
}

export interface AuthenticationResponse {
  user: User;
  csrf_token: string;
}
