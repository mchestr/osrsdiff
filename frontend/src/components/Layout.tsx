import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#1d1611' }}>
      <nav className="osrs-card border-b-0 rounded-none" style={{ borderBottom: '3px solid #1d1611', marginBottom: 0 }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <Link to="/" className="flex items-center px-2 py-2 text-xl font-bold osrs-card-title">
                OSRS Diff
              </Link>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link
                  to="/"
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium osrs-text hover:opacity-80 transition-opacity"
                >
                  Player Stats
                </Link>
                {isAdmin && (
                  <Link
                    to="/admin"
                    className="inline-flex items-center px-1 pt-1 text-sm font-medium osrs-text hover:opacity-80 transition-opacity"
                  >
                    Admin Dashboard
                  </Link>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm osrs-text">Welcome, {user?.username}</span>
              {isAdmin && (
                <span className="px-2 py-1 text-xs font-semibold osrs-text" style={{ backgroundColor: 'rgba(255, 215, 0, 0.2)', border: '1px solid #ffd700' }}>
                  Admin
                </span>
              )}
              <button
                onClick={handleLogout}
                className="osrs-btn text-sm"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8" style={{ backgroundColor: '#1d1611' }}>
        {children}
      </main>
    </div>
  );
};

