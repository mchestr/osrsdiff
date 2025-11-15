import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { logout, isAdmin, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchTerm, setSearchTerm] = useState('');

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      navigate(`/players/${encodeURIComponent(searchTerm.trim())}`);
      setSearchTerm('');
    }
  };

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#1a1510' }}>
      <nav className="osrs-nav-header">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20 gap-4">
            {/* Logo and Navigation */}
            <div className="flex items-center space-x-8 flex-1 min-w-0">
              <Link
                to="/"
                className="osrs-nav-logo flex-shrink-0"
              >
                OSRS Diff
              </Link>
              {isAuthenticated && isAdmin && (
                <div className="hidden md:flex items-center space-x-1">
                  <Link
                    to="/admin"
                    className={`osrs-nav-link ${isActive('/admin') && !isActive('/admin/players') ? 'osrs-nav-link-active' : ''}`}
                  >
                    Dashboard
                  </Link>
                  <Link
                    to="/admin/players"
                    className={`osrs-nav-link ${isActive('/admin/players') ? 'osrs-nav-link-active' : ''}`}
                  >
                    Manage Players
                  </Link>
                </div>
              )}
            </div>

            {/* Right Side: Search Bar and User Section */}
            <div className="flex items-center space-x-4 flex-shrink-0">
              {/* Search Bar */}
              <form onSubmit={handleSearch} className="hidden md:block">
                <input
                  type="text"
                  placeholder="Search for a player..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="osrs-btn text-sm py-2 w-64"
                />
              </form>

              {/* User Section */}
              {isAuthenticated && (
                <div className="flex items-center space-x-3">
                  {isAdmin && (
                    <span className="osrs-nav-badge">Admin</span>
                  )}
                  <button
                    onClick={handleLogout}
                    className="osrs-nav-logout"
                  >
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Mobile Search Bar */}
          <div className="md:hidden pb-4 pt-2">
            <form onSubmit={handleSearch}>
              <input
                type="text"
                placeholder="Search for a player..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full osrs-btn text-sm py-2"
              />
            </form>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 min-h-[calc(100vh-80px)]" style={{ backgroundColor: '#1a1510' }}>
        {children}
      </main>
      <footer className="border-t" style={{ borderColor: '#a68b5b', backgroundColor: '#1a1510' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-wrap justify-center gap-6">
            {!isAuthenticated && (
              <Link
                to="/login"
                className="osrs-footer-link"
              >
                Login
              </Link>
            )}
            <a
              href="https://github.com/mchestr/osrsdiff"
              target="_blank"
              rel="noopener noreferrer"
              className="osrs-footer-link"
            >
              GitHub
            </a>
            <a
              href="https://github.com/mchestr/osrsdiff/issues"
              target="_blank"
              rel="noopener noreferrer"
              className="osrs-footer-link"
            >
              Report Bug
            </a>
            <a
              href="https://github.com/mchestr/osrsdiff/issues"
              target="_blank"
              rel="noopener noreferrer"
              className="osrs-footer-link"
            >
              Request Feature
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};


