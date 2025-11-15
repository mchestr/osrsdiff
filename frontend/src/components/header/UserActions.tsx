import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface UserActionsProps {
  onLogout?: () => void;
  className?: string;
}

export const UserActions = ({ onLogout, className = '' }: UserActionsProps) => {
  const { isAuthenticated, isAdmin, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    onLogout?.();
  };

  if (!isAuthenticated) {
    return (
      <Link
        to="/login"
        className={`px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600 transition-colors ${className}`}
      >
        Sign In
      </Link>
    );
  }

  return (
    <div className={`flex items-center space-x-4 ${className}`}>
      {isAdmin && (
        <span className="px-3 py-1 text-xs font-semibold text-primary-700 dark:text-primary-300 bg-primary-100 dark:bg-primary-900 rounded-full">
          Admin
        </span>
      )}
      <button
        onClick={handleLogout}
        className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
      >
        Logout
      </button>
    </div>
  );
};

