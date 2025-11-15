// Type definitions for skill and boss data
export interface SkillData {
  level?: number;
  experience?: number;
  rank?: number;
}

export interface BossData {
  kc?: number | null;
  rank?: number | null;
}

export type PlayerSummary = {
  summary_text: string;
  summary?: string;
  summary_points?: string[];
  generated_at: string;
  period_start: string;
  period_end: string;
};

export interface OrderedSkill {
  name: string;
  displayName: string;
  level: number;
  experience: number;
  maxLevel: number;
}

export interface OrderedBoss {
  name: string;
  displayName: string;
  kills: number;
  rank: number | null;
}

