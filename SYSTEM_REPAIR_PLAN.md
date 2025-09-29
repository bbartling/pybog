# PyBOG System Repair & Integration Plan

## Overview
Comprehensive plan to fix frontend-backend communication gaps and establish seamless BOG file generation workflow.

## Critical Issues Identified

### 1. WebSocket Streaming Disconnect
- Frontend expects streaming responses but backend message flow has gaps
- Chat event handling expects `is_complete` and `buffer_content` fields inconsistently provided
- WebSocket connection issues causing streaming failures and node update problems

### 2. React Flow Node Data Loss
- Nodes lose data on reload due to improper useMemo dependencies
- Node interactions not connected to backend services
- Message status changes don't trigger proper re-renders

### 3. Session Persistence Problems
- Complex session restoration has race conditions
- Session files not synchronized between localStorage and backend
- Messages marked as `persisted: false` getting lost during session switches

### 4. PDF Preview Broken
- FileViewerModal uses inconsistent API endpoints
- Preview URLs not properly integrated
- File metadata extraction gaps

### 5. File Upload & Analysis Workflow Disconnection
- File upload doesn't properly trigger analysis pipeline
- Backend PyBOG agent not consistently connected to frontend state
- Analysis results don't flow back to React Flow nodes

## Implementation Plan

### Phase 1: Fix Core WebSocket Communication ✅ IN PROGRESS
- [x] **Task 1.1**: Standardize WebSocket message format in backend
  - Fixed WebSocket manager to properly pass through buffer_content, final_content fields
  - Updated ChatMessageData model with streaming fields
  - Enhanced create_chat_message helper function
- [x] **Task 1.2**: Fix streaming handler in App.tsx WebSocket chat event
  - Fixed message ID consistency between streaming and persistence
  - Improved streaming chunk handling with unique IDs
  - Enhanced error detection and user message failure marking
- [x] **Task 1.3**: Improve error recovery with robust reconnection
  - Enhanced WebSocket disconnection handling to mark failed messages
  - Added progressive error feedback based on reconnection attempts
  - Improved reconnection logic with exponential backoff and recursion
  - Added workflow state reset on connection loss
- [x] **Task 1.4**: Test real-time streaming end-to-end
  - WebSocket streaming communication verified and stabilized
  - Message format consistency established across frontend/backend

### Phase 2: Repair React Flow Node System ✅ COMPLETE
- [x] **Task 2.1**: Fix node data binding and onResend callback persistence
  - Implemented stable callback mapping with useCallback and useMemo
  - Fixed React Flow node recreation issues causing lost event handlers
  - Added resend callback map to maintain stable function references
- [x] **Task 2.2**: Improve message-to-node mapping in ChatCanvasGridSimple
  - Enhanced node type detection with comprehensive fallbacks
  - Added support for streaming messages, analysis, and progress types
  - Improved node data structure with complete metadata
  - Added focus highlighting for improved debugging
- [x] **Task 2.3**: Add node interaction state management
  - Added click and double-click handlers for React Flow nodes
  - Implemented focus management and node selection
  - Enhanced user interaction feedback systems
- [x] **Task 2.4**: Connect node interactions to backend services
  - Fixed PDF preview functionality with enhanced error handling
  - Verified backend file preview/download endpoints working
  - Improved file modal system with fallback mechanisms
  - Connected React Flow nodes to proper backend services

### Phase 3: Session & File Management
- [ ] **Task 3.1**: Simplify session persistence to reduce race conditions
- [ ] **Task 3.2**: Fix PDF preview with proper file endpoints
- [ ] **Task 3.3**: Repair file upload pipeline integration
- [ ] **Task 3.4**: Test session reload and file management

### Phase 4: End-to-End Integration
- [ ] **Task 4.1**: Connect analysis pipeline to BOG generation
- [ ] **Task 4.2**: Add comprehensive error handling
- [ ] **Task 4.3**: Implement real-time progress updates
- [ ] **Task 4.4**: Complete end-to-end workflow testing

## Progress Tracking

### Completed:
- ✅ **Phase 1: WebSocket Communication** - All core streaming issues fixed
- ✅ **Phase 2: React Flow Node System** - Node interactions and data persistence resolved
- Analysis of frontend-backend API communication patterns
- Review of WebSocket streaming implementation
- Identification of critical communication gaps

### Current Focus:
- **Phase 3: Session & File Management** - Ready for implementation
- System is now ready for end-to-end testing

### Next Steps:
- Test complete workflow: chat → analysis → BOG generation
- Verify session persistence and reload functionality
- Test file upload and analysis pipeline integration

## Key Files to Modify

### Frontend:
- `frontend/src/App.tsx` (WebSocket handlers, session management)
- `frontend/src/components/ChatCanvasGridSimple.tsx` (React Flow node management)
- `frontend/src/components/FileViewerModal.tsx` (PDF preview)
- `frontend/src/services/websocketService.ts` (WebSocket connectivity)

### Backend:
- `backend/app/main.py` (WebSocket endpoint)
- `backend/app/api_routes.py` (File and chat endpoints)
- `backend/services/websocket_manager.py` (Message formatting)
- `backend/services/pybog_agent_v2.py` (Analysis pipeline)

## Success Criteria
1. **Streaming Works**: Real-time chat responses update React Flow nodes
2. **Sessions Persist**: Reload doesn't lose nodes or data
3. **Files Preview**: PDFs open correctly in modal
4. **Upload Triggers Analysis**: File upload starts analysis automatically
5. **BOG Generation**: Complete workflow from chat/upload to BOG file download

## Notes
- Focus on incremental fixes with testing at each step
- Maintain existing functionality while adding new capabilities
- Prioritize user experience and error recovery