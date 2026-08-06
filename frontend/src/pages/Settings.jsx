import { useState, useEffect } from 'react'
import {
  Settings as SettingsIcon, Server, Check, AlertCircle,
  RefreshCw, Key, Eye, EyeOff, Trash2, Loader2, TestTube
} from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { CLOUD_PROVIDERS, CLOUD_PROVIDER_ORDER } from '../config/providers'

// ============== CLOUD PROVIDER CARD ==============
function CloudProviderCard({ provider, config, onSave, onTest, onDelete, isLoading }) {
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState(config?.base_url || provider.defaultBaseUrl || '')
  const [defaultModel, setDefaultModel] = useState(config?.extra_settings?.default_model || provider.defaultModelName || '')
  const [showKey, setShowKey] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

  const isConfigured = config?.id

  const handleSave = async () => {
    setTestResult(null)
    try {
      await onSave({
        provider: provider.id,
        name: provider.displayName,
        api_key: apiKey || undefined,
        base_url: baseUrl || undefined,
        default_model: provider.requiresModelName ? (defaultModel || undefined) : undefined,
        // The institutional endpoint is the recommended primary provider -
        // saving/updating it always (re)claims the default slot so chat and
        // video generation prefer it over any previously-configured key.
        is_default: provider.id === 'custom',
      })
      setApiKey('')
      setTestResult({ success: true, message: 'API key saved' })
    } catch (error) {
      setTestResult({ success: false, message: error.message })
    }
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
        <div className="flex items-center gap-3">
          {provider.recommended && (
            <span className="text-xs px-2 py-1 rounded-full bg-accent-olive/15 text-accent-olive font-medium">
              Recommended
            </span>
          )}
          {isConfigured && (
            <div className="flex items-center gap-1 text-xs text-accent-olive">
              <Check className="w-4 h-4" />
              <span>Configured</span>
            </div>
          )}
        </div>
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

        {/* Base URL for Azure / Custom */}
        {provider.requiresBaseUrl && (
          <div>
            <label className="block text-sm text-text-secondary mb-1">API Base URL</label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder={provider.id === 'custom' ? 'https://your-endpoint.example.com/v1' : 'https://your-resource.openai.azure.com'}
              className="w-full px-3 py-2 bg-bg-card border border-border-color rounded-lg text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-olive"
            />
          </div>
        )}

        {/* Model name for Custom (no fixed model list) */}
        {provider.requiresModelName && (
          <div>
            <label className="block text-sm text-text-secondary mb-1">Model Name</label>
            <input
              type="text"
              value={defaultModel}
              onChange={(e) => setDefaultModel(e.target.value)}
              placeholder="e.g. llama-3.3-70b"
              className="w-full px-3 py-2 bg-bg-card border border-border-color rounded-lg text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-olive"
            />
          </div>
        )}

        {provider.networkNote && (
          <div className="flex items-start gap-2 text-xs text-text-muted bg-bg-tertiary px-3 py-2 rounded-lg border border-border-color">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
            <span>{provider.networkNote}</span>
          </div>
        )}

        {/* Available Models Preview */}
        {provider.models.length > 0 && (
          <div className="text-xs text-text-muted">
            <span className="font-medium">Models: </span>
            {provider.models.slice(0, 3).map(m => m.name).join(', ')}
            {provider.models.length > 3 && ` +${provider.models.length - 3} more`}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={isLoading || !apiKey.trim() || (provider.requiresBaseUrl && !isConfigured && !baseUrl.trim())}
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
  const [configuredProviders, setConfiguredProviders] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [validationError, setValidationError] = useState(null)
  const api = useApi()

  useEffect(() => {
    loadAll()
  }, [])

  const loadAll = async () => {
    setLoading(true)
    try {
      const llmProviders = await api.get('/llm/providers/configured')
      setConfiguredProviders(llmProviders.providers || [])
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
      // Re-throw so the calling ProviderCard's handleSave can show the
      // failure to the user - this used to be swallowed here entirely,
      // so a failed save (e.g. a backend/DB error) looked identical to a
      // successful one from the UI's perspective.
      throw new Error(error.response?.data?.detail || error.message || 'Failed to save provider')
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
            <p className="text-text-muted">Configure your AI provider API keys</p>
          </div>
          <button
            onClick={loadAll}
            className="ml-auto p-2 rounded-xl bg-bg-card border border-border-color hover:bg-bg-tertiary transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-5 h-5 text-text-muted ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Validation Error Banner */}
        {validationError && (
          <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm text-red-700 mb-2">{validationError.message}</p>
                {validationError.suggestion && (
                  <div className="text-sm">
                    <span className="text-red-600 font-medium">Fix: </span>
                    <code className="bg-red-100 text-red-800 px-2 py-0.5 rounded font-mono text-xs">
                      {validationError.suggestion}
                    </code>
                  </div>
                )}
              </div>
              <button
                onClick={() => setValidationError(null)}
                className="text-red-600 hover:text-red-800 p-1"
              >
                <span className="sr-only">Dismiss</span>
                ×
              </button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-3">
              <Loader2 className="w-6 h-6 text-accent-olive animate-spin" />
              <span className="text-text-muted">Loading providers...</span>
            </div>
          </div>
        ) : (
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
      </div>
    </div>
  )
}
