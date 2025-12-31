"""
RLS Query Endpoint Example

Example endpoint showing how to integrate RLS configuration with query execution.
This demonstrates the complete flow from user authentication to RLS-enabled query execution.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_user
from src.api.models import User
from src.database.connection import get_db
from src.user.rls_loader import load_user_context_for_api, get_rls_summary
from src.integration.orchestrator_v2 import QueryOrchestrator, QueryRequest
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/query", tags=["Query with RLS"])


class NaturalLanguageQueryWithRLS(BaseModel):
    """Request model for natural language query with RLS"""
    query: str
    connection_id: int
    enable_rls: bool = True  # Enable RLS by default for security


@router.post("/natural-rls")
async def query_with_rls(
    request: NaturalLanguageQueryWithRLS,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Execute a natural language query with RLS enabled.
    
    This endpoint demonstrates the complete RLS integration:
    1. Load user RLS configuration from database
    2. Create UserContext with roles, permissions, and filters
    3. Execute query with RLS filters applied
    4. Return results filtered by user's access level
    
    Example Usage:
    ```
    POST /api/v1/query/natural-rls
    {
        "query": "Show me all transactions",
        "connection_id": 1,
        "enable_rls": true
    }
    ```
    
    For user "Bhanu" with RLS filter (region = 'Region 1'), the query will only
    return transactions from Region 1.
    """
    try:
        # Load user RLS context from database
        user_context = await load_user_context_for_api(
            db=db,
            user_id=current_user.id,
            connection_id=request.connection_id,
            enable_rls=request.enable_rls
        )
        
        # Log RLS configuration being used
        if user_context:
            rls_summary = get_rls_summary(user_context)
            logger.info(f"Query with RLS for user {current_user.username}: {rls_summary}")
        else:
            logger.info(f"Query without RLS for user {current_user.username} (admin mode)")
        
        # Create query orchestrator
        orchestrator = QueryOrchestrator(connection_id=request.connection_id)
        
        # Build query request
        query_request = QueryRequest(
            natural_language_query=request.query,
            user_context=user_context,  # None for admin, UserContext for RLS
            enable_rls=request.enable_rls
        )
        
        # Execute query with RLS
        result = await orchestrator.execute_query(query_request)
        
        # Return results with RLS metadata
        return {
            'success': True,
            'query': request.query,
            'sql_query': result.sql_query,
            'data': result.data,
            'row_count': len(result.data) if result.data else 0,
            'execution_time': result.execution_time,
            'rls_enabled': request.enable_rls,
            'rls_applied': user_context is not None and len(user_context.rls_filters or []) > 0,
            'rls_summary': get_rls_summary(user_context) if user_context else None
        }
        
    except PermissionError as e:
        # User doesn't have permission to access the data
        logger.warning(f"Permission denied for user {current_user.username}: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing query with RLS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rls-status/connection/{connection_id}")
async def get_rls_status(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get RLS configuration status for the current user and connection.
    
    This endpoint allows users to see what RLS filters and permissions
    are configured for them before executing queries.
    
    Returns:
    - Role assigned
    - RLS filters active
    - Table permissions
    - Summary of access restrictions
    """
    try:
        # Load user context
        user_context = await load_user_context_for_api(
            db=db,
            user_id=current_user.id,
            connection_id=connection_id,
            enable_rls=True
        )
        
        if not user_context:
            return {
                'rls_enabled': False,
                'message': 'RLS not configured, using admin access'
            }
        
        # Get RLS summary
        summary = get_rls_summary(user_context)
        
        return {
            'rls_enabled': True,
            'user_id': current_user.id,
            'username': current_user.username,
            'connection_id': connection_id,
            'rls_summary': summary,
            'message': f'RLS active with {summary["rls_filters_count"]} filters'
        }
        
    except Exception as e:
        logger.error(f"Error getting RLS status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Example: Integration with existing query endpoint
"""
To integrate RLS into your existing query endpoint:

1. Import the RLS loader:
   from src.user.rls_loader import load_user_context_for_api

2. Get database session:
   db: AsyncSession = Depends(get_db)

3. Load user context before executing query:
   user_context = await load_user_context_for_api(
       db=db,
       user_id=current_user.id,
       connection_id=connection_id,
       enable_rls=True  # Set to False for admin bypass
   )

4. Pass user_context to orchestrator:
   request = QueryRequest(
       natural_language_query=query,
       user_context=user_context,
       enable_rls=True
   )
   
   result = await orchestrator.execute_query(request)

That's it! The orchestrator will automatically:
- Validate user permissions
- Inject RLS filters into SQL
- Restrict access to tables/columns
- Apply row-level security
"""
