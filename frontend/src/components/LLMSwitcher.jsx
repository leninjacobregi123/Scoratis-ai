/**
 * LLM Model Switcher Component
 * Allows switching between different LLM providers and models
 */

import { useState, useEffect, useRef } from 'react';
import { ChevronDown, Check, Settings, Loader2, Monitor, Cloud, Server } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

// Provider display names and icons
const PROVIDER_META = {
  ollama: { name: 'Ollama', local: true },
  lmstudio: { name: 'LM Studio', local: true },
  localai: { name: 'LocalAI', local: true },
  textgenwebui: { name: 'Text Gen WebUI', local: true },
  openai: { name: 'OpenAI', local: false },
  anthropic: { name: 'Anthropic', local: false },
  google: { name: 'Google AI', local: false },
  groq: { name: 'Groq', local: false },
  together: { name: 'Together AI', local: false },
  azure: { name: 'Azure OpenAI', local: false },
  deepseek: { name: 'DeepSeek', local: false },
};

export default function LLMSwitcher({
  currentProvider = 'ollama',
  currentModel = 'llama3.2',
  onModelChange,
  sessionId = 'current',
  className = ''
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [allModels, setAllModels] = useState({});
  const [ollamaInstalled, setOllamaInstalled] = useState([]);
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

  // Fetch when opened
  useEffect(() => {
    if (isOpen && status === 'idle') {
      setStatus('loading');
      api.get('/llm/available-models')
        .then(res => {
          console.log('LLMSwitcher API Response:', res.data);
          setAllModels(res.data?.models || {});
          setOllamaInstalled(res.data?.ollama_installed || []);
          setStatus('done');
        })
        .catch(err => {
          console.error('LLMSwitcher API Error:', err);
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
      return currentModel.split(':')[0];
    }
    return currentModel;
  };

  return (
    <div ref={dropdownRef} style={{ position: 'relative' }}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 14px',
          backgroundColor: 'rgba(255,255,255,0.95)',
          border: '1px solid rgba(0,0,0,0.1)',
          borderRadius: '10px',
          cursor: 'pointer',
          fontSize: '13px',
          fontWeight: '500',
          color: '#333',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          transition: 'all 0.2s ease'
        }}
      >
        <Monitor size={15} style={{ opacity: 0.7 }} />
        <span>{getDisplayName()}</span>
        <ChevronDown
          size={14}
          style={{
            opacity: 0.6,
            transform: isOpen ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.2s ease'
          }}
        />
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div style={{
          position: 'absolute',
          top: 'calc(100% + 8px)',
          left: 0,
          width: '320px',
          backgroundColor: '#fff',
          border: '1px solid rgba(0,0,0,0.1)',
          borderRadius: '14px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
          zIndex: 999999,
          overflow: 'hidden'
        }}>
          {/* Header */}
          <div style={{
            padding: '14px 18px',
            borderBottom: '1px solid #eee',
            background: 'linear-gradient(to bottom, #f8f8f8, #fff)'
          }}>
            <div style={{ fontWeight: '600', fontSize: '15px', color: '#222' }}>Select Model</div>
            <div style={{ fontSize: '11px', color: '#888', marginTop: '2px' }}>
              {status === 'loading' ? 'Loading...' : 'Choose AI model for this chat'}
            </div>
          </div>

          {/* Content */}
          <div style={{ maxHeight: '380px', overflowY: 'auto' }}>
            {status === 'loading' && (
              <div style={{ padding: '40px 20px', textAlign: 'center' }}>
                <Loader2 size={28} style={{ animation: 'spin 1s linear infinite', color: '#666' }} />
                <div style={{ marginTop: '12px', color: '#666', fontSize: '14px' }}>Loading models...</div>
              </div>
            )}

            {status === 'error' && (
              <div style={{ padding: '40px 20px', textAlign: 'center', color: '#dc2626' }}>
                <div style={{ fontSize: '14px', fontWeight: '500' }}>Error loading models</div>
                <div style={{ fontSize: '12px', marginTop: '4px', opacity: 0.8 }}>Check backend connection</div>
              </div>
            )}

            {status === 'done' && (
              <>
                {/* Ollama Installed Models (Local) */}
                {ollamaInstalled.length > 0 && (
                  <div>
                    <div style={{
                      padding: '10px 18px',
                      backgroundColor: '#f5f5f5',
                      fontSize: '11px',
                      fontWeight: '600',
                      color: '#555',
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}>
                      <Server size={12} />
                      Ollama (Local) - {ollamaInstalled.length} installed
                    </div>
                    {ollamaInstalled.map(model => {
                      const isSelected = currentProvider === 'ollama' && currentModel === model;
                      return (
                        <button
                          key={`ollama-${model}`}
                          onClick={() => selectModel('ollama', model)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            width: '100%',
                            padding: '12px 18px',
                            border: 'none',
                            borderBottom: '1px solid #f0f0f0',
                            backgroundColor: isSelected ? '#e8f5e9' : '#fff',
                            textAlign: 'left',
                            cursor: 'pointer',
                            fontSize: '14px',
                            color: '#333',
                            transition: 'background-color 0.15s ease'
                          }}
                          onMouseEnter={(e) => !isSelected && (e.target.style.backgroundColor = '#f8f8f8')}
                          onMouseLeave={(e) => !isSelected && (e.target.style.backgroundColor = '#fff')}
                        >
                          <span>{model}</span>
                          {isSelected && <Check size={16} style={{ color: '#22c55e' }} />}
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* Cloud Providers */}
                {Object.entries(allModels)
                  .filter(([provider]) => !PROVIDER_META[provider]?.local)
                  .map(([provider, models]) => {
                    if (!models || models.length === 0) return null;
                    const meta = PROVIDER_META[provider] || { name: provider };

                    return (
                      <div key={provider}>
                        <div style={{
                          padding: '10px 18px',
                          backgroundColor: '#f5f5f5',
                          fontSize: '11px',
                          fontWeight: '600',
                          color: '#555',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}>
                          <Cloud size={12} />
                          {meta.name}
                        </div>
                        {models.slice(0, 4).map(model => {
                          const modelId = model.id || model;
                          const modelName = model.name || modelId;
                          const isSelected = currentProvider === provider && currentModel === modelId;

                          return (
                            <button
                              key={`${provider}-${modelId}`}
                              onClick={() => selectModel(provider, modelId)}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                width: '100%',
                                padding: '12px 18px',
                                border: 'none',
                                borderBottom: '1px solid #f0f0f0',
                                backgroundColor: isSelected ? '#e8f5e9' : '#fff',
                                textAlign: 'left',
                                cursor: 'pointer',
                                fontSize: '14px',
                                color: '#333',
                                transition: 'background-color 0.15s ease'
                              }}
                              onMouseEnter={(e) => !isSelected && (e.target.style.backgroundColor = '#f8f8f8')}
                              onMouseLeave={(e) => !isSelected && (e.target.style.backgroundColor = '#fff')}
                            >
                              <span>{modelName}</span>
                              {isSelected && <Check size={16} style={{ color: '#22c55e' }} />}
                            </button>
                          );
                        })}
                      </div>
                    );
                  })}

                {ollamaInstalled.length === 0 && Object.keys(allModels).length === 0 && (
                  <div style={{ padding: '40px 20px', textAlign: 'center', color: '#666' }}>
                    <div style={{ fontSize: '14px' }}>No models available</div>
                    <div style={{ fontSize: '12px', marginTop: '4px', opacity: 0.7 }}>
                      Run: ollama serve
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Footer */}
          <div style={{
            padding: '12px 18px',
            borderTop: '1px solid #eee',
            background: 'linear-gradient(to top, #f8f8f8, #fff)'
          }}>
            <button
              onClick={() => { setIsOpen(false); navigate('/app/settings'); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                width: '100%',
                padding: '10px',
                backgroundColor: '#fff',
                border: '1px solid #ddd',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '13px',
                color: '#555',
                fontWeight: '500',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => { e.target.style.backgroundColor = '#f5f5f5'; e.target.style.borderColor = '#ccc'; }}
              onMouseLeave={(e) => { e.target.style.backgroundColor = '#fff'; e.target.style.borderColor = '#ddd'; }}
            >
              <Settings size={14} />
              Manage API Keys
            </button>
          </div>
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
