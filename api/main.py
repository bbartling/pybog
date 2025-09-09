"""
PyBOG API - Core endpoints for BOG generation
Simplified version focused on essential functionality
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import json
import uuid
import logging
from pathlib import Path
from datetime import datetime
import mimetypes
import asyncpg
import httpx
import asyncio
import time
from starlette.middleware.base import BaseHTTPMiddleware

# Setup logging first - before any logger usage
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Docker monitoring
try:
    from .docker_monitor import DockerMonitor
    docker_monitor = DockerMonitor() if 'DockerMonitor' in locals() else None
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker_monitor = None
    logger.warning("Docker monitoring not available - install docker package")

# Redis Service
try:
    from .services.redis_service import redis_service
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis_service = None
    logger.warning("Redis service not available")

# Import core PyBOG functionality
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from bog_builder import BogFolderBuilder
from .routes.conversation import router as conversation_router
from .routes.session_management import router as session_router

# Import optional routers independently so one failure doesn't block others
try:
    from .routes.session_enhanced import router as enhanced_router
except Exception as e:
    enhanced_router = None
    logger.warning(f"Enhanced session routes unavailable: {e}")

try:
    from .routes.unified_sessions import router as unified_router
except Exception as e:
    unified_router = None
    logger.warning(f"Unified session routes unavailable: {e}")

try:
    from .routes.workflow import router as workflow_router
except Exception as e:
    workflow_router = None
    logger.warning(f"Workflow routes unavailable: {e}")
from .n8n_resume import store_resume_url, append_message

# Create FastAPI app
app = FastAPI(
    title="PyBOG API",
    version="2.0.0",
    description="Core API for generating Niagara BOG files from HVAC specifications"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include modular conversation routes (approve/request-changes/messages)
app.include_router(conversation_router)
# Include session management routes
app.include_router(session_router)
# Include enhanced and unified routes if available
if enhanced_router:
    app.include_router(enhanced_router)
if unified_router:
    app.include_router(unified_router)
if workflow_router:
    app.include_router(workflow_router)

# ------------------------
# Database helpers
# ------------------------

async def ensure_tables():
    """Create minimal tables if they do not exist.
    Flexible design so we can extend with extra columns/relations later.
    Tables:
      - sessions(session_id primary key, description, created_at, updated_at)
      - session_files(id serial pk, session_id fk, filename, mime_type, size, path, uploaded_at)
    """
    db_url = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            description TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS session_files (
            id SERIAL PRIMARY KEY,
            session_id TEXT REFERENCES sessions(session_id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            mime_type TEXT,
            size BIGINT,
            path TEXT,
            uploaded_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)
    finally:
        await conn.close()

@app.on_event("startup")
async def startup_event():
    try:
        await ensure_tables()
        logger.info("Database tables ensured")
        
        # Initialize Redis
        if REDIS_AVAILABLE and redis_service:
            connected = await redis_service.connect()
            if connected:
                logger.info("✅ Redis service initialized")
            else:
                logger.warning("⚠️ Redis connection failed, using fallback")
        
        # Initialize Docker monitoring
        if DOCKER_AVAILABLE and docker_monitor:
            try:
                await docker_monitor.initialize()
                # Start background monitoring tasks
                asyncio.create_task(health_monitoring_task())
                asyncio.create_task(log_streaming_task())
                logger.info("Docker monitoring initialized")
            except Exception as e:
                logger.warning(f"Docker monitoring initialization failed: {e}")
        else:
            logger.warning("Docker monitoring disabled - docker package not available")
            
    except Exception as e:
        logger.warning(f"Could not initialize monitoring: {e}")

# Storage paths
OUTPUTS_DIR = Path("data/outputs")
UPLOADS_DIR = Path("data/uploads")
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------
# WebSocket Connection Manager
# ------------------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        # New: separate connections for monitoring
        self.health_connections: Dict[str, WebSocket] = {}
        self.log_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session: {session_id}")
        
    # New: Health monitoring connections
    async def connect_health(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.health_connections[client_id] = websocket
        logger.info(f"Health WebSocket connected: {client_id}")
        
    # New: Log monitoring connections
    async def connect_logs(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.log_connections[client_id] = websocket
        logger.info(f"Logs WebSocket connected: {client_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session: {session_id}")
            
    def disconnect_health(self, client_id: str):
        if client_id in self.health_connections:
            del self.health_connections[client_id]
            
    def disconnect_logs(self, client_id: str):
        if client_id in self.log_connections:
            del self.log_connections[client_id]
    
    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
                logger.info(f"Message sent to session {session_id}: {message.get('type', 'unknown')}")
            except Exception as e:
                logger.error(f"Failed to send message to session {session_id}: {e}")
                self.disconnect(session_id)
        else:
            logger.warning(f"No active connection for session: {session_id}")
    
    # New: Broadcasting methods for monitoring
    async def broadcast_health(self, health_data: dict):
        await self._broadcast_to_connections(self.health_connections, "health", health_data)
        
    async def broadcast_logs(self, log_data: dict):
        await self._broadcast_to_connections(self.log_connections, "docker_log", log_data)
        
    async def broadcast_audit(self, audit_data: dict):
        await self._broadcast_to_connections(self.health_connections, "audit", audit_data)
        
    async def _broadcast_to_connections(self, connections: dict, event_type: str, data: dict):
        message = {"type": event_type, "data": data}
        disconnected = []
        
        for client_id, ws in connections.items():
            try:
                await ws.send_text(json.dumps(message))
            except:
                disconnected.append(client_id)
                
        for client_id in disconnected:
            if client_id in connections:
                del connections[client_id]
    
    async def send_analysis_complete(self, session_id: str, analysis_data: dict):
        await self.send_message(session_id, {
            "type": "analysis_complete",
            "sessionId": session_id,
            "analysis": analysis_data,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def send_bog_generated(self, session_id: str, download_url: str, message: str):
        await self.send_message(session_id, {
            "type": "bog_generated",
            "sessionId": session_id,
            "downloadUrl": download_url,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })

manager = ConnectionManager()

# --- WebSocket endpoints for real-time updates ---
from .services.workflow_service import workflow_service  # for Redis access

@app.websocket("/ws/{session_id}")
async def ws_session_updates(websocket: WebSocket, session_id: str):
    """WebSocket channel that forwards Redis workflow events for a session to the client.
    The server also responds to simple 'ping' messages with a 'pong'.
    """
    await manager.connect(websocket, session_id)

    # Subscribe to the Redis pubsub channel for this session
    redis = await workflow_service.get_redis()
    pubsub = redis.pubsub()
    channel = f"pybog:session:{session_id}:events"
    await pubsub.subscribe(channel)

    import asyncio
    import json as _json

    async def pump_redis_to_ws():
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
                if message and message.get("type") == "message":
                    data = message.get("data")
                    # data is already JSON string from publisher; forward as-is
                    try:
                        await websocket.send_text(data)
                    except Exception:
                        break
                else:
                    await asyncio.sleep(0.1)
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                pass

    async def read_ws():
        try:
            while True:
                try:
                    raw = await websocket.receive_text()
                except Exception:
                    break
                # Respond to heartbeat pings from client
                try:
                    obj = _json.loads(raw)
                    if obj.get("type") == "ping":
                        await websocket.send_text(_json.dumps({"type": "pong"}))
                except Exception:
                    # ignore non-JSON messages
                    pass
        except WebSocketDisconnect:
            pass

    task_redis = asyncio.create_task(pump_redis_to_ws())
    task_read = asyncio.create_task(read_ws())

    done, pending = await asyncio.wait({task_redis, task_read}, return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()

    manager.disconnect(session_id)

@app.websocket("/ws/health")
async def ws_health(websocket: WebSocket):
    import uuid as _uuid
    import asyncio
    client_id = str(_uuid.uuid4())
    await manager.connect_health(websocket, client_id)
    try:
        while True:
            # Keep the socket open; background tasks broadcast to connected clients
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_health(client_id)

@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    import uuid as _uuid
    import asyncio
    client_id = str(_uuid.uuid4())
    await manager.connect_logs(websocket, client_id)
    try:
        while True:
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_logs(client_id)

# Request audit middleware
class RequestAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        req_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        request.state.req_id = req_id
        response = await call_next(request)
        duration = time.time() - start_time
        
        audit_event = {
            "reqId": req_id,
            "method": request.method,
            "path": str(request.url.path),
            "status": response.status_code,
            "duration": round(duration * 1000, 2),
            "timestamp": time.time()
        }
        
        await manager.broadcast_audit(audit_event)
        return response

# Add audit middleware
app.add_middleware(RequestAuditMiddleware)

# Background monitoring tasks
async def health_monitoring_task():
    """Background task to broadcast health updates"""
    if not docker_monitor:
        return
        
    while True:
        try:
            health_data = await docker_monitor.get_system_health()
            await manager.broadcast_health(health_data)
        except Exception as e:
            logger.error(f"Health monitoring error: {e}")
        await asyncio.sleep(5)

async def log_streaming_task():
    """Background task to stream Docker logs"""
    if not docker_monitor:
        return
        
    last_check = {}
    while True:
        try:
            for container_name in docker_monitor.containers:
                logs = await docker_monitor.get_container_logs(container_name, 10)
                
                last_timestamp = last_check.get(container_name)
                new_logs = []
                
                for log in logs:
                    if not last_timestamp or log['timestamp'] > last_timestamp:
                        new_logs.append(log)
                
                if new_logs:
                    last_check[container_name] = new_logs[-1]['timestamp']
                    for log in new_logs:
                        await manager.broadcast_logs(log)
                        
        except Exception as e:
            logger.error(f"Log streaming error: {e}")
        await asyncio.sleep(2)

# ------------------------
# Pydantic Models
# ------------------------

class SensorInput(BaseModel):
    """Input sensor definition"""
    name: str
    type: str = Field(default="temperature", description="Sensor type: temperature, pressure, flow, humidity, CO2")
    units: str = Field(default="°F", description="Units: °F, PSI, CFM, %, PPM")
    default_value: float = 0.0
    range_min: Optional[float] = None
    range_max: Optional[float] = None

class ActuatorOutput(BaseModel):
    """Output actuator definition"""
    name: str
    type: str = Field(default="valve", description="Actuator type: valve, damper, VFD, relay")
    control_type: str = Field(default="modulating", description="Control type: modulating, on_off")
    range: str = Field(default="0-100%", description="Control range")
    default_value: float = 0.0

class ControlSequence(BaseModel):
    """Control logic sequence"""
    name: str
    type: str = Field(default="normal", description="Sequence type: startup, shutdown, normal, safety")
    description: str
    components: List[str] = Field(default_factory=list, description="List of component names involved")
    logic: Optional[str] = None

class BogGenerationRequest(BaseModel):
    """Request to generate a BOG file"""
    bog_name: str = Field(description="Name for the BOG file")
    session_id: Optional[str] = Field(default=None, description="Session ID for tracking")
    inputs: List[SensorInput] = Field(description="List of input sensors")
    outputs: List[ActuatorOutput] = Field(description="List of output actuators")
    control_sequences: List[ControlSequence] = Field(default_factory=list, description="Control logic sequences")
    setpoints: Dict[str, float] = Field(default_factory=dict, description="Setpoint values")
    alarms: List[Dict[str, Any]] = Field(default_factory=list, description="Alarm conditions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class BogGenerationResponse(BaseModel):
    """Response from BOG generation"""
    success: bool
    session_id: str
    bog_file_path: Optional[str] = None
    download_url: Optional[str] = None
    components_processed: Dict[str, int]
    message: str
    errors: List[str] = Field(default_factory=list)

class SchemaValidationRequest(BaseModel):
    """Request to validate HVAC schema before generation"""
    inputs: List[SensorInput]
    outputs: List[ActuatorOutput]
    control_sequences: List[ControlSequence] = Field(default_factory=list)

class SchemaValidationResponse(BaseModel):
    """Response from schema validation"""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)

class SessionStateResponse(BaseModel):
    """Response with session state information"""
    session_id: str
    state: str
    analysis_data: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str

class WorkflowApprovalRequest(BaseModel):
    """Request to approve or reject analysis"""
    session_id: str
    approved: bool
    feedback: Optional[str] = None

# ------------------------
# API Endpoints
# ------------------------

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "PyBOG API",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "generate": "/api/generate-bog",
            "validate": "/api/validate-schema",
            "download": "/api/download/{session_id}/{filename}",
            "health": "/api/health",
            "n8n_webhook": "/api/n8n/webhook/{path}"
        }
    }

@app.get("/api/health")
async def health_check():
    """Enhanced health check with detailed diagnostics and actionable feedback"""
    try:
        from .health_diagnostics import diagnostics
        detailed_health = await diagnostics.run_full_diagnostics()
        return detailed_health
    except Exception as e:
        # Fallback basic health check
        logger.error(f"Enhanced health check failed: {e}")
        
        db_ok = False
        try:
            db_url = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
            conn = await asyncpg.connect(db_url)
            row = await conn.fetchval("SELECT 1")
            db_ok = (row == 1)
            await conn.close()
        except Exception:
            db_ok = False

        n8n_ok = False
        try:
            n8n_url = os.getenv('N8N_URL', 'http://localhost:5678')
            analyze_path = os.getenv('N8N_ANALYZE_WEBHOOK_PATH', '/webhook/pybog-analyze').lstrip('/')
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{n8n_url.rstrip('/')}/{analyze_path}")
                n8n_ok = resp.status_code in (200, 401, 403, 404)
        except Exception:
            n8n_ok = False

        return {
            "overall_status": "healthy" if db_ok and n8n_ok else "degraded",
            "services": {
                "database": {"healthy": db_ok, "status": "connected" if db_ok else "failed"},
                "n8n": {"healthy": n8n_ok, "status": "running" if n8n_ok else "unreachable"}
            },
            "issues": [] if db_ok and n8n_ok else ["Basic health check only - enhanced diagnostics failed"],
            "recommendations": ["Check Docker setup and Python dependencies"] if not (db_ok and n8n_ok) else [],
            "fallback": True
        }

@app.post("/api/validate-schema", response_model=SchemaValidationResponse)
async def validate_schema(request: SchemaValidationRequest):
    """Validate HVAC schema before generation"""
    errors = []
    warnings = []
    suggestions = []
    
    # Validate inputs
    if not request.inputs:
        errors.append("No input sensors defined. At least one sensor is required.")
    else:
        for sensor in request.inputs:
            if not sensor.name:
                errors.append(f"Sensor missing name")
            if sensor.type not in ["temperature", "pressure", "flow", "humidity", "CO2"]:
                warnings.append(f"Unknown sensor type '{sensor.type}' for {sensor.name}")
    
    # Validate outputs
    if not request.outputs:
        errors.append("No output actuators defined. At least one actuator is required.")
    else:
        for actuator in request.outputs:
            if not actuator.name:
                errors.append(f"Actuator missing name")
            if actuator.type not in ["valve", "damper", "VFD", "relay"]:
                warnings.append(f"Unknown actuator type '{actuator.type}' for {actuator.name}")
    
    # Validate control sequences
    if not request.control_sequences:
        suggestions.append("Consider adding control sequences to define system behavior")
    else:
        component_names = {s.name for s in request.inputs} | {a.name for a in request.outputs}
        for sequence in request.control_sequences:
            for component in sequence.components:
                if component not in component_names:
                    warnings.append(f"Component '{component}' in sequence '{sequence.name}' not found in inputs/outputs")
    
    # Provide suggestions
    if len(request.inputs) < 2:
        suggestions.append("Consider adding more sensors for redundancy and better control")
    
    if len(request.outputs) < 2:
        suggestions.append("Consider adding more actuators for finer control")
    
    return SchemaValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        suggestions=suggestions
    )

@app.post("/api/generate-bog", response_model=BogGenerationResponse)
async def generate_bog(request: BogGenerationRequest):
    """Generate BOG file from HVAC schema"""
    
    session_id = request.session_id or str(uuid.uuid4())
    errors = []
    
    try:
        # Validate minimum requirements
        if not request.inputs:
            return BogGenerationResponse(
                success=False,
                session_id=session_id,
                components_processed={"inputs": 0, "outputs": 0, "sequences": 0},
                message="No input sensors specified",
                errors=["At least one input sensor is required"]
            )
        
        if not request.outputs:
            return BogGenerationResponse(
                success=False,
                session_id=session_id,
                components_processed={"inputs": len(request.inputs), "outputs": 0, "sequences": 0},
                message="No output actuators specified",
                errors=["At least one output actuator is required"]
            )
        
        # Create BOG builder
        bog_name = request.bog_name or f"hvac_control_{session_id[:8]}"
        builder = BogFolderBuilder(bog_name, debug=True)
        
        # Add input sensors
        for sensor in request.inputs:
            try:
                builder.add_numeric_writable(
                    sensor.name,
                    default_value=sensor.default_value,
                    facets=f"units={sensor.units}"
                )
                logger.info(f"Added sensor: {sensor.name} ({sensor.type})")
            except Exception as e:
                errors.append(f"Failed to add sensor {sensor.name}: {str(e)}")
        
        # Add output actuators
        for actuator in request.outputs:
            try:
                if actuator.control_type == "modulating":
                    builder.add_numeric_writable(
                        actuator.name,
                        default_value=actuator.default_value,
                        facets=f"range={actuator.range}"
                    )
                else:
                    builder.add_boolean_writable(
                        actuator.name,
                        default_value=bool(actuator.default_value)
                    )
                logger.info(f"Added actuator: {actuator.name} ({actuator.type})")
            except Exception as e:
                errors.append(f"Failed to add actuator {actuator.name}: {str(e)}")
        
        # Add setpoints
        for name, value in request.setpoints.items():
            try:
                builder.add_component(
                    "kitControl:NumericConst", 
                    name, 
                    properties={"value": str(value)}
                )
                logger.info(f"Added setpoint: {name} = {value}")
            except Exception as e:
                errors.append(f"Failed to add setpoint {name}: {str(e)}")
        
        # Add basic control logic (if provided)
        if request.control_sequences:
            # This would be expanded to handle actual control logic
            for sequence in request.control_sequences:
                logger.info(f"Processing sequence: {sequence.name} - {sequence.description}")
                # TODO: Implement actual control logic generation
        
        # Save BOG file
        output_path = OUTPUTS_DIR / session_id
        output_path.mkdir(exist_ok=True)
        bog_file_path = output_path / f"{bog_name}.bog"
        
        builder.save(str(bog_file_path))
        logger.info(f"BOG file saved to: {bog_file_path}")
        
        return BogGenerationResponse(
            success=True,
            session_id=session_id,
            bog_file_path=str(bog_file_path),
            download_url=f"/api/download/{session_id}/{bog_name}.bog",
            components_processed={
                "inputs": len(request.inputs),
                "outputs": len(request.outputs),
                "sequences": len(request.control_sequences)
            },
            message=f"BOG file '{bog_name}.bog' generated successfully",
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"BOG generation failed: {str(e)}")
        return BogGenerationResponse(
            success=False,
            session_id=session_id,
            components_processed={
                "inputs": len(request.inputs),
                "outputs": len(request.outputs),
                "sequences": len(request.control_sequences)
            },
            message=f"BOG generation failed: {str(e)}",
            errors=errors + [str(e)]
        )

@app.get("/api/download/{session_id}/{filename}")
async def download_bog(session_id: str, filename: str):
    """Download generated BOG file"""
    file_path = OUTPUTS_DIR / session_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )

# Removed duplicate file serving endpoint - using the more comprehensive one below

@app.post("/api/pybog/generate")
async def pybog_generate(request: BogGenerationRequest):
    """n8n-compatible endpoint for BOG generation"""
    # This is an alias for the main generate endpoint
    # to maintain compatibility with n8n workflows
    return await generate_bog(request)

# ------------------------
# Session and Workflow Control Endpoints
# ------------------------

class CreateSessionRequest(BaseModel):
    session_id: str
    description: Optional[str] = None

@app.post("/api/sessions")
async def create_session(request: CreateSessionRequest):
    """Create or upsert a session row."""
    try:
        await ensure_tables()
        db_url = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
        conn = await asyncpg.connect(db_url)
        try:
            await conn.execute(
                """
                INSERT INTO sessions(session_id, description)
                VALUES($1, $2)
                ON CONFLICT(session_id) DO UPDATE
                SET description = COALESCE(EXCLUDED.description, sessions.description),
                    updated_at = NOW(),
                    last_activity = NOW()
                """,
                request.session_id,
                request.description,
            )
            return {"session_id": request.session_id, "status": "ok"}
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Create session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import Form

@app.post("/api/sessions/{session_id}/upload")
async def upload_session_file(
    session_id: str,
    file: UploadFile = File(...),
    session_id_form: Optional[str] = Form(None),
    message_id: Optional[str] = Form(None)
):
    """Store uploaded file under data/uploads/<session_id> and register in Postgres.
    Returns a stable file_id and preview/download URLs so the frontend can persist and view files after refresh.
    """
    try:
        await ensure_tables()
        # Align session id from form if provided
        sid = session_id_form or session_id
        # Ensure session row exists
        db_url = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
        conn = await asyncpg.connect(db_url)
        try:
            await conn.execute(
                "INSERT INTO sessions(session_id) VALUES($1) ON CONFLICT(session_id) DO NOTHING",
                sid,
            )
        finally:
            await conn.close()

        # Save file to disk
        dest_dir = UPLOADS_DIR / sid
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / file.filename
        content = await file.read()
        with open(dest_path, 'wb') as f:
            f.write(content)

        # Insert file record (legacy session_files for compatibility)
        conn = await asyncpg.connect(db_url)
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_files (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT REFERENCES sessions(session_id) ON DELETE CASCADE,
                    filename TEXT NOT NULL,
                    mime_type TEXT,
                    size BIGINT,
                    path TEXT,
                    uploaded_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                INSERT INTO session_files(session_id, filename, mime_type, size, path)
                VALUES($1, $2, $3, $4, $5)
                """,
                sid,
                file.filename,
                file.content_type,
                len(content),
                str(dest_path)
            )
        finally:
            await conn.close()

        # Build stable identifiers and URLs for frontend persistence and preview
        # We use a composite string id to avoid schema coupling here; unified 'files' table may also be present separately.
        file_id = f"{sid}:{file.filename}"
        preview_url = f"/api/files/{sid}/{file.filename}?inline=1"
        download_url = f"/api/files/{sid}/{file.filename}?download=1"

        return {
            "session_id": sid,
            "filename": file.filename,
            "mime_type": file.content_type,
            "size": len(content),
            "status": "stored",
            "file_id": file_id,
            "preview_url": preview_url,
            "download_url": download_url,
            "message_id": message_id,
        }
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/{session_id}/{filename}")
async def serve_session_file(
    session_id: str,
    filename: str,
    inline: int = 1,
    download: int = 0,
):
    """
    Serve uploaded session files for inline preview or download.
    - Looks in data/uploads/{session_id}/{filename}
    - Falls back to path stored in session_files for compatibility
    """
    try:
        # Primary path (direct file system)
        file_path = UPLOADS_DIR / session_id / filename
        if not file_path.exists():
            # Fallback to database tables (both legacy and modern)
            db_url = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
            conn = await asyncpg.connect(db_url)
            try:
                # Check modern files table first
                row = await conn.fetchrow(
                    """
                    SELECT storage_path FROM files
                    WHERE session_id = $1 AND filename = $2
                    ORDER BY upload_time DESC LIMIT 1
                    """,
                    session_id, filename
                )
                if row and row['storage_path']:
                    # Handle both absolute and relative paths
                    storage_path = Path(row['storage_path'])
                    logger.info(f"Found storage_path in files table: {storage_path}")
                    if not storage_path.is_absolute():
                        # Resolve relative to current working directory
                        file_path = Path.cwd() / storage_path
                        logger.info(f"Resolved relative path to: {file_path}")
                    else:
                        file_path = storage_path
                        logger.info(f"Using absolute path: {file_path}")
                else:
                    # Fallback to legacy session_files table
                    row = await conn.fetchrow(
                        """
                        SELECT path FROM session_files
                        WHERE session_id = $1 AND filename = $2
                        ORDER BY uploaded_at DESC LIMIT 1
                        """,
                        session_id, filename
                    )
                    if row and row['path']:
                        file_path = Path(row['path'])
            finally:
                await conn.close()
        logger.info(f"Final file_path check: {file_path}, exists: {file_path.exists()}")
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        media_type = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
        disposition = 'inline' if inline and not download else 'attachment'
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename,
            content_disposition_type=disposition,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Serve file failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Recent sessions endpoint - using /api/recent-sessions to avoid routing conflicts
@app.get("/api/recent-sessions")
async def get_recent_sessions(limit: int = 10):
    """Get recent sessions with caching"""
    try:
        # Try Redis cache first
        if REDIS_AVAILABLE and redis_service and redis_service.client:
            cached_ids = await redis_service.get_recent_sessions(limit)
            if cached_ids:
                sessions = []
                for sid in cached_ids:
                    cached_data = await redis_service.get_cached_session(sid)
                    if cached_data:
                        sessions.append(cached_data)
                if sessions:
                    return {"sessions": sessions}
        
        # Fallback to database
        db_url = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
        conn = await asyncpg.connect(db_url)
        try:
            rows = await conn.fetch(
                """
                SELECT 
                    s.session_id, 
                    COALESCE(s.name, s.description, 'New Session') as name, 
                    COALESCE(s.current_state, s.state, 'idle') as state,
                    COALESCE(s.last_activity, s.updated_at, s.created_at, NOW()) as last_activity
                FROM sessions s
                ORDER BY s.last_activity DESC NULLS LAST
                LIMIT $1
                """,
                limit
            )
            
            sessions = []
            for row in rows:
                session_data = {
                    "session_id": row["session_id"],
                    "name": row["name"],
                    "state": row["state"] or "idle",
                    "last_activity": row["last_activity"].isoformat() if row["last_activity"] else datetime.utcnow().isoformat()
                }
                sessions.append(session_data)
                
                # Cache in Redis for next time
                if REDIS_AVAILABLE and redis_service:
                    await redis_service.cache_session(row["session_id"], session_data, ttl=300)
            
            return {"sessions": sessions}
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Error getting recent sessions: {e}")
        return {"sessions": []}

class PersistMessageRequest(BaseModel):
    message_id: str
    type: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    session_state: Optional[str] = None
    name: Optional[str] = None

@app.post("/api/sessions/{session_id}/messages")
async def persist_message(session_id: str, req: PersistMessageRequest):
    """Persist a chat message and optionally update session state/name."""
    db_url = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
    conn = await asyncpg.connect(db_url)
    try:
        # Ensure base tables
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS session_messages (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
                message_id VARCHAR(255) UNIQUE NOT NULL,
                type VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
        # Ensure session exists
        await conn.execute(
            "INSERT INTO sessions(session_id) VALUES($1) ON CONFLICT(session_id) DO NOTHING",
            session_id,
        )
        # Insert message (use UPSERT to handle duplicates gracefully)
        await conn.execute(
            """
            INSERT INTO session_messages(session_id, message_id, type, content, metadata)
            VALUES($1, $2, $3, $4, $5)
            ON CONFLICT(message_id) DO UPDATE SET
                content = EXCLUDED.content,
                metadata = EXCLUDED.metadata,
                created_at = CASE 
                    WHEN session_messages.created_at IS NULL THEN NOW()
                    ELSE session_messages.created_at
                END
            """,
            session_id,
            req.message_id,
            req.type,
            req.content,
            json.dumps(req.metadata or {}),
        )
        # Update session metadata
        updates = []
        params = []
        if req.name:
            updates.append("name = $%d" % (len(params)+1))
            params.append(req.name)
        if req.session_state:
            updates.append("current_state = $%d" % (len(params)+1))
            params.append(req.session_state)
        updates.append("last_activity = NOW()")
        if updates:
            query = f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = $%d" % (len(params)+1)
            params.append(session_id)
            await conn.execute(query, *params)
        return {"status": "ok"}
    finally:
        await conn.close()

@app.get("/api/sessions/{session_id}/full")
async def get_full_session(session_id: str):
    """Return complete session restoration payload."""
    db_url = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
    conn = await asyncpg.connect(db_url)
    try:
        # Session row
        try:
            sess = await conn.fetchrow(
                """
                SELECT session_id,
                       COALESCE(name, description, 'New Session') AS name,
                       COALESCE(current_state, 'idle') AS current_state,
                       COALESCE(last_activity, updated_at, created_at, NOW()) AS last_activity
                FROM sessions
                WHERE session_id = $1
                """,
                session_id,
            )
        except Exception:
            sess = await conn.fetchrow(
                """
                SELECT session_id,
                       COALESCE(description, 'New Session') AS name,
                       'idle' AS current_state,
                       COALESCE(updated_at, created_at, NOW()) AS last_activity
                FROM sessions
                WHERE session_id = $1
                """,
                session_id,
            )
        if not sess:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        # Messages
        try:
            msg_rows = await conn.fetch(
                "SELECT message_id, type, content, metadata, created_at FROM session_messages WHERE session_id=$1 ORDER BY created_at ASC",
                session_id,
            )
            messages = [
                {
                    "message_id": r["message_id"],
                    "type": r["type"],
                    "content": r["content"],
                    "metadata": r.get("metadata") or {},
                    "created_at": (r.get("created_at") or datetime.utcnow()).isoformat(),
                }
                for r in msg_rows
            ]
        except Exception:
            messages = []
        # Files
        file_rows = await conn.fetch(
            "SELECT id, filename, mime_type, size, path, uploaded_at FROM session_files WHERE session_id=$1 ORDER BY uploaded_at ASC",
            session_id,
        )
        files = [
            {
                "id": r["id"],
                "file_id": f"{session_id}:{r['filename']}",
                "filename": r["filename"],
                "mime_type": r["mime_type"],
                "size": r["size"],
                "preview_url": f"/api/files/{session_id}/{r['filename']}?inline=1",
                "download_url": f"/api/files/{session_id}/{r['filename']}?download=1",
                "path": r["path"],
                "uploaded_at": (r.get("uploaded_at") or datetime.utcnow()).isoformat(),
            }
            for r in file_rows
        ]
        # Analysis latest
        try:
            ha = await conn.fetchrow(
                """
                SELECT id, state, analysis_data, bog_data, feedback, created_at, updated_at
                FROM hvac_analysis_state
                WHERE session_id=$1
                ORDER BY updated_at DESC NULLS LAST, created_at DESC
                LIMIT 1
                """,
                session_id,
            )
            analysis = {
                "id": ha["id"],
                "state": ha["state"],
                "analysis_data": ha.get("analysis_data") or {},
                "bog_data": ha.get("bog_data") or {},
                "feedback": ha.get("feedback"),
                "created_at": (ha.get("created_at") or datetime.utcnow()).isoformat(),
                "updated_at": (ha.get("updated_at") or datetime.utcnow()).isoformat(),
            } if ha else None
        except Exception:
            analysis = None
        # BOG files
        try:
            bog_rows = await conn.fetch(
                """
                SELECT id, bog_name, file_path, download_url, generated_at, metadata
                FROM session_bog_files
                WHERE session_id=$1
                ORDER BY generated_at DESC
                """,
                session_id,
            )
            bog_files = [
                {
                    "id": r["id"],
                    "bog_name": r["bog_name"],
                    "file_path": r["file_path"],
                    "download_url": r["download_url"],
                    "generated_at": (r.get("generated_at") or datetime.utcnow()).isoformat(),
                    "metadata": r.get("metadata") or {},
                }
                for r in bog_rows
            ]
        except Exception:
            bog_files = []
        return {
            "session": {
                "session_id": sess["session_id"],
                "name": sess["name"],
                "current_state": sess.get("current_state", "idle"),
                "last_activity": (sess.get("last_activity") or datetime.utcnow()).isoformat(),
            },
            "messages": messages,
            "files": files,
            "analysis": analysis,
            "bog_files": bog_files,
        }
    finally:
        await conn.close()

# Duplicate endpoint removed - moved before /{session_id} patterns above

@app.get("/api/sessions/{session_id}/state", response_model=SessionStateResponse)
async def get_session_state(session_id: str):
    """Get current state of a session from database (hvac_chat_memory)."""
    try:
        db_url = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
        conn = await asyncpg.connect(db_url)
        try:
            # Query hvac_chat_memory with correct column names
            query = """
                SELECT session_id, role, content, state, data, created_at, updated_at
                FROM hvac_chat_memory
                WHERE session_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """
            row = await conn.fetchrow(query, session_id)
            if not row:
                raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

            state = 'UNKNOWN'
            analysis_data = None

            # Extract data from the 'data' jsonb column
            try:
                msg = row['data'] if isinstance(row['data'], dict) else {}
                if not msg and row['content']:
                    # Fallback: try to parse content as JSON
                    try:
                        msg = json.loads(row['content']) if isinstance(row['content'], str) else {}
                    except:
                        msg = {}
            except Exception:
                msg = {}

            status = (msg.get('status') or '').lower()
            if status in ('ready_for_review', 'ready'):
                state = 'AWAITING_APPROVAL'
                analysis_data = msg.get('analysis')
            elif status in ('generation_complete', 'generated'):
                state = 'DONE'
            elif status in ('processing', 'analyzing'):
                state = 'PROCESSING'
            else:
                state = 'UPLOADED'

            return SessionStateResponse(
                session_id=row['session_id'],
                state=state,
                analysis_data=analysis_data,
                created_at=row['created_at'].isoformat() if row.get('created_at') else datetime.utcnow().isoformat(),
                updated_at=row['updated_at'].isoformat() if row.get('updated_at') else datetime.utcnow().isoformat(),
            )
        finally:
            await conn.close()
    except asyncpg.PostgresError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")
    except Exception as e:
        logger.error(f"Error getting session state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/history")
async def get_session_history(session_id: str, limit: int = 100):
    """Return conversation history from hvac_chat_memory for a session."""
    try:
        db_url = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
        conn = await asyncpg.connect(db_url)
        try:
            rows = await conn.fetch(
                """
                SELECT session_id, role, content, state, data, created_at
                FROM hvac_chat_memory
                WHERE session_id = $1
                ORDER BY created_at ASC
                LIMIT $2
                """,
                session_id,
                limit,
            )
            out = []
            for r in rows:
                msg = {}
                try:
                    # Try to get message from 'data' column first
                    if r['data'] and isinstance(r['data'], dict):
                        msg = r['data']
                    # Otherwise, build from other columns
                    else:
                        msg = {
                            "role": r.get('role', 'system'),
                            "content": r.get('content', ''),
                            "state": r.get('state', 'idle')
                        }
                except Exception as e:
                    msg = {"raw": str(r), "error": str(e)}
                out.append({
                    "message": msg,
                    "created_at": (r['created_at'].isoformat() if r.get('created_at') else datetime.utcnow().isoformat()),
                })
            return {"sessionId": session_id, "messages": out}
        finally:
            await conn.close()
    except asyncpg.PostgresError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")
    except Exception as e:
        logger.error(f"Error getting session history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_id}/approve")
async def approve_analysis(session_id: str, request: WorkflowApprovalRequest):
    """Approve analysis and trigger BOG generation via n8n resume webhook"""
    try:
        if not request.approved:
            # Handle feedback/rejection case
            return {"message": "Analysis rejected, feedback recorded", "feedback": request.feedback}
        
        # Call n8n resume webhook to continue workflow
        n8n_url = os.getenv('N8N_URL', 'http://localhost:5678')
        resume_url = f"{n8n_url.rstrip('/')}/webhook/resume-chat"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(resume_url, json={
                "sessionId": session_id,
                "approved": True
            })
            
            if response.status_code == 200:
                return {
                    "message": "Analysis approved, BOG generation started",
                    "session_id": session_id,
                    "workflow_response": response.json()
                }
            else:
                logger.error(f"n8n webhook failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=502, 
                    detail=f"Workflow trigger failed: {response.text}"
                )
                
    except httpx.RequestError as e:
        logger.error(f"Request to n8n failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to connect to workflow engine")
    except Exception as e:
        logger.error(f"Error approving analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_id}/feedback")
async def submit_feedback(session_id: str, feedback: str):
    """Submit feedback for analysis changes and restart analysis"""
    try:
        # TODO: Implement feedback handling
        # This would trigger a new analysis cycle with the feedback
        return {
            "message": "Feedback submitted",
            "session_id": session_id,
            "feedback": feedback,
            "status": "pending_reanalysis"
        }
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analysis-progress")
async def analysis_progress(progress: dict):
    """Receive analysis progress updates from n8n and forward to frontend via WebSocket.
    Expected payload: { sessionId, step: 'started'|'parsed'|'ai_processing'|'waiting_review', message? }
    """
    try:
        session_id = progress.get('sessionId')
        if not session_id:
            raise HTTPException(status_code=400, detail="sessionId is required")

        step = progress.get('step', 'started')
        message = progress.get('message') or {
            'started': 'Analysis started…',
            'parsed': 'Document parsed…',
            'ai_processing': 'AI processing…',
            'waiting_review': 'Ready for review'
        }.get(step, 'Working…')

        # Persist as session message (best effort)
        try:
            db_url = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
            conn = await asyncpg.connect(db_url)
            try:
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS session_messages (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
                        message_id VARCHAR(255) UNIQUE NOT NULL,
                        type VARCHAR(50) NOT NULL,
                        content TEXT NOT NULL,
                        metadata JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    """
                )
                msg_id = f"progress_{int(datetime.utcnow().timestamp()*1000)}"
                await conn.execute(
                    """
                    INSERT INTO session_messages(session_id, message_id, type, content, metadata)
                    VALUES($1, $2, 'system', $3, $4)
                    ON CONFLICT(message_id) DO NOTHING
                    """,
                    session_id, msg_id, message, json.dumps({ 'step': step })
                )
            finally:
                await conn.close()
        except Exception:
            pass

        # Broadcast to WebSocket
        await manager.send_message(session_id, {
            'type': 'analysis_progress',
            'sessionId': session_id,
            'step': step,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        })
        return { 'status': 'ok' }
    except Exception as e:
        logger.error(f"Error processing analysis progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analysis-complete")
async def analysis_complete(analysis_data: dict):
    """Receive analysis from n8n and send to frontend via WebSocket"""
    try:
        session_id = analysis_data.get('sessionId')
        if not session_id:
            raise HTTPException(status_code=400, detail="sessionId is required")
        
        logger.info(f"Analysis complete received for session: {session_id}")
        
        # Parse analysis data
        analysis_parsed = analysis_data.get('analysis', {})
        if isinstance(analysis_parsed, str):
            try:
                analysis_parsed = json.loads(analysis_parsed)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse analysis data: {analysis_parsed}")
                analysis_parsed = {}
        
        # Normalize common field names from various workflow variants
        if 'blocks' not in analysis_parsed:
            if 'control_blocks' in analysis_parsed:
                analysis_parsed['blocks'] = analysis_parsed.get('control_blocks')
            elif 'controlBlocks' in analysis_parsed:
                analysis_parsed['blocks'] = analysis_parsed.get('controlBlocks')

        # Store resume webhook URL if provided by n8n Wait node
        resume_url = (
            analysis_data.get('resumeWebhookUrl')
            or analysis_data.get('resume_url')
            or analysis_data.get('resumeWebhook')
        )
        if resume_url:
            await store_resume_url(session_id, resume_url)
            logger.info(f"Stored resume webhook URL for session {session_id}")
        
        # Append structured message for polling fallback
        try:
            await append_message(session_id, {
                "type": "ai_analysis",
                "status": analysis_data.get('status', 'ready_for_review'),
                "inputs": analysis_parsed.get('inputs', []),
                "outputs": analysis_parsed.get('outputs', []),
                "pseudocode": analysis_parsed.get('pseudocode', []),
                "component_name": analysis_parsed.get('component_name'),
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.warning(f"Failed to append analysis message for session {session_id}: {e}")
        
        # Update session state to awaiting approval
        try:
            db_url = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
            conn = await asyncpg.connect(db_url)
            try:
                await conn.execute(
                    "UPDATE sessions SET current_state=$1, last_activity=NOW() WHERE session_id=$2",
                    'awaiting_approval',
                    session_id,
                )
            finally:
                await conn.close()
        except Exception as e:
            logger.warning(f"Failed to update session state for {session_id}: {e}")

        # Send to frontend via WebSocket
        await manager.send_analysis_complete(session_id, {
            "sessionId": session_id,
            "status": analysis_data.get('status', 'ready_for_review'),
            "message": analysis_data.get('message', 'Analysis complete'),
            "inputs": analysis_parsed.get('inputs', []),
            "outputs": analysis_parsed.get('outputs', []),
            "blocks": analysis_parsed.get('blocks', []),
            "pseudocode": analysis_parsed.get('pseudocode', []),
            "ready_for_review": True
        })
        
        return {"status": "forwarded", "session_id": session_id}
        
    except Exception as e:
        logger.error(f"Error processing analysis completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bog-generated")
async def bog_generated(generation_data: dict):
    """Receive BOG generation completion from n8n and send to frontend"""
    try:
        session_id = generation_data.get('sessionId')
        if not session_id:
            raise HTTPException(status_code=400, detail="sessionId is required")
        
        logger.info(f"BOG generation complete for session: {session_id}")
        
        download_url = generation_data.get('downloadUrl', '')
        message = generation_data.get('message', 'BOG file generated successfully!')
        
        # Append artifact message for polling fallback
        try:
            await append_message(session_id, {
                "type": "artifact",
                "fileUrl": download_url,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.warning(f"Failed to append artifact message for session {session_id}: {e}")

        # Track BOG file in session_bog_files and mark session complete
        try:
            db_url = os.getenv('DATABASE_URL', 'postgresql://pybog:pybog123@postgres:5432/pybog')
            conn = await asyncpg.connect(db_url)
            try:
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS session_bog_files (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) REFERENCES sessions(session_id) ON DELETE CASCADE,
                        analysis_id INTEGER,
                        bog_name VARCHAR(255) NOT NULL,
                        file_path TEXT NOT NULL,
                        download_url TEXT,
                        generated_at TIMESTAMPTZ DEFAULT NOW(),
                        metadata JSONB DEFAULT '{}'::jsonb
                    );
                    """
                )
                # Derive bog_name and file_path heuristically
                bog_name = None
                file_path = None
                try:
                    if download_url:
                        # If it's a path like /api/download/{session}/{filename}
                        parts = str(download_url).split('/')
                        if len(parts) >= 2:
                            bog_name = parts[-1]
                except Exception:
                    pass
                bog_name = bog_name or f"hvac_control_{session_id}"
                file_path = file_path or ''
                await conn.execute(
                    """
                    INSERT INTO session_bog_files(session_id, bog_name, file_path, download_url, metadata)
                    VALUES($1, $2, $3, $4, $5)
                    """,
                    session_id,
                    bog_name,
                    file_path,
                    download_url,
                    json.dumps({"message": message}),
                )
                await conn.execute(
                    "UPDATE sessions SET current_state=$1, last_activity=NOW() WHERE session_id=$2",
                    'complete',
                    session_id,
                )
            finally:
                await conn.close()
        except Exception as e:
            logger.warning(f"Failed to record BOG file for {session_id}: {e}")
        
        # Send to frontend via WebSocket
        await manager.send_bog_generated(session_id, download_url, message)
        
        return {"status": "forwarded", "session_id": session_id}
        
    except Exception as e:
        logger.error(f"Error processing BOG generation completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------
# WebSocket Support (Optional)
# ------------------------

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates"""
    try:
        await manager.connect(websocket, session_id)
        
        # Send initial connection confirmation
        await manager.send_message(session_id, {
            "type": "connected",
            "sessionId": session_id,
            "message": "WebSocket connected successfully",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message from {session_id}: {data}")
            
            # Handle ping/pong for connection keep-alive
            if data == "ping":
                await manager.send_message(session_id, {
                    "type": "pong",
                    "sessionId": session_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        manager.disconnect(session_id)

# ------------------------
# Docker Monitoring WebSocket Endpoints
# ------------------------

@app.websocket("/ws/health")
async def websocket_health(websocket: WebSocket):
    """WebSocket endpoint for system health monitoring"""
    client_id = str(uuid.uuid4())
    try:
        await manager.connect_health(websocket, client_id)
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        logger.info(f"Health WebSocket disconnected: {client_id}")
    finally:
        manager.disconnect_health(client_id)

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for Docker logs monitoring"""
    client_id = str(uuid.uuid4())
    try:
        await manager.connect_logs(websocket, client_id)
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        logger.info(f"Logs WebSocket disconnected: {client_id}")
    finally:
        manager.disconnect_logs(client_id)

# ------------------------
# Docker Monitoring API Endpoints
# ------------------------

@app.get("/api/docker/health")
async def get_system_health():
    """Get comprehensive system health including Docker containers"""
    if not DOCKER_AVAILABLE:
        return {"error": "Docker monitoring not available"}
    
    health = await docker_monitor.get_system_health()
    return health

@app.get("/api/docker/logs/{container_name}")
async def get_container_logs(container_name: str, tail: int = 50):
    """Get recent logs from a specific container"""
    if not DOCKER_AVAILABLE:
        return {"error": "Docker monitoring not available"}
    
    logs = await docker_monitor.get_container_logs(container_name, tail)
    return {"container": container_name, "logs": logs}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
