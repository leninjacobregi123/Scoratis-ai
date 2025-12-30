"""
Golden Dataset for Agent Evaluation

This file contains the golden dataset used to evaluate agent performance.
Each entry includes:
- Query: The user's question
- Expected behavior: What the agent should do
- Quality criteria: How to evaluate the response
- Reference answer: Optional reference for comparison

Usage:
    from tests.evaluation.golden_dataset import GOLDEN_DATASET

    for test_case in GOLDEN_DATASET:
        result = await agent.invoke(test_case["query"])
        evaluate(result, test_case)
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class ResponseFormat(str, Enum):
    """Expected response format types."""
    DEFINITION = "definition"
    EXPLANATION = "explanation"
    COMPARISON = "comparison"
    LIST = "list"
    SUMMARY = "summary"
    STEP_BY_STEP = "step_by_step"
    CONVERSATIONAL = "conversational"


class ToolExpectation(str, Enum):
    """Expected tool usage."""
    SEARCH_KNOWLEDGE = "search_knowledge_base"
    SEARCH_JOURNALS = "search_journals"
    WEB_SEARCH = "web_search"
    NONE = "none"


@dataclass
class EvaluationCriteria:
    """Criteria for evaluating a response."""
    factual_accuracy: bool = True
    relevance: bool = True
    completeness: bool = True
    clarity: bool = True
    uses_citations: bool = False
    uses_rag: bool = False
    comparison_clarity: bool = False
    examples_provided: bool = False
    technical_depth: bool = False


@dataclass
class GoldenTestCase:
    """A single test case in the golden dataset."""
    id: str
    query: str
    category: str
    expected_format: ResponseFormat
    expected_topics: List[str]
    criteria: EvaluationCriteria
    min_length: int = 50
    max_length: int = 2000
    expected_tools: List[ToolExpectation] = field(default_factory=list)
    reference_answer: str = ""
    difficulty: str = "medium"  # easy, medium, hard


# =============================================================================
# Golden Dataset
# =============================================================================

GOLDEN_DATASET: List[GoldenTestCase] = [
    # === Basic Knowledge Questions ===
    GoldenTestCase(
        id="basic_001",
        query="What is machine learning?",
        category="definitions",
        expected_format=ResponseFormat.DEFINITION,
        expected_topics=["machine learning", "AI", "artificial intelligence", "algorithms", "data"],
        criteria=EvaluationCriteria(
            factual_accuracy=True,
            relevance=True,
            completeness=True,
            clarity=True
        ),
        min_length=100,
        difficulty="easy",
        reference_answer="Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It focuses on developing algorithms that can access data and use it to learn for themselves."
    ),

    GoldenTestCase(
        id="basic_002",
        query="Explain photosynthesis in simple terms",
        category="explanations",
        expected_format=ResponseFormat.EXPLANATION,
        expected_topics=["photosynthesis", "plants", "sunlight", "carbon dioxide", "oxygen", "chlorophyll"],
        criteria=EvaluationCriteria(
            factual_accuracy=True,
            relevance=True,
            clarity=True,
            examples_provided=True
        ),
        min_length=100,
        difficulty="easy"
    ),

    # === Comparison Questions ===
    GoldenTestCase(
        id="compare_001",
        query="What's the difference between supervised and unsupervised learning?",
        category="comparisons",
        expected_format=ResponseFormat.COMPARISON,
        expected_topics=["supervised learning", "unsupervised learning", "labeled data", "classification", "clustering"],
        criteria=EvaluationCriteria(
            factual_accuracy=True,
            relevance=True,
            comparison_clarity=True,
            completeness=True
        ),
        min_length=150,
        difficulty="medium"
    ),

    GoldenTestCase(
        id="compare_002",
        query="Compare and contrast mitosis and meiosis",
        category="comparisons",
        expected_format=ResponseFormat.COMPARISON,
        expected_topics=["mitosis", "meiosis", "cell division", "chromosomes", "daughter cells"],
        criteria=EvaluationCriteria(
            factual_accuracy=True,
            comparison_clarity=True,
            completeness=True,
            technical_depth=True
        ),
        min_length=200,
        difficulty="medium"
    ),

    # === Technical Explanations ===
    GoldenTestCase(
        id="tech_001",
        query="How does a neural network learn?",
        category="technical",
        expected_format=ResponseFormat.EXPLANATION,
        expected_topics=["neural network", "backpropagation", "weights", "gradient descent", "training"],
        criteria=EvaluationCriteria(
            factual_accuracy=True,
            technical_depth=True,
            completeness=True
        ),
        min_length=200,
        difficulty="hard"
    ),

    GoldenTestCase(
        id="tech_002",
        query="Explain how transformers work in NLP",
        category="technical",
        expected_format=ResponseFormat.EXPLANATION,
        expected_topics=["transformers", "attention", "self-attention", "encoder", "decoder"],
        criteria=EvaluationCriteria(
            factual_accuracy=True,
            technical_depth=True,
            completeness=True
        ),
        min_length=250,
        difficulty="hard"
    ),

    # === List/Enumeration Questions ===
    GoldenTestCase(
        id="list_001",
        query="What are the main applications of natural language processing?",
        category="applications",
        expected_format=ResponseFormat.LIST,
        expected_topics=["NLP", "text analysis", "chatbots", "translation", "sentiment analysis"],
        criteria=EvaluationCriteria(
            factual_accuracy=True,
            completeness=True,
            examples_provided=True
        ),
        min_length=150,
        difficulty="easy"
    ),

    GoldenTestCase(
        id="list_002",
        query="List the key principles of object-oriented programming",
        category="programming",
        expected_format=ResponseFormat.LIST,
        expected_topics=["encapsulation", "inheritance", "polymorphism", "abstraction", "OOP"],
        criteria=EvaluationCriteria(
            factual_accuracy=True,
            completeness=True,
            examples_provided=True
        ),
        min_length=150,
        difficulty="medium"
    ),

    # === RAG-Required Questions ===
    GoldenTestCase(
        id="rag_001",
        query="What did I write in my notes about photosynthesis?",
        category="personal_knowledge",
        expected_format=ResponseFormat.SUMMARY,
        expected_topics=["photosynthesis", "notes"],
        expected_tools=[ToolExpectation.SEARCH_KNOWLEDGE, ToolExpectation.SEARCH_JOURNALS],
        criteria=EvaluationCriteria(
            uses_rag=True,
            uses_citations=True,
            relevance=True
        ),
        min_length=50,
        difficulty="medium"
    ),

    GoldenTestCase(
        id="rag_002",
        query="Summarize my journal entries about machine learning",
        category="personal_knowledge",
        expected_format=ResponseFormat.SUMMARY,
        expected_topics=["machine learning", "journal", "notes"],
        expected_tools=[ToolExpectation.SEARCH_JOURNALS],
        criteria=EvaluationCriteria(
            uses_rag=True,
            uses_citations=True,
            relevance=True
        ),
        min_length=50,
        difficulty="medium"
    ),

    # === Step-by-Step Instructions ===
    GoldenTestCase(
        id="steps_001",
        query="How do I implement a binary search algorithm?",
        category="programming",
        expected_format=ResponseFormat.STEP_BY_STEP,
        expected_topics=["binary search", "algorithm", "sorted array", "complexity"],
        criteria=EvaluationCriteria(
            factual_accuracy=True,
            completeness=True,
            clarity=True,
            examples_provided=True
        ),
        min_length=200,
        difficulty="medium"
    ),

    # === Current Events (Web Search Required) ===
    GoldenTestCase(
        id="current_001",
        query="What are the latest developments in AI?",
        category="current_events",
        expected_format=ResponseFormat.LIST,
        expected_topics=["AI", "developments", "recent"],
        expected_tools=[ToolExpectation.WEB_SEARCH],
        criteria=EvaluationCriteria(
            relevance=True,
            completeness=True
        ),
        min_length=100,
        difficulty="medium"
    ),

    # === Conversational / Clarification ===
    GoldenTestCase(
        id="conv_001",
        query="Can you explain that more simply?",
        category="clarification",
        expected_format=ResponseFormat.CONVERSATIONAL,
        expected_topics=[],  # Depends on context
        criteria=EvaluationCriteria(
            relevance=True,
            clarity=True
        ),
        min_length=50,
        difficulty="easy"
    ),

    # === Edge Cases ===
    GoldenTestCase(
        id="edge_001",
        query="",
        category="edge_case",
        expected_format=ResponseFormat.CONVERSATIONAL,
        expected_topics=[],
        criteria=EvaluationCriteria(),
        min_length=0,
        difficulty="easy"
    ),

    GoldenTestCase(
        id="edge_002",
        query="asdfghjkl random gibberish text",
        category="edge_case",
        expected_format=ResponseFormat.CONVERSATIONAL,
        expected_topics=[],
        criteria=EvaluationCriteria(
            relevance=True
        ),
        min_length=20,
        difficulty="easy"
    ),
]


def get_test_cases_by_category(category: str) -> List[GoldenTestCase]:
    """Get all test cases in a category."""
    return [tc for tc in GOLDEN_DATASET if tc.category == category]


def get_test_cases_by_difficulty(difficulty: str) -> List[GoldenTestCase]:
    """Get all test cases of a difficulty level."""
    return [tc for tc in GOLDEN_DATASET if tc.difficulty == difficulty]


def get_rag_required_cases() -> List[GoldenTestCase]:
    """Get all test cases that require RAG."""
    return [tc for tc in GOLDEN_DATASET if tc.criteria.uses_rag]


def get_web_search_cases() -> List[GoldenTestCase]:
    """Get all test cases that may need web search."""
    return [tc for tc in GOLDEN_DATASET if ToolExpectation.WEB_SEARCH in tc.expected_tools]
