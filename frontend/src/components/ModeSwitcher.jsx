/**
 * Learning Mode Switcher - Athenian Theme
 * Lets the student switch between exam_prep (fast, direct) and
 * deep_learning (full Socratic method) mid-conversation. Mirrors
 * LLMSwitcher.jsx's trigger-button + dropdown pattern, simplified since
 * there are only 2 fixed options (no fetching needed).
 */

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, Zap, Brain } from 'lucide-react';

const THEME = {
  primary: '#6b7c5e',
  bgCard: '#FDFBF7',
  bgSecondary: '#EBE5D8',
  textPrimary: '#3d4a35',
  textMuted: '#8a8a7a',
  border: '#D4CFB8',
  borderLight: '#E8E3D6',
};

const MODES = [
  { id: 'exam_prep', label: 'Exam Prep', icon: Zap, description: 'Fast, direct answers + recall checks' },
  { id: 'deep_learning', label: 'Deep Learning', icon: Brain, description: 'Full Socratic dialogue' },
];

export default function ModeSwitcher({ currentMode = 'deep_learning', onModeChange, className = '' }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const active = MODES.find((m) => m.id === currentMode) || MODES[1];
  const ActiveIcon = active.icon;

  return (
    <div ref={dropdownRef} className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-200"
        style={{
          backgroundColor: THEME.bgCard,
          border: `1px solid ${THEME.border}`,
          color: THEME.textPrimary,
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        }}
        title="Switch learning mode"
      >
        <ActiveIcon size={14} style={{ color: THEME.primary }} />
        <span className="text-sm font-medium">{active.label}</span>
        <ChevronDown
          size={14}
          style={{
            color: THEME.textMuted,
            transform: isOpen ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.2s ease',
          }}
        />
      </button>

      {isOpen && (
        <div
          className="absolute top-full left-0 mt-2 w-64 rounded-xl overflow-hidden z-50"
          style={{
            backgroundColor: THEME.bgCard,
            border: `1px solid ${THEME.border}`,
            boxShadow: '0 8px 32px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.08)',
          }}
        >
          <div
            className="px-4 py-3 border-b"
            style={{ backgroundColor: THEME.bgSecondary, borderColor: THEME.borderLight }}
          >
            <span className="font-semibold text-sm" style={{ color: THEME.textPrimary }}>
              Learning Mode
            </span>
          </div>
          <div className="py-1">
            {MODES.map((m) => {
              const Icon = m.icon;
              const isSelected = m.id === currentMode;
              return (
                <button
                  key={m.id}
                  onClick={() => {
                    onModeChange?.(m.id);
                    setIsOpen(false);
                  }}
                  className="w-full flex items-start gap-3 px-4 py-3 text-left transition-colors"
                  style={{ backgroundColor: isSelected ? THEME.bgSecondary : 'transparent' }}
                  onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.backgroundColor = THEME.borderLight; }}
                  onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent'; }}
                >
                  <Icon size={16} style={{ color: THEME.primary, marginTop: 2 }} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium" style={{ color: THEME.textPrimary }}>{m.label}</span>
                      {isSelected && <Check size={14} style={{ color: THEME.primary }} />}
                    </div>
                    <div className="text-xs" style={{ color: THEME.textMuted }}>{m.description}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
