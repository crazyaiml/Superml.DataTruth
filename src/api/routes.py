"""
API Endpoints

FastAPI routes for query execution and system management.
"""

import logging
from datetime import timedelta
from typing import List, Union, Optional, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import JSONResponse

from src.api.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    require_admin,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from src.api.models import (
    ClarificationResponse,
    DimensionsResponse,
    ErrorResponse,
    HealthResponse,
    MetricsResponse,
    NaturalLanguageQueryRequest,
    QueryResponse,
    StructuredQueryRequest,
    TokenRequest,
    TokenResponse,
    QueryMetadata,
    UserContextRequest,
)
from src.database import execute_query, QueryExecutionError, get_connection_pool, get_query_cache
from src.planner.query_plan import QueryPlan, TimeRange, FilterCondition
from src.planner.intent_extractor import get_intent_extractor
from src.semantic.loader import get_semantic_layer
from src.semantic.agentic_layer import (
    get_agentic_semantic_layer,
    UserContext,
)
from src.semantic.versioning import get_version_manager
from src.semantic.realtime_metrics import get_realtime_engine, RealtimeContext
from src.user import CreateUserRequest, UpdateUserRequest

# Initialize logger
logger = logging.getLogger(__name__)

# Activity Tracking (User Activity and Personalization)
try:
    from src.activity import get_activity_logger, get_pattern_analyzer, ActivityType
    from src.database.internal_db import InternalDB
    ACTIVITY_TRACKING_AVAILABLE = True
except ImportError:
    ACTIVITY_TRACKING_AVAILABLE = False
    logger.warning("Activity tracking not available")

# Phase 2: AI Synonyms and Feedback
try:
    from src.semantic.ai_synonyms import get_synonym_engine
    from src.semantic.search_index import get_search_index
    from src.feedback.collector import get_feedback_collector, FeedbackType
    PHASE2_AVAILABLE = True
except ImportError:
    PHASE2_AVAILABLE = False

# Phase 3: Data Quality and Matching
try:
    from src.quality.scorer import get_quality_scorer
    from src.quality.profiler import get_data_profiler
    from src.matching.fuzzy_matcher import get_fuzzy_matcher
    from src.matching.entity_matcher import get_entity_matcher
    PHASE3_AVAILABLE = True
except ImportError:
    PHASE3_AVAILABLE = False

router = APIRouter()


# Health Check and Monitoring Endpoints


@router.get("/health", response_model=dict, tags=["Health"])
async def health_check():
    """
    Comprehensive health check endpoint.
    Returns health status of all system components.
    """
    try:
        from src.monitoring.health import HealthChecker
        checker = HealthChecker()
        health_status = checker.check_health()  # Not async
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(content=health_status, status_code=status_code)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503
        )


@router.get("/ready", response_model=dict, tags=["Health"])
async def readiness_check():
    """
    Readiness check for load balancers.
    Returns 200 if service is ready to accept traffic.
    """
    try:
        from src.monitoring.health import HealthChecker
        checker = HealthChecker()
        is_ready = checker.check_readiness()  # Not async
        
        if is_ready.get("ready"):
            return {"status": "ready"}
        else:
            return JSONResponse(
                content={"status": "not ready"},
                status_code=503
            )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            content={"status": "not ready", "error": str(e)},
            status_code=503
        )


@router.get("/alive", response_model=dict, tags=["Health"])
async def liveness_check():
    """
    Liveness check for orchestrators.
    Returns 200 if service is alive (not deadlocked).
    """
    try:
        from src.monitoring.health import HealthChecker
        checker = HealthChecker()
        is_alive = await checker.check_liveness()
        
        if is_alive:
            return {"status": "alive"}
        else:
            return JSONResponse(
                content={"status": "dead"},
                status_code=503
            )
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return JSONResponse(
            content={"status": "dead", "error": str(e)},
            status_code=503
        )


@router.get("/metrics", response_model=dict, tags=["Monitoring"])
async def get_metrics():
    """
    Get system metrics for monitoring.
    Returns detailed metrics about system performance and resource usage.
    """
    try:
        from src.monitoring.health import HealthChecker
        checker = HealthChecker()
        metrics = await checker.get_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper Functions


def _build_user_context(current_user: dict, request_context: UserContextRequest = None) -> UserContext:
    """
    Build UserContext from current user and request context.
    
    Args:
        current_user: Authenticated user from JWT
        request_context: Optional user context from request
    
    Returns:
        UserContext object
    """
    from datetime import datetime
    
    # Parse fiscal year start if present
    fiscal_year_start = None
    if current_user.get("fiscal_year_start"):
        try:
            month, day = map(int, current_user["fiscal_year_start"].split("-"))
            fiscal_year_start = datetime(2024, month, day).date()
        except:
            pass
    
    # Build base context from user
    context = UserContext(
        user_id=current_user.get("user_id", current_user["username"]),
        role=current_user.get("role", "viewer"),  # Generic string role
        department=current_user.get("department"),  # Generic string department
        permissions=current_user.get("permissions", set()),
        default_currency=current_user.get("default_currency", "USD"),
        fiscal_year_start=fiscal_year_start,
        timezone=current_user.get("timezone", "UTC"),
    )
    
    # Override with request context if provided
    if request_context:
        if request_context.role:
            context.role = request_context.role  # Use string directly
        if request_context.department:
            context.department = request_context.department  # Use string directly
        if request_context.permissions:
            context.permissions = request_context.permissions
    
    return context


def _build_semantic_layer_from_schema(schema_data, mapper, connection_id, skip_vector_upsert=False):
    """Build a SemanticLayer from discovered schema and field mappings.
    
    Args:
        schema_data: Discovered database schema
        mapper: Field mapper for AI-powered descriptions
        connection_id: Connection identifier
        skip_vector_upsert: If True, skip vector store upsert (default False)
    """
    from src.semantic.models import (
        SemanticLayer, Metric, Dimension, Join,
        AggregationType, DataType, DimensionType, MetricFormat, FormatType
    )
    
    metrics = {}
    dimensions = {}
    joins = []
    
    # Get vector store for persistent field embeddings
    try:
        from src.vector import get_vector_store
        vector_store = get_vector_store()
        logger.info("Vector store available for semantic layer")
    except Exception as e:
        logger.warning(f"Vector store not available: {e}")
        vector_store = None
    
    # Helper function to map SQL types to DataType enum
    def map_data_type(sql_type: str) -> DataType:
        sql_type_lower = sql_type.lower()
        if 'int' in sql_type_lower or 'serial' in sql_type_lower:
            return DataType.INTEGER
        elif 'float' in sql_type_lower or 'double' in sql_type_lower or 'decimal' in sql_type_lower or 'numeric' in sql_type_lower:
            return DataType.DECIMAL
        elif 'date' in sql_type_lower or 'time' in sql_type_lower:
            return DataType.DATE
        elif 'bool' in sql_type_lower:
            return DataType.BOOLEAN
        else:
            return DataType.STRING
    
    # Helper function to determine dimension type
    def get_dimension_type(column_name: str, data_type: str) -> DimensionType:
        col_lower = column_name.lower()
        type_lower = data_type.lower()
        if 'date' in col_lower or 'time' in col_lower or 'date' in type_lower or 'time' in type_lower:
            return DimensionType.TEMPORAL
        return DimensionType.CATEGORICAL
    
    # Build metrics and dimensions from schema
    for table_name, table_meta in schema_data.tables.items():
        for column in table_meta.columns:
            column_name = column.name
            data_type = column.data_type
            
            # Get field mapping if exists
            mapping = mapper.get_mapping(table_name, column_name, connection_id)
            
            if mapping:
                display_name = mapping.display_name
                # CRITICAL FIX: Trust schema's is_measure flag over old mappings
                # Mappings may be outdated, schema is source of truth
                if hasattr(column, 'is_measure') and column.is_measure is not None:
                    is_measure = column.is_measure
                    is_dimension = not is_measure
                    # Use schema's aggregation if available, otherwise mapping's
                    if hasattr(column, 'default_aggregation') and column.default_aggregation:
                        default_agg = column.default_aggregation
                    else:
                        default_agg = mapping.default_aggregation
                else:
                    # Fall back to mapping if schema doesn't have is_measure
                    is_measure = mapping.is_measure
                    is_dimension = mapping.is_dimension
                    default_agg = mapping.default_aggregation
                description = mapping.description or f"{display_name} from {table_name}"
            else:
                # Fallback to automatic detection
                display_name = mapper.get_display_name(table_name, column_name)
                default_agg = mapper.get_aggregation(table_name, column_name)
                
                # DEBUG: Log what we're checking
                if column_name == "recommendation_mark":
                    print(f"[DEBUG] recommendation_mark: hasattr(is_measure)={hasattr(column, 'is_measure')}, is_measure={getattr(column, 'is_measure', None)}, default_agg={default_agg}")
                
                # Use schema's is_measure flag first, then fallback to aggregation detection
                if hasattr(column, 'is_measure') and column.is_measure:
                    is_measure = True
                    # If no default_agg set but schema says it's a measure, use schema's aggregation
                    if not default_agg and hasattr(column, 'default_aggregation') and column.default_aggregation:
                        default_agg = column.default_aggregation
                    elif not default_agg:
                        # Check if this is an ID field - use count_distinct instead of avg
                        col_lower = column_name.lower()
                        if col_lower == 'id' or col_lower.endswith('_id') or col_lower.startswith('id_'):
                            default_agg = "count_distinct"
                        else:
                            # Default to 'avg' for other measures without explicit aggregation
                            default_agg = "avg"
                else:
                    is_measure = default_agg in ["sum", "avg", "count", "min", "max", "count_distinct"] if default_agg else False
                
                is_dimension = not is_measure
                description = f"{display_name} from {table_name}"
            
            qualified_name = f"{table_name}.{column_name}"
            mapped_type = map_data_type(data_type)
            
            # CRITICAL: Override aggregation for ID fields - they should always be COUNT DISTINCT
            col_lower = column_name.lower()
            if is_measure and (col_lower == 'id' or col_lower.endswith('_id') or col_lower.startswith('id_')):
                default_agg = "count_distinct"
            
            # Add as metric if it's a measure
            if is_measure:
                # Use table-qualified name to avoid collisions
                metric_name = f"{display_name}"
                
                # Check if this metric name already exists from another table
                # Prioritize certain tables for common metrics
                if metric_name in metrics:
                    existing_table = metrics[metric_name].base_table
                    # Priority order for tables (higher priority = keep this one)
                    table_priority = {
                        'stockprice': 100,  # Highest priority for stock data
                        'stock_price': 100,
                        'stocks': 90,
                        'crypto_prices': 80,
                        'crypto_signal_history': 50,
                        'options': 70,
                        'default': 10
                    }
                    
                    current_priority = table_priority.get(table_name.lower(), table_priority['default'])
                    existing_priority = table_priority.get(existing_table.lower(), table_priority['default'])
                    
                    # Only skip if lower priority (don't skip same priority from same table)
                    if current_priority < existing_priority:
                        logger.debug(f"Skipping metric {metric_name} from {table_name} (lower priority than {existing_table})")
                        continue
                    # If same priority but different table, use qualified name to keep both
                    elif current_priority == existing_priority and table_name != existing_table:
                        metric_name = f"{display_name} ({table_name})"
                        logger.debug(f"Using qualified name for metric: {metric_name}")
                
                # Map aggregation string to AggregationType enum
                agg_map = {
                    "sum": AggregationType.SUM,
                    "avg": AggregationType.AVG,
                    "count": AggregationType.COUNT,
                    "count_distinct": AggregationType.COUNT_DISTINCT,
                    "min": AggregationType.MIN,
                    "max": AggregationType.MAX
                }
                agg_type = agg_map.get(default_agg.lower() if default_agg else "sum", AggregationType.SUM)
                
                # Determine format based on column name and type
                format_type = FormatType.NUMBER
                if 'price' in column_name.lower() or 'amount' in column_name.lower() or 'revenue' in column_name.lower():
                    format_type = FormatType.CURRENCY
                elif 'percent' in column_name.lower() or 'rate' in column_name.lower():
                    format_type = FormatType.PERCENTAGE
                
                # Generate synonyms for better matching
                synonyms = []
                # Add the original column name as a synonym
                if column_name.lower() != display_name.lower():
                    synonyms.append(column_name.replace('_', ' ').title())
                
                # Add variations for common patterns
                col_lower = column_name.lower()
                disp_lower = display_name.lower()
                
                # For "price change" type columns, add variations
                if 'change' in col_lower or 'change' in disp_lower:
                    synonyms.extend(['Change', 'Daily Change', 'Change 24h', '24h Change', 'Price Change'])
                    if '24h' in col_lower or '24h' in disp_lower:
                        synonyms.extend(['Change 24h', '24 Hour Change'])
                    if 'daily' in col_lower or 'daily' in disp_lower:
                        synonyms.extend(['Daily Change', 'Day Change'])
                
                # For price columns
                if 'price' in col_lower:
                    synonyms.extend(['Price', 'Stock Price', 'Current Price'])
                    # If it's a price change metric, add those synonyms too
                    if 'change' in col_lower or 'change' in disp_lower:
                        synonyms.extend(['Price Change 24h', 'Daily Price Change'])
                
                # For volume columns
                if 'volume' in col_lower:
                    synonyms.extend(['Volume', 'Trading Volume', '24h Volume'])
                
                # Remove duplicates while preserving order
                seen = set()
                synonyms = [x for x in synonyms if not (x.lower() in seen or seen.add(x.lower()))]
                
                metrics[metric_name] = Metric(
                    name=metric_name,
                    display_name=display_name,
                    description=description,
                    formula=qualified_name,
                    base_table=table_name,
                    aggregation=agg_type,
                    data_type=mapped_type,
                    format=MetricFormat(type=format_type, decimals=2),
                    synonyms=synonyms,
                    tags=[]
                )
            
            # Add as dimension if it's a dimension
            if is_dimension:
                dim_name = f"{display_name}"
                
                # Check if this dimension name already exists from another table
                # Prioritize certain tables for common dimensions
                if dim_name in dimensions:
                    existing_table = dimensions[dim_name].table
                    # Priority order for tables (same as metrics)
                    table_priority = {
                        'stockprice': 100,
                        'stock_price': 100,
                        'stocks': 90,
                        'crypto_prices': 80,
                        'crypto_signal_history': 50,
                        'options': 70,
                        'default': 10
                    }
                    
                    current_priority = table_priority.get(table_name.lower(), table_priority['default'])
                    existing_priority = table_priority.get(existing_table.lower(), table_priority['default'])
                    
                    # Only skip if lower priority
                    if current_priority < existing_priority:
                        logger.debug(f"Skipping dimension {dim_name} from {table_name} (lower priority than {existing_table})")
                        continue
                    # If same priority but different table, use qualified name to keep both
                    elif current_priority == existing_priority and table_name != existing_table:
                        dim_name = f"{display_name} ({table_name})"
                        logger.debug(f"Using qualified name for dimension: {dim_name}")
                
                dim_type = get_dimension_type(column_name, data_type)
                
                # Generate synonyms for better matching
                synonyms = []
                # Add the original column name as a synonym
                if column_name.lower() != display_name.lower():
                    synonyms.append(column_name.replace('_', ' ').title())
                # Add variations for common patterns
                if 'symbol' in column_name.lower() or 'ticker' in column_name.lower():
                    synonyms.extend(['Stock Symbol', 'Ticker', 'Stock', 'Stocks'])
                if 'sector' in column_name.lower():
                    synonyms.extend(['Industry', 'Sector'])
                if 'date' in column_name.lower():
                    synonyms.extend(['Date', 'Trading Date', 'Day'])
                
                dimensions[dim_name] = Dimension(
                    name=dim_name,
                    display_name=display_name,
                    description=description,
                    table=table_name,
                    field=column_name,
                    type=dim_type,
                    default_display=display_name,
                    synonyms=synonyms,
                    tags=[]
                )
    
    # Build joins from relationships if available
    # Import additional required types for Join
    from src.semantic.models import JoinType, JoinCardinality, JoinCondition
    
    # Load calculated metrics from database
    try:
        from src.database.internal_db import InternalDB
        logger.info(f"[CALC_METRICS] Attempting to load calculated metrics for {connection_id}")
        calc_metrics = InternalDB.execute_query(
            "SELECT * FROM calculated_metrics WHERE connection_id = %s AND is_active = true",
            params=(connection_id,)
        )
        logger.info(f"[CALC_METRICS] Found {len(calc_metrics)} calculated metrics in database")
        
        for cm in calc_metrics:
            logger.info(f"[CALC_METRICS] Processing metric: {cm['metric_name']}")
            # Convert database row to Metric object
            from src.semantic.models import AggregationType, DataType, MetricFormat, FormatType
            
            # Map aggregation string to enum
            agg_map = {
                "sum": AggregationType.SUM,
                "avg": AggregationType.AVG,
                "count": AggregationType.COUNT,
                "min": AggregationType.MIN,
                "max": AggregationType.MAX,
                "calculated": AggregationType.SUM  # For complex formulas
            }
            
            # Map format type string to enum
            format_map = {
                "currency": FormatType.CURRENCY,
                "percentage": FormatType.PERCENTAGE,
                "number": FormatType.NUMBER
            }
            
            # Skip filters for now (they can be applied at query time if needed)
            # Filters in calculated_metrics are pre-conditions, but the Metric model
            # expects Filter objects, not FilterCondition objects
            
            # Create Metric object
            metric = Metric(
                name=cm['metric_name'],
                display_name=cm['display_name'],
                description=cm.get('description', ''),
                formula=cm['formula'],  # Formula is already complete SQL expression
                base_table=cm['base_table'],
                aggregation=agg_map.get(cm.get('aggregation', 'sum'), AggregationType.SUM),
                data_type=DataType.DECIMAL if cm.get('data_type') == 'decimal' else DataType.INTEGER,
                filters=[],  # Skip filters to avoid validation issues
                format=MetricFormat(
                    type=format_map.get(cm.get('format_type', 'number'), FormatType.NUMBER),
                    decimals=2
                ),
                synonyms=cm.get('synonyms', []) or [],
                tags=[]
            )
            
            # Add to metrics dict (overwrite any column-based metric with same name)
            metrics[cm['metric_name']] = metric
            logger.info(f"Loaded calculated metric from database: {cm['metric_name']}")
            
    except Exception as e:
        logger.warning(f"Could not load calculated metrics from database: {e}")
    
    # Debug: Log created metrics and dimensions
    print(f"[DEBUG] Built semantic layer for {connection_id}:")
    print(f"  Metrics: {list(metrics.keys())}")
    print(f"  Dimensions: {list(dimensions.keys())}")
    
    # Store all metrics and dimensions to vector DB (only during discovery, not on every query)
    if vector_store and not skip_vector_upsert:
        try:
            fields_added = 0
            for metric_name, metric in metrics.items():
                vector_store.add_field(
                    connection_id=connection_id,
                    table_name=metric.base_table,
                    column_name=metric.formula.split('.')[-1] if '.' in metric.formula else metric.formula,
                    display_name=metric.display_name,
                    description=metric.description,
                    is_measure=True,
                    synonyms=metric.synonyms,
                    data_type=metric.data_type.value
                )
                fields_added += 1
            
            for dim_name, dimension in dimensions.items():
                vector_store.add_field(
                    connection_id=connection_id,
                    table_name=dimension.table,
                    column_name=dimension.field,
                    display_name=dimension.display_name,
                    description=dimension.description,
                    is_measure=False,
                    synonyms=dimension.synonyms,
                    data_type="string"  # Dimensions are typically strings
                )
                fields_added += 1
            
            logger.info(f"Added {fields_added} fields to vector store for connection {connection_id}")
        except Exception as e:
            logger.error(f"Failed to add fields to vector store: {e}")
    
    if schema_data.relationships:
        for rel in schema_data.relationships:
            # Create proper Join object with all required fields
            join_name = f"{rel.from_table}_to_{rel.to_table}"
            
            # Determine cardinality based on relationship type (default to many_to_one)
            cardinality = JoinCardinality.MANY_TO_ONE
            if hasattr(rel, 'cardinality'):
                cardinality_map = {
                    "one_to_one": JoinCardinality.ONE_TO_ONE,
                    "one_to_many": JoinCardinality.ONE_TO_MANY,
                    "many_to_one": JoinCardinality.MANY_TO_ONE,
                    "many_to_many": JoinCardinality.MANY_TO_MANY
                }
                cardinality = cardinality_map.get(rel.cardinality, JoinCardinality.MANY_TO_ONE)
            
            joins.append(Join(
                name=join_name,
                from_table=rel.from_table,
                to_table=rel.to_table,
                join_type=JoinType.LEFT,
                on=[JoinCondition(from_field=rel.from_column, to_field=rel.to_column)],
                cardinality=cardinality,
                required=False
            ))
    
    return SemanticLayer(
        metrics=metrics,
        dimensions=dimensions,
        joins=joins,
        join_preferences=[],
        synonyms={}
    )


# Authentication Endpoints


@router.post(
    "/auth/token",
    response_model=TokenResponse,
    tags=["Authentication"],
    summary="Get access token",
)
async def login(request: TokenRequest):
    """
    Authenticate and get JWT access token.

    - **username**: Username
    - **password**: Password

    Returns JWT token valid for 60 minutes.
    """
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# Query Endpoints


@router.post(
    "/query/natural",
    response_model=Union[QueryResponse, ClarificationResponse],
    responses={
        200: {"model": QueryResponse},
        202: {"model": ClarificationResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    tags=["Query"],
    summary="Execute natural language query",
)
async def query_natural_language(
    request: NaturalLanguageQueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Execute a natural language query with context-aware semantic layer.

    - **question**: Natural language question (e.g., "Revenue last quarter by agent?")
    - **connection_id**: Database connection to query (optional, uses default if not provided)
    - **context**: Previous queries for follow-up questions
    - **clarifications**: Optional clarifications for ambiguous queries
    - **user_context**: Optional user context for personalization

    Returns query results or clarification questions if needed.
    """
    try:
        # If no connection_id provided, use default (demo-sales-db for backward compatibility)
        connection_id = request.connection_id or "demo-sales-db"
        
        # Build user context
        user_context = _build_user_context(current_user, request.user_context)
        
        # Initialize agentic_layer (only used for demo-sales-db fallback)
        agentic_layer = None
        
        # Get semantic layer for this connection
        # First try to get cached schema, only discover if not cached
        try:
            from src.connection.manager import get_connection_manager
            from src.fieldmap import get_field_mapper
            
            manager = get_connection_manager()
            mapper = get_field_mapper()
            
            # Try to get cached schema first
            schema_data = manager.get_schema(connection_id)
            
            # If not cached, discover and cache it
            if schema_data is None:
                logger.info(f"Schema not cached for {connection_id}, discovering...")
                schema_data = manager.discover_schema(connection_id)
            else:
                logger.info(f"Using cached schema for {connection_id}")
            
            # Build semantic layer from schema (vector store upsert moved to /discover endpoint)
            semantic_layer = _build_semantic_layer_from_schema(
                schema_data, 
                mapper, 
                connection_id,
                skip_vector_upsert=True  # Don't upsert on every query
            )
            
        except Exception as e:
            # Fallback to static YAML-based semantic layer for demo-sales-db
            if connection_id == "demo-sales-db":
                print(f"Warning: Could not build dynamic semantic layer: {e}")
                print("Falling back to static YAML semantic layer")
                agentic_layer = get_agentic_semantic_layer()
                semantic_layer = agentic_layer.get_contextualized_layer(user_context)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not load semantic layer for connection {connection_id}: {str(e)}"
                )
        
        # Get version manager (still use for demo backward compatibility)
        version_mgr = get_version_manager()
        semantic_version = version_mgr.get_version_for_user(
            user_id=user_context.user_id,
            user_role=user_context.role,
            user_department=user_context.department if user_context.department else None
        )
        
        # Extract intent from natural language using the dynamic semantic layer
        from src.planner.intent_extractor import IntentExtractor
        extractor = IntentExtractor(semantic_layer=semantic_layer, use_ai_synonyms=False)
        extraction = extractor.extract(request.question)
        
        # Debug: Log what was extracted
        print(f"\n[DEBUG] ===== INTENT EXTRACTION =====")
        print(f"[DEBUG] Question: {request.question}")
        print(f"[DEBUG] Extracted metric: {extraction.query_plan.metric}")
        print(f"[DEBUG] Extracted dimensions: {extraction.query_plan.dimensions}")
        print(f"[DEBUG] Available metrics in semantic layer:")
        for metric_name, metric in list(semantic_layer.metrics.items())[:10]:
            print(f"[DEBUG]   - {metric_name} (synonyms: {metric.synonyms[:5] if metric.synonyms else []})")
        
        # === LEARNING SYSTEM: Try semantic matching if exact match fails ===
        from src.learning.query_learner import get_query_learner
        from src.learning.semantic_matcher import get_semantic_matcher
        from src.vector import get_vector_store
        
        learner = get_query_learner()
        
        # Get vector store and pass to semantic matcher
        try:
            vector_store = get_vector_store()
            matcher = get_semantic_matcher()
            matcher.vector_store = vector_store  # Inject vector store
        except Exception as e:
            logger.warning(f"Vector store not available for semantic matching: {e}")
            matcher = get_semantic_matcher()
        
        # Track original extracted values
        original_metric = extraction.query_plan.metric
        original_dimensions = extraction.query_plan.dimensions.copy() if extraction.query_plan.dimensions else []
        
        # If metric not found, try semantic matching
        matched_metric = None
        if extraction.query_plan.metric:
            print(f"[DEBUG] Checking if metric '{extraction.query_plan.metric}' exists in semantic layer...")
            found = semantic_layer.get_metric(extraction.query_plan.metric)
            print(f"[DEBUG] get_metric result: {found.name if found else 'NOT FOUND'}")
            if not found:
                # Try learned synonyms first
                available_metrics = list(semantic_layer.metrics.keys())
                learned_syns = learner.get_all_learned_synonyms()
                
                # Check learned synonyms
                for metric_name, synonyms in learned_syns.items():
                    if extraction.query_plan.metric.lower() in [s.lower() for s in synonyms]:
                        extraction.query_plan.metric = metric_name
                        matched_metric = metric_name
                        logger.info(f"Matched using learned synonym: '{original_metric}' -> '{metric_name}'")
                        break
                
                # If still not found, try semantic matching
                if not matched_metric:
                    print(f"[DEBUG] Trying semantic match for '{extraction.query_plan.metric}'")
                    print(f"[DEBUG] Available metrics: {available_metrics[:10]}...")  # Show first 10
                    
                    match_result = matcher.find_best_match(
                        extraction.query_plan.metric,
                        available_metrics,
                        threshold=0.3,  # Lower threshold for better recall (token-based matching needs lower threshold)
                        connection_id=connection_id,  # Pass connection ID for vector store filtering
                        field_type="metric"  # Specify we're looking for metrics
                    )
                    
                    print(f"[DEBUG] Semantic match result: {match_result}")
                    
                    if match_result:
                        matched_name, score = match_result
                        extraction.query_plan.metric = matched_name
                        matched_metric = matched_name
                        logger.info(f"Semantic match: '{original_metric}' -> '{matched_name}' (score: {score:.2f})")
                        print(f"[DEBUG] Successfully matched '{original_metric}' -> '{matched_name}' (score: {score:.2f})")
                    else:
                        logger.warning(f"No match found for metric: '{extraction.query_plan.metric}'")
                        # Get suggestions for error message
                        suggestions = matcher.get_top_matches(extraction.query_plan.metric, available_metrics, top_k=5)
                        print(f"[DEBUG] Top suggestions: {suggestions}")
                        suggestion_text = ", ".join([f"'{s[0]}' ({s[1]:.0%})" for s in suggestions[:3]])
                        raise HTTPException(
                            status_code=400,
                            detail=f"Metric not found: {extraction.query_plan.metric}. Did you mean: {suggestion_text}?"
                        )
            else:
                # Metric was found via synonym matching - update to use the actual metric name
                print(f"[DEBUG] Metric found via synonym: '{extraction.query_plan.metric}' -> '{found.name}'")
                extraction.query_plan.metric = found.name
                matched_metric = found.name
        
        # Debug: Log extracted intent
        print(f"[DEBUG] Extracted intent from '{request.question}':")
        print(f"  Metric: {extraction.query_plan.metric}")
        print(f"  Dimensions: {extraction.query_plan.dimensions}")
        print(f"  Filters: {extraction.query_plan.filters}")

        # PHASE 3: Apply fuzzy matching to filter values (e.g., agent names, client names)
        # This handles typos like "Alise" → "Alice", "Microsft" → "Microsoft"
        if extraction.query_plan.filters:
            from src.matching.fuzzy_matcher import get_fuzzy_matcher
            fuzzy_matcher = get_fuzzy_matcher()
            
            # Get database connection for the specific connection_id (not global default)
            manager = get_connection_manager()
            conn = manager.get_connection(connection_id)
            
            corrected_filters = []
            for filter_obj in extraction.query_plan.filters:
                corrected_filter = filter_obj.model_copy(deep=True)
                
                # For agent_name filters, fuzzy match against actual agent names
                if 'agent' in filter_obj.field.lower() and 'name' in filter_obj.field.lower():
                    try:
                        # Fetch all agent names from database using connection-specific connection
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT DISTINCT name FROM agents ORDER BY name")
                            agent_names = [row[0] for row in cursor.fetchall()]
                        
                        if agent_names and filter_obj.value:
                            # Fuzzy match the user's input against valid agent names
                            matches = fuzzy_matcher.fuzzy_match(
                                query=str(filter_obj.value),
                                candidates=agent_names,
                                threshold=0.7
                            )
                            
                            if matches and len(matches) > 0:
                                best_match = matches[0]
                                if best_match.score >= 0.9:
                                    # High confidence - use the match
                                    corrected_filter.value = best_match.matched_value
                                elif best_match.score >= 0.7:
                                    # Medium confidence - use match but add to assumptions
                                    corrected_filter.value = best_match.matched_value
                                    extraction.query_plan.assumptions.append(
                                        f"Matched '{filter_obj.value}' to '{best_match.matched_value}' "
                                        f"(confidence: {best_match.score:.0%}, type: {best_match.match_type})"
                                    )
                                # else: low confidence, keep original value (will likely return no results)
                    except Exception as e:
                        print(f"Warning: Could not fuzzy match agent name: {e}")
                
                # For client_name filters, fuzzy match against actual client names
                elif 'client' in filter_obj.field.lower() and 'name' in filter_obj.field.lower():
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT DISTINCT name FROM clients ORDER BY name")
                            client_names = [row[0] for row in cursor.fetchall()]
                        
                        if client_names and filter_obj.value:
                            matches = fuzzy_matcher.fuzzy_match(
                                query=str(filter_obj.value),
                                candidates=client_names,
                                threshold=0.7
                            )
                            
                            if matches and len(matches) > 0:
                                best_match = matches[0]
                                if best_match.score >= 0.9:
                                    corrected_filter.value = best_match.matched_value
                                elif best_match.score >= 0.7:
                                    corrected_filter.value = best_match.matched_value
                                    extraction.query_plan.assumptions.append(
                                        f"Matched '{filter_obj.value}' to '{best_match.matched_value}' "
                                        f"(confidence: {best_match.score:.0%}, type: {best_match.match_type})"
                                    )
                    except Exception as e:
                        print(f"Warning: Could not fuzzy match client name: {e}")
                
                # For company_name filters
                elif 'company' in filter_obj.field.lower() and 'name' in filter_obj.field.lower():
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT DISTINCT name FROM companies ORDER BY name")
                            company_names = [row[0] for row in cursor.fetchall()]
                        
                        if company_names and filter_obj.value:
                            matches = fuzzy_matcher.fuzzy_match(
                                query=str(filter_obj.value),
                                candidates=company_names,
                                threshold=0.7
                            )
                            
                            if matches and len(matches) > 0:
                                best_match = matches[0]
                                if best_match.score >= 0.9:
                                    corrected_filter.value = best_match.matched_value
                                elif best_match.score >= 0.7:
                                    corrected_filter.value = best_match.matched_value
                                    extraction.query_plan.assumptions.append(
                                        f"Matched '{filter_obj.value}' to '{best_match.matched_value}' "
                                        f"(confidence: {best_match.score:.0%}, type: {best_match.match_type})"
                                    )
                    except Exception as e:
                        print(f"Warning: Could not fuzzy match company name: {e}")
                
                corrected_filters.append(corrected_filter)
            
            # Replace filters with corrected versions
            extraction.query_plan.filters = corrected_filters
            
            # Release the connection back to the pool
            manager.release_connection(connection_id, conn)

        # Check metric access (only for demo-sales-db with agentic layer)
        if extraction.query_plan.metric and agentic_layer:
            has_access, reason = agentic_layer.check_metric_access(
                extraction.query_plan.metric,
                user_context
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=reason or "Access denied to requested metric"
                )

        # Check if clarification needed
        if extraction.query_plan.needs_clarification:
            # Get suggested queries (if agentic layer available, use it, otherwise empty)
            suggested_queries = []
            if agentic_layer:
                ctx_layer = agentic_layer.get_contextualized_layer(user_context)
                suggested_queries = ctx_layer.suggested_queries[:5]
            
            clarification = ClarificationResponse(
                needs_clarification=True,
                questions=[extraction.query_plan.clarification_question] if extraction.query_plan.clarification_question else [],
                suggestions={
                    "suggested_queries": suggested_queries
                },
            )
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content=clarification.model_dump()
            )

        # Check if this is an "insights" query (dimension filter but vague metric request)
        # Look for keywords like "insights", "performance", "overview" in the intent
        is_insights_query = (
            extraction.query_plan.intent and 
            any(word in extraction.query_plan.intent.lower() for word in ['insight', 'performance', 'overview', 'details', 'metrics']) and
            extraction.query_plan.filters and
            len(extraction.query_plan.filters) > 0
        )
        
        # If insights query, execute for ALL core metrics
        if is_insights_query:
            core_metrics = ['revenue', 'profit', 'transaction_count', 'average_transaction_value']
            # Check available metrics in semantic layer
            available_metrics = [m for m in core_metrics if m in semantic_layer.metrics]
            
            # Execute query for each metric
            combined_results = []
            total_time = 0
            
            for metric_name in available_metrics:
                # Create a copy of the query plan with this metric
                metric_plan = extraction.query_plan.model_copy(deep=True)
                metric_plan.metric = metric_name
                
                # Ensure LIMIT is set for insights queries (default to 100)
                if not metric_plan.limit:
                    metric_plan.limit = 100
                
                # Check access (only for demo-sales-db with agentic layer)
                if agentic_layer:
                    has_access, reason = agentic_layer.check_metric_access(metric_name, user_context)
                    if not has_access:
                        continue
                
                # Execute
                try:
                    result = execute_query(metric_plan, semantic_layer=semantic_layer)
                    total_time += result.execution_time_ms
                    
                    # Add metric name to each row
                    for row in result.rows:
                        row['_metric'] = metric_name
                        combined_results.extend([row])
                except Exception as e:
                    print(f"Warning: Could not fetch {metric_name}: {e}")
                    continue
            
            # Record aggregate metrics
            version_mgr.record_query(
                user_id=user_context.user_id,
                version=semantic_version,
                success=True,
                response_time_ms=total_time,
                needed_correction=False
            )
            
            return QueryResponse(
                success=True,
                data=combined_results,
                metadata=QueryMetadata(
                    execution_time_ms=total_time,
                    row_count=len(combined_results),
                    from_cache=False,
                    generated_sql=f"Multi-metric query for: {', '.join(available_metrics)}",
                ),
            )

        # Execute single query
        # Ensure LIMIT is set (default to 100 if not specified)
        if not extraction.query_plan.limit:
            extraction.query_plan.limit = 100
        
        start_time = timedelta()
        result = execute_query(extraction.query_plan, semantic_layer=semantic_layer, connection_id=connection_id)
        
        # Record query metrics for version tracking
        version_mgr.record_query(
            user_id=user_context.user_id,
            version=semantic_version,
            success=True,
            response_time_ms=result.execution_time_ms,
            needed_correction=False
        )
        
        # === LEARNING SYSTEM: Record successful query for learning ===
        learner.record_query(
            user_query=request.question,
            extracted_metric=original_metric,
            extracted_dimensions=original_dimensions,
            matched_metric=matched_metric,
            matched_dimensions=extraction.query_plan.dimensions or [],
            success=True,
            connection_id=connection_id
        )
        
        # === ACTIVITY TRACKING: Log user query activity ===
        if ACTIVITY_TRACKING_AVAILABLE:
            try:
                from decimal import Decimal
                
                logger.info("[ACTIVITY] Activity tracking is available, logging query...")
                activity_logger = get_activity_logger()
                user_id = current_user.get("user_id") or current_user.get("username")
                user_role = current_user.get("role", "analyst")
                
                # Convert Decimal to float for JSON serialization
                def convert_decimals(obj):
                    if isinstance(obj, Decimal):
                        return float(obj)
                    elif isinstance(obj, dict):
                        return {k: convert_decimals(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_decimals(item) for item in obj]
                    return obj
                
                # Prepare response data for logging
                response_data = {
                    "success": True,
                    "data": convert_decimals(result.rows[:10]),  # Log first 10 rows only, convert Decimals
                    "metadata": {
                        "execution_time_ms": result.execution_time_ms,
                        "row_count": result.row_count,
                        "from_cache": result.from_cache,
                        "generated_sql": result.sql if hasattr(result, 'sql') else None
                    }
                }
                
                activity_id = activity_logger.log_query(
                    user_id=user_id,
                    query_text=request.question,
                    response_data=response_data,
                    user_role=user_role,
                    user_goals=current_user.get("goals", [])
                )
                logger.info(f"✓ Logged query activity for user {user_id}, activity_id={activity_id}")
                
                # Auto-trigger pattern analysis every 10 queries
                try:
                    # Check total query count
                    count_result = InternalDB.execute_query(
                        "SELECT COUNT(*) FROM user_activity WHERE activity_type = 'query'",
                        fetch_one=True
                    )
                    total_queries = count_result[0] if count_result else 0
                    
                    # Trigger analysis every 10 queries
                    if total_queries % 10 == 0 and total_queries > 0:
                        logger.info(f"[AUTO_ANALYSIS] Triggering pattern analysis at {total_queries} queries")
                        from src.activity import get_pattern_analyzer
                        analyzer = get_pattern_analyzer()
                        analyzer.analyze_and_update_patterns()
                        logger.info("[AUTO_ANALYSIS] ✓ Pattern analysis completed")
                except Exception as e:
                    logger.warning(f"[AUTO_ANALYSIS] Failed to auto-trigger pattern analysis: {e}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to log activity: {e}", exc_info=True)
        else:
            logger.warning("[ACTIVITY] Activity tracking NOT available")

        return QueryResponse(
            success=True,
            data=result.rows,
            metadata=QueryMetadata(
                execution_time_ms=result.execution_time_ms,
                row_count=result.row_count,
                from_cache=result.from_cache,
                generated_sql=result.sql if hasattr(result, 'sql') else None,
            ),
        )

    except QueryExecutionError as e:
        # Record failure
        try:
            user_context = _build_user_context(current_user, request.user_context)
            version_mgr = get_version_manager()
            version = version_mgr.get_version_for_user(user_context.user_id)
            version_mgr.record_query(
                user_id=user_context.user_id,
                version=version,
                success=False,
                response_time_ms=0,
                needed_correction=False
            )
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        # === LEARNING SYSTEM: Record failed query ===
        try:
            from src.learning.query_learner import get_query_learner
            learner = get_query_learner()
            learner.record_query(
                user_query=request.question,
                extracted_metric=getattr(extraction.query_plan, 'metric', None) if 'extraction' in locals() else None,
                extracted_dimensions=getattr(extraction.query_plan, 'dimensions', []) if 'extraction' in locals() else [],
                matched_metric=None,
                matched_dimensions=[],
                success=False,
                connection_id=connection_id
            )
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


@router.post(
    "/query/structured",
    response_model=QueryResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    tags=["Query"],
    summary="Execute structured query",
)
async def query_structured(
    request: StructuredQueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Execute a structured query (QueryPlan).

    - **metric**: Metric to calculate
    - **dimensions**: Dimensions to group by
    - **time_range**: Time range filter
    - **filters**: Additional filter conditions
    - **order_by**: Sort order
    - **limit**: Maximum rows to return

    Returns query results.
    """
    try:
        # Convert request to QueryPlan
        time_range = None
        if request.time_range:
            time_range = TimeRange(
                start_date=request.time_range.start_date,
                end_date=request.time_range.end_date,
                period=request.time_range.period,
            )

        filters = [
            FilterCondition(
                field=f.field,
                operator=f.operator,
                value=f.value,
            )
            for f in request.filters
        ]

        plan = QueryPlan(
            metric=request.metric,
            dimensions=request.dimensions,
            time_range=time_range,
            filters=filters,
            order_by=request.order_by,
            limit=request.limit,
            intent="Structured query via API",
            needs_clarification=False,
        )

        # Execute query
        result = execute_query(plan)

        return QueryResponse(
            success=True,
            data=result.rows,
            metadata=QueryMetadata(
                execution_time_ms=result.execution_time_ms,
                row_count=result.row_count,
                from_cache=result.from_cache,
            ),
        )

    except QueryExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid query: {str(e)}",
        )


# Semantic Layer Endpoints


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    tags=["Semantic Layer"],
    summary="List available metrics",
)
async def list_metrics(current_user: dict = Depends(get_current_user)):
    """
    Get list of available metrics from semantic layer.

    Returns all metrics with name, display name, and description.
    """
    semantic_layer = get_semantic_layer()
    metrics_list = [
        {
            "name": metric.name,
            "display_name": metric.display_name,
            "description": metric.description,
            "data_type": metric.data_type,
        }
        for metric in semantic_layer.metrics.values()
    ]

    return MetricsResponse(metrics=metrics_list, count=len(metrics_list))


@router.get(
    "/dimensions",
    response_model=DimensionsResponse,
    tags=["Semantic Layer"],
    summary="List available dimensions",
)
async def list_dimensions(current_user: dict = Depends(get_current_user)):
    """
    Get list of available dimensions from semantic layer.

    Returns all dimensions with name, display name, and description.
    """
    semantic_layer = get_semantic_layer()
    dimensions_list = [
        {
            "name": dim.name,
            "display_name": dim.display_name,
            "description": dim.description,
            "type": dim.type,
        }
        for dim in semantic_layer.dimensions.values()
    ]

    return DimensionsResponse(dimensions=dimensions_list, count=len(dimensions_list))


# System Endpoints


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check",
)
async def health_check():
    """
    Check system health status.

    Returns status of database and cache connections.
    """
    # Check database
    db_status = "unknown"
    try:
        pool = get_connection_pool()
        with pool.connection():
            db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    # Check cache
    cache_status = "unknown"
    try:
        cache = get_query_cache()
        if cache.enabled and cache._initialized:
            cache_status = "healthy"
        else:
            cache_status = "disabled"
    except Exception:
        cache_status = "unhealthy"

    overall_status = (
        "healthy" if db_status == "healthy" else "degraded"
    )

    return HealthResponse(
        status=overall_status,
        database=db_status,
        cache=cache_status,
    )


@router.post(
    "/admin/cache/invalidate",
    tags=["Admin"],
    summary="Invalidate query cache",
    dependencies=[Depends(require_admin)],
)
async def invalidate_cache(pattern: str = "query:*"):
    """
    Invalidate cached queries (admin only).

    - **pattern**: Redis key pattern (default: all queries)

    Returns number of keys deleted.
    """
    cache = get_query_cache()
    deleted = cache.invalidate(pattern)
    return {"deleted": deleted, "pattern": pattern}


# Agentic Semantic Layer Endpoints


@router.get(
    "/semantic-layer/contextualized",
    tags=["Semantic Layer"],
    summary="Get contextualized semantic layer",
)
async def get_contextualized_semantic_layer(
    current_user: dict = Depends(get_current_user),
):
    """
    Get semantic layer adapted to current user's role and permissions.
    
    Returns:
    - Available metrics for the user
    - Role-specific suggested queries
    - Department-specific synonyms
    - Fiscal calendar if configured
    """
    try:
        user_context = _build_user_context(current_user)
        agentic_layer = get_agentic_semantic_layer()
        ctx_layer = agentic_layer.get_contextualized_layer(user_context)
        
        return {
            "metrics": [
                {
                    "name": m.name,
                    "display_name": m.display_name,
                    "description": m.description,
                    "tags": m.tags,
                }
                for m in ctx_layer.metrics.values()
            ],
            "dimensions": [
                {
                    "name": d.name,
                    "display_name": d.display_name,
                    "description": d.description,
                }
                for d in ctx_layer.dimensions.values()
            ],
            "suggested_queries": ctx_layer.suggested_queries,
            "domain_synonyms": ctx_layer.domain_synonyms,
            "fiscal_calendar": ctx_layer.fiscal_calendar,
            "restrictions": ctx_layer.restrictions,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/semantic-layer/version",
    tags=["Semantic Layer"],
    summary="Get semantic layer version for user",
)
async def get_user_semantic_version(
    current_user: dict = Depends(get_current_user),
):
    """
    Get which semantic layer version is assigned to the current user.
    """
    try:
        user_context = _build_user_context(current_user)
        version_mgr = get_version_manager()
        
        version = version_mgr.get_version_for_user(
            user_id=user_context.user_id,
            user_role=user_context.role,
            user_department=user_context.department if user_context.department else None
        )
        
        return {
            "version": version,
            "user_id": user_context.user_id,
            "role": user_context.role,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/semantic-layer/metrics/{metric_name}/enriched",
    tags=["Semantic Layer"],
    summary="Get enriched metric with real-time context",
)
async def get_enriched_metric(
    metric_name: str,
    include_pending: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """
    Get metric definition enriched with real-time context.
    
    Includes:
    - Data freshness warnings
    - Dynamic filter adjustments
    - Context-aware computation notes
    """
    try:
        # Build realtime context
        rt_context = RealtimeContext(
            include_pending=include_pending,
            use_estimated_costs=False,
            exclude_test_data=True
        )
        
        # Get enriched metric
        rt_engine = get_realtime_engine()
        enriched = rt_engine.get_metric_definition(metric_name, rt_context)
        
        return {
            "metric": {
                "name": enriched.metric.name,
                "display_name": enriched.metric.display_name,
                "description": enriched.metric.description,
                "formula": enriched.metric.formula,
                "filters": [f.model_dump() for f in enriched.metric.filters],
            },
            "data_freshness": enriched.data_freshness.value,
            "last_updated": enriched.last_updated.isoformat() if enriched.last_updated else None,
            "warnings": [w.model_dump() for w in enriched.warnings],
            "context_notes": enriched.context_notes,
            "quality_score": rt_engine.get_metric_quality_score(metric_name),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/feedback/query",
    tags=["Feedback"],
    summary="Provide feedback on query result",
)
async def submit_query_feedback(
    query_id: str,
    satisfaction_score: float,
    needed_correction: bool = False,
    correction_details: dict = None,
    current_user: dict = Depends(get_current_user),
):
    """
    Submit feedback on a query result.
    
    - **query_id**: ID of the query being reviewed
    - **satisfaction_score**: 0-1 scale (0=bad, 1=excellent)
    - **needed_correction**: Whether the result needed correction
    - **correction_details**: Details about what was corrected
    """
    try:
        user_context = _build_user_context(current_user)
        version_mgr = get_version_manager()
        
        # Get user's semantic version
        version = version_mgr.get_version_for_user(user_context.user_id)
        
        # Record feedback
        version_mgr.record_user_feedback(
            user_id=user_context.user_id,
            version=version,
            satisfaction_score=satisfaction_score
        )
        
        return {
            "success": True,
            "message": "Feedback recorded",
            "version": version
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/admin/versions/compare",
    tags=["Admin"],
    summary="Compare performance between semantic layer versions",
)
async def compare_versions(
    version_a: str,
    version_b: str,
    current_user: dict = Depends(require_admin),
):
    """
    Compare performance metrics between two semantic layer versions.
    Admin only.
    """
    try:
        version_mgr = get_version_manager()
        comparison = version_mgr.compare_versions(version_a, version_b)
        
        return comparison
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/admin/versions/{version}/promote",
    tags=["Admin"],
    summary="Promote a semantic layer version",
)
async def promote_version(
    version: str,
    rollout_percentage: int,
    current_user: dict = Depends(require_admin),
):
    """
    Promote a semantic layer version to wider rollout.
    Admin only.
    
    - **version**: Version to promote
    - **rollout_percentage**: Target rollout percentage (0-100)
    """
    try:
        if not 0 <= rollout_percentage <= 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="rollout_percentage must be between 0 and 100"
            )
        
        version_mgr = get_version_manager()
        version_mgr.promote_version(version, rollout_percentage)
        
        return {
            "success": True,
            "message": f"Version {version} promoted to {rollout_percentage}% rollout",
            "version": version,
            "rollout_percentage": rollout_percentage
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ===========================
# Phase 2: AI Synonyms & Feedback Endpoints
# ===========================

@router.post(
    "/feedback/submit",
    summary="Submit user feedback",
    description="Submit feedback on query results or synonym suggestions"
)
async def submit_feedback(
    feedback_type: str,
    original_query: Optional[str] = None,
    suggested_term: Optional[str] = None,
    actual_term: Optional[str] = None,
    comment: Optional[str] = None,
    rating: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    """Submit user feedback on queries or synonym suggestions."""
    if not PHASE2_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 2 features not available"
        )
    
    try:
        # Validate feedback type
        try:
            fb_type = FeedbackType(feedback_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid feedback type: {feedback_type}"
            )
        
        # Record feedback
        collector = get_feedback_collector()
        entry = collector.record_feedback(
            user_id=user["username"],
            username=user["username"],
            feedback_type=fb_type,
            original_query=original_query,
            suggested_term=suggested_term,
            actual_term=actual_term,
            comment=comment,
            rating=rating
        )
        
        # If it's synonym feedback, process it immediately
        if fb_type in [FeedbackType.SYNONYM_CORRECT, FeedbackType.SYNONYM_WRONG, FeedbackType.MISSING_SYNONYM]:
            synonym_engine = get_synonym_engine()
            collector.process_synonym_feedback(synonym_engine)
        
        return {
            "success": True,
            "feedback_id": entry.id,
            "message": "Feedback recorded successfully"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/feedback/stats",
    summary="Get feedback statistics",
    description="Get statistics about collected feedback"
)
async def get_feedback_stats(user: dict = Depends(get_current_user)):
    """Get feedback statistics."""
    if not PHASE2_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 2 features not available"
        )
    
    try:
        collector = get_feedback_collector()
        stats = collector.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/feedback/recent",
    summary="Get recent feedback",
    description="Get recent feedback entries (admin only)"
)
async def get_recent_feedback(
    limit: int = 20,
    user: dict = Depends(require_admin)
):
    """Get recent feedback entries."""
    if not PHASE2_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 2 features not available"
        )
    
    try:
        collector = get_feedback_collector()
        recent = collector.get_recent_feedback(limit=limit)
        return {"feedback": recent}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/synonyms/learned",
    summary="Get learned synonyms",
    description="Get all learned synonyms from user feedback"
)
async def get_learned_synonyms(
    term: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get learned synonyms."""
    if not PHASE2_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 2 features not available"
        )
    
    try:
        engine = get_synonym_engine()
        learned = engine.get_learned_synonyms(term=term)
        return {"learned_synonyms": learned}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/synonyms/suggestions",
    summary="Get synonym suggestions",
    description="Get AI-powered synonym suggestions for a query"
)
async def get_synonym_suggestions(
    query: str,
    user: dict = Depends(get_current_user)
):
    """Get AI-powered synonym suggestions."""
    if not PHASE2_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 2 features not available"
        )
    
    try:
        # Use semantic search
        search_index = get_search_index()
        results = search_index.search(
            query=query,
            top_k=5,
            min_relevance=0.6
        )
        
        suggestions = [
            {
                "term": result.name,
                "type": result.type,
                "matched_text": result.matched_term,
                "relevance_score": result.relevance_score,
                "description": result.description
            }
            for result in results
        ]
        
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/synonyms/promote",
    summary="Promote learned synonym to official",
    description="Promote a learned synonym to official status (admin only)"
)
async def promote_synonym(
    term: str,
    synonym: str,
    user: dict = Depends(require_admin)
):
    """Promote a learned synonym to official status."""
    if not PHASE2_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 2 features not available"
        )
    
    try:
        # This would update the semantic layer configuration
        # For now, just return success
        return {
            "success": True,
            "message": f"Synonym '{synonym}' promoted for term '{term}'",
            "note": "Manual update of semantic layer configuration required"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/synonyms/export",
    summary="Export promotable synonyms",
    description="Export learned synonyms ready for promotion (admin only)"
)
async def export_promotable_synonyms(user: dict = Depends(require_admin)):
    """Export synonyms ready for promotion to official status."""
    if not PHASE2_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 2 features not available"
        )
    
    try:
        engine = get_synonym_engine()
        promotable = engine.export_learned_synonyms()
        return {"promotable_synonyms": promotable}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/search-index/rebuild",
    summary="Rebuild search index",
    description="Rebuild the semantic search index (admin only)"
)
async def rebuild_search_index(user: dict = Depends(require_admin)):
    """Rebuild the semantic search index."""
    if not PHASE2_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 2 features not available"
        )
    
    try:
        search_index = get_search_index()
        semantic_layer = get_semantic_layer()
        
        search_index.build_index_from_semantic_layer(semantic_layer)
        stats = search_index.get_stats()
        
        return {
            "success": True,
            "message": "Search index rebuilt successfully",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/search-index/stats",
    summary="Get search index statistics",
    description="Get statistics about the search index"
)
async def get_search_index_stats(user: dict = Depends(get_current_user)):
    """Get search index statistics."""
    if not PHASE2_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 2 features not available"
        )
    
    try:
        search_index = get_search_index()
        stats = search_index.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# =============================================================================
# Phase 3: Data Quality & Matching Endpoints
# =============================================================================


@router.post(
    "/quality/assess-table",
    summary="Assess table data quality",
    description="Assess data quality for a specific table in a connection"
)
async def assess_table_quality(
    connection_id: str,
    table_name: str,
    user: dict = Depends(get_current_user)
):
    """Assess data quality for a database table."""
    try:
        from src.connection import get_connection_manager
        from src.quality.profiler import get_data_profiler
        
        manager = get_connection_manager()
        config = manager.get_connection_config(connection_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection not found: {connection_id}"
            )
        
        # Get connection and fetch sample data
        conn = manager.get_connection(connection_id)
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get database connection"
            )
        
        try:
            cursor = conn.cursor()
            
            # Get row count
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            row_count = cursor.fetchone()[0]
            
            # Get sample data (limit to 1000 rows for profiling)
            cursor.execute(f'SELECT * FROM "{table_name}" LIMIT 1000')
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data = [dict(zip(columns, row)) for row in rows]
            
            # Get column info
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            column_info = {row[0]: {'data_type': row[1], 'is_nullable': row[2] == 'YES'} for row in cursor.fetchall()}
            
            cursor.close()
        finally:
            conn.close()
        
        # Profile the data
        profiler = get_data_profiler()
        profile = profiler.profile_table(table_name, data)
        
        # Calculate quality scores based on profile
        quality_issues = []
        recommendations = []
        dimension_scores = {}
        
        # Completeness: check null ratios
        completeness_scores = []
        for col_name, col_profile in profile.columns.items():
            null_pct = col_profile.null_percentage / 100.0  # Convert from percentage to ratio
            completeness = 1.0 - null_pct
            completeness_scores.append(completeness)
            if null_pct > 0.1:
                quality_issues.append(f"Column '{col_name}' has {null_pct*100:.1f}% null values")
                recommendations.append(f"Consider adding default values or cleaning nulls in '{col_name}'")
        
        dimension_scores['completeness'] = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 1.0
        
        # Uniqueness: based on unique percentage
        uniqueness_scores = []
        for col_name, col_profile in profile.columns.items():
            uniqueness_scores.append(col_profile.unique_percentage / 100.0)  # Convert to ratio
        dimension_scores['uniqueness'] = sum(uniqueness_scores) / len(uniqueness_scores) if uniqueness_scores else 1.0
        
        # Consistency: check for suspected issues
        consistency_issues = 0
        for col_name, col_profile in profile.columns.items():
            if col_profile.suspected_issues:
                consistency_issues += 1
                for issue in col_profile.suspected_issues:
                    quality_issues.append(f"Column '{col_name}': {issue}")
        dimension_scores['consistency'] = 1.0 - (consistency_issues / len(profile.columns)) if profile.columns else 1.0
        
        # Validity: check for outliers
        validity_scores = []
        for col_name, col_profile in profile.columns.items():
            if col_profile.has_outliers:
                validity_scores.append(0.8)
                quality_issues.append(f"Column '{col_name}' has potential outliers")
            else:
                validity_scores.append(1.0)
        dimension_scores['validity'] = sum(validity_scores) / len(validity_scores) if validity_scores else 1.0
        
        # Calculate overall score
        overall_score = sum(dimension_scores.values()) / len(dimension_scores) if dimension_scores else 0.0
        
        # Build column details for response
        columns_detail = []
        for col_name, col_profile in profile.columns.items():
            columns_detail.append({
                "name": col_name,
                "data_type": col_profile.data_type,
                "null_ratio": col_profile.null_percentage,
                "unique_ratio": col_profile.unique_percentage / 100.0,
                "has_outliers": col_profile.has_outliers,
                "sample_values": col_profile.sample_values[:5]
            })
        
        return {
            "entity_name": table_name,
            "entity_type": "table",
            "connection_id": connection_id,
            "overall_score": overall_score,
            "dimension_scores": dimension_scores,
            "issues": quality_issues,
            "recommendations": recommendations,
            "profile": {
                "row_count": row_count,
                "column_count": len(profile.columns),
                "columns": columns_detail
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quality assessment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/quality/assess-connection",
    summary="Assess all tables in a connection",
    description="Run quality assessment on all tables in a database connection"
)
async def assess_connection_quality(
    connection_id: str,
    user: dict = Depends(get_current_user)
):
    """Assess data quality for all tables in a connection."""
    try:
        from src.connection import get_connection_manager
        from src.quality.profiler import get_data_profiler
        
        manager = get_connection_manager()
        config = manager.get_connection_config(connection_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection not found: {connection_id}"
            )
        
        # Get a single connection for all operations
        conn = manager.get_connection(connection_id)
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to establish database connection"
            )
        
        try:
            # Get list of tables from information_schema
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            table_names = [row[0] for row in cursor.fetchall()]
            cursor.close()
            
            profiler = get_data_profiler()
            results = []
            total_score = 0.0
            
            for table_name in table_names:
                try:
                    cursor = conn.cursor()
                    
                    # Get row count
                    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                    row_count = cursor.fetchone()[0]
                    
                    # Get sample data
                    cursor.execute(f'SELECT * FROM "{table_name}" LIMIT 500')
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    data = [dict(zip(columns, row)) for row in rows]
                    
                    cursor.close()
                    
                    # Profile the data
                    profile = profiler.profile_table(table_name, data)
                    
                    # Calculate scores
                    quality_issues = []
                    dimension_scores = {}
                    
                    # Completeness
                    completeness_scores = []
                    for col_name, col_profile in profile.columns.items():
                        null_pct = col_profile.null_percentage / 100.0  # Convert to ratio
                        completeness_scores.append(1.0 - null_pct)
                        if null_pct > 0.1:
                            quality_issues.append(f"Column '{col_name}' has high null ratio")
                    
                    dimension_scores['completeness'] = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 1.0
                    
                    # Uniqueness
                    uniqueness_scores = [cp.unique_percentage / 100.0 for cp in profile.columns.values()]  # Convert to ratio
                    dimension_scores['uniqueness'] = sum(uniqueness_scores) / len(uniqueness_scores) if uniqueness_scores else 1.0
                    
                    # Consistency & Validity
                    dimension_scores['consistency'] = 1.0
                    dimension_scores['validity'] = 1.0
                    
                    overall = sum(dimension_scores.values()) / len(dimension_scores)
                    total_score += overall
                    
                    results.append({
                        "table_name": table_name,
                        "overall_score": overall,
                        "row_count": row_count,
                        "column_count": len(profile.columns),
                        "issues_count": len(quality_issues),
                        "dimension_scores": dimension_scores
                    })
                except Exception as e:
                    logger.error(f"Failed to profile table {table_name}: {e}")
                    results.append({
                        "table_name": table_name,
                        "overall_score": 0.0,
                        "error": str(e)
                    })
            
            avg_score = total_score / len(results) if results else 0.0
            
            return {
                "connection_id": connection_id,
                "table_count": len(results),
                "average_score": avg_score,
                "tables": sorted(results, key=lambda x: x.get('overall_score', 0))
            }
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Connection quality assessment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/quality/assess-metric",
    summary="Assess metric data quality",
    description="Assess data quality for a specific metric"
)
async def assess_metric_quality(
    metric_name: str,
    user: dict = Depends(get_current_user)
):
    """Assess data quality for a specific metric."""
    if not PHASE3_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 3 features not available"
        )
    
    try:
        scorer = get_quality_scorer()
        semantic_layer = get_semantic_layer()
        
        # Get metric configuration
        metric = semantic_layer.get_metric(metric_name)
        if not metric:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metric '{metric_name}' not found"
            )
        
        # Assess quality
        db_conn = get_connection_pool()
        quality_score = scorer.assess_metric_quality(metric_name, metric, db_conn)
        
        return {
            "entity_name": quality_score.entity_name,
            "entity_type": quality_score.entity_type,
            "overall_score": quality_score.overall_score,
            "dimension_scores": {
                dim.value: score 
                for dim, score in quality_score.dimension_scores.items()
            },
            "issues": quality_score.issues,
            "recommendations": quality_score.recommendations
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/quality/assess-dimension",
    summary="Assess dimension data quality",
    description="Assess data quality for a specific dimension"
)
async def assess_dimension_quality(
    dimension_name: str,
    user: dict = Depends(get_current_user)
):
    """Assess data quality for a specific dimension."""
    if not PHASE3_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 3 features not available"
        )
    
    try:
        scorer = get_quality_scorer()
        semantic_layer = get_semantic_layer()
        
        # Get dimension configuration
        dimension = semantic_layer.get_dimension(dimension_name)
        if not dimension:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dimension '{dimension_name}' not found"
            )
        
        # Assess quality
        db_conn = get_connection_pool()
        quality_score = scorer.assess_dimension_quality(dimension_name, dimension, db_conn)
        
        return {
            "entity_name": quality_score.entity_name,
            "entity_type": quality_score.entity_type,
            "overall_score": quality_score.overall_score,
            "dimension_scores": {
                dim.value: score 
                for dim, score in quality_score.dimension_scores.items()
            },
            "issues": quality_score.issues,
            "recommendations": quality_score.recommendations
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/quality/report",
    summary="Get comprehensive quality report",
    description="Get quality report for all metrics and dimensions"
)
async def get_quality_report(
    entity_type: Optional[str] = None,
    min_score: float = 0.0,
    user: dict = Depends(get_current_user)
):
    """Get comprehensive quality report."""
    if not PHASE3_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 3 features not available"
        )
    
    try:
        scorer = get_quality_scorer()
        report = scorer.get_quality_report(entity_type, min_score)
        
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/quality/low-quality",
    summary="Get low quality entities",
    description="Get list of entities below quality threshold"
)
async def get_low_quality_entities(
    threshold: float = 0.7,
    user: dict = Depends(get_current_user)
):
    """Get entities with quality scores below threshold."""
    if not PHASE3_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 3 features not available"
        )
    
    try:
        scorer = get_quality_scorer()
        low_quality = scorer.get_low_quality_entities(threshold)
        
        return {
            "threshold": threshold,
            "count": len(low_quality),
            "entities": [
                {
                    "name": score.entity_name,
                    "type": score.entity_type,
                    "score": score.overall_score,
                    "issues": score.issues,
                    "recommendations": score.recommendations
                }
                for score in low_quality
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/matching/fuzzy-match",
    summary="Find fuzzy matches for a query",
    description="Find fuzzy string matches with typo tolerance"
)
async def fuzzy_match(
    query: str,
    candidates: List[str],
    threshold: float = 0.75,
    max_results: int = 5,
    user: dict = Depends(get_current_user)
):
    """Find fuzzy matches for a query string."""
    if not PHASE3_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 3 features not available"
        )
    
    try:
        matcher = get_fuzzy_matcher()
        matches = matcher.find_matches(query, candidates, threshold, max_results)
        
        return {
            "query": query,
            "matches": [
                {
                    "matched_value": m.matched_value,
                    "score": m.score,
                    "match_type": m.match_type
                }
                for m in matches
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/matching/match-dimension-value",
    summary="Match dimension value with typo tolerance",
    description="Match user input to dimension values with fuzzy matching"
)
async def match_dimension_value(
    dimension_name: str,
    user_input: str,
    threshold: float = 0.75,
    user: dict = Depends(get_current_user)
):
    """Match user input to dimension values."""
    if not PHASE3_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 3 features not available"
        )
    
    try:
        matcher = get_fuzzy_matcher()
        semantic_layer = get_semantic_layer()
        
        # Get dimension
        dimension = semantic_layer.get_dimension(dimension_name)
        if not dimension:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dimension '{dimension_name}' not found"
            )
        
        # For demo, use sample values
        # In production, fetch from database
        dimension_values = ["California", "Texas", "Florida", "New York", "Illinois"]
        
        match = matcher.match_dimension_value(user_input, dimension_values, threshold)
        
        if match:
            return {
                "dimension": dimension_name,
                "user_input": user_input,
                "match": {
                    "matched_value": match.matched_value,
                    "score": match.score,
                    "match_type": match.match_type
                }
            }
        else:
            return {
                "dimension": dimension_name,
                "user_input": user_input,
                "match": None,
                "message": "No match found above threshold"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/matching/corrections",
    summary="Suggest corrections for text",
    description="Suggest corrections for potentially misspelled text"
)
async def suggest_corrections(
    text: str,
    valid_terms: Optional[List[str]] = None,
    user: dict = Depends(get_current_user)
):
    """Suggest corrections for misspelled text."""
    if not PHASE3_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 3 features not available"
        )
    
    try:
        matcher = get_fuzzy_matcher()
        
        # If no valid terms provided, use semantic layer terms
        if not valid_terms:
            semantic_layer = get_semantic_layer()
            valid_terms = (
                list(semantic_layer.get_all_metrics().keys()) +
                list(semantic_layer.get_all_dimensions().keys())
            )
        
        corrections = matcher.suggest_corrections(text, valid_terms)
        
        return {
            "text": text,
            "corrections": [
                {
                    "original": orig,
                    "suggestion": sugg,
                    "score": score
                }
                for orig, sugg, score in corrections
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/profiling/profile-table",
    summary="Profile a data table",
    description="Generate comprehensive data profile for a table"
)
async def profile_table(
    table_name: str,
    sample_size: int = 100,
    user: dict = Depends(get_current_user)
):
    """Profile a data table."""
    if not PHASE3_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 3 features not available"
        )
    
    try:
        profiler = get_data_profiler()
        
        # In production, fetch data from database
        # For demo, return mock profile
        return {
            "message": "Table profiling not yet connected to database",
            "table_name": table_name,
            "note": "Feature available - requires database integration"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/profiling/profiles",
    summary="Get all cached profiles",
    description="Get all cached table profiles"
)
async def get_all_profiles(user: dict = Depends(get_current_user)):
    """Get all cached table profiles."""
    if not PHASE3_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Phase 3 features not available"
        )
    
    try:
        profiler = get_data_profiler()
        profiles = profiler.get_all_profiles()
        
        return {
            "count": len(profiles),
            "profiles": {
                name: {
                    "row_count": profile.row_count,
                    "column_count": profile.column_count,
                    "quality_score": profile.quality_score,
                    "profiled_at": profile.profiled_at.isoformat() if profile.profiled_at else None
                }
                for name, profile in profiles.items()
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ========================================
# ThoughtSpot-like Features: Connection Management & Field Mapping
# ========================================

@router.post(
    "/connections",
    summary="Create database connection",
    description="Create a new database connection (ThoughtSpot Step 1)"
)
async def create_connection(
    config: dict,
    user: dict = Depends(get_current_user)
):
    """Create a new database connection."""
    try:
        from src.connection import ConnectionManager, ConnectionConfig, get_connection_manager
        
        connection_config = ConnectionConfig(**config)
        manager = get_connection_manager()
        result = manager.add_connection(connection_config)
        
        response = {
            "message": "Connection created successfully",
            "connection_id": connection_config.id,
            "name": connection_config.name,
            "saved": result.get('saved', True)
        }
        
        if result.get('pool_error'):
            response["warning"] = f"Connection saved but could not verify connectivity: {result['pool_error']}"
        
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create connection: {str(e)}"
        )


@router.put(
    "/connections/{connection_id}",
    summary="Update database connection",
    description="Update an existing database connection"
)
async def update_connection(
    connection_id: str,
    config: dict,
    user: dict = Depends(get_current_user)
):
    """Update an existing database connection."""
    try:
        from src.connection import ConnectionManager, ConnectionConfig, get_connection_manager
        
        manager = get_connection_manager()
        
        # Check if connection exists
        existing_config = manager.get_connection_config(connection_id)
        if not existing_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection not found: {connection_id}"
            )
        
        # Use the provided connection_id from path, not from config body
        config['id'] = connection_id
        connection_config = ConnectionConfig(**config)
        
        # Close existing pool if it exists (so we can recreate with new config)
        if connection_id in manager.pools:
            try:
                manager.pools[connection_id].closeall()
                del manager.pools[connection_id]
                logger.info(f"Closed existing pool for {connection_id}")
            except Exception as e:
                logger.warning(f"Failed to close pool for {connection_id}: {e}")
        
        # Add/update connection (save_connection handles upsert)
        result = manager.add_connection(connection_config)
        
        response = {
            "message": "Connection updated successfully",
            "connection_id": connection_config.id,
            "name": connection_config.name,
            "saved": result.get('saved', True)
        }
        
        if result.get('pool_error'):
            response["warning"] = f"Connection updated but could not verify connectivity: {result['pool_error']}"
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update connection: {str(e)}"
        )


@router.post(
    "/connections/{connection_id}/discover",
    summary="Discover database schema",
    description="Discover all tables, columns, and relationships (ThoughtSpot Step 1)"
)
async def discover_schema(
    connection_id: str,
    user: dict = Depends(get_current_user)
):
    """Discover database schema for a connection."""
    try:
        from src.connection import get_connection_manager
        
        manager = get_connection_manager()
        
        # Check if connection exists
        config = manager.get_connection_config(connection_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection not found: {connection_id}"
            )
        
        schema = manager.discover_schema(connection_id)
        
        return schema.dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schema discovery failed: {str(e)}"
        )


@router.get(
    "/connections/{connection_id}/schema/{table_name}",
    summary="Get table schema",
    description="Get detailed schema for a specific table"
)
async def get_table_schema(
    connection_id: str,
    table_name: str,
    user: dict = Depends(get_current_user)
):
    """Get table schema details."""
    try:
        from src.connection import get_connection_manager
        
        manager = get_connection_manager()
        schema = manager.get_schema(connection_id)
        
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schema not discovered yet. Run /discover first."
            )
        
        table = schema.tables.get(table_name)
        if not table:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table not found: {table_name}"
            )
        
        return table.dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/connections/{connection_id}/relationships",
    summary="Get foreign key relationships",
    description="Get all foreign key relationships in the schema"
)
async def get_relationships(
    connection_id: str,
    user: dict = Depends(get_current_user)
):
    """Get foreign key relationships."""
    try:
        from src.connection import get_connection_manager
        
        manager = get_connection_manager()
        schema = manager.get_schema(connection_id)
        
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schema not discovered yet. Run /discover first."
            )
        
        return {
            "connection_id": connection_id,
            "relationship_count": len(schema.relationships),
            "relationships": [rel.dict() for rel in schema.relationships]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/connections",
    summary="List connections",
    description="List all configured database connections"
)
async def list_connections(user: dict = Depends(get_current_user)):
    """List all connections."""
    try:
        from src.connection import get_connection_manager
        
        manager = get_connection_manager()
        connections = manager.list_connections()
        
        return {
            "count": len(connections),
            "connections": [conn.dict() for conn in connections]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/connections/{connection_id}/metrics",
    summary="List metrics for connection",
    description="Get all metrics from the semantic layer for a specific connection"
)
async def list_connection_metrics(
    connection_id: str,
    user: dict = Depends(get_current_user)
):
    """List all metrics for a connection."""
    try:
        from src.connection import get_connection_manager
        
        manager = get_connection_manager()
        schema = manager.get_schema(connection_id)
        
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schema not discovered yet. Run /discover first."
            )
        
        # Build semantic layer for this connection
        from src.fieldmap import get_field_mapper
        mapper = get_field_mapper()
        semantic_layer = _build_semantic_layer_from_schema(schema, mapper, connection_id)
        
        metrics_list = [
            {
                "name": metric.name,
                "display_name": metric.display_name,
                "description": metric.description,
                "data_type": metric.data_type.value if hasattr(metric.data_type, 'value') else str(metric.data_type),
                "aggregation": metric.aggregation.value if hasattr(metric.aggregation, 'value') else str(metric.aggregation),
                "base_table": metric.base_table,
                "formula": metric.formula,
                "synonyms": metric.synonyms
            }
            for metric in semantic_layer.metrics.values()
        ]
        
        return {
            "connection_id": connection_id,
            "count": len(metrics_list),
            "metrics": metrics_list
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/connections/{connection_id}/dimensions",
    summary="List dimensions for connection",
    description="Get all dimensions from the semantic layer for a specific connection"
)
async def list_connection_dimensions(
    connection_id: str,
    user: dict = Depends(get_current_user)
):
    """List all dimensions for a connection."""
    try:
        from src.connection import get_connection_manager
        
        manager = get_connection_manager()
        schema = manager.get_schema(connection_id)
        
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schema not discovered yet. Run /discover first."
            )
        
        # Build semantic layer for this connection
        from src.fieldmap import get_field_mapper
        mapper = get_field_mapper()
        semantic_layer = _build_semantic_layer_from_schema(schema, mapper, connection_id)
        
        dimensions_list = [
            {
                "name": dim.name,
                "display_name": dim.display_name,
                "description": dim.description,
                "type": dim.type.value if hasattr(dim.type, 'value') else str(dim.type),
                "table": dim.table,
                "field": dim.field,
                "synonyms": dim.synonyms
            }
            for dim in semantic_layer.dimensions.values()
        ]
        
        return {
            "connection_id": connection_id,
            "count": len(dimensions_list),
            "dimensions": dimensions_list
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/fieldmap/describe",
    summary="Generate AI field descriptions",
    description="Generate business-friendly names and descriptions for table fields (ThoughtSpot Step 2)"
)
async def generate_field_descriptions(
    request: dict,
    user: dict = Depends(get_current_user)
):
    """Generate AI-powered field descriptions."""
    try:
        from src.connection import get_connection_manager
        from src.fieldmap import get_ai_describer, get_field_mapper
        
        connection_id = request.get("connection_id")
        table_name = request.get("table_name")
        
        if not connection_id or not table_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="connection_id and table_name are required"
            )
        
        # Get table metadata
        manager = get_connection_manager()
        schema = manager.get_schema(connection_id)
        
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schema not discovered yet"
            )
        
        table = schema.tables.get(table_name)
        if not table:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table not found: {table_name}"
            )
        
        # Generate descriptions
        describer = get_ai_describer()
        mappings = describer.describe_table(table)
        
        # Store in field mapper
        mapper = get_field_mapper()
        for mapping in mappings:
            mapper.add_mapping(mapping)
        
        return {
            "table_name": table_name,
            "field_count": len(mappings),
            "mappings": [m.dict() for m in mappings]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Field description failed: {str(e)}"
        )


@router.post(
    "/fieldmap/save",
    summary="Save field mapping",
    description="Save or update field mapping with custom descriptions and formulas"
)
async def save_field_mapping(
    request: dict,
    user: dict = Depends(get_current_user)
):
    """Save field mapping."""
    try:
        from src.fieldmap import get_field_mapper, FieldMapping
        
        connection_id = request.get("connection_id")
        table_name = request.get("table_name")
        field_name = request.get("field_name")
        display_name = request.get("display_name")
        description = request.get("description", "")
        default_aggregation = request.get("default_aggregation")
        is_custom = request.get("is_custom", False)
        formula = request.get("formula")
        
        if not all([connection_id, table_name, field_name]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="connection_id, table_name, and field_name are required"
            )
        
        # Create field mapping
        mapping = FieldMapping(
            connection_id=connection_id,
            table_name=table_name,
            column_name=field_name,
            display_name=display_name or field_name,
            description=description,
            synonyms=[],
            default_aggregation=default_aggregation,
            data_type="",  # Will be filled from schema
            semantic_type="",
            business_rule="",
            ai_generated=False
        )
        
        # Store mapping
        mapper = get_field_mapper()
        mapper.add_mapping(mapping)
        
        # Add to vector store for persistent semantic search
        try:
            from src.vector import get_vector_store
            vector_store = get_vector_store()
            
            # Determine if field is measure based on aggregation
            is_measure = default_aggregation is not None and default_aggregation != "none"
            
            # Determine data type from schema
            data_type = request.get("data_type", "string")
            
            vector_store.add_field(
                connection_id=connection_id,
                table_name=table_name,
                column_name=field_name,
                display_name=display_name or field_name,
                description=description,
                is_measure=is_measure,
                synonyms=[],  # Could be expanded to accept synonyms from request
                data_type=data_type,
                default_aggregation=default_aggregation
            )
            logger.info(f"Added field embedding to vector store: {connection_id}:{table_name}.{field_name}")
        except Exception as e:
            logger.warning(f"Failed to add field to vector store: {e}")
            # Don't fail the whole request if vector store fails
        
        # If custom field with formula, store in calculated_metrics table
        if is_custom and formula:
            try:
                from src.database.internal_db import InternalDB
                
                # Check if metric already exists
                existing = InternalDB.execute_query(
                    "SELECT id FROM calculated_metrics WHERE connection_id = %s AND metric_name = %s",
                    (connection_id, field_name),
                    fetch_one=True
                )
                
                if existing:
                    # Update existing metric
                    InternalDB.execute_query(
                        """UPDATE calculated_metrics 
                           SET display_name = %s, description = %s, formula = %s, 
                               base_table = %s, aggregation = %s, updated_at = CURRENT_TIMESTAMP
                           WHERE connection_id = %s AND metric_name = %s""",
                        (display_name or field_name, description, formula, 
                         table_name, default_aggregation or 'calculated', 
                         connection_id, field_name),
                        fetch_all=False
                    )
                    logger.info(f"Updated calculated metric: {connection_id}:{field_name}")
                else:
                    # Insert new metric
                    InternalDB.execute_query(
                        """INSERT INTO calculated_metrics 
                           (connection_id, metric_name, display_name, description, formula, 
                            base_table, aggregation, data_type, format_type, created_by)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (connection_id, field_name, display_name or field_name, description, 
                         formula, table_name, default_aggregation or 'calculated', 
                         'decimal', 'number', user.get('id')),
                        fetch_all=False
                    )
                    logger.info(f"Created calculated metric: {connection_id}:{field_name}")
                    
            except Exception as e:
                logger.error(f"Failed to save calculated metric to database: {e}")
                # Don't fail the request if database save fails
        
        return {
            "success": True,
            "message": "Field mapping saved successfully",
            "mapping": {
                "table_name": table_name,
                "field_name": field_name,
                "display_name": display_name,
                "description": description,
                "default_aggregation": default_aggregation,
                "is_custom": is_custom,
                "formula": formula
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save field mapping: {str(e)}"
        )


@router.get(
    "/fieldmap/{table_name}/{column_name}",
    summary="Get field mapping",
    description="Get field mapping for a specific column"
)
async def get_field_mapping(
    table_name: str,
    column_name: str,
    connection_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get field mapping."""
    try:
        from src.fieldmap import get_field_mapper
        
        mapper = get_field_mapper()
        mapping = mapper.get_mapping(table_name, column_name, connection_id)
        
        if not mapping:
            # Generate fallback
            display_name = mapper.get_display_name(table_name, column_name)
            aggregation = mapper.get_aggregation(table_name, column_name)
            
            return {
                "table_name": table_name,
                "column_name": column_name,
                "display_name": display_name,
                "default_aggregation": aggregation,
                "ai_generated": False
            }
        
        return mapping.dict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/fieldmap/search",
    summary="Search fields",
    description="Search for fields by business name or synonyms"
)
async def search_fields(
    q: str,
    user: dict = Depends(get_current_user)
):
    """Search for fields."""
    try:
        from src.fieldmap import get_field_mapper
        
        mapper = get_field_mapper()
        matches = mapper.search_fields(q)
        
        return {
            "query": q,
            "count": len(matches),
            "results": [m.dict() for m in matches]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/calculated-metrics",
    summary="Get calculated metrics",
    description="Get calculated metrics for a specific connection and optionally for a specific table"
)
async def get_calculated_metrics(
    connection_id: str,
    base_table: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get calculated metrics from database."""
    try:
        from src.database.internal_db import InternalDB
        
        if base_table:
            # Get metrics for specific table and connection
            results = InternalDB.execute_query(
                """SELECT metric_name, display_name, description, formula, 
                          base_table, aggregation, data_type, format_type,
                          synonyms, is_active
                   FROM calculated_metrics 
                   WHERE connection_id = %s AND base_table = %s AND is_active = true
                   ORDER BY metric_name""",
                (connection_id, base_table),
                fetch_all=True
            )
        else:
            # Get all metrics for this connection
            results = InternalDB.execute_query(
                """SELECT metric_name, display_name, description, formula, 
                          base_table, aggregation, data_type, format_type,
                          synonyms, is_active
                   FROM calculated_metrics 
                   WHERE connection_id = %s AND is_active = true
                   ORDER BY base_table, metric_name""",
                (connection_id,),
                fetch_all=True
            )
        
        metrics = []
        for row in results:
            metrics.append({
                "metric_name": row["metric_name"],
                "display_name": row["display_name"],
                "description": row["description"],
                "formula": row["formula"],
                "base_table": row.get("base_table", ""),
                "aggregation": row["aggregation"],
                "data_type": row["data_type"],
                "format_type": row.get("format_type"),
                "synonyms": row["synonyms"] if row.get("synonyms") else [],
                "is_active": row["is_active"]
            })
        
        return {
            "connection_id": connection_id,
            "base_table": base_table,
            "count": len(metrics),
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Failed to fetch calculated metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch calculated metrics: {str(e)}"
        )


@router.delete(
    "/calculated-metrics/{metric_name}",
    summary="Delete calculated metric",
    description="Delete a calculated metric from the database"
)
async def delete_calculated_metric(
    metric_name: str,
    connection_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete calculated metric."""
    try:
        from src.database.internal_db import InternalDB
        
        # Soft delete - set is_active to false
        InternalDB.execute_query(
            "UPDATE calculated_metrics SET is_active = false WHERE connection_id = %s AND metric_name = %s",
            (connection_id, metric_name),
            fetch_all=False
        )
        
        logger.info(f"Deleted calculated metric: {connection_id}:{metric_name}")
        
        return {
            "success": True,
            "message": f"Calculated metric '{metric_name}' deleted successfully"
        }
    except Exception as e:
        logger.error(f"Failed to delete calculated metric: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete calculated metric: {str(e)}"
        )


# Learning System Endpoints


@router.get(
    "/learning/stats",
    summary="Get learning statistics",
    description="Get statistics about query learning and semantic matching"
)
async def get_learning_stats(user: dict = Depends(get_current_user)):
    """Get learning system statistics."""
    try:
        from src.learning.query_learner import get_query_learner
        from src.learning.feedback_collector import get_feedback_collector
        
        learner = get_query_learner()
        feedback = get_feedback_collector()
        
        learning_stats = learner.get_learning_stats()
        feedback_stats = feedback.get_feedback_stats()
        
        return {
            "learning": learning_stats,
            "feedback": feedback_stats,
            "learned_synonyms_sample": dict(list(learner.get_all_learned_synonyms().items())[:10])
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/learning/synonyms/export",
    summary="Export learned synonyms",
    description="Export all learned synonyms as JSON"
)
async def export_learned_synonyms(user: dict = Depends(get_current_user)):
    """Export learned synonyms."""
    try:
        from src.learning.query_learner import get_query_learner
        learner = get_query_learner()
        return {
            "synonyms": learner.get_all_learned_synonyms(),
            "exported_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Query Suggestions Endpoints


@router.post(
    "/connections/{connection_id}/suggestions",
    summary="Get intelligent query suggestions",
    description="Generate AI-powered query suggestions based on partial input and available metrics/dimensions"
)
async def get_query_suggestions(
    connection_id: str,
    partial_query: str = "",
    max_suggestions: int = 6,
    use_llm: bool = True,
    user: dict = Depends(get_current_user)
):
    """
    Get intelligent query suggestions for a connection.
    
    Args:
        connection_id: Database connection ID
        partial_query: User's current input text (optional)
        max_suggestions: Maximum number of suggestions (default 6)
        use_llm: Whether to use LLM for suggestions (default True, falls back to rules if False)
        
    Returns:
        List of query suggestions with text, type, description, and icon
    """
    try:
        from src.connection import get_connection_manager
        from src.api.suggestions import generate_query_suggestions, generate_autocomplete_suggestions
        
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
        
        # Build semantic layer for this connection
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
        
        # Generate suggestions
        if use_llm and partial_query and len(partial_query) > 2:
            # Use LLM for intelligent complete suggestions
            suggestions = generate_query_suggestions(
                partial_query=partial_query,
                metrics=metrics,
                dimensions=dimensions,
                connection_name=conn_config.name,
                max_suggestions=max_suggestions
            )
        else:
            # Use fast autocomplete for short queries or when LLM disabled
            suggestions = generate_autocomplete_suggestions(
                partial_query=partial_query,
                metrics=metrics,
                dimensions=dimensions
            )
        
        return {
            "connection_id": connection_id,
            "partial_query": partial_query,
            "suggestions": suggestions,
            "count": len(suggestions),
            "used_llm": use_llm and len(partial_query) > 2
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


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
    if not ACTIVITY_TRACKING_AVAILABLE:
        # Fall back to regular suggestions
        return await get_query_suggestions(connection_id, partial_query, max_suggestions, True, user)
    
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
    if not ACTIVITY_TRACKING_AVAILABLE:
        return {"success": True, "message": "Activity tracking not available"}
    
    try:
        from src.user import get_user_manager
        
        logger_instance = get_activity_logger()
        user_manager = get_user_manager()
        
        # Get user profile
        user_id = user.get("user_id", user["username"])
        user_profile = user_manager.get_user(user_id)
        user_role = user_profile.role.value if user_profile else "analyst"
        
        activity_type = request.get("activity_type")
        
        if activity_type == "query" or activity_type == "chat":
            # Log query activity
            activity_id = await logger_instance.log_query(
                user_id=user_id,
                query_text=request.get("query_text"),
                connection_id=request.get("connection_id"),
                response_data=request.get("response_data"),
                user_role=user_role,
                metadata=request.get("metadata")
            )
            return {"success": True, "activity_id": activity_id}
        
        elif activity_type == "suggestion_click":
            # Log suggestion click
            activity_id = await logger_instance.log_suggestion_click(
                user_id=user_id,
                suggestion_text=request.get("suggestion_clicked"),
                query_context=request.get("query_context"),
                connection_id=request.get("connection_id"),
                user_role=user_role,
                metadata=request.get("metadata")
            )
            return {"success": True, "activity_id": activity_id}
        
        elif activity_type == "feedback":
            # Log feedback
            activity_id = await logger_instance.log_feedback(
                user_id=user_id,
                query_text=request.get("query_text"),
                rating=request.get("feedback_rating"),
                comments=request.get("comments"),
                connection_id=request.get("connection_id"),
                user_role=user_role,
                metadata=request.get("metadata")
            )
            return {"success": True, "activity_id": activity_id}
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown activity_type: {activity_type}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/activity/patterns",
    summary="Get user query patterns",
    description="Retrieve learned query patterns for the current user and their role"
)
async def get_user_patterns(
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """
    Get learned query patterns for personalization.
    
    Returns patterns for both the user and their role.
    """
    if not ACTIVITY_TRACKING_AVAILABLE:
        return {"user_patterns": [], "role_patterns": []}
    
    try:
        from src.user import get_user_manager
        
        analyzer = get_pattern_analyzer()
        user_manager = get_user_manager()
        
        # Get user profile
        user_id = user.get("user_id", user["username"])
        user_profile = user_manager.get_user(user_id)
        user_role = user_profile.role.value if user_profile else "analyst"
        
        # Get patterns
        user_patterns = await analyzer.get_user_patterns(user_id, limit)
        role_patterns = await analyzer.get_role_patterns(user_role, limit)
        
        return {
            "user_id": user_id,
            "user_role": user_role,
            "user_patterns": [
                {
                    "template": p.query_template,
                    "count": p.usage_count,
                    "last_used": p.last_used.isoformat(),
                    "success_rate": p.success_rate
                }
                for p in user_patterns
            ],
            "role_patterns": [
                {
                    "template": p.query_template,
                    "count": p.usage_count,
                    "last_used": p.last_used.isoformat(),
                    "success_rate": p.success_rate
                }
                for p in role_patterns
            ]
        }
    
    except Exception as e:
        logger.error(f"Failed to get patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/activity/analyze-patterns",
    summary="Analyze user activity and update query patterns",
    description="Manually trigger pattern analysis to populate query_patterns table from user_activity"
)
async def analyze_patterns(
    user_id: Optional[str] = None,
    role: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Analyze user activity and update query patterns.
    
    This will:
    1. Analyze recent queries from user_activity table
    2. Extract common patterns
    3. Populate query_patterns table
    4. Return statistics about patterns created
    
    Args:
        user_id: Analyze specific user (optional, admin only)
        role: Analyze specific role (optional)
    """
    if not ACTIVITY_TRACKING_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Activity tracking not available"
        )
    
    try:
        analyzer = get_pattern_analyzer()
        
        # Get count before analysis
        before_count = InternalDB.execute_query(
            "SELECT COUNT(*) as count FROM query_patterns",
            fetch_one=True
        )
        before_total = before_count['count'] if before_count and isinstance(before_count, dict) else (before_count[0] if before_count else 0)
        
        # Trigger pattern analysis
        logger.info(f"[PATTERN_ANALYSIS] Starting pattern analysis (user_id={user_id}, role={role})")
        analyzer.analyze_and_update_patterns(user_id=user_id, role=role)
        
        # Get count after analysis
        after_count = InternalDB.execute_query(
            "SELECT COUNT(*) as count FROM query_patterns",
            fetch_one=True
        )
        after_total = after_count['count'] if after_count and isinstance(after_count, dict) else (after_count[0] if after_count else 0)
        
        patterns_created = after_total - before_total
        
        # Get some sample patterns
        sample_patterns = InternalDB.execute_query(
            """SELECT pattern_type, target_id, query_template, frequency, success_rate 
               FROM query_patterns 
               ORDER BY updated_at DESC 
               LIMIT 10""",
            fetch_all=True
        )
        
        return {
            "success": True,
            "message": f"Pattern analysis completed",
            "patterns_updated": patterns_created,
            "statistics": {
                "patterns_before": before_total,
                "patterns_after": after_total,
                "patterns_created_or_updated": patterns_created,
                "analyzed_user": user_id or "all",
                "analyzed_role": role or "all"
            },
            "sample_patterns": [
                {
                    "type": p["pattern_type"],
                    "target": p["target_id"],
                    "template": p["query_template"],
                    "frequency": p["frequency"],
                    "success_rate": float(p["success_rate"]) if p["success_rate"] else 0
                }
                for p in sample_patterns
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze patterns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pattern analysis failed: {str(e)}"
        )


@router.get(
    "/activity/stats",
    summary="Get activity tracking statistics",
    description="Get statistics about users, queries, and patterns"
)
async def get_activity_stats(
    user: dict = Depends(get_current_user)
):
    """Get statistics for admin panel."""
    if not ACTIVITY_TRACKING_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Activity tracking not available"
        )
    
    try:
        # Get total users
        users_result = InternalDB.execute_query(
            "SELECT COUNT(DISTINCT user_id) as count FROM user_activity",
            fetch_one=True
        )
        total_users = users_result['count'] if users_result and isinstance(users_result, dict) else (users_result[0] if users_result else 0)
        
        # Get total queries
        queries_result = InternalDB.execute_query(
            "SELECT COUNT(*) as count FROM user_activity",
            fetch_one=True
        )
        total_queries = queries_result['count'] if queries_result and isinstance(queries_result, dict) else (queries_result[0] if queries_result else 0)
        
        # Get total patterns
        patterns_result = InternalDB.execute_query(
            "SELECT COUNT(*) as count FROM query_patterns",
            fetch_one=True
        )
        total_patterns = patterns_result['count'] if patterns_result and isinstance(patterns_result, dict) else (patterns_result[0] if patterns_result else 0)
        
        # Get last analysis time
        last_analysis = InternalDB.execute_query(
            "SELECT MAX(updated_at) as max_time FROM query_patterns",
            fetch_one=True
        )
        if last_analysis:
            last_analysis_time = last_analysis['max_time'] if isinstance(last_analysis, dict) else last_analysis[0]
        else:
            last_analysis_time = None
        
        return {
            "total_users": total_users,
            "total_queries": total_queries,
            "total_patterns": total_patterns,
            "last_analysis": last_analysis_time.isoformat() if last_analysis_time else None
        }
        
    except Exception as e:
        logger.error(f"Failed to get activity stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )



@router.get(
    "/activity/preferences",
    summary="Get user suggestion preferences",
    description="Retrieve user's suggestion preferences"
)
async def get_user_preferences(
    user: dict = Depends(get_current_user)
):
    """
    Get user's suggestion preferences.
    """
    if not ACTIVITY_TRACKING_AVAILABLE:
        return {"enabled_categories": ["all"], "max_suggestions": 6}
    
    try:
        user_id = user.get("user_id", user["username"])
        analyzer = get_pattern_analyzer()
        
        prefs = await analyzer.get_user_preferences(user_id)
        
        if prefs:
            return {
                "enabled_categories": prefs.enabled_categories,
                "max_suggestions": prefs.max_suggestions,
                "auto_execute": prefs.auto_execute
            }
        else:
            # Return defaults
            return {
                "enabled_categories": ["all"],
                "max_suggestions": 6,
                "auto_execute": False
            }
    
    except Exception as e:
        logger.error(f"Failed to get preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put(
    "/activity/preferences",
    summary="Update user suggestion preferences",
    description="Update user's suggestion preferences"
)
async def update_user_preferences(
    request: dict,
    user: dict = Depends(get_current_user)
):
    """
    Update user's suggestion preferences.
    
    Request body:
        - enabled_categories: List of categories (trending, frequent, recommended, similar)
        - max_suggestions: Max number to show (1-20)
        - auto_execute: Whether to auto-execute single suggestions
    """
    if not ACTIVITY_TRACKING_AVAILABLE:
        return {"success": True, "message": "Activity tracking not available"}
    
    try:
        user_id = user.get("user_id", user["username"])
        analyzer = get_pattern_analyzer()
        
        await analyzer.update_user_preferences(
            user_id=user_id,
            enabled_categories=request.get("enabled_categories", ["all"]),
            max_suggestions=request.get("max_suggestions", 6),
            auto_execute=request.get("auto_execute", False)
        )
        
        return {"success": True, "message": "Preferences updated"}
    
    except Exception as e:
        logger.error(f"Failed to update preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============================================================================
# Insights Endpoints
# ============================================================================

@router.post("/insights/generate")
async def generate_insights(
    connection_id: str,
    user_role: Optional[str] = None,
    insight_types: Optional[List[str]] = None,
    time_range_days: int = 7,
    max_insights: int = 10,
    min_confidence: float = 0.6,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate automated insights for a database connection.
    
    Follows architecture:
    Intent → Semantic Layer → SQL → Analytics → Assembler → LLM → UI
    
    - **connection_id**: Database connection to analyze
    - **user_role**: User role/persona (executive, trader, investor, analyst, manager, sales, operations, finance, agent)
    - **insight_types**: Types of insights to generate (pattern, trend, anomaly, etc.)
    - **time_range_days**: Time range for temporal analysis
    - **max_insights**: Maximum number of insights to return
    - **min_confidence**: Minimum confidence threshold (0-1)
    
    Returns role-tailored insight cards with narratives and suggested actions.
    """
    try:
        from src.insights.generator import get_insight_generator
        from src.insights.models import InsightsRequest, InsightType, UserRole
        
        # Parse insight types
        parsed_types = None
        if insight_types:
            parsed_types = [InsightType(t) for t in insight_types]
        
        # Parse user role
        parsed_role = None
        if user_role:
            try:
                parsed_role = UserRole(user_role)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid user role: {user_role}. Valid roles: {[r.value for r in UserRole]}"
                )
        
        # Create request
        request = InsightsRequest(
            connection_id=connection_id,
            user_role=parsed_role,
            insight_types=parsed_types,
            time_range_days=time_range_days,
            max_insights=max_insights,
            min_confidence=min_confidence
        )
        
        # Generate insights
        generator = get_insight_generator()
        response = generator.generate_insights(request)
        
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to generate insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/insights/types")
async def get_insight_types(
    current_user: dict = Depends(get_current_user),
):
    """Get available insight types."""
    from src.insights.models import InsightType
    
    return {
        "types": [
            {
                "value": t.value,
                "label": t.value.replace("_", " ").title(),
                "description": _get_insight_type_description(t)
            }
            for t in InsightType
        ]
    }


def _get_insight_type_description(insight_type) -> str:
    """Get description for insight type."""
    descriptions = {
        "pattern": "Detected patterns and regularities in data",
        "anomaly": "Unusual values and outliers",
        "trend": "Trends and changes over time",
        "comparison": "Comparisons between entities",
        "attribution": "What drives metrics and outcomes",
        "forecast": "Predictions and forecasts",
        "performance": "Performance metrics and KPIs",
        "quality": "Data quality issues and gaps",
        "usage": "Usage patterns and statistics"
    }
    return descriptions.get(insight_type.value, "")


@router.post("/insights/feedback")
async def record_insight_feedback(
    insight_id: str,
    action: str,
    current_user: dict = Depends(get_current_user),
):
    """Record user feedback on an insight for learning."""
    try:
        from src.insights.learner import get_insight_learner, InsightAction, InsightFeedback
        
        learner = get_insight_learner()
        feedback = InsightFeedback(
            insight_id=insight_id,
            user_id=current_user.get("user_id", current_user["username"]),
            action=InsightAction(action)
        )
        learner.record_feedback(feedback)
        stats = learner.get_feedback_stats(insight_id)
        
        return {"insight_id": insight_id, "action": action, "recorded": True, "stats": stats}
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))




# ============================================================================
# USER MANAGEMENT ENDPOINTS
# ============================================================================

@router.post(
    "/users",
    summary="Create user",
    description="Create a new user with role and goals"
)
async def create_user(
    request: CreateUserRequest,
    current_user: dict = Depends(require_admin)
):
    """Create a new user."""
    try:
        from src.user import get_user_manager
        manager = get_user_manager()
        user = manager.create_user(request)
        if user:
            return user.dict()
        else:
            raise HTTPException(status_code=500, detail="User creation returned None")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/users/me",
    summary="Get current user profile",
    description="Get profile for currently authenticated user"
)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user)
):
    """Get current user profile."""
    try:
        from src.user import get_user_manager
        manager = get_user_manager()
        user = manager.get_user_by_username(current_user["username"])
        if not user:
            # Return basic profile from JWT if not in DB yet
            return {
                "username": current_user["username"],
                "role": current_user.get("role", "analyst"),
                "goals": []
            }
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/users",
    summary="List users",
    description="Get list of all users"
)
async def list_users(
    include_inactive: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """List all users."""
    try:
        from src.user import get_user_manager
        manager = get_user_manager()
        users = manager.list_users(include_inactive=include_inactive)
        return {"users": [u.dict() for u in users], "total": len(users)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/users/{user_id}",
    summary="Get user",
    description="Get user profile by ID"
)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get user by ID."""
    try:
        from src.user import get_user_manager
        manager = get_user_manager()
        user = manager.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/users/{user_id}",
    summary="Update user",
    description="Update user profile, role, or goals"
)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update user details."""
    try:
        from src.user import get_user_manager
        manager = get_user_manager()
        
        # Users can update themselves, admins can update anyone
        if current_user.get("role") != "admin" and current_user.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        user = manager.update_user(user_id, request)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/users/{user_id}",
    summary="Delete user",
    description="Delete user (soft delete by default)"
)
async def delete_user(
    user_id: str,
    hard_delete: bool = False,
    current_user: dict = Depends(require_admin)
):
    """Delete a user."""
    try:
        from src.user import get_user_manager
        manager = get_user_manager()
        success = manager.delete_user(user_id, soft_delete=not hard_delete)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"deleted": True, "user_id": user_id, "hard_delete": hard_delete}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/users/goals/suggestions",
    summary="Get goal suggestions",
    description="Get suggested goals for a role"
)
async def get_goal_suggestions(
    role: str,
    current_user: dict = Depends(get_current_user)
):
    """Get suggested goals for a role."""
    try:
        from src.user import get_user_manager, UserRole
        manager = get_user_manager()
        try:
            user_role = UserRole(role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
        
        suggestions = manager.get_goal_suggestions(user_role)
        return {"role": role, "suggested_goals": suggestions}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CHAT SESSION MANAGEMENT
# ============================================

@router.post(
    "/chat/sessions",
    summary="Create a new chat session",
    description="Create a new conversation session"
)
async def create_chat_session(
    connection_id: Optional[str] = None,
    title: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Create a new chat session."""
    try:
        from src.chat import get_chat_manager
        manager = get_chat_manager()
        session = manager.create_session(
            user_id=current_user['username'],
            connection_id=connection_id,
            title=title
        )
        return session.to_dict()
    except Exception as e:
        logger.error(f"Failed to create chat session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/chat/sessions",
    summary="List chat sessions",
    description="Get all chat sessions for the current user"
)
async def list_chat_sessions(
    limit: int = 50,
    include_archived: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """List chat sessions for current user."""
    try:
        from src.chat import get_chat_manager
        manager = get_chat_manager()
        sessions = manager.list_sessions(
            user_id=current_user['username'],
            limit=limit,
            include_archived=include_archived
        )
        return {
            "sessions": [s.to_dict() for s in sessions],
            "total": len(sessions)
        }
    except Exception as e:
        logger.error(f"Failed to list chat sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/chat/sessions/{session_id}",
    summary="Get chat session",
    description="Get a specific chat session with its messages"
)
async def get_chat_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get chat session and its messages."""
    try:
        from src.chat import get_chat_manager
        manager = get_chat_manager()
        
        # Get session
        session = manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Verify ownership
        if session.user_id != current_user['username']:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")
        
        # Get messages
        messages = manager.get_messages(session_id)
        
        return {
            "session": session.to_dict(),
            "messages": [m.to_dict() for m in messages]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/chat/sessions/{session_id}/messages",
    summary="Add message to session",
    description="Add a message to a chat session"
)
async def add_chat_message(
    session_id: str,
    role: str,
    content: str,
    sql_query: Optional[str] = None,
    result_data: Optional[Any] = None,
    result_metadata: Optional[Dict] = None,
    processing_time_ms: Optional[int] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict] = None,
    current_user: dict = Depends(get_current_user)
):
    """Add a message to a chat session."""
    try:
        from src.chat import get_chat_manager
        manager = get_chat_manager()
        
        # Verify session ownership
        session = manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != current_user['username']:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")
        
        # Add message
        message = manager.add_message(
            session_id=session_id,
            role=role,
            content=content,
            sql_query=sql_query,
            result_data=result_data,
            result_metadata=result_metadata,
            processing_time_ms=processing_time_ms,
            error_message=error_message,
            metadata=metadata
        )
        
        return message.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/chat/sessions/{session_id}",
    summary="Update chat session",
    description="Update session title or archive status"
)
async def update_chat_session(
    session_id: str,
    title: Optional[str] = None,
    is_archived: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """Update chat session."""
    try:
        from src.chat import get_chat_manager
        manager = get_chat_manager()
        
        # Verify session ownership
        session = manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != current_user['username']:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")
        
        # Update fields
        if title is not None:
            manager.update_session_title(session_id, title)
        
        if is_archived is not None and is_archived:
            manager.archive_session(session_id)
        
        # Return updated session
        updated_session = manager.get_session(session_id)
        return updated_session.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update chat session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/chat/sessions/{session_id}",
    summary="Delete chat session",
    description="Delete a chat session and all its messages"
)
async def delete_chat_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete chat session."""
    try:
        from src.chat import get_chat_manager
        manager = get_chat_manager()
        
        # Verify session ownership
        session = manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.user_id != current_user['username']:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")
        
        # Delete session
        manager.delete_session(session_id)
        
        return {"success": True, "message": "Session deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete chat session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Example Query Management
# ============================================================================

@router.post(
    "/admin/connections/{connection_id}/generate-examples",
    summary="Generate example queries using LLM",
    description="Admin endpoint to generate example queries for a connection using LLM based on schema analysis"
)
async def generate_example_queries(
    connection_id: str,
    current_user: dict = Depends(require_admin)
):
    """Generate example queries for a connection using LLM."""
    try:
        from src.database.internal_db import InternalDB
        from src.connection import get_connection_manager
        import os
        from openai import OpenAI
        
        # Get connection details
        conn_result = InternalDB.execute_query(
            "SELECT id, name, type, description FROM connections WHERE id = %s",
            (connection_id,)
        )
        if not conn_result or len(conn_result) == 0:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        connection = conn_result[0]
        
        # Get schema for this connection
        manager = get_connection_manager()
        schema = manager.discover_schema(connection_id)
        schema_dict = schema.dict()
        
        # Build schema summary for LLM
        schema_summary = []
        for table_name, table_info in schema_dict['tables'].items():
            measures = [col['name'] for col in table_info['columns'] if col.get('is_measure')]
            dimensions = [col['name'] for col in table_info['columns'] if col.get('is_dimension')]
            schema_summary.append({
                'table': table_name,
                'measures': measures,
                'dimensions': dimensions,
                'row_count': table_info.get('row_count', 0)
            })
        
        # Generate examples using LLM
        client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        
        prompt = f"""You are a business intelligence assistant. Generate 6-8 high-quality example questions that users could ask about this database.

Database: {connection['name']} ({connection['type']})
Schema:
{chr(10).join([f"- Table: {t['table']}, Measures: {', '.join(t['measures'])}, Dimensions: {', '.join(t['dimensions'])}" for t in schema_summary[:5]])}

Requirements:
1. Questions should be natural language, business-focused
2. Cover different query types: aggregations, comparisons, trends, filtering, top N
3. Use actual column names from the schema
4. Make questions realistic for this domain
5. Include time-based questions if date columns exist

Return JSON array of objects with: {{"text": "question", "icon": "emoji", "description": "brief explanation"}}
Use varied emojis: 📊📈📉🗺️⏱️🔍💰👥🏆📋"""

        response = client.chat.completions.create(
            model=os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        import json
        examples = json.loads(response.choices[0].message.content)
        
        # Handle different response formats
        if isinstance(examples, dict):
            examples = examples.get('examples', examples.get('questions', []))
        
        # Delete existing examples for this connection
        InternalDB.execute_query(
            "DELETE FROM connection_example_queries WHERE connection_id = %s",
            (connection_id,)
        )
        
        # Insert new examples
        inserted_count = 0
        for idx, example in enumerate(examples[:8]):  # Limit to 8 examples
            InternalDB.execute_query(
                """INSERT INTO connection_example_queries 
                   (connection_id, query_text, icon, description, display_order, created_by)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    connection_id,
                    example.get('text', example.get('question', '')),
                    example.get('icon', '📊'),
                    example.get('description', ''),
                    idx,
                    current_user['username']
                )
            )
            inserted_count += 1
        
        return {
            "success": True,
            "message": f"Generated {inserted_count} example queries",
            "examples": examples[:8]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate examples: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/connections/{connection_id}/examples",
    summary="Get example queries for connection",
    description="Get admin-generated example queries for a connection"
)
async def get_example_queries(
    connection_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get example queries for a connection."""
    try:
        from src.database.internal_db import InternalDB
        
        results = InternalDB.execute_query(
            """SELECT id, query_text, icon, description, display_order
               FROM connection_example_queries
               WHERE connection_id = %s AND is_active = true
               ORDER BY display_order ASC""",
            (connection_id,)
        )
        
        examples = []
        for row in results:
            examples.append({
                'id': str(row['id']) if isinstance(row, dict) else str(row[0]),
                'text': row['query_text'] if isinstance(row, dict) else row[1],
                'icon': row['icon'] if isinstance(row, dict) else row[2],
                'description': row['description'] if isinstance(row, dict) else row[3]
            })
        
        return {"examples": examples}
    except Exception as e:
        logger.error(f"Failed to fetch examples: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/admin/connections/{connection_id}/examples/{example_id}",
    summary="Update example query",
    description="Admin endpoint to update an example query"
)
async def update_example_query(
    connection_id: str,
    example_id: str,
    query_text: str,
    icon: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: dict = Depends(require_admin)
):
    """Update an example query."""
    try:
        from src.database.internal_db import InternalDB
        
        updates = []
        params = []
        
        if query_text:
            updates.append("query_text = %s")
            params.append(query_text)
        if icon:
            updates.append("icon = %s")
            params.append(icon)
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        if is_active is not None:
            updates.append("is_active = %s")
            params.append(is_active)
        
        if updates:
            params.extend([example_id, connection_id])
            InternalDB.execute_query(
                f"""UPDATE connection_example_queries
                    SET {', '.join(updates)}
                    WHERE id = %s AND connection_id = %s""",
                tuple(params)
            )
        
        return {"success": True, "message": "Example updated"}
    except Exception as e:
        logger.error(f"Failed to update example: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/admin/connections/{connection_id}/examples/{example_id}",
    summary="Delete example query",
    description="Admin endpoint to delete an example query"
)
async def delete_example_query(
    connection_id: str,
    example_id: str,
    current_user: dict = Depends(require_admin)
):
    """Delete an example query."""
    try:
        from src.database.internal_db import InternalDB
        
        InternalDB.execute_query(
            "DELETE FROM connection_example_queries WHERE id = %s AND connection_id = %s",
            (example_id, connection_id)
        )
        
        return {"success": True, "message": "Example deleted"}
    except Exception as e:
        logger.error(f"Failed to delete example: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
