/**
 * SearchTrailIndicator Component
 *
 * Shows users which sources were searched during query processing.
 * Provides transparency about the Private-First search strategy:
 * - Knowledge Base searched first
 * - Web search as fallback
 * - Clear indication of results found
 */

import { Database, Globe, MessageSquare, CheckCircle, XCircle, Search } from 'lucide-react';

// Map tool names to icons
const SOURCE_ICONS = {
  search_knowledge_base: Database,
  knowledge_base: Database,
  web_search: Globe,
  search_past_conversations: MessageSquare,
};

// Map tool names to display labels
const SOURCE_LABELS = {
  search_knowledge_base: 'Your Notes',
  knowledge_base: 'Your Notes',
  web_search: 'Web Search',
  search_past_conversations: 'Past Chats',
};

/**
 * Single search attempt indicator
 */
function SearchAttemptBadge({ attempt, theme }) {
  const themeClasses = theme?.classes || {};
  const Icon = SOURCE_ICONS[attempt.source] || Search;
  const label = SOURCE_LABELS[attempt.source] || attempt.source.replace(/_/g, ' ');
  const hasResults = attempt.had_results || attempt.results_count > 0;

  return (
    <div
      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
                  transition-all ${hasResults
                    ? 'bg-green-100 text-green-700 border border-green-200'
                    : 'bg-gray-100 text-gray-500 border border-gray-200'
                  }`}
      title={`${label}: ${attempt.results_count || 0} results found`}
    >
      <Icon size={12} />
      <span>{label}</span>
      {hasResults ? (
        <span className="flex items-center gap-0.5">
          <CheckCircle size={10} className="text-green-600" />
          <span className="text-green-600">{attempt.results_count}</span>
        </span>
      ) : (
        <XCircle size={10} className="text-gray-400" />
      )}
    </div>
  );
}

/**
 * Main SearchTrailIndicator component
 */
export function SearchTrailIndicator({ searchTrail, theme, compact = false }) {
  const themeClasses = theme?.classes || {};

  // No trail or no attempts
  if (!searchTrail?.attempts?.length) return null;

  const attempts = searchTrail.attempts;
  const hasAnyResults = attempts.some(a => a.had_results || a.results_count > 0);
  const allFailed = !hasAnyResults && attempts.length > 0;

  if (compact) {
    // Compact mode - just icons
    return (
      <div className="flex items-center gap-1">
        {attempts.map((attempt, idx) => {
          const Icon = SOURCE_ICONS[attempt.source] || Search;
          const hasResults = attempt.had_results || attempt.results_count > 0;

          return (
            <div
              key={idx}
              className={`p-1 rounded ${hasResults ? 'text-green-600' : 'text-gray-400'}`}
              title={`${SOURCE_LABELS[attempt.source]}: ${attempt.results_count || 0} results`}
            >
              <Icon size={14} />
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className={`flex flex-wrap items-center gap-2 px-3 py-2 rounded-lg mb-3
                     ${themeClasses.bgSecondary || 'bg-gray-50'}
                     ${themeClasses.border ? `border ${themeClasses.border}` : 'border border-gray-200'}`}>
      {/* Label */}
      <span className={`text-xs font-medium ${themeClasses.textMuted || 'text-gray-500'}`}>
        <Search size={12} className="inline mr-1" />
        Sources searched:
      </span>

      {/* Search Attempts */}
      <div className="flex flex-wrap items-center gap-1.5">
        {attempts.map((attempt, idx) => (
          <SearchAttemptBadge
            key={idx}
            attempt={attempt}
            theme={theme}
          />
        ))}
      </div>

      {/* Status indicator */}
      {allFailed && (
        <span className="text-xs text-amber-600 flex items-center gap-1 ml-auto">
          No results found
        </span>
      )}
    </div>
  );
}

/**
 * SearchFallbackIndicator - Shows the KB→Web fallback pattern
 */
export function SearchFallbackIndicator({ searchTrail, theme }) {
  const themeClasses = theme?.classes || {};

  if (!searchTrail?.attempts?.length) return null;

  const kbSearch = searchTrail.attempts.find(a =>
    a.source === 'search_knowledge_base' || a.source === 'knowledge_base'
  );
  const webSearch = searchTrail.attempts.find(a => a.source === 'web_search');

  if (!kbSearch) return null;

  const kbHasResults = kbSearch?.had_results || kbSearch?.results_count > 0;
  const webHasResults = webSearch?.had_results || webSearch?.results_count > 0;

  return (
    <div className="flex items-center gap-2 text-xs">
      {/* KB Search Result */}
      <div className={`flex items-center gap-1 px-2 py-1 rounded
                       ${kbHasResults ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
        <Database size={12} />
        <span>Notes: {kbSearch.results_count || 0}</span>
      </div>

      {/* Fallback Arrow (if KB was empty and web was searched) */}
      {!kbHasResults && webSearch && (
        <>
          <span className={themeClasses.textMuted || 'text-gray-400'}>→</span>
          <div className={`flex items-center gap-1 px-2 py-1 rounded
                           ${webHasResults ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
            <Globe size={12} />
            <span>Web: {webSearch.results_count || 0}</span>
          </div>
        </>
      )}
    </div>
  );
}

export default SearchTrailIndicator;
