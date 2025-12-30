import { useState, useEffect } from 'react';
import {
  Brain, Search, BookOpen, Globe, CheckCircle, AlertCircle,
  Loader2, Lightbulb, ListTodo, Users, Shield, Send
} from 'lucide-react';

// Tool icons mapping
const TOOL_ICONS = {
  think: Brain,
  plan: ListTodo,
  search_knowledge_base: BookOpen,
  search_journals: BookOpen,
  search_past_conversations: BookOpen,
  web_search: Globe,
  delegate: Users,
  verify_response: Shield,
  finalize_response: Send,
  get_learning_context: Lightbulb,
  remember_discovery: Lightbulb,
  default: Search
};

// Tool display names
const TOOL_NAMES = {
  think: 'Thinking',
  plan: 'Planning',
  search_knowledge_base: 'Searching Knowledge',
  search_journals: 'Searching Journals',
  search_past_conversations: 'Checking History',
  web_search: 'Web Search',
  delegate: 'Delegating Task',
  verify_response: 'Verifying Response',
  finalize_response: 'Finalizing',
  get_learning_context: 'Getting Context',
  remember_discovery: 'Recording Discovery'
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
function WorkflowStep({ step, isActive, isComplete }) {
  const Icon = TOOL_ICONS[step.tool] || TOOL_ICONS.default;
  const displayName = TOOL_NAMES[step.tool] || step.tool;

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all ${
      isActive
        ? 'bg-blue-50 border border-blue-200 text-blue-700'
        : isComplete
          ? 'bg-green-50 border border-green-200 text-green-700'
          : 'bg-gray-50 border border-gray-200 text-gray-600'
    }`}>
      <div className="flex-shrink-0">
        {isActive ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : isComplete ? (
          <CheckCircle className="w-4 h-4" />
        ) : (
          <Icon className="w-4 h-4" />
        )}
      </div>
      <span className="truncate">{displayName}</span>
      {step.args?.agent_type && (
        <span className="text-xs opacity-75">
          ({SUBAGENT_LABELS[step.args.agent_type] || step.args.agent_type})
        </span>
      )}
    </div>
  );
}

// Thinking bubble component
function ThinkingBubble({ thought, confidence }) {
  return (
    <div className="flex items-start gap-2 px-3 py-2 bg-purple-50 border border-purple-200 rounded-lg text-sm">
      <Brain className="w-4 h-4 text-purple-600 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-purple-800 italic">{thought}</p>
        {confidence !== undefined && (
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1 h-1.5 bg-purple-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-purple-500 rounded-full transition-all"
                style={{ width: `${(confidence * 100).toFixed(0)}%` }}
              />
            </div>
            <span className="text-xs text-purple-600">{(confidence * 100).toFixed(0)}%</span>
          </div>
        )}
      </div>
    </div>
  );
}

// Plan display component
function PlanDisplay({ goal, steps, currentStep }) {
  return (
    <div className="px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-sm">
      <div className="flex items-center gap-2 mb-2">
        <ListTodo className="w-4 h-4 text-amber-600" />
        <span className="font-medium text-amber-800">Plan: {goal}</span>
      </div>
      <div className="space-y-1 pl-6">
        {steps.map((step, idx) => (
          <div key={idx} className={`flex items-center gap-2 ${
            idx < currentStep ? 'text-green-600' :
            idx === currentStep ? 'text-amber-700 font-medium' :
            'text-gray-500'
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
function VerificationResult({ result, issues, suggestions }) {
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

// Main Agentic Workflow component
export default function AgenticWorkflow({
  steps = [],
  activeStep = null,
  thinking = null,
  plan = null,
  verification = null,
  isComplete = false,
  showDetails = false
}) {
  const [expanded, setExpanded] = useState(showDetails);

  // Count completed steps
  const completedCount = steps.filter(s => s.complete).length;
  const hasActivity = steps.length > 0 || thinking || plan || verification;

  if (!hasActivity && !isComplete) return null;

  return (
    <div className="mb-3 animate-fade-in">
      {/* Compact view - shows progress bar and current action */}
      <div
        className="flex items-center gap-3 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {!isComplete ? (
          <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
        ) : (
          <CheckCircle className="w-4 h-4 text-green-500" />
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-700">
              {isComplete
                ? 'Response ready'
                : activeStep
                  ? TOOL_NAMES[activeStep.tool] || activeStep.tool
                  : 'Processing...'}
            </span>
            {steps.length > 0 && (
              <span className="text-xs text-gray-500">
                ({completedCount}/{steps.length} steps)
              </span>
            )}
          </div>

          {/* Mini progress bar */}
          {steps.length > 0 && (
            <div className="h-1 mt-1 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all"
                style={{ width: `${(completedCount / steps.length) * 100}%` }}
              />
            </div>
          )}
        </div>

        <span className="text-xs text-gray-400">{expanded ? '▲' : '▼'}</span>
      </div>

      {/* Expanded view - shows all details */}
      {expanded && (
        <div className="mt-2 space-y-2 pl-2 border-l-2 border-gray-200">
          {/* Thinking */}
          {thinking && (
            <ThinkingBubble thought={thinking.thought} confidence={thinking.confidence} />
          )}

          {/* Plan */}
          {plan && plan.goal && (
            <PlanDisplay
              goal={plan.goal}
              steps={plan.steps || []}
              currentStep={plan.currentStep || 0}
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
                />
              ))}
            </div>
          )}

          {/* Verification */}
          {verification && (
            <VerificationResult
              result={verification.result}
              issues={verification.issues}
              suggestions={verification.suggestions}
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
    isComplete: false
  });

  const resetWorkflow = () => {
    setWorkflowState({
      steps: [],
      activeStep: null,
      thinking: null,
      plan: null,
      verification: null,
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
  };

  const handleComplete = () => {
    setWorkflowState(prev => ({
      ...prev,
      isComplete: true,
      activeStep: null
    }));
  };

  return {
    workflowState,
    resetWorkflow,
    handleToolStart,
    handleToolEnd,
    handleComplete
  };
}
