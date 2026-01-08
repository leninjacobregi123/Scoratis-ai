/**
 * WebSearchProgress Component
 *
 * Perplexity-style "Researching websites" indicator
 * Shows web search progress with source cards in a grid layout
 */

import { useState, useEffect } from 'react';
import { Globe, Search, Loader2, ExternalLink } from 'lucide-react';

// Extract domain from URL
function extractDomain(url) {
  try {
    const domain = new URL(url).hostname.replace('www.', '');
    return domain.length > 20 ? domain.substring(0, 17) + '...' : domain;
  } catch {
    return url?.substring(0, 20) || 'unknown';
  }
}

// Get favicon URL for a domain
function getFaviconUrl(url) {
  try {
    const domain = new URL(url).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return null;
  }
}

// Single source card in the grid
function SourceCard({ source, index, isLoading }) {
  const [imgError, setImgError] = useState(false);
  const faviconUrl = getFaviconUrl(source.url);
  const domain = extractDomain(source.url);
  const title = source.title?.length > 25
    ? source.title.substring(0, 22) + '...'
    : source.title || 'Loading...';

  return (
    <div
      className={`flex items-center gap-2.5 px-3 py-2 rounded-lg bg-[#2a2a2a] border border-[#3a3a3a]
                  hover:border-[#4a4a4a] transition-all cursor-pointer group
                  ${isLoading ? 'animate-pulse' : ''}`}
      style={{ animationDelay: `${index * 100}ms` }}
      onClick={() => source.url && window.open(source.url, '_blank')}
      title={source.title}
    >
      {/* Favicon */}
      <div className="w-5 h-5 flex-shrink-0 rounded overflow-hidden bg-[#3a3a3a] flex items-center justify-center">
        {faviconUrl && !imgError ? (
          <img
            src={faviconUrl}
            alt=""
            className="w-4 h-4"
            onError={() => setImgError(true)}
          />
        ) : (
          <Globe className="w-3 h-3 text-gray-500" />
        )}
      </div>

      {/* Domain */}
      <span className="text-xs text-gray-400 flex-shrink-0 w-16 truncate">
        {domain}
      </span>

      {/* Title */}
      <span className="text-sm text-gray-200 truncate flex-1">
        {title}
      </span>

      {/* External link indicator */}
      <ExternalLink className="w-3 h-3 text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
    </div>
  );
}

// Skeleton card for loading state
function SkeletonCard({ index }) {
  return (
    <div
      className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-[#2a2a2a] border border-[#3a3a3a] animate-pulse"
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <div className="w-5 h-5 rounded bg-[#3a3a3a]" />
      <div className="w-16 h-3 rounded bg-[#3a3a3a]" />
      <div className="flex-1 h-3 rounded bg-[#3a3a3a]" />
    </div>
  );
}

/**
 * Main WebSearchProgress component
 */
export function WebSearchProgress({
  isSearching = false,
  searchResults = [],
  query = '',
  theme
}) {
  const [showSkeleton, setShowSkeleton] = useState(true);

  // Show skeleton briefly, then show results
  useEffect(() => {
    if (searchResults.length > 0) {
      const timer = setTimeout(() => setShowSkeleton(false), 300);
      return () => clearTimeout(timer);
    } else {
      setShowSkeleton(true);
    }
  }, [searchResults]);

  if (!isSearching && searchResults.length === 0) return null;

  return (
    <div className="mb-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
          {isSearching ? (
            <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />
          ) : (
            <Globe className="w-3.5 h-3.5 text-white" />
          )}
        </div>
        <span className="text-sm font-medium text-gray-300">
          {isSearching ? 'Researching websites...' : 'Sources found'}
        </span>
        {searchResults.length > 0 && (
          <span className="text-xs text-gray-500">
            ({searchResults.length} sources)
          </span>
        )}
      </div>

      {/* Sources Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {showSkeleton && isSearching && searchResults.length === 0 ? (
          // Show skeleton cards while loading
          [...Array(6)].map((_, i) => <SkeletonCard key={i} index={i} />)
        ) : (
          // Show actual results
          searchResults.map((source, idx) => (
            <SourceCard
              key={idx}
              source={source}
              index={idx}
              isLoading={isSearching}
            />
          ))
        )}
      </div>

      {/* Divider */}
      {searchResults.length > 0 && !isSearching && (
        <div className="mt-4 border-t border-[#3a3a3a]" />
      )}
    </div>
  );
}

/**
 * Light theme version for Athenian theme
 */
export function WebSearchProgressLight({
  isSearching = false,
  searchResults = [],
  query = '',
  theme
}) {
  const [showSkeleton, setShowSkeleton] = useState(true);

  useEffect(() => {
    if (searchResults.length > 0) {
      const timer = setTimeout(() => setShowSkeleton(false), 300);
      return () => clearTimeout(timer);
    } else {
      setShowSkeleton(true);
    }
  }, [searchResults]);

  if (!isSearching && searchResults.length === 0) return null;

  return (
    <div className="mb-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#6b7c5e] to-[#4a5a40] flex items-center justify-center">
          {isSearching ? (
            <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />
          ) : (
            <Globe className="w-3.5 h-3.5 text-white" />
          )}
        </div>
        <span className="text-sm font-medium text-gray-700">
          {isSearching ? 'Researching websites...' : 'Sources found'}
        </span>
        {searchResults.length > 0 && (
          <span className="text-xs text-gray-500">
            ({searchResults.length} sources)
          </span>
        )}
      </div>

      {/* Sources Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {showSkeleton && isSearching && searchResults.length === 0 ? (
          [...Array(6)].map((_, i) => (
            <div
              key={i}
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-gray-50 border border-gray-200 animate-pulse"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <div className="w-5 h-5 rounded bg-gray-200" />
              <div className="w-16 h-3 rounded bg-gray-200" />
              <div className="flex-1 h-3 rounded bg-gray-200" />
            </div>
          ))
        ) : (
          searchResults.map((source, idx) => (
            <SourceCardLight key={idx} source={source} index={idx} isLoading={isSearching} />
          ))
        )}
      </div>

      {searchResults.length > 0 && !isSearching && (
        <div className="mt-4 border-t border-gray-200" />
      )}
    </div>
  );
}

// Light theme source card
function SourceCardLight({ source, index, isLoading }) {
  const [imgError, setImgError] = useState(false);
  const faviconUrl = getFaviconUrl(source.url);
  const domain = extractDomain(source.url);
  const title = source.title?.length > 25
    ? source.title.substring(0, 22) + '...'
    : source.title || 'Loading...';

  return (
    <div
      className={`flex items-center gap-2.5 px-3 py-2 rounded-lg bg-white border border-gray-200
                  hover:border-[#6b7c5e]/50 hover:bg-[#6b7c5e]/5 transition-all cursor-pointer group
                  ${isLoading ? 'animate-pulse' : ''}`}
      style={{ animationDelay: `${index * 100}ms` }}
      onClick={() => source.url && window.open(source.url, '_blank')}
      title={source.title}
    >
      <div className="w-5 h-5 flex-shrink-0 rounded overflow-hidden bg-gray-100 flex items-center justify-center">
        {faviconUrl && !imgError ? (
          <img
            src={faviconUrl}
            alt=""
            className="w-4 h-4"
            onError={() => setImgError(true)}
          />
        ) : (
          <Globe className="w-3 h-3 text-gray-400" />
        )}
      </div>

      <span className="text-xs text-gray-500 flex-shrink-0 w-16 truncate">
        {domain}
      </span>

      <span className="text-sm text-gray-700 truncate flex-1">
        {title}
      </span>

      <ExternalLink className="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
    </div>
  );
}

export default WebSearchProgress;
