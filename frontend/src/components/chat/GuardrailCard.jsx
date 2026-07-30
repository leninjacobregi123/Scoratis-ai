import React from 'react';

export default function GuardrailCard({ message, suggestedSubject, onSwitchSubject }) {
  const subjectName = suggestedSubject?.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 my-4 animate-fade-in">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center flex-shrink-0">
          <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <div className="flex-1">
          <h4 className="font-semibold text-amber-900 mb-2">Topic Guidance</h4>
          <div className="text-amber-800 text-sm leading-relaxed whitespace-pre-wrap">
            {message}
          </div>
          {suggestedSubject && (
            <button
              onClick={() => onSwitchSubject(suggestedSubject)}
              className="mt-3 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
              Switch to {subjectName}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
