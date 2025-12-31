"""
Subject Guardrail Service
Validates that user queries are related to the selected subject channel.
Implements a hybrid approach: allows minor tangents but blocks completely unrelated topics.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class GuardrailResult(str, Enum):
    """Result types for guardrail check"""
    ALLOWED = "allowed"           # Query is on-topic
    TANGENT = "tangent"           # Query is a related tangent (allowed)
    BLOCKED = "blocked"           # Query is completely off-topic


@dataclass
class GuardrailResponse:
    """Response from guardrail check"""
    result: GuardrailResult
    message: Optional[str] = None           # Redirection message if blocked
    suggested_subject: Optional[str] = None  # Better subject for this query
    confidence: float = 1.0                  # Confidence in the decision


# Subject boundaries: core topics and allowed tangents
SUBJECT_BOUNDARIES: Dict[str, Dict] = {
    "physics": {
        "core_topics": [
            "mechanics", "motion", "force", "energy", "momentum",
            "thermodynamics", "heat", "temperature", "entropy",
            "electromagnetism", "electricity", "magnetism", "circuits",
            "waves", "sound", "light", "optics",
            "quantum physics", "quantum mechanics", "particle physics",
            "relativity", "spacetime", "gravity", "gravitational",
            "nuclear physics", "radioactivity", "fission", "fusion",
            "astrophysics", "cosmology", "black holes", "stars",
            "fluid dynamics", "pressure", "buoyancy",
        ],
        "allowed_tangents": [
            # Math connections
            "calculus", "differential equations", "vectors", "trigonometry",
            # Chemistry connections
            "atomic structure", "electrons", "molecular bonds",
            # Engineering connections
            "machines", "engines", "electronics",
            # Philosophy of science
            "scientific method", "experiments", "measurement",
        ],
        "blocked_patterns": [
            "recipe", "cooking", "literature analysis", "poem", "essay writing",
            "history of war", "political", "economics market", "psychology therapy",
        ],
        "redirect_message": "That's an interesting topic, but it's not directly related to Physics. Would you like to explore the physical principles behind it, or switch to a more appropriate subject?",
    },

    "chemistry": {
        "core_topics": [
            "atoms", "molecules", "elements", "compounds",
            "periodic table", "electron configuration", "orbitals",
            "chemical bonds", "ionic", "covalent", "metallic",
            "chemical reactions", "stoichiometry", "balancing equations",
            "acids", "bases", "pH", "buffers",
            "organic chemistry", "hydrocarbons", "functional groups",
            "biochemistry", "proteins", "carbohydrates", "lipids",
            "thermochemistry", "enthalpy", "entropy", "gibbs",
            "electrochemistry", "redox", "oxidation", "reduction",
            "kinetics", "reaction rates", "catalysts",
            "solutions", "concentration", "molarity", "solubility",
        ],
        "allowed_tangents": [
            # Biology connections
            "metabolism", "enzymes", "dna structure",
            # Physics connections
            "quantum mechanics", "spectroscopy", "energy levels",
            # Environmental
            "pollution", "green chemistry", "climate",
            # Practical applications
            "pharmaceuticals", "materials", "polymers",
        ],
        "blocked_patterns": [
            "history of civilization", "literature", "art critique",
            "political science", "psychology behavior", "music theory",
        ],
        "redirect_message": "That's a fascinating question, but it doesn't fall within Chemistry. Perhaps we can find the chemical aspects of your topic, or you might want to explore a different subject channel.",
    },

    "biology": {
        "core_topics": [
            "cells", "cell biology", "organelles", "mitochondria",
            "genetics", "dna", "rna", "genes", "chromosomes", "heredity",
            "evolution", "natural selection", "adaptation", "speciation",
            "ecology", "ecosystems", "food chains", "biodiversity",
            "anatomy", "physiology", "organ systems",
            "microbiology", "bacteria", "viruses", "microorganisms",
            "botany", "plants", "photosynthesis", "plant biology",
            "zoology", "animals", "animal behavior",
            "biochemistry", "metabolism", "enzymes",
            "immunology", "immune system", "antibodies",
            "neurobiology", "nervous system", "neurons",
        ],
        "allowed_tangents": [
            # Chemistry connections
            "molecular biology", "chemical reactions in cells",
            # Environmental
            "climate change effects", "conservation",
            # Medical
            "diseases", "medicine", "health",
            # Agriculture
            "farming", "crop science", "breeding",
        ],
        "blocked_patterns": [
            "pure mathematics", "physics equations", "programming code",
            "historical events", "literature analysis", "art history",
        ],
        "redirect_message": "That's an intriguing topic! While it's not directly about Biology, we could explore the biological aspects. Would you like to do that, or switch to a subject that better fits your question?",
    },

    "mathematics": {
        "core_topics": [
            "algebra", "equations", "variables", "polynomials",
            "calculus", "derivatives", "integrals", "limits",
            "geometry", "shapes", "angles", "triangles", "circles",
            "trigonometry", "sine", "cosine", "tangent",
            "statistics", "probability", "data analysis", "distributions",
            "linear algebra", "matrices", "vectors", "eigenvalues",
            "number theory", "primes", "divisibility",
            "discrete math", "combinatorics", "graph theory",
            "logic", "proofs", "theorems",
            "differential equations", "sequences", "series",
        ],
        "allowed_tangents": [
            # Physics applications
            "physics problems", "motion equations",
            # Computer science
            "algorithms", "complexity", "cryptography",
            # Economics
            "optimization", "game theory", "financial math",
            # Philosophy
            "mathematical logic", "foundations of math",
        ],
        "blocked_patterns": [
            "biology experiments", "chemical reactions", "history events",
            "literature essay", "art critique", "music composition",
        ],
        "redirect_message": "Great curiosity! That topic isn't primarily mathematical, but if there are mathematical aspects you'd like to explore, I'm here to help. Otherwise, consider switching to a more suitable subject.",
    },

    "computer_science": {
        "core_topics": [
            "programming", "coding", "software", "algorithms",
            "data structures", "arrays", "lists", "trees", "graphs",
            "databases", "sql", "nosql", "queries",
            "operating systems", "processes", "memory", "file systems",
            "networking", "protocols", "tcp", "http", "internet",
            "artificial intelligence", "machine learning", "neural networks",
            "cybersecurity", "encryption", "hacking", "security",
            "web development", "frontend", "backend", "apis",
            "compilers", "interpreters", "programming languages",
            "software engineering", "design patterns", "testing",
        ],
        "allowed_tangents": [
            # Mathematics
            "discrete math", "logic", "complexity theory",
            # Physics
            "computer hardware", "electronics", "quantum computing",
            # Applications
            "automation", "robotics", "game development",
        ],
        "blocked_patterns": [
            "biology cells", "chemistry reactions", "history wars",
            "literature analysis", "psychology therapy", "art painting",
        ],
        "redirect_message": "Interesting question! It's not directly about Computer Science, but if you're curious about how technology relates to it, let me know. Or feel free to switch to a more relevant subject.",
    },

    "english": {
        "core_topics": [
            "grammar", "syntax", "punctuation", "spelling",
            "writing", "essays", "paragraphs", "thesis",
            "literature", "novels", "poetry", "drama", "prose",
            "literary analysis", "themes", "symbolism", "motifs",
            "rhetoric", "persuasion", "argumentation",
            "creative writing", "fiction", "storytelling",
            "vocabulary", "word meanings", "etymology",
            "reading comprehension", "analysis", "interpretation",
            "authors", "literary movements", "genres",
        ],
        "allowed_tangents": [
            # History
            "historical context", "cultural background",
            # Philosophy
            "philosophical themes", "ethics in literature",
            # Psychology
            "character psychology", "motivation",
        ],
        "blocked_patterns": [
            "math equations", "physics formulas", "chemistry reactions",
            "computer code", "biology experiments",
        ],
        "redirect_message": "That's an interesting topic, but it falls outside English/Literature studies. If you'd like to explore the linguistic or literary aspects, I can help with that. Otherwise, another subject might be more suitable.",
    },

    "history": {
        "core_topics": [
            "civilizations", "empires", "kingdoms", "nations",
            "wars", "battles", "conflicts", "revolutions",
            "historical figures", "leaders", "monarchs", "presidents",
            "ancient history", "medieval", "renaissance", "modern",
            "world wars", "cold war", "colonialism", "imperialism",
            "social movements", "civil rights", "suffrage",
            "historical events", "treaties", "declarations",
            "archaeology", "artifacts", "excavations",
            "historiography", "primary sources", "historical analysis",
        ],
        "allowed_tangents": [
            # Geography
            "historical geography", "maps", "borders",
            # Economics
            "economic history", "trade routes", "industrial revolution",
            # Philosophy
            "political philosophy", "historical ideas",
            # Culture
            "art history", "cultural history", "religion history",
        ],
        "blocked_patterns": [
            "math problems", "physics equations", "chemistry experiments",
            "computer programming", "biology lab",
        ],
        "redirect_message": "Fascinating question! While it's not directly about History, there might be historical aspects we can explore. Would you like to find the historical angle, or switch to another subject?",
    },

    "philosophy": {
        "core_topics": [
            "ethics", "morality", "right and wrong", "virtue",
            "metaphysics", "existence", "reality", "being",
            "epistemology", "knowledge", "truth", "belief",
            "logic", "reasoning", "arguments", "fallacies",
            "political philosophy", "justice", "rights", "freedom",
            "philosophy of mind", "consciousness", "free will",
            "aesthetics", "beauty", "art philosophy",
            "philosophers", "plato", "aristotle", "kant", "nietzsche",
            "existentialism", "meaning of life", "purpose",
        ],
        "allowed_tangents": [
            # Science philosophy
            "philosophy of science", "scientific method",
            # Religion
            "philosophy of religion", "theology",
            # Psychology
            "philosophy of mind", "cognitive science",
            # Math
            "philosophy of mathematics", "logic",
        ],
        "blocked_patterns": [
            "math calculations", "physics formulas", "chemistry lab",
            "computer code", "biology experiments", "cooking recipes",
        ],
        "redirect_message": "An intriguing question! It's not directly within philosophical inquiry, but many topics have philosophical dimensions. Would you like to explore those, or switch to a different subject?",
    },

    "psychology": {
        "core_topics": [
            "behavior", "mind", "mental processes", "cognition",
            "emotions", "feelings", "mood", "affect",
            "personality", "traits", "temperament",
            "developmental psychology", "child development", "aging",
            "social psychology", "groups", "conformity", "influence",
            "cognitive psychology", "memory", "attention", "perception",
            "clinical psychology", "disorders", "therapy", "treatment",
            "neuroscience", "brain", "neurons", "neural",
            "motivation", "learning", "conditioning",
            "psychological theories", "freud", "jung", "skinner",
        ],
        "allowed_tangents": [
            # Biology
            "neurobiology", "brain chemistry", "genetics and behavior",
            # Philosophy
            "philosophy of mind", "consciousness",
            # Sociology
            "social behavior", "culture", "groups",
            # Education
            "learning theories", "educational psychology",
        ],
        "blocked_patterns": [
            "math equations", "physics formulas", "chemistry synthesis",
            "computer algorithms", "historical battles",
        ],
        "redirect_message": "That's an interesting question! While it's not directly about Psychology, there may be psychological aspects worth exploring. Would you like to examine those, or try a different subject?",
    },

    "economics": {
        "core_topics": [
            "supply and demand", "markets", "prices", "equilibrium",
            "microeconomics", "firms", "consumers", "production",
            "macroeconomics", "gdp", "inflation", "unemployment",
            "monetary policy", "fiscal policy", "interest rates",
            "international trade", "globalization", "exchange rates",
            "economic growth", "development", "poverty",
            "behavioral economics", "decision making", "biases",
            "game theory", "strategy", "competition",
            "financial markets", "stocks", "bonds", "investing",
            "economic theories", "adam smith", "keynes", "marx",
        ],
        "allowed_tangents": [
            # Mathematics
            "statistics", "econometrics", "optimization",
            # Politics
            "economic policy", "government regulation",
            # History
            "economic history", "great depression",
            # Psychology
            "behavioral economics", "consumer behavior",
        ],
        "blocked_patterns": [
            "biology cells", "chemistry formulas", "physics motion",
            "literature analysis", "art critique",
        ],
        "redirect_message": "Interesting question! It's not primarily economic in nature, but there might be economic implications to explore. Would you like to look at the economic angle, or switch to another subject?",
    },

    "general": {
        "core_topics": [],  # Accept everything
        "allowed_tangents": [],
        "blocked_patterns": [],
        "redirect_message": None,
    },
}


class GuardrailService:
    """
    Service for validating that user queries are related to the selected subject.

    Uses a combination of:
    1. Keyword matching for quick filtering
    2. Pattern matching for known off-topic queries
    3. Optional LLM-based classification for edge cases
    """

    def __init__(self, llm_service=None):
        """
        Initialize the guardrail service.

        Args:
            llm_service: Optional LLM service for complex classification
        """
        self.llm_service = llm_service
        self._classification_cache: Dict[str, GuardrailResponse] = {}

    def check_query(
        self,
        query: str,
        subject: str,
        use_llm: bool = False,
    ) -> GuardrailResponse:
        """
        Check if a query is related to the given subject.

        Args:
            query: The user's query
            subject: The selected subject channel
            use_llm: Whether to use LLM for complex cases

        Returns:
            GuardrailResponse with result and optional message
        """
        # General subject accepts everything
        if subject == "general" or subject not in SUBJECT_BOUNDARIES:
            return GuardrailResponse(
                result=GuardrailResult.ALLOWED,
                confidence=1.0
            )

        query_lower = query.lower()
        boundaries = SUBJECT_BOUNDARIES[subject]

        # Step 1: Check for blocked patterns (quick rejection)
        for pattern in boundaries.get("blocked_patterns", []):
            if pattern.lower() in query_lower:
                suggested = self._suggest_subject(query_lower)
                return GuardrailResponse(
                    result=GuardrailResult.BLOCKED,
                    message=boundaries.get("redirect_message"),
                    suggested_subject=suggested,
                    confidence=0.9
                )

        # Step 2: Check for core topics (quick acceptance)
        for topic in boundaries.get("core_topics", []):
            if topic.lower() in query_lower:
                return GuardrailResponse(
                    result=GuardrailResult.ALLOWED,
                    confidence=0.95
                )

        # Step 3: Check for allowed tangents
        for tangent in boundaries.get("allowed_tangents", []):
            if tangent.lower() in query_lower:
                return GuardrailResponse(
                    result=GuardrailResult.TANGENT,
                    confidence=0.85
                )

        # Step 4: For short queries or common phrases, allow with lower confidence
        if len(query.split()) <= 5:
            # Short queries are usually contextual, allow them
            return GuardrailResponse(
                result=GuardrailResult.ALLOWED,
                confidence=0.7
            )

        # Step 5: Use LLM for complex classification if enabled
        if use_llm and self.llm_service:
            return self._llm_classify(query, subject, boundaries)

        # Default: Allow with moderate confidence (hybrid approach - lenient)
        return GuardrailResponse(
            result=GuardrailResult.ALLOWED,
            confidence=0.6
        )

    async def check_query_async(
        self,
        query: str,
        subject: str,
        use_llm: bool = True,
    ) -> GuardrailResponse:
        """
        Async version of check_query with LLM support.

        Args:
            query: The user's query
            subject: The selected subject channel
            use_llm: Whether to use LLM for classification

        Returns:
            GuardrailResponse with result and optional message
        """
        # Check cache first
        cache_key = f"{subject}:{query[:100]}"
        if cache_key in self._classification_cache:
            return self._classification_cache[cache_key]

        # Quick keyword-based check first
        quick_result = self.check_query(query, subject, use_llm=False)

        # If confident enough, return immediately
        if quick_result.confidence >= 0.85:
            return quick_result

        # For ambiguous cases with LLM enabled
        if use_llm and self.llm_service and quick_result.confidence < 0.7:
            result = await self._llm_classify_async(query, subject)
            # Cache the result
            self._classification_cache[cache_key] = result
            # Limit cache size
            if len(self._classification_cache) > 1000:
                # Remove oldest entries
                keys = list(self._classification_cache.keys())[:100]
                for k in keys:
                    del self._classification_cache[k]
            return result

        return quick_result

    def _suggest_subject(self, query_lower: str) -> Optional[str]:
        """
        Suggest a more appropriate subject for the query.

        Args:
            query_lower: Lowercase query string

        Returns:
            Subject ID or None
        """
        # Check each subject's core topics
        subject_scores = {}

        for subject, boundaries in SUBJECT_BOUNDARIES.items():
            if subject == "general":
                continue

            score = 0
            for topic in boundaries.get("core_topics", []):
                if topic.lower() in query_lower:
                    score += 1

            if score > 0:
                subject_scores[subject] = score

        if subject_scores:
            return max(subject_scores, key=subject_scores.get)

        return None

    def _llm_classify(
        self,
        query: str,
        subject: str,
        boundaries: Dict,
    ) -> GuardrailResponse:
        """
        Use LLM to classify query relevance (sync version).
        This is a placeholder - actual implementation would be async.
        """
        # For sync context, fall back to keyword matching
        return GuardrailResponse(
            result=GuardrailResult.ALLOWED,
            confidence=0.5
        )

    async def _llm_classify_async(
        self,
        query: str,
        subject: str,
    ) -> GuardrailResponse:
        """
        Use LLM to classify query relevance to subject.

        Args:
            query: The user's query
            subject: The selected subject

        Returns:
            GuardrailResponse based on LLM classification
        """
        if not self.llm_service:
            return GuardrailResponse(
                result=GuardrailResult.ALLOWED,
                confidence=0.5
            )

        boundaries = SUBJECT_BOUNDARIES.get(subject, {})
        core_topics = ", ".join(boundaries.get("core_topics", [])[:10])

        classification_prompt = f"""You are a subject relevance classifier. Determine if the user's question is related to {subject}.

Core topics for {subject}: {core_topics}

User's question: "{query}"

Respond with ONLY one of these options:
- ALLOWED: The question is clearly about {subject}
- TANGENT: The question is indirectly related (a cross-subject connection)
- BLOCKED: The question is completely unrelated to {subject}

Also provide a confidence score (0.0 to 1.0) and if BLOCKED, suggest a better subject.

Format: RESULT|CONFIDENCE|SUGGESTED_SUBJECT (or NONE)
Example: ALLOWED|0.95|NONE
Example: BLOCKED|0.85|physics"""

        try:
            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": classification_prompt}],
                system_prompt="You are a precise classifier. Respond only in the specified format.",
                max_tokens=50
            )

            # Parse response
            parts = response.strip().split("|")
            if len(parts) >= 2:
                result_str = parts[0].strip().upper()
                confidence = float(parts[1]) if len(parts) > 1 else 0.7
                suggested = parts[2].strip() if len(parts) > 2 and parts[2].strip() != "NONE" else None

                if result_str == "ALLOWED":
                    result = GuardrailResult.ALLOWED
                elif result_str == "TANGENT":
                    result = GuardrailResult.TANGENT
                else:
                    result = GuardrailResult.BLOCKED

                return GuardrailResponse(
                    result=result,
                    message=boundaries.get("redirect_message") if result == GuardrailResult.BLOCKED else None,
                    suggested_subject=suggested,
                    confidence=confidence
                )
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")

        # Default to allowing on LLM failure
        return GuardrailResponse(
            result=GuardrailResult.ALLOWED,
            confidence=0.5
        )

    def get_redirection_response(
        self,
        guardrail_response: GuardrailResponse,
        subject: str,
        query: str,
    ) -> str:
        """
        Generate a friendly redirection message for blocked queries.

        Args:
            guardrail_response: The guardrail check result
            subject: The current subject
            query: The original query

        Returns:
            User-friendly redirection message
        """
        boundaries = SUBJECT_BOUNDARIES.get(subject, {})
        base_message = guardrail_response.message or boundaries.get("redirect_message", "")

        if not base_message:
            base_message = f"That question doesn't seem to be about {subject}."

        # Add suggestion if available
        if guardrail_response.suggested_subject:
            suggested_name = guardrail_response.suggested_subject.replace("_", " ").title()
            base_message += f"\n\nThis might be a great question for the **{suggested_name}** channel!"

        return base_message


# Singleton instance
_guardrail_service: Optional[GuardrailService] = None


def get_guardrail_service(llm_service=None) -> GuardrailService:
    """Get or create the guardrail service singleton."""
    global _guardrail_service
    if _guardrail_service is None:
        _guardrail_service = GuardrailService(llm_service)
    elif llm_service and not _guardrail_service.llm_service:
        _guardrail_service.llm_service = llm_service
    return _guardrail_service
