"""
Intent Extractor

Extracts structured query plans from natural language questions.
"""

from typing import Dict, List, Optional

from src.llm.client import get_llm_client, create_messages
from src.llm.prompts import load_prompt
from src.planner.query_plan import IntentExtraction, QueryPlan
from src.semantic.loader import get_semantic_layer

# Phase 2: AI Synonyms integration
try:
    from src.semantic.ai_synonyms import get_synonym_engine
    from src.semantic.search_index import get_search_index
    AI_SYNONYMS_AVAILABLE = True
except ImportError:
    AI_SYNONYMS_AVAILABLE = False


class IntentExtractor:
    """Extracts query intent from natural language using LLM."""

    def __init__(self, semantic_layer=None, use_ai_synonyms: bool = True) -> None:
        """Initialize intent extractor."""
        with open('/tmp/intent_debug.txt', 'a') as f:
            f.write(f"\n=== IntentExtractor.__init__ called\n")
        
        try:
            self.llm = get_llm_client()
            with open('/tmp/intent_debug.txt', 'a') as f:
                f.write(f"✓ LLM client obtained\n")
        except Exception as e:
            with open('/tmp/intent_debug.txt', 'a') as f:
                import traceback
                f.write(f"✗ LLM client failed: {type(e).__name__}: {str(e)}\n")
                f.write(f"{traceback.format_exc()}\n")
            raise
        
        # Use provided semantic layer or fallback to global one
        self.semantic_layer = semantic_layer if semantic_layer is not None else get_semantic_layer()
        
        # Phase 2: Initialize AI synonym engine if available
        self.use_ai_synonyms = use_ai_synonyms and AI_SYNONYMS_AVAILABLE
        if self.use_ai_synonyms:
            self.synonym_engine = get_synonym_engine()
            self.search_index = get_search_index()
            self._initialize_ai_synonyms()
    
    def _initialize_ai_synonyms(self):
        """Initialize AI synonym engine with semantic layer data"""
        try:
            # Load official synonyms into the engine
            for metric_name, metric in self.semantic_layer.metrics.items():
                self.synonym_engine.load_official_synonyms(
                    metric_name,
                    metric.synonyms
                )
            
            # Build search index
            self.search_index.build_index_from_semantic_layer(self.semantic_layer)
        except Exception as e:
            print(f"Warning: Could not initialize AI synonyms: {e}")
            self.use_ai_synonyms = False

    def extract(self, question: str, user_context: Optional[Dict] = None) -> IntentExtraction:
        """
        Extract query plan from natural language question.

        Args:
            question: User's natural language question
            user_context: Optional user context for synonym learning

        Returns:
            IntentExtraction with structured query plan

        Raises:
            ValueError: If LLM fails to generate valid plan
        """
        with open('/tmp/intent_debug.txt', 'a') as f:
            f.write(f"\n===\nextract() called with: {question}\n")
        
        # Phase 2: Try AI synonym suggestions first if enabled
        ai_suggestions = None
        if self.use_ai_synonyms:
            ai_suggestions = self._get_ai_suggestions(question)
        
        # Build context about available metrics and dimensions
        context = self._build_semantic_context(ai_suggestions)

        # Load the intent extraction prompt
        system_prompt = load_prompt("intent-extraction")

        # Create messages
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Available context:\n{context}\n\nUser question: {question}",
            },
        ]

        # Get structured response
        try:
            with open('/tmp/intent_debug.txt', 'a') as f:
                f.write("About to call llm.complete_structured\n")
            result = self.llm.complete_structured(
                messages=messages, model_class=IntentExtraction, temperature=0.1
            )
            with open('/tmp/intent_debug.txt', 'a') as f:
                f.write("complete_structured returned successfully\n")
            
            # Phase 2: Store AI suggestions in result for feedback collection
            if ai_suggestions and hasattr(result, '_ai_suggestions'):
                result._ai_suggestions = ai_suggestions
            
            return result
        except Exception as e:
            with open('/tmp/intent_debug.txt', 'a') as f:
                import traceback
                f.write(f"EXCEPTION in complete_structured!\n")
                f.write(f"Type: {type(e).__name__}\n")
                f.write(f"Message: {str(e)}\n")
                f.write(f"Traceback:\n{traceback.format_exc()}\n")
            raise ValueError(f"Failed to extract intent from question: {question}") from e
    
    def _get_ai_suggestions(self, question: str) -> Optional[List[Dict]]:
        """Get AI-powered synonym suggestions for the question"""
        try:
            # Use semantic search to find relevant terms
            search_results = self.search_index.search(
                query=question,
                top_k=5,
                min_relevance=0.6
            )
            
            suggestions = []
            for result in search_results:
                suggestions.append({
                    'term': result.name,
                    'type': result.type,
                    'matched_text': result.matched_term,
                    'relevance': result.relevance_score
                })
            
            return suggestions if suggestions else None
        except Exception as e:
            print(f"Warning: AI synonym suggestion failed: {e}")
            return None

    def _build_semantic_context(self, ai_suggestions: Optional[List[Dict]] = None) -> str:
        """Build context about semantic layer for the LLM."""
        lines = ["# Semantic Layer Context\n"]
        
        # Phase 2: Add AI suggestions at the top if available
        if ai_suggestions:
            lines.append("## AI-Suggested Relevant Terms:")
            for suggestion in ai_suggestions:
                lines.append(
                    f"- **{suggestion['term']}** ({suggestion['type']}) - "
                    f"matched '{suggestion['matched_text']}' "
                    f"(relevance: {suggestion['relevance']:.2f})"
                )
            lines.append("")

        # Metrics
        lines.append("## Available Metrics:")
        for metric in self.semantic_layer.metrics.values():
            lines.append(f"- **{metric.name}**: {metric.description}")
            if metric.synonyms:
                lines.append(f"  Synonyms: {', '.join(metric.synonyms)}")

        lines.append("")

        # Dimensions
        lines.append("## Available Dimensions:")
        for dimension in self.semantic_layer.dimensions.values():
            lines.append(f"- **{dimension.name}**: {dimension.description}")
            if dimension.synonyms:
                lines.append(f"  Synonyms: {', '.join(dimension.synonyms)}")

        return "\n".join(lines)


def extract_intent(question: str) -> IntentExtraction:
    """
    Extract query plan from natural language question.

    Args:
        question: User's question

    Returns:
        IntentExtraction with query plan
    """
    extractor = IntentExtractor()
    return extractor.extract(question)


# Singleton instance
_intent_extractor_instance = None


def get_intent_extractor() -> IntentExtractor:
    """
    Get or create the global IntentExtractor instance.

    Returns:
        IntentExtractor: Singleton instance
    """
    global _intent_extractor_instance
    if _intent_extractor_instance is None:
        _intent_extractor_instance = IntentExtractor()
    return _intent_extractor_instance
