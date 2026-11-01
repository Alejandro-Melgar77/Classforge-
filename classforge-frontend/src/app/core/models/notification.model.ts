export interface AppNotification {
  id: string;
  user_id: string;
  title: string;
  message: string;
  type: string; // 'diagram_update', 'mention', 'system', 'team_invite'
  read: boolean;
  project_id?: string | null;
  diagram_id?: string | null;
  actor_id?: string | null;
  created_at: string;
}

export interface NotificationsPayload {
  items: AppNotification[];
  total: number;
  unread_count: number;
  page: number;
  limit: number;
}
