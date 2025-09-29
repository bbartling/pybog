# Design Document

## Overview

This design focuses on creating a unified, production-ready PyBOG HVAC Control Builder system by consolidating multiple backend implementations into a single FastAPI backend, preserving the Neo Brutalism frontend, and establishing a complete workflow for HVAC document analysis and BOG file generation. The system will integrate the latest PyBOG features from the source repository and provide real-time communication through WebSocket connections.

## Architecture

### System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   PostgreSQL    │  │     Redis       │  │    pgAdmin      │ │
│  │   + pgvector    │  │     Cache       │  │   Management    │ │
│  │   Port: 5432    │  │   Port: 6379    │  │   Port: 5847    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────┐
│                   Unified FastAPI Backend                       │
│                        Port: 8847                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   WebSocket     │  │   LangChain     │  │   PyBOG BOG     │ │
│  │   Manager       │  │   AI Agent      │  │   Generator     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Session       │  │   File          │  │   Analysis      │ │
│  │   Service       │  │   Service       │  │   Engine        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                  │
                              WebSocket + HTTP
                                  │
┌─────────────────────────────────────────────────────────────────┐
│              Neo Brutalism React Frontend                       │
│                        Port: 3847                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Chat Canvas   │  │   File Viewer   │  │   Session       │ │
│  │   Grid (React   │  │   Modal         │  │   Manager       │ │
│  │   Flow)         │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   WebSocket     │  │   Unified API   │  │   Progress      │ │
│  │   Service       │  │   Service       │  │   Tracking      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend (Unified FastAPI)**
- FastAPI 0.104+ with WebSocket support
- Python 3.11+ with asyncio for concurrent processing
- LangChain for AI agent functionality with OpenAI integration
- PyBOG integration from latest source repository
- asyncpg for PostgreSQL database operations
- Pydantic for data validation and serialization

**Database Layer**
- PostgreSQL 15+ with pgvector extension
- Unified schema for sessions, chat history, files, and analysis
- Hybrid file storage (BYTEA for <10MB, file system for larger files)
- Automated cleanup and retention policies

**Frontend (Preserved Neo Brutalism)**
- React 18 with TypeScript
- React Flow for wiresheet-style node visualization
- Material-UI with custom Neo Brutalism theme
- WebSocket client for real-time updates
- Professional file viewer with PDF/document support

**Infrastructure**
- Docker Compose for complete system orchestration
- nginx for production frontend serving
- Redis for caching and session management
- pgAdmin for database administration

## Components and Interfaces

### 1. Unified FastAPI Backend

#### Core Application Structure
```python
# main.py - Application entry point
app = FastAPI(
    title="PyBOG HVAC Control Builder",
    version="3.0.0",
    description="Unified backend for HVAC control sequence analysis and BOG generation"
)

# Middleware configuration
app.add_middleware(CORSMiddleware, allow_origins=config.cors_origins)
app.add_middleware(WebSocketMiddleware)

# Route organization
app.include_router(session_router, prefix="/api/sessions")
app.include_router(file_router, prefix="/api/files") 
app.include_router(analysis_router, prefix="/api/analysis")
app.include_router(websocket_router, prefix="/ws")
```

#### Session Management Service
```python
class SessionService:
    """Handles session lifecycle and persistence"""
    
    async def create_session(self, name: str) -> Session:
        """Create new session with unique ID"""
        
    async def get_session(self, session_id: str) -> Session:
        """Retrieve session with associated data"""
        
    async def update_session(self, session_id: str, updates: dict) -> Session:
        """Update session metadata"""
        
    async def delete_session(self, session_id: str) -> bool:
        """Delete session and all associated data"""
        
    async def list_user_sessions(self) -> List[Session]:
        """List all sessions for management interface"""
```

#### File Management Service
```python
class FileService:
    """Handles file upload, storage, and retrieval with hybrid storage strategy"""
    
    async def upload_file(self, session_id: str, file: UploadFile) -> FileRecord:
        """Upload file with automatic storage decision (BYTEA vs file system)"""
        
    async def get_file_content(self, file_id: int) -> bytes:
        """Retrieve file content from BYTEA or file system"""
        
    async def get_file_metadata(self, file_id: int) -> FileRecord:
        """Get file metadata and preview information"""
        
    async def extract_text_content(self, file_id: int) -> TextExtractionResult:
        """Extract text from PDF, DOCX, or text files"""
        
    async def delete_file(self, file_id: int) -> bool:
        """Delete file and cleanup storage"""
        
    async def cleanup_old_files(self) -> CleanupResult:
        """Background task for file retention policy"""
```

#### Analysis Engine
```python
class AnalysisEngine:
    """Handles HVAC document analysis and BOG file generation"""
    
    async def analyze_document(self, session_id: str, file_id: int) -> AnalysisResult:
        """Analyze HVAC document and extract control logic"""
        
    async def generate_bog_file(self, session_id: str, analysis_data: dict) -> int:
        """Generate PyBOG BOG file from analysis results"""
        
    async def get_analysis_status(self, analysis_id: int) -> AnalysisStatus:
        """Get current status of analysis operation"""
        
    async def cancel_analysis(self, analysis_id: int) -> bool:
        """Cancel running analysis operation"""
```

#### LangChain AI Agent
```python
class PyBOGAgent:
    """Intelligent conversational agent for HVAC guidance"""
    
    async def process_chat_message(self, session_id: str, message: str) -> None:
        """Process user message and generate streaming response"""
        
    async def analyze_hvac_sequence(self, content: str) -> HVACAnalysis:
        """Analyze HVAC control sequence and extract components"""
        
    async def provide_guidance(self, context: dict) -> str:
        """Provide expert guidance on HVAC control design"""
        
    async def review_analysis_quality(self, analysis: dict) -> QualityAssessment:
        """Review and assess analysis quality"""
```

### 2. WebSocket Communication System

#### WebSocket Manager
```python
class WebSocketManager:
    """Manages WebSocket connections and real-time communication"""
    
    async def connect_session(self, websocket: WebSocket, session_id: str):
        """Connect WebSocket to session with authentication"""
        
    async def broadcast_to_session(self, session_id: str, message: WebSocketMessage):
        """Broadcast message to all connections for a session"""
        
    async def handle_session_events(self, session_id: str, event: Event):
        """Handle events from event bus and broadcast to WebSocket"""
        
    async def resume_session(self, session_id: str, websocket: WebSocket):
        """Resume session by replaying recent events"""
```

#### Message Envelope System
```python
class WebSocketMessage(BaseModel):
    """Standardized WebSocket message format"""
    type: Literal["chat", "progress", "analysis_complete", "error", "file_uploaded"]
    session_id: str
    data: Dict[str, Any]
    timestamp: datetime
    
class ProgressUpdate(BaseModel):
    """Progress tracking for long-running operations"""
    operation: str  # 'extract_text', 'analyze_document', 'generate_bog'
    state: ProgressState  # 'queued', 'processing', 'finalizing', 'complete', 'failed'
    progress_percent: Optional[int]
    message: str
    metadata: Dict[str, Any] = {}
```

### 3. Neo Brutalism Frontend Integration

#### Unified API Service
```typescript
class UnifiedAPIService {
  // Session management
  async createSession(name: string): Promise<Session>
  async getSession(sessionId: string): Promise<SessionWithFiles>
  async deleteSession(sessionId: string): Promise<void>
  async renameSession(sessionId: string, name: string): Promise<void>
  
  // File operations
  async uploadFile(sessionId: string, file: File): Promise<FileUploadResult>
  async getFilePreview(fileId: number): Promise<string>
  async downloadFile(fileId: number): Promise<Blob>
  
  // Analysis operations
  async startAnalysis(sessionId: string, fileId: number): Promise<AnalysisResult>
  async getAnalysisStatus(analysisId: number): Promise<AnalysisStatus>
  async cancelAnalysis(analysisId: number): Promise<void>
}
```

#### WebSocket Service
```typescript
class WebSocketService {
  connect(sessionId: string): Promise<WebSocket>
  disconnect(): void
  
  // Event handlers
  onChatResponse(callback: (content: string, isComplete: boolean) => void): void
  onProgress(callback: (update: ProgressUpdate) => void): void
  onAnalysisComplete(callback: (result: AnalysisResult) => void): void
  onError(callback: (error: ErrorMessage) => void): void
  
  // Send messages
  sendChatMessage(message: string): void
  sendFileApproval(fileId: number, approved: boolean): void
}
```

#### Chat Canvas Grid (Enhanced)
```typescript
interface ChatCanvasGridProps {
  messages: ChatMessage[]
  sessionId: string
  onApproveAnalysis: () => void
  onRequestChanges: (feedback: string) => void
  onResendMessage: (message: ChatMessage) => void
  workflowState: WorkflowState
  focusMessageId?: string
}

// Enhanced node types for different message types
const nodeTypes = {
  userMessage: UserNodeWithResend,
  systemMessage: SystemNodeNiagara,
  analysisMessage: AnalysisGridNode,
  progressMessage: ProgressNode,
  textReviewMessage: TextReviewNode,
  filePreviewMessage: FilePreviewNode,
}
```

## Data Models

### Core Data Models

```python
# Session Management
class Session(BaseModel):
    session_id: str
    name: str
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

class ChatMessage(BaseModel):
    id: int
    session_id: str
    message_type: Literal["user", "assistant", "system"]
    content: str
    metadata: Dict[str, Any] = {}
    created_at: datetime

# File Management with Hybrid Storage
class FileRecord(BaseModel):
    id: int
    session_id: str
    filename: str
    original_name: str
    mime_type: Optional[str]
    file_type: Literal["upload", "bog", "analysis", "document"]
    file_size: int
    state: ProgressState
    storage_type: Literal["bytea", "file_path"]
    metadata: Dict[str, Any] = {}
    created_at: datetime
    archived_at: Optional[datetime] = None

# HVAC Analysis Models
class IOPoint(BaseModel):
    name: str
    type: Literal["input", "output"]
    data_type: Literal["boolean", "numeric", "string", "enum"]
    units: Optional[str] = None
    description: str
    range_min: Optional[float] = None
    range_max: Optional[float] = None

class ControlBlock(BaseModel):
    name: str
    type: str  # "PID", "Schedule", "Logic", "Alarm", etc.
    description: str
    inputs: List[str]
    outputs: List[str]
    parameters: Dict[str, Any] = {}
    logic_description: str

class HVACSequence(BaseModel):
    equipment_type: str  # "AHU", "VAV", "Chiller", etc.
    operation_modes: List[str]
    control_stages: List[str]
    economizer_config: Optional[Dict[str, Any]] = None
    schedule_requirements: Optional[Dict[str, Any]] = None

class AnalysisResult(BaseModel):
    id: int
    session_id: str
    input_file_id: int
    bog_file_id: Optional[int] = None
    state: ProgressState
    hvac_sequence: HVACSequence
    io_points: List[IOPoint]
    control_blocks: List[ControlBlock]
    pseudocode: List[Dict[str, Any]]
    quality_score: float
    issues: List[str] = []
    recommendations: List[str] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime
    completed_at: Optional[datetime] = None

# Progress and State Management
class ProgressState(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"

class WorkflowState(BaseModel):
    state: Literal["idle", "analyzing", "awaiting_approval", "generating", "complete"]
    current_operation: Optional[str] = None
    progress_percent: Optional[int] = None
    resume_url: Optional[str] = None
    metadata: Dict[str, Any] = {}
```

### PyBOG Integration Models

```python
# PyBOG Builder Integration
class PyBOGConfig(BaseModel):
    folder_name: str
    components: List[ComponentDefinition]
    links: List[LinkDefinition]
    reduction_blocks: List[ReductionBlockDefinition]
    metadata: Dict[str, Any] = {}

class BOGGenerationRequest(BaseModel):
    session_id: str
    analysis_id: int
    config_overrides: Optional[Dict[str, Any]] = None
    output_format: Literal["bog", "json", "both"] = "bog"

class BOGGenerationResult(BaseModel):
    bog_file_id: int
    bog_file_path: str
    generation_log: List[str]
    warnings: List[str] = []
    errors: List[str] = []
    metadata: Dict[str, Any] = {}
```

## Error Handling

### Standardized Error Management

```python
class ErrorHandler:
    """Centralized error handling with categorized error codes"""
    
    ERROR_CATEGORIES = {
        "FILE": "File upload, processing, or storage errors",
        "ANALYSIS": "Document analysis and LLM processing errors", 
        "BOG": "PyBOG generation and validation errors",
        "DB": "Database connection and query errors",
        "WEBSOCKET": "WebSocket connection and communication errors",
        "AUTH": "Authentication and authorization errors",
        "VALIDATION": "Input validation and data format errors"
    }
    
    async def handle_error(
        self,
        error_code: str,
        operation: str,
        error: Exception,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorResponse
```

### Error Response Format

```python
class ErrorResponse(BaseModel):
    error_code: str  # "FILE", "ANALYSIS", "BOG", "DB", "WEBSOCKET", "AUTH", "VALIDATION"
    operation: str   # "upload_file", "analyze_document", "generate_bog", etc.
    message: str
    session_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    recovery_suggestions: List[str] = []
    retry_possible: bool = False
```

## Testing Strategy

### Comprehensive Testing Approach

**Unit Tests**
- Service layer functionality (SessionService, FileService, AnalysisEngine)
- PyBOG integration and BOG file generation
- WebSocket message handling and event bus operations
- Database operations and data model validation
- Error handling and recovery scenarios

**Integration Tests**
- End-to-end workflow: upload → extract → analyze → generate BOG
- WebSocket real-time communication and session resume
- File storage hybrid logic (BYTEA vs file system)
- Frontend-backend API integration
- Database transaction integrity

**Performance Tests**
- Concurrent WebSocket connections and message throughput
- Large file upload and processing performance
- Database query optimization and connection pooling
- Memory usage during long-running analysis operations

**Frontend Tests**
- React Flow node rendering and interaction
- WebSocket service connection and reconnection
- File upload progress and error handling
- Session management and persistence
- Neo Brutalism theme consistency

### Test Structure

```
tests/
├── unit/
│   ├── test_session_service.py
│   ├── test_file_service.py
│   ├── test_analysis_engine.py
│   ├── test_pybog_integration.py
│   └── test_websocket_manager.py
├── integration/
│   ├── test_complete_workflow.py
│   ├── test_websocket_communication.py
│   ├── test_file_storage_hybrid.py
│   └── test_frontend_backend_integration.py
├── performance/
│   ├── test_concurrent_sessions.py
│   ├── test_large_file_processing.py
│   └── test_database_performance.py
└── frontend/
    ├── test_chat_canvas_grid.py
    ├── test_websocket_service.py
    └── test_session_management.py
```

## Deployment Architecture

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  # Database with pgvector extension
  postgres:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_USER: pybog
      POSTGRES_PASSWORD: pybog123
      POSTGRES_DB: pybog
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init_database.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pybog"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis for caching and session management
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  # Unified FastAPI Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://pybog:pybog123@postgres:5432/pybog
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data/uploads:/app/data/uploads
      - ./data/outputs:/app/data/outputs
    ports:
      - "8847:8000"
    depends_on:
      postgres:
        condition: service_healthy

  # Neo Brutalism Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      - REACT_APP_API_URL=http://localhost:8847
    ports:
      - "3847:80"
    depends_on:
      - backend

  # Database Administration
  pgadmin:
    image: dpage/pgadmin4:latest
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@pybog.local
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5847:80"
    depends_on:
      - postgres
```

### Production Considerations

**Security**
- Environment variable management for sensitive configuration
- HTTPS/WSS encryption for production deployment
- Database connection encryption and authentication
- File upload validation and virus scanning
- Rate limiting for API endpoints and WebSocket connections

**Scalability**
- Horizontal scaling with load balancer for multiple backend instances
- Database connection pooling and read replicas
- Redis clustering for session management
- CDN integration for static file serving
- Background task queue for long-running operations

**Monitoring**
- Application performance monitoring (APM) integration
- Database query performance tracking
- WebSocket connection monitoring
- Error rate and response time alerting
- Resource usage monitoring (CPU, memory, disk)

**Backup and Recovery**
- Automated database backups with point-in-time recovery
- File storage backup strategy for uploaded documents
- Configuration backup and version control
- Disaster recovery procedures and testing