# api/docker_monitor.py - New Docker monitoring module
import asyncio
import docker
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import psutil

logger = logging.getLogger(__name__)

class DockerMonitor:
    def __init__(self):
        self.client = None
        self.containers = ['pybog-api', 'pybog-frontend', 'pybog-n8n', 'pybog-postgres', 'pybog-redis']
        
    async def initialize(self):
        try:
            self.client = docker.from_env()
            logger.info("Docker client initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            return False
            
    async def get_container_logs(self, container_name: str, tail: int = 50):
        """Get recent logs from a container"""
        if not self.client:
            return []
            
        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=tail, timestamps=True).decode('utf-8').split('\n')
            
            parsed_logs = []
            for log_line in logs:
                if log_line.strip():
                    # Parse timestamp if present
                    parts = log_line.split(' ', 1)
                    if len(parts) == 2 and parts[0].endswith('Z'):
                        timestamp = parts[0]
                        message = parts[1]
                    else:
                        timestamp = datetime.utcnow().isoformat() + 'Z'
                        message = log_line
                        
                    parsed_logs.append({
                        "container": container_name,
                        "timestamp": timestamp,
                        "message": message.strip(),
                        "level": self._infer_log_level(message)
                    })
                    
            return parsed_logs[-tail:]
        except Exception as e:
            logger.error(f"Error getting logs for {container_name}: {e}")
            return []
            
    def _infer_log_level(self, message: str) -> str:
        """Infer log level from message content"""
        msg_lower = message.lower()
        if any(term in msg_lower for term in ['error', 'exception', 'failed', 'fatal']):
            return 'error'
        elif any(term in msg_lower for term in ['warn', 'warning']):
            return 'warn'
        elif any(term in msg_lower for term in ['info', 'starting', 'started', 'connected']):
            return 'info'
        elif any(term in msg_lower for term in ['debug', 'trace']):
            return 'debug'
        return 'info'
            
    async def get_system_health(self) -> Dict:
        """Get comprehensive system health metrics"""
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
            },
            "containers": {}
        }
        
        if not self.client:
            return health
            
        try:
            for container in self.client.containers.list(all=True):
                if container.name.startswith('pybog-'):
                    try:
                        stats = container.stats(stream=False)
                        health["containers"][container.name] = {
                            "status": container.status,
                            "cpu_percent": self._calculate_cpu_percent(stats),
                            "memory_usage": stats['memory_stats'].get('usage', 0),
                            "memory_limit": stats['memory_stats'].get('limit', 0),
                            "memory_percent": self._calculate_memory_percent(stats),
                        }
                    except Exception as e:
                        health["containers"][container.name] = {
                            "status": container.status,
                            "error": str(e)
                        }
        except Exception as e:
            health["docker_error"] = str(e)
            
        return health
        
    def _calculate_cpu_percent(self, stats):
        """Calculate CPU percentage from Docker stats"""
        try:
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
            if system_delta > 0:
                return (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
        except:
            pass
        return 0.0
        
    def _calculate_memory_percent(self, stats):
        """Calculate memory percentage from Docker stats"""
        try:
            usage = stats['memory_stats'].get('usage', 0)
            limit = stats['memory_stats'].get('limit', 0)
            if limit > 0:
                return (usage / limit) * 100.0
        except:
            pass
        return 0.0
