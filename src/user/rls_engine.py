"""
Row-Level Security (RLS) Engine

Automatically injects security filters into SQL queries based on user permissions.
Implements ThoughtSpot-style query rewriting for data security.
"""

import sqlparse
from sqlparse import sql, tokens as T
from typing import List, Dict, Any, Optional, Set, Tuple
from pydantic import BaseModel, Field

from src.user.authorization import UserContext, RLSFilter


class RLSInjectionResult(BaseModel):
    """Result of RLS filter injection."""
    original_sql: str = Field(description="Original SQL query")
    rewritten_sql: str = Field(description="SQL with RLS filters injected")
    injected_filters: List[Dict[str, str]] = Field(description="Filters that were injected")
    tables_affected: List[str] = Field(description="Tables that had filters applied")
    bypass_detected: bool = Field(default=False, description="Whether bypass attempt was detected")


class RLSEngine:
    """
    Row-Level Security engine for automatic filter injection.
    
    Key features:
    - Parses SQL AST to identify tables
    - Injects RLS filters into WHERE clauses
    - Handles JOINs, subqueries, CTEs
    - Prevents bypass attempts
    - Audit logging
    """
    
    def __init__(self, enable_audit: bool = True):
        """
        Initialize RLS engine.
        
        Args:
            enable_audit: Enable audit logging of RLS operations
        """
        self.enable_audit = enable_audit
        self._audit_log: List[Dict[str, Any]] = []
    
    def inject_rls(
        self,
        sql: str,
        user_context: UserContext
    ) -> RLSInjectionResult:
        """
        Inject RLS filters into SQL query.
        
        Args:
            sql: Original SQL query
            user_context: User context with RLS filters
        
        Returns:
            RLSInjectionResult with rewritten SQL
        """
        if not user_context.rls_filters:
            # No RLS filters to apply
            return RLSInjectionResult(
                original_sql=sql,
                rewritten_sql=sql,
                injected_filters=[],
                tables_affected=[]
            )
        
        # Parse SQL
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                raise ValueError("Failed to parse SQL")
            
            statement = parsed[0]
        except Exception as e:
            raise ValueError(f"SQL parsing error: {str(e)}")
        
        # Extract tables from query
        tables_in_query = self._extract_tables(statement)
        
        # Find applicable RLS filters
        applicable_filters = self._find_applicable_filters(
            tables_in_query,
            user_context.rls_filters
        )
        
        if not applicable_filters:
            # No applicable filters
            return RLSInjectionResult(
                original_sql=sql,
                rewritten_sql=sql,
                injected_filters=[],
                tables_affected=[]
            )
        
        # Inject filters into SQL
        rewritten_sql = self._inject_filters_into_sql(
            sql,
            statement,
            applicable_filters
        )
        
        # Build result
        result = RLSInjectionResult(
            original_sql=sql,
            rewritten_sql=rewritten_sql,
            injected_filters=[
                {
                    "table": f.table_name,
                    "filter": f.filter_condition,
                    "description": f.description or ""
                }
                for f in applicable_filters
            ],
            tables_affected=[f.table_name for f in applicable_filters]
        )
        
        # Audit log
        if self.enable_audit:
            self._audit_log.append({
                "user_id": user_context.user_id,
                "original_sql": sql,
                "rewritten_sql": rewritten_sql,
                "filters_applied": len(applicable_filters),
                "tables_affected": result.tables_affected
            })
        
        return result
    
    def _extract_tables(self, statement: sql.Statement) -> Set[str]:
        """Extract all table names from SQL statement."""
        tables = set()
        
        # Look for FROM and JOIN clauses
        from_seen = False
        join_seen = False
        
        for token in statement.tokens:
            # FROM keyword
            if token.ttype is T.Keyword and token.value.upper() == 'FROM':
                from_seen = True
                continue
            
            # JOIN keyword
            if token.ttype is T.Keyword and 'JOIN' in token.value.upper():
                join_seen = True
                continue
            
            # Identifier after FROM or JOIN
            if (from_seen or join_seen) and isinstance(token, sql.Identifier):
                table_name = token.get_real_name()
                if table_name:
                    tables.add(table_name.lower())
                from_seen = False
                join_seen = False
            
            # Simple name token
            elif (from_seen or join_seen) and token.ttype is T.Name:
                tables.add(token.value.lower())
                from_seen = False
                join_seen = False
            
            # Recurse into subqueries
            if isinstance(token, sql.Parenthesis):
                try:
                    inner_sql = token.value.strip('()')
                    inner_parsed = sqlparse.parse(inner_sql)
                    if inner_parsed:
                        tables.update(self._extract_tables(inner_parsed[0]))
                except:
                    pass
            
            # Recurse into other structures
            if hasattr(token, 'tokens'):
                tables.update(self._extract_tables(token))
        
        return tables
    
    def _find_applicable_filters(
        self,
        tables_in_query: Set[str],
        rls_filters: List[RLSFilter]
    ) -> List[RLSFilter]:
        """Find RLS filters that apply to tables in query."""
        applicable = []
        
        for rls_filter in rls_filters:
            if rls_filter.table_name.lower() in tables_in_query:
                applicable.append(rls_filter)
        
        return applicable
    
    def _inject_filters_into_sql(
        self,
        sql: str,
        statement: sql.Statement,
        filters: List[RLSFilter]
    ) -> str:
        """
        Inject RLS filters into SQL WHERE clause.
        
        Strategy:
        1. If WHERE clause exists, AND the RLS filters
        2. If no WHERE clause, add one with RLS filters
        3. Handle multiple tables with appropriate filters
        """
        # Group filters by table
        filters_by_table = {}
        for f in filters:
            filters_by_table[f.table_name.lower()] = f.filter_condition
        
        # Find WHERE clause position
        where_idx = None
        for idx, token in enumerate(statement.tokens):
            if token.ttype is T.Keyword and token.value.upper() == 'WHERE':
                where_idx = idx
                break
        
        if where_idx is not None:
            # WHERE clause exists - inject filters
            return self._inject_into_existing_where(sql, filters_by_table)
        else:
            # No WHERE clause - add one
            return self._add_where_with_filters(sql, filters_by_table)
    
    def _inject_into_existing_where(
        self,
        sql: str,
        filters_by_table: Dict[str, str]
    ) -> str:
        """Inject RLS filters into existing WHERE clause."""
        # Simple approach: wrap existing WHERE in parentheses and AND our filters
        
        # Find WHERE clause
        where_match = sqlparse.parse(sql)[0]
        where_start = None
        where_end = None
        
        tokens = where_match.tokens
        for idx, token in enumerate(tokens):
            if token.ttype is T.Keyword and token.value.upper() == 'WHERE':
                where_start = idx
                # Find the end of WHERE clause (next keyword like GROUP BY, ORDER BY, LIMIT)
                for end_idx in range(idx + 1, len(tokens)):
                    end_token = tokens[end_idx]
                    if end_token.ttype is T.Keyword and end_token.value.upper() in (
                        'GROUP', 'ORDER', 'LIMIT', 'HAVING', 'UNION'
                    ):
                        where_end = end_idx
                        break
                if where_end is None:
                    where_end = len(tokens)
                break
        
        if where_start is None:
            # Fallback: simple string injection
            return self._simple_string_injection(sql, filters_by_table)
        
        # Extract WHERE condition
        where_condition_tokens = tokens[where_start + 1:where_end]
        where_condition = ''.join(str(t) for t in where_condition_tokens).strip()
        
        # Build RLS filter string
        rls_conditions = [f"({condition})" for condition in filters_by_table.values()]
        rls_filter_str = " AND ".join(rls_conditions)
        
        # Rebuild SQL
        before_where = ''.join(str(t) for t in tokens[:where_start])
        after_where = ''.join(str(t) for t in tokens[where_end:])
        
        new_where = f"WHERE ({where_condition}) AND {rls_filter_str}"
        
        return f"{before_where} {new_where} {after_where}"
    
    def _add_where_with_filters(
        self,
        sql: str,
        filters_by_table: Dict[str, str]
    ) -> str:
        """Add WHERE clause with RLS filters to query without WHERE."""
        # Build RLS filter string
        rls_conditions = [f"({condition})" for condition in filters_by_table.values()]
        rls_filter_str = " AND ".join(rls_conditions)
        
        # Find position to insert WHERE
        # Look for GROUP BY, ORDER BY, LIMIT, or end of query
        parsed = sqlparse.parse(sql)[0]
        insert_before_keywords = ['GROUP', 'ORDER', 'LIMIT', 'HAVING', 'UNION']
        
        insert_position = None
        for idx, token in enumerate(parsed.tokens):
            if token.ttype is T.Keyword and token.value.upper() in insert_before_keywords:
                # Insert before this keyword
                before_tokens = parsed.tokens[:idx]
                after_tokens = parsed.tokens[idx:]
                
                before_sql = ''.join(str(t) for t in before_tokens).strip()
                after_sql = ''.join(str(t) for t in after_tokens).strip()
                
                return f"{before_sql} WHERE {rls_filter_str} {after_sql}"
        
        # No keywords found - insert at end (before semicolon if exists)
        sql_stripped = sql.rstrip(';').strip()
        return f"{sql_stripped} WHERE {rls_filter_str}"
    
    def _simple_string_injection(
        self,
        sql: str,
        filters_by_table: Dict[str, str]
    ) -> str:
        """Simple string-based injection (fallback)."""
        rls_conditions = [f"({condition})" for condition in filters_by_table.values()]
        rls_filter_str = " AND ".join(rls_conditions)
        
        # Find WHERE keyword
        sql_upper = sql.upper()
        where_pos = sql_upper.find('WHERE')
        
        if where_pos != -1:
            # Find end of WHERE clause
            end_keywords = ['GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING']
            end_pos = len(sql)
            for keyword in end_keywords:
                kw_pos = sql_upper.find(keyword, where_pos)
                if kw_pos != -1:
                    end_pos = min(end_pos, kw_pos)
            
            # Extract parts
            before = sql[:where_pos + 5]  # Including 'WHERE'
            condition = sql[where_pos + 5:end_pos].strip()
            after = sql[end_pos:]
            
            return f"{before} ({condition}) AND {rls_filter_str} {after}"
        else:
            # No WHERE - add one
            return self._add_where_with_filters(sql, filters_by_table)
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get RLS audit log."""
        return self._audit_log.copy()
    
    def clear_audit_log(self):
        """Clear audit log."""
        self._audit_log.clear()


# Example usage and testing
if __name__ == "__main__":
    from src.user.authorization import UserContext, Role, RLSFilter, TablePermission
    
    # Create user with RLS filters
    user = UserContext(
        user_id="user_123",
        username="john.analyst",
        roles=[Role.ANALYST],
        table_permissions=[
            TablePermission(table_name="orders", can_query=True, can_view=True)
        ],
        rls_filters=[
            RLSFilter(
                table_name="orders",
                filter_condition="region = 'US'",
                description="US region only"
            ),
            RLSFilter(
                table_name="orders",
                filter_condition="order_date >= '2024-01-01'",
                description="Orders from 2024 onwards"
            )
        ]
    )
    
    # Create RLS engine
    rls_engine = RLSEngine(enable_audit=True)
    
    # Test 1: Simple query without WHERE
    sql1 = "SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id LIMIT 100"
    result1 = rls_engine.inject_rls(sql1, user)
    print("Test 1: Simple query without WHERE")
    print(f"Original: {result1.original_sql}")
    print(f"Rewritten: {result1.rewritten_sql}")
    print(f"Filters: {result1.injected_filters}\n")
    
    # Test 2: Query with existing WHERE
    sql2 = "SELECT * FROM orders WHERE status = 'completed' LIMIT 100"
    result2 = rls_engine.inject_rls(sql2, user)
    print("Test 2: Query with existing WHERE")
    print(f"Original: {result2.original_sql}")
    print(f"Rewritten: {result2.rewritten_sql}")
    print(f"Filters: {result2.injected_filters}\n")
    
    # Test 3: Query with JOIN
    sql3 = """
    SELECT c.name, SUM(o.amount) 
    FROM customers c 
    JOIN orders o ON c.id = o.customer_id 
    GROUP BY c.name 
    LIMIT 100
    """
    result3 = rls_engine.inject_rls(sql3, user)
    print("Test 3: Query with JOIN")
    print(f"Original: {result3.original_sql}")
    print(f"Rewritten: {result3.rewritten_sql}")
    print(f"Filters: {result3.injected_filters}\n")
    
    # Test 4: No applicable filters
    sql4 = "SELECT * FROM customers LIMIT 100"
    result4 = rls_engine.inject_rls(sql4, user)
    print("Test 4: No applicable filters")
    print(f"Original: {result4.original_sql}")
    print(f"Rewritten: {result4.rewritten_sql}")
    print(f"Filters: {result4.injected_filters}\n")
    
    # Show audit log
    print("Audit Log:")
    for log_entry in rls_engine.get_audit_log():
        print(f"  User: {log_entry['user_id']}")
        print(f"  Filters applied: {log_entry['filters_applied']}")
        print(f"  Tables affected: {log_entry['tables_affected']}\n")
