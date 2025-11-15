import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Header } from './header';
import { Sidebar } from './sidebar';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  // Sidebar state - on mobile it's toggleable, on desktop it's always visible via CSS
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // Collapsed state - persisted in localStorage
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const stored = localStorage.getItem('sidebarCollapsed');
    return stored === 'true';
  });

  const toggleSidebar = () => {
    setSidebarOpen((prev) => !prev);
  };

  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  const toggleCollapse = () => {
    setSidebarCollapsed((prev) => {
      const newValue = !prev;
      localStorage.setItem('sidebarCollapsed', String(newValue));
      return newValue;
    });
  };

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={closeSidebar}
        collapsed={sidebarCollapsed}
      />
      <Header
        onSidebarToggle={toggleSidebar}
        onToggleCollapse={toggleCollapse}
        sidebarCollapsed={sidebarCollapsed}
      />

      {/* Main Content with top padding for fixed nav and left padding for sidebar */}
      <main
        className={`pt-20 transition-all duration-300 ${
          sidebarCollapsed ? 'lg:pl-16' : 'lg:pl-64'
        }`}
      >
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="col-span-1 md:col-span-2">
              <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-4">OSRS Diff</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                The open source Old School RuneScape player progress tracker.
              </p>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Links</h4>
              <ul className="space-y-2">
                {!isAuthenticated && (
                  <li>
                    <Link
                      to="/login"
                      className="text-sm text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
                    >
                      Login
                    </Link>
                  </li>
                )}
                <li>
                  <a
                    href="https://github.com/mchestr/osrsdiff"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
                  >
                    GitHub
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Support</h4>
              <ul className="space-y-2">
                <li>
                  <a
                    href="https://github.com/mchestr/osrsdiff/issues"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
                  >
                    Report Bug
                  </a>
                </li>
                <li>
                  <a
                    href="https://github.com/mchestr/osrsdiff/issues"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
                  >
                    Request Feature
                  </a>
                </li>
              </ul>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t border-gray-200 dark:border-gray-700 text-center text-sm text-gray-600 dark:text-gray-400">
            <p>© {new Date().getFullYear()} OSRS Diff. Open source project.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};


