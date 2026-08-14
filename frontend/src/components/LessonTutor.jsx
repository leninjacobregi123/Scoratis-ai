/**
 * Scene-grounded tutor panel.
 *
 * The Socratic tutor, docked beside the slide. Every message carries the
 * lesson and the scene the learner is currently on, so the backend can put
 * that scene's slide text and narration in the model's context (see
 * api/routes/chat.py::_build_lesson_scene_context). That is the whole point:
 * "why is the midpoint 4?" is answerable here and meaningless in a bare chat.
 *
 * Conversation state reuses the lesson's own session id, so the thread
 * persists with the lesson and every existing chat mechanism - history, RAG,
 * memory - works unchanged.
 */
import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, MessageCircleQuestion } from 'lucide-react';
import { getAuthHeaders, refreshAccessToken, clearTokens, getRefreshToken } from '../utils/auth';
import { stripReasoning } from '../utils/stripReasoning';

// Same retry rule as Chat.jsx: only a genuinely rejected refresh ends the
// session; a transient backend outage must not throw the learner out.
async function fetchWithAuthRetry(url, options) {
  const response = await fetch(url, options);
  if (response.status !== 401) return response;

  const newToken = await refreshAccessToken();
  if (!newToken) {
    if (!getRefreshToken()) {
      clearTokens();
      if (window.location.pathname !== '/login') window.location.href = '/login';
    }
    return response;
  }
  return fetch(url, {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${newToken}` },
  });
}

const SUGGESTIONS = [
  "I don't understand this part",
  'Why does that work?',
  'Can you give another example?',
];

export default function LessonTutor({ lessonId, sessionId, scene, sceneTitle, onAsk }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, busy]);

  // Abandon an in-flight answer if the component goes away, so a stream
  // can't keep writing into unmounted state.
  useEffect(() => () => abortRef.current?.abort(), []);

  const send = async (text) => {
    const content = (text ?? input).trim();
    if (!content || busy) return;

    setInput('');
    setMessages((m) => [...m, { role: 'user', content }]);
    setBusy(true);
    onAsk?.(); // let the player pause narration

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      const res = await fetchWithAuthRetry(`${baseUrl}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
          message: content,
          session_id: sessionId,
          use_web_search: false, // the answer should come from the lesson, not the web
          use_reasoning: false,
          lesson_id: lessonId,
          scene_id: scene?.id,
        }),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error('The tutor could not be reached');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let answer = '';
      setMessages((m) => [...m, { role: 'assistant', content: '' }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const line of decoder.decode(value, { stream: true }).split('\n')) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.chunk) {
              answer += data.chunk;
              setMessages((m) => {
                const next = [...m];
                next[next.length - 1] = { role: 'assistant', content: answer };
                return next;
              });
            }
          } catch { /* keep-alive or partial frame */ }
        }
      }

      if (!answer.trim()) {
        setMessages((m) => {
          const next = [...m];
          next[next.length - 1] = {
            role: 'assistant',
            content: "I couldn't put an answer together just then - try asking again.",
          };
          return next;
        });
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        setMessages((m) => [
          ...m,
          { role: 'assistant', content: `Something went wrong: ${e.message}` },
        ]);
      }
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  };

  return (
    <div className="flex flex-col h-full rounded-xl border border-border-color bg-bg-card overflow-hidden">
      <div className="px-4 py-3 border-b border-border-color flex items-center gap-2">
        <MessageCircleQuestion className="w-4 h-4 text-accent-olive shrink-0" />
        <span className="text-sm font-medium text-text-primary">Ask about this scene</span>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
        {messages.length === 0 && (
          <div className="text-sm text-text-muted">
            <p className="mb-3">
              Stuck on <span className="text-text-secondary">{sceneTitle}</span>? Ask and
              I'll answer about what's on screen.
            </p>
            <div className="space-y-1.5">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="block w-full text-left px-3 py-1.5 rounded-lg bg-bg-secondary hover:bg-bg-tertiary text-text-secondary text-xs transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={`text-sm rounded-lg px-3 py-2 ${
              m.role === 'user'
                ? 'bg-accent-olive/15 text-text-primary ml-6'
                : 'bg-bg-secondary text-text-secondary mr-2 whitespace-pre-wrap'
            }`}
          >
            {(m.role === 'assistant' ? stripReasoning(m.content) : m.content)
              || (busy && i === messages.length - 1 ? '…' : '')}
          </div>
        ))}

        {busy && (
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <Loader2 className="w-3 h-3 animate-spin" /> thinking…
          </div>
        )}
      </div>

      <div className="p-3 border-t border-border-color flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onFocus={onAsk}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Ask about this scene..."
          className="flex-1 min-w-0 px-3 py-2 rounded-lg bg-bg-secondary border border-border-color text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-olive"
        />
        <button
          onClick={() => send()}
          disabled={busy || !input.trim()}
          className="px-3 py-2 rounded-lg bg-accent-olive hover:bg-accent-olive-dark text-white disabled:opacity-40 shrink-0"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
