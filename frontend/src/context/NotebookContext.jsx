/**
 * Which notebook the student is currently working in.
 *
 * Everything they do - chats, generated courses - is filed into the active
 * notebook, so this has to be resolved before the main screen is useful.
 * Resolution order on sign-in:
 *
 *   1. the id remembered in localStorage, if it still exists and is live
 *   2. whatever the server says was opened most recently
 *   3. nothing - the app sends them to create their first notebook
 *
 * The server is the authority, not localStorage: a notebook archived or
 * deleted on another device must not resurrect itself here just because
 * this browser still remembers the id.
 */
import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { useApi } from '../hooks/useApi';
import { useAuth } from './AuthContext';

const STORAGE_KEY = 'scoratis_active_notebook';

const NotebookContext = createContext(null);

export function NotebookProvider({ children }) {
  const api = useApi();
  const { isAuthenticated } = useAuth();

  const [notebooks, setNotebooks] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const data = await api.get('/notebooks');
    const list = data.notebooks || [];
    setNotebooks(list);
    return list;
  }, [api]);

  // Resolve the active notebook once per sign-in.
  useEffect(() => {
    if (!isAuthenticated) {
      setNotebooks([]);
      setActiveId(null);
      setLoading(false);
      return;
    }

    let alive = true;
    (async () => {
      setLoading(true);
      try {
        const list = await refresh();
        if (!alive) return;

        const remembered = Number(localStorage.getItem(STORAGE_KEY)) || null;
        const stillValid = remembered && list.some((n) => n.id === remembered);
        if (stillValid) {
          setActiveId(remembered);
          return;
        }

        const { notebook } = await api.get('/notebooks/recent');
        if (!alive) return;
        if (notebook) {
          setActiveId(notebook.id);
          localStorage.setItem(STORAGE_KEY, String(notebook.id));
        } else {
          setActiveId(null);
          localStorage.removeItem(STORAGE_KEY);
        }
      } catch {
        if (alive) setActiveId(null);
      } finally {
        if (alive) setLoading(false);
      }
    })();

    return () => { alive = false; };
  }, [isAuthenticated, api, refresh]);

  // Opening is a server-side event, not just local state: last_opened_at is
  // what "resume where you left off" reads on the next sign-in, including
  // from a different browser.
  const openNotebook = useCallback(async (id) => {
    setActiveId(id);
    localStorage.setItem(STORAGE_KEY, String(id));
    try {
      await api.post(`/notebooks/${id}/open`);
    } catch {
      /* the notebook is open locally either way */
    }
  }, [api]);

  const createNotebook = useCallback(async ({ name, parentId = null, description = '' }) => {
    const created = await api.post('/notebooks', {
      name,
      parent_id: parentId,
      description,
    });
    await refresh();
    return created;
  }, [api, refresh]);

  const active = useMemo(
    () => notebooks.find((n) => n.id === activeId) || null,
    [notebooks, activeId]
  );

  // Root-first path to the active notebook, for breadcrumbs.
  const breadcrumb = useMemo(() => {
    if (!active) return [];
    const byId = new Map(notebooks.map((n) => [n.id, n]));
    const path = [];
    const seen = new Set();
    let node = active;
    while (node && !seen.has(node.id)) {
      seen.add(node.id);
      path.unshift(node);
      node = node.parent_id ? byId.get(node.parent_id) : null;
    }
    return path;
  }, [active, notebooks]);

  const value = useMemo(() => ({
    notebooks,
    active,
    activeId,
    breadcrumb,
    loading,
    refresh,
    openNotebook,
    createNotebook,
  }), [notebooks, active, activeId, breadcrumb, loading, refresh, openNotebook, createNotebook]);

  return <NotebookContext.Provider value={value}>{children}</NotebookContext.Provider>;
}

export function useNotebook() {
  const ctx = useContext(NotebookContext);
  if (!ctx) throw new Error('useNotebook must be used inside a NotebookProvider');
  return ctx;
}
