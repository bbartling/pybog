"""
PyBOG LangChain Agent Service

This service provides intelligent conversation handling and document analysis
using LangChain with OpenAI integration. It emits events to the EventBus
for streaming responses and maintains session context.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema.output import LLMResult

from core.events import EventBus, Event
from models.agent_models import (
    ChatMessage, MessageType, DocumentAnalysis, ChatResponse, 
    AgentError, IOPoint, ControlBlock
)

logger = logging.getLogger(__name__)


class StreamingCallbackHandler(AsyncCallbackHandler):
    """Callback handler for streaming LLM responses."""
    
    def __init__(self, event_bus: EventBus, session_id: str, operation: str):
        self.event_bus = event_bus
        self.session_id = session_id
        self.operation = operation
        self.content_buffer = ""
    
    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Handle new token from LLM streaming."""
        self.content_buffer += token
        
        # Emit streaming chat event
        await self.event_bus.publish(
            self.session_id,
            Event(
                type="chat",
                session_id=self.session_id,
                operation=self.operation,
                data={
                    "content": token,
                    "is_complete": False,
                    "buffer_content": self.content_buffer
                }
            )
        )
    
    async def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Handle LLM completion."""
        # Emit completion event
        await self.event_bus.publish(
            self.session_id,
            Event(
                type="chat",
                session_id=self.session_id,
                operation=self.operation,
                data={
                    "content": "",
                    "is_complete": True,
                    "final_content": self.content_buffer
                }
            )
        )


class PyBOGAgent:
    """
    LangChain agent for PyBOG chat and document analysis.
    
    Provides intelligent conversation handling with streaming responses
    and structured document analysis for PyBOG file generation.
    """
    
    def __init__(self, event_bus: EventBus, openai_api_key: Optional[str] = None):
        """
        Initialize the PyBOG agent.
        
        Args:
            event_bus: EventBus instance for event emission
            openai_api_key: OpenAI API key (optional, can use env var)
        """
        self.event_bus = event_bus
        
        # Initialize OpenAI LLM with streaming support
        try:
            self.llm = ChatOpenAI(
                model="gpt-4",
                temperature=0.7,
                streaming=True,
                api_key=openai_api_key
            )
        except Exception as e:
            # Fallback initialization
            self.llm = ChatOpenAI(
                model="gpt-4",
                temperature=0.7,
                streaming=True
            )
        
        # Session conversation history
        self._session_history: Dict[str, list] = {}
        
        # PyBOG system prompt
        self.system_prompt = """You are a PyBOG (Python Building Operations Guide) expert assistant. 
        You help users create optimal building automation logic by analyzing HVAC sequences, 
        control strategies, and building operations documents.

        Your expertise includes:
        - HVAC control sequences and strategies
        - Building automation systems (BAS)
        - Energy efficiency optimization
        - Fault detection and diagnostics
        - Control logic design patterns
        - Input/output point identification
        - Control block decomposition

        When analyzing documents, focus on:
        1. Identifying input and output points with proper data types
        2. Breaking down control logic into manageable blocks
        3. Creating clear pseudocode representations
        4. Assessing complexity and potential issues
        5. Providing actionable recommendations

        Always provide helpful, accurate, and practical guidance for building automation professionals."""
    
    async def process_chat_message(self, session_id: str, message: str) -> None:
        """
        Process a chat message and emit streaming response events.
        
        Args:
            session_id: Session identifier
            message: User message content
        """
        try:
            # Initialize session history if needed
            if session_id not in self._session_history:
                self._session_history[session_id] = [
                    SystemMessage(content=self.system_prompt)
                ]
            
            # Add user message to history
            self._session_history[session_id].append(
                HumanMessage(content=message)
            )
            
            # Emit progress event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="progress",
                    session_id=session_id,
                    operation="chat",
                    data={
                        "state": "processing",
                        "message": "Processing your message...",
                        "operation": "chat"
                    }
                )
            )
            
            # Create streaming callback handler
            callback_handler = StreamingCallbackHandler(
                self.event_bus, session_id, "chat"
            )
            
            # Generate streaming response
            response = await self.llm.agenerate(
                [self._session_history[session_id]],
                callbacks=[callback_handler]
            )
            
            # Add assistant response to history
            assistant_message = response.generations[0][0].text
            self._session_history[session_id].append(
                AIMessage(content=assistant_message)
            )
            
            # Emit completion progress event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="progress",
                    session_id=session_id,
                    operation="chat",
                    data={
                        "state": "complete",
                        "message": "Chat response completed",
                        "operation": "chat"
                    }
                )
            )
            
        except Exception as e:
            logger.error(f"Error processing chat message for session {session_id}: {e}")
            
            # Emit error event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="error",
                    session_id=session_id,
                    operation="chat",
                    data={
                        "error_code": "CHAT_PROCESSING",
                        "message": f"Failed to process chat message: {str(e)}",
                        "operation": "chat",
                        "session_id": session_id
                    }
                )
            )
    
    async def analyze_document_content(self, session_id: str, content: str) -> Dict[str, Any]:
        """
        Analyze document content and return structured JSON analysis.
        
        Args:
            session_id: Session identifier
            content: Document content to analyze
            
        Returns:
            Structured analysis as dictionary
        """
        try:
            # Emit progress event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="progress",
                    session_id=session_id,
                    operation="document_analysis",
                    data={
                        "state": "processing",
                        "message": "Analyzing document content...",
                        "operation": "document_analysis"
                    }
                )
            )
            
            # Create analysis prompt
            analysis_prompt = f"""Analyze the following building automation document and extract structured information for PyBOG file generation.

Document Content:
{content}

Please provide a JSON response with the following structure:
{{
    "io_points": [
        {{
            "name": "point_name",
            "type": "input" or "output",
            "data_type": "boolean", "numeric", or "string",
            "units": "optional units",
            "description": "point description"
        }}
    ],
    "control_blocks": [
        {{
            "name": "block_name",
            "type": "control_type",
            "description": "block description",
            "logic": ["logic step 1", "logic step 2"],
            "complexity": 1-10
        }}
    ],
    "pseudocode": [
        {{
            "step": 1,
            "description": "step description",
            "code": "pseudocode"
        }}
    ],
    "quality_score": 0.0-1.0,
    "issues": ["issue 1", "issue 2"],
    "metadata": {{
        "document_type": "sequence|specification|manual",
        "confidence": 0.0-1.0,
        "recommendations": ["rec 1", "rec 2"]
    }}
}}

Focus on identifying clear input/output points, logical control blocks, and actionable pseudocode."""
            
            # Generate analysis
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=analysis_prompt)
            ]
            
            response = await self.llm.agenerate([messages])
            analysis_text = response.generations[0][0].text
            
            # Parse JSON response
            try:
                # Extract JSON from response (handle potential markdown formatting)
                json_start = analysis_text.find('{')
                json_end = analysis_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_text = analysis_text[json_start:json_end]
                    analysis_data = json.loads(json_text)
                else:
                    raise ValueError("No valid JSON found in response")
                
                # Validate and structure the analysis
                structured_analysis = self._validate_analysis_data(analysis_data)
                
                # Emit completion event
                await self.event_bus.publish(
                    session_id,
                    Event(
                        type="progress",
                        session_id=session_id,
                        operation="document_analysis",
                        data={
                            "state": "complete",
                            "message": "Document analysis completed",
                            "operation": "document_analysis"
                        }
                    )
                )
                
                return structured_analysis
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse analysis JSON: {e}")
                
                # Return fallback analysis
                fallback_analysis = {
                    "io_points": [],
                    "control_blocks": [],
                    "pseudocode": [],
                    "quality_score": 0.0,
                    "issues": [f"Failed to parse structured analysis: {str(e)}"],
                    "metadata": {
                        "document_type": "unknown",
                        "confidence": 0.0,
                        "recommendations": ["Manual review required"]
                    }
                }
                
                return fallback_analysis
                
        except Exception as e:
            logger.error(f"Error analyzing document for session {session_id}: {e}")
            
            # Emit error event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="error",
                    session_id=session_id,
                    operation="document_analysis",
                    data={
                        "error_code": "DOCUMENT_ANALYSIS",
                        "message": f"Failed to analyze document: {str(e)}",
                        "operation": "document_analysis",
                        "session_id": session_id
                    }
                )
            )
            
            # Return error analysis
            return {
                "io_points": [],
                "control_blocks": [],
                "pseudocode": [],
                "quality_score": 0.0,
                "issues": [f"Analysis failed: {str(e)}"],
                "metadata": {
                    "document_type": "error",
                    "confidence": 0.0,
                    "recommendations": ["Retry analysis or contact support"]
                }
            }
    
    def _validate_analysis_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean analysis data structure.
        
        Args:
            data: Raw analysis data from LLM
            
        Returns:
            Validated and cleaned analysis data
        """
        # Ensure required fields exist with defaults
        validated = {
            "io_points": data.get("io_points", []),
            "control_blocks": data.get("control_blocks", []),
            "pseudocode": data.get("pseudocode", []),
            "quality_score": max(0.0, min(1.0, data.get("quality_score", 0.0))),
            "issues": data.get("issues", []),
            "metadata": data.get("metadata", {})
        }
        
        # Validate IO points
        valid_io_points = []
        for point in validated["io_points"]:
            if isinstance(point, dict) and all(
                key in point for key in ["name", "type", "data_type", "description"]
            ):
                if point["type"] in ["input", "output"] and point["data_type"] in ["boolean", "numeric", "string"]:
                    valid_io_points.append(point)
        
        validated["io_points"] = valid_io_points
        
        # Validate control blocks
        valid_control_blocks = []
        for block in validated["control_blocks"]:
            if isinstance(block, dict) and all(
                key in block for key in ["name", "type", "description", "logic", "complexity"]
            ):
                if isinstance(block["logic"], list) and isinstance(block["complexity"], (int, float)):
                    block["complexity"] = max(1, min(10, int(block["complexity"])))
                    valid_control_blocks.append(block)
        
        validated["control_blocks"] = valid_control_blocks
        
        # Ensure metadata has required fields
        if "metadata" not in validated or not isinstance(validated["metadata"], dict):
            validated["metadata"] = {}
        
        validated["metadata"].setdefault("document_type", "unknown")
        validated["metadata"].setdefault("confidence", 0.0)
        validated["metadata"].setdefault("recommendations", [])
        
        return validated
    
    def get_session_history(self, session_id: str) -> list:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of conversation messages
        """
        return self._session_history.get(session_id, [])
    
    def clear_session_history(self, session_id: str) -> None:
        """
        Clear conversation history for a session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._session_history:
            del self._session_history[session_id]
    
    def get_active_sessions(self) -> list:
        """Get list of active session IDs."""
        return list(self._session_history.keys())