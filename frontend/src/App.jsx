import { BrowserRouter as Router, Routes, Route, Outlet } from 'react-router-dom';
import Gallery from './pages/Gallery';
import Dashboard from './pages/Dashboard';
import Home from './pages/Home';
import Chat from './pages/Chat';
import VideoVault from './pages/VideoVault';
import Settings from './pages/Settings';

function App() {
  return (
    <Router>
      <Routes>
        {/* 3D Gallery Landing Page */}
        <Route path="/" element={<Gallery />} />

        {/* Main Scoratis Application with Nested Routes */}
        <Route path="/app" element={<Dashboard />}>
          <Route index element={<Home />} />
          <Route path="home" element={<Home />} />
          <Route path="scoratis" element={<Chat />} />
          <Route path="videos" element={<VideoVault />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
