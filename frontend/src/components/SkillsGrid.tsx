import React from 'react';

export interface SkillsGridProps {
  skills: Array<{ name: string; displayName: string; level: number; experience: number; maxLevel: number }>;
  skillIcons: Record<string, string>;
  totalLevel: number;
  onSkillClick: (skillName: string) => void;
}

export const SkillsGrid: React.FC<SkillsGridProps> = ({
  skills,
  skillIcons,
  totalLevel,
  onSkillClick,
}) => {
  return (
    <div className="osrs-skills-panel" style={{ padding: '8px' }}>
      <div className="osrs-skills-grid">
        {skills.map((skill) => {
          const iconUrl = skillIcons[skill.name];
          const maxLevel = skill.maxLevel;
          return (
            <div
              key={skill.name}
              className="osrs-skill-cell cursor-pointer hover:opacity-80 transition-opacity"
              onClick={() => onSkillClick(skill.name)}
              title={`Click to view ${skill.displayName} details`}
            >
              <div className="osrs-skill-icon">
                {iconUrl && iconUrl !== '⚓' ? (
                  <img
                    src={iconUrl}
                    alt={skill.displayName}
                    className="osrs-skill-icon-img"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                      if (!target.parentElement?.querySelector('.osrs-skill-icon-fallback')) {
                        const fallback = document.createElement('span');
                        fallback.textContent = '❓';
                        fallback.className = 'osrs-skill-icon-fallback';
                        target.parentElement?.appendChild(fallback);
                      }
                    }}
                  />
                ) : (
                  <span className="osrs-skill-icon-fallback">{iconUrl || '❓'}</span>
                )}
              </div>
              <div className="osrs-skill-level">
                {skill.level}/{maxLevel}
              </div>
            </div>
          );
        })}
      </div>
      <div className="osrs-total-level">
        Total level: {totalLevel}
      </div>
    </div>
  );
};

