export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: string;
}

export interface Team {
  id: string;
  name: string;
  description: string;
  scrum_master_id: string;
  scrum_master_name?: string;
  member_ids: string[];
  members?: TeamMember[];
  avatar_color: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CreateTeamDto {
  name: string;
  description?: string;
  scrum_master_id: string;
  member_ids?: string[];
}

export interface UpdateTeamDto {
  name?: string;
  description?: string;
  scrum_master_id?: string;
  member_ids?: string[];
  is_active?: boolean;
}
