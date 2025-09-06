"""
Redis Service for PyBOG
Handles caching, session management, and real-time updates
"""
import redis.asyncio as redis
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RedisService:
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
        self.client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        
    async def connect(self):
        """Initialize Redis connection"""
        try:
            self.client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.client.ping()
            logger.info("✅ Redis connected successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            
    # Session Caching
    async def cache_session(self, session_id: str, session_data: Dict[str, Any], ttl: int = 3600):
        """Cache session data with TTL"""
        if not self.client:
            return False
        try:
            key = f"session:{session_id}"
            await self.client.setex(
                key,
                ttl,
                json.dumps(session_data, default=str)
            )
            # Also update the recent sessions list
            await self.client.zadd(
                "recent_sessions",
                {session_id: datetime.utcnow().timestamp()}
            )
            # Trim to keep only last 100 sessions
            await self.client.zremrangebyrank("recent_sessions", 0, -101)
            return True
        except Exception as e:
            logger.error(f"Failed to cache session {session_id}: {e}")
            return False
    
    async def get_cached_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached session data"""
        if not self.client:
            return None
        try:
            key = f"session:{session_id}"
            data = await self.client.get(key)
            if data:
                # Refresh TTL on access
                await self.client.expire(key, 3600)
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached session {session_id}: {e}")
            return None
    
    async def get_recent_sessions(self, limit: int = 10) -> List[str]:
        """Get list of recent session IDs"""
        if not self.client:
            return []
        try:
            # Get most recent sessions
            session_ids = await self.client.zrevrange(
                "recent_sessions", 
                0, 
                limit - 1
            )
            return session_ids
        except Exception as e:
            logger.error(f"Failed to get recent sessions: {e}")
            return []
    
    # Message Queue for Processing
    async def queue_message(self, session_id: str, message: Dict[str, Any]):
        """Queue a message for processing"""
        if not self.client:
            return False
        try:
            queue_key = f"message_queue:{session_id}"
            await self.client.rpush(
                queue_key,
                json.dumps(message, default=str)
            )
            # Set expiry for queue
            await self.client.expire(queue_key, 7200)  # 2 hours
            return True
        except Exception as e:
            logger.error(f"Failed to queue message: {e}")
            return False
    
    async def get_queued_messages(self, session_id: str, count: int = 10) -> List[Dict[str, Any]]:
        """Get queued messages for processing"""
        if not self.client:
            return []
        try:
            queue_key = f"message_queue:{session_id}"
            messages = []
            for _ in range(count):
                msg = await self.client.lpop(queue_key)
                if msg:
                    messages.append(json.loads(msg))
                else:
                    break
            return messages
        except Exception as e:
            logger.error(f"Failed to get queued messages: {e}")
            return []
    
    # Real-time Updates via Pub/Sub
    async def publish_update(self, channel: str, data: Dict[str, Any]):
        """Publish update to a channel"""
        if not self.client:
            return False
        try:
            await self.client.publish(
                channel,
                json.dumps(data, default=str)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            return False
    
    async def subscribe_to_updates(self, channels: List[str]):
        """Subscribe to update channels"""
        if not self.client:
            return None
        try:
            self.pubsub = self.client.pubsub()
            await self.pubsub.subscribe(*channels)
            return self.pubsub
        except Exception as e:
            logger.error(f"Failed to subscribe to channels: {e}")
            return None
    
    # Session State Management
    async def set_session_state(self, session_id: str, state: str, data: Optional[Dict] = None):
        """Set session state with optional data"""
        if not self.client:
            return False
        try:
            state_key = f"session_state:{session_id}"
            state_data = {
                "state": state,
                "updated_at": datetime.utcnow().isoformat(),
                "data": data or {}
            }
            await self.client.setex(
                state_key,
                3600,  # 1 hour TTL
                json.dumps(state_data)
            )
            # Publish state change
            await self.publish_update(
                f"session:{session_id}",
                {"type": "state_change", "state": state, "data": data}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set session state: {e}")
            return False
    
    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current session state"""
        if not self.client:
            return None
        try:
            state_key = f"session_state:{session_id}"
            data = await self.client.get(state_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get session state: {e}")
            return None
    
    # Analysis Results Caching
    async def cache_analysis(self, session_id: str, analysis_data: Dict[str, Any]):
        """Cache analysis results"""
        if not self.client:
            return False
        try:
            key = f"analysis:{session_id}"
            await self.client.setex(
                key,
                7200,  # 2 hours TTL
                json.dumps(analysis_data, default=str)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cache analysis: {e}")
            return False
    
    async def get_cached_analysis(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis results"""
        if not self.client:
            return None
        try:
            key = f"analysis:{session_id}"
            data = await self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached analysis: {e}")
            return None
    
    # Health Check
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            if not self.client:
                return {
                    "healthy": False,
                    "status": "disconnected",
                    "message": "Redis client not initialized"
                }
            
            # Ping Redis
            await self.client.ping()
            
            # Get some stats
            info = await self.client.info()
            
            return {
                "healthy": True,
                "status": "connected",
                "message": "Redis is operational",
                "details": {
                    "version": info.get("redis_version", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "uptime_days": info.get("uptime_in_days", 0)
                }
            }
        except Exception as e:
            return {
                "healthy": False,
                "status": "error",
                "message": str(e)
            }

# Singleton instance
redis_service = RedisService()
