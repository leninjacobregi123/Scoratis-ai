import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error('Uncaught error in component tree:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-[#f5f0e6] text-[#4a5a40] p-8 text-center">
          <h1 className="text-2xl font-serif italic">Something went wrong</h1>
          <p className="text-sm text-[#8a8a7a] max-w-md">
            Scoratis hit an unexpected error and couldn't continue. Reloading usually fixes it.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="bg-[#4a5a40] text-[#f5f0e6] px-8 py-3 rounded-full font-bold text-xs uppercase tracking-widest hover:bg-[#3a4a30] transition-colors"
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
