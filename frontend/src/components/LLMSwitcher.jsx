/**
 * LLM Model Switcher Component - Athenian Theme
 * Allows switching between different LLM providers and models
 * Shows only installed Ollama models and configured cloud providers
 */

import { useState, useEffect, useRef } from 'react';
import { ChevronDown, Check, Settings, Loader2, Cpu, Cloud, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { getAccessToken } from '../utils/auth';

// Separate instance from useApi.js's shared one (this component predates it),
// but still attaches the auth token so /llm/providers/configured works.
const api = axios.create({ baseURL: '/api' });
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Provider display names and icons
const PROVIDER_META = {
  ollama: { name: 'Ollama', icon: '🦙', local: true },
  lmstudio: { name: 'LM Studio', icon: '💻', local: true },
  localai: { name: 'LocalAI', icon: '🏠', local: true },
  textgenwebui: { name: 'Text Gen WebUI', icon: '🌐', local: true },
  openai: { name: 'OpenAI', icon: '🤖', local: false },
  anthropic: { name: 'Anthropic', icon: '🧠', local: false },
  google: { name: 'Google AI', icon: '✨', local: false },
  groq: { name: 'Groq', icon: '⚡', local: false },
  together: { name: 'Together AI', icon: '🤝', local: false },
  azure: { name: 'Azure OpenAI', icon: '☁️', local: false },
  deepseek: { name: 'DeepSeek', icon: '🔍', local: false },
};

// Athenian theme colors
const THEME = {
  primary: '#6b7c5e',
  primaryHover: '#5a6b4f',
  primaryLight: '#8a9a7a',
  bgPrimary: '#F5F0E6',
  bgSecondary: '#EBE5D8',
  bgCard: '#FDFBF7',
  textPrimary: '#3d4a35',
  textSecondary: '#6b7c5e',
  textMuted: '#8a8a7a',
  border: '#D4CFB8',
  borderLight: '#E8E3D6',
  success: '#6b7c5e',
  hover: 'rgba(107, 124, 94, 0.08)',
};

export default function LLMSwitcher({
  currentProvider = 'ollama',
  currentModel = 'llama3.2',
  onModelChange,
  sessionId = 'current',
  className = ''
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [ollamaModels, setOllamaModels] = useState([]);
  const [configuredProviders, setConfiguredProviders] = useState([]);
  const [cloudModels, setCloudModels] = useState({});
  const [status, setStatus] = useState('idle');
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Fetch models when opened
  useEffect(() => {
    if (isOpen && status === 'idle') {
      setStatus('loading');

      // Fetch both available models and configured providers
      Promise.all([
        api.get('/llm/available-models'),
        api.get('/llm/providers/configured').catch(() => ({ data: { providers: [] } }))
      ])
        .then(([modelsRes, configuredRes]) => {
          // Get installed Ollama models (filter out embedding models)
          const embeddingPatterns = ['minilm', 'embed', 'bge', 'e5-', 'gte-'];
          const allOllamaModels = modelsRes.data?.ollama_installed || [];
          const chatModels = allOllamaModels.filter(model => {
            const lowerModel = model.toLowerCase();
            return !embeddingPatterns.some(pattern => lowerModel.includes(pattern));
          });
          setOllamaModels(chatModels);

          // Get configured cloud providers
          const configured = configuredRes.data?.providers || [];
          setConfiguredProviders(configured);

          // Get cloud models only for configured providers
          const allModels = modelsRes.data?.models || {};
          const filteredCloud = {};

          configured.forEach(config => {
            const providerId = config.provider?.toLowerCase() || config.provider;
            if (allModels[providerId]) {
              filteredCloud[providerId] = allModels[providerId];
            }
          });

          setCloudModels(filteredCloud);
          setStatus('done');
        })
        .catch(err => {
          console.error('LLMSwitcher Error:', err);
          setStatus('error');
        });
    }
  }, [isOpen, status]);

  // Reset when closed
  useEffect(() => {
    if (!isOpen) setStatus('idle');
  }, [isOpen]);

  const selectModel = (provider, model) => {
    if (onModelChange) onModelChange(provider, model);
    setIsOpen(false);
  };

  // Get display name for current model
  const getDisplayName = () => {
    if (currentProvider === 'ollama' && currentModel) {
      // Clean up ollama model names (remove :latest, etc.)
      return currentModel.split(':')[0];
    }
    return currentModel;
  };

  // Check if a model is currently selected
  const isSelected = (provider, model) => {
    return currentProvider === provider && currentModel === model;
  };

  const hasConfiguredCloud = Object.keys(cloudModels).length > 0;

  return (
    <div ref={dropdownRef} className={`relative ${className}`}>
      {/* Trigger Button - Athenian Style */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-200 group"
        style={{
          backgroundColor: THEME.bgCard,
          border: `1px solid ${THEME.border}`,
          color: THEME.textPrimary,
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = THEME.primary;
          e.currentTarget.style.boxShadow = `0 2px 8px rgba(107, 124, 94, 0.15)`;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = THEME.border;
          e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.08)';
        }}
      >
        <Cpu size={14} style={{ color: THEME.primary }} />
        <span className="text-sm font-medium">{getDisplayName()}</span>
        <ChevronDown
          size={14}
          style={{
            color: THEME.textMuted,
            transform: isOpen ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.2s ease'
          }}
        />
      </button>

      {/* Dropdown Panel - Athenian Style */}
      {isOpen && (
        <div
          className="absolute top-full left-0 mt-2 w-72 rounded-xl overflow-hidden z-50"
          style={{
            backgroundColor: THEME.bgCard,
            border: `1px solid ${THEME.border}`,
            boxShadow: '0 8px 32px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.08)',
          }}
        >
          {/* Header */}
          <div
            className="px-4 py-3 border-b"
            style={{
              backgroundColor: THEME.bgSecondary,
              borderColor: THEME.borderLight,
            }}
          >
            <div className="flex items-center gap-2">
              <Sparkles size={16} style={{ color: THEME.primary }} />
              <span className="font-semibold text-sm" style={{ color: THEME.textPrimary }}>
                Select Model
              </span>
            </div>
            <p className="text-xs mt-0.5" style={{ color: THEME.textMuted }}>
              {status === 'loading' ? 'Loading available models...' : 'Choose AI model for this chat'}
            </p>
          </div>

          {/* Content */}
          <div className="max-h-80 overflow-y-auto">
            {status === 'loading' && (
              <div className="flex flex-col items-center justify-center py-10">
                <Loader2 size={24} className="animate-spin" style={{ color: THEME.primary }} />
                <span className="text-sm mt-2" style={{ color: THEME.textMuted }}>Loading models...</span>
              </div>
            )}

            {status === 'error' && (
              <div className="flex flex-col items-center justify-center py-10">
                <span className="text-sm font-medium" style={{ color: '#dc2626' }}>Error loading models</span>
                <span className="text-xs mt-1" style={{ color: THEME.textMuted }}>Check backend connection</span>
              </div>
            )}

            {status === 'done' && (
              <>
                {/* Local Ollama Models Section */}
                {ollamaModels.length > 0 && (
                  <div>
                    <div
                      className="px-4 py-2 flex items-center gap-2"
                      style={{
                        backgroundColor: THEME.bgSecondary,
                        borderBottom: `1px solid ${THEME.borderLight}`,
                      }}
                    >
                      <Cpu size={12} style={{ color: THEME.primary }} />
                      <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: THEME.textSecondary }}>
                        Local Models
                      </span>
                      <span className="text-xs px-1.5 py-0.5 rounded-full" style={{
                        backgroundColor: THEME.hover,
                        color: THEME.textSecondary
                      }}>
                        {ollamaModels.length}
                      </span>
                    </div>

                    {ollamaModels.map(model => {
                      const selected = isSelected('ollama', model);
                      return (
                        <button
                          key={`ollama-${model}`}
                          onClick={() => selectModel('ollama', model)}
                          className="flex items-center justify-between w-full px-4 py-2.5 text-left transition-colors"
                          style={{
                            backgroundColor: selected ? THEME.hover : 'transparent',
                            borderBottom: `1px solid ${THEME.borderLight}`,
                          }}
                          onMouseEnter={(e) => !selected && (e.currentTarget.style.backgroundColor = THEME.hover)}
                          onMouseLeave={(e) => !selected && (e.currentTarget.style.backgroundColor = 'transparent')}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-base">🦙</span>
                            <span className="text-sm font-medium" style={{ color: THEME.textPrimary }}>
                              {model}
                            </span>
                          </div>
                          {selected && <Check size={16} style={{ color: THEME.success }} />}
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* Cloud Provider Models Section */}
                {hasConfiguredCloud && (
                  <div>
                    <div
                      className="px-4 py-2 flex items-center gap-2"
                      style={{
                        backgroundColor: THEME.bgSecondary,
                        borderBottom: `1px solid ${THEME.borderLight}`,
                      }}
                    >
                      <Cloud size={12} style={{ color: THEME.primary }} />
                      <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: THEME.textSecondary }}>
                        Cloud APIs
                      </span>
                    </div>

                    {Object.entries(cloudModels).map(([provider, models]) => {
                      if (!models || models.length === 0) return null;
                      const meta = PROVIDER_META[provider] || { name: provider, icon: '🤖' };

                      return (
                        <div key={provider}>
                          {/* Provider Sub-header */}
                          <div
                            className="px-4 py-1.5 flex items-center gap-1.5"
                            style={{ backgroundColor: 'rgba(107, 124, 94, 0.03)' }}
                          >
                            <span className="text-sm">{meta.icon}</span>
                            <span className="text-xs font-medium" style={{ color: THEME.textMuted }}>
                              {meta.name}
                            </span>
                          </div>

                          {/* Models */}
                          {models.slice(0, 4).map(model => {
                            const modelId = model.id || model;
                            const modelName = model.name || modelId;
                            const selected = isSelected(provider, modelId);

                            return (
                              <button
                                key={`${provider}-${modelId}`}
                                onClick={() => selectModel(provider, modelId)}
                                className="flex items-center justify-between w-full px-4 py-2.5 text-left transition-colors"
                                style={{
                                  backgroundColor: selected ? THEME.hover : 'transparent',
                                  borderBottom: `1px solid ${THEME.borderLight}`,
                                }}
                                onMouseEnter={(e) => !selected && (e.currentTarget.style.backgroundColor = THEME.hover)}
                                onMouseLeave={(e) => !selected && (e.currentTarget.style.backgroundColor = 'transparent')}
                              >
                                <span className="text-sm font-medium pl-5" style={{ color: THEME.textPrimary }}>
                                  {modelName}
                                </span>
                                {selected && <Check size={16} style={{ color: THEME.success }} />}
                              </button>
                            );
                          })}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Empty State */}
                {ollamaModels.length === 0 && !hasConfiguredCloud && (
                  <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
                    <Cpu size={32} style={{ color: THEME.textMuted, opacity: 0.5 }} />
                    <span className="text-sm font-medium mt-3" style={{ color: THEME.textPrimary }}>
                      No models available
                    </span>
                    <span className="text-xs mt-1" style={{ color: THEME.textMuted }}>
                      Run <code className="px-1 py-0.5 rounded" style={{ backgroundColor: THEME.bgSecondary }}>ollama serve</code> or configure cloud APIs
                    </span>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Footer - Settings Link */}
          <div
            className="px-3 py-2.5 border-t"
            style={{
              backgroundColor: THEME.bgSecondary,
              borderColor: THEME.borderLight,
            }}
          >
            <button
              onClick={() => { setIsOpen(false); navigate('/app/settings'); }}
              className="flex items-center justify-center gap-2 w-full px-3 py-2 rounded-lg transition-all"
              style={{
                backgroundColor: THEME.bgCard,
                border: `1px solid ${THEME.border}`,
                color: THEME.textSecondary,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = THEME.hover;
                e.currentTarget.style.borderColor = THEME.primary;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = THEME.bgCard;
                e.currentTarget.style.borderColor = THEME.border;
              }}
            >
              <Settings size={14} />
              <span className="text-xs font-medium">Manage API Keys</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
