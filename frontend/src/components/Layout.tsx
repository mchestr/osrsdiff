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
    <div className="min-h-screen" style={{ backgroundColor: '#1d1611' }}>
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
                  <>
                    <Link
                      to="/admin"
                      className={`osrs-nav-link ${isActive('/admin') ? 'osrs-nav-link-active' : ''}`}
                    >
                      Admin
                    </Link>
                    <Link
                      to="/task-executions"
                      className={`osrs-nav-link ${isActive('/task-executions') ? 'osrs-nav-link-active' : ''}`}
                    >
                      Task Executions
                    </Link>
                  </>
                )}
              </div>
            </div>

            {/* User Section */}
            <div className="flex items-center space-x-3">
              {isAuthenticated ? (
                <>
                  {isAdmin && (
                    <span className="osrs-nav-badge">Admin</span>
                  )}
                  <button
                    onClick={handleLogout}
                    className="osrs-nav-logout"
                  >
                    Logout
                  </button>
                </>
              ) : (
                <Link
                  to="/login"
                  className="osrs-nav-link"
                >
                  Login
                </Link>
              )}
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" style={{ backgroundColor: '#1d1611', minHeight: 'calc(100vh - 80px)' }}>
        {children}
      </main>
    </div>
  );
};

