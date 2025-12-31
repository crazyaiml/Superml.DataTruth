"""
SQL Builder - Convert QueryPlan to SQL

Generates PostgreSQL queries from structured QueryPlan objects.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from src.planner.query_plan import QueryPlan
from src.semantic.loader import get_semantic_layer
from src.semantic.models import Dimension, Join, Metric


class SQLBuilder:
    """Builds SQL queries from QueryPlan objects."""

    def __init__(self, semantic_layer=None) -> None:
        """Initialize SQL builder with semantic layer.
        
        Args:
            semantic_layer: Optional semantic layer instance. If not provided,
                          uses the global semantic layer.
        """
        self.semantic_layer = semantic_layer if semantic_layer is not None else get_semantic_layer()

    def build(self, query_plan: QueryPlan) -> str:
        """
        Build SQL query from QueryPlan.

        Args:
            query_plan: Structured query plan

        Returns:
            PostgreSQL query string

        Raises:
            ValueError: If query plan is invalid or metric/dimensions not found
        """
        # Get metric
        metric = self._get_metric(query_plan.metric)
        
        # Get dimensions
        dimensions = [self._get_dimension(d) for d in query_plan.dimensions]
        
        # Get tables required by filters
        filter_tables = self._get_filter_tables(query_plan.filters)
        
        # Determine required tables and joins
        required_tables = self._get_required_tables(metric, dimensions, filter_tables)
        joins = self._resolve_joins(required_tables)
        
        # Build query parts
        select_clause = self._build_select(metric, dimensions, query_plan.time_grain)
        from_clause = self._build_from(metric.base_table)
        join_clause = self._build_joins(joins)
        where_clause = self._build_where(query_plan, metric)
        group_by_clause = self._build_group_by(dimensions, query_plan.time_grain)
        order_by_clause = self._build_order_by(query_plan.order_by, metric, dimensions)
        limit_offset_clause = self._build_limit_offset(query_plan.limit, query_plan.offset)
        
        # Combine all parts
        sql_parts = [select_clause, from_clause]
        if join_clause:
            sql_parts.append(join_clause)
        if where_clause:
            sql_parts.append(where_clause)
        if group_by_clause:
            sql_parts.append(group_by_clause)
        if order_by_clause:
            sql_parts.append(order_by_clause)
        if limit_offset_clause:
            sql_parts.append(limit_offset_clause)

        return "\n".join(sql_parts) + ";"

    def _get_metric(self, metric_name: str) -> Metric:
        """Get metric by name or synonym."""
        # Try using the built-in method first
        metric = self.semantic_layer.get_metric(metric_name)
        if metric:
            return metric
        raise ValueError(f"Metrics 1 not found: {metric_name}")

    def _get_dimension(self, dimension_name: str) -> Dimension:
        """Get dimension by name or synonym."""
        # Try using the built-in method first
        dimension = self.semantic_layer.get_dimension(dimension_name)
        if dimension:
            return dimension
        raise ValueError(f"Dimension not found: {dimension_name}")

    def _get_filter_tables(self, filters: List) -> Set[str]:
        """Get tables required by filter conditions."""
        tables = set()
        for filter_cond in filters:
            field = filter_cond.field
            # Try to find if it's a dimension
            dim = self.semantic_layer.get_dimension(field)
            if dim:
                tables.add(dim.table)
        return tables

    def _get_required_tables(self, metric: Metric, dimensions: List[Dimension], filter_tables: Set[str] = None) -> Set[str]:
        """Determine all tables needed for the query."""
        tables = {metric.base_table}
        for dim in dimensions:
            tables.add(dim.table)
        if filter_tables:
            tables.update(filter_tables)
        return tables

    def _resolve_joins(self, required_tables: Set[str]) -> List[Join]:
        """Find necessary joins to connect all required tables."""
        if len(required_tables) == 1:
            return []
        
        # Use a simple approach: find joins that connect the required tables
        needed_joins = []
        connected_tables = set()
        
        # Start with the first table (usually the base table)
        base_table = list(required_tables)[0]
        connected_tables.add(base_table)
        
        # Keep adding joins until all tables are connected
        max_iterations = len(required_tables) * 2
        iteration = 0
        
        while connected_tables != required_tables and iteration < max_iterations:
            for join in self.semantic_layer.joins:
                # Check if we can connect a new table from an already connected one
                if join.from_table in connected_tables and join.to_table in required_tables:
                    # Only add if the target table hasn't been connected yet
                    if join.to_table not in connected_tables:
                        needed_joins.append(join)
                        connected_tables.add(join.to_table)
                elif join.to_table in connected_tables and join.from_table in required_tables:
                    # Reverse join - only add if the target table hasn't been connected yet
                    if join.from_table not in connected_tables:
                        needed_joins.append(join)
                        connected_tables.add(join.from_table)
            iteration += 1
        
        return needed_joins

    def _build_select(self, metric: Metric, dimensions: List[Dimension], time_grain: Optional[str] = None) -> str:
        """Build SELECT clause.
        
        Args:
            metric: The metric to aggregate
            dimensions: List of dimensions to group by
            time_grain: Optional temporal aggregation ('day', 'week', 'month', 'quarter', 'year')
        """
        select_items = []
        
        # Add dimensions first
        for dim in dimensions:
            # Check if this is a temporal dimension and time_grain is specified
            is_temporal_dim = self._is_temporal_dimension(dim)
            
            if time_grain and is_temporal_dim:
                # Apply temporal aggregation using DATE_TRUNC with proper formatting
                field_ref = self._get_dimension_field_ref(dim)
                # Use DATE_TRUNC in SELECT but cast to date for cleaner display
                if time_grain == 'day':
                    # Just cast to date for daily granularity
                    select_items.append(f"  DATE_TRUNC('{time_grain}', {field_ref})::date AS \"{dim.display_name}\"")
                elif time_grain in ['month', 'quarter', 'year']:
                    # For month/quarter/year, format as string for better display
                    # But we'll need to keep DATE_TRUNC in GROUP BY
                    if time_grain == 'month':
                        select_items.append(f"  TO_CHAR(DATE_TRUNC('{time_grain}', {field_ref}), 'YYYY-MM') AS \"{dim.display_name}\"")
                    elif time_grain == 'quarter':
                        select_items.append(f"  TO_CHAR(DATE_TRUNC('{time_grain}', {field_ref}), 'YYYY-\\\"Q\\\"Q') AS \"{dim.display_name}\"")
                    elif time_grain == 'year':
                        select_items.append(f"  TO_CHAR(DATE_TRUNC('{time_grain}', {field_ref}), 'YYYY') AS \"{dim.display_name}\"")
                elif time_grain == 'week':
                    # For week, cast to date to show the start of the week
                    select_items.append(f"  DATE_TRUNC('{time_grain}', {field_ref})::date AS \"{dim.display_name}\"")
                else:
                    # Fallback to default DATE_TRUNC
                    select_items.append(f"  DATE_TRUNC('{time_grain}', {field_ref}) AS \"{dim.display_name}\"")
            else:
                # Regular dimension without temporal aggregation
                # Use the field property if available (for dynamic semantic layers)
                if dim.field:
                    select_items.append(f"  {dim.table}.{dim.field} AS \"{dim.display_name}\"")
                elif dim.default_display:
                    # Look up the attribute to get the actual field (for agentic layers)
                    display_field = self._get_dimension_field(dim, dim.default_display)
                    select_items.append(f"  {display_field} AS \"{dim.display_name}\"")
                else:
                    select_items.append(f"  {dim.table}.{dim.name} AS \"{dim.display_name}\"")
        
        # Add metric aggregation
        metric_expr = self._build_metric_expression(metric)
        select_items.append(f"  {metric_expr} AS \"{metric.display_name}\"")
        
        return "SELECT\n" + ",\n".join(select_items)

    def _get_dimension_field(self, dimension: Dimension, attribute_name: str) -> str:
        """Get the field for a dimension attribute."""
        # Look up the attribute by name
        for attr in dimension.attributes:
            if attr.name == attribute_name:
                return attr.field
        # Fallback to table.attribute_name if not found
        return f"{dimension.table}.{attribute_name}"
    
    def _is_temporal_dimension(self, dimension: Dimension) -> bool:
        """Check if a dimension is temporal (date/time based)."""
        dim_name_lower = dimension.name.lower()
        field_lower = dimension.field.lower() if dimension.field else ""
        display_lower = dimension.display_name.lower() if dimension.display_name else ""
        
        temporal_keywords = ['date', 'time', 'timestamp', 'dt', 'created', 'modified', 'updated']
        
        return any(keyword in dim_name_lower or keyword in field_lower or keyword in display_lower
                   for keyword in temporal_keywords)
    
    def _get_dimension_field_ref(self, dimension: Dimension) -> str:
        """Get the full field reference for a dimension (table.field)."""
        if dimension.field:
            return f"{dimension.table}.{dimension.field}"
        elif dimension.default_display:
            return self._get_dimension_field(dimension, dimension.default_display)
        else:
            return f"{dimension.table}.{dimension.name}"

    def _build_metric_expression(self, metric: Metric) -> str:
        """Build metric aggregation expression."""
        formula = metric.formula
        table = metric.base_table
        
        # Check if formula already contains aggregation function
        formula_upper = formula.upper()
        if any(agg in formula_upper for agg in ['SUM(', 'AVG(', 'COUNT(', 'MIN(', 'MAX(']):
            # Formula already has aggregation, use it as-is
            return formula
        
        # Check if formula already includes table name (e.g., "stockprice.change")
        if '.' in formula:
            # Formula is already qualified with table name
            column_ref = formula
        else:
            # Formula is just the column name, qualify it with table
            column_ref = f"{table}.{formula}"
        
        # Simple aggregation patterns - apply aggregation to formula
        if metric.aggregation == "sum":
            return f"SUM({column_ref})"
        elif metric.aggregation == "avg":
            return f"AVG({column_ref})"
        elif metric.aggregation == "count":
            if formula == "*":
                return f"COUNT(*)"
            return f"COUNT({column_ref})"
        elif metric.aggregation == "count_distinct":
            return f"COUNT(DISTINCT {column_ref})"
        elif metric.aggregation == "formula":
            # For calculated metrics like profit_margin
            # This is a simplified version - real implementation would need expression parsing
            return formula
        else:
            # No aggregation specified, just use formula
            return column_ref

    def _build_from(self, base_table: str) -> str:
        """Build FROM clause."""
        return f"FROM {base_table}"

    def _build_joins(self, joins: List[Join]) -> str:
        """Build JOIN clauses."""
        if not joins:
            return ""
        
        join_clauses = []
        for join in joins:
            join_type = join.join_type.upper()
            # Build ON conditions from JoinCondition objects
            on_conditions = []
            for condition in join.on:
                on_conditions.append(
                    f"{join.from_table}.{condition.from_field} = {join.to_table}.{condition.to_field}"
                )
            on_clause = " AND ".join(on_conditions)
            
            join_clauses.append(
                f"{join_type} JOIN {join.to_table} ON {on_clause}"
            )
        
        return "\n".join(join_clauses)

    def _build_where(self, query_plan: QueryPlan, metric: Metric) -> str:
        """Build WHERE clause."""
        conditions = []
        
        # Add metric-level filters (e.g., status='completed')
        if metric.filters:
            for filter_cond in metric.filters:
                field = filter_cond.field
                operator = filter_cond.operator
                value = filter_cond.value
                
                # Check if field already has table prefix
                if '.' in field:
                    field_expr = field
                else:
                    field_expr = f"{metric.base_table}.{field}"
                
                # Format value based on type
                if isinstance(value, str):
                    conditions.append(f"{field_expr} {operator} '{value}'")
                else:
                    conditions.append(f"{field_expr} {operator} {value}")
        
        # Add time range filter
        if query_plan.time_range:
            time_filter = self._build_time_filter(query_plan.time_range, metric.base_table)
            if time_filter:
                conditions.append(time_filter)
        
        # Add user-specified filters
        if query_plan.filters:
            for filter_cond in query_plan.filters:
                field = filter_cond.field
                operator = filter_cond.operator.value if hasattr(filter_cond.operator, 'value') else filter_cond.operator
                value = filter_cond.value
                
                # Try to find the dimension to get the actual field
                dim = self.semantic_layer.get_dimension(field)
                if dim:
                    # Use the actual field property directly (best option)
                    if dim.field:
                        field_expr = f"{dim.table}.{dim.field}"
                    elif dim.name_field:
                        field_expr = f"{dim.table}.{dim.name_field}"
                    else:
                        # Fallback: extract just the field name from dimension name
                        # Remove table qualifiers like "(tablename)" from the field
                        clean_field = field.split('(')[0].strip() if '(' in field else field
                        field_expr = f"{dim.table}.{clean_field}"
                else:
                    # Find which table the field belongs to
                    table = self._find_field_table(field)
                    if not table:
                        # Fallback to metric's base table for derived/unmapped fields
                        table = metric.base_table
                    field_expr = f"{table}.{field}"
                
                if isinstance(value, str):
                    conditions.append(f"{field_expr} {operator} '{value}'")
                else:
                    conditions.append(f"{field_expr} {operator} {value}")
        
        if not conditions:
            return ""
        
        return "WHERE " + "\n  AND ".join(conditions)

    def _build_time_filter(self, time_range, base_table: str) -> Optional[str]:
        """Build time range filter."""
        if not time_range:
            return None
        
        # Check if we have a date/time column in the semantic layer for this table
        # Look for common temporal column names in dimensions
        date_column = None
        if self.semantic_layer:
            for dim in self.semantic_layer.dimensions.values():
                if dim.table == base_table:
                    dim_name_lower = dim.name.lower()
                    field_lower = dim.field.lower()
                    # Check for common date/time column patterns
                    if any(pattern in dim_name_lower or pattern in field_lower 
                           for pattern in ['date', 'time', 'timestamp', 'dt', 'created', 'modified']):
                        date_column = f"{base_table}.{dim.field}"
                        break
        
        # Fallback to transaction_date if no temporal dimension found
        # (This maintains backward compatibility for tables with transaction_date)
        if not date_column:
            # Skip time filtering if no date column is available
            # This allows queries on non-temporal tables (like stockprice) to work
            return None
        
        # Handle period-based ranges
        if time_range.period:
            return self._period_to_date_filter(time_range.period, date_column)
        
        # Handle explicit date ranges
        if time_range.start_date and time_range.end_date:
            return f"{date_column} BETWEEN '{time_range.start_date}' AND '{time_range.end_date}'"
        
        return None

    def _period_to_date_filter(self, period: str, date_column: str) -> str:
        """Convert period string to date filter."""
        # Use a more reasonable reference date for queries
        # In a production system, this would be the current date
        # For demo purposes with historical data, use the latest data date
        today = datetime(2024, 12, 31).date()
        
        if period == "last_quarter":
            # Last complete quarter
            current_quarter = (today.month - 1) // 3
            if current_quarter == 0:
                # Last quarter of previous year
                start = datetime(today.year - 1, 10, 1).date()
                end = datetime(today.year - 1, 12, 31).date()
            else:
                start_month = (current_quarter - 1) * 3 + 1
                end_month = start_month + 2
                start = datetime(today.year, start_month, 1).date()
                # Last day of end_month
                if end_month == 12:
                    end = datetime(today.year, 12, 31).date()
                else:
                    end = datetime(today.year, end_month + 1, 1).date() - timedelta(days=1)
            
            return f"{date_column} BETWEEN '{start}' AND '{end}'"
        
        elif period == "last_year":
            start = datetime(today.year - 1, 1, 1).date()
            end = datetime(today.year - 1, 12, 31).date()
            return f"{date_column} BETWEEN '{start}' AND '{end}'"
        
        elif period == "last_5_years":
            start = datetime(today.year - 5, 1, 1).date()
            end = today
            return f"{date_column} BETWEEN '{start}' AND '{end}'"
        
        elif period == "this_year" or period == "ytd":
            start = datetime(today.year, 1, 1).date()
            return f"{date_column} >= '{start}'"
        
        elif period == "last_month":
            if today.month == 1:
                start = datetime(today.year - 1, 12, 1).date()
                end = datetime(today.year - 1, 12, 31).date()
            else:
                start = datetime(today.year, today.month - 1, 1).date()
                end = datetime(today.year, today.month, 1).date() - timedelta(days=1)
            return f"{date_column} BETWEEN '{start}' AND '{end}'"
        
        elif period == "last_90_days":
            start = today - timedelta(days=90)
            return f"{date_column} >= '{start}'"
        
        else:
            # Default to last 90 days
            start = today - timedelta(days=90)
            return f"{date_column} >= '{start}'"

    def _find_field_table(self, field: str) -> Optional[str]:
        """Find which table contains a field."""
        # Check if it's a dimension name directly
        dim = self.semantic_layer.get_dimension(field)
        if dim and dim.table:
            return dim.table
        
        # Check dimension attributes
        for dim in self.semantic_layer.dimensions.values():
            if field == dim.name:
                if dim.table:
                    return dim.table
            elif field in [attr.name for attr in dim.attributes]:
                return dim.table
        
        # Could also check metric base tables
        return None

    def _build_group_by(self, dimensions: List[Dimension], time_grain: Optional[str] = None) -> str:
        """Build GROUP BY clause.
        
        Args:
            dimensions: List of dimensions to group by
            time_grain: Optional temporal aggregation ('day', 'week', 'month', 'quarter', 'year')
        """
        if not dimensions:
            return ""
        
        group_items = []
        for dim in dimensions:
            # Check if this is a temporal dimension and time_grain is specified
            is_temporal_dim = self._is_temporal_dimension(dim)
            
            if time_grain and is_temporal_dim:
                # Apply temporal aggregation using DATE_TRUNC
                field_ref = self._get_dimension_field_ref(dim)
                group_items.append(f"DATE_TRUNC('{time_grain}', {field_ref})")
            else:
                # Regular grouping without temporal aggregation
                # Use the field property if available (for dynamic semantic layers)
                if dim.field:
                    group_items.append(f"{dim.table}.{dim.field}")
                elif dim.default_display:
                    # Look up the attribute to get the actual field (for agentic layers)
                    display_field = self._get_dimension_field(dim, dim.default_display)
                    group_items.append(display_field)
                else:
                    group_items.append(f"{dim.table}.{dim.name}")
        
        return "GROUP BY " + ", ".join(group_items)

    def _build_order_by(
        self,
        order_by: Optional[Dict[str, str]],
        metric: Metric,
        dimensions: List[Dimension]
    ) -> str:
        """Build ORDER BY clause."""
        if not order_by:
            return ""
        
        order_items = []
        for field, direction in order_by.items():
            direction_upper = direction.upper()
            
            # Check if it's the metric
            if field == metric.name or metric.matches_name(field):
                # Use quoted display name to match SELECT alias
                order_items.append(f'"{metric.display_name}" {direction_upper}')
            else:
                # Check if it's a dimension
                for dim in dimensions:
                    if field == dim.name or dim.matches_name(field):
                        # Use quoted display name to match SELECT alias
                        order_items.append(f'"{dim.display_name}" {direction_upper}')
                        break
        
        if not order_items:
            return ""
        
        return "ORDER BY " + ", ".join(order_items)

    def _build_limit_offset(self, limit: Optional[int], offset: Optional[int]) -> str:
        """
        Build LIMIT and OFFSET clause.
        
        Args:
            limit: Maximum number of rows to return
            offset: Number of rows to skip (for ordinal queries)
        
        Returns:
            LIMIT and OFFSET clause
        """
        if not limit:
            return ""
        
        clause = f"LIMIT {limit}"
        if offset:
            clause += f" OFFSET {offset}"
        
        return clause


def build_sql(query_plan: QueryPlan, semantic_layer=None) -> str:
    """
    Build SQL query from QueryPlan.

    Args:
        query_plan: Structured query plan
        semantic_layer: Optional semantic layer instance. If not provided,
                       uses the global semantic layer.

    Returns:
        PostgreSQL query string

    Example:
        >>> from src.planner.query_plan import QueryPlan, TimeRange
        >>> plan = QueryPlan(
        ...     metric="revenue",
        ...     dimensions=["agent"],
        ...     time_range=TimeRange(period="last_quarter"),
        ...     order_by={"revenue": "desc"},
        ...     limit=10
        ... )
        >>> sql = build_sql(plan)
    """
    builder = SQLBuilder(semantic_layer=semantic_layer)
    return builder.build(query_plan)
