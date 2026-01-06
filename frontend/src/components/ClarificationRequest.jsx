/**
 * ClarificationRequest Component
 *
 * Displayed when the agent cannot find information and needs user help.
 * Shows:
 * - The reason clarification is needed
 * - What sources were searched (search trail)
 * - Clickable suggestions to help user rephrase
 */

import { HelpCircle, ArrowRight, Search, MessageCircle, Lightbulb } from 'lucide-react';

export function ClarificationRequest({
  reason,
  suggestions = [],
  searchTrail = [],
  onSuggestionClick,
  theme
}) {
  const themeClasses = theme?.classes || {};

  return (
    <div className={`rounded-xl overflow-hidden border-2 border-dashed
                     ${themeClasses.border || 'border-amber-300'}
                     ${themeClasses.bgSecondary || 'bg-amber-50'}`}>
      {/* Header */}
      <div className={`flex items-center gap-3 px-4 py-3
                       ${themeClasses.bgTertiary || 'bg-amber-100/50'}`}>
        <div className={`p-2 rounded-full ${themeClasses.bgPrimary || 'bg-amber-500'}`}>
          <HelpCircle size={18} className="text-white" />
        </div>
        <div>
          <h4 className={`font-medium ${themeClasses.text || 'text-amber-900'}`}>
            I need your help
          </h4>
          <p className={`text-xs ${themeClasses.textMuted || 'text-amber-700'}`}>
            Could you provide more details?
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Reason */}
        <div className="flex items-start gap-2">
          <MessageCircle size={16} className={themeClasses.textMuted || 'text-amber-600'} />
          <p className={`text-sm ${themeClasses.text || 'text-gray-700'}`}>
            {reason}
          </p>
        </div>

        {/* Search Trail Summary */}
        {searchTrail && searchTrail.length > 0 && (
          <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg
                           ${themeClasses.bgTertiary || 'bg-amber-100/30'}`}>
            <Search size={14} className={themeClasses.textMuted || 'text-amber-600'} />
            <span className={themeClasses.textMuted || 'text-amber-700'}>
              Searched:
            </span>
            <div className="flex flex-wrap gap-1">
              {searchTrail.map((trail, idx) => (
                <span
                  key={idx}
                  className={`px-2 py-0.5 rounded ${themeClasses.bgSecondary || 'bg-amber-100'}`}
                >
                  {trail}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Suggestions */}
        {suggestions && suggestions.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-1.5">
              <Lightbulb size={14} className={themeClasses.textMuted || 'text-amber-600'} />
              <span className={`text-xs font-medium ${themeClasses.textMuted || 'text-amber-700'}`}>
                Try one of these:
              </span>
            </div>

            <div className="flex flex-wrap gap-2">
              {suggestions.map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => onSuggestionClick?.(suggestion)}
                  className={`group flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm
                              font-medium transition-all hover:scale-[1.02] active:scale-[0.98]
                              ${themeClasses.bgPrimary || 'bg-amber-500'}
                              ${themeClasses.textOnPrimary || 'text-white'}
                              hover:shadow-md`}
                >
                  <span>{suggestion}</span>
                  <ArrowRight
                    size={14}
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                  />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Custom Input Hint */}
        <p className={`text-xs ${themeClasses.textMuted || 'text-amber-600'}`}>
          Or type your own question with more specific details.
        </p>
      </div>
    </div>
  );
}

export default ClarificationRequest;
