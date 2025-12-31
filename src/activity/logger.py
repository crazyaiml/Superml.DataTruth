"""
Activity Logger

Logs user activities to database for learning and personalization.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.activity.models import (
    ActivityType, UserActivity, LogActivityRequest
)
from src.database.internal_db import InternalDB

logger = logging.getLogger(__name__)

_activity_logger = None


class ActivityLogger:
    """Logs user activity for personalized suggestions."""
    
    def __init__(self):
        """Initialize activity logger and ensure tables exist."""
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure activity tracking tables exist."""
        try:
            # Tables should be created by migration 004
            # Just verify they exist
            result = InternalDB.execute_query("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('user_activity', 'query_patterns', 'suggestion_cache', 'user_suggestion_preferences')
            """)
            
            # Handle both list and object with .rows attribute
            rows = result.rows if hasattr(result, 'rows') else result
            existing_tables = {row[0] if isinstance(row, (list, tuple)) else row['table_name'] for row in rows}
            expected_tables = {'user_activity', 'query_patterns', 'suggestion_cache', 'user_suggestion_preferences'}
            missing = expected_tables - existing_tables
            
            if missing:
                logger.warning(f"⚠ Activity tracking tables not found: {missing}. Run migration 004.")
            else:
                logger.info("✓ Activity tracking tables ready")
                
        except Exception as e:
            logger.error(f"Failed to verify activity tables: {e}")
    
    def log_activity(
        self,
        user_id: str,
        activity_type: ActivityType,
        query_text: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
        suggestion_clicked: Optional[str] = None,
        feedback_rating: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Log a user activity.
        
        Args:
            user_id: User identifier
            activity_type: Type of activity (query, chat, suggestion_click, feedback)
            query_text: User's query or chat message
            response_data: Full response including SQL, results, metadata
            suggestion_clicked: Which suggestion was clicked
            feedback_rating: Rating 1-5 if feedback
            metadata: Additional context (role, preferences, etc.)
            
        Returns:
            Activity ID if successful, None otherwise
        """
        try:
            query = """
                INSERT INTO user_activity 
                (user_id, activity_type, query_text, response_data, suggestion_clicked, feedback_rating, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            result = InternalDB.execute_query(
                query,
                (
                    user_id,
                    activity_type.value,
                    query_text,
                    json.dumps(response_data) if response_data else None,
                    suggestion_clicked,
                    feedback_rating,
                    json.dumps(metadata) if metadata else '{}'
                )
            )
            
            if result.rows:
                activity_id = result.rows[0][0]
                logger.info(f"✓ Logged {activity_type.value} activity for user {user_id} (ID: {activity_id})")
                return activity_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            return None
    
    def log_query(
        self,
        user_id: str,
        query_text: str,
        response_data: Dict[str, Any],
        user_role: Optional[str] = None,
        user_goals: Optional[List[str]] = None
    ) -> Optional[int]:
        """Log a query execution."""
        metadata = {}
        if user_role:
            metadata['role'] = user_role
        if user_goals:
            metadata['goals'] = user_goals
        
        # Extract key metrics from response
        if response_data:
            metadata['has_results'] = bool(response_data.get('data'))
            metadata['row_count'] = len(response_data.get('data', []))
            metadata['execution_time'] = response_data.get('metadata', {}).get('execution_time_ms')
            metadata['sql_used'] = bool(response_data.get('metadata', {}).get('generated_sql'))
        
        return self.log_activity(
            user_id=user_id,
            activity_type=ActivityType.QUERY,
            query_text=query_text,
            response_data=response_data,
            metadata=metadata
        )
    
    def log_suggestion_click(
        self,
        user_id: str,
        suggestion_text: str,
        user_role: Optional[str] = None
    ) -> Optional[int]:
        """Log when a user clicks a suggestion."""
        metadata = {}
        if user_role:
            metadata['role'] = user_role
        
        return self.log_activity(
            user_id=user_id,
            activity_type=ActivityType.SUGGESTION_CLICK,
            suggestion_clicked=suggestion_text,
            metadata=metadata
        )
    
    def log_feedback(
        self,
        user_id: str,
        query_text: str,
        rating: int,
        comment: Optional[str] = None
    ) -> Optional[int]:
        """Log user feedback on a query."""
        metadata = {}
        if comment:
            metadata['comment'] = comment
        
        return self.log_activity(
            user_id=user_id,
            activity_type=ActivityType.FEEDBACK,
            query_text=query_text,
            feedback_rating=rating,
            metadata=metadata
        )
    
    def get_user_activities(
        self,
        user_id: str,
        activity_type: Optional[ActivityType] = None,
        limit: int = 100
    ) -> List[UserActivity]:
        """Get recent activities for a user."""
        try:
            query = """
                SELECT id, user_id, activity_type, query_text, response_data, 
                       suggestion_clicked, feedback_rating, metadata, created_at
                FROM user_activity
                WHERE user_id = %s
            """
            params = [user_id]
            
            if activity_type:
                query += " AND activity_type = %s"
                params.append(activity_type.value)
            
            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            
            result = InternalDB.execute_query(query, tuple(params))
            
            activities = []
            for row in result.rows:
                # Parse JSONB fields
                response_data = json.loads(row[4]) if row[4] else None
                metadata = json.loads(row[7]) if row[7] else {}
                
                activities.append(UserActivity(
                    id=row[0],
                    user_id=row[1],
                    activity_type=ActivityType(row[2]),
                    query_text=row[3],
                    response_data=response_data,
                    suggestion_clicked=row[5],
                    feedback_rating=row[6],
                    metadata=metadata,
                    created_at=row[8]
                ))
            
            return activities
            
        except Exception as e:
            logger.error(f"Failed to get user activities: {e}")
            return []
    
    def get_popular_queries(
        self,
        role: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most common queries, optionally filtered by role."""
        try:
            query = """
                SELECT query_text, COUNT(*) as frequency,
                       AVG(CAST(metadata->>'execution_time' AS FLOAT)) as avg_time
                FROM user_activity
                WHERE activity_type = 'query' AND query_text IS NOT NULL
            """
            params = []
            
            if role:
                query += " AND metadata->>'role' = %s"
                params.append(role)
            
            query += """
                GROUP BY query_text
                ORDER BY frequency DESC
                LIMIT %s
            """
            params.append(limit)
            
            result = InternalDB.execute_query(query, tuple(params) if params else None)
            
            popular = []
            for row in result.rows:
                popular.append({
                    'query_text': row[0],
                    'frequency': row[1],
                    'avg_time': row[2]
                })
            
            return popular
            
        except Exception as e:
            logger.error(f"Failed to get popular queries: {e}")
            return []


def get_activity_logger() -> ActivityLogger:
    """Get or create singleton ActivityLogger instance."""
    global _activity_logger
    if _activity_logger is None:
        _activity_logger = ActivityLogger()
    return _activity_logger
