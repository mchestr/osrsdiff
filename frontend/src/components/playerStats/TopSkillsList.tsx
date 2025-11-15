import type { ProgressAnalysisResponse } from '../../api/models/ProgressAnalysisResponse';
import { SKILL_ICONS } from '../../utils/skillIcons';

interface TopSkillsListProps {
  progressWeek: ProgressAnalysisResponse | null;
  onSkillClick: (skillName: string) => void;
}

export const TopSkillsList: React.FC<TopSkillsListProps> = ({ progressWeek, onSkillClick }) => {
  const topSkillsData = progressWeek
    ? Object.entries(progressWeek.progress.experience_gained)
        .filter(([skill]) => skill !== 'overall')
        .map(([skill, exp]) => ({
          name: skill,
          displayName: skill.charAt(0).toUpperCase() + skill.slice(1),
          value: exp,
        }))
        .filter((item) => item.value > 0)
        .sort((a, b) => b.value - a.value)
        .slice(0, 10)
    : [];

  return (
    <>
      <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">
        Top Skills Progress (7d)
      </h3>
      {topSkillsData.length > 0 ? (
        <div className="space-y-3 max-h-[520px] overflow-y-auto">
          {topSkillsData.map((skillData, index) => {
            const iconUrl = SKILL_ICONS[skillData.name];
            const levels = progressWeek?.progress.levels_gained[skillData.name] || 0;
            return (
              <div
                key={skillData.name}
                className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors cursor-pointer"
                onClick={() => onSkillClick(skillData.name)}
              >
                <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-primary-100 dark:bg-primary-900/50 rounded-lg text-xs font-bold text-primary-600 dark:text-primary-400">
                  #{index + 1}
                </div>
                {iconUrl && iconUrl !== '⚓' ? (
                  <img
                    src={iconUrl}
                    alt={skillData.displayName}
                    className="w-8 h-8 flex-shrink-0"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                    }}
                  />
                ) : (
                  <span className="w-8 h-8 flex items-center justify-center text-lg">{iconUrl || '❓'}</span>
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-semibold text-secondary-900 dark:text-secondary-100 capitalize truncate">
                      {skillData.displayName}
                    </span>
                    <span className="text-sm font-medium text-secondary-700 dark:text-secondary-200 whitespace-nowrap">
                      {skillData.value >= 1000000
                        ? `${(skillData.value / 1000000).toFixed(2)}M`
                        : skillData.value >= 1000
                        ? `${(skillData.value / 1000).toFixed(1)}K`
                        : skillData.value.toLocaleString()}
                    </span>
                  </div>
                  {levels > 0 && (
                    <div className="text-xs text-green-600 dark:text-green-400">
                      +{levels} level{levels !== 1 ? 's' : ''}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-secondary-500 dark:text-secondary-300">
            No progress data available
          </div>
        </div>
      )}
    </>
  );
};

