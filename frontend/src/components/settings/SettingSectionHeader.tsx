import React from 'react';

interface SettingSectionHeaderProps {
  title: string;
  description: string;
  isFirst?: boolean;
}

export const SettingSectionHeader: React.FC<SettingSectionHeaderProps> = ({
  title,
  description,
  isFirst = false,
}) => {
  return (
    <div className={`px-4 py-2 bg-gray-50 dark:bg-gray-700/60 border-b border-gray-200 dark:border-gray-600 ${isFirst ? '' : 'border-t'}`}>
      <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-100">{title}</h2>
      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{description}</p>
    </div>
  );
};

