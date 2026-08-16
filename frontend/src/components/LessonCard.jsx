/**
 * Inline lesson card for the chat thread.
 *
 * When the agent decides a question deserves a whole lesson rather than a
 * reply, it calls generate_lesson - a Celery job that takes minutes. Without
 * this card the only feedback was a sentence saying a lesson "is being
 * built", with no way to tell whether it worked or to reach it afterwards.
 *
 * Polls only while the lesson is actually building, then stops - a finished
 * lesson never changes, so continuing to poll would be pure noise.
 */
import { useState, useEffect } from 'react';
import { GraduationCap, Loader2, AlertCircle, ArrowRight, Check } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi';

const POLL_MS = 4000;

export default function LessonCard({ lessonId, requirement }) {
  const api = useApi();
  const navigate = useNavigate();
  const [lesson, setLesson] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!lessonId) return;
    let alive = true;
    let timer;

    const load = async () => {
      try {
        const data = await api.get(`/lessons/${lessonId}`);
        if (!alive) return;
        setLesson(data);
        if (data.status === 'pending' || data.status === 'generating') {
          timer = setTimeout(load, POLL_MS);
        }
      } catch {
        if (alive) setFailed(true);
      }
    };

    load();
    return () => { alive = false; clearTimeout(timer); };
  }, [lessonId, api]);

  if (!lessonId) return null;

  if (failed) {
    return (
      <div className="mt-3 p-3 rounded-xl border border-border-color bg-bg-card flex items-center gap-2 text-sm text-text-muted">
        <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
        That lesson could not be loaded.
      </div>
    );
  }

  const building = !lesson || lesson.status === 'pending' || lesson.status === 'generating';
  const errored = lesson?.status === 'failed';
  const done = lesson?.scene_count > 0 && lesson?.completed_count >= lesson?.scene_count;

  return (
    <button
      onClick={() => !building && navigate(`/app/lessons/${lessonId}`)}
      disabled={building}
      className={`mt-3 w-full text-left p-4 rounded-xl border transition-colors ${
        building
          ? 'border-border-color bg-bg-card cursor-default'
          : 'border-accent-olive/40 bg-accent-olive/5 hover:border-accent-olive cursor-pointer'
      }`}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 shrink-0">
          {building ? (
            <Loader2 className="w-5 h-5 text-accent-olive animate-spin" />
          ) : errored ? (
            <AlertCircle className="w-5 h-5 text-red-400" />
          ) : done ? (
            <Check className="w-5 h-5 text-accent-olive" />
          ) : (
            <GraduationCap className="w-5 h-5 text-accent-olive" />
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="text-xs uppercase tracking-wide text-text-muted mb-0.5">
            {building ? 'Building lesson' : errored ? 'Lesson failed' : 'Interactive lesson'}
          </div>
          <h4 className="font-semibold text-text-primary truncate">
            {lesson?.title || requirement || 'Lesson'}
          </h4>

          {lesson?.summary && !building && (
            <p className="text-sm text-text-muted mt-1 line-clamp-2">{lesson.summary}</p>
          )}

          {building ? (
            <>
              <p className="text-xs text-text-muted mt-1">
                {lesson?.message || 'Queued...'}
              </p>
              <div className="w-full h-1 bg-bg-tertiary rounded-full mt-2 overflow-hidden">
                <div
                  className="h-full bg-accent-olive transition-all duration-500"
                  style={{ width: `${lesson?.progress_percent || 0}%` }}
                />
              </div>
            </>
          ) : errored ? (
            <p className="text-xs text-text-muted mt-1">{lesson.error_message}</p>
          ) : (
            <div className="flex items-center gap-3 mt-2 text-xs text-text-muted">
              <span>{lesson.scene_count} scenes</span>
              {lesson.completed_count > 0 && (
                <span className={done ? 'text-accent-olive' : ''}>
                  {done ? '✓ Complete' : `${lesson.completed_count}/${lesson.scene_count} done`}
                </span>
              )}
              <span className="ml-auto flex items-center gap-1 text-accent-olive">
                Open <ArrowRight className="w-3 h-3" />
              </span>
            </div>
          )}
        </div>
      </div>
    </button>
  );
}
