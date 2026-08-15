/**
 * A review session: answer what is due, one question at a time.
 *
 * The queue decides what appears, so there is no list to browse and no way
 * to skip ahead - that is the whole mechanism. What the student controls is
 * how honestly they answer, so the screen is built around making the answer
 * the only thing on it.
 *
 * Free recall hides the answer until they have committed to one. Revealing
 * it early turns retrieval practice into re-reading, which is the passive
 * studying this feature exists to replace.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Brain, Loader2, Check, X, ArrowRight, RotateCcw, Trash2, PartyPopper,
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { useNotebook } from '../context/NotebookContext';

const GRADE_LABELS = {
  1: { label: 'Forgot', tone: 'text-red-400' },
  2: { label: 'Hard', tone: 'text-amber-400' },
  3: { label: 'Good', tone: 'text-accent-olive' },
  4: { label: 'Easy', tone: 'text-accent-olive' },
};

export default function Review() {
  const api = useApi();
  const navigate = useNavigate();
  const { activeId: notebookId, active: notebook } = useNotebook();

  const [queue, setQueue] = useState([]);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [response, setResponse] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get(
        notebookId ? `/review/due?notebook_id=${notebookId}` : '/review/due'
      );
      setQueue(data.items || []);
      setIndex(0);
    } catch (e) {
      setError('Could not load your review queue');
    } finally {
      setLoading(false);
    }
  }, [api, notebookId]);

  useEffect(() => { load(); }, [load]);

  const item = queue[index];

  const submit = async (body) => {
    if (submitting || !item) return;
    setSubmitting(true);
    setError(null);
    try {
      setResult(await api.post(`/review/${item.id}/answer`, body));
      setDone((d) => d + 1);
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not mark that answer');
    } finally {
      setSubmitting(false);
    }
  };

  const next = () => {
    setResult(null);
    setResponse('');
    setIndex((i) => i + 1);
  };

  const retire = async () => {
    if (!item) return;
    try {
      await api.post(`/review/${item.id}/retire`, {});
      next();
    } catch {
      setError('Could not remove that question');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-text-muted">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Finding what's due…
      </div>
    );
  }

  // Nothing due is a good outcome, not an empty state to apologise for.
  if (!queue.length || index >= queue.length) {
    const finished = done > 0;
    return (
      <div className="max-w-lg mx-auto py-24 px-6 text-center">
        {finished
          ? <PartyPopper className="w-12 h-12 text-accent-olive mx-auto mb-4" />
          : <Check className="w-12 h-12 text-accent-olive mx-auto mb-4" />}
        <h1 className="text-2xl font-semibold text-text-primary mb-2">
          {finished ? `${done} reviewed` : 'Nothing due'}
        </h1>
        <p className="text-text-muted mb-8">
          {finished
            ? 'That is everything for now. The ones you found hard will come back sooner.'
            : 'Come back when something is due, or study a lesson to build new questions.'}
        </p>
        <div className="flex gap-2 justify-center">
          <button
            onClick={load}
            className="px-4 py-2.5 rounded-xl border border-border-color text-text-secondary hover:text-text-primary hover:border-accent-olive transition-colors"
          >
            Check again
          </button>
          <button
            onClick={() => navigate(notebookId ? `/app/notebooks/${notebookId}` : '/app/notebooks')}
            className="px-4 py-2.5 rounded-xl bg-accent-olive hover:bg-accent-olive-dark text-white font-medium"
          >
            Back to {notebook?.name || 'notebooks'}
          </button>
        </div>
      </div>
    );
  }

  const isMcq = item.kind === 'mcq' && Array.isArray(item.options);

  return (
    <div className="max-w-2xl mx-auto py-8 px-6">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-2 text-text-muted text-sm">
          <Brain className="w-4 h-4 text-accent-olive" />
          Review{notebook ? ` · ${notebook.name}` : ''}
        </div>
        <div className="text-sm text-text-muted tabular-nums">
          {index + 1} of {queue.length}
        </div>
      </div>

      <div className="h-1 bg-bg-tertiary rounded-full mb-8 overflow-hidden">
        <div
          className="h-full bg-accent-olive transition-all duration-300"
          style={{ width: `${(index / queue.length) * 100}%` }}
        />
      </div>

      <h2 className="text-xl text-text-primary mb-6 leading-relaxed">{item.prompt}</h2>

      {error && <p className="text-sm text-red-400 mb-4">{error}</p>}

      {!result && (
        <>
          {isMcq ? (
            <div className="space-y-2">
              {item.options.map((option) => (
                <button
                  key={option}
                  onClick={() => submit({ response: option })}
                  disabled={submitting}
                  className="w-full text-left px-4 py-3 rounded-xl border border-border-color bg-bg-card hover:border-accent-olive text-text-primary transition-colors disabled:opacity-50"
                >
                  {option}
                </button>
              ))}
            </div>
          ) : (
            <>
              <textarea
                value={response}
                onChange={(e) => setResponse(e.target.value)}
                placeholder="Write what you remember…"
                rows={5}
                autoFocus
                className="w-full px-4 py-3 rounded-xl bg-bg-secondary border border-border-color text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-olive resize-none"
              />
              <div className="flex items-center gap-2 mt-3">
                <button
                  onClick={() => submit({ response })}
                  disabled={!response.trim() || submitting}
                  className="px-5 py-2.5 rounded-xl bg-accent-olive hover:bg-accent-olive-dark text-white font-medium disabled:opacity-40 flex items-center gap-2"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  Check answer
                </button>
                {/* The honest way out when nothing comes to mind. Marking it
                    forgotten is more useful than guessing, and it comes back
                    within the session either way. */}
                <button
                  onClick={() => submit({ grade: 1 })}
                  disabled={submitting}
                  className="px-4 py-2.5 rounded-xl border border-border-color text-text-muted hover:text-text-primary transition-colors"
                >
                  I don't remember
                </button>
              </div>
            </>
          )}

          <button
            onClick={retire}
            className="mt-6 text-xs text-text-muted hover:text-red-400 flex items-center gap-1 transition-colors"
            title="Stop asking this question"
          >
            <Trash2 className="w-3 h-3" /> This question isn't right
          </button>
        </>
      )}

      {result && (
        <div className="rounded-xl border border-border-color bg-bg-card p-5">
          <div className="flex items-center gap-2 mb-3">
            {result.grade >= 3
              ? <Check className="w-5 h-5 text-accent-olive" />
              : <X className="w-5 h-5 text-red-400" />}
            <span className={`font-medium ${GRADE_LABELS[result.grade]?.tone}`}>
              {GRADE_LABELS[result.grade]?.label}
            </span>
          </div>

          {result.feedback && (
            <p className="text-text-secondary mb-4">{result.feedback}</p>
          )}

          <div className="text-sm text-text-muted mb-4">
            <div className="uppercase tracking-wide text-xs mb-1">Answer</div>
            <p className="text-text-secondary">{result.correct_answer}</p>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs text-text-muted flex items-center gap-1">
              <RotateCcw className="w-3 h-3" />
              {result.interval_days < 1
                ? 'Back later in this session'
                : `Back in ${Math.round(result.interval_days)} day${Math.round(result.interval_days) === 1 ? '' : 's'}`}
            </span>
            <button
              onClick={next}
              autoFocus
              className="px-4 py-2 rounded-xl bg-accent-olive hover:bg-accent-olive-dark text-white font-medium flex items-center gap-2"
            >
              Next <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
