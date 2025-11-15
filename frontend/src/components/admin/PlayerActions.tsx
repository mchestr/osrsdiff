import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import type { PlayerResponse } from '../../api/models/PlayerResponse';

interface PlayerActionsProps {
  player: PlayerResponse;
  onTriggerFetch: (username: string) => void;
  onRecalculateGameMode: (username: string) => void;
  onDeactivate: (username: string) => void;
  onReactivate: (username: string) => void;
  onDelete: (username: string) => void;
  activatingPlayer: string | null;
  deletingPlayer: string | null;
  recalculatingGameMode: string | null;
}

export const PlayerActions: React.FC<PlayerActionsProps> = ({
  player,
  onTriggerFetch,
  onRecalculateGameMode,
  onDeactivate,
  onReactivate,
  onDelete,
  activatingPlayer,
  deletingPlayer,
  recalculatingGameMode,
}) => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState<{ top: number; right: number } | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const isActivating = activatingPlayer === player.username;
  const isDeleting = deletingPlayer === player.username;
  const isRecalculating = recalculatingGameMode === player.username;

  const handleToggle = () => {
    if (!isOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setPosition({
        top: rect.bottom + 4,
        right: window.innerWidth - rect.right,
      });
    }
    setIsOpen(!isOpen);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node) &&
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setPosition(null);
      }
    };

    const handleScroll = () => {
      setIsOpen(false);
      setPosition(null);
    };

    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('scroll', handleScroll, true);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('scroll', handleScroll, true);
    };
  }, [isOpen]);

  const handleAction = (action: () => void) => {
    action();
    setIsOpen(false);
    setPosition(null);
  };

  const dropdownContent = isOpen && position ? (
    <div
      ref={dropdownRef}
      className="fixed w-48 rounded-md shadow-lg bg-white dark:bg-secondary-800 border border-secondary-200 dark:border-secondary-700 z-[9999]"
      style={{
        top: `${position.top}px`,
        right: `${position.right}px`,
      }}
      role="menu"
    >
      <div className="py-1">
        <button
          onClick={() => handleAction(() => navigate(`/players/${player.username}`))}
          className="w-full text-left px-4 py-2 text-sm osrs-text hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors flex items-center gap-2"
          role="menuitem"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          View Player
        </button>

        <button
          onClick={() => handleAction(() => onTriggerFetch(player.username))}
          className="w-full text-left px-4 py-2 text-sm osrs-text hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors flex items-center gap-2"
          role="menuitem"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Trigger Fetch
        </button>

        <button
          onClick={() => handleAction(() => onRecalculateGameMode(player.username))}
          disabled={isRecalculating}
          className="w-full text-left px-4 py-2 text-sm osrs-text hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          role="menuitem"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
          {isRecalculating ? 'Recalculating...' : 'Recalculate Game Mode'}
        </button>

        {player.is_active ? (
          <button
            onClick={() => handleAction(() => onDeactivate(player.username))}
            disabled={isActivating}
            className="w-full text-left px-4 py-2 text-sm osrs-text hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            role="menuitem"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
            {isActivating ? 'Deactivating...' : 'Deactivate'}
          </button>
        ) : (
          <button
            onClick={() => handleAction(() => onReactivate(player.username))}
            disabled={isActivating}
            className="w-full text-left px-4 py-2 text-sm osrs-text hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            role="menuitem"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {isActivating ? 'Reactivating...' : 'Reactivate'}
          </button>
        )}

        <div className="border-t border-secondary-200 dark:border-secondary-700 my-1" />

        <button
          onClick={() => handleAction(() => onDelete(player.username))}
          disabled={isDeleting}
          className="w-full text-left px-4 py-2 text-sm text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          role="menuitem"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          {isDeleting ? 'Deleting...' : 'Delete Player'}
        </button>
      </div>
    </div>
  ) : null;

  return (
    <>
      <button
        ref={buttonRef}
        onClick={handleToggle}
        className="osrs-btn px-2 py-1.5 text-sm font-medium hover:opacity-80 transition-opacity"
        aria-label="Actions menu"
        aria-expanded={isOpen}
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
          />
        </svg>
      </button>
      {createPortal(dropdownContent, document.body)}
    </>
  );
};

