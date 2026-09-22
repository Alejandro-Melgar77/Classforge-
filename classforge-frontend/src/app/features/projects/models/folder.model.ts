export interface Folder {
  id: string;
  name: string;
  owner_id: string;
  team_id: string | null;
  project_id: string | null;
  parent_folder_id: string | null;
  type: 'personal' | 'team' | 'project';
  children?: Folder[];
}
