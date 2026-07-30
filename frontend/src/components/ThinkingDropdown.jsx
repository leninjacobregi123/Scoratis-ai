/**
 * ThinkingDropdown Component
 *
 * DeepSeek-style collapsible thinking display
 * Shows model's chain-of-thought reasoning in a faded, expandable section
 */

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Brain, Sparkles } from 'lucide-react';

/**
 * Main ThinkingDropdown component - Dark theme (default)
 */
export function ThinkingDropdown({ thinking, isStreaming = false }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showContent, setShowContent] = useState(false);

  // Auto-expand while streaming, collapse when done
  useEffect(() => {
    if (isStreaming && thinking) {
      setIsExpanded(true);
    }
  }, [isStreaming, thinking]);

  // Delay content reveal for smooth animation
  useEffect(() => {
    if (isExpanded) {
      const timer = setTimeout(() => setShowContent(true), 50);
      return () => clearTimeout(timer);
    } else {
      setShowContent(false);
    }
  }, [isExpanded]);

  if (!thinking) return null;

  // Count thinking lines for display
  const thinkingLines = thinking.split('\n').filter(line => line.trim()).length;

  return (
    <div className="mb-4 animate-fade-in">
      {/* Collapsible Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 px-3 py-2 w-full rounded-lg
                   bg-gradient-to-r from-purple-500/10 to-blue-500/10
                   border border-purple-500/20 hover:border-purple-500/40
                   transition-all duration-200 group"
      >
        {/* Thinking indicator */}
        <div className="relative">
          <Brain className="w-4 h-4 text-purple-400" />
          {isStreaming && (
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
          )}
        </div>

        {/* Label */}
        <span className="text-sm font-medium text-purple-300">
          {isStreaming ? 'Thinking...' : 'Thought Process'}
        </span>

        {/* Line count badge */}
        <span className="text-xs px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded">
          {thinkingLines} steps
        </span>

        {/* Expand/Collapse indicator */}
        <div className="ml-auto flex items-center gap-1 text-gray-500 group-hover:text-purple-400 transition-colors">
          <span className="text-xs">{isExpanded ? 'Hide' : 'Show'}</span>
          {isExpanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </div>
      </button>

      {/* Expandable Content */}
      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out
                    ${isExpanded ? 'max-h-96 opacity-100 mt-2' : 'max-h-0 opacity-0'}`}
      >
        <div
          className={`px-4 py-3 rounded-lg bg-[#1a1a1a] border border-[#2a2a2a]
                      overflow-y-auto max-h-80 custom-scrollbar
                      transition-opacity duration-200
                      ${showContent ? 'opacity-100' : 'opacity-0'}`}
        >
          {/* Faded thinking content */}
          <div className="text-sm text-gray-400/70 whitespace-pre-wrap font-mono leading-relaxed">
            {thinking.split('\n').map((line, idx) => (
              <div key={idx} className="flex gap-2 mb-1">
                {line.trim() && (
                  <>
                    <span className="text-purple-500/50 select-none">{'>>'}</span>
                    <span className={line.startsWith('Source') || line.startsWith('I ')
                      ? 'text-blue-400/60'
                      : ''}>
                      {line}
                    </span>
                  </>
                )}
                {!line.trim() && <span>&nbsp;</span>}
              </div>
            ))}
          </div>

          {/* Streaming indicator at bottom */}
          {isStreaming && (
            <div className="flex items-center gap-2 mt-3 pt-2 border-t border-[#2a2a2a]">
              <Sparkles className="w-3 h-3 text-purple-400 animate-pulse" />
              <span className="text-xs text-purple-400/70">Processing...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Light theme version for Athenian theme
 */
export function ThinkingDropdownLight({ thinking, isStreaming = false }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showContent, setShowContent] = useState(false);

  useEffect(() => {
    if (isStreaming && thinking) {
      setIsExpanded(true);
    }
  }, [isStreaming, thinking]);

  useEffect(() => {
    if (isExpanded) {
      const timer = setTimeout(() => setShowContent(true), 50);
      return () => clearTimeout(timer);
    } else {
      setShowContent(false);
    }
  }, [isExpanded]);

  if (!thinking) return null;

  const thinkingLines = thinking.split('\n').filter(line => line.trim()).length;

  return (
    <div className="mb-4 animate-fade-in">
      {/* Collapsible Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 px-3 py-2 w-full rounded-lg
                   bg-gradient-to-r from-[#6b7c5e]/10 to-[#4a5a40]/10
                   border border-[#6b7c5e]/30 hover:border-[#6b7c5e]/50
                   transition-all duration-200 group"
      >
        <div className="relative">
          <Brain className="w-4 h-4 text-[#6b7c5e]" />
          {isStreaming && (
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-[#6b7c5e] rounded-full animate-pulse" />
          )}
        </div>

        <span className="text-sm font-medium text-[#4a5a40]">
          {isStreaming ? 'Thinking...' : 'Thought Process'}
        </span>

        <span className="text-xs px-1.5 py-0.5 bg-[#6b7c5e]/15 text-[#4a5a40] rounded">
          {thinkingLines} steps
        </span>

        <div className="ml-auto flex items-center gap-1 text-gray-500 group-hover:text-[#6b7c5e] transition-colors">
          <span className="text-xs">{isExpanded ? 'Hide' : 'Show'}</span>
          {isExpanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </div>
      </button>

      {/* Expandable Content */}
      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out
                    ${isExpanded ? 'max-h-96 opacity-100 mt-2' : 'max-h-0 opacity-0'}`}
      >
        <div
          className={`px-4 py-3 rounded-lg bg-gray-50 border border-gray-200
                      overflow-y-auto max-h-80 custom-scrollbar
                      transition-opacity duration-200
                      ${showContent ? 'opacity-100' : 'opacity-0'}`}
        >
          <div className="text-sm text-gray-500/80 whitespace-pre-wrap font-mono leading-relaxed">
            {thinking.split('\n').map((line, idx) => (
              <div key={idx} className="flex gap-2 mb-1">
                {line.trim() && (
                  <>
                    <span className="text-[#6b7c5e]/50 select-none">{'>>'}</span>
                    <span className={line.startsWith('Source') || line.startsWith('I ')
                      ? 'text-[#4a5a40]/70'
                      : ''}>
                      {line}
                    </span>
                  </>
                )}
                {!line.trim() && <span>&nbsp;</span>}
              </div>
            ))}
          </div>

          {isStreaming && (
            <div className="flex items-center gap-2 mt-3 pt-2 border-t border-gray-200">
              <Sparkles className="w-3 h-3 text-[#6b7c5e] animate-pulse" />
              <span className="text-xs text-[#6b7c5e]/70">Processing...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ThinkingDropdown;
