import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { LoadingSpinner } from './components/LoadingSpinner';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Home } from './pages/Home';
import { PlayerStats } from './pages/PlayerStats';
import { AdminDashboard } from './pages/AdminDashboard';
import { AdminPlayerList } from './pages/AdminPlayerList';
import { TaskExecutions } from './pages/TaskExecutions';
import { TaskExecutionDetail } from './pages/TaskExecutionDetail';

const AppRoutes = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <LoadingSpinner message="Loading..." fullScreen />;
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
          <Layout>
            <Home />
          </Layout>
        }
      />
      <Route
        path="/players/:username"
        element={
          <Layout>
            <PlayerStats />
          </Layout>
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
        path="/admin/players"
        element={
          <ProtectedRoute requireAdmin>
            <Layout>
              <AdminPlayerList />
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
      <ThemeProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;

