export interface DatabaseStats {
  total_players: number;
  active_players: number;
  inactive_players: number;
  total_hiscore_records: number;
  oldest_record: string | null;
  newest_record: string | null;
  records_last_24h: number;
  records_last_7d: number;
  avg_records_per_player: number;
}

export interface SystemHealth {
  status: string;
  database_connected: boolean;
  total_storage_mb: number | null;
  uptime_info: Record<string, unknown>;
}

export interface ExecutionSummary {
  total: number;
  successCount: number;
  failureCount: number;
  retryCount: number;
  pendingCount: number;
  successRate: number;
  failureRate: number;
  avgDuration: number;
  recentFailures24h: number;
  recentFailures7d: number;
  statusBreakdown: Record<string, number>;
}

