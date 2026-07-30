import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { TrendingUp, MessageCircle, Layers, Award, Loader, BarChart3 } from 'lucide-react';
import { useApi } from '../hooks/useApi';

function masteryColor(score) {
  if (score >= 70) return { bar: 'bg-emerald-500', text: 'text-emerald-500' };
  if (score >= 40) return { bar: 'bg-accent-olive', text: 'text-accent-olive' };
  return { bar: 'bg-amber-500', text: 'text-amber-500' };
}

export default function Progress() {
  const api = useApi();
  const navigate = useNavigate();
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api.get('/progress')
      .then((data) => { if (!cancelled) setSubjects(data.subjects || []); })
      .catch((err) => { if (!cancelled) setError(err.message || 'Failed to load progress'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [api]);

  return (
    <div className="p-8 h-full overflow-y-auto">
      <div className="flex items-center gap-4 mb-8">
        <BarChart3 className="w-8 h-8 text-accent-olive" />
        <div>
          <h1 className="text-3xl font-light text-text-primary" style={{ fontFamily: 'Georgia, serif' }}>Your Progress</h1>
          <p className="text-text-muted text-sm">Mastery, activity, and quiz performance by subject</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <Loader className="w-8 h-8 animate-spin text-accent-olive" />
        </div>
      ) : error ? (
        <div className="text-center py-16 text-red-400">{error}</div>
      ) : subjects.length === 0 ? (
        <div className="text-center py-16">
          <TrendingUp className="w-16 h-16 text-text-muted mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-text-secondary">No progress yet</h2>
          <p className="text-text-muted mb-6">Start a conversation or take a quiz to see your progress here.</p>
          <button
            onClick={() => navigate('/app/scoratis')}
            className="px-6 py-2.5 bg-accent-olive hover:bg-accent-olive-dark text-white rounded-xl transition-colors"
          >
            Start Learning
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {subjects.map((s) => {
            const colors = masteryColor(s.mastery_score);
            return (
              <div key={s.subject} className="bg-bg-card border border-border-color rounded-2xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-text-primary capitalize" style={{ fontFamily: 'Georgia, serif' }}>
                    {s.subject.replace(/_/g, ' ')}
                  </h3>
                  <span className={`text-2xl font-bold ${colors.text}`}>{Math.round(s.mastery_score)}%</span>
                </div>

                <div className="w-full h-2 bg-bg-tertiary rounded-full overflow-hidden mb-5">
                  <div
                    className={`h-full ${colors.bar} rounded-full transition-all duration-500`}
                    style={{ width: `${Math.min(100, Math.max(0, s.mastery_score))}%` }}
                  />
                </div>

                <div className="grid grid-cols-3 gap-3 text-center">
                  <div>
                    <div className="flex items-center justify-center gap-1 text-text-muted mb-1">
                      <MessageCircle className="w-3.5 h-3.5" />
                    </div>
                    <div className="text-lg font-semibold text-text-primary">{s.total_turns}</div>
                    <div className="text-xs text-text-muted">Turns</div>
                  </div>
                  <div>
                    <div className="flex items-center justify-center gap-1 text-text-muted mb-1">
                      <Layers className="w-3.5 h-3.5" />
                    </div>
                    <div className="text-lg font-semibold text-text-primary">{s.total_sessions}</div>
                    <div className="text-xs text-text-muted">Sessions</div>
                  </div>
                  <div>
                    <div className="flex items-center justify-center gap-1 text-text-muted mb-1">
                      <Award className="w-3.5 h-3.5" />
                    </div>
                    <div className="text-lg font-semibold text-text-primary">
                      {s.quizzes_taken > 0 ? `${Math.round(s.quiz_average)}%` : '—'}
                    </div>
                    <div className="text-xs text-text-muted">{s.quizzes_taken} quiz{s.quizzes_taken === 1 ? '' : 'zes'}</div>
                  </div>
                </div>

                {s.last_active_at && (
                  <p className="text-xs text-text-muted mt-4 pt-4 border-t border-border-color/50">
                    Last active {new Date(s.last_active_at).toLocaleDateString()}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
