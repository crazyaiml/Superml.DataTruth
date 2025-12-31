"""
Pattern Analyzer

Analyzes user activity to identify query patterns for personalized suggestions.
"""

import logging
import json
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import Counter
import re

from src.activity.models import QueryPattern, SuggestionPreferences
from src.database.internal_db import InternalDB

logger = logging.getLogger(__name__)

_pattern_analyzer = None


class PatternAnalyzer:
    """Analyzes user activity to learn query patterns."""
    
    def __init__(self):
        """Initialize pattern analyzer."""
        pass
    
    def analyze_and_update_patterns(self, user_id: Optional[str] = None, role: Optional[str] = None):
        """
        Analyze recent activity and update query patterns.
        
        Args:
            user_id: Specific user to analyze, or None for all users
            role: Specific role to analyze, or None for all roles
        """
        try:
            # Get recent queries
            query = """
                SELECT user_id, query_text, response_data, metadata
                FROM user_activity
                WHERE activity_type = 'query'
                AND created_at >= NOW() - INTERVAL '30 days'
            """
            params = []
            
            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
            
            if role:
                query += " AND metadata->>'role' = %s"
                params.append(role)
            
            result = InternalDB.execute_query(query, tuple(params) if params else None)
            
            # Handle both list and object with .rows attribute
            rows = result.rows if hasattr(result, 'rows') else result
            
            # Group queries by user and role
            user_queries: Dict[str, List] = {}
            role_queries: Dict[str, List] = {}
            
            for row in rows:
                # Handle both dict and tuple/list row formats
                if isinstance(row, dict):
                    uid = row['user_id']
                    query_text = row['query_text']
                    response_data = json.loads(row['response_data']) if row.get('response_data') else {}
                    metadata = json.loads(row['metadata']) if row.get('metadata') else {}
                else:
                    uid = row[0]
                    query_text = row[1]
                    response_data = json.loads(row[2]) if row[2] else {}
                    metadata = json.loads(row[3]) if row[3] else {}
                
                user_role = metadata.get('role', 'unknown')
                
                # Track per user
                if uid not in user_queries:
                    user_queries[uid] = []
                user_queries[uid].append({
                    'query': query_text,
                    'response': response_data,
                    'metadata': metadata
                })
                
                # Track per role
                if user_role not in role_queries:
                    role_queries[user_role] = []
                role_queries[user_role].append({
                    'query': query_text,
                    'response': response_data,
                    'metadata': metadata
                })
            
            # Analyze patterns for each user
            for uid, queries in user_queries.items():
                self._update_user_patterns(uid, queries)
            
            # Analyze patterns for each role
            for user_role, queries in role_queries.items():
                self._update_role_patterns(user_role, queries)
            
            logger.info(f"✓ Updated patterns for {len(user_queries)} users and {len(role_queries)} roles")
            
        except Exception as e:
            logger.error(f"Failed to analyze patterns: {e}")
    
    def _update_user_patterns(self, user_id: str, queries: List[Dict]):
        """Update patterns for a specific user."""
        try:
            # Extract templates from queries
            templates = self._extract_templates(queries)
            
            # Update or insert patterns
            for template, stats in templates.items():
                self._upsert_pattern(
                    pattern_type='user_specific',
                    target_id=user_id,
                    query_template=template,
                    frequency=stats['frequency'],
                    success_rate=stats['success_rate'],
                    avg_response_time=stats['avg_response_time'],
                    metadata=stats['metadata']
                )
            
        except Exception as e:
            logger.error(f"Failed to update user patterns for {user_id}: {e}")
    
    def _update_role_patterns(self, role: str, queries: List[Dict]):
        """Update patterns for a specific role."""
        try:
            # Extract templates from queries
            templates = self._extract_templates(queries)
            
            # Update or insert patterns
            for template, stats in templates.items():
                self._upsert_pattern(
                    pattern_type='role_based',
                    target_id=role,
                    query_template=template,
                    frequency=stats['frequency'],
                    success_rate=stats['success_rate'],
                    avg_response_time=stats['avg_response_time'],
                    metadata=stats['metadata']
                )
            
        except Exception as e:
            logger.error(f"Failed to update role patterns for {role}: {e}")
    
    def _extract_templates(self, queries: List[Dict]) -> Dict[str, Dict]:
        """
        Extract query templates from actual queries.
        
        Returns dict of {template: stats}
        """
        templates = {}
        
        for q in queries:
            query_text = q['query'].lower().strip()
            response = q.get('response', {})
            metadata = q.get('metadata', {})
            
            # Generalize the query to create a template
            template = self._generalize_query(query_text)
            
            if template not in templates:
                templates[template] = {
                    'frequency': 0,
                    'success_count': 0,
                    'total_time': 0.0,
                    'time_count': 0,
                    'metadata': {
                        'metrics_used': [],
                        'dimensions_used': [],
                        'filters_used': []
                    }
                }
            
            templates[template]['frequency'] += 1
            
            # Track success
            if response.get('data'):
                templates[template]['success_count'] += 1
            
            # Track response time
            exec_time = metadata.get('execution_time')
            if exec_time:
                templates[template]['total_time'] += float(exec_time)
                templates[template]['time_count'] += 1
        
        # Calculate rates and averages
        for template, stats in templates.items():
            stats['success_rate'] = stats['success_count'] / stats['frequency'] if stats['frequency'] > 0 else 0
            stats['avg_response_time'] = stats['total_time'] / stats['time_count'] if stats['time_count'] > 0 else None
        
        return templates
    
    def _generalize_query(self, query_text: str) -> str:
        """
        Convert specific query to generalized template.
        
        Examples:
        - "top 10 stocks by volume" -> "top {N} {entity} by {metric}"
        - "show me profit for Q1 2024" -> "show me {metric} for {timeframe}"
        """
        # Replace numbers with {N}
        template = re.sub(r'\b\d+\b', '{N}', query_text)
        
        # Replace specific years with {year}
        template = re.sub(r'\b20\d{2}\b', '{year}', template)
        
        # Replace quarter references
        template = re.sub(r'\bq[1-4]\b', '{quarter}', template, flags=re.IGNORECASE)
        
        # Replace months
        months = ['january', 'february', 'march', 'april', 'may', 'june',
                  'july', 'august', 'september', 'october', 'november', 'december',
                  'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        for month in months:
            template = re.sub(rf'\b{month}\b', '{month}', template, flags=re.IGNORECASE)
        
        return template.strip()
    
    def _upsert_pattern(
        self,
        pattern_type: str,
        target_id: str,
        query_template: str,
        frequency: int,
        success_rate: float,
        avg_response_time: Optional[float],
        metadata: Dict
    ):
        """Insert or update a query pattern."""
        try:
            # Check if pattern exists
            check_query = """
                SELECT id, frequency FROM query_patterns
                WHERE pattern_type = %s AND target_id = %s AND query_template = %s
            """
            result = InternalDB.execute_query(check_query, (pattern_type, target_id, query_template))
            
            if result.rows:
                # Update existing pattern
                pattern_id = result.rows[0][0]
                old_frequency = result.rows[0][1]
                new_frequency = old_frequency + frequency
                
                update_query = """
                    UPDATE query_patterns
                    SET frequency = %s,
                        success_rate = %s,
                        avg_response_time = %s,
                        last_used = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP,
                        metadata = %s
                    WHERE id = %s
                """
                InternalDB.execute_query(
                    update_query,
                    (new_frequency, success_rate, avg_response_time, json.dumps(metadata), pattern_id)
                )
            else:
                # Insert new pattern
                insert_query = """
                    INSERT INTO query_patterns
                    (pattern_type, target_id, query_template, frequency, success_rate, 
                     avg_response_time, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                InternalDB.execute_query(
                    insert_query,
                    (pattern_type, target_id, query_template, frequency, success_rate,
                     avg_response_time, json.dumps(metadata))
                )
        
        except Exception as e:
            logger.error(f"Failed to upsert pattern: {e}")
    
    def get_user_patterns(self, user_id: str, limit: int = 10) -> List[QueryPattern]:
        """Get top patterns for a user."""
        try:
            query = """
                SELECT id, pattern_type, target_id, query_template, frequency,
                       success_rate, avg_response_time, last_used, metadata,
                       created_at, updated_at
                FROM query_patterns
                WHERE pattern_type = 'user_specific' AND target_id = %s
                ORDER BY frequency DESC, success_rate DESC
                LIMIT %s
            """
            result = InternalDB.execute_query(query, (user_id, limit))
            
            patterns = []
            for row in result.rows:
                metadata = json.loads(row[8]) if row[8] else {}
                patterns.append(QueryPattern(
                    id=row[0],
                    pattern_type=row[1],
                    target_id=row[2],
                    query_template=row[3],
                    frequency=row[4],
                    success_rate=row[5],
                    avg_response_time=row[6],
                    last_used=row[7],
                    metadata=metadata,
                    created_at=row[9],
                    updated_at=row[10]
                ))
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to get user patterns: {e}")
            return []
    
    def get_role_patterns(self, role: str, limit: int = 10) -> List[QueryPattern]:
        """Get top patterns for a role."""
        try:
            query = """
                SELECT id, pattern_type, target_id, query_template, frequency,
                       success_rate, avg_response_time, last_used, metadata,
                       created_at, updated_at
                FROM query_patterns
                WHERE pattern_type = 'role_based' AND target_id = %s
                ORDER BY frequency DESC, success_rate DESC
                LIMIT %s
            """
            result = InternalDB.execute_query(query, (role, limit))
            
            patterns = []
            for row in result.rows:
                metadata = json.loads(row[8]) if row[8] else {}
                patterns.append(QueryPattern(
                    id=row[0],
                    pattern_type=row[1],
                    target_id=row[2],
                    query_template=row[3],
                    frequency=row[4],
                    success_rate=row[5],
                    avg_response_time=row[6],
                    last_used=row[7],
                    metadata=metadata,
                    created_at=row[9],
                    updated_at=row[10]
                ))
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to get role patterns: {e}")
            return []
    
    def get_or_create_user_preferences(self, user_id: str) -> SuggestionPreferences:
        """Get user's suggestion preferences or create defaults."""
        try:
            query = """
                SELECT user_id, preferred_query_types, excluded_metrics,
                       preferred_metrics, preferred_dimensions, show_advanced_queries,
                       max_suggestions, updated_at
                FROM user_suggestion_preferences
                WHERE user_id = %s
            """
            result = InternalDB.execute_query(query, (user_id,))
            
            if result.rows:
                row = result.rows[0]
                return SuggestionPreferences(
                    user_id=row[0],
                    preferred_query_types=json.loads(row[1]) if row[1] else [],
                    excluded_metrics=json.loads(row[2]) if row[2] else [],
                    preferred_metrics=json.loads(row[3]) if row[3] else [],
                    preferred_dimensions=json.loads(row[4]) if row[4] else [],
                    show_advanced_queries=row[5],
                    max_suggestions=row[6],
                    updated_at=row[7]
                )
            else:
                # Create default preferences
                defaults = SuggestionPreferences(user_id=user_id)
                self._create_user_preferences(defaults)
                return defaults
                
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return SuggestionPreferences(user_id=user_id)
    
    def _create_user_preferences(self, prefs: SuggestionPreferences):
        """Create default user preferences."""
        try:
            query = """
                INSERT INTO user_suggestion_preferences
                (user_id, preferred_query_types, excluded_metrics, preferred_metrics,
                 preferred_dimensions, show_advanced_queries, max_suggestions)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            """
            InternalDB.execute_query(
                query,
                (
                    prefs.user_id,
                    json.dumps(prefs.preferred_query_types),
                    json.dumps(prefs.excluded_metrics),
                    json.dumps(prefs.preferred_metrics),
                    json.dumps(prefs.preferred_dimensions),
                    prefs.show_advanced_queries,
                    prefs.max_suggestions
                )
            )
        except Exception as e:
            logger.error(f"Failed to create user preferences: {e}")
    
    def update_user_preferences(self, prefs: SuggestionPreferences):
        """Update user's suggestion preferences."""
        try:
            query = """
                UPDATE user_suggestion_preferences
                SET preferred_query_types = %s,
                    excluded_metrics = %s,
                    preferred_metrics = %s,
                    preferred_dimensions = %s,
                    show_advanced_queries = %s,
                    max_suggestions = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """
            InternalDB.execute_query(
                query,
                (
                    json.dumps(prefs.preferred_query_types),
                    json.dumps(prefs.excluded_metrics),
                    json.dumps(prefs.preferred_metrics),
                    json.dumps(prefs.preferred_dimensions),
                    prefs.show_advanced_queries,
                    prefs.max_suggestions,
                    prefs.user_id
                )
            )
            logger.info(f"✓ Updated preferences for user {prefs.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to update user preferences: {e}")


def get_pattern_analyzer() -> PatternAnalyzer:
    """Get or create singleton PatternAnalyzer instance."""
    global _pattern_analyzer
    if _pattern_analyzer is None:
        _pattern_analyzer = PatternAnalyzer()
    return _pattern_analyzer
