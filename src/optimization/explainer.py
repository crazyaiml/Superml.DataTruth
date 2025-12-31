"""
EXPLAIN Plan Analyzer

Analyzes PostgreSQL EXPLAIN output to identify performance issues and suggest optimizations.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import psycopg2


class ExplainNode(BaseModel):
    """Single node in EXPLAIN plan tree."""
    
    node_type: str = Field(description="Type of operation (Seq Scan, Index Scan, etc.)")
    relation_name: Optional[str] = Field(default=None, description="Table/index name")
    startup_cost: float = Field(default=0.0, description="Estimated startup cost")
    total_cost: float = Field(default=0.0, description="Estimated total cost")
    plan_rows: int = Field(default=0, description="Estimated number of rows")
    plan_width: int = Field(default=0, description="Estimated average row width")
    actual_time: Optional[float] = Field(default=None, description="Actual execution time")
    actual_rows: Optional[int] = Field(default=None, description="Actual rows returned")
    children: List["ExplainNode"] = Field(default_factory=list, description="Child nodes")


class ExplainPlan(BaseModel):
    """Complete EXPLAIN plan with analysis."""
    
    query: str = Field(description="SQL query analyzed")
    plan_tree: ExplainNode = Field(description="Root node of plan tree")
    execution_time_ms: Optional[float] = Field(default=None, description="Total execution time")
    planning_time_ms: Optional[float] = Field(default=None, description="Planning time")
    total_cost: float = Field(default=0.0, description="Total estimated cost")
    issues: List[str] = Field(default_factory=list, description="Identified performance issues")
    recommendations: List[str] = Field(default_factory=list, description="Optimization recommendations")


class ExplainAnalyzer:
    """Analyzes EXPLAIN plans and provides optimization recommendations."""
    
    def __init__(self, connection):
        """
        Initialize EXPLAIN analyzer.
        
        Args:
            connection: psycopg2 database connection
        """
        self.connection = connection
    
    def analyze_query(self, sql: str, analyze: bool = False) -> ExplainPlan:
        """
        Run EXPLAIN on query and analyze results.
        
        Args:
            sql: SQL query to analyze
            analyze: Whether to run EXPLAIN ANALYZE (actually executes query)
            
        Returns:
            ExplainPlan with analysis results
        """
        # Run EXPLAIN
        explain_sql = f"EXPLAIN (FORMAT JSON, ANALYZE {analyze}, BUFFERS {analyze}) {sql}"
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(explain_sql)
            result = cursor.fetchone()[0]
            
            # Parse EXPLAIN output
            plan_data = result[0] if isinstance(result, list) else result
            
            # Extract root plan node
            plan_tree = self._parse_plan_node(plan_data['Plan'])
            
            # Create ExplainPlan
            explain_plan = ExplainPlan(
                query=sql,
                plan_tree=plan_tree,
                execution_time_ms=plan_data.get('Execution Time'),
                planning_time_ms=plan_data.get('Planning Time'),
                total_cost=plan_tree.total_cost
            )
            
            # Analyze for issues and recommendations
            self._analyze_plan(explain_plan)
            
            return explain_plan
            
        finally:
            cursor.close()
    
    def _parse_plan_node(self, node_data: Dict[str, Any]) -> ExplainNode:
        """
        Parse a single EXPLAIN plan node.
        
        Args:
            node_data: Raw plan node data from EXPLAIN
            
        Returns:
            Parsed ExplainNode
        """
        node = ExplainNode(
            node_type=node_data.get('Node Type', 'Unknown'),
            relation_name=node_data.get('Relation Name'),
            startup_cost=node_data.get('Startup Cost', 0.0),
            total_cost=node_data.get('Total Cost', 0.0),
            plan_rows=node_data.get('Plan Rows', 0),
            plan_width=node_data.get('Plan Width', 0),
            actual_time=node_data.get('Actual Total Time'),
            actual_rows=node_data.get('Actual Rows')
        )
        
        # Parse child nodes recursively
        if 'Plans' in node_data:
            node.children = [self._parse_plan_node(child) for child in node_data['Plans']]
        
        return node
    
    def _analyze_plan(self, explain_plan: ExplainPlan):
        """
        Analyze EXPLAIN plan and populate issues/recommendations.
        
        Args:
            explain_plan: ExplainPlan to analyze (modified in place)
        """
        self._check_for_seq_scans(explain_plan.plan_tree, explain_plan.issues, explain_plan.recommendations)
        self._check_for_expensive_operations(explain_plan.plan_tree, explain_plan.issues, explain_plan.recommendations)
        self._check_row_estimation_accuracy(explain_plan.plan_tree, explain_plan.issues, explain_plan.recommendations)
        self._check_for_sorts(explain_plan.plan_tree, explain_plan.issues, explain_plan.recommendations)
    
    def _check_for_seq_scans(self, node: ExplainNode, issues: List[str], recommendations: List[str]):
        """Check for sequential scans that might benefit from indexes."""
        if node.node_type == 'Seq Scan' and node.plan_rows > 1000:
            issues.append(f"Sequential scan on {node.relation_name} with {node.plan_rows} rows")
            recommendations.append(
                f"Consider adding an index on {node.relation_name} for frequently filtered columns"
            )
        
        # Recursively check children
        for child in node.children:
            self._check_for_seq_scans(child, issues, recommendations)
    
    def _check_for_expensive_operations(self, node: ExplainNode, issues: List[str], recommendations: List[str]):
        """Check for expensive operations."""
        # High cost operations
        if node.total_cost > 10000:
            issues.append(f"{node.node_type} has high cost: {node.total_cost:.2f}")
            recommendations.append("Review query logic and consider optimizing joins or filters")
        
        # Large result sets
        if node.plan_rows > 100000:
            issues.append(f"{node.node_type} returns {node.plan_rows} rows")
            recommendations.append("Consider adding LIMIT clause or more selective WHERE conditions")
        
        # Recursively check children
        for child in node.children:
            self._check_for_expensive_operations(child, issues, recommendations)
    
    def _check_row_estimation_accuracy(self, node: ExplainNode, issues: List[str], recommendations: List[str]):
        """Check if row estimates are significantly off from actual rows."""
        if node.actual_rows is not None and node.plan_rows > 0:
            ratio = node.actual_rows / node.plan_rows
            
            # If estimate is off by more than 10x
            if ratio > 10 or ratio < 0.1:
                issues.append(
                    f"{node.node_type}: Estimated {node.plan_rows} rows but got {node.actual_rows} rows"
                )
                recommendations.append(
                    f"Run ANALYZE on {node.relation_name or 'relevant tables'} to update statistics"
                )
        
        # Recursively check children
        for child in node.children:
            self._check_row_estimation_accuracy(child, issues, recommendations)
    
    def _check_for_sorts(self, node: ExplainNode, issues: List[str], recommendations: List[str]):
        """Check for expensive sort operations."""
        if node.node_type == 'Sort' and node.plan_rows > 10000:
            issues.append(f"Large sort operation on {node.plan_rows} rows")
            recommendations.append("Consider using indexed columns for ORDER BY or reducing result set before sorting")
        
        # Recursively check children
        for child in node.children:
            self._check_for_sorts(child, issues, recommendations)
    
    def get_optimization_suggestions(self, sql: str) -> Dict[str, Any]:
        """
        Get optimization suggestions for a query without running EXPLAIN ANALYZE.
        
        Args:
            sql: SQL query to analyze
            
        Returns:
            Dictionary with suggestions
        """
        explain_plan = self.analyze_query(sql, analyze=False)
        
        return {
            "query": sql,
            "estimated_cost": explain_plan.total_cost,
            "estimated_rows": explain_plan.plan_tree.plan_rows,
            "issues": explain_plan.issues,
            "recommendations": explain_plan.recommendations,
            "plan_summary": self._get_plan_summary(explain_plan.plan_tree)
        }
    
    def _get_plan_summary(self, node: ExplainNode, depth: int = 0) -> List[str]:
        """
        Get human-readable plan summary.
        
        Args:
            node: Plan node to summarize
            depth: Current depth in tree (for indentation)
            
        Returns:
            List of summary lines
        """
        indent = "  " * depth
        lines = [
            f"{indent}{node.node_type}" +
            (f" on {node.relation_name}" if node.relation_name else "") +
            f" (cost={node.total_cost:.2f}, rows={node.plan_rows})"
        ]
        
        for child in node.children:
            lines.extend(self._get_plan_summary(child, depth + 1))
        
        return lines


# Singleton instance
_explain_analyzer_instance = None


def get_explain_analyzer(connection=None) -> Optional[ExplainAnalyzer]:
    """
    Get or create the global ExplainAnalyzer instance.
    
    Args:
        connection: Database connection (required on first call)
        
    Returns:
        ExplainAnalyzer singleton or None if no connection provided
    """
    global _explain_analyzer_instance
    
    if _explain_analyzer_instance is None:
        if connection is None:
            return None
        _explain_analyzer_instance = ExplainAnalyzer(connection)
    
    return _explain_analyzer_instance
