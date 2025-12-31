"""
Agentic Semantic Layer - Context-Aware Dynamic Semantic Layer

This module provides a dynamic, context-aware semantic layer that adapts based on:
- User role and permissions
- Department and business context
- Recent query history
- Data freshness and quality
- Fiscal calendar settings

GENERIC DESIGN:
- Roles are string-based (not enum) for maximum flexibility
- Works for any domain: business, trading, healthcare, manufacturing, etc.
- Departments are configurable strings
- Permissions are tag-based and extensible
"""

from datetime import datetime, date
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel

from src.semantic.loader import get_semantic_layer
from src.semantic.models import Metric, Dimension, SemanticLayer


# Role hierarchy for access level comparison
# These are suggested roles, but ANY string role can be used
ROLE_HIERARCHY = {
    "admin": 100,      # Full access
    "manager": 80,     # High-level access
    "analyst": 60,     # Analysis access
    "specialist": 40,  # Domain-specific access
    "viewer": 20,      # Read-only access
    "guest": 10        # Minimal access
}


class UserContext(BaseModel):
    """User context for personalizing semantic layer.
    
    FLEXIBLE DESIGN - Works for any domain:
    - Business: role="analyst", department="finance"
    - Trading: role="trader", department="equities"  
    - Healthcare: role="doctor", department="cardiology"
    - Manufacturing: role="engineer", department="quality"
    """
    
    user_id: str
    role: str  # Flexible role string (any value works)
    department: Optional[str] = None  # Flexible department string
    permissions: Set[str] = set()  # Metric tags or names user can access
    default_currency: str = "USD"
    fiscal_year_start: Optional[date] = None
    timezone: str = "UTC"
    preferences: Dict[str, Any] = {}
    
    def get_role_level(self) -> int:
        """Get role hierarchy level for comparison.
        
        Returns hierarchy level (0-100) for generic role comparison.
        Unknown roles default to 0.
        """
        return ROLE_HIERARCHY.get(self.role, 0)


class ContextualizedSemanticLayer(BaseModel):
    """Semantic layer adapted to user context."""
    
    metrics: Dict[str, Metric]
    dimensions: Dict[str, Dimension]
    suggested_queries: List[str]
    domain_synonyms: Dict[str, List[str]]
    fiscal_calendar: Optional[Dict[str, Any]] = None
    restrictions: Dict[str, Any] = {}


from pydantic import BaseModel


class AgenticSemanticLayer:
    """
    Context-aware semantic layer that adapts based on user context.
    
    Features:
    - Role-based metric filtering
    - Department-specific synonyms
    - Suggested queries based on role
    - Fiscal calendar awareness
    - Real-time data freshness checks
    """
    
    def __init__(self):
        """Initialize agentic semantic layer."""
        self.base_layer = get_semantic_layer()
        
        # Role-based permissions - flexible string keys
        # Can be loaded from config for different domains
        self.role_permissions = {
            "admin": {"*"},  # All metrics
            "manager": {"*"},  # Broad access
            "analyst": {"financial", "core", "accounting", "operational"},
            "specialist": {"core", "operational"},
            "viewer": {"core"},  # Basic metrics only
            "guest": {"core"},
        }
        
        # Role-based suggested queries - generic templates
        self.role_queries = {
            "admin": [
                "What are the key performance indicators?",
                "Show me high-level trends",
                "Performance overview and summary",
                "Top metrics summary",
                "Strategic insights"
            ],
            "manager": [
                "What are the key metrics for my area?",
                "Show trends over the last quarter",
                "Performance overview",
                "Comparative analysis",
                "Team or area insights"
            ],
            "analyst": [
                "Detailed breakdown by category",
                "Trend analysis over time",
                "Comparative metrics",
                "Data quality check",
                "In-depth analysis"
            ],
            "specialist": [
                "Metrics for my area",
                "Recent activity",
                "Domain-specific trends"
            ],
            "viewer": [
                "Summary overview",
                "Basic metrics"
            ],
        }
        
        # Department-specific synonyms - extensible
        self.department_synonyms = {
            "finance": {
                "revenue": ["recognized_revenue", "accrued_revenue", "bookings"],
                "profit": ["net_income", "bottom_line", "earnings"],
                "client": ["account", "customer", "debtor"]
            },
            "sales": {
                "revenue": ["bookings", "deals_closed", "sales"],
                "client": ["account", "customer", "prospect"],
                "agent": ["rep", "sales_rep", "account_executive"]
            },
            "operations": {
                "transaction": ["order", "deal", "engagement"],
                "agent": ["operator", "team_member", "resource"],
                "client": ["customer", "account", "partner"]
            },
            "trading": {
                "transaction": ["trade", "order", "execution"],
                "amount": ["notional", "value", "volume"],
                "client": ["counterparty", "account"]
            },
            "healthcare": {
                "transaction": ["visit", "appointment", "procedure"],
                "client": ["patient", "case"],
                "agent": ["provider", "physician", "clinician"]
            },
        }
    
    def get_contextualized_layer(
        self, 
        user_context: UserContext,
        query_history: Optional[List[str]] = None
    ) -> ContextualizedSemanticLayer:
        """
        Get semantic layer adapted to user context.
        
        Args:
            user_context: User information and preferences
            query_history: Recent user queries for personalization
        
        Returns:
            Contextualized semantic layer with filtered content
        """
        # Filter metrics by permissions
        filtered_metrics = self._filter_metrics_by_permission(user_context)
        
        # Filter dimensions (dimensions usually available to all)
        filtered_dimensions = self._filter_dimensions(user_context)
        
        # Get role-specific suggested queries
        suggested_queries = self._get_suggested_queries(user_context, query_history)
        
        # Get department-specific synonyms
        domain_synonyms = self._get_domain_synonyms(user_context)
        
        # Get fiscal calendar if configured
        fiscal_calendar = self._get_fiscal_calendar(user_context)
        
        # Build restrictions info
        restrictions = {
            "filtered_metrics": len(self.base_layer.metrics) - len(filtered_metrics),
            "role": user_context.role,  # Already a string, no need for .value
            "permissions": list(user_context.permissions)
        }
        
        return ContextualizedSemanticLayer(
            metrics=filtered_metrics,
            dimensions=filtered_dimensions,
            suggested_queries=suggested_queries,
            domain_synonyms=domain_synonyms,
            fiscal_calendar=fiscal_calendar,
            restrictions=restrictions
        )
    
    def _filter_metrics_by_permission(
        self, 
        context: UserContext
    ) -> Dict[str, Metric]:
        """Filter metrics based on user permissions."""
        # Get allowed tags for this role
        allowed_tags = self.role_permissions.get(context.role, set())
        
        # If user has wildcard permission, return all
        if "*" in allowed_tags or "*" in context.permissions:
            return dict(self.base_layer.metrics)
        
        # Combine role permissions with user-specific permissions
        all_permissions = allowed_tags | context.permissions
        
        # Filter metrics
        filtered = {}
        for name, metric in self.base_layer.metrics.items():
            # Check if metric name is explicitly allowed
            if name in all_permissions:
                filtered[name] = metric
                continue
            
            # Check if any of metric's tags are allowed
            if any(tag in all_permissions for tag in metric.tags):
                filtered[name] = metric
                continue
        
        return filtered
    
    def _filter_dimensions(self, context: UserContext) -> Dict[str, Dimension]:
        """
        Filter dimensions based on user context.
        Most dimensions are available to all, but some may be restricted.
        """
        # For now, return all dimensions
        # In the future, you might restrict sensitive dimensions
        # (e.g., employee_salary dimension only for HR role)
        return dict(self.base_layer.dimensions)
    
    def _get_suggested_queries(
        self, 
        context: UserContext,
        query_history: Optional[List[str]] = None
    ) -> List[str]:
        """
        Get role-specific suggested queries.
        
        Could be enhanced with ML to personalize based on query history.
        """
        base_suggestions = self.role_queries.get(context.role, [])
        
        # TODO: Use query_history to personalize suggestions
        # For now, return role-based suggestions
        return base_suggestions
    
    def _get_domain_synonyms(self, context: UserContext) -> Dict[str, List[str]]:
        """Get department-specific synonyms."""
        if context.department:
            return self.department_synonyms.get(context.department, {})
        return {}
    
    def _get_fiscal_calendar(
        self, 
        context: UserContext
    ) -> Optional[Dict[str, Any]]:
        """
        Get fiscal calendar configuration.
        
        Returns fiscal year info if user has it configured.
        """
        if not context.fiscal_year_start:
            return None
        
        # Calculate current fiscal year
        today = datetime.now().date()
        fy_start = context.fiscal_year_start
        
        # Determine current fiscal year
        if today.month < fy_start.month or (
            today.month == fy_start.month and today.day < fy_start.day
        ):
            current_fy = today.year
        else:
            current_fy = today.year + 1
        
        return {
            "fiscal_year_start": fy_start.isoformat(),
            "current_fiscal_year": current_fy,
            "fiscal_quarter": self._get_fiscal_quarter(today, fy_start),
            "fiscal_month": self._get_fiscal_month(today, fy_start)
        }
    
    def _get_fiscal_quarter(self, date: date, fy_start: date) -> int:
        """Calculate fiscal quarter for a date."""
        # Calculate months since fiscal year start
        months_since_start = (
            (date.year - fy_start.year) * 12 + 
            date.month - fy_start.month
        ) % 12
        
        return (months_since_start // 3) + 1
    
    def _get_fiscal_month(self, date: date, fy_start: date) -> int:
        """Calculate fiscal month for a date."""
        months_since_start = (
            (date.year - fy_start.year) * 12 + 
            date.month - fy_start.month
        ) % 12
        
        return months_since_start + 1
    
    def check_metric_access(
        self, 
        metric_name: str, 
        user_context: UserContext
    ) -> tuple[bool, Optional[str]]:
        """
        Check if user has access to a specific metric.
        
        Returns:
            (has_access, reason_if_denied)
        """
        # Get contextualized layer
        ctx_layer = self.get_contextualized_layer(user_context)
        
        # Check if metric is available
        if metric_name in ctx_layer.metrics:
            return True, None
        
        # Check if metric exists in base layer
        if metric_name in self.base_layer.metrics:
            return False, f"Metric '{metric_name}' requires higher access level"
        
        return False, f"Metric '{metric_name}' not found"
    
    def get_available_metrics(
        self, 
        user_context: UserContext,
        tags: Optional[List[str]] = None
    ) -> List[Metric]:
        """
        Get list of metrics available to user, optionally filtered by tags.
        
        Args:
            user_context: User context
            tags: Filter by these tags
        
        Returns:
            List of available metrics
        """
        ctx_layer = self.get_contextualized_layer(user_context)
        metrics = list(ctx_layer.metrics.values())
        
        if tags:
            metrics = [
                m for m in metrics 
                if any(tag in m.tags for tag in tags)
            ]
        
        return metrics


# Singleton instance
_agentic_layer_instance: Optional[AgenticSemanticLayer] = None


def get_agentic_semantic_layer() -> AgenticSemanticLayer:
    """
    Get or create the global AgenticSemanticLayer instance.
    
    Returns:
        AgenticSemanticLayer singleton
    """
    global _agentic_layer_instance
    if _agentic_layer_instance is None:
        _agentic_layer_instance = AgenticSemanticLayer()
    return _agentic_layer_instance
