import { useEffect, useRef, useState } from 'react';

// Renders Google's own "Sign in with Google" button via the Google
// Identity Services script (loaded in index.html). Polls briefly for
// window.google since the script tag is async/defer and may not have
// finished loading yet when this mounts. Renders nothing if
// VITE_GOOGLE_CLIENT_ID isn't set, rather than showing a button that
// can never work.
export default function GoogleSignInButton({ onCredential }) {
  const buttonRef = useRef(null);
  const [ready, setReady] = useState(false);
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!clientId) return;
    if (window.google?.accounts?.id) {
      setReady(true);
      return;
    }
    const interval = setInterval(() => {
      if (window.google?.accounts?.id) {
        setReady(true);
        clearInterval(interval);
      }
    }, 100);
    const timeout = setTimeout(() => clearInterval(interval), 10000);
    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [clientId]);

  useEffect(() => {
    if (!ready || !buttonRef.current) return;
    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: (response) => onCredential(response.credential),
    });
    window.google.accounts.id.renderButton(buttonRef.current, {
      theme: 'outline',
      size: 'large',
      width: 336,
      text: 'continue_with',
      shape: 'pill',
    });
  }, [ready, clientId, onCredential]);

  if (!clientId) return null;

  return <div ref={buttonRef} className="flex justify-center" />;
}
