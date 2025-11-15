import React from 'react';
import type { Setting, SettingSection } from './types';
import { SettingSectionHeader } from './SettingSectionHeader';
import { SettingRow } from './SettingRow';

interface SettingsTableProps {
  sections: SettingSection[];
  onRowClick: (setting: Setting, e: React.MouseEvent) => void;
  onEdit: (setting: Setting) => void;
  onReset: (key: string) => void;
  disabled?: boolean;
}

export const SettingsTable: React.FC<SettingsTableProps> = ({
  sections,
  onRowClick,
  onEdit,
  onReset,
  disabled = false,
}) => {
  return (
    <div className="osrs-card p-0 overflow-hidden">
      {sections.map((section, sectionIndex) => (
        <div key={section.title}>
          <SettingSectionHeader
            title={section.title}
            description={section.description}
            isFirst={sectionIndex === 0}
          />
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {section.settings.map((setting) => (
              <SettingRow
                key={setting.id}
                setting={setting}
                onRowClick={onRowClick}
                onEdit={onEdit}
                onReset={onReset}
                disabled={disabled}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

