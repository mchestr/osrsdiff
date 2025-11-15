// OSRS skill order matching the game interface (3 columns x 8 rows)
export const OSRS_SKILL_ORDER = [
  'attack', 'hitpoints', 'mining',
  'strength', 'agility', 'smithing',
  'defence', 'herblore', 'fishing',
  'ranged', 'thieving', 'cooking',
  'prayer', 'crafting', 'firemaking',
  'magic', 'fletching', 'woodcutting',
  'runecraft', 'slayer', 'farming',
  'construction', 'hunter', 'sailing',
];

// OSRS experience table - experience required for each level
export const getExpForLevel = (level: number): number => {
  if (level <= 1) return 0;
  let total = 0;
  for (let i = 1; i < level; i++) {
    total += Math.floor(i + 300 * Math.pow(2, i / 7));
  }
  return Math.floor(total / 4);
};

// Calculate experience needed for next level
export const getExpToNextLevel = (currentLevel: number, currentExp: number): number => {
  if (currentLevel >= 99) return 0;
  const nextLevelExp = getExpForLevel(currentLevel + 1);
  return Math.max(0, nextLevelExp - currentExp);
};

// Calculate experience needed for max level (99)
export const getExpToMax = (currentLevel: number, currentExp: number): number => {
  if (currentLevel >= 99) return 0;
  const maxLevelExp = getExpForLevel(99);
  return Math.max(0, maxLevelExp - currentExp);
};

// Format time duration
export const formatDuration = (days: number): string => {
  if (days < 0) return 'N/A';
  if (days < 1) {
    const hours = Math.floor(days * 24);
    if (hours < 1) {
      const minutes = Math.floor(days * 24 * 60);
      return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
    }
    return `${hours} hour${hours !== 1 ? 's' : ''}`;
  }
  if (days < 7) {
    return `${Math.floor(days)} day${Math.floor(days) !== 1 ? 's' : ''}`;
  }
  if (days < 30) {
    const weeks = Math.floor(days / 7);
    const remainingDays = Math.floor(days % 7);
    if (remainingDays === 0) {
      return `${weeks} week${weeks !== 1 ? 's' : ''}`;
    }
    return `${weeks} week${weeks !== 1 ? 's' : ''}, ${remainingDays} day${remainingDays !== 1 ? 's' : ''}`;
  }
  if (days < 365) {
    const months = Math.floor(days / 30);
    const remainingDays = Math.floor(days % 30);
    if (remainingDays === 0) {
      return `${months} month${months !== 1 ? 's' : ''}`;
    }
    return `${months} month${months !== 1 ? 's' : ''}, ${remainingDays} day${remainingDays !== 1 ? 's' : ''}`;
  }
  const years = Math.floor(days / 365);
  const remainingDays = Math.floor(days % 365);
  if (remainingDays === 0) {
    return `${years} year${years !== 1 ? 's' : ''}`;
  }
  const months = Math.floor(remainingDays / 30);
  return `${years} year${years !== 1 ? 's' : ''}, ${months} month${months !== 1 ? 's' : ''}`;
};

