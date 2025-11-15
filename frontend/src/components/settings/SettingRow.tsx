import React from 'react';
import type { Setting } from './types';
import { SettingValueDisplay } from './SettingValueDisplay';
import { SettingActionButtons } from './SettingActionButtons';

interface SettingRowProps {
  setting: Setting;
  onRowClick: (setting: Setting, e: React.MouseEvent) => void;
  onEdit: (setting: Setting) => void;
  onReset: (key: string) => void;
  disabled?: boolean;
}

export const SettingRow: React.FC<SettingRowProps> = ({
  setting,
  onRowClick,
  onEdit,
  onReset,
  disabled = false,
}) => {
  return (
    <div
      onClick={(e) => onRowClick(setting, e)}
      className="px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors cursor-pointer"
    >
      <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
        <div className="md:col-span-3">
          <div className="font-medium text-sm text-gray-900 dark:text-gray-100">
            {setting.display_name || setting.key}
          </div>
          {setting.key !== (setting.display_name || setting.key) && (
            <div className="text-xs text-gray-500 dark:text-gray-500 mt-0.5 font-mono">
              {setting.key}
            </div>
          )}
        </div>
        <div className="md:col-span-2">
          {setting.description && (
            <div className="text-xs text-gray-600 dark:text-gray-400 line-clamp-1">
              {setting.description}
            </div>
          )}
        </div>
        <div className="md:col-span-4">
          <SettingValueDisplay setting={setting} />
        </div>
        <div className="md:col-span-2 text-xs text-gray-500 dark:text-gray-500">
          {new Date(setting.updated_at).toLocaleDateString()}
        </div>
        <SettingActionButtons
          setting={setting}
          onEdit={onEdit}
          onReset={onReset}
          disabled={disabled}
        />
      </div>
    </div>
  );
};

