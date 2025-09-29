# PyBOG LangChain Agent Implementation

## Overview

The PyBOG Agent is a LangChain-based service that provides intelligent conversation handling and document analysis for building automation systems. It integrates with the EventBus system to provide streaming responses and maintains session context for continuous conversations.

## Features

### Core Capabilities
- **Streaming Chat Responses**: Real-time streaming of LLM responses through EventBus
- **Document Analysis**: Structured analysis of HVAC/building automation documents
- **Session Management**: Maintains conversation history per session
- **Event-Driven Architecture**: Emits events for all operations (chat, analysis, errors)
- **Error Handling**: Comprehensive error handling with standardized error codes

### LangChain Integration
- Uses OpenAI GPT-4 for intelligent responses
- Streaming callback handlers for real-time token emission
- Conversation memory management
- Specialized prompts for building automation expertise

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PyBOGAgent                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Chat Handler  │  │ Document Analyzer│  │ Session Manager │ │
│  │                 │  │                 │  │                 │ │
│  │ - Streaming     │  │ - JSON Analysis │  │ - History       │ │
│  │ - Context       │  │ - Validation    │  │ - Isolation     │ │
│  │ - Memory        │  │ - Structured    │  │ - Cleanup       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                  │
                              EventBus
                                  │
┌─────────────────────────────────────────────────────────────────┐
│                    Event Types                                  │
│  • chat: Streaming tokens and completion                        │
│  • progress: Operation state updates                            │
│  • error: Error events with codes                              │
└─────────────────────────────────────────────────────────────────┘
```

## Usage

### Basic Chat Interaction

```python
from core.events import EventBus
from services.pybog_agent import PyBOGAgent

# Initialize
event_bus = EventBus()
agent = PyBOGAgent(event_bus, openai_api_key="your_key")

# Subscribe to events
async def handle_events(event):
    if event.type == "chat":
        if event.data["is_complete"]:
            print(f"Complete: {event.data['final_content']}")
        else:
            print(f"Token: {event.data['content']}")

await event_bus.subscribe("session_id", handle_events)

# Process chat message
await agent.process_chat_message("session_id", "Explain VAV control sequences")
```

### Document Analysis

```python
# Analyze HVAC document
document_content = """
VAV Box Control Sequence:
1. Monitor zone temperature
2. Modulate damper position based on demand
3. Enable reheat when needed
"""

analysis = await agent.analyze_document_content("session_id", document_content)

print(f"Quality Score: {analysis['quality_score']}")
print(f"IO Points: {len(analysis['io_points'])}")
print(f"Control Blocks: {len(analysis['control_blocks'])}")
```

## Event Types

### Chat Events
```json
{
  "type": "chat",
  "session_id": "session_123",
  "operation": "chat",
  "data": {
    "content": "Hello",
    "is_complete": false,
    "buffer_content": "Hello world"
  }
}
```

### Progress Events
```json
{
  "type": "progress",
  "session_id": "session_123",
  "operation": "document_analysis",
  "data": {
    "state": "processing",
    "message": "Analyzing document content...",
    "operation": "document_analysis"
  }
}
```

### Error Events
```json
{
  "type": "error",
  "session_id": "session_123",
  "operation": "chat",
  "data": {
    "error_code": "CHAT_PROCESSING",
    "message": "Failed to process message",
    "session_id": "session_123"
  }
}
```

## Document Analysis Output

The agent returns structured analysis in this format:

```json
{
  "io_points": [
    {
      "name": "zone_temperature",
      "type": "input",
      "data_type": "numeric",
      "units": "°F",
      "description": "Zone temperature sensor"
    }
  ],
  "control_blocks": [
    {
      "name": "damper_control",
      "type": "PID",
      "description": "VAV damper position control",
      "logic": ["Read zone temp", "Calculate demand", "Modulate damper"],
      "complexity": 5
    }
  ],
  "pseudocode": [
    {
      "step": 1,
      "description": "Read temperature sensor",
      "code": "temp = read_sensor('zone_temp')"
    }
  ],
  "quality_score": 0.85,
  "issues": [],
  "metadata": {
    "document_type": "sequence",
    "confidence": 0.9,
    "recommendations": ["Add fault detection"]
  }
}
```

## Error Codes

- **AGENT_INIT**: Agent initialization failures
- **CHAT_PROCESSING**: Chat message processing errors
- **DOCUMENT_ANALYSIS**: Document analysis failures
- **LLM_ERROR**: LangChain/OpenAI API errors

## Session Management

- **Conversation History**: Maintains LangChain message history per session
- **Session Isolation**: Each session has independent context
- **Memory Management**: Automatic cleanup of inactive sessions
- **Context Preservation**: System prompts and conversation flow maintained

## Testing

The implementation includes comprehensive tests:

- **Unit Tests**: `tests/test_pybog_agent.py`
- **Integration Tests**: `tests/test_pybog_agent_integration.py`
- **EventBus Integration**: Verifies proper event emission
- **Streaming Tests**: Validates real-time token streaming
- **Error Handling**: Tests all error scenarios

Run tests:
```bash
python -m pytest tests/test_pybog_agent.py -v
python -m pytest tests/test_pybog_agent_integration.py -v
```

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for LangChain OpenAI integration

### Agent Configuration
```python
agent = PyBOGAgent(
    event_bus=event_bus,
    openai_api_key="your_key"  # Optional, can use env var
)
```

### LLM Settings
- Model: GPT-4
- Temperature: 0.7
- Streaming: Enabled
- Max Tokens: Default (varies by model)

## Integration with FastAPI

See `examples/fastapi_agent_integration.py` for complete FastAPI integration example with WebSocket support.

## Performance Considerations

- **Streaming**: Reduces perceived latency for long responses
- **Session Isolation**: Prevents memory leaks between sessions
- **Event Buffering**: EventBus provides replay functionality
- **Error Recovery**: Graceful handling of LLM failures

## Future Enhancements

- **Custom Models**: Support for other LLM providers
- **Advanced Prompting**: Dynamic prompt engineering
- **Caching**: Response caching for common queries
- **Metrics**: Performance and usage tracking