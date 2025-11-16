import { useState, useMemo } from 'react';
import type { ProgressAnalysisResponse } from '../../api/models/ProgressAnalysisResponse';
import type { OrderedSkill } from '../../types/player';
import { SKILL_ICONS } from '../../utils/skillIcons';
import { DataTable, type Column } from '../common';

interface SkillsProgressTableProps {
  progressDay: ProgressAnalysisResponse | null;
  progressWeek: ProgressAnalysisResponse | null;
  progressMonth: ProgressAnalysisResponse | null;
  orderedSkills: OrderedSkill[];
  onSkillClick: (skillName: string) => void;
}

interface SkillWithProgress extends OrderedSkill, Record<string, unknown> {
  experienceGained: number;
  levelsGained: number;
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

  const skillsWithProgress = useMemo<SkillWithProgress[]>(() => {
    return orderedSkills.map((skill) => {
      const experience = currentProgress?.progress.experience_gained[skill.name] || 0;
      const levels = currentProgress?.progress.levels_gained[skill.name] || 0;
      return {
        ...skill,
        experienceGained: experience,
        levelsGained: levels,
      };
    });
  }, [orderedSkills, currentProgress]);

  const columns: Column<SkillWithProgress>[] = [
    {
      key: 'displayName',
      label: 'Skill',
      sortable: true,
      render: (skill) => {
        const iconUrl = SKILL_ICONS[skill.name];
        return (
          <div
            className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
            onClick={(e) => {
              e.stopPropagation();
              onSkillClick(skill.name);
            }}
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
            <span className="font-medium text-sm text-gray-900 dark:text-gray-100">{skill.displayName}</span>
          </div>
        );
      },
    },
    {
      key: 'level',
      label: 'Current Level',
      sortable: true,
      render: (skill) => (
        <span className="font-semibold text-sm text-gray-900 dark:text-gray-100">
          {skill.level}
        </span>
      ),
      className: 'text-right',
      headerClassName: 'text-right',
    },
    {
      key: 'levelsGained',
      label: 'Levels Gained',
      sortable: true,
      render: (skill) =>
        skill.levelsGained > 0 ? (
          <span className="font-semibold text-sm text-green-600 dark:text-green-400">
            +{skill.levelsGained}
          </span>
        ) : (
          <span className="text-sm text-gray-500 dark:text-gray-300">0</span>
        ),
      className: 'text-right',
      headerClassName: 'text-right',
    },
    {
      key: 'experienceGained',
      label: 'Experience Gained',
      sortable: true,
      render: (skill) =>
        skill.experienceGained > 0 ? (
          <span className="font-semibold text-sm text-gray-900 dark:text-gray-100">
            {skill.experienceGained.toLocaleString()}
          </span>
        ) : (
          <span className="text-sm text-gray-500 dark:text-gray-300">0</span>
        ),
      className: 'text-right',
      headerClassName: 'text-right',
    },
  ];

  const getRowClassName = (skill: SkillWithProgress): string => {
    return skill.experienceGained > 0
      ? 'bg-green-50/30 dark:bg-green-900/20'
      : '';
  };

  return (
    <div className="osrs-card">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Skills Progress Summary
        </h2>
        <div className="inline-flex rounded-md shadow-sm border border-gray-300 dark:border-gray-600 overflow-hidden" role="group">
          <button
            type="button"
            onClick={() => setSelectedPeriod(1)}
            className={`px-3 py-1.5 text-sm font-medium transition-colors border-r border-gray-300 dark:border-gray-600 ${
              selectedPeriod === 1
                ? 'bg-primary-600 text-white dark:bg-primary-500'
                : 'bg-white text-gray-700 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            1d
          </button>
          <button
            type="button"
            onClick={() => setSelectedPeriod(7)}
            className={`px-3 py-1.5 text-sm font-medium transition-colors border-r border-gray-300 dark:border-gray-600 ${
              selectedPeriod === 7
                ? 'bg-primary-600 text-white dark:bg-primary-500'
                : 'bg-white text-gray-700 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            7d
          </button>
          <button
            type="button"
            onClick={() => setSelectedPeriod(30)}
            className={`px-3 py-1.5 text-sm font-medium transition-colors ${
              selectedPeriod === 30
                ? 'bg-primary-600 text-white dark:bg-primary-500'
                : 'bg-white text-gray-700 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            30d
          </button>
        </div>
      </div>

      {currentProgress ? (
        <DataTable
          data={skillsWithProgress}
          columns={columns}
          keyExtractor={(skill) => skill.name}
          emptyMessage="No skills data available"
          searchable
          searchPlaceholder="Search skills..."
          searchKeys={['displayName', 'name']}
          rowClassName={getRowClassName}
        />
      ) : (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          No progress data available for the selected period
        </div>
      )}
    </div>
  );
};

