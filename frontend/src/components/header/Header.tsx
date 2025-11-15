import { useNavigate } from 'react-router-dom';
import { SearchBar } from './SearchBar';
import { ThemeToggle } from './ThemeToggle';
import { UserActions } from './UserActions';

interface HeaderProps {
  onSidebarToggle: () => void;
  onToggleCollapse: () => void;
  sidebarCollapsed: boolean;
}

export const Header = ({ onSidebarToggle, onToggleCollapse, sidebarCollapsed }: HeaderProps) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    navigate('/login');
  };

  return (
    <nav
      className={`fixed top-0 right-0 left-0 z-40 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-700 shadow-sm transition-all duration-300 ${
        sidebarCollapsed ? 'lg:left-16' : 'lg:left-64'
      }`}
    >
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-20">
          {/* Left side - Sidebar Toggle (mobile: open/close, desktop: collapse/expand) */}
          <div className="flex items-center">
            <button
              onClick={onSidebarToggle}
              className="p-2 text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 transition-colors lg:hidden"
              aria-label="Toggle sidebar"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>
            <button
              onClick={onToggleCollapse}
              className="hidden lg:flex p-2 text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
              aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>
          </div>

          {/* Right side - Search Bar, Theme Toggle, and User Actions */}
          <div className="flex items-center space-x-4">
            {/* Search Bar */}
            <div className="hidden lg:block">
              <SearchBar />
            </div>

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* User Actions */}
            <UserActions onLogout={handleLogout} />
          </div>
        </div>
      </div>
    </nav>
  );
};

