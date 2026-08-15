import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Home from './pages/Home';
import Chat from './pages/Chat';
import VideoVault from './pages/VideoVault';
import Lessons from './pages/Lessons';
import Notebooks from './pages/Notebooks';
import NotebookDetail from './pages/NotebookDetail';
import Review from './pages/Review';
import Lesson from './pages/Lesson';
import Settings from './pages/Settings';
import Login from './pages/Login';
import Signup from './pages/Signup';
import SharedTranscript from './pages/SharedTranscript';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NotebookProvider, useNotebook } from './context/NotebookContext';
import ErrorBoundary from './components/ErrorBoundary';

function RequireAuth({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-bg-primary grid-bg text-text-muted">Loading...</div>;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return children;
}

// Landing ("/") used to be the 3D Gallery itself, forcing every visitor -
// logged in or not - through its loading screen and subject picker before
// they could even sign in. Auth now comes first: signed-in users go
// straight to the app, everyone else goes straight to login. The Gallery
// and the whole subject-selection concept it existed for have since been
// removed entirely - Scoratis is one unified experience now.
function Landing() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-bg-primary grid-bg text-text-muted">Loading...</div>;
  }
  return <Navigate to={isAuthenticated ? '/app' : '/login'} replace />;
}

// The flow the app is built around: sign in, land in a notebook, study.
// Everything a student generates is filed into the active notebook, so
// "/app" resolves to one rather than to a generic dashboard - and to the
// create screen when they have none yet, which is the only honest place
// to send someone with nowhere to file anything.
function NotebookGate() {
  const { loading, activeId, notebooks } = useNotebook();

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center text-text-muted">
        Loading your notebooks...
      </div>
    );
  }
  if (!notebooks.length || !activeId) {
    return <Navigate to="/app/notebooks" replace />;
  }
  return <Navigate to={`/app/notebooks/${activeId}`} replace />;
}

function App() {
  return (
    <ErrorBoundary>
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Landing />} />

          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/shared/:token" element={<SharedTranscript />} />

          {/* Main Scoratis Application with Nested Routes - requires auth */}
          <Route
            path="/app"
            element={
              <RequireAuth>
                <NotebookProvider>
                  <Dashboard />
                </NotebookProvider>
              </RequireAuth>
            }
          >
            <Route index element={<NotebookGate />} />
            <Route path="notebooks" element={<Notebooks />} />
            <Route path="notebooks/:notebookId" element={<NotebookDetail />} />
            <Route path="review" element={<Review />} />
            <Route path="home" element={<Home />} />
            <Route path="scoratis" element={<Chat />} />
            <Route path="videos" element={<VideoVault />} />
            <Route path="lessons" element={<Lessons />} />
            <Route path="lessons/:lessonId" element={<Lesson />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </AuthProvider>
    </Router>
    </ErrorBoundary>
  );
}

export default App;
