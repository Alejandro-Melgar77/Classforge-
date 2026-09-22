export type ProjectStatus = 'in_progress' | 'completed' | 'review' | 'archived';
export type ProjectType = 'team' | 'personal';

export interface Project {
  id: string;
  name: string;
  description: string;
  team_id: string | null;
  owner_id: string;
  type: ProjectType;
  status: ProjectStatus;
  color_tag: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}
