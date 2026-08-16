/**
 * Lesson player.
 *
 * Renders a generated lesson as a sequence of scenes. Each scene is a slide
 * (the @maic/dsl JSON the backend produced) plus an action list that drives
 * narration and spotlighting.
 *
 * Playback model: actions run in order. A `speech` action synthesises audio
 * via the existing /chat/tts endpoint (Edge TTS, free) and advances when the
 * audio ends; `spotlight` marks an element and advances immediately;
 * `play_video` plays the embedded Manim render to completion. That keeps the
 * narration and the visuals in step without needing precomputed timings.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { SlideCanvas, SlideRendererProvider } from '@maic/renderer';
import {
  ChevronLeft, ChevronRight, Play, Pause, Loader2, ArrowLeft, AlertCircle, Check,
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { getAuthHeaders } from '../utils/auth';
import LessonTutor from '../components/LessonTutor';

const POLL_MS = 3000;

export default function Lesson() {
  const { lessonId } = useParams();
  const navigate = useNavigate();
  const api = useApi();

  const [lesson, setLesson] = useState(null);
  const [error, setError] = useState(null);
  const [sceneIdx, setSceneIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [actionIdx, setActionIdx] = useState(-1);
  const [spotlightId, setSpotlightId] = useState(null);
  const [caption, setCaption] = useState('');
  const [completed, setCompleted] = useState([]);

  const audioRef = useRef(null);
  const cancelled = useRef(false);

  // ---- load + poll while still generating
  useEffect(() => {
    let timer;
    let alive = true;
    const load = async () => {
      try {
        const data = await api.get(`/lessons/${lessonId}`);
        if (!alive) return;
        setLesson(data);
        // Restore progress once, on first load - later polls must not stomp
        // scenes the learner has completed since.
        setCompleted((prev) => (prev.length ? prev : data.completed_scene_ids || []));
        setSceneIdx((prev) => (prev === 0 ? data.last_scene_index || 0 : prev));
        if (data.status === 'pending' || data.status === 'generating') {
          timer = setTimeout(load, POLL_MS);
        }
      } catch (e) {
        if (alive) setError(e.message || 'Could not load this lesson');
      }
    };
    load();
    return () => { alive = false; clearTimeout(timer); };
  }, [lessonId, api]);

  // Stop any in-flight narration when leaving or switching scenes.
  const stopPlayback = useCallback(() => {
    cancelled.current = true;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setPlaying(false);
    setActionIdx(-1);
    setSpotlightId(null);
    setCaption('');
  }, []);

  useEffect(() => stopPlayback, [stopPlayback]);

  const scenes = lesson?.scenes || [];
  const scene = scenes[sceneIdx];

  // /chat/tts returns the audio FILE (FileResponse, audio/mpeg) - not JSON
  // with a URL. Same handling as Chat.jsx: read it as a blob and play that.
  const speak = (text) =>
    new Promise((resolve) => {
      // If audio can't play for any reason, fall back to a read-time pause so
      // the lesson still advances instead of stalling on a silent scene.
      const readingPause = () => setTimeout(resolve, Math.min(8000, Math.max(1500, text.length * 55)));

      fetch('/chat/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ text }),
      })
        .then((r) => (r.ok ? r.blob() : Promise.reject(new Error('tts failed'))))
        .then((blob) => {
          if (cancelled.current) return resolve();
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audioRef.current = audio;
          const done = () => {
            URL.revokeObjectURL(url); // the blob is ours to clean up
            resolve();
          };
          audio.onended = done;
          audio.onerror = () => {
            URL.revokeObjectURL(url);
            readingPause();
          };
          audio.play().catch(() => {
            URL.revokeObjectURL(url);
            readingPause();
          });
        })
        .catch(readingPause);
    });

  const playScene = async () => {
    if (!scene) return;
    cancelled.current = false;
    setPlaying(true);
    const actions = scene.actions || [];

    for (let i = 0; i < actions.length; i++) {
      if (cancelled.current) break;
      const a = actions[i];
      setActionIdx(i);

      if (a.type === 'speech') {
        setCaption(a.content);
        await speak(a.content);
      } else if (a.type === 'spotlight') {
        setSpotlightId(a.elementId);
        await new Promise((r) => setTimeout(r, 600));
      } else if (a.type === 'play_video') {
        const el = document.querySelector('#lesson-canvas video');
        if (el) {
          await new Promise((resolve) => {
            el.onended = resolve;
            el.play().catch(resolve);
          });
        }
      }
    }
    if (!cancelled.current) {
      setPlaying(false);
      setActionIdx(-1);
      setSpotlightId(null);
      markComplete(scene.id);
    }
  };

  // Completion is earned by playing a scene through, not by clicking onto it -
  // otherwise skimming the tabs would mark the whole lesson done.
  const markComplete = (sceneId) => {
    if (!sceneId || completed.includes(sceneId)) return;
    setCompleted((prev) => [...prev, sceneId]);
    api.post(`/lessons/${lessonId}/progress`, { completed_scene_id: sceneId })
      .catch(() => { /* progress is best-effort; never block playback */ });
  };

  const goScene = (next) => {
    stopPlayback();
    setSceneIdx(next);
    api.post(`/lessons/${lessonId}/progress`, { last_scene_index: next })
      .catch(() => {});
  };

  // ---- states
  if (error) {
    return (
      <Shell onBack={() => navigate('/app/lessons')}>
        <div className="flex flex-col items-center justify-center h-64 text-text-muted">
          <AlertCircle className="w-10 h-10 mb-3 text-red-400" />
          <p>{error}</p>
        </div>
      </Shell>
    );
  }

  if (!lesson) {
    return (
      <Shell onBack={() => navigate('/app/lessons')}>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-accent-olive" />
        </div>
      </Shell>
    );
  }

  if (lesson.status === 'failed') {
    return (
      <Shell onBack={() => navigate('/app/lessons')} title={lesson.title}>
        <div className="flex flex-col items-center justify-center h-64 text-text-muted">
          <AlertCircle className="w-10 h-10 mb-3 text-red-400" />
          <p className="font-medium text-text-secondary">Lesson generation failed</p>
          <p className="text-sm mt-1 max-w-lg text-center">{lesson.error_message}</p>
        </div>
      </Shell>
    );
  }

  if (lesson.status !== 'completed' && scenes.length === 0) {
    return (
      <Shell onBack={() => navigate('/app/lessons')} title={lesson.title || 'Building your lesson'}>
        <div className="flex flex-col items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-accent-olive mb-4" />
          <p className="text-text-secondary">{lesson.message || 'Working...'}</p>
          <div className="w-64 h-1.5 bg-bg-tertiary rounded-full mt-4 overflow-hidden">
            <div
              className="h-full bg-accent-olive transition-all duration-500"
              style={{ width: `${lesson.progress_percent || 0}%` }}
            />
          </div>
        </div>
      </Shell>
    );
  }

  return (
    <Shell onBack={() => navigate('/app/lessons')} title={lesson.title}>
      {lesson.status !== 'completed' && (
        <div className="mb-3 text-xs text-text-muted">
          Still building — {lesson.message} ({lesson.progress_percent}%)
        </div>
      )}

      {/* Overall progress */}
      <div className="flex items-center gap-3 mb-3">
        <div className="flex-1 h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
          <div
            className="h-full bg-accent-olive transition-all duration-500"
            style={{ width: `${scenes.length ? (completed.length / scenes.length) * 100 : 0}%` }}
          />
        </div>
        <span className="text-xs text-text-muted whitespace-nowrap">
          {completed.length} of {scenes.length} complete
        </span>
      </div>

      {/* Scene strip */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {scenes.map((s, i) => {
          const done = completed.includes(s.id);
          return (
            <button
              key={s.id}
              onClick={() => goScene(i)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${
                i === sceneIdx
                  ? 'bg-accent-olive text-white'
                  : done
                  ? 'bg-accent-olive/15 text-text-secondary hover:text-text-primary'
                  : 'bg-bg-card text-text-muted hover:text-text-primary'
              }`}
            >
              {done && <Check className="w-3 h-3 shrink-0" />}
              {i + 1}. {s.title}
              {s.type === 'video' && ' ▸'}
            </button>
          );
        })}
      </div>

      {/* Slide + tutor. The tutor sits beside the slide rather than below it
          so the learner can see what they are asking about while they type. */}
      <div className="flex flex-col lg:flex-row gap-4 items-stretch">
        <div className="lg:flex-[2] min-w-0">
          <div
            id="lesson-canvas"
            className="relative w-full rounded-xl overflow-hidden border border-border-color"
            style={{ aspectRatio: '1000 / 562' }}
          >
            {scene?.slide && (
              <SlideRendererProvider>
                <SlideCanvas slide={withSpotlight(scene.slide, spotlightId)} />
              </SlideRendererProvider>
            )}
          </div>
        </div>

        <div className="lg:flex-1 min-w-0 lg:max-w-sm h-[340px] lg:h-auto">
          <LessonTutor
            lessonId={lesson.id}
            // Lessons created from the API have no originating chat, so fall
            // back to a deterministic per-lesson thread id. Stable across
            // reloads, and keeps each lesson's Q&A in its own conversation.
            sessionId={lesson.session_id || `lesson-${lesson.id}`}
            scene={scene}
            sceneTitle={scene?.title}
            onAsk={stopPlayback}
          />
        </div>
      </div>

      {/* Narration caption */}
      {caption && (
        <div className="mt-3 p-3 rounded-lg bg-bg-card border border-border-color text-sm text-text-secondary">
          {caption}
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center justify-between mt-4">
        <button
          onClick={() => goScene(Math.max(0, sceneIdx - 1))}
          disabled={sceneIdx === 0}
          className="flex items-center gap-1 px-3 py-2 rounded-lg text-text-muted hover:text-text-primary disabled:opacity-30"
        >
          <ChevronLeft className="w-4 h-4" /> Previous
        </button>

        <button
          onClick={playing ? stopPlayback : playScene}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent-olive hover:bg-accent-olive-dark text-white font-medium"
        >
          {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          {playing ? 'Stop' : 'Play scene'}
        </button>

        <button
          onClick={() => goScene(Math.min(scenes.length - 1, sceneIdx + 1))}
          disabled={sceneIdx >= scenes.length - 1}
          className="flex items-center gap-1 px-3 py-2 rounded-lg text-text-muted hover:text-text-primary disabled:opacity-30"
        >
          Next <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      <p className="text-center text-xs text-text-muted mt-3">
        Scene {sceneIdx + 1} of {scenes.length}
        {actionIdx >= 0 && ` · action ${actionIdx + 1}/${scene?.actions?.length || 0}`}
        {completed.includes(scene?.id) && ' · completed'}
      </p>

      {completed.length === scenes.length && scenes.length > 0 && (
        <div className="mt-4 p-4 rounded-xl bg-accent-olive/10 border border-accent-olive/30 text-center">
          <Check className="w-6 h-6 text-accent-olive mx-auto mb-1" />
          <p className="text-text-primary font-medium">Lesson complete</p>
          <p className="text-sm text-text-muted">
            You worked through all {scenes.length} scenes of {lesson.title}.
          </p>
        </div>
      )}
    </Shell>
  );
}

/** Dim everything except the spotlit element, by tweaking element opacity in
 *  a COPY of the slide - the renderer has its own overlay components, but
 *  they need the geometry plumbing that only pays off once we also do laser
 *  and annotation actions. */
function withSpotlight(slide, spotlightId) {
  if (!spotlightId) return slide;
  return {
    ...slide,
    elements: slide.elements.map((el) =>
      el.id === spotlightId ? el : { ...el, opacity: 0.35 }
    ),
  };
}

function Shell({ children, onBack, title }) {
  return (
    <div className="h-full overflow-y-auto p-8 bg-bg-primary">
      <div className="max-w-5xl mx-auto">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-text-muted hover:text-text-primary mb-4 text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Lessons
        </button>
        {title && (
          <h1
            className="text-2xl font-semibold text-text-primary mb-4"
            style={{ fontFamily: 'Georgia, serif' }}
          >
            {title}
          </h1>
        )}
        {children}
      </div>
    </div>
  );
}
