/**
 * LLM Provider Configuration
 * Defines available cloud providers and their models for the model switcher
 */

// Cloud API Providers (Require API key)
export const CLOUD_PROVIDERS = {
  openai: {
    id: 'openai',
    name: 'OpenAI',
    displayName: 'OpenAI',
    requiresApiKey: true,
    isLocal: false,
    description: 'GPT-4 and GPT-3.5 models',
    color: '#74AA9C',
    models: [
      { id: 'gpt-4o', name: 'GPT-4o', description: 'Most capable', recommended: true },
      { id: 'gpt-4o-mini', name: 'GPT-4o Mini', description: 'Fast & affordable' },
      { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', description: 'High capability' },
      { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', description: 'Fast & cheap' },
      { id: 'o1-preview', name: 'o1 Preview', description: 'Advanced reasoning' },
      { id: 'o1-mini', name: 'o1 Mini', description: 'Fast reasoning' },
    ],
  },
  anthropic: {
    id: 'anthropic',
    name: 'Anthropic',
    displayName: 'Anthropic',
    requiresApiKey: true,
    isLocal: false,
    description: 'Claude models - safe and capable',
    color: '#D4A574',
    models: [
      { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', description: 'Best overall', recommended: true },
      { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus', description: 'Most capable' },
      { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', description: 'Fast & efficient' },
    ],
  },
  google: {
    id: 'google',
    name: 'Google AI',
    displayName: 'Google AI',
    requiresApiKey: true,
    isLocal: false,
    description: 'Gemini models',
    color: '#4285F4',
    models: [
      { id: 'gemini-2.0-flash-exp', name: 'Gemini 2.0 Flash', description: 'Latest & fastest', recommended: true },
      { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', description: 'Most capable' },
      { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash', description: 'Fast & efficient' },
    ],
  },
  groq: {
    id: 'groq',
    name: 'Groq',
    displayName: 'Groq',
    requiresApiKey: true,
    isLocal: false,
    description: 'Ultra-fast inference on LPU hardware',
    color: '#F55036',
    models: [
      { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B', description: 'Most capable', recommended: true },
      { id: 'llama-3.1-70b-versatile', name: 'Llama 3.1 70B', description: 'High quality' },
      { id: 'mixtral-8x7b-32768', name: 'Mixtral 8x7B', description: 'Mixture of experts' },
      { id: 'llama-3.1-8b-instant', name: 'Llama 3.1 8B', description: 'Instant responses' },
      { id: 'gemma2-9b-it', name: 'Gemma 2 9B', description: 'Google Gemma' },
    ],
  },
  together: {
    id: 'together',
    name: 'Together AI',
    displayName: 'Together AI',
    requiresApiKey: true,
    isLocal: false,
    description: 'Open source models at scale',
    color: '#7C3AED',
    models: [
      { id: 'meta-llama/Llama-3.3-70B-Instruct-Turbo', name: 'Llama 3.3 70B', description: 'Most capable', recommended: true },
      { id: 'meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo', name: 'Llama 3.1 405B', description: 'Largest open model' },
      { id: 'deepseek-ai/DeepSeek-R1-Distill-Llama-70B', name: 'DeepSeek R1 70B', description: 'Advanced reasoning' },
      { id: 'Qwen/Qwen2.5-72B-Instruct-Turbo', name: 'Qwen 2.5 72B', description: 'Excellent reasoning' },
      { id: 'mistralai/Mixtral-8x22B-Instruct-v0.1', name: 'Mixtral 8x22B', description: 'Large MoE' },
    ],
  },
  azure: {
    id: 'azure',
    name: 'Azure OpenAI',
    displayName: 'Azure OpenAI',
    requiresApiKey: true,
    isLocal: false,
    description: 'Enterprise Azure deployment',
    color: '#0078D4',
    requiresBaseUrl: true,
    models: [
      { id: 'gpt-4o', name: 'GPT-4o (Azure)', description: 'Enterprise', recommended: true },
      { id: 'gpt-4-turbo', name: 'GPT-4 Turbo (Azure)', description: 'High capability' },
      { id: 'gpt-35-turbo', name: 'GPT-3.5 Turbo (Azure)', description: 'Fast' },
    ],
  },
  deepseek: {
    id: 'deepseek',
    name: 'DeepSeek',
    displayName: 'DeepSeek',
    requiresApiKey: true,
    isLocal: false,
    description: 'DeepSeek reasoning models',
    color: '#0EA5E9',
    models: [
      { id: 'deepseek-chat', name: 'DeepSeek Chat', description: 'General chat', recommended: true },
      { id: 'deepseek-coder', name: 'DeepSeek Coder', description: 'Code specialized' },
      { id: 'deepseek-reasoner', name: 'DeepSeek Reasoner', description: 'Advanced reasoning' },
    ],
  },
  custom: {
    id: 'custom',
    name: 'Custom',
    displayName: 'Institutional (Sofie Code)',
    requiresApiKey: true,
    isLocal: false,
    requiresBaseUrl: true,
    requiresModelName: true,
    recommended: true,
    description: "Karunya University's Sofie Code LLM gateway - just paste your personal key",
    color: '#6b7c5e',
    networkNote: 'Campus network or VPN only - "connection refused/timed out" almost always means you\'re off-campus.',
    models: [],
  },
};

// Combined providers
export const PROVIDERS = {
  ...CLOUD_PROVIDERS,
};

// Order for display - institutional endpoint first since it's the primary/
// recommended provider; the others remain available as fallback options.
export const CLOUD_PROVIDER_ORDER = ['custom', 'openai', 'anthropic', 'google', 'groq', 'together', 'deepseek', 'azure'];
export const PROVIDER_ORDER = [...CLOUD_PROVIDER_ORDER];

// Helper functions
export function getProviderById(id) {
  return PROVIDERS[id] || null;
}

export function getModelById(providerId, modelId) {
  const provider = PROVIDERS[providerId];
  if (!provider) return null;
  return provider.models.find(m => m.id === modelId) || null;
}

export function getProviderDisplayName(providerId, modelId) {
  const provider = PROVIDERS[providerId];
  const model = getModelById(providerId, modelId);
  if (!provider || !model) return modelId;
  return model.name;
}

export default PROVIDERS;
