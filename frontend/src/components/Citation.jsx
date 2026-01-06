/**
 * Citation Components
 * Renders inline citation numbers, popup previews, and footnote sections
 *
 * Updated for Enhanced RAG with superscript footnotes
 */

import { useState, useRef, useEffect } from 'react';
import { FileText, BookOpen, MessageSquare, X, ExternalLink, Quote } from 'lucide-react';
import { formatSourceType } from '../utils/citations';

// Unicode superscript digits for footnote display
const SUPERSCRIPT_MAP = {
  '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
  '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
};

/**
 * Convert a number to superscript Unicode characters
 */
export function toSuperscript(num) {
  return String(num).split('').map(d => SUPERSCRIPT_MAP[d] || d).join('');
}

/**
 * SuperscriptCitation - Inline superscript footnote marker
 * Clickable to show source details
 */
export function SuperscriptCitation({ number, source, onClick, theme }) {
  const themeClasses = theme?.classes || {};

  return (
    <sup
      onClick={() => onClick?.(source)}
      className={`cursor-pointer font-semibold transition-all hover:opacity-70
                  ${themeClasses.textPrimary || 'text-blue-600'}`}
      title={source?.documentTitle || `Source ${number}`}
    >
      {toSuperscript(number)}
    </sup>
  );
}

/**
 * CitationNumber - Inline superscript citation number
 * Clickable to show/hide citation popup
 */
export function CitationNumber({ index, onClick, isActive }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center justify-center min-w-[18px] h-[18px] px-1
                  text-[10px] font-semibold rounded-sm transition-all cursor-pointer
                  hover:scale-110 -translate-y-1
                  ${isActive
                    ? 'bg-blue-600 text-white'
                    : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                  }`}
      title={`View source [${index}]`}
    >
      {index}
    </button>
  );
}

/**
 * CitationPopup - Floating popup showing source details
 */
export function CitationPopup({
  source,
  onClose,
  position = 'bottom',
  citationNumber
}) {
  const popupRef = useRef(null);

  // Close on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (popupRef.current && !popupRef.current.contains(event.target)) {
        onClose();
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  // Close on Escape key
  useEffect(() => {
    function handleEscape(event) {
      if (event.key === 'Escape') {
        onClose();
      }
    }
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  if (!source) return null;

  const getSourceIcon = () => {
    switch (source.sourceType) {
      case 'journal':
        return <BookOpen className="w-4 h-4" />;
      case 'chat':
        return <MessageSquare className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  return (
    <div
      ref={popupRef}
      className={`absolute z-50 w-80 bg-white rounded-xl shadow-xl border border-gray-200
                  animate-fade-in overflow-hidden
                  ${position === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <span className="flex items-center justify-center w-6 h-6 bg-blue-100 text-blue-700 rounded text-xs font-bold">
            {citationNumber}
          </span>
          <div className="flex items-center gap-1.5 text-gray-600">
            {getSourceIcon()}
            <span className="text-xs font-medium">{formatSourceType(source.sourceType)}</span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-gray-200 text-gray-400 hover:text-gray-600 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Document Title */}
        <h4 className="font-medium text-gray-900 text-sm mb-2 line-clamp-2">
          {source.documentTitle}
        </h4>

        {/* Page indicator */}
        {source.page && (
          <div className="text-xs text-gray-500 mb-2">
            Page {source.page}
          </div>
        )}

        {/* Content Preview */}
        <div className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 border border-gray-100">
          <p className="line-clamp-4 leading-relaxed">
            {source.contentPreview || source.content || 'No preview available'}
          </p>
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Chunk ID: {source.chunkId}</span>
          {source.documentId && (
            <span className="flex items-center gap-1">
              <ExternalLink className="w-3 h-3" />
              Doc #{source.documentId}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * CitationList - List of all sources used in a message
 */
export function CitationList({ sources, onSourceClick }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-4 pt-4 border-t border-gray-200">
      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
        Sources ({sources.length})
      </h4>
      <div className="space-y-2">
        {sources.map((source, i) => (
          <button
            key={source.chunkId || i}
            onClick={() => onSourceClick?.(source)}
            className="w-full flex items-start gap-3 p-3 rounded-lg bg-gray-50
                       hover:bg-gray-100 transition-colors text-left group"
          >
            <span className="flex items-center justify-center w-6 h-6 bg-blue-100
                           text-blue-700 rounded text-xs font-bold flex-shrink-0">
              {source.citationNumber || i + 1}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate group-hover:text-blue-600">
                {source.documentTitle || 'Unknown Document'}
              </p>
              <p className="text-xs text-gray-500 truncate mt-0.5">
                {source.contentPreview?.substring(0, 80)}...
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * SourcesBadge - Small badge showing number of sources
 */
export function SourcesBadge({ count, onClick }) {
  if (!count) return null;

  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 px-2 py-1 bg-blue-50
                 text-blue-700 rounded-full text-xs font-medium
                 hover:bg-blue-100 transition-colors"
    >
      <FileText className="w-3 h-3" />
      {count} source{count !== 1 ? 's' : ''}
    </button>
  );
}

/**
 * FootnotesSection - Academic-style footnotes displayed below content
 * Renders sources with superscript numbers, titles, and content previews
 */
export function FootnotesSection({ sources, citationInfo, theme, onSourceClick }) {
  const themeClasses = theme?.classes || {};

  // Filter to only cited sources if citationInfo is available
  const displaySources = sources?.filter(s => s.was_cited !== false) || [];

  if (!displaySources || displaySources.length === 0) return null;

  const getSourceIcon = (sourceType) => {
    switch (sourceType) {
      case 'journal':
        return <BookOpen className="w-3 h-3" />;
      case 'chat':
        return <MessageSquare className="w-3 h-3" />;
      default:
        return <FileText className="w-3 h-3" />;
    }
  };

  return (
    <div className={`mt-4 pt-4 border-t ${themeClasses.border || 'border-gray-200'}`}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <Quote className={`w-4 h-4 ${themeClasses.textMuted || 'text-gray-500'}`} />
        <h4 className={`text-xs font-semibold uppercase tracking-wider
                        ${themeClasses.textMuted || 'text-gray-500'}`}>
          Sources
          {citationInfo?.citations_used && (
            <span className="font-normal ml-1">
              ({citationInfo.citations_used} of {citationInfo.total_sources} used)
            </span>
          )}
        </h4>
      </div>

      {/* Footnotes List */}
      <div className="space-y-2">
        {displaySources.map((source, idx) => {
          const citationNum = source.citationNumber || source.citation_number || idx + 1;
          const title = source.documentTitle || source.document_title || 'Unknown Source';
          const preview = source.contentPreview || source.content_preview || '';
          const page = source.page;
          const sourceType = source.sourceType || source.source_type;

          return (
            <div
              key={source.chunkId || source.chunk_id || idx}
              onClick={() => onSourceClick?.(source)}
              className={`flex items-start gap-2 text-sm cursor-pointer
                          hover:opacity-80 transition-opacity`}
            >
              {/* Superscript Number */}
              <span className={`font-semibold min-w-[1rem]
                               ${themeClasses.textPrimary || 'text-blue-600'}`}>
                {toSuperscript(citationNum)}
              </span>

              {/* Source Details */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  {/* Source Type Icon */}
                  <span className={themeClasses.textMuted || 'text-gray-400'}>
                    {getSourceIcon(sourceType)}
                  </span>

                  {/* Title */}
                  <span className={`font-medium ${themeClasses.text || 'text-gray-900'}`}>
                    {title}
                  </span>

                  {/* Page Number */}
                  {page && (
                    <span className={themeClasses.textMuted || 'text-gray-500'}>
                      , p.{page}
                    </span>
                  )}
                </div>

                {/* Content Preview */}
                {preview && (
                  <p className={`mt-0.5 text-xs italic line-clamp-2
                                ${themeClasses.textMuted || 'text-gray-500'}`}>
                    — "{preview.substring(0, 100)}{preview.length > 100 ? '...' : ''}"
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * FormattedFootnotes - Parse and render markdown footnotes from backend
 * Handles the footnotes string returned by citation_processor
 */
export function FormattedFootnotes({ footnotesMarkdown, theme }) {
  const themeClasses = theme?.classes || {};

  if (!footnotesMarkdown) return null;

  // The backend returns formatted markdown like:
  // ---
  // **Sources:**
  // ¹ **Title**, p.5 — "preview..."
  // ² **Another**, p.10 — "preview..."

  return (
    <div
      className={`mt-4 pt-4 border-t prose prose-sm max-w-none
                  ${themeClasses.border || 'border-gray-200'}
                  ${themeClasses.text || 'text-gray-700'}`}
      dangerouslySetInnerHTML={{
        __html: footnotesMarkdown
          .replace(/\*\*Sources:\*\*/g, '<strong class="text-sm uppercase tracking-wider">Sources:</strong>')
          .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
          .replace(/\n/g, '<br/>')
      }}
    />
  );
}

export default {
  CitationNumber,
  CitationPopup,
  CitationList,
  SourcesBadge,
  SuperscriptCitation,
  FootnotesSection,
  FormattedFootnotes,
  toSuperscript,
};
