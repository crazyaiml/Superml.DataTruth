"""
Pagination Support

Provides cursor-based and offset-based pagination for query results.
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Pagination parameters."""
    
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=100, ge=1, le=10000, description="Items per page")
    cursor: Optional[str] = Field(default=None, description="Cursor for cursor-based pagination")
    
    @property
    def offset(self) -> int:
        """Calculate offset for offset-based pagination."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit value."""
        return self.page_size


class PaginationMetadata(BaseModel):
    """Pagination metadata in response."""
    
    total_count: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there's a next page")
    has_previous: bool = Field(description="Whether there's a previous page")
    next_cursor: Optional[str] = Field(default=None, description="Cursor for next page")
    previous_cursor: Optional[str] = Field(default=None, description="Cursor for previous page")


def paginate_results(
    results: List[Dict[str, Any]],
    total_count: int,
    params: PaginationParams
) -> Tuple[List[Dict[str, Any]], PaginationMetadata]:
    """
    Apply pagination to query results.
    
    Args:
        results: Full list of results
        total_count: Total number of items available
        params: Pagination parameters
        
    Returns:
        Tuple of (paginated_results, metadata)
    """
    # Calculate pagination metadata
    total_pages = (total_count + params.page_size - 1) // params.page_size
    has_next = params.page < total_pages
    has_previous = params.page > 1
    
    # Slice results for current page
    start_idx = params.offset
    end_idx = start_idx + params.page_size
    paginated = results[start_idx:end_idx]
    
    metadata = PaginationMetadata(
        total_count=total_count,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous
    )
    
    return paginated, metadata


def get_pagination_metadata(
    total_count: int,
    params: PaginationParams
) -> PaginationMetadata:
    """
    Get pagination metadata without slicing results.
    
    Args:
        total_count: Total number of items
        params: Pagination parameters
        
    Returns:
        Pagination metadata
    """
    total_pages = (total_count + params.page_size - 1) // params.page_size
    has_next = params.page < total_pages
    has_previous = params.page > 1
    
    return PaginationMetadata(
        total_count=total_count,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous
    )


def apply_pagination_to_sql(sql: str, params: PaginationParams) -> str:
    """
    Add LIMIT and OFFSET clauses to SQL query.
    
    Args:
        sql: Original SQL query
        params: Pagination parameters
        
    Returns:
        SQL with pagination clauses
    """
    # Remove trailing semicolon if present
    sql = sql.rstrip(';').strip()
    
    # Add LIMIT and OFFSET
    paginated_sql = f"{sql}\nLIMIT {params.limit} OFFSET {params.offset}"
    
    return paginated_sql


def get_count_sql(sql: str) -> str:
    """
    Generate COUNT query from original SQL.
    
    Args:
        sql: Original SQL query
        
    Returns:
        SQL query that counts total rows
    """
    # Remove trailing semicolon
    sql = sql.rstrip(';').strip()
    
    # Wrap in COUNT query
    count_sql = f"SELECT COUNT(*) as total FROM ({sql}) as count_query"
    
    return count_sql
