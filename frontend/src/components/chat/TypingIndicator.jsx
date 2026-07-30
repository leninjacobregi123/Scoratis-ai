import React from 'react';

export default function TypingIndicator({ currentSubject, isDark }) {
  const displayName = currentSubject ? `${currentSubject.icon} ${currentSubject.name}` : 'Socrates';

  return (
    <div className={`py-6 animate-fade-in ${isDark ? 'bg-white/5' : 'bg-bg-secondary/50'}`}>
      <div className="max-w-3xl mx-auto px-6">
        <div className="flex items-center gap-2 mb-4">
          <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-800'}`}>{displayName}</span>
          <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-text-muted/60'}`}>·</span>
          <span className={`text-xs animate-pulse ${isDark ? 'text-gray-400' : 'text-text-muted/60'}`}>thinking...</span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full animate-bounce ${isDark ? 'bg-white/60' : 'bg-gray-600'}`}
                style={{ animationDelay: `${i * 150}ms` }}
              />
            ))}
          </div>
          <span className={`text-sm ${isDark ? 'text-gray-300' : 'text-text-muted'}`}>Formulating a response...</span>
        </div>
      </div>
    </div>
  );
}
