/**
 * LLM Provider Configuration
 * Defines available providers and their models for the model switcher
 * Supports both cloud APIs and local LLM providers
 */

// Local LLM Providers (No API key required, run on your machine)
export const LOCAL_PROVIDERS = {
  ollama: {
    id: 'ollama',
    name: 'Ollama',
    displayName: 'Ollama',
    requiresApiKey: false,
    isLocal: true,
    defaultBaseUrl: 'http://localhost:11434',
    description: 'Popular local LLM runner with easy model management',
    setupCommand: 'curl -fsSL https://ollama.com/install.sh | sh',
    color: '#4A90D9',
    models: [
      { id: 'llama3.2', name: 'Llama 3.2 3B', description: 'Fast & efficient', recommended: true },
      { id: 'llama3.2:1b', name: 'Llama 3.2 1B', description: 'Ultra lightweight' },
      { id: 'llama3.1', name: 'Llama 3.1 8B', description: 'Excellent quality' },
      { id: 'llama3.1:70b', name: 'Llama 3.1 70B', description: 'Best quality (needs 48GB+ VRAM)' },
      { id: 'mistral', name: 'Mistral 7B', description: 'Fast and capable' },
      { id: 'mixtral', name: 'Mixtral 8x7B', description: 'Mixture of experts' },
      { id: 'qwen2.5', name: 'Qwen 2.5 7B', description: 'Strong reasoning' },
      { id: 'qwen2.5:32b', name: 'Qwen 2.5 32B', description: 'Excellent all-around' },
      { id: 'phi3', name: 'Phi-3 Mini', description: 'Microsoft small model' },
      { id: 'gemma2', name: 'Gemma 2 9B', description: 'Google open model' },
      { id: 'codellama', name: 'CodeLlama 7B', description: 'Meta coding model' },
      { id: 'deepseek-coder', name: 'DeepSeek Coder', description: 'Code specialized' },
      { id: 'deepseek-coder-v2', name: 'DeepSeek Coder V2', description: 'Latest code model' },
      { id: 'starcoder2', name: 'StarCoder2 7B', description: 'Code generation' },
    ],
  },
  lmstudio: {
    id: 'lmstudio',
    name: 'LM Studio',
    displayName: 'LM Studio',
    requiresApiKey: false,
    isLocal: true,
    defaultBaseUrl: 'http://localhost:1234/v1',
    description: 'GUI app for running local models with OpenAI-compatible API',
    setupUrl: 'https://lmstudio.ai/',
    color: '#8B5CF6',
    models: [
      { id: 'local-model', name: 'Loaded Model', description: 'Currently loaded model in LM Studio' },
    ],
    note: 'Models are managed in LM Studio app. Start local server to use.',
  },
  localai: {
    id: 'localai',
    name: 'LocalAI',
    displayName: 'LocalAI',
    requiresApiKey: false,
    isLocal: true,
    defaultBaseUrl: 'http://localhost:8080/v1',
    description: 'Self-hosted OpenAI-compatible API for various model formats',
    setupCommand: 'docker run -p 8080:8080 localai/localai',
    color: '#10B981',
    models: [
      { id: 'gpt4all-j', name: 'GPT4All-J', description: 'General purpose' },
      { id: 'ggml-gpt4all-j', name: 'GGML GPT4All', description: 'Optimized GGML' },
      { id: 'wizardlm', name: 'WizardLM', description: 'Instruction following' },
      { id: 'orca-mini', name: 'Orca Mini', description: 'Microsoft Orca' },
    ],
    note: 'Download models separately. Supports GGML, GGUF, and more.',
  },
  textgenwebui: {
    id: 'textgenwebui',
    name: 'Text Generation WebUI',
    displayName: 'Text Gen WebUI',
    requiresApiKey: false,
    isLocal: true,
    defaultBaseUrl: 'http://localhost:5000/v1',
    description: 'Gradio web UI with extensive model support and extensions',
    setupUrl: 'https://github.com/oobabooga/text-generation-webui',
    color: '#F59E0B',
    models: [
      { id: 'loaded-model', name: 'Loaded Model', description: 'Currently loaded in WebUI' },
    ],
    note: 'Enable API extension in WebUI settings. Supports many formats.',
  },
};

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
};

// Combined providers
export const PROVIDERS = {
  ...LOCAL_PROVIDERS,
  ...CLOUD_PROVIDERS,
};

// Order for display
export const LOCAL_PROVIDER_ORDER = ['ollama', 'lmstudio', 'localai', 'textgenwebui'];
export const CLOUD_PROVIDER_ORDER = ['openai', 'anthropic', 'google', 'groq', 'together', 'deepseek', 'azure'];
export const PROVIDER_ORDER = [...LOCAL_PROVIDER_ORDER, ...CLOUD_PROVIDER_ORDER];

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

export function isLocalProvider(providerId) {
  return LOCAL_PROVIDERS[providerId] !== undefined;
}

export function getProvidersByType(type) {
  if (type === 'local') return LOCAL_PROVIDERS;
  if (type === 'cloud') return CLOUD_PROVIDERS;
  return PROVIDERS;
}

export default PROVIDERS;
