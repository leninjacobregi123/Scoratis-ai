import { useState, useEffect, useCallback } from 'react';
import { GraduationCap, Loader, CheckCircle2, XCircle, RotateCcw, Sparkles } from 'lucide-react';
import { useApi } from '../hooks/useApi';

export default function Quizzes() {
  const api = useApi();
  const [subjects, setSubjects] = useState([]);
  const [subject, setSubject] = useState('physics');
  const [topic, setTopic] = useState('');
  const [numQuestions, setNumQuestions] = useState(5);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);

  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get('/subjects').then((data) => {
      setSubjects(data.subjects || []);
      if (data.subjects?.length) setSubject(data.subjects[0].id);
    }).catch(() => {});
  }, [api]);

  const handleGenerate = useCallback(async (e) => {
    e.preventDefault();
    if (!topic.trim()) return;
    setGenerating(true);
    setError(null);
    setResult(null);
    setAnswers({});
    try {
      const generated = await api.post('/quizzes/generate', {
        subject,
        topic: topic.trim(),
        num_questions: Number(numQuestions),
      });
      setQuiz(generated);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate quiz. The model may be slow right now - try again.');
    } finally {
      setGenerating(false);
    }
  }, [api, subject, topic, numQuestions]);

  const handleSubmit = useCallback(async () => {
    if (!quiz) return;
    setSubmitting(true);
    try {
      const res = await api.post(`/quizzes/${quiz.id}/submit`, { answers });
      setResult(res);
    } catch (err) {
      setError('Failed to submit quiz.');
    } finally {
      setSubmitting(false);
    }
  }, [api, quiz, answers]);

  const handleReset = () => {
    setQuiz(null);
    setAnswers({});
    setResult(null);
    setTopic('');
  };

  const allAnswered = quiz && quiz.questions.every((q) => answers[q.id]);

  return (
    <div className="p-8 h-full overflow-y-auto flex flex-col items-center">
      <div className="w-full max-w-2xl">
        <div className="flex items-center gap-4 mb-8">
          <GraduationCap className="w-8 h-8 text-accent-olive" />
          <div>
            <h1 className="text-3xl font-light text-text-primary" style={{ fontFamily: 'Georgia, serif' }}>Practice Quizzes</h1>
            <p className="text-text-muted text-sm">Generate practice questions on any topic</p>
          </div>
        </div>

        {!quiz && (
          <form onSubmit={handleGenerate} className="bg-bg-card border border-border-color rounded-2xl p-6 space-y-4">
            <div>
              <label className="block text-sm text-text-muted mb-1.5">Subject</label>
              <select
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full px-3 py-2.5 bg-bg-tertiary border border-border-color rounded-xl text-text-primary focus:outline-none focus:border-accent-olive"
              >
                {subjects.length > 0 ? subjects.map((s) => (
                  <option key={s.id} value={s.id}>{s.icon} {s.name}</option>
                )) : <option value="physics">Physics</option>}
              </select>
            </div>
            <div>
              <label className="block text-sm text-text-muted mb-1.5">Topic</label>
              <input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g. Newton's laws of motion"
                className="w-full px-3 py-2.5 bg-bg-tertiary border border-border-color rounded-xl text-text-primary focus:outline-none focus:border-accent-olive"
              />
            </div>
            <div>
              <label className="block text-sm text-text-muted mb-1.5">Number of questions</label>
              <input
                type="number"
                min={1}
                max={15}
                value={numQuestions}
                onChange={(e) => setNumQuestions(e.target.value)}
                className="w-full px-3 py-2.5 bg-bg-tertiary border border-border-color rounded-xl text-text-primary focus:outline-none focus:border-accent-olive"
              />
            </div>
            {error && <p className="text-sm text-red-400">{error}</p>}
            <button
              type="submit"
              disabled={generating || !topic.trim()}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-accent-olive hover:bg-accent-olive-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors"
            >
              {generating ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  Generating... this can take a minute
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Generate Quiz
                </>
              )}
            </button>
          </form>
        )}

        {quiz && !result && (
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-text-primary">{quiz.topic}</h2>
              <span className="text-xs text-text-muted capitalize">{quiz.subject.replace(/_/g, ' ')}</span>
            </div>

            {quiz.questions.map((q, i) => (
              <div key={q.id} className="bg-bg-card border border-border-color rounded-2xl p-5">
                <p className="text-text-primary font-medium mb-3">{i + 1}. {q.question_text}</p>
                <div className="space-y-2">
                  {q.options.map((opt) => (
                    <label
                      key={opt}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-xl border cursor-pointer transition-colors ${
                        answers[q.id] === opt
                          ? 'border-accent-olive bg-accent-olive/10 text-text-primary'
                          : 'border-border-color text-text-secondary hover:border-accent-olive/40'
                      }`}
                    >
                      <input
                        type="radio"
                        name={`q_${q.id}`}
                        checked={answers[q.id] === opt}
                        onChange={() => setAnswers((a) => ({ ...a, [q.id]: opt }))}
                        className="accent-accent-olive"
                      />
                      <span className="text-sm">{opt}</span>
                    </label>
                  ))}
                </div>
              </div>
            ))}

            <button
              onClick={handleSubmit}
              disabled={!allAnswered || submitting}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-accent-olive hover:bg-accent-olive-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors"
            >
              {submitting ? <Loader className="w-4 h-4 animate-spin" /> : 'Submit Answers'}
            </button>
          </div>
        )}

        {result && (
          <div className="space-y-5">
            <div className="bg-bg-card border border-border-color rounded-2xl p-6 text-center">
              <div className="text-4xl font-bold text-accent-olive mb-1">{Math.round(result.attempt.score)}%</div>
              <p className="text-text-muted text-sm">
                {result.attempt.answers.missed_question_ids.length === 0
                  ? 'Perfect score!'
                  : `${result.quiz.questions.length - result.attempt.answers.missed_question_ids.length} of ${result.quiz.questions.length} correct`}
              </p>
            </div>

            {result.quiz.questions.map((q, i) => {
              const selected = answers[q.id];
              const isCorrect = selected === q.correct_answer;
              return (
                <div key={q.id} className="bg-bg-card border border-border-color rounded-2xl p-5">
                  <div className="flex items-start gap-2 mb-2">
                    {isCorrect ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                    )}
                    <p className="text-text-primary font-medium">{i + 1}. {q.question_text}</p>
                  </div>
                  <div className="ml-7 space-y-1 text-sm">
                    {!isCorrect && <p className="text-red-400">Your answer: {selected}</p>}
                    <p className="text-emerald-500">Correct answer: {q.correct_answer}</p>
                    {q.explanation && <p className="text-text-muted mt-1">{q.explanation}</p>}
                  </div>
                </div>
              );
            })}

            <button
              onClick={handleReset}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-bg-card border border-border-color hover:border-accent-olive rounded-xl text-text-secondary hover:text-text-primary transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              New Quiz
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
