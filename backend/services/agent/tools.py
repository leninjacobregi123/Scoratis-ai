"""
Agent Tool Registry
Defines all tools available to the Scoratis agent.

Architecture:
1. ToolDefinition: Blueprint for a tool (name, description, factory)
2. TOOL_REGISTRY: Central list of all available tools
3. build_tools(): Factory function that assembles tools with dependencies
"""

import json
import logging
from typing import Optional, List, Dict, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Categories for organizing tools"""
    KNOWLEDGE = "knowledge"
    SEARCH = "search"
    MEMORY = "memory"
    LEARNING = "learning"
    UTILITY = "utility"


@dataclass
class ToolParameter:
    """Definition of a tool parameter"""
    name: str
    type: str  # string, integer, boolean, array, object
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Any = None


@dataclass
class ToolDefinition:
    """
    Blueprint for an agent tool.

    This is NOT the actual tool implementation - it's a blueprint that describes:
    - What the tool does (for the LLM to understand)
    - What parameters it accepts
    - A factory function to create the actual tool with dependencies injected

    The factory pattern allows us to inject database sessions, services, etc.
    at runtime without the tool definitions knowing about them.
    """
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter]
    factory: Callable[..., Callable[..., Awaitable[Any]]]

    # Optional metadata
    examples: List[str] = field(default_factory=list)
    requires_db: bool = False
    requires_rag: bool = False
    requires_web: bool = False

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling schema"""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


# =============================================================================
# Tool Factory Functions
# These create the actual tool implementations with injected dependencies
# =============================================================================

def create_search_knowledge_base_tool(
    db_session: AsyncSession,
    rag_service: Any,
    user_id: int = 1,
    subject: Optional[str] = None
) -> Callable[..., Awaitable[Dict[str, Any]]]:
    """
    Factory for the knowledge base search tool.
    Searches journals, documents, and past conversations.

    Enhanced with:
    - Subject filtering (subject-isolated knowledge spaces)
    - Query reformulation (automatic query optimization)
    - Cross-encoder re-ranking (improved relevance)
    - Contextual grouping (chunks grouped by document)
    """
    async def search_knowledge_base(
        query: str,
        limit: int = 5,
        use_enhanced: bool = True
    ) -> Dict[str, Any]:
        """
        Search the user's knowledge base for relevant information.

        Args:
            query: Search query
            limit: Maximum results to return
            use_enhanced: Whether to use enhanced RAG pipeline with re-ranking
        """
        try:
            # Ensure limit is an integer
            limit_int = int(limit) if limit else 5

            # Try enhanced search if available
            if use_enhanced and hasattr(rag_service, 'enhanced_search'):
                from services.rag_service import SearchFilters

                filters = SearchFilters(subject=subject)
                results = await rag_service.enhanced_search(
                    db_session,
                    query,
                    user_id,
                    filters=filters,
                    use_query_reformulation=True,
                    use_reranker=True,
                    use_contextual_grouping=True,
                    limit=limit_int * 2  # Get more candidates for re-ranking
                )

                sources = results.get("sources", [])[:limit_int]
                search_info = results.get("search_info", {})

                result = {
                    "success": True,
                    "query": query,
                    "reformulated_query": search_info.get("reformulated_query"),
                    "results_count": len(sources),
                    "reranked": search_info.get("reranked", False),
                    "grouped": search_info.get("grouped", False),
                    "sources": [
                        {
                            "citation_number": s.get("citation_number"),
                            "document_title": s.get("document_title"),
                            "content_preview": str(s.get("content_preview", "") or "")[:300],
                            "source_type": s.get("source_type"),
                            "chunk_id": s.get("chunk_id"),
                            "relevance_score": s.get("rrf_score", 0)
                        }
                        for s in sources
                    ],
                    "context_xml": results.get("context_xml", "")
                }

                # Add explicit NO_RESULTS message if empty
                if len(sources) == 0:
                    result["message"] = "NO_RESULTS: No matching documents found in knowledge base."
                    result["suggestion"] = "Consider using web_search to find public information on this topic."

                return result
            else:
                # Fallback to basic search
                results = await rag_service.get_context_with_citations(
                    db_session, query, user_id, subject=subject
                )

                sources = results.get("sources", [])[:limit_int]

                result = {
                    "success": True,
                    "query": query,
                    "results_count": len(sources),
                    "sources": [
                        {
                            "citation_number": s.get("citation_number"),
                            "document_title": s.get("document_title"),
                            "content_preview": str(s.get("content_preview", "") or "")[:300],
                            "source_type": s.get("source_type"),
                            "chunk_id": s.get("chunk_id")
                        }
                        for s in sources
                    ],
                    "context_xml": results.get("context_xml", "")
                }

                # Add explicit NO_RESULTS message if empty
                if len(sources) == 0:
                    result["message"] = "NO_RESULTS: No matching documents found in knowledge base."
                    result["suggestion"] = "Consider using web_search to find public information on this topic."

                return result

        except Exception as e:
            logger.error(f"Knowledge base search error: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results_count": 0,
                "sources": []
            }

    return search_knowledge_base


def create_search_journals_tool(
    db_session: AsyncSession,
    rag_service: Any,
    user_id: int = 1
) -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for the journal-specific search tool."""
    async def search_journals(query: str, limit: int = 5) -> Dict[str, Any]:
        """Search the user's journal entries for relevant notes."""
        try:
            # Ensure limit is an integer
            limit_int = int(limit) if limit else 5
            results = await rag_service.search_journals(db_session, query, user_id, limit_int)

            return {
                "success": True,
                "query": query,
                "results_count": len(results) if results else 0,
                "journals": [
                    {
                        "title": getattr(r, 'title', ''),
                        "content_preview": str(getattr(r, 'content', '') or '')[:300],
                        "similarity": round(getattr(r, 'similarity', 0.0), 3),
                        "tags": getattr(r, 'metadata', {}).get("tags", []) if hasattr(r, 'metadata') else []
                    }
                    for r in (results or [])
                ]
            }

        except Exception as e:
            logger.error(f"Journal search error: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results_count": 0,
                "journals": []
            }

    return search_journals


def create_search_past_conversations_tool(
    db_session: AsyncSession,
    rag_service: Any,
    current_session_id: str,
    user_id: int = 1
) -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for searching past conversation history."""
    async def search_past_conversations(query: str, limit: int = 5) -> Dict[str, Any]:
        """Search past conversations for relevant discussions."""
        try:
            # Ensure limit is an integer
            limit_int = int(limit) if limit else 5
            results = await rag_service.search_conversations(
                db_session, query,
                exclude_session_id=current_session_id,
                user_id=user_id,
                limit=limit_int
            )

            return {
                "success": True,
                "query": query,
                "results_count": len(results) if results else 0,
                "conversations": [
                    {
                        "content_preview": str(getattr(r, 'content', '') or '')[:300],
                        "sender": getattr(r, 'metadata', {}).get("sender") if hasattr(r, 'metadata') else None,
                        "similarity": round(getattr(r, 'similarity', 0.0), 3),
                        "conversation_title": getattr(r, 'title', '')
                    }
                    for r in (results or [])
                ]
            }

        except Exception as e:
            logger.error(f"Conversation search error: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results_count": 0,
                "conversations": []
            }

    return search_past_conversations


def create_web_search_tool(
    web_search_service: Any
) -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for the web search tool."""
    async def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Search the web for current information.
        Use this when the knowledge base doesn't have the answer
        or when you need up-to-date information.
        """
        try:
            results = await web_search_service.search(query, max_results=max_results)
            results_count = len(results) if results else 0

            result = {
                "success": True,
                "query": query,
                "results_count": results_count,
                "results": results or []
            }

            # Add explicit NO_RESULTS message if empty
            if results_count == 0:
                result["message"] = "NO_RESULTS: No matching results found on the web."
                result["suggestion"] = "Consider asking the user for clarification or more context."

            return result

        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results_count": 0,
                "results": [],
                "message": f"WEB_SEARCH_ERROR: {str(e)}",
                "suggestion": "Consider asking the user for clarification or trying a different query."
            }

    return web_search


def create_get_learning_context_tool(
    langgraph_service: Any,
    session_id: str
) -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for getting the current learning context."""
    async def get_learning_context() -> Dict[str, Any]:
        """
        Get the current learning context for this session.
        Returns topics discussed, learning state, and turn count.
        """
        try:
            context = await langgraph_service.get_session_context(session_id)
            return {
                "success": True,
                **context
            }
        except Exception as e:
            logger.error(f"Learning context error: {e}")
            return {
                "success": False,
                "error": str(e),
                "topics_discussed": [],
                "turn_count": 0,
                "current_topic": None,
                "learning_state": "initial"
            }

    return get_learning_context


def create_analyze_for_video_tool(
    llm_service: Any,
    subject: str
) -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for analyzing content for video generation potential."""
    async def analyze_for_video(
        topic: str,
        explanation: str,
        learning_state: str = "engaged"
    ) -> Dict[str, Any]:
        """
        Analyze if a topic/explanation would benefit from video visualization.
        Returns whether video should be generated and what type.
        """
        # This is a simplified version - the full analysis happens in the graph
        return {
            "success": True,
            "topic": topic,
            "analyzed": True,
            "message": "Video analysis will be performed by the main agent loop"
        }

    return analyze_for_video


def create_remember_discovery_tool(
    langgraph_service: Any,
    session_id: str
) -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for recording key discoveries in the learning journey."""
    async def remember_discovery(discovery: str, topic: str) -> Dict[str, Any]:
        """
        Record a key discovery or insight from the learning session.
        This helps track the student's progress and breakthroughs.
        """
        try:
            # Get current state
            if session_id in langgraph_service._fallback_states:
                state = langgraph_service._fallback_states[session_id]
                learning = state.get("learning_state", {})
                discoveries = learning.get("key_discoveries", [])

                # Add new discovery
                discoveries.append({
                    "discovery": discovery,
                    "topic": topic,
                    "turn": learning.get("turn_count", 0)
                })
                learning["key_discoveries"] = discoveries[-10:]  # Keep last 10
                state["learning_state"] = learning

            return {
                "success": True,
                "recorded": True,
                "discovery": discovery,
                "topic": topic
            }

        except Exception as e:
            logger.error(f"Remember discovery error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    return remember_discovery


# =============================================================================
# Agentic Loop Tools
# =============================================================================

def create_think_tool() -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for the thinking/reasoning tool."""
    async def think(
        thought: str,
        confidence: float = 0.5,
        needs_more_info: bool = False
    ) -> Dict[str, Any]:
        """
        Record a reasoning step in your thought process.
        Use this to think through complex problems step by step.

        Args:
            thought: Your current thought or reasoning step
            confidence: How confident you are (0.0 to 1.0)
            needs_more_info: Whether you need to gather more information

        Returns:
            Acknowledgment of the recorded thought
        """
        return {
            "success": True,
            "thought_recorded": True,
            "thought": thought,
            "confidence": confidence,
            "needs_more_info": needs_more_info,
            "instruction": "Continue reasoning or use other tools to gather information."
        }

    return think


def create_plan_tool() -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for the planning tool."""
    async def plan(
        goal: str,
        steps: List[str],
        current_step: int = 0
    ) -> Dict[str, Any]:
        """
        Create or update an execution plan.
        Use this to organize your approach to complex tasks.

        Args:
            goal: The main goal to achieve
            steps: List of steps to accomplish the goal
            current_step: Index of the current step (0-based)

        Returns:
            Plan status with next step guidance
        """
        return {
            "success": True,
            "plan_created": True,
            "goal": goal,
            "steps": steps,
            "total_steps": len(steps),
            "current_step": current_step,
            "next_step": steps[current_step] if current_step < len(steps) else "All steps complete",
            "instruction": f"Execute step {current_step + 1}: {steps[current_step]}" if current_step < len(steps) else "Plan complete, formulate response."
        }

    return plan


def create_delegate_tool(
    orchestrator: Any
) -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for the sub-agent delegation tool."""
    async def delegate(
        agent_type: str,
        task: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delegate a task to a specialized sub-agent.

        Agent types:
        - research: Deep knowledge retrieval and exploration
        - analysis: Complex reasoning and analysis
        - summary: Synthesis and summarization
        - expert: Subject-matter expertise
        - fact_check: Verify accuracy of information

        Args:
            agent_type: Type of sub-agent to use
            task: The task to delegate
            context: Additional context for the sub-agent

        Returns:
            Result from the sub-agent
        """
        if orchestrator is None:
            return {
                "success": False,
                "error": "Orchestrator not available",
                "agent_type": agent_type,
                "task": task
            }

        try:
            from .orchestrator import DelegationDecision, SubAgentType

            # Map string to enum
            agent_type_map = {
                "research": SubAgentType.RESEARCH,
                "analysis": SubAgentType.ANALYSIS,
                "summary": SubAgentType.SUMMARY,
                "expert": SubAgentType.EXPERT,
                "fact_check": SubAgentType.FACT_CHECK,
            }

            agent_enum = agent_type_map.get(agent_type.lower())
            if not agent_enum:
                return {
                    "success": False,
                    "error": f"Unknown agent type: {agent_type}. Valid types: {list(agent_type_map.keys())}",
                    "agent_type": agent_type,
                    "task": task
                }

            decision = DelegationDecision(
                should_delegate=True,
                agent_type=agent_enum,
                task_description=task,
                reasoning="Explicit delegation request"
            )

            result = await orchestrator.delegate(
                decision=decision,
                context={"additional_context": context} if context else {},
                tool_map=None  # Sub-agent will build its own tools
            )

            return {
                "success": result.success,
                "agent_type": result.agent_type,
                "task": task,
                "result": result.result,
                "confidence": result.confidence,
                "sources_used": result.sources_used,
                "error": result.error
            }

        except Exception as e:
            logger.error(f"Delegation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent_type": agent_type,
                "task": task
            }

    return delegate


def create_verify_response_tool(
    verifier: Any
) -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for the response verification tool."""
    async def verify_response(
        response: str,
        query: str,
        check_facts: bool = True
    ) -> Dict[str, Any]:
        """
        Verify the quality of a response before finalizing.

        Args:
            response: The response to verify
            query: The original user query
            check_facts: Whether to check factual accuracy

        Returns:
            Verification result with feedback
        """
        if verifier is None:
            # Fallback to quick verification
            from .verifier import get_quick_verifier
            quick = get_quick_verifier()
            result = quick.quick_check(query, response)
            return {
                "success": True,
                "verified": True,
                "result": result.result,
                "score": result.confidence_score,
                "issues": result.issues,
                "suggestions": result.suggestions,
                "mode": "quick"
            }

        try:
            result = await verifier.verify(
                user_query=query,
                response=response,
                sources=[],  # Will be injected by graph if available
                context={}
            )

            return {
                "success": True,
                "verified": result.verified,
                "result": result.result,
                "score": result.confidence_score,
                "feedback": result.feedback,
                "issues": result.issues,
                "suggestions": result.suggestions,
                "mode": "full"
            }

        except Exception as e:
            logger.error(f"Verification error: {e}")
            return {
                "success": False,
                "error": str(e),
                "verified": False
            }

    return verify_response


def create_request_clarification_tool() -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for the clarification request tool."""
    async def request_clarification(
        reason: str,
        suggestions: List[str] = None,
        search_trail: List[str] = None
    ) -> Dict[str, Any]:
        """
        Request clarification from the user when you cannot find information.

        Use this when:
        - Both knowledge base AND web search returned no results
        - The query is ambiguous and needs more context
        - You're uncertain how to proceed

        Args:
            reason: Why you need clarification
            suggestions: Suggested ways to rephrase or clarify
            search_trail: List of sources that were searched

        Returns:
            Clarification request formatted for user
        """
        return {
            "success": True,
            "action": "clarification_requested",
            "reason": reason,
            "suggestions": suggestions or [],
            "search_trail": search_trail or [],
            "instruction": "Ask the user to clarify or provide more context."
        }

    return request_clarification


def create_finalize_response_tool() -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for the response finalization tool."""
    async def finalize_response(
        response: str,
        confidence: float = 0.8,
        verification_passed: bool = True
    ) -> Dict[str, Any]:
        """
        Mark a response as final and ready to deliver.

        Use this when you're confident your response is complete and accurate.

        Args:
            response: The final response text
            confidence: Your confidence level (0.0 to 1.0)
            verification_passed: Whether verification was passed

        Returns:
            Finalization confirmation
        """
        return {
            "success": True,
            "finalized": True,
            "response": response,
            "confidence": confidence,
            "verification_passed": verification_passed,
            "instruction": "Response has been finalized. Deliver to user."
        }

    return finalize_response


# =============================================================================
# Multimedia Tools (Manim, Links, Images)
# =============================================================================

def create_manim_animation_tool(
    animation_service: Any = None
) -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for the Manim animation creation tool."""
    async def create_manim_animation(
        manim_code: str,
        title: str,
        description: str = "",
        quality: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate a mathematical animation using Manim library.

        Use this to create explanatory visualizations for:
        - Mathematical concepts (graphs, functions, transformations)
        - Physics simulations (motion, waves, fields)
        - Geometric proofs and constructions
        - Algorithm visualizations

        Args:
            manim_code: Python code using Manim library (must define a Scene class)
            title: Title for the animation
            description: Brief description of what the animation shows
            quality: Video quality - "low", "medium", "high" (default: medium)

        Returns:
            Dict with animation URL or generation status
        """
        try:
            if animation_service:
                # Use the actual animation service if available
                result = await animation_service.create_animation(
                    code=manim_code,
                    title=title,
                    description=description,
                    quality=quality
                )
                return {
                    "success": True,
                    "animation_id": result.get("id"),
                    "video_url": result.get("video_url"),
                    "thumbnail_url": result.get("thumbnail_url"),
                    "title": title,
                    "description": description,
                    "status": "completed"
                }
            else:
                # Return pending status for async processing
                import hashlib
                animation_id = hashlib.md5(manim_code.encode()).hexdigest()[:12]
                return {
                    "success": True,
                    "animation_id": animation_id,
                    "manim_code": manim_code,
                    "title": title,
                    "description": description,
                    "quality": quality,
                    "status": "queued",
                    "message": "Animation queued for rendering. Will be available shortly."
                }

        except Exception as e:
            logger.error(f"Manim animation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "title": title,
                "status": "failed"
            }

    return create_manim_animation


def create_link_preview_tool(
    preview_service: Any = None
) -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for the link preview tool."""
    async def link_preview(
        url: str,
        include_screenshot: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a rich preview card for a URL.

        Automatically use this when:
        - A URL is mentioned in the conversation
        - Providing reference links to the student
        - Sharing educational resources

        Args:
            url: The URL to preview
            include_screenshot: Whether to include a page screenshot

        Returns:
            Rich preview data including title, description, image
        """
        try:
            import aiohttp
            from urllib.parse import urlparse

            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return {
                    "success": False,
                    "error": "Invalid URL format",
                    "url": url
                }

            if preview_service:
                # Use actual preview service if available
                result = await preview_service.get_preview(url, include_screenshot)
                return {
                    "success": True,
                    "url": url,
                    "title": result.get("title"),
                    "description": result.get("description"),
                    "image_url": result.get("image"),
                    "favicon_url": result.get("favicon"),
                    "domain": parsed.netloc,
                    "screenshot_url": result.get("screenshot") if include_screenshot else None
                }
            else:
                # Fallback: basic URL metadata extraction
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            html = await response.text()

                            # Extract basic metadata
                            title = ""
                            description = ""
                            image = ""

                            # Simple regex extraction (fallback)
                            import re
                            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
                            if title_match:
                                title = title_match.group(1).strip()

                            og_title = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                            if og_title:
                                title = og_title.group(1).strip()

                            og_desc = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                            if og_desc:
                                description = og_desc.group(1).strip()

                            og_image = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                            if og_image:
                                image = og_image.group(1).strip()

                            return {
                                "success": True,
                                "url": url,
                                "title": title or parsed.netloc,
                                "description": description[:200] if description else "",
                                "image_url": image,
                                "domain": parsed.netloc,
                                "favicon_url": f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"HTTP {response.status}",
                                "url": url,
                                "domain": parsed.netloc
                            }

        except Exception as e:
            logger.error(f"Link preview error: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    return link_preview


def create_display_image_tool(
    image_service: Any = None
) -> Callable[..., Awaitable[Dict[str, Any]]]:
    """Factory for the image display tool."""
    async def display_image(
        image_url: str,
        alt_text: str = "",
        caption: str = "",
        size: str = "medium"
    ) -> Dict[str, Any]:
        """
        Display an image directly in the chat interface.

        Use this when:
        - You find a relevant diagram or visualization during research
        - The student would benefit from seeing an image
        - Explaining concepts that have useful visual representations

        Args:
            image_url: URL of the image to display
            alt_text: Accessibility text describing the image
            caption: Caption to display below the image
            size: Display size - "small", "medium", "large" (default: medium)

        Returns:
            Image display configuration for the frontend
        """
        try:
            import aiohttp
            from urllib.parse import urlparse

            # Validate URL
            parsed = urlparse(image_url)
            if not parsed.scheme or not parsed.netloc:
                return {
                    "success": False,
                    "error": "Invalid image URL format",
                    "image_url": image_url
                }

            # Validate it's actually an image (check content-type)
            valid_image = False
            content_type = None

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(image_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        content_type = response.headers.get("content-type", "")
                        valid_image = any(t in content_type.lower() for t in ["image/", "png", "jpg", "jpeg", "gif", "webp", "svg"])
            except:
                # If HEAD fails, assume it might still be valid
                valid_image = any(ext in image_url.lower() for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"])

            if not valid_image and content_type:
                return {
                    "success": False,
                    "error": f"URL does not appear to be an image (content-type: {content_type})",
                    "image_url": image_url
                }

            # Map size to dimensions
            size_map = {
                "small": {"max_width": 300, "max_height": 200},
                "medium": {"max_width": 500, "max_height": 400},
                "large": {"max_width": 800, "max_height": 600}
            }
            dimensions = size_map.get(size, size_map["medium"])

            return {
                "success": True,
                "type": "image_display",
                "image_url": image_url,
                "alt_text": alt_text or "Educational image",
                "caption": caption,
                "size": size,
                "dimensions": dimensions,
                "instruction": "Display this image in the chat interface"
            }

        except Exception as e:
            logger.error(f"Display image error: {e}")
            return {
                "success": False,
                "error": str(e),
                "image_url": image_url
            }

    return display_image


# =============================================================================
# Tool Registry
# Central registry of all available tools
# =============================================================================

class AgenticToolCategory(str, Enum):
    """Categories for agentic tools"""
    REASONING = "reasoning"
    DELEGATION = "delegation"
    VERIFICATION = "verification"


TOOL_REGISTRY: List[ToolDefinition] = [
    # === Agentic Loop Tools ===
    ToolDefinition(
        name="think",
        description="""Record a reasoning step in your thought process.
Use this to think through complex problems step by step.
Helps maintain a chain of thought across multiple iterations.

Use when:
- Breaking down a complex problem
- Reasoning through multiple considerations
- Documenting your thought process""",
        category=ToolCategory.UTILITY,
        parameters=[
            ToolParameter(
                name="thought",
                type="string",
                description="Your current thought or reasoning step",
                required=True
            ),
            ToolParameter(
                name="confidence",
                type="number",
                description="How confident you are (0.0 to 1.0)",
                required=False,
                default=0.5
            ),
            ToolParameter(
                name="needs_more_info",
                type="boolean",
                description="Whether you need to gather more information",
                required=False,
                default=False
            )
        ],
        factory=create_think_tool,
        examples=[
            "think(thought='The user is asking about quantum entanglement. I should first check their notes.', confidence=0.7)",
            "think(thought='I need more context about their background knowledge.', needs_more_info=True)"
        ]
    ),

    ToolDefinition(
        name="plan",
        description="""Create or update an execution plan for complex tasks.
Use this to organize your approach before diving into a problem.

Use when:
- Tackling a multi-step problem
- The task requires multiple tool uses
- You need to organize your approach""",
        category=ToolCategory.UTILITY,
        parameters=[
            ToolParameter(
                name="goal",
                type="string",
                description="The main goal to achieve",
                required=True
            ),
            ToolParameter(
                name="steps",
                type="array",
                description="List of steps to accomplish the goal",
                required=True
            ),
            ToolParameter(
                name="current_step",
                type="integer",
                description="Index of the current step (0-based)",
                required=False,
                default=0
            )
        ],
        factory=create_plan_tool,
        examples=[
            "plan(goal='Explain photosynthesis', steps=['Search knowledge base', 'Check learning context', 'Build explanation with analogies'])"
        ]
    ),

    ToolDefinition(
        name="delegate",
        description="""Delegate a task to a specialized sub-agent for better results.

Sub-agent types:
- research: Deep knowledge retrieval and exploration
- analysis: Complex reasoning and analysis
- summary: Synthesis and summarization
- expert: Subject-matter expertise
- fact_check: Verify accuracy of information

Use when:
- The task is complex and specialized
- You need deep research or analysis
- The query requires expert knowledge""",
        category=ToolCategory.UTILITY,
        parameters=[
            ToolParameter(
                name="agent_type",
                type="string",
                description="Type of sub-agent: research, analysis, summary, expert, fact_check",
                required=True,
                enum=["research", "analysis", "summary", "expert", "fact_check"]
            ),
            ToolParameter(
                name="task",
                type="string",
                description="The task to delegate to the sub-agent",
                required=True
            ),
            ToolParameter(
                name="context",
                type="string",
                description="Additional context for the sub-agent",
                required=False
            )
        ],
        factory=create_delegate_tool,
        examples=[
            "delegate(agent_type='research', task='Find all information about Newton laws in the knowledge base')",
            "delegate(agent_type='analysis', task='Compare and contrast mitosis and meiosis')"
        ]
    ),

    ToolDefinition(
        name="verify_response",
        description="""Verify the quality of a response before delivering it.
Checks for accuracy, completeness, and educational value.

Use when:
- You've drafted a response and want to verify quality
- The response contains factual claims
- You want to ensure completeness""",
        category=ToolCategory.UTILITY,
        parameters=[
            ToolParameter(
                name="response",
                type="string",
                description="The response text to verify",
                required=True
            ),
            ToolParameter(
                name="query",
                type="string",
                description="The original user query",
                required=True
            ),
            ToolParameter(
                name="check_facts",
                type="boolean",
                description="Whether to check factual accuracy",
                required=False,
                default=True
            )
        ],
        factory=create_verify_response_tool,
        examples=[
            "verify_response(response='Photosynthesis is...', query='What is photosynthesis?')"
        ]
    ),

    ToolDefinition(
        name="finalize_response",
        description="""Mark a response as final and ready to deliver.
Use this when you're confident your response is complete and accurate.

This signals that the agentic loop should end and deliver the response.""",
        category=ToolCategory.UTILITY,
        parameters=[
            ToolParameter(
                name="response",
                type="string",
                description="The final response text",
                required=True
            ),
            ToolParameter(
                name="confidence",
                type="number",
                description="Your confidence level (0.0 to 1.0)",
                required=False,
                default=0.8
            ),
            ToolParameter(
                name="verification_passed",
                type="boolean",
                description="Whether verification was passed",
                required=False,
                default=True
            )
        ],
        factory=create_finalize_response_tool,
        examples=[
            "finalize_response(response='Here is my complete answer...', confidence=0.9)"
        ]
    ),

    ToolDefinition(
        name="request_clarification",
        description="""Request clarification from the user when you cannot find information.

Use this tool when:
- BOTH knowledge base AND web search returned NO RESULTS
- The query is ambiguous and needs more context
- You're uncertain how to proceed after exhausting search options

This signals that you need user input to continue effectively.
IMPORTANT: Only use after both search tools have been tried and returned empty.""",
        category=ToolCategory.UTILITY,
        parameters=[
            ToolParameter(
                name="reason",
                type="string",
                description="Why you need clarification from the user",
                required=True
            ),
            ToolParameter(
                name="suggestions",
                type="array",
                description="Suggested ways to rephrase or clarify the query",
                required=False
            ),
            ToolParameter(
                name="search_trail",
                type="array",
                description="List of sources that were searched (for transparency)",
                required=False
            )
        ],
        factory=create_request_clarification_tool,
        examples=[
            "request_clarification(reason='I could not find information on this topic in your notes or on the web.', suggestions=['Could you provide more context?', 'What specific aspect interests you?'])",
            "request_clarification(reason='The query is ambiguous', suggestions=['Are you asking about X or Y?'], search_trail=['knowledge_base: 0 results', 'web_search: 0 results'])"
        ]
    ),

    # === Knowledge Tools ===
    ToolDefinition(
        name="search_knowledge_base",
        description="""Search the user's PRIVATE knowledge base including journals, uploaded documents, and notes.

**THIS IS YOUR PRIMARY INFORMATION SOURCE - ALWAYS TRY FIRST**

Use this tool when:
- User asks about ANY topic that could be in their notes
- Looking for personalized context or previous learning
- The query is substantive enough to warrant a search
- The user references "my notes" or "what I wrote"
- Looking for information from uploaded PDFs, documents, or notes

**IMPORTANT**:
- If this returns NO RESULTS (results_count=0), you should then try web_search
  to find public information on the topic.
- Always check this source BEFORE web_search for substantive queries.

Returns: Relevant chunks with citation numbers for reference. May be empty if no matches found.""",
        category=ToolCategory.KNOWLEDGE,
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="The search query to find relevant knowledge",
                required=True
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum number of results to return (default: 5)",
                required=False,
                default=5
            )
        ],
        factory=create_search_knowledge_base_tool,
        requires_db=True,
        requires_rag=True,
        examples=[
            "search_knowledge_base(query='photosynthesis notes')",
            "search_knowledge_base(query='calculus derivatives', limit=3)"
        ]
    ),

    ToolDefinition(
        name="search_journals",
        description="""Search specifically through the user's journal entries.
Use this when:
- The user asks about their personal notes or reflections
- Looking for study notes on a specific topic
- The user mentions "my journal" or "what I learned"

Returns journal entries with titles and content previews.""",
        category=ToolCategory.KNOWLEDGE,
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="The search query for journal entries",
                required=True
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum number of journals to return (default: 5)",
                required=False,
                default=5
            )
        ],
        factory=create_search_journals_tool,
        requires_db=True,
        requires_rag=True,
        examples=[
            "search_journals(query='physics momentum')",
            "search_journals(query='essay ideas', limit=3)"
        ]
    ),

    ToolDefinition(
        name="search_past_conversations",
        description="""Search through past conversations with the tutor.
Use this when:
- The user references a previous discussion ("we talked about...")
- You need context from earlier learning sessions
- Looking for explanations given before on a topic
- The user asks to continue from where they left off

Returns relevant past exchanges with context.""",
        category=ToolCategory.MEMORY,
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="The search query for past conversations",
                required=True
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum number of results (default: 5)",
                required=False,
                default=5
            )
        ],
        factory=create_search_past_conversations_tool,
        requires_db=True,
        requires_rag=True,
        examples=[
            "search_past_conversations(query='explained gravity')",
            "search_past_conversations(query='homework help chemistry')"
        ]
    ),

    ToolDefinition(
        name="web_search",
        description="""Search the PUBLIC web for current information and facts.

**THIS IS YOUR SECONDARY/FALLBACK SOURCE**

Use this tool when:
- search_knowledge_base returned NO RESULTS (results_count=0)
- User explicitly asks to "search the web" or "look online"
- Topic requires current/recent information not in notes
- You need up-to-date information (news, current events)
- Looking for authoritative sources on a topic
- Verifying or supplementing information from knowledge base

**IMPORTANT**:
- Only use AFTER knowledge base search returns empty, unless user explicitly requests web search.
- If both knowledge base AND web search return no results, consider asking for clarification.

Returns: Web search results with titles and snippets. May be empty if no matches found.""",
        category=ToolCategory.SEARCH,
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="The web search query",
                required=True
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="Maximum search results (default: 5)",
                required=False,
                default=5
            )
        ],
        factory=create_web_search_tool,
        requires_web=True,
        examples=[
            "web_search(query='latest discoveries in quantum computing 2024')",
            "web_search(query='Newton laws of motion explained', max_results=3)"
        ]
    ),

    ToolDefinition(
        name="get_learning_context",
        description="""Get the current learning context for this session.
Use this to understand:
- What topics have been discussed
- The student's current learning state
- How many turns have occurred
- Previous key discoveries

Helpful for personalizing responses based on session history.""",
        category=ToolCategory.LEARNING,
        parameters=[],
        factory=create_get_learning_context_tool,
        examples=[
            "get_learning_context()"
        ]
    ),

    ToolDefinition(
        name="remember_discovery",
        description="""Record a key discovery or breakthrough in the student's learning.
Use this when:
- The student has an "aha moment"
- A concept finally clicks for them
- They make a connection between ideas
- They solve a problem in an insightful way

This helps track learning progress and can be referenced later.""",
        category=ToolCategory.LEARNING,
        parameters=[
            ToolParameter(
                name="discovery",
                type="string",
                description="Description of the discovery or insight",
                required=True
            ),
            ToolParameter(
                name="topic",
                type="string",
                description="The topic area of the discovery",
                required=True
            )
        ],
        factory=create_remember_discovery_tool,
        examples=[
            "remember_discovery(discovery='Understood that force equals mass times acceleration', topic='Newton laws')"
        ]
    ),

    # === Multimedia Tools ===
    ToolDefinition(
        name="create_manim_animation",
        description="""Generate a mathematical animation using Manim library to visualize concepts.

**PROACTIVE USE**: Create animations when explaining complex visual concepts!

Use this tool when:
- Explaining mathematical transformations or functions
- Visualizing physics concepts (motion, waves, fields)
- Demonstrating geometric proofs or constructions
- Showing algorithm step-by-step execution
- The student would benefit from seeing a concept in motion

The Manim code must define a Scene class with a construct() method.
The animation will be rendered and displayed to the student.""",
        category=ToolCategory.UTILITY,
        parameters=[
            ToolParameter(
                name="manim_code",
                type="string",
                description="Python code using Manim library (must define a Scene class with construct method)",
                required=True
            ),
            ToolParameter(
                name="title",
                type="string",
                description="Title for the animation",
                required=True
            ),
            ToolParameter(
                name="description",
                type="string",
                description="Brief description of what the animation demonstrates",
                required=False,
                default=""
            ),
            ToolParameter(
                name="quality",
                type="string",
                description="Video quality: 'low', 'medium', 'high'",
                required=False,
                default="medium",
                enum=["low", "medium", "high"]
            )
        ],
        factory=create_manim_animation_tool,
        examples=[
            """create_manim_animation(
    manim_code='''
from manim import *
class SineWave(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3], y_range=[-2, 2])
        sine_curve = axes.plot(lambda x: np.sin(x), color=BLUE)
        self.play(Create(axes), Create(sine_curve))
''',
    title='Sine Wave Visualization',
    description='Shows the sine function graphed on coordinate axes'
)"""
        ]
    ),

    ToolDefinition(
        name="link_preview",
        description="""Generate a rich preview card for a URL with title, description, and image.

**AUTOMATIC USE**: Use this whenever you mention or share a URL with the student!

Use this tool when:
- Sharing a reference link with the student
- A URL is mentioned in the conversation
- Providing links to educational resources
- Citing sources from the web

Returns a rich preview with title, description, image, and domain info.""",
        category=ToolCategory.UTILITY,
        parameters=[
            ToolParameter(
                name="url",
                type="string",
                description="The URL to generate a preview for",
                required=True
            ),
            ToolParameter(
                name="include_screenshot",
                type="boolean",
                description="Whether to include a page screenshot",
                required=False,
                default=False
            )
        ],
        factory=create_link_preview_tool,
        examples=[
            "link_preview(url='https://en.wikipedia.org/wiki/Quantum_mechanics')",
            "link_preview(url='https://www.khanacademy.org/math/calculus', include_screenshot=True)"
        ]
    ),

    ToolDefinition(
        name="display_image",
        description="""Display an image directly in the chat interface.

**PROACTIVE USE**: Show images when they would help explain a concept!

Use this tool when:
- You find a relevant diagram during research
- A visual would help explain the concept
- The student asks about something with useful visual representations
- Showing scientific diagrams, charts, or illustrations

The image will be displayed inline in the chat with optional caption.""",
        category=ToolCategory.UTILITY,
        parameters=[
            ToolParameter(
                name="image_url",
                type="string",
                description="URL of the image to display",
                required=True
            ),
            ToolParameter(
                name="alt_text",
                type="string",
                description="Accessibility text describing the image",
                required=False,
                default=""
            ),
            ToolParameter(
                name="caption",
                type="string",
                description="Caption to display below the image",
                required=False,
                default=""
            ),
            ToolParameter(
                name="size",
                type="string",
                description="Display size: 'small', 'medium', 'large'",
                required=False,
                default="medium",
                enum=["small", "medium", "large"]
            )
        ],
        factory=create_display_image_tool,
        examples=[
            "display_image(image_url='https://example.com/diagram.png', caption='Cell structure diagram', size='large')",
            "display_image(image_url='https://example.com/graph.svg', alt_text='Graph showing exponential growth')"
        ]
    ),
]


def get_tool_by_name(name: str) -> Optional[ToolDefinition]:
    """Get a tool definition by name"""
    for tool in TOOL_REGISTRY:
        if tool.name == name:
            return tool
    return None


def get_tools_by_category(category: ToolCategory) -> List[ToolDefinition]:
    """Get all tools in a category"""
    return [t for t in TOOL_REGISTRY if t.category == category]


def get_all_tool_schemas() -> List[Dict[str, Any]]:
    """Get OpenAI function schemas for all tools"""
    return [tool.to_openai_schema() for tool in TOOL_REGISTRY]
