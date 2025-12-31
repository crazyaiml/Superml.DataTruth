"""
SQL Validator - Security and Safety Checks

Validates SQL queries before execution to prevent security issues.
"""

import re
from typing import List, Tuple


class SQLValidator:
    """Validates SQL queries for security and safety."""

    # Dangerous SQL keywords that should never appear
    FORBIDDEN_KEYWORDS = {
        "DROP", "DELETE", "TRUNCATE", "INSERT", "UPDATE",
        "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC",
        "EXECUTE", "CALL", "DECLARE", "BEGIN", "END",
        "COMMIT", "ROLLBACK", "SAVEPOINT", "SET",
    }

    # Dangerous SQL patterns
    FORBIDDEN_PATTERNS = {
        r";.*?(?:DROP|DELETE|INSERT|UPDATE|ALTER|CREATE)": "multiple statements with dangerous keywords",
        r"--.*": "SQL comments",
        r"/\*.*?\*/": "block comments",
        r"xp_": "extended stored procedures",
        r"sp_": "system stored procedures",
    }

    def __init__(self, max_row_limit: int = 10000) -> None:
        """
        Initialize validator.

        Args:
            max_row_limit: Maximum allowed LIMIT value
        """
        self.max_row_limit = max_row_limit

    def validate(self, sql: str) -> Tuple[bool, List[str]]:
        """
        Validate SQL query.

        Args:
            sql: SQL query string

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check for forbidden keywords
        sql_upper = sql.upper()
        for keyword in self.FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{keyword}\b", sql_upper):
                errors.append(f"Forbidden keyword detected: {keyword}")

        # Check for forbidden patterns
        for pattern, description in self.FORBIDDEN_PATTERNS.items():
            if re.search(pattern, sql, re.IGNORECASE):
                errors.append(f"Forbidden pattern detected: {description}")

        # Check that it's a SELECT query
        if not sql_upper.strip().startswith("SELECT"):
            errors.append("Query must start with SELECT")

        # Check for LIMIT clause
        if "LIMIT" not in sql_upper:
            errors.append("Query must include a LIMIT clause")
        else:
            # Check LIMIT value
            limit_match = re.search(r"LIMIT\s+(\d+)", sql_upper)
            if limit_match:
                limit_value = int(limit_match.group(1))
                if limit_value > self.max_row_limit:
                    errors.append(
                        f"LIMIT {limit_value} exceeds maximum allowed {self.max_row_limit}"
                    )

        # Check for multiple statements
        statement_count = sql.count(";")
        if statement_count > 1:
            errors.append("Multiple SQL statements not allowed")

        # Check for UNION (can be used for SQL injection)
        if "UNION" in sql_upper:
            errors.append("UNION operations not allowed")

        is_valid = len(errors) == 0
        return is_valid, errors

    def validate_and_raise(self, sql: str) -> None:
        """
        Validate SQL and raise exception if invalid.

        Args:
            sql: SQL query string

        Raises:
            ValueError: If SQL is invalid
        """
        is_valid, errors = self.validate(sql)
        if not is_valid:
            error_msg = "SQL validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
            raise ValueError(error_msg)


def validate_sql(sql: str, max_row_limit: int = 10000) -> Tuple[bool, List[str]]:
    """
    Validate SQL query.

    Args:
        sql: SQL query string
        max_row_limit: Maximum allowed LIMIT value

    Returns:
        Tuple of (is_valid, list_of_errors)

    Example:
        >>> sql = "SELECT * FROM users LIMIT 100;"
        >>> is_valid, errors = validate_sql(sql)
        >>> if is_valid:
        ...     print("SQL is safe to execute")
    """
    validator = SQLValidator(max_row_limit=max_row_limit)
    return validator.validate(sql)
