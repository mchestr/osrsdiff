import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { SearchBar } from './SearchBar';

interface MobileMenuProps {
  isOpen: boolean;
  onClose: () => void;
  onLogout?: () => void;
}

export const MobileMenu = ({ isOpen, onClose, onLogout }: MobileMenuProps) => {
  const { isAuthenticated, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    onClose();
    onLogout?.();
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="lg:hidden pb-4 pt-2 border-t border-gray-200 dark:border-gray-700">
      <div className="space-y-3">
        <SearchBar onSearch={onClose} className="pt-2" />
        {isAuthenticated ? (
          <button
            onClick={handleLogout}
            className="block w-full text-left py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
          >
            Logout
          </button>
        ) : (
          <Link
            to="/login"
            className="block py-2 text-sm font-medium text-primary-600 dark:text-primary-400"
            onClick={onClose}
          >
            Sign In
          </Link>
        )}
      </div>
    </div>
  );
};

