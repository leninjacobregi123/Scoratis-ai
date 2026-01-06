import { useState, useEffect } from 'react';
import {
  Brain, Search, BookOpen, Globe, CheckCircle, AlertCircle,
  Loader2, Lightbulb, ListTodo, Users, Shield, Send,
  Film, Link2, Image, HelpCircle, Database, MessageSquare
} from 'lucide-react';

// Tool icons mapping
const TOOL_ICONS = {
  // Reasoning tools
  think: Brain,
  plan: ListTodo,

  // Search tools (Private-First)
  search_knowledge_base: Database,
  knowledge_base: Database,
  search_journals: BookOpen,
  search_past_conversations: MessageSquare,
  web_search: Globe,

  // Delegation & verification
  delegate: Users,
  verify_response: Shield,
  finalize_response: Send,

  // Learning context
  get_learning_context: Lightbulb,
  remember_discovery: Lightbulb,

  // Multimedia tools (NEW)
  create_manim_animation: Film,
  link_preview: Link2,
  display_image: Image,

  // Clarification (NEW)
  request_clarification: HelpCircle,

  default: Search
};

// Tool display names
const TOOL_NAMES = {
  // Reasoning
  think: 'Thinking',
  plan: 'Planning',

  // Search (Private-First)
  search_knowledge_base: 'Searching Your Notes',
  knowledge_base: 'Searching Your Notes',
  search_journals: 'Searching Journals',
  search_past_conversations: 'Checking Past Chats',
  web_search: 'Web Search (Fallback)',

  // Delegation & verification
  delegate: 'Delegating Task',
  verify_response: 'Verifying Response',
  finalize_response: 'Finalizing',

  // Learning context
  get_learning_context: 'Getting Context',
  remember_discovery: 'Recording Discovery',

  // Multimedia (NEW)
  create_manim_animation: 'Creating Animation',
  link_preview: 'Fetching Link Preview',
  display_image: 'Displaying Image',

  // Clarification (NEW)
  request_clarification: 'Asking for Help'
};

// Sub-agent type labels
const SUBAGENT_LABELS = {
  research: 'Research Agent',
  analysis: 'Analysis Agent',
  summary: 'Summary Agent',
  expert: 'Expert Agent',
  fact_check: 'Fact Check Agent'
};

// Single workflow step component
function WorkflowStep({ step, isActive, isComplete, theme }) {
  const themeClasses = theme?.classes || {};
  const Icon = TOOL_ICONS[step.tool] || TOOL_ICONS.default;
  const displayName = TOOL_NAMES[step.tool] || step.tool;

  // Check if this is a search tool to show result count
  const isSearchTool = ['search_knowledge_base', 'web_search', 'search_journals', 'search_past_conversations'].includes(step.tool);
  const hasResults = step.result?.results_count > 0 || step.result?.sources?.length > 0;

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all ${
      isActive
        ? `${themeClasses.bgSecondary || 'bg-blue-50'} border ${themeClasses.border || 'border-blue-200'} ${themeClasses.textPrimary || 'text-blue-700'}`
        : isComplete
          ? isSearchTool && !hasResults
            ? 'bg-amber-50 border border-amber-200 text-amber-700'
            : 'bg-green-50 border border-green-200 text-green-700'
          : `${themeClasses.bgSecondary || 'bg-gray-50'} border ${themeClasses.border || 'border-gray-200'} ${themeClasses.textMuted || 'text-gray-600'}`
    }`}>
      <div className="flex-shrink-0">
        {isActive ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : isComplete ? (
          isSearchTool && !hasResults ? (
            <AlertCircle className="w-4 h-4" />
          ) : (
            <CheckCircle className="w-4 h-4" />
          )
        ) : (
          <Icon className="w-4 h-4" />
        )}
      </div>
      <span className="truncate">{displayName}</span>

      {/* Show result count for search tools */}
      {isComplete && isSearchTool && (
        <span className="text-xs opacity-75">
          ({step.result?.results_count || 0} results)
        </span>
      )}

      {step.args?.agent_type && (
        <span className="text-xs opacity-75">
          ({SUBAGENT_LABELS[step.args.agent_type] || step.args.agent_type})
        </span>
      )}
    </div>
  );
}

// Thinking bubble component
function ThinkingBubble({ thought, confidence, theme }) {
  const themeClasses = theme?.classes || {};

  return (
    <div className={`flex items-start gap-2 px-3 py-2 rounded-lg text-sm border
                     ${themeClasses.bgTertiary || 'bg-purple-50'}
                     ${themeClasses.border || 'border-purple-200'}`}>
      <Brain className={`w-4 h-4 flex-shrink-0 mt-0.5 ${themeClasses.textPrimary || 'text-purple-600'}`} />
      <div className="flex-1 min-w-0">
        <p className={`italic ${themeClasses.text || 'text-purple-800'}`}>{thought}</p>
        {confidence !== undefined && (
          <div className="flex items-center gap-2 mt-1">
            <div className={`flex-1 h-1.5 rounded-full overflow-hidden ${themeClasses.bgSecondary || 'bg-purple-200'}`}>
              <div
                className={`h-full rounded-full transition-all ${themeClasses.bgPrimary || 'bg-purple-500'}`}
                style={{ width: `${(confidence * 100).toFixed(0)}%` }}
              />
            </div>
            <span className={`text-xs ${themeClasses.textMuted || 'text-purple-600'}`}>
              {(confidence * 100).toFixed(0)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// Plan display component
function PlanDisplay({ goal, steps, currentStep, theme }) {
  const themeClasses = theme?.classes || {};

  return (
    <div className={`px-3 py-2 rounded-lg text-sm border
                     ${themeClasses.bgTertiary || 'bg-amber-50'}
                     ${themeClasses.border || 'border-amber-200'}`}>
      <div className="flex items-center gap-2 mb-2">
        <ListTodo className={`w-4 h-4 ${themeClasses.textPrimary || 'text-amber-600'}`} />
        <span className={`font-medium ${themeClasses.text || 'text-amber-800'}`}>Plan: {goal}</span>
      </div>
      <div className="space-y-1 pl-6">
        {steps.map((step, idx) => (
          <div key={idx} className={`flex items-center gap-2 ${
            idx < currentStep ? 'text-green-600' :
            idx === currentStep ? `${themeClasses.textPrimary || 'text-amber-700'} font-medium` :
            `${themeClasses.textMuted || 'text-gray-500'}`
          }`}>
            <span className="w-4 text-center">
              {idx < currentStep ? '✓' : idx === currentStep ? '→' : `${idx + 1}.`}
            </span>
            <span className="truncate">{step}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Verification result component
function VerificationResult({ result, issues, suggestions, theme }) {
  const themeClasses = theme?.classes || {};
  const isApproved = result === 'approved';

  return (
    <div className={`px-3 py-2 rounded-lg text-sm border ${
      isApproved
        ? 'bg-green-50 border-green-200'
        : 'bg-yellow-50 border-yellow-200'
    }`}>
      <div className="flex items-center gap-2 mb-1">
        {isApproved ? (
          <CheckCircle className="w-4 h-4 text-green-600" />
        ) : (
          <AlertCircle className="w-4 h-4 text-yellow-600" />
        )}
        <span className={`font-medium ${isApproved ? 'text-green-700' : 'text-yellow-700'}`}>
          {isApproved ? 'Response Verified' : 'Revision Needed'}
        </span>
      </div>
      {!isApproved && issues && issues.length > 0 && (
        <ul className="list-disc list-inside text-yellow-700 text-xs mt-1">
          {issues.slice(0, 3).map((issue, idx) => (
            <li key={idx}>{issue}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

// Search Trail Summary component
function SearchTrailSummary({ searchTrail, theme }) {
  const themeClasses = theme?.classes || {};

  if (!searchTrail?.attempts?.length) return null;

  const attempts = searchTrail.attempts;
  const hasAnyResults = attempts.some(a => a.had_results || a.results_count > 0);

  return (
    <div className={`flex flex-wrap items-center gap-2 px-3 py-2 rounded-lg text-xs border
                     ${themeClasses.bgSecondary || 'bg-gray-50'}
                     ${themeClasses.border || 'border-gray-200'}`}>
      <span className={`font-medium ${themeClasses.textMuted || 'text-gray-500'}`}>
        <Search className="w-3 h-3 inline mr-1" />
        Sources:
      </span>
      {attempts.map((attempt, idx) => {
        const hasResults = attempt.had_results || attempt.results_count > 0;
        const Icon = TOOL_ICONS[attempt.source] || Database;
        const label = TOOL_NAMES[attempt.source] || attempt.source.replace(/_/g, ' ');

        return (
          <span
            key={idx}
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full
                        ${hasResults
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-500'
                        }`}
          >
            <Icon className="w-3 h-3" />
            <span>{attempt.results_count || 0}</span>
          </span>
        );
      })}
      {!hasAnyResults && (
        <span className="text-amber-600 ml-1">No results found</span>
      )}
    </div>
  );
}

// Main Agentic Workflow component
export default function AgenticWorkflow({
  steps = [],
  activeStep = null,
  thinking = null,
  plan = null,
  verification = null,
  searchTrail = null,
  isComplete = false,
  showDetails = false,
  theme
}) {
  const themeClasses = theme?.classes || {};
  const [expanded, setExpanded] = useState(showDetails);

  // Count completed steps
  const completedCount = steps.filter(s => s.complete).length;
  const hasActivity = steps.length > 0 || thinking || plan || verification || searchTrail;

  if (!hasActivity && !isComplete) return null;

  return (
    <div className="mb-3 animate-fade-in">
      {/* Compact view - shows progress bar and current action */}
      <div
        className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors
                    ${themeClasses.bgSecondary || 'bg-gray-50'}
                    border ${themeClasses.border || 'border-gray-200'}
                    hover:opacity-90`}
        onClick={() => setExpanded(!expanded)}
      >
        {!isComplete ? (
          <Loader2 className={`w-4 h-4 animate-spin ${themeClasses.textPrimary || 'text-blue-500'}`} />
        ) : (
          <CheckCircle className="w-4 h-4 text-green-500" />
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-sm ${themeClasses.text || 'text-gray-700'}`}>
              {isComplete
                ? 'Response ready'
                : activeStep
                  ? TOOL_NAMES[activeStep.tool] || activeStep.tool
                  : 'Processing...'}
            </span>
            {steps.length > 0 && (
              <span className={`text-xs ${themeClasses.textMuted || 'text-gray-500'}`}>
                ({completedCount}/{steps.length} steps)
              </span>
            )}
          </div>

          {/* Mini progress bar */}
          {steps.length > 0 && (
            <div className={`h-1 mt-1 rounded-full overflow-hidden ${themeClasses.bgTertiary || 'bg-gray-200'}`}>
              <div
                className={`h-full rounded-full transition-all ${themeClasses.bgPrimary || 'bg-blue-500'}`}
                style={{ width: `${(completedCount / steps.length) * 100}%` }}
              />
            </div>
          )}
        </div>

        <span className={`text-xs ${themeClasses.textMuted || 'text-gray-400'}`}>
          {expanded ? '▲' : '▼'}
        </span>
      </div>

      {/* Expanded view - shows all details */}
      {expanded && (
        <div className={`mt-2 space-y-2 pl-2 border-l-2 ${themeClasses.border || 'border-gray-200'}`}>
          {/* Thinking */}
          {thinking && (
            <ThinkingBubble thought={thinking.thought} confidence={thinking.confidence} theme={theme} />
          )}

          {/* Plan */}
          {plan && plan.goal && (
            <PlanDisplay
              goal={plan.goal}
              steps={plan.steps || []}
              currentStep={plan.currentStep || 0}
              theme={theme}
            />
          )}

          {/* Tool steps */}
          {steps.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {steps.map((step, idx) => (
                <WorkflowStep
                  key={idx}
                  step={step}
                  isActive={activeStep?.tool === step.tool && !step.complete}
                  isComplete={step.complete}
                  theme={theme}
                />
              ))}
            </div>
          )}

          {/* Search Trail */}
          {searchTrail && (
            <SearchTrailSummary searchTrail={searchTrail} theme={theme} />
          )}

          {/* Verification */}
          {verification && (
            <VerificationResult
              result={verification.result}
              issues={verification.issues}
              suggestions={verification.suggestions}
              theme={theme}
            />
          )}
        </div>
      )}
    </div>
  );
}

// Hook for managing agentic workflow state
export function useAgenticWorkflow() {
  const [workflowState, setWorkflowState] = useState({
    steps: [],
    activeStep: null,
    thinking: null,
    plan: null,
    verification: null,
    searchTrail: null,
    isComplete: false
  });

  const resetWorkflow = () => {
    setWorkflowState({
      steps: [],
      activeStep: null,
      thinking: null,
      plan: null,
      verification: null,
      searchTrail: null,
      isComplete: false
    });
  };

  const handleToolStart = (tool, args) => {
    setWorkflowState(prev => ({
      ...prev,
      steps: [...prev.steps, { tool, args, complete: false }],
      activeStep: { tool, args }
    }));
  };

  const handleToolEnd = (tool, result) => {
    setWorkflowState(prev => ({
      ...prev,
      steps: prev.steps.map(s =>
        s.tool === tool && !s.complete
          ? { ...s, complete: true, result }
          : s
      ),
      activeStep: null
    }));

    // Handle special tools
    if (tool === 'think' && result?.thought) {
      setWorkflowState(prev => ({
        ...prev,
        thinking: {
          thought: result.thought,
          confidence: result.confidence
        }
      }));
    }

    if (tool === 'plan' && result?.plan_created) {
      setWorkflowState(prev => ({
        ...prev,
        plan: {
          goal: result.goal,
          steps: result.steps,
          currentStep: result.current_step
        }
      }));
    }

    if (tool === 'verify_response') {
      setWorkflowState(prev => ({
        ...prev,
        verification: {
          result: result.result,
          issues: result.issues,
          suggestions: result.suggestions
        }
      }));
    }

    // Track search attempts in search trail
    const searchTools = ['search_knowledge_base', 'web_search', 'search_journals', 'search_past_conversations'];
    if (searchTools.includes(tool)) {
      setWorkflowState(prev => {
        const currentTrail = prev.searchTrail || { attempts: [] };
        return {
          ...prev,
          searchTrail: {
            attempts: [
              ...currentTrail.attempts,
              {
                source: tool,
                query: result?.query || '',
                results_count: result?.results_count || result?.sources?.length || 0,
                had_results: (result?.results_count || result?.sources?.length || 0) > 0
              }
            ]
          }
        };
      });
    }
  };

  const handleComplete = () => {
    setWorkflowState(prev => ({
      ...prev,
      isComplete: true,
      activeStep: null
    }));
  };

  // Update search trail from response data
  const updateSearchTrail = (trail) => {
    setWorkflowState(prev => ({
      ...prev,
      searchTrail: trail
    }));
  };

  return {
    workflowState,
    resetWorkflow,
    handleToolStart,
    handleToolEnd,
    handleComplete,
    updateSearchTrail
  };
}
