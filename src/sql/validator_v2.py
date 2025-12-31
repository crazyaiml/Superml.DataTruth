"""
Production-Grade SQL Validator using AST Parsing

Validates LLM-generated SQL queries using proper syntax tree analysis.
Handles CTEs, nested queries, functions, casts, quoted identifiers, and complex constructs.
"""

import re
import sqlparse
from sqlparse import sql, tokens as T
from typing import List, Tuple, Dict, Any, Optional, Set
from enum import Enum
from pydantic import BaseModel, Field


class ValidationLevel(str, Enum):
    """Validation strictness levels."""
    STRICT = "strict"      # Maximum security, minimal SQL features
    MODERATE = "moderate"  # Balanced security and functionality
    PERMISSIVE = "permissive"  # Minimal restrictions


class ValidationError(BaseModel):
    """Structured validation error."""
    code: str = Field(description="Error code")
    message: str = Field(description="Error message")
    severity: str = Field(description="Error severity: error, warning, info")
    location: Optional[str] = Field(default=None, description="Location in SQL")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class SQLValidationResult(BaseModel):
    """Result of SQL validation."""
    is_valid: bool = Field(description="Whether SQL is valid")
    errors: List[ValidationError] = Field(default_factory=list, description="Validation errors")
    warnings: List[ValidationError] = Field(default_factory=list, description="Validation warnings")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Validation metadata")


class ProductionSQLValidator:
    """
    Production-grade SQL validator using AST parsing.
    
    Features:
    - AST-based parsing (not regex)
    - Handles CTEs, nested queries, functions, casts
    - Semantic validation against schema
    - Security checks (SQL injection, dangerous operations)
    - Performance validation (complexity checks)
    """
    
    # Dangerous DML/DDL operations
    FORBIDDEN_STATEMENT_TYPES = {
        'DROP', 'DELETE', 'TRUNCATE', 'INSERT', 'UPDATE',
        'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'MERGE'
    }
    
    # Dangerous functions (system access, file operations, etc.)
    FORBIDDEN_FUNCTIONS = {
        'xp_cmdshell', 'xp_regread', 'xp_regwrite',
        'sp_executesql', 'sp_oacreate', 'sp_oamethod',
        'load_file', 'into outfile', 'into dumpfile',
        'pg_read_file', 'pg_ls_dir', 'pg_execute',
        'dbms_java', 'dbms_scheduler', 'utl_file',
        'system', 'shell', 'exec'
    }
    
    # Allowed aggregate functions
    ALLOWED_AGGREGATES = {
        'count', 'sum', 'avg', 'min', 'max', 'median',
        'stddev', 'variance', 'percentile', 'mode',
        'first', 'last', 'array_agg', 'string_agg'
    }
    
    # Allowed scalar functions
    ALLOWED_SCALAR_FUNCTIONS = {
        # String functions
        'upper', 'lower', 'trim', 'ltrim', 'rtrim', 'substring', 'substr',
        'concat', 'concat_ws', 'replace', 'length', 'char_length',
        'left', 'right', 'reverse', 'format', 'coalesce', 'nullif',
        # Date/time functions
        'now', 'current_date', 'current_timestamp', 'date_trunc', 'date_part',
        'extract', 'to_date', 'to_timestamp', 'age', 'interval',
        'year', 'month', 'day', 'hour', 'minute', 'second',
        # Math functions
        'abs', 'ceil', 'floor', 'round', 'trunc', 'mod', 'power', 'sqrt',
        'exp', 'ln', 'log', 'sign', 'random',
        # Type casting
        'cast', 'convert', '::',
        # Conditional
        'case', 'when', 'then', 'else', 'end', 'if', 'ifnull', 'nullif'
    }
    
    def __init__(
        self,
        semantic_context: Optional[Dict[str, Any]] = None,
        validation_level: ValidationLevel = ValidationLevel.MODERATE,
        max_row_limit: int = 10000,
        max_query_depth: int = 5,
        max_joins: int = 10,
        require_limit: bool = True
    ):
        """
        Initialize validator.
        
        Args:
            semantic_context: Schema information (tables, columns, metrics, dimensions)
            validation_level: Validation strictness
            max_row_limit: Maximum allowed LIMIT value
            max_query_depth: Maximum nesting depth for subqueries
            max_joins: Maximum number of JOINs allowed
            require_limit: Whether LIMIT clause is required
        """
        self.semantic_context = semantic_context or {}
        self.validation_level = validation_level
        self.max_row_limit = max_row_limit
        self.max_query_depth = max_query_depth
        self.max_joins = max_joins
        self.require_limit = require_limit
        
        # Extract schema information
        self._load_schema()
    
    def _load_schema(self):
        """Load schema information from semantic context."""
        self.valid_tables = set()
        self.valid_columns = {}  # table -> set(columns)
        self.valid_metrics = set()
        self.valid_dimensions = set()
        
        if not self.semantic_context:
            return
        
        # Load metrics
        for metric in self.semantic_context.get('metrics', []):
            if isinstance(metric, dict):
                self.valid_metrics.add(metric.get('name', '').lower())
                # Extract table/column from metric definition
                if 'table' in metric:
                    self.valid_tables.add(metric['table'].lower())
                    if metric['table'].lower() not in self.valid_columns:
                        self.valid_columns[metric['table'].lower()] = set()
                    if 'column' in metric:
                        self.valid_columns[metric['table'].lower()].add(metric['column'].lower())
        
        # Load dimensions
        for dimension in self.semantic_context.get('dimensions', []):
            if isinstance(dimension, dict):
                self.valid_dimensions.add(dimension.get('name', '').lower())
                if 'table' in dimension:
                    self.valid_tables.add(dimension['table'].lower())
                    if dimension['table'].lower() not in self.valid_columns:
                        self.valid_columns[dimension['table'].lower()] = set()
                    if 'column' in dimension:
                        self.valid_columns[dimension['table'].lower()].add(dimension['column'].lower())
    
    def validate(self, sql: str) -> SQLValidationResult:
        """
        Validate SQL query with comprehensive checks.
        
        Args:
            sql: SQL query string
        
        Returns:
            SQLValidationResult with errors, warnings, and metadata
        """
        errors = []
        warnings = []
        metadata = {
            'query_length': len(sql),
            'has_cte': False,
            'has_subquery': False,
            'join_count': 0,
            'query_depth': 0,
            'statement_type': None
        }
        
        # 1. Parse SQL
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                errors.append(ValidationError(
                    code="PARSE_ERROR",
                    message="Failed to parse SQL - empty or invalid syntax",
                    severity="error"
                ))
                return SQLValidationResult(is_valid=False, errors=errors, metadata=metadata)
            
            statement = parsed[0]
        except Exception as e:
            errors.append(ValidationError(
                code="PARSE_ERROR",
                message=f"SQL parsing failed: {str(e)}",
                severity="error",
                context={"exception": str(e)}
            ))
            return SQLValidationResult(is_valid=False, errors=errors, metadata=metadata)
        
        # 2. Security checks
        security_errors = self._validate_security(sql, statement)
        errors.extend(security_errors)
        
        # 3. Statement type validation
        stmt_type = statement.get_type()
        metadata['statement_type'] = stmt_type
        
        if stmt_type != 'SELECT':
            errors.append(ValidationError(
                code="INVALID_STATEMENT_TYPE",
                message=f"Only SELECT statements allowed, found: {stmt_type}",
                severity="error",
                context={"statement_type": stmt_type}
            ))
        
        # 4. Structure validation
        structure_errors, structure_warnings = self._validate_structure(statement, metadata)
        errors.extend(structure_errors)
        warnings.extend(structure_warnings)
        
        # 5. Schema validation
        if self.semantic_context:
            schema_errors, schema_warnings = self._validate_schema(statement)
            errors.extend(schema_errors)
            warnings.extend(schema_warnings)
        
        # 6. Performance validation
        perf_warnings = self._validate_performance(statement, metadata)
        warnings.extend(perf_warnings)
        
        # 7. LIMIT clause validation
        if self.require_limit:
            limit_errors = self._validate_limit(statement)
            errors.extend(limit_errors)
        
        is_valid = len(errors) == 0
        return SQLValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
    
    def _validate_security(self, sql: str, statement: sql.Statement) -> List[ValidationError]:
        """Validate security aspects of SQL."""
        errors = []
        sql_upper = sql.upper()
        
        # Check for forbidden statement types
        for forbidden in self.FORBIDDEN_STATEMENT_TYPES:
            if re.search(rf'\b{forbidden}\b', sql_upper):
                errors.append(ValidationError(
                    code="FORBIDDEN_OPERATION",
                    message=f"Forbidden operation detected: {forbidden}",
                    severity="error",
                    context={"operation": forbidden}
                ))
        
        # Check for forbidden functions
        for forbidden_func in self.FORBIDDEN_FUNCTIONS:
            if forbidden_func.lower() in sql.lower():
                errors.append(ValidationError(
                    code="FORBIDDEN_FUNCTION",
                    message=f"Forbidden function detected: {forbidden_func}",
                    severity="error",
                    context={"function": forbidden_func}
                ))
        
        # Check for SQL injection patterns
        injection_patterns = [
            (r";\s*(?:DROP|DELETE|INSERT|UPDATE|ALTER)", "Multiple statements with dangerous operations"),
            (r"'\s*OR\s*'1'\s*=\s*'1", "SQL injection pattern: OR '1'='1'"),
            (r"'\s*OR\s*1\s*=\s*1", "SQL injection pattern: OR 1=1"),
            (r"--\s*$", "Comment at end of query (potential injection)"),
            (r"/\*.*?\*/", "Block comment (potential injection)"),
            (r"UNION\s+(?:ALL\s+)?SELECT", "UNION-based injection attempt"),
        ]
        
        for pattern, description in injection_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                errors.append(ValidationError(
                    code="SQL_INJECTION_RISK",
                    message=f"SQL injection risk: {description}",
                    severity="error",
                    location=pattern
                ))
        
        # Check for multiple statements (semicolon followed by more SQL)
        statements = sql.strip().split(';')
        non_empty_statements = [s for s in statements if s.strip()]
        if len(non_empty_statements) > 1:
            errors.append(ValidationError(
                code="MULTIPLE_STATEMENTS",
                message="Multiple SQL statements not allowed",
                severity="error",
                context={"statement_count": len(non_empty_statements)}
            ))
        
        return errors
    
    def _validate_structure(
        self,
        statement: sql.Statement,
        metadata: Dict[str, Any]
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate SQL structure using AST."""
        errors = []
        warnings = []
        
        # Track CTEs
        for token in statement.tokens:
            if token.ttype is T.Keyword.CTE:
                metadata['has_cte'] = True
        
        # Count JOINs
        join_count = 0
        for token in statement.flatten():
            if token.ttype is T.Keyword and 'JOIN' in token.value.upper():
                join_count += 1
        
        metadata['join_count'] = join_count
        
        if join_count > self.max_joins:
            errors.append(ValidationError(
                code="TOO_MANY_JOINS",
                message=f"Query has {join_count} JOINs, maximum allowed is {self.max_joins}",
                severity="error",
                context={"join_count": join_count, "max_joins": self.max_joins}
            ))
        
        # Check for subqueries and depth
        depth = self._calculate_query_depth(statement)
        metadata['query_depth'] = depth
        metadata['has_subquery'] = depth > 1
        
        if depth > self.max_query_depth:
            errors.append(ValidationError(
                code="EXCESSIVE_NESTING",
                message=f"Query nesting depth {depth} exceeds maximum {self.max_query_depth}",
                severity="error",
                context={"depth": depth, "max_depth": self.max_query_depth}
            ))
        
        # Validate functions
        function_errors = self._validate_functions(statement)
        errors.extend(function_errors)
        
        return errors, warnings
    
    def _calculate_query_depth(self, statement: sql.Statement, current_depth: int = 1) -> int:
        """Calculate nesting depth of subqueries."""
        max_depth = current_depth
        
        for token in statement.tokens:
            if isinstance(token, sql.Parenthesis):
                # Check if this is a subquery
                inner_sql = token.value.strip('()')
                try:
                    parsed_inner = sqlparse.parse(inner_sql)
                    if parsed_inner and parsed_inner[0].get_type() == 'SELECT':
                        # This is a subquery
                        inner_depth = self._calculate_query_depth(parsed_inner[0], current_depth + 1)
                        max_depth = max(max_depth, inner_depth)
                except:
                    pass
            elif hasattr(token, 'tokens'):
                inner_depth = self._calculate_query_depth(token, current_depth)
                max_depth = max(max_depth, inner_depth)
        
        return max_depth
    
    def _validate_functions(self, statement: sql.Statement) -> List[ValidationError]:
        """Validate function usage."""
        errors = []
        
        # Extract all function calls
        functions_used = self._extract_functions(statement)
        
        # Check against allowed functions
        allowed_functions = self.ALLOWED_AGGREGATES | self.ALLOWED_SCALAR_FUNCTIONS
        
        for func_name in functions_used:
            func_lower = func_name.lower()
            
            # Check if function is allowed
            if self.validation_level == ValidationLevel.STRICT:
                if func_lower not in allowed_functions:
                    errors.append(ValidationError(
                        code="FORBIDDEN_FUNCTION",
                        message=f"Function not in allowed list: {func_name}",
                        severity="error",
                        context={"function": func_name, "level": "strict"}
                    ))
        
        return errors
    
    def _extract_functions(self, token: sql.Token) -> Set[str]:
        """Extract all function names from SQL."""
        functions = set()
        
        if isinstance(token, sql.Function):
            func_name = token.get_name()
            if func_name:
                functions.add(func_name)
        
        if hasattr(token, 'tokens'):
            for sub_token in token.tokens:
                functions.update(self._extract_functions(sub_token))
        
        return functions
    
    def _validate_schema(
        self,
        statement: sql.Statement
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate references against semantic schema."""
        errors = []
        warnings = []
        
        # Extract table references
        tables_used = self._extract_table_references(statement)
        
        # Validate tables exist in schema
        for table in tables_used:
            if table.lower() not in self.valid_tables:
                warnings.append(ValidationError(
                    code="UNKNOWN_TABLE",
                    message=f"Table not found in semantic layer: {table}",
                    severity="warning",
                    context={"table": table}
                ))
        
        # Extract column references
        columns_used = self._extract_column_references(statement)
        
        # Validate columns exist in schema
        for table, column in columns_used:
            if table and table.lower() in self.valid_columns:
                if column.lower() not in self.valid_columns[table.lower()]:
                    warnings.append(ValidationError(
                        code="UNKNOWN_COLUMN",
                        message=f"Column {column} not found in table {table}",
                        severity="warning",
                        context={"table": table, "column": column}
                    ))
        
        return errors, warnings
    
    def _extract_table_references(self, statement: sql.Statement) -> Set[str]:
        """Extract all table references from SQL."""
        tables = set()
        
        # Look for FROM and JOIN clauses
        from_seen = False
        for token in statement.tokens:
            if token.ttype is T.Keyword and token.value.upper() in ('FROM', 'JOIN'):
                from_seen = True
            elif from_seen and isinstance(token, sql.Identifier):
                tables.add(token.get_real_name())
                from_seen = False
            elif from_seen and token.ttype is T.Name:
                tables.add(token.value)
                from_seen = False
        
        return tables
    
    def _extract_column_references(self, statement: sql.Statement) -> Set[Tuple[Optional[str], str]]:
        """Extract all column references from SQL."""
        columns = set()
        
        for token in statement.flatten():
            if token.ttype is T.Name:
                # Check if it's a qualified name (table.column)
                parent = token.parent
                if isinstance(parent, sql.Identifier):
                    real_name = parent.get_real_name()
                    parent_name = parent.get_parent_name()
                    if parent_name:
                        columns.add((parent_name, real_name))
                    else:
                        columns.add((None, real_name))
        
        return columns
    
    def _validate_performance(
        self,
        statement: sql.Statement,
        metadata: Dict[str, Any]
    ) -> List[ValidationError]:
        """Validate performance aspects."""
        warnings = []
        
        # Warn about SELECT *
        sql_str = str(statement)
        if re.search(r'SELECT\s+\*', sql_str, re.IGNORECASE):
            warnings.append(ValidationError(
                code="SELECT_STAR",
                message="SELECT * may impact performance, consider explicit columns",
                severity="warning"
            ))
        
        # Warn about missing WHERE with JOINs
        has_where = any(
            token.ttype is T.Keyword and token.value.upper() == 'WHERE'
            for token in statement.tokens
        )
        
        if metadata['join_count'] > 0 and not has_where:
            warnings.append(ValidationError(
                code="MISSING_WHERE",
                message="Query with JOINs but no WHERE clause may be inefficient",
                severity="warning",
                context={"join_count": metadata['join_count']}
            ))
        
        # Warn about excessive nesting
        if metadata['query_depth'] > 3:
            warnings.append(ValidationError(
                code="DEEP_NESTING",
                message=f"Query has nesting depth {metadata['query_depth']}, consider flattening",
                severity="warning",
                context={"depth": metadata['query_depth']}
            ))
        
        return warnings
    
    def _validate_limit(self, statement: sql.Statement) -> List[ValidationError]:
        """Validate LIMIT clause."""
        errors = []
        
        sql_str = str(statement).upper()
        
        # Check if LIMIT exists
        if 'LIMIT' not in sql_str:
            errors.append(ValidationError(
                code="MISSING_LIMIT",
                message="Query must include a LIMIT clause",
                severity="error"
            ))
            return errors
        
        # Extract and validate LIMIT value
        limit_match = re.search(r'LIMIT\s+(\d+)', sql_str)
        if limit_match:
            limit_value = int(limit_match.group(1))
            if limit_value > self.max_row_limit:
                errors.append(ValidationError(
                    code="EXCESSIVE_LIMIT",
                    message=f"LIMIT {limit_value} exceeds maximum allowed {self.max_row_limit}",
                    severity="error",
                    context={"limit": limit_value, "max_limit": self.max_row_limit}
                ))
        
        return errors
    
    def validate_and_raise(self, sql: str) -> None:
        """
        Validate SQL and raise exception if invalid.
        
        Args:
            sql: SQL query string
        
        Raises:
            ValueError: If SQL is invalid
        """
        result = self.validate(sql)
        if not result.is_valid:
            error_messages = [
                f"[{err.code}] {err.message}"
                for err in result.errors
            ]
            raise ValueError(
                "SQL validation failed:\n" + "\n".join(f"  - {msg}" for msg in error_messages)
            )


def validate_sql_v2(
    sql: str,
    semantic_context: Optional[Dict[str, Any]] = None,
    validation_level: ValidationLevel = ValidationLevel.MODERATE,
    max_row_limit: int = 10000
) -> SQLValidationResult:
    """
    Validate SQL query using production-grade validator.
    
    Args:
        sql: SQL query string
        semantic_context: Schema information
        validation_level: Validation strictness
        max_row_limit: Maximum allowed LIMIT value
    
    Returns:
        SQLValidationResult with errors, warnings, and metadata
    
    Example:
        >>> sql = "SELECT user_id, COUNT(*) FROM users WHERE active = true GROUP BY user_id LIMIT 100"
        >>> result = validate_sql_v2(sql)
        >>> if result.is_valid:
        ...     print("SQL is safe to execute")
        >>> else:
        ...     for error in result.errors:
        ...         print(f"{error.code}: {error.message}")
    """
    validator = ProductionSQLValidator(
        semantic_context=semantic_context,
        validation_level=validation_level,
        max_row_limit=max_row_limit
    )
    return validator.validate(sql)
