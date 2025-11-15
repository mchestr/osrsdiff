interface QuickActionsProps {
  onVerifySchedules: () => void;
  onGenerateSummaries: () => void;
  verifyingSchedules: boolean;
  generatingSummaries: boolean;
}

export const QuickActions: React.FC<QuickActionsProps> = ({
  onVerifySchedules,
  onGenerateSummaries,
  verifyingSchedules,
  generatingSummaries,
}) => {
  return (
    <div className="osrs-card">
      <h2 className="osrs-card-title mb-6">Quick Actions</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button
          onClick={onVerifySchedules}
          disabled={verifyingSchedules}
          className="osrs-btn text-left p-4 transition-colors bg-secondary-100 dark:bg-secondary-800 border border-secondary-300 dark:border-secondary-600 hover:bg-secondary-200 dark:hover:bg-secondary-700"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
            minHeight: '80px'
          }}
        >
          <div className="flex items-center justify-between">
            <span className="font-semibold osrs-text">Verify Schedules</span>
            <span className="text-xl" style={{ color: '#ffd700' }}>🔍</span>
          </div>
          <span className="text-xs osrs-text-secondary">
            {verifyingSchedules ? 'Checking schedule integrity...' : 'Validate all player fetch schedules'}
          </span>
        </button>
        <button
          onClick={onGenerateSummaries}
          disabled={generatingSummaries}
          className="osrs-btn text-left p-4 transition-colors bg-secondary-100 dark:bg-secondary-800 border border-secondary-300 dark:border-secondary-600 hover:bg-secondary-200 dark:hover:bg-secondary-700"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
            minHeight: '80px'
          }}
        >
          <div className="flex items-center justify-between">
            <span className="font-semibold osrs-text">Generate Summaries</span>
            <span className="text-xl" style={{ color: '#ffd700' }}>✨</span>
          </div>
          <span className="text-xs osrs-text-secondary">
            {generatingSummaries ? 'Generating summaries...' : 'Generate AI summaries for all active players'}
          </span>
        </button>
      </div>
    </div>
  );
};

