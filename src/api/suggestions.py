"""
Query Suggestions API

Provides intelligent query suggestions using LLM based on:
- Current database connection
- Available metrics and dimensions
- User's partial input
- Query patterns and examples
- User activity and learned patterns (personalized)
- Role-based preferences
"""

import os
import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from openai import OpenAI

from src.activity.logger import get_activity_logger
from src.activity.analyzer import get_pattern_analyzer

logger = logging.getLogger(__name__)

# Initialize OpenAI client (uses OPENAI_API_KEY env var)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_personalized_suggestions(
    partial_query: str,
    metrics: List[Dict],
    dimensions: List[Dict],
    connection_name: str,
    user_id: str,
    user_role: Optional[str] = None,
    max_suggestions: int = 6
) -> Dict[str, any]:
    """
    Generate personalized query suggestions using learned patterns + LLM.
    
    Args:
        partial_query: User's current input text
        metrics: Available metrics from semantic layer
        dimensions: Available dimensions from semantic layer
        connection_name: Name of the database connection
        user_id: User identifier for personalization
        user_role: User's role for role-based suggestions
        max_suggestions: Maximum number of suggestions to return
        
    Returns:
        Dict with suggestions, source, and learned patterns
    """
    try:
        analyzer = get_pattern_analyzer()
        
        # Check cache first
        cached = _get_cached_suggestions(user_id, partial_query, user_role)
        if cached:
            logger.info(f"[Suggestions] Returning cached suggestions for {user_id}")
            return {
                "suggestions": cached,
                "source": "cached",
                "user_patterns": [],
                "role_patterns": []
            }
        
        # Get learned patterns
        user_patterns = analyzer.get_user_patterns(user_id, limit=5)
        role_patterns = analyzer.get_role_patterns(user_role, limit=5) if user_role else []
        user_prefs = analyzer.get_or_create_user_preferences(user_id)
        
        # Generate suggestions using patterns + LLM
        suggestions = _generate_with_patterns(
            partial_query=partial_query,
            metrics=metrics,
            dimensions=dimensions,
            connection_name=connection_name,
            user_patterns=user_patterns,
            role_patterns=role_patterns,
            user_prefs=user_prefs,
            max_suggestions=max_suggestions
        )
        
        # Cache the results
        _cache_suggestions(user_id, partial_query, user_role, suggestions)
        
        return {
            "suggestions": suggestions,
            "source": "llm_with_patterns",
            "user_patterns": [p.query_template for p in user_patterns[:3]],
            "role_patterns": [p.query_template for p in role_patterns[:3]]
        }
        
    except Exception as e:
        logger.error(f"[Suggestions] Failed to generate personalized suggestions: {e}")
        # Fallback to basic LLM suggestions
        return {
            "suggestions": generate_query_suggestions(
                partial_query, metrics, dimensions, connection_name, max_suggestions
            ),
            "source": "llm_fallback",
            "user_patterns": [],
            "role_patterns": []
        }


def generate_query_suggestions(
    partial_query: str,
    metrics: List[Dict],
    dimensions: List[Dict],
    connection_name: str,
    max_suggestions: int = 6
) -> List[Dict[str, str]]:
    """
    Generate intelligent query suggestions using LLM (non-personalized).
    
    Args:
        partial_query: User's current input text
        metrics: Available metrics from semantic layer
        dimensions: Available dimensions from semantic layer
        connection_name: Name of the database connection
        max_suggestions: Maximum number of suggestions to return
        
    Returns:
        List of suggestion dictionaries with 'text', 'type', and 'description'
    """
    
    # Limit to top metrics/dimensions for cost efficiency
    top_metrics = metrics[:20]  # First 20 metrics
    top_dimensions = dimensions[:15]  # First 15 dimensions
    
    # Build a concise prompt
    metrics_str = ", ".join([m.get("name", m.get("display_name", "")) for m in top_metrics])
    dimensions_str = ", ".join([d.get("name", d.get("display_name", "")) for d in top_dimensions])
    
    # Use affordable GPT-4o-mini for suggestions
    prompt = f"""You are a SQL query assistant. Generate {max_suggestions} natural language query suggestions.

Database: {connection_name}
Available Metrics: {metrics_str}
Available Dimensions: {dimensions_str}

User Input: "{partial_query}"

Generate {max_suggestions} complete query suggestions that:
1. Use available metrics and dimensions
2. Complete or extend the user's input naturally
3. Are diverse (comparisons, rankings, trends, aggregations)
4. Are short and actionable (under 15 words)

Return ONLY a JSON object with this exact format:
{{"suggestions": [{{"text": "query text", "type": "complete|metric|dimension|filter", "description": "what it shows"}}]}}

Examples of good suggestions:
- "Top 10 stocks by recommendation mark"
- "Average volume by sector"
- "Compare high and low prices by name"
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Most affordable option ~$0.15/$0.60 per 1M tokens
            messages=[
                {"role": "system", "content": "You are a helpful SQL query assistant. Always return valid JSON objects with a 'suggestions' array."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400,  # Limit tokens for cost control
            response_format={"type": "json_object"}
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        
        # Handle different response formats
        if isinstance(result, dict) and "suggestions" in result:
            suggestions = result["suggestions"]
        elif isinstance(result, list):
            suggestions = result
        elif isinstance(result, dict) and "queries" in result:
            suggestions = result["queries"]
        else:
            suggestions = []
            
        # Validate and normalize suggestions
        normalized = []
        for i, sug in enumerate(suggestions[:max_suggestions]):
            if isinstance(sug, dict) and "text" in sug:
                normalized.append({
                    "text": sug.get("text", ""),
                    "type": sug.get("type", "complete"),
                    "description": sug.get("description", "Query suggestion"),
                    "icon": _get_icon_for_type(sug.get("type", "complete"))
                })
            elif isinstance(sug, str):
                # If it's just a string, create a proper suggestion object
                normalized.append({
                    "text": sug,
                    "type": "complete",
                    "description": "Query suggestion",
                    "icon": "💬"
                })
        
        return normalized if normalized else _get_fallback_suggestions(metrics, dimensions)
        
    except Exception as e:
        print(f"[Suggestions] LLM error: {e}")
        # Return fallback rule-based suggestions
        return _get_fallback_suggestions(metrics, dimensions)


def _get_icon_for_type(suggestion_type: str) -> str:
    """Get emoji icon for suggestion type."""
    icons = {
        "complete": "💬",
        "metric": "📊",
        "dimension": "🏷️",
        "filter": "📆",
        "comparison": "⚖️",
        "ranking": "🏆",
        "trend": "📈",
        "aggregation": "🔢"
    }
    return icons.get(suggestion_type, "💬")


def _get_fallback_suggestions(metrics: List[Dict], dimensions: List[Dict]) -> List[Dict[str, str]]:
    """
    Generate rule-based fallback suggestions when LLM fails.
    
    Args:
        metrics: Available metrics
        dimensions: Available dimensions
        
    Returns:
        List of basic suggestions
    """
    suggestions = []
    
    # Take first few metrics and dimensions
    top_metrics = metrics[:3]
    top_dims = dimensions[:3]
    
    # Generate patterns
    if top_metrics and top_dims:
        metric = top_metrics[0].get("name", top_metrics[0].get("display_name", "value"))
        dim = top_dims[0].get("name", top_dims[0].get("display_name", "category"))
        
        suggestions.extend([
            {
                "text": f"Top 10 {dim} by {metric}",
                "type": "ranking",
                "description": "Show highest values",
                "icon": "🏆"
            },
            {
                "text": f"Total {metric} by {dim}",
                "type": "aggregation",
                "description": "Sum by category",
                "icon": "🔢"
            },
            {
                "text": f"Compare {metric} across {dim}",
                "type": "comparison",
                "description": "Side-by-side comparison",
                "icon": "⚖️"
            }
        ])
    
    # Add generic time-based suggestions
    if any("date" in m.get("name", "").lower() or "time" in m.get("name", "").lower() 
           for m in dimensions):
        suggestions.append({
            "text": "Show trends over time",
            "type": "trend",
            "description": "Time series analysis",
            "icon": "📈"
        })
    
    # Add filter suggestions
    suggestions.extend([
        {
            "text": "Last 30 days",
            "type": "filter",
            "description": "Time filter",
            "icon": "📆"
        },
        {
            "text": "Top 5 results",
            "type": "filter",
            "description": "Limit results",
            "icon": "🔟"
        }
    ])
    
    return suggestions[:6]


def generate_autocomplete_suggestions(
    partial_query: str,
    metrics: List[Dict],
    dimensions: List[Dict]
) -> List[Dict[str, str]]:
    """
    Generate quick autocomplete suggestions for typing (no LLM call).
    
    Used for immediate feedback as user types. Returns simple completions
    based on matching metric/dimension names.
    
    Args:
        partial_query: Current input text
        metrics: Available metrics
        dimensions: Available dimensions
        
    Returns:
        List of quick suggestions
    """
    suggestions = []
    query_lower = partial_query.lower()
    
    # Find matching metrics
    for metric in metrics[:30]:  # Check first 30
        name = metric.get("name", metric.get("display_name", ""))
        if name.lower().startswith(query_lower) or query_lower in name.lower():
            suggestions.append({
                "text": name,
                "type": "metric",
                "description": metric.get("description", "Metric"),
                "icon": "📊"
            })
            if len(suggestions) >= 3:
                break
    
    # Find matching dimensions
    for dim in dimensions[:30]:
        name = dim.get("name", dim.get("display_name", ""))
        if name.lower().startswith(query_lower) or query_lower in name.lower():
            suggestions.append({
                "text": f"by {name}",
                "type": "dimension",
                "description": dim.get("description", "Dimension"),
                "icon": "🏷️"
            })
            if len(suggestions) >= 5:
                break
    
    return suggestions[:6]


# ============================================================================
# PERSONALIZATION HELPERS
# ============================================================================

def _generate_with_patterns(
    partial_query: str,
    metrics: List[Dict],
    dimensions: List[Dict],
    connection_name: str,
    user_patterns: List,
    role_patterns: List,
    user_prefs,
    max_suggestions: int = 6
) -> List[Dict[str, str]]:
    """Generate suggestions enriched with learned patterns."""
    
    # Build context from patterns
    pattern_context = ""
    if user_patterns:
        user_templates = [p.query_template for p in user_patterns[:3]]
        pattern_context += f"\n\nUser's common queries:\n- " + "\n- ".join(user_templates)
    
    if role_patterns:
        role_templates = [p.query_template for p in role_patterns[:3]]
        pattern_context += f"\n\nCommon role queries:\n- " + "\n- ".join(role_templates)
    
    # Apply preferences
    filtered_metrics = metrics
    filtered_dimensions = dimensions
    
    if user_prefs.preferred_metrics:
        # Prioritize preferred metrics
        preferred = [m for m in metrics if m.get("name") in user_prefs.preferred_metrics]
        others = [m for m in metrics if m.get("name") not in user_prefs.preferred_metrics]
        filtered_metrics = preferred + others
    
    if user_prefs.excluded_metrics:
        # Remove excluded metrics
        filtered_metrics = [m for m in filtered_metrics if m.get("name") not in user_prefs.excluded_metrics]
    
    # Limit for cost efficiency
    top_metrics = filtered_metrics[:20]
    top_dimensions = filtered_dimensions[:15]
    
    metrics_str = ", ".join([m.get("name", m.get("display_name", "")) for m in top_metrics])
    dimensions_str = ", ".join([d.get("name", d.get("display_name", "")) for d in top_dimensions])
    
    prompt = f"""You are a SQL query assistant. Generate {max_suggestions} personalized natural language query suggestions.

Database: {connection_name}
Available Metrics: {metrics_str}
Available Dimensions: {dimensions_str}
{pattern_context}

User Input: "{partial_query}"

Generate {max_suggestions} complete query suggestions that:
1. Use available metrics and dimensions
2. Align with user's common query patterns when relevant
3. Complete or extend the user's input naturally
4. Are diverse (comparisons, rankings, trends, aggregations)
5. Are short and actionable (under 15 words)

Return ONLY a JSON object with this exact format:
{{"suggestions": [{{"text": "query text", "type": "complete|metric|dimension|filter", "description": "what it shows"}}]}}

Examples of good suggestions:
- "Top 10 stocks by recommendation mark"
- "Average volume by sector"
- "Compare high and low prices by name"
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful SQL query assistant that personalizes suggestions based on user history. Always return valid JSON objects with a 'suggestions' array."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Handle different response formats
        if isinstance(result, dict) and "suggestions" in result:
            suggestions = result["suggestions"]
        elif isinstance(result, list):
            suggestions = result
        else:
            suggestions = []
        
        # Normalize
        normalized = []
        for sug in suggestions[:max_suggestions]:
            if isinstance(sug, dict) and "text" in sug:
                normalized.append({
                    "text": sug.get("text", ""),
                    "type": sug.get("type", "complete"),
                    "description": sug.get("description", "Query suggestion"),
                    "icon": _get_icon_for_type(sug.get("type", "complete"))
                })
        
        return normalized if normalized else _get_fallback_suggestions(metrics, dimensions)
        
    except Exception as e:
        logger.error(f"[Suggestions] LLM error with patterns: {e}")
        return _get_fallback_suggestions(metrics, dimensions)


def _get_cached_suggestions(user_id: str, partial_query: str, role: Optional[str]) -> Optional[List[Dict]]:
    """Check if we have cached suggestions for this context."""
    try:
        from src.database.internal_db import InternalDB
        
        # Generate context hash
        context = f"{user_id}:{role}:{partial_query.lower().strip()}"
        context_hash = hashlib.md5(context.encode()).hexdigest()
        
        query = """
            SELECT suggestions, hit_count
            FROM suggestion_cache
            WHERE user_id = %s AND context_hash = %s
            AND expires_at > CURRENT_TIMESTAMP
            ORDER BY generated_at DESC
            LIMIT 1
        """
        result = InternalDB.execute_query(query, (user_id, context_hash))
        
        if result.rows:
            suggestions = json.loads(result.rows[0][0])
            
            # Update hit count
            InternalDB.execute_query(
                "UPDATE suggestion_cache SET hit_count = hit_count + 1 WHERE user_id = %s AND context_hash = %s",
                (user_id, context_hash)
            )
            
            return suggestions
        
        return None
        
    except Exception as e:
        logger.error(f"[Suggestions] Cache lookup failed: {e}")
        return None


def _cache_suggestions(user_id: str, partial_query: str, role: Optional[str], suggestions: List[Dict]):
    """Cache generated suggestions."""
    try:
        from src.database.internal_db import InternalDB
        
        # Generate context hash
        context = f"{user_id}:{role}:{partial_query.lower().strip()}"
        context_hash = hashlib.md5(context.encode()).hexdigest()
        
        # Clean old entries first
        InternalDB.execute_query(
            "DELETE FROM suggestion_cache WHERE expires_at < CURRENT_TIMESTAMP"
        )
        
        # Insert new cache entry
        query = """
            INSERT INTO suggestion_cache (user_id, context_hash, suggestions)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
        """
        InternalDB.execute_query(query, (user_id, context_hash, json.dumps(suggestions)))
        
    except Exception as e:
        logger.error(f"[Suggestions] Cache insert failed: {e}")
