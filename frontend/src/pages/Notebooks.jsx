/**
 * The notebook shelf: every notebook the student has, as a tree.
 *
 * Doubles as the first-run screen. A brand-new account has nothing here,
 * and an empty shelf with no obvious next step is a dead end - so when
 * there are no notebooks at all this renders a single "name your first
 * notebook" prompt instead of an empty list with a hidden + button.
 */
import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BookMarked as NotebookIcon, Plus, ChevronRight, ChevronDown,
  Loader2, Archive, Trash2, Pencil, FolderInput, MessageSquare, GraduationCap,
} from 'lucide-react';
import { useNotebook } from '../context/NotebookContext';
import { useApi } from '../hooks/useApi';

function Row({ node, childrenOf, depth, expanded, onToggle, onOpen, onAction, busyId }) {
  const kids = childrenOf.get(node.id) || [];
  const isOpen = expanded.has(node.id);
  const counts = node.counts || { conversations: 0, lessons: 0 };

  return (
    <>
      <div
        className="group flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-bg-secondary transition-colors"
        style={{ paddingLeft: `${12 + depth * 20}px` }}
      >
        <button
          onClick={() => onToggle(node.id)}
          className={`shrink-0 p-0.5 rounded ${kids.length ? 'text-text-muted hover:text-text-primary' : 'invisible'}`}
          aria-label={isOpen ? 'Collapse' : 'Expand'}
        >
          {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>

        <button onClick={() => onOpen(node)} className="flex items-center gap-2 min-w-0 flex-1 text-left">
          <NotebookIcon className="w-4 h-4 text-accent-olive shrink-0" />
          <span className="truncate text-text-primary">{node.name}</span>
          {(counts.conversations > 0 || counts.lessons > 0) && (
            <span className="flex items-center gap-2 text-xs text-text-muted shrink-0">
              {counts.conversations > 0 && (
                <span className="flex items-center gap-1">
                  <MessageSquare className="w-3 h-3" />{counts.conversations}
                </span>
              )}
              {counts.lessons > 0 && (
                <span className="flex items-center gap-1">
                  <GraduationCap className="w-3 h-3" />{counts.lessons}
                </span>
              )}
            </span>
          )}
        </button>

        {busyId === node.id ? (
          <Loader2 className="w-4 h-4 animate-spin text-text-muted" />
        ) : (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button onClick={() => onAction('add-child', node)} title="Add sub-notebook"
              className="p-1 rounded text-text-muted hover:text-text-primary"><Plus className="w-3.5 h-3.5" /></button>
            <button onClick={() => onAction('rename', node)} title="Rename"
              className="p-1 rounded text-text-muted hover:text-text-primary"><Pencil className="w-3.5 h-3.5" /></button>
            <button onClick={() => onAction('move', node)} title="Move"
              className="p-1 rounded text-text-muted hover:text-text-primary"><FolderInput className="w-3.5 h-3.5" /></button>
            <button onClick={() => onAction('archive', node)} title="Archive"
              className="p-1 rounded text-text-muted hover:text-text-primary"><Archive className="w-3.5 h-3.5" /></button>
            <button onClick={() => onAction('delete', node)} title="Delete"
              className="p-1 rounded text-text-muted hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
          </div>
        )}
      </div>

      {isOpen && kids.map((kid) => (
        <Row key={kid.id} node={kid} childrenOf={childrenOf} depth={depth + 1}
          expanded={expanded} onToggle={onToggle} onOpen={onOpen}
          onAction={onAction} busyId={busyId} />
      ))}
    </>
  );
}

export default function Notebooks() {
  const { notebooks, loading, refresh, openNotebook, createNotebook } = useNotebook();
  const api = useApi();
  const navigate = useNavigate();

  const [expanded, setExpanded] = useState(new Set());
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState(null);

  const childrenOf = useMemo(() => {
    const map = new Map();
    for (const n of notebooks) {
      const key = n.parent_id ?? null;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(n);
    }
    return map;
  }, [notebooks]);

  const roots = childrenOf.get(null) || [];

  const toggle = (id) => setExpanded((prev) => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const open = async (node) => {
    await openNotebook(node.id);
    navigate(`/app/notebooks/${node.id}`);
  };

  const create = async (parentId = null) => {
    const name = newName.trim();
    if (!name || creating) return;
    setCreating(true);
    setError(null);
    try {
      const created = await createNotebook({ name, parentId });
      setNewName('');
      await openNotebook(created.id);
      navigate(`/app/notebooks/${created.id}`);
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not create that notebook');
    } finally {
      setCreating(false);
    }
  };

  const action = async (kind, node) => {
    setError(null);
    try {
      if (kind === 'add-child') {
        const name = window.prompt(`Name the sub-notebook inside "${node.name}"`);
        if (!name?.trim()) return;
        setBusyId(node.id);
        await createNotebook({ name: name.trim(), parentId: node.id });
        setExpanded((prev) => new Set(prev).add(node.id));
      } else if (kind === 'rename') {
        const name = window.prompt('Rename notebook', node.name);
        if (!name?.trim() || name === node.name) return;
        setBusyId(node.id);
        await api.patch(`/notebooks/${node.id}`, { name: name.trim() });
        await refresh();
      } else if (kind === 'move') {
        const options = notebooks
          .filter((n) => n.id !== node.id)
          .map((n) => `${n.id}: ${n.name}`)
          .join('\n');
        const answer = window.prompt(
          `Move "${node.name}" into which notebook?\n\nEnter an id, or leave blank for top level.\n\n${options}`
        );
        if (answer === null) return;
        const parentId = answer.trim() ? Number(answer.trim()) : null;
        setBusyId(node.id);
        await api.patch(`/notebooks/${node.id}`, { parent_id: parentId });
        await refresh();
      } else if (kind === 'archive') {
        setBusyId(node.id);
        await api.patch(`/notebooks/${node.id}`, { archived: true });
        await refresh();
      } else if (kind === 'delete') {
        const counts = node.counts || { conversations: 0, lessons: 0 };
        const kids = (childrenOf.get(node.id) || []).length;
        // Say exactly what survives. The API unfiles rather than destroys,
        // and a warning that implies otherwise would make people archive
        // things they actually wanted gone.
        const detail = [
          kids && `${kids} sub-notebook${kids > 1 ? 's' : ''} will move to the top level`,
          counts.conversations && `${counts.conversations} chat${counts.conversations > 1 ? 's' : ''} will be kept but unfiled`,
          counts.lessons && `${counts.lessons} course${counts.lessons > 1 ? 's' : ''} will be kept but unfiled`,
        ].filter(Boolean).join('\n');
        const ok = window.confirm(
          `Delete "${node.name}"?\n\n${detail || 'It is empty.'}\n\nNothing you have made is deleted.`
        );
        if (!ok) return;
        setBusyId(node.id);
        await api.delete(`/notebooks/${node.id}?permanent=true`);
        await refresh();
      }
    } catch (e) {
      setError(e.response?.data?.detail || 'That did not work');
    } finally {
      setBusyId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-text-muted">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading your notebooks…
      </div>
    );
  }

  // First run: one prompt, no empty list.
  if (notebooks.length === 0) {
    return (
      <div className="max-w-lg mx-auto py-20 px-6 text-center">
        <NotebookIcon className="w-12 h-12 text-accent-olive mx-auto mb-4" />
        <h1 className="text-2xl font-semibold text-text-primary mb-2">Start a notebook</h1>
        <p className="text-text-muted mb-8">
          A notebook keeps everything for one subject together — your chats and the
          courses built from them — so you can pick up where you left off.
        </p>
        <div className="flex gap-2">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && create(null)}
            placeholder="e.g. Biology"
            autoFocus
            className="flex-1 px-4 py-3 rounded-xl bg-bg-secondary border border-border-color text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-olive"
          />
          <button
            onClick={() => create(null)}
            disabled={!newName.trim() || creating}
            className="px-5 py-3 rounded-xl bg-accent-olive hover:bg-accent-olive-dark text-white font-medium disabled:opacity-40"
          >
            {creating ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Create'}
          </button>
        </div>
        {error && <p className="text-sm text-red-400 mt-3">{error}</p>}
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto py-8 px-6">
      <h1 className="text-2xl font-semibold text-text-primary mb-1">Notebooks</h1>
      <p className="text-text-muted mb-6">Pick one to carry on, or start a new one.</p>

      <div className="flex gap-2 mb-6">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && create(null)}
          placeholder="New notebook name"
          className="flex-1 px-4 py-2.5 rounded-xl bg-bg-secondary border border-border-color text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-olive"
        />
        <button
          onClick={() => create(null)}
          disabled={!newName.trim() || creating}
          className="px-4 py-2.5 rounded-xl bg-accent-olive hover:bg-accent-olive-dark text-white font-medium disabled:opacity-40 flex items-center gap-2"
        >
          {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          New
        </button>
      </div>

      {error && <p className="text-sm text-red-400 mb-4">{error}</p>}

      <div className="rounded-xl border border-border-color bg-bg-card py-2">
        {roots.map((node) => (
          <Row key={node.id} node={node} childrenOf={childrenOf} depth={0}
            expanded={expanded} onToggle={toggle} onOpen={open}
            onAction={action} busyId={busyId} />
        ))}
      </div>
    </div>
  );
}
