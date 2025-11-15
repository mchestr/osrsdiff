import { useState } from 'react';
import type { ProgressAnalysisResponse } from '../../api/models/ProgressAnalysisResponse';
import type { OrderedSkill } from '../../types/player';
import { SKILL_ICONS } from '../../utils/skillIcons';

interface SkillsProgressTableProps {
  progressDay: ProgressAnalysisResponse | null;
  progressWeek: ProgressAnalysisResponse | null;
  progressMonth: ProgressAnalysisResponse | null;
  orderedSkills: OrderedSkill[];
  onSkillClick: (skillName: string) => void;
}

export const SkillsProgressTable: React.FC<SkillsProgressTableProps> = ({
  progressDay,
  progressWeek,
  progressMonth,
  orderedSkills,
  onSkillClick,
}) => {
  const [selectedPeriod, setSelectedPeriod] = useState<number>(7);

  const getProgressForPeriod = (period: number): ProgressAnalysisResponse | null => {
    switch (period) {
      case 1:
        return progressDay;
      case 7:
        return progressWeek;
      case 30:
        return progressMonth;
      default:
        return progressWeek;
    }
  };

  const currentProgress = getProgressForPeriod(selectedPeriod);

  const getSkillProgress = (skillName: string) => {
    if (!currentProgress) {
      return { experience: 0, levels: 0 };
    }
    return {
      experience: currentProgress.progress.experience_gained[skillName] || 0,
      levels: currentProgress.progress.levels_gained[skillName] || 0,
    };
  };

  return (
    <div className="card bg-white dark:bg-gray-800">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100">Skills Progress Summary</h2>
        <select
          value={selectedPeriod}
          onChange={(e) => setSelectedPeriod(Number(e.target.value))}
          className="input text-sm bg-white dark:bg-secondary-800 dark:text-secondary-100 dark:border-secondary-600"
        >
          <option value={1} className="dark:bg-secondary-800 dark:text-secondary-100">Last 1 Day</option>
          <option value={7} className="dark:bg-secondary-800 dark:text-secondary-100">Last 7 Days</option>
          <option value={30} className="dark:bg-secondary-800 dark:text-secondary-100">Last 30 Days</option>
        </select>
      </div>

      {currentProgress ? (
        <div className="overflow-x-auto -mx-6 sm:mx-0">
          <table className="w-full min-w-[600px]">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-3 px-4 font-semibold text-sm text-secondary-700 dark:text-secondary-200">Skill</th>
                <th className="text-right py-3 px-4 font-semibold text-sm text-secondary-700 dark:text-secondary-200 whitespace-nowrap">Current Level</th>
                <th className="text-right py-3 px-4 font-semibold text-sm text-secondary-700 dark:text-secondary-200 whitespace-nowrap">Levels Gained</th>
                <th className="text-right py-3 px-4 font-semibold text-sm text-secondary-700 dark:text-secondary-200 whitespace-nowrap">Experience Gained</th>
              </tr>
            </thead>
            <tbody>
              {orderedSkills.map((skill) => {
                const progress = getSkillProgress(skill.name);
                const iconUrl = SKILL_ICONS[skill.name];
                return (
                  <tr
                    key={skill.name}
                    className={`border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                      progress.experience > 0 ? 'bg-green-50/30 dark:bg-green-900/20' : ''
                    }`}
                  >
                    <td className="py-3 px-4">
                      <div
                        className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
                        onClick={() => onSkillClick(skill.name)}
                      >
                        {iconUrl && iconUrl !== '⚓' ? (
                          <img
                            src={iconUrl}
                            alt={skill.displayName}
                            className="w-5 h-5 flex-shrink-0"
                            onError={(e) => {
                              const target = e.target as HTMLImageElement;
                              target.style.display = 'none';
                            }}
                          />
                        ) : (
                          <span className="w-5 h-5 flex items-center justify-center text-xs">{iconUrl || '❓'}</span>
                        )}
                        <span className="font-medium text-sm text-secondary-900 dark:text-secondary-100">{skill.displayName}</span>
                      </div>
                    </td>
                    <td className="text-right py-3 px-4">
                      <span className="font-semibold text-sm text-secondary-900 dark:text-secondary-100">{skill.level}</span>
                    </td>
                    <td className="text-right py-3 px-4">
                      {progress.levels > 0 ? (
                        <span className="font-semibold text-sm text-green-600 dark:text-green-400">+{progress.levels}</span>
                      ) : (
                        <span className="text-sm text-secondary-500 dark:text-secondary-300">0</span>
                      )}
                    </td>
                    <td className="text-right py-3 px-4">
                      {progress.experience > 0 ? (
                        <span className="font-semibold text-sm text-secondary-900 dark:text-secondary-100">{progress.experience.toLocaleString()}</span>
                      ) : (
                        <span className="text-sm text-secondary-500 dark:text-secondary-300">0</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-8 text-secondary-500 dark:text-secondary-300">
          No progress data available for the selected period
        </div>
      )}
    </div>
  );
};

