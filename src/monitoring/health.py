"""
Health Check and Monitoring Module

Provides health check endpoints and system monitoring.
"""

import logging
import time
import psutil
from typing import Dict, Any
from datetime import datetime

from src.database.internal_db import InternalDB

logger = logging.getLogger(__name__)


class HealthChecker:
    """System health checker."""
    
    def __init__(self):
        """Initialize health checker."""
        self.start_time = time.time()
    
    def check_health(self) -> Dict[str, Any]:
        """
        Comprehensive health check.
        
        Returns:
            Dict with health status of all components
        """
        health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - self.start_time),
            "checks": {}
        }
        
        # Check database
        db_health = self._check_database()
        health["checks"]["database"] = db_health
        if db_health["status"] != "healthy":
            health["status"] = "unhealthy"
        
        # Check system resources
        system_health = self._check_system_resources()
        health["checks"]["system"] = system_health
        if system_health["status"] == "critical":
            health["status"] = "unhealthy"
        
        return health
    
    def check_readiness(self) -> Dict[str, Any]:
        """
        Readiness check for load balancers.
        
        Returns:
            Dict indicating if service is ready to accept traffic
        """
        ready = {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # Check database connection
        try:
            result = InternalDB.execute_query("SELECT 1")
            ready["checks"]["database"] = {"status": "connected"}
        except Exception as e:
            ready["ready"] = False
            ready["checks"]["database"] = {
                "status": "disconnected",
                "error": str(e)
            }
        
        return ready
    
    def check_liveness(self) -> Dict[str, Any]:
        """
        Liveness check for orchestrators (k8s).
        
        Returns:
            Dict indicating if service is alive
        """
        return {
            "alive": True,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - self.start_time)
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get system metrics for monitoring.
        
        Returns:
            Dict with various metrics
        """
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - self.start_time),
            "system": self._get_system_metrics(),
            "database": self._get_database_metrics()
        }
        
        return metrics
    
    def _check_database(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            start = time.time()
            result = InternalDB.execute_query("SELECT 1")
            response_time_ms = (time.time() - start) * 1000
            
            # Count active connections
            conn_result = InternalDB.execute_query("""
                SELECT count(*) 
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """)
            active_connections = conn_result.rows[0][0] if conn_result.rows else 0
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time_ms, 2),
                "active_connections": active_connections
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine status based on thresholds
            status = "healthy"
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                status = "critical"
            elif cpu_percent > 75 or memory.percent > 75 or disk.percent > 80:
                status = "warning"
            
            return {
                "status": status,
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory.percent, 2),
                "memory_available_mb": round(memory.available / 1024 / 1024, 2),
                "disk_percent": round(disk.percent, 2),
                "disk_free_gb": round(disk.free / 1024 / 1024 / 1024, 2)
            }
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {
                "status": "unknown",
                "error": str(e)
            }
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get detailed system metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu": {
                    "percent": round(cpu_percent, 2),
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "total_mb": round(memory.total / 1024 / 1024, 2),
                    "used_mb": round(memory.used / 1024 / 1024, 2),
                    "available_mb": round(memory.available / 1024 / 1024, 2),
                    "percent": round(memory.percent, 2)
                },
                "disk": {
                    "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                    "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                    "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                    "percent": round(disk.percent, 2)
                }
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {"error": str(e)}
    
    def _get_database_metrics(self) -> Dict[str, Any]:
        """Get database metrics."""
        try:
            # Database size
            size_result = InternalDB.execute_query("""
                SELECT pg_database_size(current_database())
            """)
            db_size_bytes = size_result.rows[0][0] if size_result.rows else 0
            
            # Table sizes
            table_result = InternalDB.execute_query("""
                SELECT 
                    schemaname,
                    COUNT(*) as table_count,
                    SUM(pg_total_relation_size(schemaname||'.'||tablename)) as total_size
                FROM pg_tables
                WHERE schemaname = 'public'
                GROUP BY schemaname
            """)
            
            table_stats = {}
            if table_result.rows:
                row = table_result.rows[0]
                table_stats = {
                    "table_count": row[1],
                    "total_size_mb": round(row[2] / 1024 / 1024, 2)
                }
            
            # Connection stats
            conn_result = InternalDB.execute_query("""
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity
                WHERE datname = current_database()
            """)
            
            conn_stats = {}
            if conn_result.rows:
                row = conn_result.rows[0]
                conn_stats = {
                    "total": row[0],
                    "active": row[1],
                    "idle": row[2]
                }
            
            return {
                "size_mb": round(db_size_bytes / 1024 / 1024, 2),
                "tables": table_stats,
                "connections": conn_stats
            }
        except Exception as e:
            logger.error(f"Failed to get database metrics: {e}")
            return {"error": str(e)}


# Singleton instance
_health_checker = None


def get_health_checker() -> HealthChecker:
    """Get or create singleton HealthChecker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
