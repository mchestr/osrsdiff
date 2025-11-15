import React from 'react';
import type { Setting } from './types';
import { obfuscateValue } from './utils';

interface SettingValueDisplayProps {
  setting: Setting;
}

export const SettingValueDisplay: React.FC<SettingValueDisplayProps> = ({ setting }) => {
  if (setting.setting_type === 'boolean') {
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
        setting.value.toLowerCase() === 'true'
          ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
          : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-300'
      }`}>
        {setting.value.toLowerCase() === 'true' ? 'True' : 'False'}
      </span>
    );
  }

  return (
    <div className="font-mono text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded truncate max-w-full">
      {setting.is_secret ? obfuscateValue(setting.value) : setting.value}
    </div>
  );
};

