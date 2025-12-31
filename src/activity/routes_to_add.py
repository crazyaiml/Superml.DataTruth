"""
Activity and Personalization Routes

API endpoints for user activity tracking and personalized suggestions.
These should be added to src/api/routes.py after the suggestions endpoints.
"""

# Add these imports at the top of routes.py:
# from src.activity import get_activity_logger, get_pattern_analyzer, ActivityType

# Add these routes after the /connections/{connection_id}/suggestions endpoint:

@router.post(
    "/connections/{connection_id}/suggestions/personalized",
    summary="Get personalized query suggestions",
    description="Generate AI-powered personalized query suggestions based on user history, role, and preferences"
)
async def get_personalized_suggestions(
    connection_id: str,
    partial_query: str = "",
    max_suggestions: int = 6,
    user: dict = Depends(get_current_user)
):
    """
    Get personalized query suggestions for a connection based on user activity.
    
    Args:
        connection_id: Database connection ID
        partial_query: User's current input text (optional)
        max_suggestions: Maximum number of suggestions (default 6)
        
    Returns:
        Personalized suggestions with source and learned patterns
    """
    try:
        from src.connection import get_connection_manager
        from src.api.suggestions import generate_personalized_suggestions
        from src.user import get_user_manager
        
        # Get user profile for role
        user_manager = get_user_manager()
        user_id = user.get("user_id", user["username"])
        user_profile = user_manager.get_user(user_id)
        user_role = user_profile.role.value if user_profile else "analyst"
        
        # Get connection and schema
        manager = get_connection_manager()
        if connection_id not in manager.connections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection '{connection_id}' not found"
            )
        
        conn_config = manager.connections[connection_id]
        schema = manager.get_schema(connection_id)
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schema not discovered yet. Run /discover first."
            )
        
        # Build semantic layer
        from src.fieldmap import get_field_mapper
        mapper = get_field_mapper()
        semantic_layer = _build_semantic_layer_from_schema(schema, mapper, connection_id)
        
        # Extract metrics and dimensions
        metrics = [
            {
                "name": metric.name,
                "display_name": metric.display_name,
                "description": metric.description,
                "data_type": metric.data_type,
                "aggregation": metric.aggregation
            }
            for metric in semantic_layer.metrics.values()
        ]
        
        dimensions = [
            {
                "name": dim.name,
                "display_name": dim.display_name,
                "description": dim.description,
                "type": dim.type
            }
            for dim in semantic_layer.dimensions.values()
        ]
        
        # Generate personalized suggestions
        result = generate_personalized_suggestions(
            partial_query=partial_query,
            metrics=metrics,
            dimensions=dimensions,
            connection_name=conn_config.name,
            user_id=user_id,
            user_role=user_role,
            max_suggestions=max_suggestions
        )
        
        return {
            "connection_id": connection_id,
            "partial_query": partial_query,
            "suggestions": result["suggestions"],
            "source": result["source"],
            "user_patterns": result.get("user_patterns", []),
            "role_patterns": result.get("role_patterns", []),
            "count": len(result["suggestions"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate personalized suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# USER ACTIVITY TRACKING ENDPOINTS
# ============================================================================

@router.post(
    "/activity/log",
    summary="Log user activity",
    description="Log user queries, suggestion clicks, and feedback for personalization"
)
async def log_user_activity(
    request: dict,
    user: dict = Depends(get_current_user)
):
    """
    Log a user activity for learning and personalization.
    
    Request body:
        - activity_type: query | chat | suggestion_click | feedback
        - query_text: Optional query text
        - response_data: Optional response data
        - suggestion_clicked: Optional suggestion that was clicked
        - feedback_rating: Optional rating 1-5
        - metadata: Optional additional context
    """
    try:
        from src.activity import get_activity_logger, ActivityType
        from src.user import get_user_manager
        
        logger_instance = get_activity_logger()
        user_manager = get_user_manager()
        
        user_id = user.get("user_id", user["username"])
        user_profile = user_manager.get_user(user_id)
        
        # Parse activity type
        try:
            activity_type = ActivityType(request.get("activity_type"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid activity_type. Must be one of: query, chat, suggestion_click, feedback"
            )
        
        # Enrich metadata with user context
        metadata = request.get("metadata", {})
        if user_profile:
            metadata['role'] = user_profile.role.value
            metadata['department'] = user_profile.department
            metadata['goals'] = user_profile.goals
        
        # Log the activity
        activity_id = logger_instance.log_activity(
            user_id=user_id,
            activity_type=activity_type,
            query_text=request.get("query_text"),
            response_data=request.get("response_data"),
            suggestion_clicked=request.get("suggestion_clicked"),
            feedback_rating=request.get("feedback_rating"),
            metadata=metadata
        )
        
        # Trigger pattern analysis for queries (async would be better)
        if activity_type == ActivityType.QUERY and user_profile:
            from src.activity import get_pattern_analyzer
            analyzer = get_pattern_analyzer()
            # Analyze patterns in background (simplified - would use task queue in production)
            try:
                analyzer.analyze_and_update_patterns(user_id=user_id, role=user_profile.role.value)
            except Exception as e:
                logger.warning(f"Pattern analysis failed: {e}")
        
        return {
            "success": True,
            "activity_id": activity_id,
            "activity_type": activity_type.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/activity/history",
    summary="Get user activity history",
    description="Retrieve recent activity for the current user"
)
async def get_activity_history(
    activity_type: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(get_current_user)
):
    """Get activity history for current user."""
    try:
        from src.activity import get_activity_logger, ActivityType
        
        logger_instance = get_activity_logger()
        user_id = user.get("user_id", user["username"])
        
        # Parse activity type filter
        activity_filter = None
        if activity_type:
            try:
                activity_filter = ActivityType(activity_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid activity_type. Must be one of: query, chat, suggestion_click, feedback"
                )
        
        activities = logger_instance.get_user_activities(
            user_id=user_id,
            activity_type=activity_filter,
            limit=limit
        )
        
        return {
            "user_id": user_id,
            "activities": [a.model_dump() for a in activities],
            "count": len(activities)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get activity history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/activity/patterns",
    summary="Get user's learned query patterns",
    description="Retrieve learned query patterns for the current user"
)
async def get_user_patterns(
    limit: int = 10,
    user: dict = Depends(get_current_user)
):
    """Get learned query patterns for current user."""
    try:
        from src.activity import get_pattern_analyzer
        from src.user import get_user_manager
        
        analyzer = get_pattern_analyzer()
        user_manager = get_user_manager()
        
        user_id = user.get("user_id", user["username"])
        user_profile = user_manager.get_user(user_id)
        
        # Get user-specific patterns
        user_patterns = analyzer.get_user_patterns(user_id, limit=limit)
        
        # Get role-based patterns
        role_patterns = []
        if user_profile:
            role_patterns = analyzer.get_role_patterns(user_profile.role.value, limit=limit)
        
        return {
            "user_id": user_id,
            "user_patterns": [p.model_dump() for p in user_patterns],
            "role_patterns": [p.model_dump() for p in role_patterns],
            "user_pattern_count": len(user_patterns),
            "role_pattern_count": len(role_patterns)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/activity/preferences",
    summary="Get user suggestion preferences",
    description="Get current user's suggestion preferences"
)
async def get_suggestion_preferences(
    user: dict = Depends(get_current_user)
):
    """Get user's suggestion preferences."""
    try:
        from src.activity import get_pattern_analyzer
        
        analyzer = get_pattern_analyzer()
        user_id = user.get("user_id", user["username"])
        
        prefs = analyzer.get_or_create_user_preferences(user_id)
        
        return prefs.model_dump()
        
    except Exception as e:
        logger.error(f"Failed to get preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put(
    "/activity/preferences",
    summary="Update user suggestion preferences",
    description="Update current user's suggestion preferences"
)
async def update_suggestion_preferences(
    request: dict,
    user: dict = Depends(get_current_user)
):
    """Update user's suggestion preferences."""
    try:
        from src.activity import get_pattern_analyzer
        from src.activity.models import SuggestionPreferences
        
        analyzer = get_pattern_analyzer()
        user_id = user.get("user_id", user["username"])
        
        # Get current preferences
        prefs = analyzer.get_or_create_user_preferences(user_id)
        
        # Update with provided values
        if "preferred_query_types" in request:
            prefs.preferred_query_types = request["preferred_query_types"]
        if "excluded_metrics" in request:
            prefs.excluded_metrics = request["excluded_metrics"]
        if "preferred_metrics" in request:
            prefs.preferred_metrics = request["preferred_metrics"]
        if "preferred_dimensions" in request:
            prefs.preferred_dimensions = request["preferred_dimensions"]
        if "show_advanced_queries" in request:
            prefs.show_advanced_queries = request["show_advanced_queries"]
        if "max_suggestions" in request:
            prefs.max_suggestions = request["max_suggestions"]
        
        # Save updated preferences
        analyzer.update_user_preferences(prefs)
        
        return {
            "success": True,
            "preferences": prefs.model_dump()
        }
        
    except Exception as e:
        logger.error(f"Failed to update preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
