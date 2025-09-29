# Implementation Plan

- [x] 1. System cleanup and PyBOG integration





  - Remove conflicting api/ directory and consolidate all backend code into backend/
  - Pull latest PyBOG code from "C:\Users\tech\Projects\pybog-cnoccir" and update bog_builder module
  - Clean up old n8n references and unused imports throughout the codebase
  - Update requirements.txt to remove duplicate dependencies and add missing ones
  - _Requirements: 1.1, 1.2, 1.5_

- [x] 2. Fix and complete database integration














  - Review and test existing database connection in backend/core/config.py
  - Complete database service implementation to connect existing services to PostgreSQL
  - Fix session persistence and chat message storage in SessionService
  - Test file storage with both BYTEA and file system paths in FileService
  - _Requirements: 1.4, 3.1, 3.2_

- [x] 3. Complete WebSocket integration and fix broken connections








  - Fix WebSocket endpoint in backend/app/main.py to properly handle session connections
  - Connect existing WebSocketManager to EventBus for real-time communication
  - Test and fix session resume functionality with event replay
  - Ensure WebSocket messages use standardized envelope format from websocket_models.py
  - _Requirements: 9.1, 9.2, 9.3, 9.5_

- [x] 4. Complete file processing and text extraction





  - Implement missing text extraction methods in FileService for PDF, DOCX, and text files
  - Add file preview generation and metadata extraction
  - Complete file cleanup background task implementation
  - Test hybrid storage decision logic (BYTEA vs file system)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 5. Enhance and connect AI agent functionality






  - Complete PyBOGAgentV2 implementation with proper OpenAI integration
  - Add streaming response capability through WebSocket events
  - Implement HVAC domain knowledge and expert guidance prompts
  - Connect agent to chat endpoints in api_routes.py for real conversations
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 6. Complete analysis engine and BOG generation





  - Finish AnalysisEngine implementation with document analysis capabilities
  - Integrate updated PyBOG builder for BOG file generation from analysis results
  - Add analysis quality assessment and validation logic
  - Connect analysis results to file storage and session management
  - _Requirements: 6.2, 6.3, 7.1, 7.2, 7.3_

- [x] 7. Fix frontend API integration













  - Update frontend UnifiedAPIService to use correct backend endpoints from api_routes.py
  - Remove all old n8n workflow references from frontend services
  - Fix WebSocket service connection to use new backend WebSocket endpoint
  - Test and fix session management, file upload, and chat functionality
  - _Requirements: 2.5, 9.3, 9.4_

- [x] 8. Restore and enhance file viewer functionality





  - Fix FileViewerModal component to work with new backend file endpoints
  - Restore PDF preview, zoom, and navigation capabilities
  - Update file management interface to show proper file metadata and status
  - Ensure Neo Brutalism styling is preserved throughout file viewer
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 9. Implement review and approval workflow





  - Create text review nodes for extracted document content approval
  - Add analysis review interface with user feedback and modification options
  - Implement workflow state management with proper transitions
  - Connect approval workflow to WebSocket for real-time updates
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 10. Enhance Neo Brutalism UI and fix node interactions





  - Fix ChatCanvasGrid node positioning and collision detection
  - Implement text truncation with popup functionality for long content
  - Enhance React Flow animations and edge styling for different workflow states
  - Ensure proper spacing and visual hierarchy in wiresheet design
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 11. Complete error handling and recovery





  - Implement comprehensive error handling in all backend services
  - Add standardized error codes and user-friendly error messages
  - Create error recovery suggestions and retry mechanisms
  - Test error scenarios and ensure proper WebSocket error communication
  - _Requirements: 5.4, 5.5, 9.4_

- [x] 12. Fix Docker deployment and service orchestration























  - Update docker-compose.yml to use only the unified backend (remove api service)
  - Fix backend Dockerfile to include all necessary dependencies
  - Ensure proper service health checks and dependency management
  - Test complete system startup and connectivity between all services
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 13. Integration testing and system validation







  - Test complete workflow: session creation → file upload → text extraction → analysis → BOG generation
  - Validate WebSocket communication and session resume functionality
  - Test concurrent sessions and multi-user scenarios
  - Verify file storage, cleanup, and retention policies work correctly
  - _Requirements: 3.4, 5.4, 6.5, 7.4, 9.5_

- [ ] 14. Performance optimization and monitoring
  - Add structured logging throughout backend services
  - Implement basic performance monitoring for database and API operations
  - Add system health monitoring and alerting for critical failures
  - Optimize database queries and connection pooling for production use
  - _Requirements: 8.5, 9.3_