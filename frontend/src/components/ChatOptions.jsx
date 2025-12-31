import { useState } from 'react';
import { Globe, Brain, FileSearch, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

// Toggle Switch Component
function Toggle({ enabled, onChange, disabled = false }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      disabled={disabled}
      onClick={() => !disabled && onChange(!enabled)}
      className={`
        relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent
        transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
        ${enabled ? 'bg-blue-600' : 'bg-gray-200'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      <span
        aria-hidden="true"
        className={`
          pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0
          transition duration-200 ease-in-out
          ${enabled ? 'translate-x-4' : 'translate-x-0'}
        `}
      />
    </button>
  );
}

// Option Row Component
function OptionRow({ icon: Icon, label, description, enabled, onChange, disabled = false }) {
  return (
    <div
      className={`flex items-center justify-between py-2 ${disabled ? 'opacity-50' : ''}`}
    >
      <div className="flex items-center gap-3">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${enabled ? 'bg-blue-100' : 'bg-gray-100'}`}>
          <Icon className={`w-4 h-4 ${enabled ? 'text-blue-600' : 'text-gray-500'}`} />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-900">{label}</p>
          {description && (
            <p className="text-xs text-gray-500">{description}</p>
          )}
        </div>
      </div>
      <Toggle enabled={enabled} onChange={onChange} disabled={disabled} />
    </div>
  );
}

// Chat Options Panel - Expanded view
export function ChatOptionsPanel({ options, onChange, className = '' }) {
  return (
    <div className={`bg-white border border-gray-200 rounded-xl shadow-lg p-4 ${className}`}>
      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
        Chat Options
      </h4>
      <div className="space-y-1">
        <OptionRow
          icon={Globe}
          label="Web Search"
          description="Search the web for current information"
          enabled={options.useWebSearch}
          onChange={(val) => onChange({ ...options, useWebSearch: val })}
        />
        <OptionRow
          icon={Brain}
          label="Deep Thinking"
          description="Enable extended reasoning (slower)"
          enabled={options.useReasoning}
          onChange={(val) => onChange({ ...options, useReasoning: val })}
        />
        <OptionRow
          icon={FileSearch}
          label="Use Documents"
          description="Search your uploaded documents"
          enabled={options.useDocuments}
          onChange={(val) => onChange({ ...options, useDocuments: val })}
        />
      </div>
    </div>
  );
}

// Compact Chat Options Bar - Inline version above input
export function ChatOptionsBar({ options, onChange, className = '' }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`${className}`}>
      {/* Compact pills */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => onChange({ ...options, useWebSearch: !options.useWebSearch })}
          className={`
            flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all
            ${options.useWebSearch
              ? 'bg-blue-100 text-blue-700 border border-blue-300'
              : 'bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200'}
          `}
        >
          <Globe className="w-3.5 h-3.5" />
          Web Search
        </button>

        <button
          onClick={() => onChange({ ...options, useReasoning: !options.useReasoning })}
          className={`
            flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all
            ${options.useReasoning
              ? 'bg-purple-100 text-purple-700 border border-purple-300'
              : 'bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200'}
          `}
        >
          <Brain className="w-3.5 h-3.5" />
          Deep Thinking
        </button>

        <button
          onClick={() => onChange({ ...options, useDocuments: !options.useDocuments })}
          className={`
            flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all
            ${options.useDocuments
              ? 'bg-green-100 text-green-700 border border-green-300'
              : 'bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200'}
          `}
        >
          <FileSearch className="w-3.5 h-3.5" />
          Documents
        </button>

        {/* More options toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 px-2 py-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors"
        >
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Expanded panel */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <ChatOptionsPanel options={options} onChange={onChange} className="border-0 shadow-none p-0" />
        </div>
      )}
    </div>
  );
}

// Mini Options Indicator - Shows active options count
export function ChatOptionsIndicator({ options, onClick }) {
  const activeCount = [options.useWebSearch, options.useReasoning, options.useDocuments].filter(Boolean).length;

  if (activeCount === 0) return null;

  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 px-2 py-1 bg-blue-50 hover:bg-blue-100 rounded-md text-xs text-blue-700 transition-colors"
      title="Chat options"
    >
      <Sparkles className="w-3.5 h-3.5" />
      <span>{activeCount} option{activeCount !== 1 ? 's' : ''} active</span>
    </button>
  );
}

// Default options
export const DEFAULT_CHAT_OPTIONS = {
  useWebSearch: true,
  useReasoning: false,
  useDocuments: true,
};

export default {
  ChatOptionsPanel,
  ChatOptionsBar,
  ChatOptionsIndicator,
  Toggle,
  DEFAULT_CHAT_OPTIONS,
};
