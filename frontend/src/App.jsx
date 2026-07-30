import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Gallery from './pages/Gallery';
import Dashboard from './pages/Dashboard';
import Home from './pages/Home';
import Chat from './pages/Chat';
import VideoVault from './pages/VideoVault';
import Settings from './pages/Settings';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Progress from './pages/Progress';
import Review from './pages/Review';
import Quizzes from './pages/Quizzes';
import SharedTranscript from './pages/SharedTranscript';
import { AuthProvider, useAuth } from './context/AuthContext';
import ErrorBoundary from './components/ErrorBoundary';

function RequireAuth({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-bg-primary text-text-muted">Loading...</div>;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return children;
}

function App() {
  return (
    <ErrorBoundary>
    <Router>
      <AuthProvider>
        <Routes>
          {/* 3D Gallery Landing Page - stays public/browsable */}
          <Route path="/" element={<Gallery />} />

          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/shared/:token" element={<SharedTranscript />} />

          {/* Main Scoratis Application with Nested Routes - requires auth */}
          <Route
            path="/app"
            element={
              <RequireAuth>
                <Dashboard />
              </RequireAuth>
            }
          >
            <Route index element={<Home />} />
            <Route path="home" element={<Home />} />
            <Route path="scoratis" element={<Chat />} />
            <Route path="videos" element={<VideoVault />} />
            <Route path="progress" element={<Progress />} />
            <Route path="review" element={<Review />} />
            <Route path="quizzes" element={<Quizzes />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </AuthProvider>
    </Router>
    </ErrorBoundary>
  );
}

export default App;
