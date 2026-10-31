export interface UserProfile {
  id: string;
  email: string;
  full_name?: string | null;
  role?: string;
  auth_provider?: string;
  is_active?: boolean;
  created_at?: string;
}

export default UserProfile;

