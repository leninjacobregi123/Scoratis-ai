import { useState } from 'react';
import { Globe, Brain, FileSearch, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

// Athenian olive theme colors
const THEME = {
  primary: '#6b7c5e',
  primaryLight: '#8a9a7a',
  primaryDark: '#4a5a40',
  bgActive: 'rgba(107, 124, 94, 0.15)',
  bgHover: 'rgba(107, 124, 94, 0.08)',
};

// Toggle Switch Component - Athenian styled
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
        transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-[#6b7c5e]/50 focus:ring-offset-2
        ${enabled ? 'bg-[#6b7c5e]' : 'bg-gray-300'}
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

// Option Row Component - Athenian styled
function OptionRow({ icon: Icon, label, description, enabled, onChange, disabled = false }) {
  return (
    <div
      className={`flex items-center justify-between py-2.5 px-2 rounded-lg transition-colors ${disabled ? 'opacity-50' : 'hover:bg-[#6b7c5e]/5'}`}
    >
      <div className="flex items-center gap-3">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${enabled ? 'bg-[#6b7c5e]/15' : 'bg-gray-100'}`}>
          <Icon className={`w-4 h-4 transition-colors ${enabled ? 'text-[#6b7c5e]' : 'text-gray-400'}`} />
        </div>
        <div>
          <p className={`text-sm font-medium transition-colors ${enabled ? 'text-[#4a5a40]' : 'text-gray-700'}`}>{label}</p>
          {description && (
            <p className="text-xs text-gray-500">{description}</p>
          )}
        </div>
      </div>
      <Toggle enabled={enabled} onChange={onChange} disabled={disabled} />
    </div>
  );
}

// Chat Options Panel - Expanded view with Athenian styling
export function ChatOptionsPanel({ options, onChange, className = '' }) {
  return (
    <div className={`bg-white/95 backdrop-blur-sm border border-[#D4CFB8] rounded-xl shadow-lg p-4 ${className}`}>
      <h4 className="text-xs font-semibold text-[#6b7c5e] uppercase tracking-wider mb-3 flex items-center gap-2">
        <Sparkles className="w-3.5 h-3.5" />
        Chat Options
      </h4>
      <div className="space-y-0.5">
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

// Compact Chat Options Bar - Athenian styled inline pills
export function ChatOptionsBar({ options, onChange, className = '' }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`${className}`}>
      {/* Compact pills with Athenian theme */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => onChange({ ...options, useWebSearch: !options.useWebSearch })}
          className={`
            flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200
            ${options.useWebSearch
              ? 'bg-[#6b7c5e]/15 text-[#4a5a40] border border-[#6b7c5e]/40 shadow-sm'
              : 'bg-white/80 text-gray-500 border border-gray-200 hover:border-[#6b7c5e]/30 hover:bg-[#6b7c5e]/5'}
          `}
        >
          <Globe className={`w-3.5 h-3.5 ${options.useWebSearch ? 'text-[#6b7c5e]' : ''}`} />
          Search
        </button>

        <button
          onClick={() => onChange({ ...options, useReasoning: !options.useReasoning })}
          className={`
            flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200
            ${options.useReasoning
              ? 'bg-[#6b7c5e]/15 text-[#4a5a40] border border-[#6b7c5e]/40 shadow-sm'
              : 'bg-white/80 text-gray-500 border border-gray-200 hover:border-[#6b7c5e]/30 hover:bg-[#6b7c5e]/5'}
          `}
        >
          <Brain className={`w-3.5 h-3.5 ${options.useReasoning ? 'text-[#6b7c5e]' : ''}`} />
          Think
        </button>

        <button
          onClick={() => onChange({ ...options, useDocuments: !options.useDocuments })}
          className={`
            flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200
            ${options.useDocuments
              ? 'bg-[#6b7c5e]/15 text-[#4a5a40] border border-[#6b7c5e]/40 shadow-sm'
              : 'bg-white/80 text-gray-500 border border-gray-200 hover:border-[#6b7c5e]/30 hover:bg-[#6b7c5e]/5'}
          `}
        >
          <FileSearch className={`w-3.5 h-3.5 ${options.useDocuments ? 'text-[#6b7c5e]' : ''}`} />
          Docs
        </button>

        {/* More options toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 px-2 py-1.5 text-xs text-gray-400 hover:text-[#6b7c5e] transition-colors rounded-full hover:bg-[#6b7c5e]/5"
          title={expanded ? 'Hide options' : 'More options'}
        >
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Expanded panel */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-[#D4CFB8]/50">
          <ChatOptionsPanel options={options} onChange={onChange} className="border-0 shadow-none p-0 bg-transparent" />
        </div>
      )}
    </div>
  );
}

// Mini Options Indicator - Athenian styled
export function ChatOptionsIndicator({ options, onClick }) {
  const activeCount = [options.useWebSearch, options.useReasoning, options.useDocuments].filter(Boolean).length;

  if (activeCount === 0) return null;

  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 px-2.5 py-1 bg-[#6b7c5e]/10 hover:bg-[#6b7c5e]/20 rounded-lg text-xs text-[#4a5a40] font-medium transition-colors border border-[#6b7c5e]/20"
      title="Chat options"
    >
      <Sparkles className="w-3.5 h-3.5 text-[#6b7c5e]" />
      <span>{activeCount} active</span>
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
