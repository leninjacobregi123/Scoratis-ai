import { useState, useEffect } from 'react';
import { useSearchParams, Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Toast from '../components/Toast';
import JournalModal from '../components/JournalModal';
import FolderModal from '../components/FolderModal';
import { useApi } from '../hooks/useApi';

function Dashboard() {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session');

  const [stats, setStats] = useState({});
  const [folders, setFolders] = useState([]);
  const [journals, setJournals] = useState([]);
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);
  const [journalModal, setJournalModal] = useState({ open: false, journal: null });
  const [folderModal, setFolderModal] = useState(false);

  const api = useApi();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsData, foldersData, journalsData, videosData] = await Promise.all([
        api.get('/stats'),
        api.get('/folders'),
        api.get('/journals'),
        api.get('/videos/generated')
      ]);
      setStats(statsData);
      setFolders(foldersData);
      setJournals(journalsData);
      setVideos(videosData.videos || []);
    } catch (error) {
      showToast('Failed to load data', 'error');
    } finally {
      setLoading(false);
    }
  };

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleSaveJournal = async (data) => {
    try {
      if (journalModal.journal?.id) {
        await api.put(`/journals/${journalModal.journal.id}`, data);
        showToast('Journal updated!');
      } else {
        await api.post('/journals', data);
        showToast('Journal created!');
      }
      setJournalModal({ open: false, journal: null });
      loadData();
    } catch (error) {
      showToast('Failed to save journal', 'error');
    }
  };

  const handleSaveFolder = async (data) => {
    try {
      await api.post('/folders', data);
      showToast('Folder created!');
      setFolderModal(false);
      loadData();
    } catch (error) {
      showToast('Failed to create folder', 'error');
    }
  };

  return (
    <div className="flex h-screen bg-bg-primary">
      <Sidebar
        stats={stats}
        showGalleryLink={true}
      />

      <main className="flex-1 overflow-hidden relative">
        {/* Grid Background */}
        <div className="absolute inset-0 grid-bg pointer-events-none" />

        <Outlet context={{ stats, folders, journals, videos, loading, onNewJournal: () => setJournalModal({ open: true, journal: null }), onEditJournal: (journal) => setJournalModal({ open: true, journal }), onNewFolder: () => setFolderModal(true), initialSessionId: sessionId }} />

      </main>

      {/* Modals */}
      {journalModal.open && (
        <JournalModal
          journal={journalModal.journal}
          folders={folders}
          onSave={handleSaveJournal}
          onClose={() => setJournalModal({ open: false, journal: null })}
        />
      )}

      {folderModal && (
        <FolderModal
          onSave={handleSaveFolder}
          onClose={() => setFolderModal(false)}
        />
      )}

      {/* Toast */}
      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  );
}

export default Dashboard;
