import { Link } from 'react-router-dom';

interface MenuItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

interface SidebarMenuProps {
  items: MenuItem[];
  isActive: (path: string) => boolean;
  onLinkClick?: () => void;
  collapsed?: boolean;
}

export const SidebarMenu = ({ items, isActive, onLinkClick, collapsed = false }: SidebarMenuProps) => {
  return (
    <nav className="space-y-1">
      {items.map((item) => {
        const active = isActive(item.path);
        return (
          <Link
            key={item.path}
            to={item.path}
            onClick={onLinkClick}
            className={`
              flex items-center rounded-lg transition-colors
              ${collapsed ? 'justify-center px-3 py-3' : 'px-4 py-3'}
              text-sm font-medium
              ${
                active
                  ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
              }
            `}
            title={collapsed ? item.label : undefined}
          >
            <span className={`flex-shrink-0 ${collapsed ? '' : 'mr-3'}`}>{item.icon}</span>
            {!collapsed && <span>{item.label}</span>}
          </Link>
        );
      })}
    </nav>
  );
};

