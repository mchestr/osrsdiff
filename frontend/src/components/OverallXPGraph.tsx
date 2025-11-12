import { format } from 'date-fns';
import { useEffect, useState } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api/apiClient';
import type { SkillProgressResponse } from '../api/models/SkillProgressResponse';

interface OverallXPGraphProps {
  username: string;
}

export const OverallXPGraph: React.FC<OverallXPGraphProps> = ({ username }) => {
  const [progress, setProgress] = useState<SkillProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!username) return;

      try {
        setLoading(true);
        setError(null);
        // Fetch overall XP progress (90 days of history)
        const data = await api.HistoryService.getSkillProgressApiV1PlayersUsernameHistorySkillsSkillGet(
          username,
          'overall',
          90
        );
        setProgress(data);
      } catch (err: unknown) {
        console.error('Failed to load overall XP progress:', err);
        setError('Failed to load XP data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [username]);

  if (loading) {
    return (
      <div className="osrs-card" style={{ padding: '16px' }}>
        <h3 className="osrs-card-title text-base mb-4">Overall XP</h3>
        <div className="osrs-text-secondary text-sm text-center py-8">Loading...</div>
      </div>
    );
  }

  if (error || !progress || !progress.timeline || progress.timeline.length === 0) {
    return (
      <div className="osrs-card" style={{ padding: '16px' }}>
        <h3 className="osrs-card-title text-base mb-4">Overall XP</h3>
        <div className="osrs-text-secondary text-sm text-center py-8">
          {error || 'No data available'}
        </div>
      </div>
    );
  }

  // Prepare timeline data for chart
  const timelineData = progress.timeline.map((entry) => ({
    date: format(new Date(entry.date), 'MMM d'),
    experience: entry.experience ?? 0,
    level: entry.level ?? 0,
  }));

  const currentXP = progress.timeline[progress.timeline.length - 1]?.experience ?? 0;
  const xpGained = progress.progress.experience_gained ?? 0;

  return (
    <div className="osrs-card" style={{ padding: '16px' }}>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-2">
        <h3 className="osrs-card-title text-base">Overall XP</h3>

        {/* Current Stats */}
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <span className="osrs-stat-label text-xs">Total XP</span>
            <span className="osrs-text text-sm font-semibold">
              {currentXP ? (currentXP / 1000000).toFixed(2) + 'M' : 'N/A'}
            </span>
          </div>
          {xpGained > 0 && (
            <div className="flex items-center gap-2">
              <span className="osrs-stat-label text-xs">Gained (90d)</span>
              <span className="osrs-text text-sm font-medium text-green-400">
                +{(xpGained / 1000000).toFixed(2)}M
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Graph */}
      <div className="h-64" style={{ backgroundColor: '#1d1611' }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={timelineData} margin={{ top: 20, right: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#8b7355" opacity={0.3} />
            <XAxis
              dataKey="date"
              angle={-45}
              textAnchor="end"
              height={80}
              tick={{ fontSize: 11, fill: '#ffd700', fontWeight: 500 }}
              interval="preserveStartEnd"
              stroke="#8b7355"
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#ffd700', fontWeight: 500 }}
              stroke="#8b7355"
              tickFormatter={(value) => {
                if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
                if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
                return value.toString();
              }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#2d2418',
                border: '2px solid #8b7355',
                borderRadius: '0',
                fontSize: '12px',
                fontWeight: 500,
                padding: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                color: '#ffd700'
              }}
              labelStyle={{
                marginBottom: '4px',
                fontSize: '13px',
                fontWeight: 600,
                color: '#ffd700'
              }}
              formatter={(value: number) => {
                if (value >= 1000000) return `${(value / 1000000).toFixed(2)}M XP`;
                if (value >= 1000) return `${(value / 1000).toFixed(1)}K XP`;
                return `${value} XP`;
              }}
            />
            <Line
              type="monotone"
              dataKey="experience"
              stroke="#ffd700"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

