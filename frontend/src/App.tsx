import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Home } from './pages/Home';
import { PlayerStats } from './pages/PlayerStats';
import { AdminDashboard } from './pages/AdminDashboard';
import { TaskExecutions } from './pages/TaskExecutions';
import { TaskExecutionDetail } from './pages/TaskExecutionDetail';

const AppRoutes = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen" style={{ backgroundColor: '#1d1611' }}>
        <div className="osrs-text text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={
          isAuthenticated ? <Navigate to="/" replace /> : <Login />
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout>
              <Home />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/players/:username"
        element={
          <ProtectedRoute>
            <Layout>
              <PlayerStats />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute requireAdmin>
            <Layout>
              <AdminDashboard />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/task-executions"
        element={
          <ProtectedRoute requireAdmin>
            <Layout>
              <TaskExecutions />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/task-executions/:id"
        element={
          <ProtectedRoute requireAdmin>
            <Layout>
              <TaskExecutionDetail />
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
};

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;

