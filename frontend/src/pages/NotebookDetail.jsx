/**
 * Inside one notebook: its sub-notebooks, chats and generated courses,
 * with the one action that matters most - start studying - at the top.
 *
 * Opening this page is what marks the notebook as active, so a deep link
 * or a browser refresh lands the student in the right place rather than
 * silently leaving the previous notebook active underneath.
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  BookMarked as NotebookIcon, MessageSquare, GraduationCap, Loader2,
  ChevronRight, Sparkles, AlertCircle,
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { useNotebook } from '../context/NotebookContext';

export default function NotebookDetail() {
  const { notebookId } = useParams();
  const api = useApi();
  const navigate = useNavigate();
  const { openNotebook, breadcrumb, activeId } = useNotebook();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const id = Number(notebookId);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.get(`/notebooks/${id}/contents`));
    } catch (e) {
      setError(e.response?.status === 404 ? 'That notebook no longer exists.' : 'Could not open that notebook');
    } finally {
      setLoading(false);
    }
  }, [api, id]);

  useEffect(() => { load(); }, [load]);

  // Landing here IS opening it - deep links and refreshes included.
  useEffect(() => {
    if (!Number.isNaN(id) && id !== activeId) openNotebook(id);
  }, [id, activeId, openNotebook]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-text-muted">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Opening…
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-lg mx-auto py-20 px-6 text-center">
        <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
        <p className="text-text-primary mb-4">{error}</p>
        <Link to="/app/notebooks" className="text-accent-olive hover:underline">Back to notebooks</Link>
      </div>
    );
  }

  const { notebook, children = [], conversations = [], lessons = [] } = data || {};
  const empty = !children.length && !conversations.length && !lessons.length;

  return (
    <div className="max-w-4xl mx-auto py-8 px-6">
      <nav className="flex items-center gap-1 text-sm text-text-muted mb-4 flex-wrap">
        <Link to="/app/notebooks" className="hover:text-text-primary">Notebooks</Link>
        {breadcrumb.map((n) => (
          <span key={n.id} className="flex items-center gap-1">
            <ChevronRight className="w-3.5 h-3.5" />
            <Link
              to={`/app/notebooks/${n.id}`}
              className={n.id === id ? 'text-text-primary' : 'hover:text-text-primary'}
            >
              {n.name}
            </Link>
          </span>
        ))}
      </nav>

      <div className="flex items-start justify-between gap-4 mb-8">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold text-text-primary flex items-center gap-2">
            <NotebookIcon className="w-6 h-6 text-accent-olive shrink-0" />
            {notebook?.name}
          </h1>
          {notebook?.description && (
            <p className="text-text-muted mt-1">{notebook.description}</p>
          )}
        </div>
        <button
          onClick={() => navigate('/app/scoratis')}
          className="shrink-0 px-4 py-2.5 rounded-xl bg-accent-olive hover:bg-accent-olive-dark text-white font-medium flex items-center gap-2"
        >
          <Sparkles className="w-4 h-4" />
          Start studying
        </button>
      </div>

      {empty && (
        <div className="rounded-xl border border-border-color bg-bg-card p-10 text-center">
          <p className="text-text-primary mb-1">Nothing in here yet.</p>
          <p className="text-text-muted text-sm">
            Start studying and whatever you learn gets filed here.
          </p>
        </div>
      )}

      {children.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm uppercase tracking-wide text-text-muted mb-2">Sub-notebooks</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {children.map((c) => (
              <Link key={c.id} to={`/app/notebooks/${c.id}`}
                className="flex items-center gap-2 p-3 rounded-xl border border-border-color bg-bg-card hover:border-accent-olive transition-colors">
                <NotebookIcon className="w-4 h-4 text-accent-olive shrink-0" />
                <span className="truncate text-text-primary">{c.name}</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {lessons.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm uppercase tracking-wide text-text-muted mb-2">Courses</h2>
          <div className="space-y-2">
            {lessons.map((l) => (
              <Link key={l.id} to={`/app/lessons/${l.id}`}
                className="flex items-center gap-3 p-3 rounded-xl border border-border-color bg-bg-card hover:border-accent-olive transition-colors">
                <GraduationCap className="w-4 h-4 text-accent-olive shrink-0" />
                <span className="truncate text-text-primary flex-1">{l.title || l.requirement}</span>
                <span className="text-xs text-text-muted shrink-0">
                  {l.status === 'completed' ? `${l.scene_count} scenes` : l.status}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {conversations.length > 0 && (
        <section>
          <h2 className="text-sm uppercase tracking-wide text-text-muted mb-2">Chats</h2>
          <div className="space-y-2">
            {conversations.map((c) => (
              <button key={c.id}
                onClick={() => navigate(`/app/scoratis?conversation=${c.id}`)}
                className="w-full flex items-center gap-3 p-3 rounded-xl border border-border-color bg-bg-card hover:border-accent-olive transition-colors text-left">
                <MessageSquare className="w-4 h-4 text-accent-olive shrink-0" />
                <span className="truncate text-text-primary flex-1">{c.title || 'Untitled chat'}</span>
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
