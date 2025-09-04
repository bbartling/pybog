# N8N Workflow Configuration Issues & Fixes

## Current Status

### ✅ Active Workflows:
1. **Workflow 1 - Ingestion** (ID: 4QJwjZbYOoBA396f)
   - Webhook Path: `/webhook/ingest-doc`
   - Status: ACTIVE but BROKEN

2. **Workflow 2 - AnalysisChat** (ID: E0he1nElaKknBqib) 
   - Webhook Path: `/webhook/resume-chat`
   - Status: ACTIVE

## 🚨 Critical Issues Found

### Issue 1: Workflow 1 Expects Binary Files
**Problem**: The "Initialize Conversation" node crashes because it expects binary files but receives JSON.

**Error**: `Cannot read properties of undefined (reading 'files0')`

**Current Code (BROKEN)**:
```javascript
while(item.binary[`files${index}`]){
  const file=item.binary[`files${index}`];
  // This fails because item.binary is undefined
}
```

**Solution**: Modify the workflow to handle both binary files AND JSON payloads.

### Issue 2: Frontend Sends Wrong Format
**Problem**: Frontend sends JSON with extracted text, but N8N expects multipart/form-data with actual files.

**Frontend Sends**:
```json
{
  "sessionId": "xxx",
  "text": "message",
  "extracted_text": "content"
}
```

**N8N Expects**:
- Multipart form data with:
  - Binary file as `files0`, `files1`, etc.
  - Form fields: `sessionId`, `message`, `history`

### Issue 3: Workflow 2 Has Multiple Entry Points
**Problem**: Workflow 2 has both:
- A webhook trigger (`/webhook/resume-chat`)
- A chat trigger node
- Another webhook trigger

This creates confusion about which entry point to use.

## 🔧 Required Modifications

### Option 1: Modify N8N Workflows (Recommended)

#### Fix for Workflow 1 - Ingestion
Replace the "Initialize Conversation" node code with:

```javascript
const item = $input.first();
const data = item.json;
const files = [];
let index = 0;

// Check if binary files exist
if (item.binary) {
  while (item.binary[`files${index}`]) {
    const file = item.binary[`files${index}`];
    files.push({
      filename: file.fileName,
      mimeType: file.mimeType,
      binaryKey: `files${index}`
    });
    index++;
  }
}

// Also check for extracted_text in JSON (fallback)
const extractedText = data.extracted_text || data.extractedText || '';

return {
  json: {
    sessionId: data.sessionId || data.session_id || Date.now().toString(),
    userMessage: data.message || data.text || '',
    conversationHistory: data.history || data.conversationHistory || [],
    files: files,
    extracted_text: extractedText,
    hasBinaryFiles: files.length > 0,
    hasExtractedText: extractedText.length > 0
  }
};
```

#### Fix for "Has Files?" Node
Change the condition from:
```
$json.files.length > 0
```

To:
```
$json.hasBinaryFiles === true
```

#### Add Alternative Path
Add a new branch that handles pre-extracted text when no binary files are present:
1. Add an IF node checking `hasExtractedText`
2. If true, skip OpenAI extraction and use provided text
3. If false, return error

### Option 2: Create Adapter Workflow

Create a new "adapter" workflow that:
1. Receives requests from the frontend
2. Determines if files need extraction
3. Routes to appropriate workflow
4. Returns unified response

### Option 3: Use API as Intermediary (Current Approach)

We've already implemented this partially:
1. API receives files from frontend
2. API extracts text locally
3. API sends proper format to N8N

## 📝 Implementation Steps

### Step 1: Update N8N Workflow 1
1. Open N8N UI: http://localhost:5678
2. Edit "Workflow 1 - Ingestion"
3. Modify "Initialize Conversation" node with the fixed code above
4. Save and activate

### Step 2: Test with Different Inputs
Test the workflow with:
1. Binary file upload
2. JSON with extracted_text
3. Mixed format (both file and text)

### Step 3: Update Frontend Integration
Ensure frontend uses the corrected endpoints:
- For file upload: Send actual files as multipart/form-data
- For text analysis: Send JSON with extracted_text
- For approval: Send to `/webhook/resume-chat`

## 🎯 Quick Test Commands

### Test Workflow 1 with JSON (after fix):
```powershell
$body = @{
    sessionId = "test_123"
    message = "Test message"
    extracted_text = "Sample HVAC document content with temperature sensors and dampers"
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:5678/webhook/ingest-doc -Method POST -Body $body -ContentType "application/json"
```

### Test Workflow 2:
```powershell
$body = @{
    sessionId = "test_123"
    approved = $true
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:5678/webhook/resume-chat -Method POST -Body $body -ContentType "application/json"
```

## 📊 Workflow Architecture After Fixes

```
Frontend Upload
    ↓
API receives file
    ↓
API extracts text (PyPDF2/python-docx)
    ↓
API sends to N8N with BOTH:
  - Original file (if needed for OpenAI)
  - Pre-extracted text (as fallback)
    ↓
N8N Workflow 1 handles both formats
    ↓
If has files: Send to OpenAI
If has text: Use provided text
    ↓
Store in PostgreSQL
    ↓
Return to frontend for approval
    ↓
User approves
    ↓
Workflow 2 generates BOG
```

## ⚠️ Important Notes

1. **OpenAI Credentials**: Ensure OpenAI API credentials are configured in N8N
2. **PostgreSQL Credentials**: Both workflows need database access
3. **Webhook Security**: Consider adding authentication to webhooks in production
4. **Error Handling**: Add proper error handling nodes in workflows
5. **Logging**: Enable N8N execution logging for debugging

## Next Steps

1. **Immediate**: Fix the "Initialize Conversation" node in Workflow 1
2. **Short-term**: Add better error handling and logging
3. **Long-term**: Consider consolidating into a single, more robust workflow
