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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
    setMobileMenuOpen(false);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      navigate(`/players/${encodeURIComponent(searchTerm.trim())}`);
      setSearchTerm('');
      setMobileMenuOpen(false);
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
          <div className="flex justify-between items-center h-16 sm:h-20 gap-2 sm:gap-4">
            {/* Logo and Desktop Navigation */}
            <div className="flex items-center space-x-4 sm:space-x-8 flex-1 min-w-0">
              <Link
                to="/"
                className="osrs-nav-logo flex-shrink-0 text-lg sm:text-xl"
                onClick={() => setMobileMenuOpen(false)}
              >
                OSRS Diff
              </Link>
              {isAuthenticated && isAdmin && (
                <div className="hidden lg:flex items-center space-x-1">
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

            {/* Right Side: Desktop Search Bar and User Section */}
            <div className="hidden lg:flex items-center space-x-4 flex-shrink-0">
              {/* Search Bar */}
              <form onSubmit={handleSearch}>
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

            {/* Mobile Menu Button */}
            <div className="lg:hidden flex items-center gap-2">
              {isAuthenticated && (
                <>
                  {isAdmin && (
                    <span className="osrs-nav-badge text-xs px-2 py-0.5">Admin</span>
                  )}
                  <button
                    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    className="osrs-nav-logout p-2 min-w-[44px] min-h-[44px] flex items-center justify-center"
                    aria-label="Toggle menu"
                  >
                    <svg
                      className="w-6 h-6"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      style={{ color: '#ffd700' }}
                    >
                      {mobileMenuOpen ? (
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      ) : (
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                      )}
                    </svg>
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Mobile Menu Dropdown */}
          {mobileMenuOpen && (
            <div className="lg:hidden pb-4 pt-2 border-t" style={{ borderColor: '#8b7355' }}>
              <div className="space-y-2">
                {/* Mobile Search Bar */}
                <form onSubmit={handleSearch} className="mb-3">
                  <input
                    type="text"
                    placeholder="Search for a player..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full osrs-btn text-sm py-2.5 px-4"
                  />
                </form>

                {/* Mobile Navigation Links */}
                {isAuthenticated && isAdmin && (
                  <div className="flex flex-col space-y-1">
                    <Link
                      to="/admin"
                      className={`osrs-nav-link py-2.5 px-4 ${isActive('/admin') && !isActive('/admin/players') ? 'osrs-nav-link-active' : ''}`}
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      Dashboard
                    </Link>
                    <Link
                      to="/admin/players"
                      className={`osrs-nav-link py-2.5 px-4 ${isActive('/admin/players') ? 'osrs-nav-link-active' : ''}`}
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      Manage Players
                    </Link>
                  </div>
                )}

                {/* Mobile Logout Button */}
                {isAuthenticated && (
                  <button
                    onClick={handleLogout}
                    className="osrs-nav-logout w-full py-2.5 px-4 text-left"
                  >
                    Logout
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 lg:px-8 py-4 sm:py-6 md:py-8 min-h-[calc(100vh-64px)] sm:min-h-[calc(100vh-80px)]" style={{ backgroundColor: '#1a1510' }}>
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


