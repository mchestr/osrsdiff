import { useState } from 'react';
import { Footer } from './Footer';
import { Header } from './header';
import { Sidebar } from './sidebar';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
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

      <Footer sidebarCollapsed={sidebarCollapsed} />
    </div>
  );
};


