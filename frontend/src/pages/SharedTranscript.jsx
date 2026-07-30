import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Loader, MessageCircle } from 'lucide-react';

export default function SharedTranscript() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/shared/${token}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(res.status === 404 ? 'This shared link is invalid or has been revoked.' : 'Failed to load transcript.');
        return res.json();
      })
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <div className="min-h-screen bg-bg-primary flex flex-col items-center py-16 px-6">
      <div className="w-full max-w-2xl">
        <div className="flex items-center gap-3 mb-8">
          <MessageCircle className="w-6 h-6 text-accent-olive" />
          <span className="text-lg font-light text-text-primary" style={{ fontFamily: 'Georgia, serif' }}>Scoratis</span>
          <span className="text-text-muted text-sm">· Shared conversation</span>
        </div>

        {loading ? (
          <div className="flex justify-center py-24">
            <Loader className="w-8 h-8 animate-spin text-accent-olive" />
          </div>
        ) : error ? (
          <div className="text-center py-24">
            <p className="text-text-secondary mb-4">{error}</p>
            <Link to="/" className="text-accent-olive hover:underline">Go to Scoratis</Link>
          </div>
        ) : (
          <>
            <h1 className="text-2xl font-semibold text-text-primary mb-1" style={{ fontFamily: 'Georgia, serif' }}>
              {data.title || 'Untitled Conversation'}
            </h1>
            {data.subject && (
              <p className="text-sm text-text-muted mb-8 capitalize">{data.subject.replace(/_/g, ' ')}</p>
            )}

            <div className="space-y-6">
              {data.messages.map((m, i) => (
                <div key={i} className="bg-bg-card border border-border-color rounded-2xl p-5">
                  <div className="text-xs font-semibold text-accent-olive mb-2">
                    {m.role === 'user' ? 'Student' : 'Socrates'}
                  </div>
                  <p className="text-text-primary whitespace-pre-wrap leading-relaxed">{m.content}</p>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
