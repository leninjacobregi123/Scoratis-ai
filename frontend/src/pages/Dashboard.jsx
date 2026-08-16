import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Outlet, useNavigate, useLocation } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Toast from '../components/Toast';
import { useApi } from '../hooks/useApi';
import { useNotebook } from '../context/NotebookContext';

function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sessionId = searchParams.get('session');
  const navigate = useNavigate();
  const location = useLocation();

  const [stats, setStats] = useState({});
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Chat/Conversation state for sidebar
  const [conversations, setConversations] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(sessionId);

  const api = useApi();
  const { activeId: activeNotebookId } = useNotebook();

  useEffect(() => {
    loadData();
    loadConversations();
  }, []);

  // Update active session when URL changes
  useEffect(() => {
    setActiveSessionId(sessionId);
  }, [sessionId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsData, videosData] = await Promise.all([
        api.get('/stats'),
        api.get('/videos/generated')
      ]);
      setStats(statsData);
      setVideos(videosData.videos || []);
    } catch (error) {
      showToast('Failed to load data', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Load chat conversations for sidebar
  const loadConversations = useCallback(async () => {
    try {
      const data = await api.get(
        activeNotebookId ? `/chat/conversations?notebook_id=${activeNotebookId}` : '/chat/conversations'
      );
      setConversations(data.conversations || []);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  }, [api]);

  // Handle new chat creation
  const handleNewChat = useCallback(() => {
    const newSessionId = 'session_' + Date.now();
    setActiveSessionId(newSessionId);
    // Navigate to scoratis chat with new session
    navigate('/app/scoratis');
  }, [navigate]);

  // Handle chat selection from sidebar
  const handleSelectChat = useCallback((conversationId) => {
    setActiveSessionId(conversationId);
    // Navigate to scoratis chat with selected session
    navigate(`/app/scoratis?session=${conversationId}`);
  }, [navigate]);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  return (
    <div className="flex h-screen bg-bg-primary">
      <Sidebar
        stats={stats}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        recentChats={conversations}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        activeSessionId={activeSessionId}
      />

      <main className="flex-1 overflow-hidden relative">
        {/* Grid Background */}
        <div className="absolute inset-0 grid-bg pointer-events-none" />

        <Outlet context={{
          stats,
          videos,
          loading,
          initialSessionId: sessionId,
          // Chat-related context for updating sidebar
          conversations,
          activeSessionId,
          onConversationCreated: loadConversations,
          setActiveSessionId
        }} />

      </main>

      {/* Toast */}
      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  );
}

export default Dashboard;
