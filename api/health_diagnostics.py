# api/health_diagnostics.py - Enhanced health diagnostics
import asyncio
import logging
import os
from typing import Dict, List, Any
import asyncpg
import httpx

logger = logging.getLogger(__name__)

class HealthDiagnostics:
    def __init__(self):
        self.checks = {
            "database": self._check_database,
            "n8n": self._check_n8n,
            "docker": self._check_docker,
            "api": self._check_api_health,
            "websockets": self._check_websocket_support
        }
    
    async def run_full_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive health diagnostics with actionable feedback"""
        results = {
            "overall_status": "checking",
            "services": {},
            "issues": [],
            "recommendations": [],
            "system_info": await self._get_system_info()
        }
        
        # Run all health checks
        for service_name, check_func in self.checks.items():
            try:
                service_result = await check_func()
                results["services"][service_name] = service_result
                
                if not service_result["healthy"]:
                    results["issues"].append(service_result)
                    if service_result.get("recommendation"):
                        results["recommendations"].append(service_result["recommendation"])
                        
            except Exception as e:
                results["services"][service_name] = {
                    "healthy": False,
                    "status": "error",
                    "message": f"Health check failed: {str(e)}",
                    "recommendation": f"Service {service_name} health check encountered an error"
                }
        
        # Determine overall status
        healthy_services = sum(1 for s in results["services"].values() if s["healthy"])
        total_services = len(results["services"])
        
        if healthy_services == total_services:
            results["overall_status"] = "healthy"
        elif healthy_services > 0:
            results["overall_status"] = "degraded"
        else:
            results["overall_status"] = "unhealthy"
            
        return results
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check PostgreSQL database connectivity"""
        try:
            db_url = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
            conn = await asyncpg.connect(db_url)
            
            # Test basic query
            result = await conn.fetchval("SELECT 1")
            await conn.close()
            
            if result == 1:
                return {
                    "healthy": True,
                    "status": "connected",
                    "message": "Database connection successful",
                    "details": {"url": db_url.split('@')[1] if '@' in db_url else db_url}
                }
            else:
                return {
                    "healthy": False,
                    "status": "query_failed",
                    "message": "Database connected but query failed",
                    "recommendation": "Check database permissions and configuration"
                }
                
        except Exception as e:
            return {
                "healthy": False,
                "status": "connection_failed",
                "message": f"Database connection failed: {str(e)}",
                "recommendation": "Ensure PostgreSQL container is running: docker-compose up postgres"
            }
    
    async def _check_n8n(self) -> Dict[str, Any]:
        """Check n8n workflow engine connectivity"""
        try:
            n8n_url = os.getenv('N8N_URL', 'http://n8n:5678')
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try to reach n8n health endpoint or webhook
                try:
                    response = await client.get(f"{n8n_url}/healthz")
                    if response.status_code == 200:
                        return {
                            "healthy": True,
                            "status": "running",
                            "message": "n8n workflow engine is running",
                            "details": {"url": n8n_url}
                        }
                except:
                    # Try webhook endpoint (expect 404 for GET)
                    response = await client.get(f"{n8n_url}/webhook/pybog-analyze")
                    if response.status_code in [404, 405]:  # Expected for webhook
                        return {
                            "healthy": True,
                            "status": "running",
                            "message": "n8n is running (webhook endpoint accessible)",
                            "details": {"url": n8n_url}
                        }
                
                return {
                    "healthy": False,
                    "status": "unreachable",
                    "message": f"n8n returned status {response.status_code}",
                    "recommendation": "Check n8n container: docker-compose logs n8n"
                }
                
        except Exception as e:
            return {
                "healthy": False,
                "status": "connection_failed", 
                "message": f"Cannot reach n8n: {str(e)}",
                "recommendation": "Start n8n container: docker-compose up n8n"
            }
    
    async def _check_docker(self) -> Dict[str, Any]:
        """Check Docker monitoring capabilities"""
        try:
            import docker
            client = docker.from_env()
            
            # Test basic Docker connectivity
            client.ping()
            
            # Check if we can list containers
            containers = client.containers.list(all=True)
            pybog_containers = [c for c in containers if c.name.startswith('pybog-')]
            
            return {
                "healthy": True,
                "status": "connected",
                "message": f"Docker monitoring active ({len(pybog_containers)} PyBOG containers)",
                "details": {
                    "total_containers": len(containers),
                    "pybog_containers": [c.name for c in pybog_containers]
                }
            }
            
        except ImportError:
            return {
                "healthy": False,
                "status": "not_installed",
                "message": "Docker Python library not installed",
                "recommendation": "Install Docker monitoring: pip install docker psutil"
            }
        except Exception as e:
            return {
                "healthy": False,
                "status": "access_denied",
                "message": f"Docker access failed: {str(e)}",
                "recommendation": "Ensure Docker socket is accessible. On Windows: enable Docker socket in docker-compose.yml"
            }
    
    async def _check_api_health(self) -> Dict[str, Any]:
        """Check API internal health"""
        try:
            # Check if we can import our modules
            from .docker_monitor import DockerMonitor
            
            return {
                "healthy": True,
                "status": "running",
                "message": "API services loaded successfully"
            }
        except ImportError as e:
            return {
                "healthy": False,
                "status": "module_error",
                "message": f"API module import failed: {str(e)}",
                "recommendation": "Check Python dependencies and file structure"
            }
    
    async def _check_websocket_support(self) -> Dict[str, Any]:
        """Check WebSocket support"""
        try:
            # This is a basic check - in a real implementation you'd test actual WS connections
            import websockets
            return {
                "healthy": True,
                "status": "supported",
                "message": "WebSocket support available"
            }
        except ImportError:
            return {
                "healthy": False,
                "status": "not_supported",
                "message": "WebSocket library not available",
                "recommendation": "WebSocket support included in uvicorn[standard]"
            }
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information"""
        import platform
        import sys
        
        return {
            "platform": platform.system(),
            "python_version": sys.version,
            "architecture": platform.architecture()[0],
            "environment": {
                "DATABASE_URL": "configured" if os.getenv('DATABASE_URL') else "missing",
                "N8N_URL": "configured" if os.getenv('N8N_URL') else "missing", 
                "OPENAI_API_KEY": "configured" if os.getenv('OPENAI_API_KEY') else "missing"
            }
        }

# Initialize diagnostics
diagnostics = HealthDiagnostics()
