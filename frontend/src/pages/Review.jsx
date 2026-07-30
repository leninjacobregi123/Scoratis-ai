import { useState, useEffect, useCallback } from 'react';
import { Brain, Loader, CheckCircle2, RotateCcw } from 'lucide-react';
import { useApi } from '../hooks/useApi';

const QUALITY_OPTIONS = [
  { quality: 1, label: 'Forgot', color: 'bg-red-500/10 border-red-500/40 text-red-400 hover:bg-red-500/20' },
  { quality: 3, label: 'Hard', color: 'bg-amber-500/10 border-amber-500/40 text-amber-400 hover:bg-amber-500/20' },
  { quality: 4, label: 'Good', color: 'bg-accent-olive/10 border-accent-olive/40 text-accent-olive hover:bg-accent-olive/20' },
  { quality: 5, label: 'Easy', color: 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/20' },
];

export default function Review() {
  const api = useApi();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [gradedCount, setGradedCount] = useState(0);

  const loadDue = useCallback(() => {
    setLoading(true);
    api.get('/review/due')
      .then((data) => {
        setItems(data.due || []);
        setIndex(0);
        setRevealed(false);
        setGradedCount(0);
      })
      .finally(() => setLoading(false));
  }, [api]);

  useEffect(() => { loadDue(); }, [loadDue]);

  const current = items[index];

  const handleGrade = async (quality) => {
    if (!current) return;
    try {
      await api.post(`/review/${current.id}/grade`, { quality });
    } catch (err) {
      console.error('Grade failed:', err);
    }
    setGradedCount((c) => c + 1);
    setRevealed(false);
    setIndex((i) => i + 1);
  };

  const done = !loading && (items.length === 0 || index >= items.length);

  return (
    <div className="p-8 h-full overflow-y-auto flex flex-col items-center">
      <div className="w-full max-w-2xl">
        <div className="flex items-center gap-4 mb-8">
          <Brain className="w-8 h-8 text-accent-olive" />
          <div>
            <h1 className="text-3xl font-light text-text-primary" style={{ fontFamily: 'Georgia, serif' }}>Review</h1>
            <p className="text-text-muted text-sm">Spaced repetition of concepts you've discovered</p>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <Loader className="w-8 h-8 animate-spin text-accent-olive" />
          </div>
        ) : done ? (
          <div className="text-center py-16 bg-bg-card border border-border-color rounded-2xl">
            <CheckCircle2 className="w-16 h-16 text-accent-olive mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-text-primary mb-2">
              {gradedCount > 0 ? `Reviewed ${gradedCount} item${gradedCount === 1 ? '' : 's'}` : "You're all caught up"}
            </h2>
            <p className="text-text-muted mb-6">
              {items.length === 0 && gradedCount === 0
                ? 'Nothing is due for review right now. Chat with your tutor or take a quiz to build your review queue.'
                : 'Check back later for the next batch.'}
            </p>
            <button
              onClick={loadDue}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-bg-card border border-border-color hover:border-accent-olive rounded-xl text-text-secondary hover:text-text-primary transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        ) : (
          <>
            <div className="text-sm text-text-muted mb-3 text-center">
              {index + 1} of {items.length} · <span className="capitalize">{current.subject.replace(/_/g, ' ')}</span>
            </div>

            <div
              onClick={() => setRevealed((r) => !r)}
              className="min-h-[240px] bg-bg-card border border-border-color rounded-2xl p-8 flex items-center justify-center text-center cursor-pointer hover:border-accent-olive/40 transition-colors"
            >
              <div>
                <p className="text-xs uppercase tracking-wider text-text-muted mb-3">
                  {current.source_type === 'quiz_question' ? 'Question you missed' : 'Concept you discovered'}
                </p>
                <p className="text-xl text-text-primary" style={{ fontFamily: 'Georgia, serif' }}>{current.concept}</p>
                {!revealed && (
                  <p className="text-xs text-text-muted mt-6">Click to reveal grading options</p>
                )}
              </div>
            </div>

            {revealed && (
              <div className="grid grid-cols-4 gap-3 mt-4">
                {QUALITY_OPTIONS.map((opt) => (
                  <button
                    key={opt.quality}
                    onClick={() => handleGrade(opt.quality)}
                    className={`px-3 py-3 rounded-xl border font-medium text-sm transition-colors ${opt.color}`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
