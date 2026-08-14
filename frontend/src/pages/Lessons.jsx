/**
 * Lessons index: create a lesson, and see the ones already built.
 *
 * Generation is a multi-minute Celery job, so rows for in-flight lessons poll
 * their own progress rather than waiting on a single blocking request.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { GraduationCap, Loader2, Plus, AlertCircle, Play } from 'lucide-react';
import { useApi } from '../hooks/useApi';

const POLL_MS = 4000;

export default function Lessons() {
  const api = useApi();
  const navigate = useNavigate();

  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [requirement, setRequirement] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const data = await api.get('/lessons');
      setLessons(data.lessons || []);
    } catch (e) {
      setError(e.message || 'Could not load lessons');
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => { load(); }, [load]);

  // Keep polling only while something is actually in flight.
  useEffect(() => {
    const busy = lessons.some((l) => l.status === 'pending' || l.status === 'generating');
    if (!busy) return;
    const t = setTimeout(load, POLL_MS);
    return () => clearTimeout(t);
  }, [lessons, load]);

  const create = async () => {
    const text = requirement.trim();
    if (!text || creating) return;
    setCreating(true);
    setError(null);
    try {
      const res = await api.post('/lessons', { requirement: text });
      setRequirement('');
      await load();
      if (res?.id) navigate(`/app/lessons/${res.id}`);
    } catch (e) {
      setError(e.message || 'Could not start that lesson');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-8 bg-bg-primary">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <GraduationCap className="w-7 h-7 text-accent-olive" />
          <h1
            className="text-3xl font-light text-text-primary"
            style={{ fontFamily: 'Georgia, serif' }}
          >
            Lessons
          </h1>
        </div>

        {/* Create */}
        <div className="glass-card rounded-xl p-5 mb-8 border border-border-color">
          <label className="block text-sm text-text-secondary mb-2">
            What would you like to learn?
          </label>
          <div className="flex gap-3">
            <input
              value={requirement}
              onChange={(e) => setRequirement(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && create()}
              placeholder="e.g. Teach me how a four-stroke engine works, from scratch"
              className="flex-1 px-4 py-2.5 rounded-lg bg-bg-secondary border border-border-color text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-olive"
            />
            <button
              onClick={create}
              disabled={creating || !requirement.trim()}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-accent-olive hover:bg-accent-olive-dark text-white font-medium disabled:opacity-40"
            >
              {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Build
            </button>
          </div>
          <p className="text-xs text-text-muted mt-2">
            Builds an outline, slides with narration, and animations where they help. Takes a few minutes.
          </p>
          {error && (
            <p className="text-xs text-red-400 mt-2 flex items-center gap-1">
              <AlertCircle className="w-3 h-3" /> {error}
            </p>
          )}
        </div>

        {/* List */}
        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-accent-olive" />
          </div>
        ) : lessons.length === 0 ? (
          <div className="text-center py-16 text-text-muted">
            <GraduationCap className="w-14 h-14 mx-auto mb-4 opacity-40" />
            <p className="text-text-secondary font-medium">No lessons yet</p>
            <p className="text-sm">Ask for a topic above and one will be built for you.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {lessons.map((l) => (
              <LessonRow key={l.id} lesson={l} onOpen={() => navigate(`/app/lessons/${l.id}`)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function LessonRow({ lesson, onOpen }) {
  const busy = lesson.status === 'pending' || lesson.status === 'generating';
  const failed = lesson.status === 'failed';
  const done = lesson.scene_count > 0 && lesson.completed_count >= lesson.scene_count;

  return (
    <button
      onClick={onOpen}
      className="w-full text-left p-4 rounded-xl bg-bg-card border border-border-color hover:border-accent-olive/50 transition-colors"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-text-primary truncate">
            {lesson.title || lesson.requirement}
          </h3>
          {lesson.summary && (
            <p className="text-sm text-text-muted mt-1 line-clamp-2">{lesson.summary}</p>
          )}
          <div className="flex items-center gap-3 mt-2 text-xs text-text-muted">
            <span>{new Date(lesson.created_at).toLocaleString()}</span>
            {lesson.scene_count > 0 && <span>{lesson.scene_count} scenes</span>}
            {lesson.scene_count > 0 && lesson.completed_count > 0 && (
              <span className={done ? 'text-accent-olive' : ''}>
                {done ? '✓ Complete' : `${lesson.completed_count}/${lesson.scene_count} done`}
              </span>
            )}
          </div>
          {lesson.scene_count > 0 && lesson.completed_count > 0 && !done && (
            <div className="w-full h-1 bg-bg-tertiary rounded-full mt-2 overflow-hidden">
              <div
                className="h-full bg-accent-olive/70"
                style={{ width: `${(lesson.completed_count / lesson.scene_count) * 100}%` }}
              />
            </div>
          )}
        </div>

        <div className="shrink-0">
          {busy ? (
            <div className="flex items-center gap-2 text-accent-olive text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              {lesson.progress_percent}%
            </div>
          ) : failed ? (
            <AlertCircle className="w-5 h-5 text-red-400" />
          ) : (
            <Play className="w-5 h-5 text-accent-olive" />
          )}
        </div>
      </div>

      {busy && (
        <div className="w-full h-1 bg-bg-tertiary rounded-full mt-3 overflow-hidden">
          <div
            className="h-full bg-accent-olive transition-all duration-500"
            style={{ width: `${lesson.progress_percent || 0}%` }}
          />
        </div>
      )}
    </button>
  );
}
