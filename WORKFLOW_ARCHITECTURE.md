# PyBOG N8N Workflow Architecture

## Overview

PyBOG uses two sophisticated N8N workflows to handle document ingestion, analysis, and BOG generation. These workflows integrate with OpenAI for text extraction and analysis, PostgreSQL for state management, and the PyBOG API for BOG file generation.

## Workflow 1: Document Ingestion (`/webhook/ingest-doc`)

### Purpose
Handles file upload, text extraction using OpenAI, and prepares data for analysis.

### Trigger
- **Webhook URL**: `http://localhost:5678/webhook/ingest-doc`
- **Method**: POST
- **Accepts**: Binary files and JSON metadata

### Data Flow

```
1. Webhook Trigger (receives files)
       ↓
2. Initialize Conversation
   - Extracts sessionId, userMessage, conversationHistory
   - Identifies uploaded files
       ↓
3. Has Files? (conditional branch)
       ├─Yes→ Process Files
       │      ↓
       │   4. Split In Batches (process each file)
       │      ↓
       │   5. Upload File to OpenAI
       │      - Uses OpenAI assistants API
       │      - Purpose: "assistants"
       │      ↓
       │   6. Extract Text with OpenAI
       │      - Model: gpt-4o-mini
       │      - Extracts text content
       │      ↓
       │   7. Get Extracted Text
       │      - Parses OpenAI response
       │      ↓
       │   8. Aggregate
       │      - Collects all file extractions
       │      ↓
       │   9. Concatenate Text
       │      - Combines all extracted text
       │      ↓
       └─No→  Set Empty Extracted
              ↓
10. Merge Branches
       ↓
11. Prepare Payload
    - Returns: sessionId, userMessage, conversationHistory, extracted_text
       ↓
12. Webhook Response
```

### Input Format
```json
{
  "sessionId": "session_123",
  "message": "Analyze this HVAC spec",
  "history": [],
  "files": [binary data]
}
```

### Output Format
```json
{
  "sessionId": "session_123",
  "userMessage": "Analyze this HVAC spec",
  "conversationHistory": [],
  "extracted_text": "Full extracted text from all files..."
}
```

## Workflow 2: Analysis & BOG Generation (`/webhook/resume-chat`)

### Purpose
Retrieves analyzed data from database, formats it for PyBOG API, triggers BOG generation.

### Trigger
- **Webhook URL**: `http://localhost:5678/webhook/resume-chat`
- **Method**: POST
- **Called when**: User approves analysis results

### Data Flow

```
1. Resume Webhook
   - Receives approval signal with sessionId
       ↓
2. Retrieve Analysis (PostgreSQL)
   - Query: SELECT from hvac_chat_memory
   - Filter: session_id AND state='pending_approval'
   - Sort: created_at DESC
       ↓
3. Schema Formatter (JavaScript)
   - Parses stored analysis data
   - Maps to PyBOG API schema:
     • inputs: Array of sensor definitions
     • outputs: Array of actuator definitions
     • control_sequences: Logic blocks
     • setpoints: Default values
       ↓
4. Call PyBOG API
   - URL: http://api:8000/api/generate-bog
   - Method: POST
   - Timeout: 45 seconds
       ↓
5. Update Completion State (PostgreSQL)
   - Updates session state in hvac_chat_memory
       ↓
6. Prepare Final Response
   - Formats response with download URL
   - Sets status (COMPLETED/ERROR)
       ↓
7. Final Webhook Response
       ↓
8. Notify BOG Generated
   - URL: http://api:8000/api/bog-generated
   - Sends download URL to frontend via WebSocket
```

### Input Format (Approval)
```json
{
  "sessionId": "session_123",
  "approved": true
}
```

### Schema Formatter Output (to PyBOG API)
```json
{
  "bog_name": "hvac_control_session_123",
  "session_id": "session_123",
  "inputs": [
    {
      "name": "Supply_Air_Temperature",
      "type": "temperature",
      "units": "°F",
      "default_value": 0.0
    }
  ],
  "outputs": [
    {
      "name": "Supply_Damper",
      "type": "damper",
      "control_type": "modulating",
      "range": "0-100%",
      "default_value": 0.0
    }
  ],
  "control_sequences": [
    {
      "name": "Temperature_Control",
      "type": "sequence",
      "description": "Control logic for Temperature_Control",
      "components": ["Supply_Air_Temperature", "Supply_Damper"],
      "logic": "IF supply_temp > setpoint THEN modulate_damper(50%)"
    }
  ],
  "setpoints": {
    "temperature_deadband": 2.0,
    "pressure_deadband": 1.0,
    "default_timeout": 300
  }
}
```

## How My Simple Workflow Helped

My unified workflow template (`Unified-PyBOG-Workflow.json`) was created to:

1. **Establish webhook endpoints** that the frontend expected
2. **Create a basic data flow** for testing
3. **Provide a fallback** when the actual workflows aren't activated

However, it's **NOT a replacement** for your sophisticated workflows. It was meant as scaffolding to get the integration working.

## The Real Solution

To make everything work properly:

### 1. Import and Activate Your Workflows
```bash
# In N8N UI (http://localhost:5678):
1. Import "Workflow 1 - Ingestion.json"
2. Import "Workflow 2 - AnalysisChat.json"
3. Configure OpenAI credentials in both
4. Configure PostgreSQL credentials
5. Activate both workflows
```

### 2. Frontend Now Uses Correct Endpoints
After our fixes, the frontend now calls:
- `/api/n8n/webhook/ingest-doc` (via proxy) → Workflow 1
- `/api/n8n/webhook/resume-chat` (via proxy) → Workflow 2

### 3. Data Flow Works End-to-End
```
User uploads document
    ↓
Frontend → API proxy → N8N Workflow 1 (ingest-doc)
    ↓
OpenAI extracts text
    ↓
Stores in PostgreSQL with state='pending_approval'
    ↓
User reviews and approves
    ↓
Frontend → API proxy → N8N Workflow 2 (resume-chat)
    ↓
Retrieves analysis from DB
    ↓
Formats and calls PyBOG API
    ↓
BOG file generated
    ↓
WebSocket notifies frontend
    ↓
User downloads BOG file
```

## Key Integration Points

### Database Schema (hvac_chat_memory)
- `session_id`: Unique session identifier
- `state`: Workflow state (pending_approval, completed, etc.)
- `data`: JSONB containing analysis results
- `result_data`: JSONB containing BOG generation results
- `human_message`: User input
- `ai_message`: AI response

### API Endpoints
- `/api/n8n/webhook/{webhook_name}`: Proxy to N8N
- `/api/generate-bog`: BOG generation endpoint
- `/api/bog-generated`: Notification endpoint
- `/api/analysis-complete`: Analysis notification

### WebSocket Events
- `analysis_complete`: Sent when Workflow 1 completes
- `bog_generated`: Sent when Workflow 2 completes

## Testing the Complete Flow

1. **Start all services**: `docker-compose up -d`
2. **Import N8N workflows**: Via N8N UI
3. **Configure credentials**: OpenAI API key in N8N
4. **Upload test document**: Via frontend
5. **Check PostgreSQL**: Verify state changes
6. **Approve analysis**: Trigger Workflow 2
7. **Download BOG**: Verify file generation

## Troubleshooting

### If workflows don't trigger:
- Check webhook URLs are accessible
- Verify N8N workflows are activated
- Check PostgreSQL credentials in N8N
- Look at N8N execution logs

### If OpenAI fails:
- Verify API key is configured in N8N
- Check file format is supported
- Ensure files aren't too large

### If BOG generation fails:
- Check PyBOG API is running
- Verify schema formatting in Workflow 2
- Check API logs for validation errors
