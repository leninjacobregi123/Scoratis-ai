import { useState, useEffect } from 'react'
import {
  Settings as SettingsIcon, Cpu, Server, Check, AlertCircle,
  ChevronDown, ChevronRight, RefreshCw, Activity,
  Thermometer, Hash, TestTube, Loader2, Download, Terminal,
  Key, Eye, EyeOff, Trash2, Plus, Wifi, WifiOff, ExternalLink, Monitor
} from 'lucide-react'
import { useApi } from '../hooks/useApi'
import {
  PROVIDERS, LOCAL_PROVIDERS, CLOUD_PROVIDERS,
  LOCAL_PROVIDER_ORDER, CLOUD_PROVIDER_ORDER
} from '../config/providers'

// ============== LOCAL PROVIDER CARD ==============
function LocalProviderCard({ provider, config, onSave, onTest, onDelete, isLoading, ollamaStatus }) {
  const [baseUrl, setBaseUrl] = useState(config?.base_url || provider.defaultBaseUrl || '')
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

  const isConfigured = config?.id
  const isOllama = provider.id === 'ollama'
  const isAvailable = isOllama ? ollamaStatus?.available : isConfigured

  const handleSave = async () => {
    await onSave({
      provider: provider.id,
      name: provider.displayName,
      base_url: baseUrl,
      is_default: false,
    })
  }

  const handleTest = async () => {
    if (!config?.id && !isOllama) return
    setTesting(true)
    setTestResult(null)
    try {
      if (isOllama) {
        setTestResult({ success: ollamaStatus?.available, message: ollamaStatus?.available ? 'Ollama is running' : 'Ollama not available' })
      } else {
        const result = await onTest(config.id)
        setTestResult(result)
      }
    } catch (error) {
      setTestResult({ success: false, message: error.message })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className={`p-5 rounded-xl border transition-all ${
      isAvailable
        ? 'bg-bg-secondary border-accent-olive/30'
        : 'bg-bg-card border-border-color'
    }`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-accent-olive/10 flex items-center justify-center">
            <Monitor className="w-5 h-5 text-accent-olive" />
          </div>
          <div>
            <h3 className="font-semibold text-text-primary">{provider.displayName}</h3>
            <p className="text-xs text-text-muted">{provider.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isAvailable ? (
            <div className="flex items-center gap-1 text-xs text-accent-olive">
              <Wifi className="w-4 h-4" />
              <span>Connected</span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-xs text-text-muted">
              <WifiOff className="w-4 h-4" />
              <span>Offline</span>
            </div>
          )}
        </div>
      </div>

      {/* Ollama specific status */}
      {isOllama && ollamaStatus && (
        <div className="mb-4 p-3 rounded-lg bg-bg-tertiary border border-border-color">
          {ollamaStatus.available ? (
            <div>
              <div className="flex items-center gap-2 text-accent-olive text-sm mb-2">
                <Check className="w-4 h-4" />
                <span>Ollama Running</span>
              </div>
              {ollamaStatus.installed_models?.length > 0 && (
                <div className="text-xs text-text-muted">
                  Installed: {ollamaStatus.installed_models.slice(0, 5).join(', ')}
                  {ollamaStatus.installed_models.length > 5 && ` +${ollamaStatus.installed_models.length - 5} more`}
                </div>
              )}
            </div>
          ) : (
            <div className="text-sm">
              <div className="text-red-600 mb-2">Ollama not running</div>
              <code className="text-xs text-accent-olive bg-bg-primary px-2 py-1 rounded">
                {provider.setupCommand}
              </code>
            </div>
          )}
        </div>
      )}

      {/* Base URL Configuration for non-Ollama providers */}
      {!isOllama && (
        <div className="space-y-3">
          <div>
            <label className="block text-sm text-text-secondary mb-1">Server URL</label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder={provider.defaultBaseUrl}
              className="w-full px-3 py-2 bg-bg-card border border-border-color rounded-lg text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-olive"
            />
          </div>

          {provider.note && (
            <p className="text-xs text-text-muted italic">{provider.note}</p>
          )}

          {provider.setupUrl && (
            <a
              href={provider.setupUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-accent-olive hover:underline"
            >
              <ExternalLink className="w-3 h-3" />
              Download {provider.displayName}
            </a>
          )}

          {provider.setupCommand && (
            <div className="text-xs">
              <span className="text-text-muted">Setup: </span>
              <code className="text-accent-olive bg-bg-primary px-2 py-1 rounded">{provider.setupCommand}</code>
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={isLoading || !baseUrl.trim()}
              className="flex-1 px-4 py-2 bg-accent-olive/20 text-accent-olive rounded-lg hover:bg-accent-olive/30 transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Saving...' : isConfigured ? 'Update' : 'Save'}
            </button>
            {isConfigured && (
              <>
                <button
                  onClick={handleTest}
                  disabled={testing}
                  className="px-4 py-2 bg-bg-tertiary text-text-secondary rounded-lg hover:text-text-primary transition-colors disabled:opacity-50"
                >
                  {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <TestTube className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => onDelete(config.id)}
                  className="px-4 py-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {testResult && (
        <div className={`mt-3 p-3 rounded-lg ${testResult.success ? 'bg-accent-olive/10 border border-accent-olive/30' : 'bg-red-50 border border-red-200'}`}>
          <div className="flex items-center gap-2">
            {testResult.success ? <Check className="w-4 h-4 text-accent-olive" /> : <AlertCircle className="w-4 h-4 text-red-600" />}
            <span className={`text-sm ${testResult.success ? 'text-accent-olive' : 'text-red-600'}`}>{testResult.message}</span>
          </div>
        </div>
      )}
    </div>
  )
}

// ============== CLOUD PROVIDER CARD ==============
function CloudProviderCard({ provider, config, onSave, onTest, onDelete, isLoading }) {
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState(config?.base_url || '')
  const [showKey, setShowKey] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

  const isConfigured = config?.id

  const handleSave = async () => {
    await onSave({
      provider: provider.id,
      name: provider.displayName,
      api_key: apiKey || undefined,
      base_url: baseUrl || undefined,
      is_default: false,
    })
    setApiKey('')
  }

  const handleTest = async () => {
    if (!config?.id) return
    setTesting(true)
    setTestResult(null)
    try {
      const result = await onTest(config.id)
      setTestResult(result)
    } catch (error) {
      setTestResult({ success: false, message: error.message })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className={`p-5 rounded-xl border transition-all ${
      isConfigured
        ? 'bg-bg-secondary border-accent-olive/30'
        : 'bg-bg-card border-border-color'
    }`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-accent-olive/10 flex items-center justify-center">
            <Server className="w-5 h-5 text-accent-olive" />
          </div>
          <div>
            <h3 className="font-semibold text-text-primary">{provider.displayName}</h3>
            <p className="text-xs text-text-muted">{provider.description}</p>
          </div>
        </div>
        {isConfigured && (
          <div className="flex items-center gap-1 text-xs text-accent-olive">
            <Check className="w-4 h-4" />
            <span>Configured</span>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {/* Current API Key Display */}
        {isConfigured && config.api_key_masked && (
          <div className="flex items-center gap-2 text-sm text-text-muted bg-bg-tertiary px-3 py-2 rounded-lg border border-border-color">
            <Key className="w-4 h-4" />
            <span className="font-mono">{config.api_key_masked}</span>
          </div>
        )}

        {/* API Key Input */}
        <div>
          <label className="block text-sm text-text-secondary mb-1">
            {isConfigured ? 'Update API Key' : 'API Key'}
          </label>
          <div className="relative">
            <input
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={isConfigured ? 'Enter new key to update...' : `Enter your ${provider.name} API key`}
              className="w-full px-3 py-2 pr-10 bg-bg-card border border-border-color rounded-lg text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-olive"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
            >
              {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Base URL for Azure */}
        {provider.requiresBaseUrl && (
          <div>
            <label className="block text-sm text-text-secondary mb-1">API Base URL</label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://your-resource.openai.azure.com"
              className="w-full px-3 py-2 bg-bg-card border border-border-color rounded-lg text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-olive"
            />
          </div>
        )}

        {/* Available Models Preview */}
        <div className="text-xs text-text-muted">
          <span className="font-medium">Models: </span>
          {provider.models.slice(0, 3).map(m => m.name).join(', ')}
          {provider.models.length > 3 && ` +${provider.models.length - 3} more`}
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={isLoading || !apiKey.trim()}
            className="flex-1 px-4 py-2 bg-accent-olive/20 text-accent-olive rounded-lg hover:bg-accent-olive/30 transition-colors disabled:opacity-50"
          >
            {isLoading ? 'Saving...' : isConfigured ? 'Update Key' : 'Save'}
          </button>
          {isConfigured && (
            <>
              <button
                onClick={handleTest}
                disabled={testing}
                className="px-4 py-2 bg-bg-tertiary text-text-secondary rounded-lg hover:text-text-primary transition-colors disabled:opacity-50"
              >
                {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <TestTube className="w-4 h-4" />}
              </button>
              <button
                onClick={() => onDelete(config.id)}
                className="px-4 py-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>

      {testResult && (
        <div className={`mt-3 p-3 rounded-lg ${testResult.success ? 'bg-accent-olive/10 border border-accent-olive/30' : 'bg-red-50 border border-red-200'}`}>
          <div className="flex items-center gap-2">
            {testResult.success ? <Check className="w-4 h-4 text-accent-olive" /> : <AlertCircle className="w-4 h-4 text-red-600" />}
            <span className={`text-sm ${testResult.success ? 'text-accent-olive' : 'text-red-600'}`}>{testResult.message}</span>
          </div>
        </div>
      )}
    </div>
  )
}

// ============== MAIN SETTINGS COMPONENT ==============
export default function Settings() {
  const [activeTab, setActiveTab] = useState('local')
  const [configuredProviders, setConfiguredProviders] = useState([])
  const [ollamaStatus, setOllamaStatus] = useState(null)
  const [currentConfig, setCurrentConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [temperature, setTemperature] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(2048)
  const [contextLength, setContextLength] = useState(4096)
  const api = useApi()

  useEffect(() => {
    loadAll()
  }, [])

  const loadAll = async () => {
    setLoading(true)
    try {
      const [providers, models, llmProviders] = await Promise.all([
        api.get('/llm/providers'),
        api.get('/llm/available-models'),
        api.get('/llm/providers/configured')
      ])

      setOllamaStatus({
        available: models.ollama_available || false,
        installed_models: models.ollama_installed || []
      })
      setConfiguredProviders(llmProviders.providers || [])
      setCurrentConfig(providers.current)

      if (providers.current) {
        setTemperature(providers.current.temperature || 0.7)
        setMaxTokens(providers.current.max_tokens || 2048)
        setContextLength(providers.current.context_length || 4096)
      }
    } catch (error) {
      console.error('Failed to load settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const saveProviderConfig = async (config) => {
    setSaving(true)
    try {
      await api.post('/llm/providers/configured', config)
      await loadAll()
    } catch (error) {
      console.error('Failed to save provider:', error)
    } finally {
      setSaving(false)
    }
  }

  const testProviderConfig = async (providerId) => {
    return await api.post(`/llm/providers/${providerId}/test`)
  }

  const deleteProviderConfig = async (providerId) => {
    try {
      await api.delete(`/llm/providers/configured/${providerId}`)
      await loadAll()
    } catch (error) {
      console.error('Failed to delete provider:', error)
    }
  }

  const getProviderConfig = (providerId) => {
    return configuredProviders.find(p => p.provider === providerId)
  }

  const updateModelSettings = async () => {
    if (!currentConfig) return
    setSaving(true)
    try {
      await api.post('/llm/configure', {
        model: currentConfig.model,
        provider: currentConfig.provider || 'ollama',
        temperature,
        max_tokens: maxTokens,
        context_length: contextLength
      })
    } catch (error) {
      console.error('Failed to update settings:', error)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto relative z-10 p-8 bg-bg-primary">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <div className="w-14 h-14 rounded-2xl bg-accent-olive/20 flex items-center justify-center">
            <SettingsIcon className="w-7 h-7 text-accent-olive" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-text-primary" style={{ fontFamily: 'Georgia, serif' }}>
              AI Model Settings
            </h1>
            <p className="text-text-muted">Configure local and cloud AI providers</p>
          </div>
          <button
            onClick={loadAll}
            className="ml-auto p-2 rounded-xl bg-bg-card border border-border-color hover:bg-bg-tertiary transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-5 h-5 text-text-muted ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6 border-b border-border-color pb-4">
          <button
            onClick={() => setActiveTab('local')}
            className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors flex items-center gap-2 ${
              activeTab === 'local'
                ? 'bg-accent-olive/20 text-text-primary border border-accent-olive/30'
                : 'bg-bg-card text-text-muted hover:text-text-primary border border-border-color'
            }`}
          >
            <Monitor className="w-4 h-4" />
            Local LLMs
          </button>
          <button
            onClick={() => setActiveTab('cloud')}
            className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors flex items-center gap-2 ${
              activeTab === 'cloud'
                ? 'bg-accent-olive/20 text-text-primary border border-accent-olive/30'
                : 'bg-bg-card text-text-muted hover:text-text-primary border border-border-color'
            }`}
          >
            <Key className="w-4 h-4" />
            Cloud APIs
          </button>
          <button
            onClick={() => setActiveTab('parameters')}
            className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors flex items-center gap-2 ${
              activeTab === 'parameters'
                ? 'bg-accent-olive/20 text-text-primary border border-accent-olive/30'
                : 'bg-bg-card text-text-muted hover:text-text-primary border border-border-color'
            }`}
          >
            <Thermometer className="w-4 h-4" />
            Parameters
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-3">
              <Loader2 className="w-6 h-6 text-accent-olive animate-spin" />
              <span className="text-text-muted">Loading providers...</span>
            </div>
          </div>
        ) : (
          <>
            {/* Local LLMs Tab */}
            {activeTab === 'local' && (
              <div className="space-y-6">
                <div className="p-4 rounded-xl bg-bg-secondary border border-accent-olive/30">
                  <p className="text-sm text-text-secondary">
                    <strong className="text-text-primary">Local models</strong> run on your machine for complete privacy. No data is sent to external servers.
                    Ollama is recommended for the easiest setup.
                  </p>
                </div>

                <div className="grid gap-4">
                  {LOCAL_PROVIDER_ORDER.map(providerId => {
                    const provider = LOCAL_PROVIDERS[providerId]
                    if (!provider) return null
                    const config = getProviderConfig(providerId)

                    return (
                      <LocalProviderCard
                        key={providerId}
                        provider={provider}
                        config={config}
                        onSave={saveProviderConfig}
                        onTest={testProviderConfig}
                        onDelete={deleteProviderConfig}
                        isLoading={saving}
                        ollamaStatus={providerId === 'ollama' ? ollamaStatus : null}
                      />
                    )
                  })}
                </div>

                {/* Ollama Model Installation Guide */}
                <div className="p-6 rounded-2xl bg-bg-card border border-border-color">
                  <h3 className="text-lg font-semibold text-text-primary mb-3 flex items-center gap-2" style={{ fontFamily: 'Georgia, serif' }}>
                    <Terminal className="w-5 h-5 text-accent-olive" />
                    Install Ollama Models
                  </h3>
                  <p className="text-sm text-text-muted mb-3">
                    Run these commands in your terminal to download models:
                  </p>
                  <div className="font-mono text-sm space-y-2">
                    <div className="flex items-center gap-2 text-text-muted">
                      <span className="text-accent-olive">ollama pull llama3.2</span>
                      <span className="text-xs opacity-60"># Fast, 3B params</span>
                    </div>
                    <div className="flex items-center gap-2 text-text-muted">
                      <span className="text-accent-olive">ollama pull mistral</span>
                      <span className="text-xs opacity-60"># Capable, 7B params</span>
                    </div>
                    <div className="flex items-center gap-2 text-text-muted">
                      <span className="text-accent-olive">ollama pull qwen2.5</span>
                      <span className="text-xs opacity-60"># Strong reasoning</span>
                    </div>
                    <div className="flex items-center gap-2 text-text-muted">
                      <span className="text-accent-olive">ollama pull codellama</span>
                      <span className="text-xs opacity-60"># Coding specialized</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Cloud APIs Tab */}
            {activeTab === 'cloud' && (
              <div className="space-y-6">
                <div className="p-4 rounded-xl bg-bg-secondary border border-accent-olive/30">
                  <p className="text-sm text-text-secondary">
                    <strong className="text-text-primary">Cloud providers</strong> offer powerful models via API. Your API keys are encrypted and stored securely.
                    Data is sent to the provider's servers.
                  </p>
                </div>

                <div className="grid gap-4">
                  {CLOUD_PROVIDER_ORDER.map(providerId => {
                    const provider = CLOUD_PROVIDERS[providerId]
                    if (!provider) return null
                    const config = getProviderConfig(providerId)

                    return (
                      <CloudProviderCard
                        key={providerId}
                        provider={provider}
                        config={config}
                        onSave={saveProviderConfig}
                        onTest={testProviderConfig}
                        onDelete={deleteProviderConfig}
                        isLoading={saving}
                      />
                    )
                  })}
                </div>
              </div>
            )}

            {/* Model Parameters Tab */}
            {activeTab === 'parameters' && (
              <div className="space-y-6">
                {/* Current Model */}
                {currentConfig && (
                  <div className="p-6 rounded-2xl bg-bg-secondary border border-accent-olive/30">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-xl bg-accent-olive/20 flex items-center justify-center">
                        <Activity className="w-6 h-6 text-accent-olive" />
                      </div>
                      <div>
                        <div className="font-semibold text-text-primary text-lg">Active Model</div>
                        <div className="text-sm text-text-muted">
                          {currentConfig.model} via {currentConfig.provider || 'Ollama'}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Parameters */}
                <div className="p-6 rounded-2xl bg-bg-card border border-border-color">
                  <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2" style={{ fontFamily: 'Georgia, serif' }}>
                    <Thermometer className="w-5 h-5 text-accent-olive" />
                    Generation Parameters
                  </h2>

                  <div className="space-y-6">
                    <div>
                      <label className="block text-sm text-text-secondary mb-2">
                        Temperature: <span className="text-accent-olive font-medium">{temperature}</span>
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={temperature}
                        onChange={(e) => setTemperature(parseFloat(e.target.value))}
                        className="w-full accent-accent-olive"
                      />
                      <div className="flex justify-between text-xs text-text-muted mt-1">
                        <span>Precise (0)</span>
                        <span>Creative (1)</span>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm text-text-secondary mb-2">
                        <Hash className="w-4 h-4 inline mr-1" />
                        Max Tokens: <span className="text-accent-olive font-medium">{maxTokens}</span>
                      </label>
                      <input
                        type="range"
                        min="256"
                        max="4096"
                        step="256"
                        value={maxTokens}
                        onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                        className="w-full accent-accent-olive"
                      />
                    </div>

                    <div>
                      <label className="block text-sm text-text-secondary mb-2">
                        Context Length: <span className="text-accent-olive font-medium">{contextLength}</span>
                      </label>
                      <input
                        type="range"
                        min="1024"
                        max="8192"
                        step="1024"
                        value={contextLength}
                        onChange={(e) => setContextLength(parseInt(e.target.value))}
                        className="w-full accent-accent-olive"
                      />
                    </div>
                  </div>

                  <button
                    onClick={updateModelSettings}
                    disabled={saving}
                    className="mt-6 px-6 py-2 bg-accent-olive/20 text-accent-olive rounded-xl hover:bg-accent-olive/30 transition-colors disabled:opacity-50 font-medium"
                  >
                    {saving ? 'Saving...' : 'Apply Settings'}
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
