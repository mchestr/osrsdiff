import type { Setting, SettingSection } from './types';

// Helper function to determine section for a setting
export const getSettingSection = (key: string): string => {
  if (key.startsWith('openai_')) {
    return 'openai';
  }
  if (key.startsWith('jwt_')) {
    return 'jwt';
  }
  if (key.startsWith('database_')) {
    return 'database';
  }
  if (key.startsWith('redis_')) {
    return 'redis';
  }
  if (key.startsWith('taskiq_')) {
    return 'taskiq';
  }
  if (key.startsWith('admin_')) {
    return 'admin';
  }
  if (['environment', 'debug', 'log_level'].includes(key)) {
    return 'general';
  }
  return 'other';
};

// Helper function to group settings by section
export const groupSettingsBySection = (settings: Setting[]): SettingSection[] => {
  const sections: Record<string, Setting[]> = {
    general: [],
    database: [],
    redis: [],
    jwt: [],
    taskiq: [],
    admin: [],
    openai: [],
    other: [],
  };

  settings.forEach((setting) => {
    const section = getSettingSection(setting.key);
    sections[section].push(setting);
  });

  const result: SettingSection[] = [];

  if (sections.general.length > 0) {
    result.push({
      title: 'General Settings',
      description: 'Basic application configuration',
      settings: sections.general.sort((a, b) => a.key.localeCompare(b.key)),
    });
  }

  // Database and Redis settings are excluded from UI as they're not easily changeable
  // They're filtered out before grouping in the Settings page

  if (sections.jwt.length > 0) {
    result.push({
      title: 'Authentication Settings',
      description: 'Configure JWT token settings for user authentication',
      settings: sections.jwt.sort((a, b) => a.key.localeCompare(b.key)),
    });
  }

  if (sections.taskiq.length > 0) {
    result.push({
      title: 'TaskIQ Settings',
      description: 'Configure background task processing settings',
      settings: sections.taskiq.sort((a, b) => a.key.localeCompare(b.key)),
    });
  }

  if (sections.admin.length > 0) {
    result.push({
      title: 'Admin Settings',
      description: 'Configure default admin user settings',
      settings: sections.admin.sort((a, b) => a.key.localeCompare(b.key)),
    });
  }

  if (sections.openai.length > 0) {
    result.push({
      title: 'OpenAI Settings',
      description: 'Configure OpenAI API settings for AI-powered summary generation',
      settings: sections.openai.sort((a, b) => a.key.localeCompare(b.key)),
    });
  }

  if (sections.other.length > 0) {
    result.push({
      title: 'Other Settings',
      description: 'Additional application settings',
      settings: sections.other.sort((a, b) => a.key.localeCompare(b.key)),
    });
  }

  return result;
};

// Helper function to obfuscate secret values
export const obfuscateValue = (value: string): string => {
  if (!value) return '';
  // Show first 2 and last 2 characters, obfuscate the rest
  if (value.length <= 4) {
    return '•'.repeat(value.length);
  }
  return `${value.substring(0, 2)}${'•'.repeat(Math.min(value.length - 4, 20))}${value.substring(value.length - 2)}`;
};

