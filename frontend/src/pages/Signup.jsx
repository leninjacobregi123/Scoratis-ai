import { useCallback, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import GoogleSignInButton from '../components/GoogleSignInButton';

export default function Signup() {
  const { signup, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const googleEnabled = Boolean(import.meta.env.VITE_GOOGLE_CLIENT_ID);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setSubmitting(true);
    try {
      await signup(username, email, password);
      navigate('/app', { replace: true });
    } catch (err) {
      setError(err.message || 'Signup failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleCredential = useCallback(async (credential) => {
    setError('');
    try {
      await loginWithGoogle(credential);
      navigate('/app', { replace: true });
    } catch (err) {
      setError(err.message || 'Google sign-in failed');
    }
  }, [loginWithGoogle, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary grid-bg px-4">
      <div className="w-full max-w-md bg-bg-card border border-border-color rounded-3xl p-8 shadow-xl">
        <div className="flex items-center justify-center mb-8">
          <div className="w-16 h-16 rounded-full overflow-hidden border border-border-color shadow-md bg-bg-tertiary">
            <img src="/socrates-nobg.png" alt="Scoratis" className="w-full h-full object-contain p-1.5" />
          </div>
        </div>
        <h1
          className="text-3xl font-light text-text-primary text-center mb-2"
          style={{ fontFamily: 'Georgia, serif' }}
        >
          Create your account
        </h1>
        <p className="text-text-muted text-center mb-8">Begin your Socratic learning journey</p>

        {error && (
          <div className="mb-6 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">
            {error}
          </div>
        )}

        {googleEnabled && (
          <>
            <GoogleSignInButton onCredential={handleGoogleCredential} />
            <div className="flex items-center gap-3 my-6">
              <div className="flex-1 h-px bg-border-color" />
              <span className="text-xs uppercase tracking-wider text-text-muted">or</span>
              <div className="flex-1 h-px bg-border-color" />
            </div>
          </>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1.5">Username</label>
            <input
              type="text"
              required
              minLength={3}
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 bg-bg-tertiary border border-border-color rounded-xl text-text-primary focus:outline-none focus:border-accent-olive transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1.5">Email</label>
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 bg-bg-tertiary border border-border-color rounded-xl text-text-primary focus:outline-none focus:border-accent-olive transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1.5">Password</label>
            <input
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-bg-tertiary border border-border-color rounded-xl text-text-primary focus:outline-none focus:border-accent-olive transition-colors"
            />
            <p className="text-xs text-text-muted mt-1.5">At least 8 characters</p>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3 bg-accent-olive hover:bg-accent-olive-dark disabled:opacity-60 text-white font-semibold rounded-xl transition-all"
          >
            {submitting ? 'Creating account...' : 'Sign up'}
          </button>
        </form>

        <p className="text-center text-text-muted text-sm mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-accent-olive hover:text-accent-olive-dark font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
