"""
Sub-Agent Orchestrator
Implements the sub-agent delegation pattern for complex task handling.

The orchestrator decides when to delegate tasks to specialized sub-agents:
- Research Agent: Deep knowledge retrieval and exploration
- Analysis Agent: Complex reasoning and analysis
- Summary Agent: Synthesis and summarization
- Expert Agent: Subject-matter expertise
- Fact Check Agent: Verification of facts

Architecture:
1. Main agent determines if task needs delegation
2. Orchestrator spawns appropriate sub-agent(s)
3. Sub-agents complete their specialized tasks
4. Results are aggregated back to main agent
"""

import json
import logging
import asyncio
from typing import Optional, List, Dict, Any, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum

from .state import (
    SubAgentType,
    SubAgentResult,
    Scratchpad,
    AgentPhase,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Sub-Agent Configurations
# =============================================================================

@dataclass
class SubAgentConfig:
    """Configuration for a sub-agent type"""
    agent_type: SubAgentType
    system_prompt: str
    max_iterations: int = 3
    tools_allowed: List[str] = None
    temperature: float = 0.7
    requires_verification: bool = False

    def __post_init__(self):
        if self.tools_allowed is None:
            self.tools_allowed = []


SUBAGENT_CONFIGS: Dict[SubAgentType, SubAgentConfig] = {
    SubAgentType.RESEARCH: SubAgentConfig(
        agent_type=SubAgentType.RESEARCH,
        system_prompt="""You are a Research Sub-Agent specialized in deep knowledge retrieval.

Your task is to thoroughly research a topic using available tools:
- Search the knowledge base for relevant information
- Search past conversations for context
- Use web search for current information

INSTRUCTIONS:
1. Break down the research task into specific queries
2. Execute multiple searches to gather comprehensive information
3. Synthesize findings into a clear, structured response
4. Cite all sources with their identifiers
5. Note any gaps in information

Return your findings in a structured format with:
- Key findings (bulleted)
- Supporting evidence (with citations)
- Information gaps (if any)
- Confidence level (0-1)""",
        max_iterations=4,
        tools_allowed=["search_knowledge_base", "search_journals", "search_past_conversations", "web_search"],
        temperature=0.5
    ),

    SubAgentType.ANALYSIS: SubAgentConfig(
        agent_type=SubAgentType.ANALYSIS,
        system_prompt="""You are an Analysis Sub-Agent specialized in complex reasoning.

Your task is to analyze information and provide deep insights:
- Break down complex problems into components
- Identify patterns and relationships
- Draw logical conclusions
- Consider multiple perspectives

INSTRUCTIONS:
1. Clearly state the problem being analyzed
2. List all relevant factors and considerations
3. Apply logical reasoning step by step
4. Present your analysis with clear explanations
5. Provide actionable conclusions

Return your analysis in a structured format with:
- Problem statement
- Key factors considered
- Analysis steps
- Conclusions
- Confidence level (0-1)""",
        max_iterations=3,
        tools_allowed=["get_learning_context"],
        temperature=0.6
    ),

    SubAgentType.SUMMARY: SubAgentConfig(
        agent_type=SubAgentType.SUMMARY,
        system_prompt="""You are a Summary Sub-Agent specialized in synthesis and summarization.

Your task is to synthesize information into clear, concise summaries:
- Distill key points from complex content
- Organize information logically
- Highlight the most important takeaways
- Create accessible explanations

INSTRUCTIONS:
1. Identify the main themes and key points
2. Organize information hierarchically
3. Remove redundancy while preserving meaning
4. Use clear, simple language
5. Ensure completeness of essential information

Return your summary in a structured format with:
- Executive summary (2-3 sentences)
- Key points (bulleted)
- Supporting details
- Recommendations (if applicable)""",
        max_iterations=2,
        tools_allowed=[],
        temperature=0.5
    ),

    SubAgentType.EXPERT: SubAgentConfig(
        agent_type=SubAgentType.EXPERT,
        system_prompt="""You are an Expert Sub-Agent with deep subject-matter knowledge.

Your task is to provide authoritative expertise on the given subject:
- Apply domain-specific knowledge
- Explain concepts at the appropriate level
- Connect ideas to broader frameworks
- Provide examples and analogies

INSTRUCTIONS:
1. Assess the user's current understanding level
2. Explain concepts clearly and accurately
3. Use relevant examples and analogies
4. Connect to related concepts
5. Suggest next steps for learning

Return your expert response with:
- Core explanation
- Examples and analogies
- Connections to related concepts
- Follow-up suggestions""",
        max_iterations=2,
        tools_allowed=["search_knowledge_base", "get_learning_context"],
        temperature=0.7
    ),

    SubAgentType.FACT_CHECK: SubAgentConfig(
        agent_type=SubAgentType.FACT_CHECK,
        system_prompt="""You are a Fact-Check Sub-Agent specialized in verification.

Your task is to verify the accuracy of information:
- Cross-reference claims with sources
- Identify unsupported statements
- Flag potential inaccuracies
- Provide correct information when errors found

INSTRUCTIONS:
1. Identify specific claims to verify
2. Search for supporting evidence
3. Compare against authoritative sources
4. Note any discrepancies or errors
5. Provide corrections if needed

Return your verification in a structured format with:
- Claims verified (list)
- Verification status for each
- Sources used
- Corrections needed
- Overall accuracy score (0-1)""",
        max_iterations=3,
        tools_allowed=["search_knowledge_base", "web_search"],
        temperature=0.3,
        requires_verification=False
    ),
}


# =============================================================================
# Delegation Decision
# =============================================================================

@dataclass
class DelegationDecision:
    """Decision on whether to delegate and to which sub-agent"""
    should_delegate: bool
    agent_type: Optional[SubAgentType] = None
    task_description: str = ""
    reasoning: str = ""
    priority: int = 1  # 1 = normal, 2 = high, 3 = critical


class DelegationCriteria:
    """Criteria for delegation decisions"""

    @staticmethod
    def should_delegate_research(query: str, context: Dict[str, Any]) -> bool:
        """Determine if research delegation is needed"""
        research_triggers = [
            "find information about",
            "search for",
            "look up",
            "what do my notes say",
            "what did we discuss",
            "in-depth",
            "comprehensive",
            "detailed research",
        ]
        query_lower = query.lower()
        return any(trigger in query_lower for trigger in research_triggers)

    @staticmethod
    def should_delegate_analysis(query: str, context: Dict[str, Any]) -> bool:
        """Determine if analysis delegation is needed"""
        analysis_triggers = [
            "analyze",
            "compare",
            "contrast",
            "evaluate",
            "assess",
            "break down",
            "explain the relationship",
            "pros and cons",
            "advantages and disadvantages",
        ]
        query_lower = query.lower()
        return any(trigger in query_lower for trigger in analysis_triggers)

    @staticmethod
    def should_delegate_summary(query: str, context: Dict[str, Any]) -> bool:
        """Determine if summary delegation is needed"""
        summary_triggers = [
            "summarize",
            "summary",
            "recap",
            "overview",
            "key points",
            "main ideas",
            "tldr",
            "in brief",
        ]
        query_lower = query.lower()
        return any(trigger in query_lower for trigger in summary_triggers)

    @staticmethod
    def is_complex_query(query: str, context: Dict[str, Any]) -> bool:
        """Determine if query is complex enough to warrant delegation"""
        # Complex if: long query, multiple questions, or technical terms
        word_count = len(query.split())
        has_multiple_questions = query.count("?") > 1

        complexity_indicators = [
            word_count > 30,
            has_multiple_questions,
            "step by step" in query.lower(),
            "explain how" in query.lower(),
            "explain why" in query.lower(),
        ]
        return sum(complexity_indicators) >= 2


def decide_delegation(
    query: str,
    context: Dict[str, Any],
    scratchpad: Scratchpad
) -> DelegationDecision:
    """
    Decide if and how to delegate the current task.

    Args:
        query: The user's query
        context: Current context including RAG, learning state, etc.
        scratchpad: Current reasoning scratchpad

    Returns:
        DelegationDecision with recommended action
    """
    # Check if scratchpad already indicates need for delegation
    if scratchpad.should_delegate and scratchpad.delegation_reason:
        agent_type = _infer_agent_type(scratchpad.delegation_reason)
        return DelegationDecision(
            should_delegate=True,
            agent_type=agent_type,
            task_description=scratchpad.delegation_reason,
            reasoning="Delegation indicated by reasoning process"
        )

    # Check specific delegation criteria
    if DelegationCriteria.should_delegate_research(query, context):
        return DelegationDecision(
            should_delegate=True,
            agent_type=SubAgentType.RESEARCH,
            task_description=f"Research: {query}",
            reasoning="Query requires comprehensive research"
        )

    if DelegationCriteria.should_delegate_analysis(query, context):
        return DelegationDecision(
            should_delegate=True,
            agent_type=SubAgentType.ANALYSIS,
            task_description=f"Analyze: {query}",
            reasoning="Query requires deep analysis"
        )

    if DelegationCriteria.should_delegate_summary(query, context):
        return DelegationDecision(
            should_delegate=True,
            agent_type=SubAgentType.SUMMARY,
            task_description=f"Summarize: {query}",
            reasoning="Query requires synthesis/summarization"
        )

    # Check for complex queries
    if DelegationCriteria.is_complex_query(query, context):
        return DelegationDecision(
            should_delegate=True,
            agent_type=SubAgentType.EXPERT,
            task_description=f"Expert assistance: {query}",
            reasoning="Query is complex and requires expert handling",
            priority=2
        )

    # No delegation needed
    return DelegationDecision(
        should_delegate=False,
        reasoning="Query can be handled by main agent"
    )


def _infer_agent_type(reason: str) -> SubAgentType:
    """Infer the appropriate sub-agent type from a delegation reason"""
    reason_lower = reason.lower()

    if any(word in reason_lower for word in ["research", "search", "find", "look up"]):
        return SubAgentType.RESEARCH
    elif any(word in reason_lower for word in ["analyze", "compare", "evaluate"]):
        return SubAgentType.ANALYSIS
    elif any(word in reason_lower for word in ["summarize", "recap", "overview"]):
        return SubAgentType.SUMMARY
    elif any(word in reason_lower for word in ["verify", "fact", "check", "accurate"]):
        return SubAgentType.FACT_CHECK
    else:
        return SubAgentType.EXPERT


# =============================================================================
# Sub-Agent Executor
# =============================================================================

class SubAgentExecutor:
    """
    Executes sub-agent tasks with their specialized configurations.

    This class manages the lifecycle of sub-agent executions:
    1. Sets up the sub-agent with appropriate config
    2. Runs the sub-agent loop
    3. Collects and returns results
    """

    def __init__(
        self,
        llm_service: Any,
        tool_builder: Any = None,
    ):
        self.llm_service = llm_service
        self.tool_builder = tool_builder

    async def execute(
        self,
        agent_type: SubAgentType,
        task: str,
        context: Dict[str, Any],
        tool_map: Optional[Dict[str, Callable]] = None
    ) -> SubAgentResult:
        """
        Execute a sub-agent task.

        Args:
            agent_type: Type of sub-agent to use
            task: Task description for the sub-agent
            context: Context to provide to the sub-agent
            tool_map: Map of tool name to function

        Returns:
            SubAgentResult with the sub-agent's output
        """
        config = SUBAGENT_CONFIGS.get(agent_type)
        if not config:
            return SubAgentResult(
                agent_type=agent_type.value,
                task=task,
                result="",
                success=False,
                error=f"Unknown sub-agent type: {agent_type}"
            )

        # Build system prompt with context
        system_prompt = self._build_prompt(config, task, context)

        # Filter tools to only allowed ones
        filtered_tools = {}
        if tool_map and config.tools_allowed:
            filtered_tools = {
                name: func
                for name, func in tool_map.items()
                if name in config.tools_allowed
            }

        # Execute sub-agent loop
        try:
            result = await self._run_subagent_loop(
                config=config,
                system_prompt=system_prompt,
                task=task,
                tool_map=filtered_tools,
                context=context
            )
            return result

        except Exception as e:
            logger.error(f"Sub-agent execution error: {e}")
            return SubAgentResult(
                agent_type=agent_type.value,
                task=task,
                result="",
                success=False,
                error=str(e)
            )

    def _build_prompt(
        self,
        config: SubAgentConfig,
        task: str,
        context: Dict[str, Any]
    ) -> str:
        """Build the complete system prompt for the sub-agent"""
        prompt_parts = [config.system_prompt]

        # Add task
        prompt_parts.append(f"\n\n## YOUR TASK\n{task}")

        # Add context if available
        if context.get("rag_context"):
            rag_xml = context["rag_context"].get("context_xml", "")
            if rag_xml:
                prompt_parts.append(f"\n\n## AVAILABLE CONTEXT\n{rag_xml}")

        if context.get("learning_state"):
            state = context["learning_state"]
            prompt_parts.append(f"\n\n## LEARNING STATE\nTopics: {state.get('topics_discussed', [])}")

        return "\n".join(prompt_parts)

    async def _run_subagent_loop(
        self,
        config: SubAgentConfig,
        system_prompt: str,
        task: str,
        tool_map: Dict[str, Callable],
        context: Dict[str, Any]
    ) -> SubAgentResult:
        """Run the sub-agent's reasoning loop"""
        messages = [{"role": "user", "content": task}]
        iteration = 0
        sources_used = []
        full_response = ""

        while iteration < config.max_iterations:
            iteration += 1

            try:
                if tool_map:
                    # Get tool schemas for allowed tools
                    tool_schemas = self._get_tool_schemas(list(tool_map.keys()))

                    # Call LLM with tools
                    response = await self.llm_service.generate_with_tools(
                        messages=messages,
                        system_prompt=system_prompt,
                        tools=tool_schemas
                    )

                    # Check for tool calls
                    tool_calls = response.get("tool_calls", [])

                    if tool_calls:
                        # Execute tools
                        for call in tool_calls:
                            tool_name = call.get("function", {}).get("name") or call.get("name")

                            if tool_name not in tool_map:
                                continue

                            # Parse arguments
                            args_str = call.get("function", {}).get("arguments") or call.get("arguments", "{}")
                            if isinstance(args_str, str):
                                args = json.loads(args_str)
                            else:
                                args = args_str

                            # Execute
                            result = await tool_map[tool_name](**args)
                            sources_used.append(tool_name)

                            # Add to messages
                            tool_id = call.get("id", f"tool_{iteration}")
                            messages.append({
                                "role": "assistant",
                                "content": response.get("content", ""),
                                "tool_calls": [call]
                            })
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "name": tool_name,
                                "content": json.dumps(result)
                            })

                        continue  # Continue loop for more reasoning

                    else:
                        # No tools, final response
                        full_response = response.get("content", "")
                        break

                else:
                    # No tools, simple generation
                    full_response = await self.llm_service.generate(
                        messages=messages,
                        system_prompt=system_prompt
                    )
                    break

            except Exception as e:
                logger.error(f"Sub-agent iteration {iteration} error: {e}")
                break

        # Calculate confidence based on iterations and sources
        confidence = min(1.0, 0.5 + (0.1 * len(sources_used)) + (0.1 * iteration))

        return SubAgentResult(
            agent_type=config.agent_type.value,
            task=task,
            result=full_response,
            confidence=confidence,
            sources_used=sources_used,
            iteration_count=iteration,
            success=bool(full_response)
        )

    def _get_tool_schemas(self, tool_names: List[str]) -> List[Dict[str, Any]]:
        """Get OpenAI function schemas for specified tools"""
        from .tools import get_tool_by_name
        schemas = []
        for name in tool_names:
            tool = get_tool_by_name(name)
            if tool:
                schemas.append(tool.to_openai_schema())
        return schemas


# =============================================================================
# Orchestrator
# =============================================================================

class SubAgentOrchestrator:
    """
    Main orchestrator for sub-agent delegation.

    Coordinates the execution of sub-agents and aggregates their results.
    """

    def __init__(
        self,
        llm_service: Any,
        tool_builder: Any = None
    ):
        self.llm_service = llm_service
        self.tool_builder = tool_builder
        self.executor = SubAgentExecutor(llm_service, tool_builder)
        self._active_tasks: Dict[str, asyncio.Task] = {}

    async def delegate(
        self,
        decision: DelegationDecision,
        context: Dict[str, Any],
        tool_map: Optional[Dict[str, Callable]] = None
    ) -> SubAgentResult:
        """
        Delegate a task to a sub-agent based on the decision.

        Args:
            decision: Delegation decision with agent type and task
            context: Context to provide to the sub-agent
            tool_map: Available tools

        Returns:
            SubAgentResult from the sub-agent
        """
        if not decision.should_delegate or not decision.agent_type:
            return SubAgentResult(
                agent_type="none",
                task="",
                result="",
                success=False,
                error="No delegation required"
            )

        logger.info(f"Delegating to {decision.agent_type.value}: {decision.task_description}")

        result = await self.executor.execute(
            agent_type=decision.agent_type,
            task=decision.task_description,
            context=context,
            tool_map=tool_map
        )

        return result

    async def delegate_parallel(
        self,
        decisions: List[DelegationDecision],
        context: Dict[str, Any],
        tool_map: Optional[Dict[str, Callable]] = None
    ) -> List[SubAgentResult]:
        """
        Delegate multiple tasks to sub-agents in parallel.

        Args:
            decisions: List of delegation decisions
            context: Context to provide to sub-agents
            tool_map: Available tools

        Returns:
            List of SubAgentResults
        """
        tasks = []
        for decision in decisions:
            if decision.should_delegate and decision.agent_type:
                task = self.delegate(decision, context, tool_map)
                tasks.append(task)

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(SubAgentResult(
                    agent_type=decisions[i].agent_type.value if decisions[i].agent_type else "unknown",
                    task=decisions[i].task_description,
                    result="",
                    success=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)

        return processed_results

    def aggregate_results(
        self,
        results: List[SubAgentResult],
        original_query: str
    ) -> Dict[str, Any]:
        """
        Aggregate results from multiple sub-agents.

        Args:
            results: List of sub-agent results
            original_query: The original user query

        Returns:
            Aggregated result dict
        """
        if not results:
            return {
                "success": False,
                "aggregated_content": "",
                "sources": [],
                "confidence": 0.0
            }

        # Combine successful results
        successful_results = [r for r in results if r.success]

        if not successful_results:
            return {
                "success": False,
                "aggregated_content": "",
                "sources": [],
                "confidence": 0.0,
                "errors": [r.error for r in results if r.error]
            }

        # Aggregate content
        aggregated_parts = []
        all_sources = []
        total_confidence = 0.0

        for result in successful_results:
            agent_label = result.agent_type.upper()
            aggregated_parts.append(f"[{agent_label}]\n{result.result}")
            all_sources.extend(result.sources_used)
            total_confidence += result.confidence

        avg_confidence = total_confidence / len(successful_results)

        return {
            "success": True,
            "aggregated_content": "\n\n".join(aggregated_parts),
            "sources": list(set(all_sources)),
            "confidence": avg_confidence,
            "agent_count": len(successful_results),
            "results": [r.to_dict() for r in successful_results]
        }


# =============================================================================
# Factory Functions
# =============================================================================

_orchestrator_instance: Optional[SubAgentOrchestrator] = None


def create_orchestrator(
    llm_service: Any,
    tool_builder: Any = None
) -> SubAgentOrchestrator:
    """Create or get the orchestrator instance"""
    global _orchestrator_instance

    if _orchestrator_instance is None:
        _orchestrator_instance = SubAgentOrchestrator(
            llm_service=llm_service,
            tool_builder=tool_builder
        )

    return _orchestrator_instance


def get_orchestrator() -> Optional[SubAgentOrchestrator]:
    """Get the current orchestrator instance"""
    return _orchestrator_instance
