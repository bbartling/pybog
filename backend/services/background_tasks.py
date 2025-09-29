"""
Background task service for periodic operations.
Handles file cleanup, maintenance tasks, and scheduled operations.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from core.events import EventBus, Event
from services.file_service import FileService

logger = logging.getLogger(__name__)


class BackgroundTaskService:
    """
    Service for managing background tasks and periodic operations.
    
    Handles:
    - Periodic file cleanup
    - System maintenance tasks
    - Health monitoring
    """
    
    def __init__(self, event_bus: EventBus, file_service: FileService):
        self.event_bus = event_bus
        self.file_service = file_service
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        
        # Configuration for task intervals (in seconds)
        self.task_intervals = {
            "file_cleanup": 3600,  # 1 hour
            "health_check": 300,   # 5 minutes
            "metrics_collection": 900  # 15 minutes
        }
        
        logger.info("BackgroundTaskService initialized")
    
    async def start(self) -> None:
        """Start all background tasks."""
        if self._running:
            logger.warning("Background tasks already running")
            return
        
        self._running = True
        
        # Start periodic tasks
        self._tasks["file_cleanup"] = asyncio.create_task(
            self._periodic_file_cleanup()
        )
        self._tasks["health_check"] = asyncio.create_task(
            self._periodic_health_check()
        )
        self._tasks["metrics_collection"] = asyncio.create_task(
            self._periodic_metrics_collection()
        )
        
        logger.info("Background tasks started")
        
        # Emit startup event
        await self._emit_system_event(
            "background_tasks_started",
            "progress",
            {
                "message": "Background task service started",
                "tasks_started": list(self._tasks.keys()),
                "intervals": self.task_intervals
            }
        )
    
    async def stop(self) -> None:
        """Stop all background tasks."""
        if not self._running:
            logger.warning("Background tasks not running")
            return
        
        self._running = False
        
        # Cancel all tasks
        for task_name, task in self._tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Background task '{task_name}' cancelled")
        
        self._tasks.clear()
        logger.info("Background tasks stopped")
        
        # Emit shutdown event
        await self._emit_system_event(
            "background_tasks_stopped",
            "progress",
            {
                "message": "Background task service stopped"
            }
        )
    
    async def _emit_system_event(self, operation: str, event_type: str, data: Dict[str, Any]) -> None:
        """Emit a system-level event."""
        try:
            event = Event(
                type=event_type,
                session_id="system",
                operation=operation,
                data=data
            )
            await self.event_bus.publish("system", event)
            logger.debug(f"Emitted system event: {operation}")
        except Exception as e:
            logger.error(f"Failed to emit system event: {e}")
    
    async def _periodic_file_cleanup(self) -> None:
        """Periodic file cleanup task."""
        logger.info("Starting periodic file cleanup task")
        
        while self._running:
            try:
                # Wait for the interval
                await asyncio.sleep(self.task_intervals["file_cleanup"])
                
                if not self._running:
                    break
                
                logger.info("Running scheduled file cleanup")
                
                # Run file cleanup
                cleanup_result = await self.file_service.cleanup_old_files()
                
                # Log results
                logger.info(
                    f"Scheduled file cleanup completed: "
                    f"{cleanup_result.archived_count} archived, "
                    f"{cleanup_result.purged_count} purged"
                )
                
                # Emit cleanup completion event
                await self._emit_system_event(
                    "scheduled_file_cleanup",
                    "progress",
                    {
                        "message": f"Scheduled cleanup: {cleanup_result.archived_count} archived, {cleanup_result.purged_count} purged",
                        "archived_count": cleanup_result.archived_count,
                        "purged_count": cleanup_result.purged_count,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
            except asyncio.CancelledError:
                logger.info("File cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic file cleanup: {e}")
                
                # Emit error event
                await self._emit_system_event(
                    "scheduled_file_cleanup",
                    "error",
                    {
                        "error_code": "BACKGROUND_TASK",
                        "message": f"Scheduled file cleanup failed: {str(e)}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
                # Continue running despite errors
                continue
    
    async def _periodic_health_check(self) -> None:
        """Periodic system health check task."""
        logger.info("Starting periodic health check task")
        
        while self._running:
            try:
                # Wait for the interval
                await asyncio.sleep(self.task_intervals["health_check"])
                
                if not self._running:
                    break
                
                # Perform health checks
                health_status = await self._perform_health_check()
                
                # Emit health status event
                await self._emit_system_event(
                    "health_check",
                    "progress",
                    {
                        "message": f"System health check: {health_status['status']}",
                        "health_data": health_status,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
            except asyncio.CancelledError:
                logger.info("Health check task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic health check: {e}")
                continue
    
    async def _periodic_metrics_collection(self) -> None:
        """Periodic metrics collection task."""
        logger.info("Starting periodic metrics collection task")
        
        while self._running:
            try:
                # Wait for the interval
                await asyncio.sleep(self.task_intervals["metrics_collection"])
                
                if not self._running:
                    break
                
                # Collect system metrics
                metrics = await self._collect_system_metrics()
                
                # Emit metrics event
                await self._emit_system_event(
                    "metrics_collection",
                    "progress",
                    {
                        "message": "System metrics collected",
                        "metrics": metrics,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
            except asyncio.CancelledError:
                logger.info("Metrics collection task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic metrics collection: {e}")
                continue
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """
        Perform system health checks.
        
        Returns:
            Health status dictionary
        """
        health_status = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Check database connectivity
            from core.database import get_database
            db = await get_database()
            await db.fetch_val("SELECT 1")
            health_status["checks"]["database"] = "healthy"
        except Exception as e:
            health_status["checks"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        try:
            # Check file system access
            import os
            from pathlib import Path
            upload_dir = Path("data/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            test_file = upload_dir / "health_check.tmp"
            test_file.write_text("health check")
            test_file.unlink()
            health_status["checks"]["file_system"] = "healthy"
        except Exception as e:
            health_status["checks"]["file_system"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        try:
            # Check memory usage
            import psutil
            memory = psutil.virtual_memory()
            health_status["checks"]["memory"] = {
                "status": "healthy" if memory.percent < 90 else "warning",
                "usage_percent": memory.percent,
                "available_gb": round(memory.available / (1024**3), 2)
            }
            if memory.percent > 95:
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["checks"]["memory"] = f"unknown: {str(e)}"
        
        return health_status
    
    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """
        Collect system performance metrics.
        
        Returns:
            System metrics dictionary
        """
        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            import psutil
            
            # CPU metrics
            metrics["cpu"] = {
                "usage_percent": psutil.cpu_percent(interval=1),
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
            
            # Memory metrics
            memory = psutil.virtual_memory()
            metrics["memory"] = {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "usage_percent": memory.percent
            }
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            metrics["disk"] = {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "usage_percent": round((disk.used / disk.total) * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            metrics["error"] = str(e)
        
        return metrics
    
    async def run_manual_cleanup(self) -> Dict[str, Any]:
        """
        Run manual file cleanup operation.
        
        Returns:
            Cleanup result dictionary
        """
        try:
            logger.info("Running manual file cleanup")
            
            # Emit cleanup started event
            await self._emit_system_event(
                "manual_file_cleanup",
                "progress",
                {
                    "message": "Manual file cleanup started",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Run cleanup
            cleanup_result = await self.file_service.cleanup_old_files()
            
            result = {
                "success": True,
                "archived_count": cleanup_result.archived_count,
                "purged_count": cleanup_result.purged_count,
                "total_processed": cleanup_result.total_processed,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Emit completion event
            await self._emit_system_event(
                "manual_file_cleanup",
                "progress",
                {
                    "message": f"Manual cleanup completed: {cleanup_result.archived_count} archived, {cleanup_result.purged_count} purged",
                    "result": result
                }
            )
            
            logger.info(f"Manual file cleanup completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Manual file cleanup failed: {e}")
            
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Emit error event
            await self._emit_system_event(
                "manual_file_cleanup",
                "error",
                {
                    "error_code": "BACKGROUND_TASK",
                    "message": f"Manual file cleanup failed: {str(e)}",
                    "result": error_result
                }
            )
            
            return error_result
    
    def get_task_status(self) -> Dict[str, Any]:
        """
        Get status of all background tasks.
        
        Returns:
            Task status dictionary
        """
        status = {
            "running": self._running,
            "tasks": {},
            "intervals": self.task_intervals,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        for task_name, task in self._tasks.items():
            status["tasks"][task_name] = {
                "running": not task.done(),
                "cancelled": task.cancelled() if task.done() else False,
                "exception": str(task.exception()) if task.done() and task.exception() else None
            }
        
        return status