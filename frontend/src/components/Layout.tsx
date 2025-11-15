import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { logout, isAdmin, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#1a1510' }}>
      {isAuthenticated && (
        <nav className="osrs-nav-header">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-20">
              {/* Logo and Navigation */}
              <div className="flex items-center space-x-8">
                <Link
                  to="/"
                  className="osrs-nav-logo"
                >
                  OSRS Diff
                </Link>
                <div className="hidden md:flex items-center space-x-1">
                  <Link
                    to="/"
                    className={`osrs-nav-link ${isActive('/') ? 'osrs-nav-link-active' : ''}`}
                  >
                    Players
                  </Link>
                  {isAdmin && (
                    <Link
                      to="/admin"
                      className={`osrs-nav-link ${isActive('/admin') ? 'osrs-nav-link-active' : ''}`}
                    >
                      Admin
                    </Link>
                  )}
                </div>
              </div>

              {/* User Section */}
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
            </div>
          </div>
        </nav>
      )}
      <main className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 ${isAuthenticated ? 'min-h-[calc(100vh-80px)]' : 'min-h-screen'}`} style={{ backgroundColor: '#1a1510' }}>
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


