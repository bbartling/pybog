# Requirements Document

## Introduction

This project involves a comprehensive system restoration and streamlining of the PyBOG HVAC Control Builder application. The current system is in a broken state after an incomplete backend migration, with multiple conflicting backend implementations and a disconnected frontend. The goal is to create a fully functional, dockerized system with a unified FastAPI backend, preserved Neo Brutalism frontend, and complete chat-based workflow for HVAC control sequence analysis and BOG file generation. The system must integrate the latest PyBOG features from the source repository and provide a seamless user experience for uploading files, reviewing extracted content, and generating control logic.

## Requirements

### Requirement 1

**User Story:** As a developer, I want a clean, unified backend architecture, so that the system has a single source of truth and eliminates conflicting implementations.

#### Acceptance Criteria

1. WHEN reviewing the codebase THEN the system SHALL consolidate the multiple backend implementations (`api/` and `backend/`) into a single unified FastAPI backend
2. WHEN integrating PyBOG features THEN the system SHALL pull the latest code from "C:\Users\tech\Projects\pybog-cnoccir" and update the bog_builder module with current functionality
3. WHEN implementing the backend THEN the system SHALL use FastAPI with WebSocket support for real-time communication
4. WHEN handling database operations THEN the system SHALL use a single PostgreSQL database with proper schema for sessions, files, chat history, and analysis results
5. IF legacy code conflicts exist THEN the system SHALL remove outdated implementations and maintain only the working unified backend

### Requirement 2

**User Story:** As a user, I want the Neo Brutalism frontend to be fully functional and connected to the backend, so that I can interact with the system through the professional wiresheet-style interface.

#### Acceptance Criteria

1. WHEN using the interface THEN the system SHALL preserve the existing Neo Brutalism styling and Tridium Niagara wiresheet design
2. WHEN interacting with the chat canvas THEN the system SHALL maintain the react-flow nodes and edges with proper animations and spacing
3. WHEN text is long in nodes THEN the system SHALL truncate content and provide popups for full text viewing
4. WHEN nodes are positioned THEN the system SHALL implement smart design principles for zero collision and proper spacing
5. WHEN connecting to the backend THEN the system SHALL update all API calls to use the unified FastAPI endpoints instead of old n8n workflows

### Requirement 3

**User Story:** As a user, I want complete session management functionality, so that I can create, manage, and persist chat sessions with associated files.

#### Acceptance Criteria

1. WHEN creating a session THEN the system SHALL generate a unique session ID and store it in the database
2. WHEN uploading files THEN the system SHALL associate files with the current session and store them securely
3. WHEN viewing sessions THEN the system SHALL display all associated files with proper preview capabilities
4. WHEN switching sessions THEN the system SHALL load the complete session state including chat history and files
5. WHEN deleting sessions THEN the system SHALL remove all associated data including files and chat history

### Requirement 4

**User Story:** As a user, I want intelligent chat functionality with an AI agent, so that I can get expert guidance on HVAC control systems and sequence design.

#### Acceptance Criteria

1. WHEN starting a conversation THEN the system SHALL greet users professionally and prompt for next steps
2. WHEN asking questions THEN the system SHALL provide knowledgeable responses about HVAC control systems using OpenAI LLM
3. WHEN reviewing partial sequences THEN the system SHALL provide expert guidance and direction for completion
4. WHEN designing sequences THEN the system SHALL walk users through a conversational Q&A process
5. WHEN providing guidance THEN the system SHALL leverage professional agent knowledge to suggest optimal approaches

### Requirement 5

**User Story:** As a user, I want robust file processing capabilities, so that I can upload and extract content from various document types for analysis.

#### Acceptance Criteria

1. WHEN uploading PDF files THEN the system SHALL extract text content and make it available for review
2. WHEN uploading DOCX files THEN the system SHALL extract formatted text content accurately
3. WHEN uploading text files THEN the system SHALL process the content directly
4. WHEN extraction completes THEN the system SHALL present the extracted text to the user for review and approval
5. IF extraction fails THEN the system SHALL provide clear error messages and retry options

### Requirement 6

**User Story:** As a user, I want a comprehensive review and approval workflow, so that I can verify extracted content and analysis results before BOG file generation.

#### Acceptance Criteria

1. WHEN text extraction completes THEN the system SHALL display the extracted content in a review interface
2. WHEN reviewing extracted text THEN the system SHALL allow users to edit, approve, or request re-extraction
3. WHEN analysis completes THEN the system SHALL present analysis results for user review and approval
4. WHEN walking through sequence design THEN the system SHALL provide Q&A interactions for user confirmation
5. WHEN users approve content THEN the system SHALL proceed to the next workflow step automatically

### Requirement 7

**User Story:** As a user, I want PyBOG file generation and management, so that I can create, download, and store control logic files.

#### Acceptance Criteria

1. WHEN analysis is approved THEN the system SHALL generate PyBOG BOG files using the integrated bog_builder
2. WHEN BOG files are created THEN the system SHALL store them associated with the chat session
3. WHEN BOG files are ready THEN the system SHALL provide download links and file management options
4. WHEN viewing session files THEN the system SHALL display all uploaded documents and generated BOG files
5. WHEN managing files THEN the system SHALL provide preview, download, and deletion capabilities

### Requirement 8

**User Story:** As a developer, I want a fully dockerized deployment system, so that the entire application can be deployed consistently with all dependencies contained.

#### Acceptance Criteria

1. WHEN deploying the system THEN the system SHALL use Docker containers for all components
2. WHEN starting services THEN the system SHALL include PostgreSQL database and pgAdmin in the container stack
3. WHEN running the backend THEN the system SHALL containerize the FastAPI application with all dependencies
4. WHEN serving the frontend THEN the system SHALL use a production-ready container with proper nginx configuration
5. WHEN orchestrating services THEN the system SHALL use docker-compose for complete system deployment

### Requirement 9

**User Story:** As a user, I want real-time communication and progress tracking, so that I can see live updates during file processing and analysis.

#### Acceptance Criteria

1. WHEN processing files THEN the system SHALL provide real-time progress updates via WebSocket connections
2. WHEN analysis is running THEN the system SHALL stream progress information to the chat interface
3. WHEN operations complete THEN the system SHALL notify users immediately with results
4. WHEN errors occur THEN the system SHALL provide immediate feedback with clear error messages
5. WHEN reconnecting THEN the system SHALL restore session state and continue from the last known position

### Requirement 10

**User Story:** As a user, I want the professional file viewer functionality restored, so that I can preview and interact with uploaded documents effectively.

#### Acceptance Criteria

1. WHEN viewing PDF files THEN the system SHALL display them in the professional Neo Brutalism file viewer
2. WHEN previewing documents THEN the system SHALL maintain the existing viewer styling and functionality
3. WHEN interacting with files THEN the system SHALL provide zoom, navigation, and text selection capabilities
4. WHEN managing multiple files THEN the system SHALL organize them clearly within the session interface
5. WHEN accessing file metadata THEN the system SHALL display file information, upload dates, and processing status