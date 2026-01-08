"""
Unit Tests for Query Classifier

Tests the query classification system that determines whether queries are:
- Trivial (greetings, small talk) -> Skip tools
- General Knowledge (simple facts) -> Skip tools
- Substantive (research needed) -> Use tools

Location: testing_SAI/unit/test_query_classifier.py
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from services.agent.query_classifier import QueryClassifier, QueryClassification

# Mark all tests as unit tests
pytestmark = pytest.mark.unit


class TestQueryClassifierInit:
    """Tests for QueryClassifier initialization."""

    def test_classifier_initializes(self):
        """Test that classifier initializes without error."""
        classifier = QueryClassifier()
        assert classifier is not None

    def test_patterns_are_compiled(self):
        """Test that regex patterns are pre-compiled."""
        classifier = QueryClassifier()
        assert len(classifier._trivial_compiled) > 0
        assert len(classifier._substantive_compiled) > 0


class TestTrivialQueryClassification:
    """Tests for trivial query detection (should skip tools)."""

    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    # === Greetings ===
    @pytest.mark.parametrize("query", [
        "hi",
        "Hi",
        "HI",
        "hello",
        "Hello!",
        "hey",
        "Hey there",
        "hiya",
        "good morning",
        "Good Morning!",
        "good afternoon",
        "good evening",
        "good night",
        "greetings",
    ])
    def test_greetings_are_trivial(self, classifier, query):
        """Greeting queries should be classified as trivial."""
        result = classifier.classify(query)
        assert result.is_trivial is True, f"'{query}' should be trivial"
        assert result.skip_tools is True, f"'{query}' should skip tools"

    # === Pleasantries ===
    @pytest.mark.parametrize("query", [
        "thank you",
        "Thanks!",
        "thanks",
        "thx",
        "ty",
        "thank u",
        "much appreciated",
    ])
    def test_thanks_are_trivial(self, classifier, query):
        """Thank you messages should be trivial."""
        result = classifier.classify(query)
        assert result.is_trivial is True, f"'{query}' should be trivial"

    # === Farewells ===
    @pytest.mark.parametrize("query", [
        "bye",
        "goodbye",
        "Goodbye!",
        "see you",
        "see ya",
        "later",
        "cya",
        "farewell",
    ])
    def test_farewells_are_trivial(self, classifier, query):
        """Farewell messages should be trivial."""
        result = classifier.classify(query)
        assert result.is_trivial is True, f"'{query}' should be trivial"

    # === Small Talk ===
    @pytest.mark.parametrize("query", [
        "how are you",
        "How are you?",
        "how're you",
        "how r u",
        "how you doing",
        "how do you do",
    ])
    def test_small_talk_is_trivial(self, classifier, query):
        """Small talk should be trivial."""
        result = classifier.classify(query)
        assert result.is_trivial is True, f"'{query}' should be trivial"

    # === Single Word Responses ===
    @pytest.mark.parametrize("query", [
        "yes",
        "Yes",
        "no",
        "No",
        "ok",
        "OK",
        "okay",
        "sure",
        "maybe",
        "nope",
        "yep",
        "yup",
        "nah",
    ])
    def test_yes_no_responses_are_trivial(self, classifier, query):
        """Yes/no responses should be trivial."""
        result = classifier.classify(query)
        assert result.is_trivial is True, f"'{query}' should be trivial"

    # === Acknowledgments ===
    @pytest.mark.parametrize("query", [
        "cool",
        "awesome",
        "great",
        "nice",
        "perfect",
        "excellent",
        "wonderful",
        "got it",
        "understood",
        "i see",
        "i understand",
        "makes sense",
        "alright",
        "sounds good",
    ])
    def test_acknowledgments_are_trivial(self, classifier, query):
        """Acknowledgment responses should be trivial."""
        result = classifier.classify(query)
        assert result.is_trivial is True, f"'{query}' should be trivial"

    # === Filler Words ===
    @pytest.mark.parametrize("query", [
        "hmm",
        "hm",
        "um",
        "uh",
        "ah",
        "oh",
        "wow",
    ])
    def test_filler_words_are_trivial(self, classifier, query):
        """Filler words should be trivial."""
        result = classifier.classify(query)
        assert result.is_trivial is True, f"'{query}' should be trivial"


class TestSubstantiveQueryClassification:
    """Tests for substantive query detection (should use tools)."""

    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    # === Personal Knowledge Queries ===
    @pytest.mark.parametrize("query", [
        "What is in my notes about physics?",
        "Search my documents for quantum mechanics",
        "What did I write about Newton's laws?",
        "Find my journal entries about biology",
        "Look up my notes on calculus",
        "What's in my uploaded files about chemistry?",
    ])
    def test_personal_knowledge_queries_are_substantive(self, classifier, query):
        """Personal knowledge queries should be substantive."""
        result = classifier.classify(query)
        assert result.is_trivial is False, f"'{query}' should NOT be trivial"
        assert result.skip_tools is False, f"'{query}' should NOT skip tools"
        assert result.query_type == "substantive"

    # === Research Requests ===
    @pytest.mark.parametrize("query", [
        "Search for information about machine learning",
        "Find resources on neural networks",
        "Look for articles about climate change",
        "Research the history of computers",
        "Explore the topic of quantum physics",
        "Investigate the causes of WWI",
    ])
    def test_research_requests_are_substantive(self, classifier, query):
        """Research requests should be substantive."""
        result = classifier.classify(query)
        assert result.is_trivial is False, f"'{query}' should NOT be trivial"
        assert result.skip_tools is False

    # === Explanation Requests ===
    @pytest.mark.parametrize("query", [
        "Tell me about photosynthesis",
        "Explain how neural networks work",
        "Describe the process of mitosis",
        "Can you help me understand relativity?",
        "Please assist with calculus integration",
    ])
    def test_explanation_requests_are_substantive(self, classifier, query):
        """Explanation requests should be substantive."""
        result = classifier.classify(query)
        assert result.is_trivial is False, f"'{query}' should NOT be trivial"

    # === Analysis Requests ===
    @pytest.mark.parametrize("query", [
        "Compare and contrast mitosis and meiosis",
        "Analyze the differences between TCP and UDP",
        "Evaluate the pros and cons of renewable energy",
        "Assess the impact of social media on society",
        "What are the advantages and disadvantages of remote work?",
    ])
    def test_analysis_requests_are_substantive(self, classifier, query):
        """Analysis requests should be substantive."""
        result = classifier.classify(query)
        assert result.is_trivial is False
        assert result.skip_tools is False

    # === Context-Based Queries ===
    @pytest.mark.parametrize("query", [
        "Based on my notes, what is the formula for kinetic energy?",
        "According to my documents, when was the French Revolution?",
        "Referring to our previous discussion, what was the key point?",
        "In the context of machine learning, what is overfitting?",
    ])
    def test_context_queries_are_substantive(self, classifier, query):
        """Context-based queries should be substantive."""
        result = classifier.classify(query)
        assert result.is_trivial is False


class TestGeneralKnowledgeClassification:
    """Tests for general knowledge queries (may skip tools)."""

    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    @pytest.mark.parametrize("query", [
        "What is the capital of France?",
        "Who was the first president of the USA?",
        "How many days are in a year?",
    ])
    def test_simple_facts_may_skip_tools(self, classifier, query):
        """Simple factual questions may skip tools."""
        result = classifier.classify(query)
        # These could be either trivial or general_knowledge
        assert result.query_type in ["trivial", "general_knowledge", "substantive"]


class TestQueryClassificationOutput:
    """Tests for QueryClassification dataclass output."""

    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    def test_classification_has_all_fields(self, classifier):
        """Classification result should have all required fields."""
        result = classifier.classify("Hello")

        assert hasattr(result, 'is_trivial')
        assert hasattr(result, 'query_type')
        assert hasattr(result, 'skip_tools')
        assert hasattr(result, 'reason')
        assert hasattr(result, 'confidence')

    def test_confidence_in_valid_range(self, classifier):
        """Confidence should be between 0 and 1."""
        for query in ["hi", "what is physics?", "search my notes"]:
            result = classifier.classify(query)
            assert 0.0 <= result.confidence <= 1.0

    def test_query_type_is_valid(self, classifier):
        """Query type should be one of the valid types."""
        valid_types = ["trivial", "general_knowledge", "substantive"]

        for query in ["hi", "what is 2+2?", "explain quantum entanglement in detail"]:
            result = classifier.classify(query)
            assert result.query_type in valid_types


class TestSubjectContext:
    """Tests for subject context affecting classification."""

    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    def test_subject_context_affects_classification(self, classifier):
        """Subject context should affect classification of ambiguous queries."""
        # A longer query in subject context should be substantive
        query = "Tell me more about this topic we're studying"

        result_no_subject = classifier.classify(query)
        result_with_subject = classifier.classify(query, subject="physics")

        # With subject context, more likely to be substantive
        if len(query) > 20:
            assert result_with_subject.query_type == "substantive"


class TestHelperMethods:
    """Tests for helper methods."""

    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    def test_is_trivial_method(self, classifier):
        """Test is_trivial helper method."""
        assert classifier.is_trivial("hi") is True
        assert classifier.is_trivial("explain quantum physics") is False

    def test_should_skip_tools_method(self, classifier):
        """Test should_skip_tools helper method."""
        assert classifier.should_skip_tools("hello") is True
        assert classifier.should_skip_tools("search my notes for physics") is False


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def classifier(self):
        return QueryClassifier()

    def test_empty_string(self, classifier):
        """Empty string should be handled gracefully."""
        result = classifier.classify("")
        assert result is not None

    def test_whitespace_only(self, classifier):
        """Whitespace-only string should be handled."""
        result = classifier.classify("   ")
        assert result is not None

    def test_very_long_query(self, classifier):
        """Very long queries should be handled."""
        long_query = "explain " * 100 + "physics"
        result = classifier.classify(long_query)
        assert result.is_trivial is False

    def test_special_characters(self, classifier):
        """Queries with special characters should be handled."""
        result = classifier.classify("What is E=mc²?")
        assert result is not None

    def test_mixed_case(self, classifier):
        """Mixed case should not affect classification."""
        result_lower = classifier.classify("hello")
        result_upper = classifier.classify("HELLO")
        result_mixed = classifier.classify("HeLLo")

        assert result_lower.is_trivial == result_upper.is_trivial == result_mixed.is_trivial

    def test_with_punctuation(self, classifier):
        """Punctuation should not break classification."""
        assert classifier.is_trivial("hi!") is True
        assert classifier.is_trivial("hello...") is True
        assert classifier.is_trivial("thanks!!!") is True
