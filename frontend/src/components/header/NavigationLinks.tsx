import { Link } from 'react-router-dom';

interface NavigationLinksProps {
  isAdmin: boolean;
  isActive: (path: string) => boolean;
  className?: string;
  onLinkClick?: () => void;
}

export const NavigationLinks = ({
  isAdmin,
  isActive,
  className = '',
  onLinkClick,
}: NavigationLinksProps) => {
  if (!isAdmin) {
    return null;
  }

  return (
    <div className={className}>
      <Link
        to="/admin"
        onClick={onLinkClick}
        className={`text-sm font-medium transition-colors ${
          isActive('/admin') && !isActive('/admin/players')
            ? 'text-primary-600 dark:text-primary-400'
            : 'text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400'
        }`}
      >
        Dashboard
      </Link>
      <Link
        to="/admin/players"
        onClick={onLinkClick}
        className={`text-sm font-medium transition-colors ${
          isActive('/admin/players')
            ? 'text-primary-600 dark:text-primary-400'
            : 'text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400'
        }`}
      >
        Manage Players
      </Link>
    </div>
  );
};

