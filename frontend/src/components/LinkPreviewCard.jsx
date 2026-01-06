/**
 * LinkPreviewCard Component
 *
 * Displays rich link previews with Open Graph data.
 * Features:
 * - Title, description, and image preview
 * - Favicon and domain display
 * - Loading and error states
 * - Compact and expanded modes
 * - Theme-aware styling
 */

import { useState } from 'react';
import {
  ExternalLink,
  Globe,
  Image as ImageIcon,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  Link2
} from 'lucide-react';

/**
 * Preview status types
 */
const PreviewStatus = {
  LOADING: 'loading',
  READY: 'ready',
  ERROR: 'error'
};

/**
 * Extract domain from URL
 */
function extractDomain(url) {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname.replace('www.', '');
  } catch {
    return url;
  }
}

/**
 * Truncate text with ellipsis
 */
function truncate(text, maxLength) {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

/**
 * Loading state display
 */
function PreviewLoading({ theme }) {
  const themeClasses = theme?.classes || {};

  return (
    <div className={`flex items-center gap-3 p-4 rounded-xl border
                     ${themeClasses.border || 'border-gray-200'}
                     ${themeClasses.bgSecondary || 'bg-gray-50'}`}>
      <Loader2
        size={20}
        className={`animate-spin ${themeClasses.textPrimary || 'text-blue-500'}`}
      />
      <span className={`text-sm ${themeClasses.textMuted || 'text-gray-500'}`}>
        Loading preview...
      </span>
    </div>
  );
}

/**
 * Error state display
 */
function PreviewError({ url, error, theme }) {
  const themeClasses = theme?.classes || {};
  const domain = extractDomain(url);

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={`flex items-center gap-3 p-4 rounded-xl border
                  border-red-200 bg-red-50 hover:bg-red-100 transition-colors`}
    >
      <AlertCircle size={20} className="text-red-500 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-red-700 truncate">{domain}</p>
        <p className="text-xs text-red-600">
          {error || 'Unable to load preview'}
        </p>
      </div>
      <ExternalLink size={16} className="text-red-400 flex-shrink-0" />
    </a>
  );
}

/**
 * Compact preview (inline link style)
 */
function CompactPreview({ preview, url, theme }) {
  const themeClasses = theme?.classes || {};
  const domain = extractDomain(url);

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg
                  ${themeClasses.bgSecondary || 'bg-blue-50'}
                  hover:opacity-80 transition-opacity group`}
    >
      {/* Favicon */}
      {preview.favicon ? (
        <img
          src={preview.favicon}
          alt=""
          className="w-4 h-4 rounded"
          onError={(e) => {
            e.target.style.display = 'none';
          }}
        />
      ) : (
        <Globe size={14} className={themeClasses.textPrimary || 'text-blue-500'} />
      )}

      {/* Title */}
      <span className={`text-sm font-medium ${themeClasses.textPrimary || 'text-blue-600'}`}>
        {truncate(preview.title || domain, 50)}
      </span>

      <ExternalLink
        size={12}
        className={`opacity-0 group-hover:opacity-100 transition-opacity
                    ${themeClasses.textMuted || 'text-blue-400'}`}
      />
    </a>
  );
}

/**
 * Full preview card (with image and description)
 */
function FullPreview({ preview, url, theme, showImage = true }) {
  const themeClasses = theme?.classes || {};
  const domain = extractDomain(url);
  const hasImage = showImage && preview.image;

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={`block rounded-xl overflow-hidden border
                  ${themeClasses.border || 'border-gray-200'}
                  ${themeClasses.bgSecondary || 'bg-white'}
                  hover:shadow-md transition-all group`}
    >
      {/* Image */}
      {hasImage && (
        <div className="relative aspect-[2/1] bg-gray-100 overflow-hidden">
          <img
            src={preview.image}
            alt={preview.title || ''}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => {
              e.target.parentElement.style.display = 'none';
            }}
          />
        </div>
      )}

      {/* Content */}
      <div className="p-4">
        {/* Domain & Favicon */}
        <div className="flex items-center gap-2 mb-2">
          {preview.favicon ? (
            <img
              src={preview.favicon}
              alt=""
              className="w-4 h-4 rounded"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          ) : (
            <Globe size={14} className={themeClasses.textMuted || 'text-gray-400'} />
          )}
          <span className={`text-xs ${themeClasses.textMuted || 'text-gray-500'}`}>
            {domain}
          </span>
        </div>

        {/* Title */}
        <h4 className={`font-semibold line-clamp-2 mb-1
                        ${themeClasses.text || 'text-gray-900'}
                        group-hover:${themeClasses.textPrimary || 'text-blue-600'}
                        transition-colors`}>
          {preview.title || url}
        </h4>

        {/* Description */}
        {preview.description && (
          <p className={`text-sm line-clamp-2 ${themeClasses.textMuted || 'text-gray-600'}`}>
            {preview.description}
          </p>
        )}

        {/* Site Name */}
        {preview.siteName && preview.siteName !== domain && (
          <p className={`text-xs mt-2 ${themeClasses.textMuted || 'text-gray-400'}`}>
            {preview.siteName}
          </p>
        )}
      </div>
    </a>
  );
}

/**
 * Main LinkPreviewCard Component
 */
export function LinkPreviewCard({
  url,
  preview,
  status = PreviewStatus.READY,
  error,
  variant = 'full', // 'full', 'compact', 'auto'
  showImage = true,
  theme
}) {
  const themeClasses = theme?.classes || {};
  const [expanded, setExpanded] = useState(false);

  // Loading state
  if (status === PreviewStatus.LOADING) {
    return <PreviewLoading theme={theme} />;
  }

  // Error state
  if (status === PreviewStatus.ERROR || !preview) {
    return <PreviewError url={url} error={error} theme={theme} />;
  }

  // Auto variant: compact if no image/description, full otherwise
  const effectiveVariant = variant === 'auto'
    ? (preview.image || preview.description) ? 'full' : 'compact'
    : variant;

  // Compact variant
  if (effectiveVariant === 'compact') {
    return <CompactPreview preview={preview} url={url} theme={theme} />;
  }

  // Full variant
  return <FullPreview preview={preview} url={url} theme={theme} showImage={showImage} />;
}

/**
 * Multiple link previews in a grid
 */
export function LinkPreviewGrid({ links, theme, columns = 2 }) {
  const themeClasses = theme?.classes || {};

  if (!links || links.length === 0) return null;

  // Single link - full width
  if (links.length === 1) {
    return (
      <LinkPreviewCard
        url={links[0].url}
        preview={links[0].preview}
        status={links[0].status}
        error={links[0].error}
        theme={theme}
      />
    );
  }

  // Multiple links - grid layout
  return (
    <div className={`grid gap-3 ${columns === 2 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1'}`}>
      {links.map((link, idx) => (
        <LinkPreviewCard
          key={link.url || idx}
          url={link.url}
          preview={link.preview}
          status={link.status}
          error={link.error}
          variant="full"
          showImage={links.length <= 2} // Show images only for 1-2 links
          theme={theme}
        />
      ))}
    </div>
  );
}

/**
 * Inline link with expandable preview
 */
export function ExpandableLinkPreview({ url, preview, status, error, theme, children }) {
  const themeClasses = theme?.classes || {};
  const [isExpanded, setIsExpanded] = useState(false);
  const domain = extractDomain(url);

  return (
    <div className="inline-block">
      {/* Inline link trigger */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded
                    ${themeClasses.bgSecondary || 'bg-blue-50'}
                    ${themeClasses.textPrimary || 'text-blue-600'}
                    hover:opacity-80 transition-opacity text-sm`}
      >
        <Link2 size={12} />
        <span className="font-medium">{children || domain}</span>
        {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {/* Expanded preview */}
      {isExpanded && (
        <div className="mt-2 max-w-md animate-fade-in">
          <LinkPreviewCard
            url={url}
            preview={preview}
            status={status}
            error={error}
            theme={theme}
          />
        </div>
      )}
    </div>
  );
}

export default LinkPreviewCard;
