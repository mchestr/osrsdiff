import React from 'react';
import ironmanBadge from '../assets/images/ironman-badge.png';
import hardcoreIronmanBadge from '../assets/images/hardcore-ironman-badge.png';
import ultimateIronmanBadge from '../assets/images/ultimate-ironman-badge.png';

interface GameModeBadgeProps {
  gameMode: string | null | undefined;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const GameModeBadge: React.FC<GameModeBadgeProps> = ({
  gameMode,
  size = 'md',
  className = '',
}) => {
  if (!gameMode || gameMode === 'regular') {
    return null;
  }

  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  const badgeMap: Record<string, { src: string; alt: string }> = {
    ironman: {
      src: ironmanBadge,
      alt: 'Ironman',
    },
    hardcore: {
      src: hardcoreIronmanBadge,
      alt: 'Hardcore Ironman',
    },
    ultimate: {
      src: ultimateIronmanBadge,
      alt: 'Ultimate Ironman',
    },
  };

  const badge = badgeMap[gameMode.toLowerCase()];
  if (!badge) {
    return null;
  }

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full bg-secondary-100 dark:bg-secondary-800 p-0.5 ${sizeClasses[size]} ${className}`}
      title={badge.alt}
    >
      <img
        src={badge.src}
        alt={badge.alt}
        className="w-full h-full object-contain"
      />
    </span>
  );
};

