# PyBOG Conversational Flow Improvements

## What We Fixed

### 1. Clear Conversation Threading
- **Before**: Messages were scattered across three vertical lanes (system/tool/user) making it hard to follow the conversation
- **After**: Messages now alternate left (user) and right (assistant/system) in a clear conversational pattern

### 2. Process Step Visualization  
- **New Feature**: N8n workflow steps now appear as small process nodes in the middle
- Shows real-time progress: Split Files → Extract Text → Aggregate → Analysis
- Each step shows status (running/ok/error) with metrics

### 3. WebSocket Integration
- **Fixed**: Now properly consumes `process_step` events from n8n HTTP hooks
- Updates process nodes in real-time as workflow executes
- Shows live status updates in the flow

### 4. Visual Conversation Phases
- **New Swimlanes**: Horizontal phases instead of vertical lanes
  - USER INPUT: Where user messages appear
  - PROCESSING: Shows workflow steps  
  - ANALYSIS: AI analysis and extraction
  - REVIEW: Approval/feedback stage
  - OUTPUT: Final BOG generation

### 5. Improved Layout Algorithm
- Left-aligned: User messages
- Center: Process/status nodes
- Right-aligned: Assistant/analysis messages
- Clear flow lines connecting conversation pairs
- Automatic viewport focusing on recent messages

## Visual Improvements

### Message Nodes
- **User**: Purple border, left side, gradient background
- **Assistant**: Blue border, right side  
- **Analysis**: Green border with expandable details
- **Process**: Dark mini-nodes with status indicators
- **Artifacts**: Orange border for BOG outputs

### Connection Lines
- Conversation pairs: Strong purple lines
- Process flows: Animated dashed lines when running
- Clear directional arrows showing flow

## How to Test

1. **Start a conversation**: Type a message or upload a file
2. **Watch the flow**: 
   - User message appears on left
   - Process nodes appear in center showing workflow steps
   - Assistant response appears on right
3. **Upload a document**:
   - See extraction steps animate in real-time
   - Analysis appears with inputs/outputs clearly shown
4. **Review and approve**:
   - Clear approval interface
   - BOG generation shown as final step

## Technical Details

### New Components
- `ProcessNode.tsx`: Displays n8n workflow steps
- `ConversationSwimlanes.tsx`: Phase-based layout system

### Updated Components  
- `ChatCanvas.tsx`: Complete layout refactor for conversation flow
- `App.tsx`: WebSocket handler for process_step events

### Key Changes
- Removed confusing lane-based layout
- Added alternating left/right conversation pattern
- Integrated real-time workflow visualization
- Fixed message threading and connections
- Added phase-based swimlanes for clarity

## Result
The interface now clearly shows a conversational dialog with:
- Clear request → processing → response flow
- Live workflow step visualization
- Intuitive left-right conversation pattern
- Visual phases showing where you are in the process
- Better connection lines showing relationships

This makes it much easier to:
- Follow the conversation
- Understand what's being processed
- See the relationship between messages
- Track workflow progress in real-time
