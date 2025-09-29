"""
PyBOG Agent V2 - Enhanced AI Agent with OpenAI Integration and HVAC Domain Knowledge

This service provides intelligent conversation handling, document analysis, and HVAC expertise
using OpenAI's API with streaming responses and comprehensive domain knowledge.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, AsyncGenerator, List
from uuid import uuid4

from pydantic import BaseModel, Field
import openai

from core.events import EventBus, Event
from core.database import get_database
from models.agent_models import DocumentAnalysis, IOPoint, ControlBlock

# Configure logging
logger = logging.getLogger(__name__)


class AgentStreamResponse(BaseModel):
    """Streaming response from agent."""
    session_id: str
    message_type: str  # 'chunk', 'complete', 'error', 'status', 'analysis_complete', 'bog_created', 'chat_response'
    content: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BOGCreationRequest(BaseModel):
    """Request for BOG creation."""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class DocumentContext(BaseModel):
    """Context for document analysis."""
    file_path: str
    file_type: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnalysisContext(BaseModel):
    """Context for analysis operations."""
    session_id: str
    operation: str
    documents: List[DocumentContext] = Field(default_factory=list)
    previous_analysis: Optional[str] = None
    iteration_count: int = 0
    max_iterations: int = 3


class PyBOGAgentV2:
    """
    Enhanced PyBOG Agent V2 with comprehensive HVAC domain knowledge and streaming capabilities.
    
    Features:
    - OpenAI integration with streaming responses
    - HVAC domain expertise and guidance
    - Structured document analysis for control sequences
    - Real-time WebSocket communication
    - Expert guidance prompts and recommendations
    """
    
    def __init__(self, event_bus: EventBus, openai_api_key: Optional[str] = None):
        """
        Initialize the PyBOG agent with OpenAI client and HVAC expertise.
        
        Args:
            event_bus: Event bus for publishing events
            openai_api_key: OpenAI API key (optional, can use env var)
        """
        self.event_bus = event_bus
        self.openai_api_key = openai_api_key
        
        # Initialize OpenAI client
        import os
        if openai_api_key:
            os.environ['OPENAI_API_KEY'] = openai_api_key
        
        # Check if API key is available
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("No OpenAI API key provided - agent will use mock responses")
            self.client = None
        else:
            self.client = openai.AsyncOpenAI(api_key=api_key)
        
        # Session conversation history
        self._session_history: Dict[str, List[Dict[str, str]]] = {}
        
        # HVAC domain knowledge and system prompts
        self.hvac_system_prompt = self._get_hvac_system_prompt()
        self.analysis_system_prompt = self._get_analysis_system_prompt()
        
        logger.info("PyBOG Agent V2 initialized with HVAC domain knowledge")
    
    def _get_hvac_system_prompt(self) -> str:
        """Get the comprehensive HVAC system prompt for chat interactions."""
        return """You are a PyBOG (Python Building Operations Guide) expert assistant specializing in HVAC control systems and building automation. You have deep expertise in:

**HVAC Systems & Equipment:**
- Air Handling Units (AHUs), Variable Air Volume (VAV) systems, Fan Coil Units (FCUs)
- Chillers, Boilers, Heat Pumps, Cooling Towers, and Heat Recovery systems
- Economizers, Dampers, Valves, Sensors, and Actuators
- Energy Recovery Ventilators (ERVs) and Heat Recovery Ventilators (HRVs)

**Control Strategies & Sequences:**
- Optimal Start/Stop, Night Setback, and Demand Control Ventilation
- Economizer control with enthalpy and temperature-based strategies
- Static Pressure Reset, Supply Air Temperature Reset, and Chilled Water Reset
- Staging control for multiple units and equipment optimization
- Fault Detection and Diagnostics (FDD) strategies

**Building Automation Systems:**
- BACnet, Modbus, LonWorks, and other communication protocols
- Point naming conventions and data types (AI, AO, BI, BO, AV, BV)
- Control logic programming and sequence development
- Energy management and optimization strategies

**Your Role:**
- Provide expert guidance on HVAC control sequence design and optimization
- Help analyze existing control documents and identify improvement opportunities
- Walk users through conversational Q&A for sequence development
- Offer professional recommendations based on industry best practices
- Assist with PyBOG file generation for building automation systems

**Communication Style:**
- Professional and knowledgeable, suitable for HVAC engineers and technicians
- Provide clear explanations with practical examples
- Ask clarifying questions to understand specific requirements
- Offer step-by-step guidance for complex control sequences
- Reference industry standards (ASHRAE, NIST) when appropriate

Always focus on practical, implementable solutions that improve energy efficiency, occupant comfort, and system reliability."""

    def _get_analysis_system_prompt(self) -> str:
        """Get the system prompt for document analysis operations."""
        return """You are an expert HVAC document analyzer specializing in extracting structured control information from building automation documents. Your task is to analyze HVAC control sequences, specifications, and operational documents to extract:

**Input/Output Points:**
- Identify all sensors, actuators, and control points
- Classify as input (sensors, feedback) or output (commands, setpoints)
- Determine data types (boolean, numeric, string) and units
- Provide clear, descriptive names following BACnet conventions

**Control Blocks:**
- Break down complex control sequences into logical blocks
- Identify control types (PID, Logic, Schedule, Alarm, etc.)
- Extract control logic and operational steps
- Assess complexity and interdependencies

**Pseudocode Generation:**
- Create step-by-step pseudocode for control sequences
- Use clear, implementable logic statements
- Include conditional logic, calculations, and state transitions
- Ensure code is suitable for PyBOG file generation

**Quality Assessment:**
- Evaluate completeness and clarity of control sequences
- Identify missing information or potential issues
- Provide recommendations for improvement
- Assess implementation complexity and feasibility

Focus on extracting actionable, structured information that can be directly used for building automation system programming and PyBOG file generation."""

    async def _save_message_to_db(self, session_id: str, message_type: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Save a message to the database."""
        try:
            db = await get_database()
            await db.execute_query(
                """
                INSERT INTO chat_messages (session_id, message_type, content, metadata)
                VALUES ($1, $2, $3, $4)
                """,
                session_id, message_type, content, json.dumps(metadata or {})
            )
            logger.info(f"Message saved to database: {message_type} for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to save message to database: {e}")

    async def process_chat_message(self, session_id: str, message: str) -> None:
        """
        Process a chat message with streaming response through WebSocket events.

        Args:
            session_id: Session identifier
            message: User message content
        """
        try:
            # Save user message to database
            await self._save_message_to_db(session_id, "user", message)

            # Initialize session history if needed
            if session_id not in self._session_history:
                self._session_history[session_id] = [
                    {"role": "system", "content": self.hvac_system_prompt}
                ]

            # Get file context for this session
            file_context = await self._get_session_file_context(session_id)

            # Enhance message with file context if available
            enhanced_message = message
            if file_context:
                enhanced_message = f"{message}\n\nAvailable files in this session:\n{file_context}"

            # Add enhanced message to history
            self._session_history[session_id].append(
                {"role": "user", "content": enhanced_message}
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
            
            # Check if user is requesting file analysis
            if self._is_file_analysis_request(message) and file_context:
                await self._handle_file_analysis_request(session_id, message)
            else:
                # Generate streaming response
                if self.client:
                    await self._stream_openai_response(session_id, self._session_history[session_id])
                else:
                    await self._stream_mock_response(session_id, message)
            
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
    
    async def _stream_openai_response(self, session_id: str, messages: List[Dict[str, str]]) -> None:
        """Stream OpenAI response through WebSocket events."""
        try:
            logger.info(f"Starting OpenAI streaming for session {session_id}")
            response_content = ""
            chunk_count = 0

            # Get available tools for this session
            tools = await self._get_available_tools(session_id)

            # Create streaming completion with tools if available
            logger.info(f"Creating OpenAI streaming completion for session {session_id} with {len(tools)} tools")
            stream_params = {
                "model": "gpt-4o-mini",
                "messages": messages,
                "temperature": 0.7,
                "stream": True,
                "max_tokens": 2000
            }

            if tools:
                stream_params["tools"] = tools
                stream_params["tool_choice"] = "auto"

            stream = await self.client.chat.completions.create(**stream_params)
            logger.info(f"OpenAI stream created, starting to process chunks for session {session_id}")

            # Stream response chunks
            async for chunk in stream:
                try:
                    chunk_count += 1
                    logger.debug(f"Processing chunk {chunk_count} for session {session_id}")

                    if chunk.choices[0].delta.content is not None:
                        content_chunk = chunk.choices[0].delta.content
                        response_content += content_chunk

                        # Emit streaming chunk event
                        logger.info(f"Publishing streaming chunk {chunk_count} for session {session_id}: {len(content_chunk)} chars")
                        await self.event_bus.publish(
                            session_id,
                            Event(
                                type="chat",
                                session_id=session_id,
                                operation="chat",
                                data={
                                    "content": content_chunk,
                                    "is_complete": False,
                                    "buffer_content": response_content
                                }
                            )
                        )
                        logger.debug(f"Successfully published chunk {chunk_count} for session {session_id}")
                    else:
                        logger.debug(f"Chunk {chunk_count} has no content for session {session_id}")

                        # Check for tool calls
                        if chunk.choices[0].delta.tool_calls:
                            for tool_call in chunk.choices[0].delta.tool_calls:
                                if tool_call.function:
                                    logger.info(f"Tool call requested: {tool_call.function.name}")
                                    # Handle tool call asynchronously
                                    asyncio.create_task(self._handle_tool_call(session_id, tool_call))

                except Exception as chunk_error:
                    logger.error(f"Error processing streaming chunk {chunk_count} for session {session_id}: {chunk_error}")
                    continue

            logger.info(f"Completed streaming {chunk_count} chunks for session {session_id}, total content: {len(response_content)} chars")
            
            # Add assistant response to history
            self._session_history[session_id].append(
                {"role": "assistant", "content": response_content}
            )
            
            # Save assistant response to database
            await self._save_message_to_db(session_id, "assistant", response_content, {
                "model": "gpt-4o-mini",
                "tokens": len(response_content.split()),
                "streaming": True
            })
            
            # Emit completion event
            logger.info(f"Publishing completion event for session {session_id}")
            await self.event_bus.publish(
                session_id,
                Event(
                    type="chat",
                    session_id=session_id,
                    operation="chat",
                    data={
                        "content": "",
                        "is_complete": True,
                        "final_content": response_content
                    }
                )
            )
            
        except Exception as e:
            logger.error(f"Error streaming OpenAI response: {e}")
            raise
    
    async def _stream_mock_response(self, session_id: str, user_message: str) -> None:
        """Stream mock response for testing without OpenAI API key."""
        mock_response = f"""Hello! I'm the PyBOG HVAC expert assistant. I received your message: "{user_message[:50]}..."

I'm here to help you with:
• HVAC control sequence analysis and design
• Building automation system programming
• Energy optimization strategies
• Fault detection and diagnostics
• PyBOG file generation

What specific HVAC control challenge can I help you with today? Please share details about your system, equipment, or control requirements."""
        
        # Simulate streaming by sending chunks
        words = mock_response.split()
        current_content = ""
        
        for i, word in enumerate(words):
            current_content += word + " "
            
            # Emit chunk every few words
            if i % 3 == 0 or i == len(words) - 1:
                await self.event_bus.publish(
                    session_id,
                    Event(
                        type="chat",
                        session_id=session_id,
                        operation="chat",
                        data={
                            "content": word + " ",
                            "is_complete": False,
                            "buffer_content": current_content
                        }
                    )
                )
                
                # Small delay to simulate streaming
                await asyncio.sleep(0.1)
        
        # Add to session history
        self._session_history[session_id].append(
            {"role": "assistant", "content": mock_response}
        )
        
        # Save assistant response to database
        await self._save_message_to_db(session_id, "assistant", mock_response, {
            "model": "mock",
            "tokens": len(mock_response.split()),
            "streaming": True
        })
        
        # Emit completion event
        await self.event_bus.publish(
            session_id,
            Event(
                type="chat",
                session_id=session_id,
                operation="chat",
                data={
                    "content": "",
                    "is_complete": True,
                    "final_content": mock_response
                }
            )
        )
    
    async def analyze_document_content(self, session_id: str, content: str, analysis_type: str = "hvac_analysis") -> Dict[str, Any]:
        """
        Analyze document content and return structured HVAC analysis.
        
        Args:
            session_id: Session identifier
            content: Document content to analyze
            analysis_type: Type of analysis to perform
            
        Returns:
            Dictionary with structured analysis results
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
                        "message": "Analyzing HVAC document content...",
                        "operation": "document_analysis"
                    }
                )
            )
            
            if self.client:
                analysis_result = await self._analyze_with_openai(content, analysis_type)
            else:
                analysis_result = await self._analyze_with_mock(content, analysis_type)
            
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
            
            return analysis_result
                
        except Exception as e:
            logger.error(f"Error analyzing document content: {e}")
            
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
    
    async def _analyze_with_openai(self, content: str, analysis_type: str) -> Dict[str, Any]:
        """Perform analysis using OpenAI API."""
        analysis_prompt = f"""Analyze this HVAC document and extract structured information for PyBOG file generation.

Document Content:
{content}

Please provide a JSON response with the following structure:
{{
    "io_points": [
        {{
            "name": "point_name",
            "type": "input" or "output",
            "data_type": "boolean", "numeric", or "string",
            "units": "optional units (°F, CFM, %RH, etc.)",
            "description": "clear description of the point"
        }}
    ],
    "control_blocks": [
        {{
            "name": "block_name",
            "type": "PID|Logic|Schedule|Alarm|Economizer|Reset|Staging",
            "description": "detailed block description",
            "logic": ["step 1", "step 2", "step 3"],
            "complexity": 1-10
        }}
    ],
    "pseudocode": [
        {{
            "step": 1,
            "description": "step description",
            "code": "IF condition THEN action ELSE alternative"
        }}
    ],
    "quality_score": 0.0-1.0,
    "issues": ["missing information", "unclear sequences"],
    "metadata": {{
        "document_type": "sequence|specification|manual|drawing",
        "confidence": 0.0-1.0,
        "recommendations": ["specific improvement suggestions"]
    }}
}}

Focus on HVAC-specific elements:
- Temperature, pressure, flow, and humidity sensors
- Damper, valve, and fan control outputs
- Control sequences for economizers, staging, and resets
- Energy efficiency and comfort optimization logic"""
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.analysis_system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            analysis_text = response.choices[0].message.content
            
            # Parse JSON response
            json_start = analysis_text.find('{')
            json_end = analysis_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = analysis_text[json_start:json_end]
                analysis_data = json.loads(json_text)
                return self._validate_analysis_data(analysis_data)
            else:
                raise ValueError("No valid JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse analysis JSON: {e}")
            return self._get_fallback_analysis(content)
    
    async def _analyze_with_mock(self, content: str, analysis_type: str) -> Dict[str, Any]:
        """Perform mock analysis for testing."""
        # Simulate processing delay
        await asyncio.sleep(1)
        
        # Generate mock analysis based on content
        content_length = len(content)
        word_count = len(content.split())
        
        # Mock IO points based on common HVAC terms
        io_points = []
        if "temperature" in content.lower():
            io_points.extend([
                {
                    "name": "SAT_Sensor",
                    "type": "input",
                    "data_type": "numeric",
                    "units": "°F",
                    "description": "Supply Air Temperature Sensor"
                },
                {
                    "name": "SAT_Setpoint",
                    "type": "output",
                    "data_type": "numeric",
                    "units": "°F",
                    "description": "Supply Air Temperature Setpoint"
                }
            ])
        
        if "damper" in content.lower() or "economizer" in content.lower():
            io_points.append({
                "name": "OA_Damper_Cmd",
                "type": "output",
                "data_type": "numeric",
                "units": "%",
                "description": "Outside Air Damper Command"
            })
        
        # Mock control blocks
        control_blocks = [
            {
                "name": "Temperature_Control",
                "type": "PID",
                "description": "Supply air temperature control loop",
                "logic": [
                    "Read supply air temperature sensor",
                    "Compare to setpoint",
                    "Calculate PID output",
                    "Send command to heating/cooling valve"
                ],
                "complexity": 5
            }
        ]
        
        # Mock pseudocode
        pseudocode = [
            {
                "step": 1,
                "description": "Initialize control loop",
                "code": "SET SAT_Setpoint = 55°F"
            },
            {
                "step": 2,
                "description": "Read sensor values",
                "code": "READ SAT_Sensor"
            },
            {
                "step": 3,
                "description": "Control logic",
                "code": "IF SAT_Sensor > SAT_Setpoint THEN Increase_Cooling ELSE Decrease_Cooling"
            }
        ]
        
        return {
            "io_points": io_points,
            "control_blocks": control_blocks,
            "pseudocode": pseudocode,
            "quality_score": 0.75,
            "issues": ["Mock analysis - limited detail available"],
            "metadata": {
                "document_type": "sequence",
                "confidence": 0.8,
                "recommendations": [
                    f"Document analyzed: {word_count} words, {content_length} characters",
                    "Consider adding more specific control parameters",
                    "Verify sensor and actuator specifications"
                ]
            }
        }
    
    def _validate_analysis_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean analysis data structure."""
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
    
    def _get_fallback_analysis(self, content: str) -> Dict[str, Any]:
        """Get fallback analysis when parsing fails."""
        return {
            "io_points": [],
            "control_blocks": [],
            "pseudocode": [],
            "quality_score": 0.0,
            "issues": ["Failed to parse structured analysis from AI response"],
            "metadata": {
                "document_type": "unknown",
                "confidence": 0.0,
                "recommendations": ["Manual review required", "Consider simplifying document content"]
            }
        }
    
    async def provide_hvac_guidance(self, session_id: str, context: Dict[str, Any]) -> str:
        """
        Provide expert HVAC guidance based on context.
        
        Args:
            session_id: Session identifier
            context: Context information for guidance
            
        Returns:
            Expert guidance text
        """
        try:
            guidance_prompt = f"""Provide expert HVAC guidance based on this context:

Context: {json.dumps(context, indent=2)}

Please provide specific, actionable guidance that addresses:
1. Best practices for the described system/situation
2. Potential issues or considerations
3. Optimization opportunities
4. Implementation recommendations

Focus on practical, professional advice suitable for HVAC engineers and technicians."""
            
            if self.client:
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": self.hvac_system_prompt},
                        {"role": "user", "content": guidance_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1500
                )
                return response.choices[0].message.content
            else:
                return f"""Based on the provided context, here are some general HVAC guidance recommendations:

• Ensure proper sensor calibration and maintenance schedules
• Implement energy-efficient control sequences with appropriate deadbands
• Consider occupancy-based control strategies for optimal comfort and efficiency
• Verify proper equipment staging and sequencing to avoid short cycling
• Implement fault detection and diagnostic capabilities for proactive maintenance

For more specific guidance, please provide additional details about your system configuration, operational requirements, and any specific challenges you're facing."""
                
        except Exception as e:
            logger.error(f"Error providing HVAC guidance: {e}")
            return f"I apologize, but I encountered an error while generating guidance: {str(e)}. Please try again or contact support if the issue persists."
    
    def get_session_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get conversation history for a session."""
        return self._session_history.get(session_id, [])
    
    def clear_session_history(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        if session_id in self._session_history:
            del self._session_history[session_id]
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs."""
        return list(self._session_history.keys())
    
    async def start_chat_pipeline(self, session_id: str, text: str) -> None:
        """
        Start the complete chat pipeline: chat → clarifiers → analysis → BOG → downloads
        
        Args:
            session_id: Session identifier
            text: User message text
        """
        try:
            logger.info(f"Starting chat pipeline for session {session_id}")
            
            # Step 1: Process initial chat message
            await self.process_chat_message(session_id, text)
            
            # Step 2: Determine if clarifiers are needed or proceed directly to analysis
            needs_clarification = await self._needs_clarification(text)
            
            if needs_clarification:
                # Emit clarification request
                await self.event_bus.publish(
                    session_id,
                    Event(
                        type="message",
                        session_id=session_id,
                        operation="clarification",
                        data={
                            "type": "clarification_needed",
                            "message": "I need some additional information to provide the best analysis.",
                            "questions": await self._generate_clarification_questions(text)
                        }
                    )
                )
            else:
                # Proceed directly to analysis
                await self._start_analysis_from_text(session_id, text)
                
        except Exception as e:
            logger.error(f"Error starting chat pipeline: {e}")
            await self.event_bus.publish(
                session_id,
                Event(
                    type="error",
                    session_id=session_id,
                    operation="chat_pipeline",
                    data={
                        "error": str(e),
                        "retryable": True,
                        "step": "chat_pipeline_start"
                    }
                )
            )
    
    async def start_analysis_pipeline(self, session_id: str, text: Optional[str] = None, source_ids: List[str] = None) -> str:
        """
        Start analysis pipeline with WebSocket progress updates
        
        Args:
            session_id: Session identifier
            text: Text content to analyze
            source_ids: List of source file IDs
            
        Returns:
            Analysis ID
        """
        analysis_id = str(uuid4())
        
        try:
            logger.info(f"Starting analysis pipeline {analysis_id} for session {session_id}")
            
            # Emit analysis started event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="message",
                    session_id=session_id,
                    operation="analysis",
                    data={
                        "type": "analysis.started",
                        "analysisId": analysis_id,
                        "sessionId": session_id
                    }
                )
            )
            
            # Start analysis process
            asyncio.create_task(self._run_analysis_pipeline(session_id, analysis_id, text, source_ids or []))
            
            return analysis_id
            
        except Exception as e:
            logger.error(f"Error starting analysis pipeline: {e}")
            await self.event_bus.publish(
                session_id,
                Event(
                    type="message",
                    session_id=session_id,
                    operation="analysis",
                    data={
                        "type": "analysis.failed",
                        "analysisId": analysis_id,
                        "error": str(e),
                        "retryable": True
                    }
                )
            )
            raise
    
    async def start_bog_generation(self, session_id: str, analysis_id: str) -> str:
        """
        Start BOG generation pipeline with WebSocket progress updates
        
        Args:
            session_id: Session identifier
            analysis_id: Analysis ID to generate BOG from
            
        Returns:
            Artifact ID
        """
        artifact_id = str(uuid4())
        
        try:
            logger.info(f"Starting BOG generation {artifact_id} for analysis {analysis_id}")
            
            # Emit BOG started event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="message",
                    session_id=session_id,
                    operation="bog_generation",
                    data={
                        "type": "bog.started",
                        "bogId": artifact_id,
                        "analysisId": analysis_id
                    }
                )
            )
            
            # Start BOG generation process
            asyncio.create_task(self._run_bog_generation(session_id, analysis_id, artifact_id))
            
            return artifact_id
            
        except Exception as e:
            logger.error(f"Error starting BOG generation: {e}")
            await self.event_bus.publish(
                session_id,
                Event(
                    type="message",
                    session_id=session_id,
                    operation="bog_generation",
                    data={
                        "type": "bog.failed",
                        "bogId": artifact_id,
                        "error": str(e),
                        "retryable": True
                    }
                )
            )
            raise
    
    async def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get current session state for resume functionality
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session state dictionary
        """
        try:
            # Get session data from database
            db = await get_database()
            session_data = await db.fetch_one(
                "SELECT * FROM sessions WHERE session_id = $1",
                session_id
            )
            
            if not session_data:
                return {
                    "status": "idle",
                    "last_step": "idle",
                    "artifacts": [],
                    "current_analysis": None,
                    "pipeline_state": {}
                }
            
            # Get artifacts for this session
            artifacts = await db.fetch_all(
                "SELECT * FROM artifacts WHERE session_id = $1 ORDER BY created_at DESC",
                session_id
            )
            
            return {
                "status": session_data.get("status", "idle"),
                "last_step": session_data.get("last_step", "idle"),
                "artifacts": [
                    {
                        "artifactId": artifact["id"],
                        "type": artifact["type"],
                        "filename": artifact["filename"],
                        "downloadUrl": f"/api/files/{artifact['id']}/download"
                    }
                    for artifact in artifacts
                ],
                "current_analysis": session_data.get("current_analysis"),
                "pipeline_state": session_data.get("pipeline_state", {})
            }
            
        except Exception as e:
            logger.error(f"Error getting session state: {e}")
            return {
                "status": "error",
                "last_step": "error",
                "artifacts": [],
                "current_analysis": None,
                "pipeline_state": {"error": str(e)}
            }
    
    async def _needs_clarification(self, text: str) -> bool:
        """Determine if the user input needs clarification."""
        # Simple heuristics - in production this could use AI
        text_lower = text.lower()
        
        # Check if text is too short or vague
        if len(text.split()) < 5:
            return True
        
        # Check if it contains specific HVAC terms
        hvac_terms = [
            'ahu', 'vav', 'fcu', 'economizer', 'damper', 'valve', 'sensor',
            'temperature', 'pressure', 'flow', 'humidity', 'setpoint',
            'control', 'sequence', 'schedule', 'alarm'
        ]
        
        has_hvac_terms = any(term in text_lower for term in hvac_terms)
        
        # If no HVAC terms and short, needs clarification
        return not has_hvac_terms and len(text.split()) < 10
    
    async def _generate_clarification_questions(self, text: str) -> List[str]:
        """Generate clarification questions based on user input."""
        return [
            "What type of HVAC equipment are you working with? (AHU, VAV, FCU, etc.)",
            "What are the main operating modes or sequences you need?",
            "Are there specific temperature, pressure, or flow requirements?",
            "Do you need economizer control or energy recovery features?",
            "What are the key alarms or safety interlocks required?"
        ]
    
    async def _start_analysis_from_text(self, session_id: str, text: str) -> None:
        """Start analysis from text input and check for uploaded files."""
        try:
            # Check if user is asking to analyze files
            text_lower = text.lower()
            analyze_keywords = ['analyze', 'analysis', 'extract', 'process', 'review']
            file_keywords = ['file', 'document', 'upload', 'pdf', 'doc']

            wants_file_analysis = (
                any(keyword in text_lower for keyword in analyze_keywords) and
                any(keyword in text_lower for keyword in file_keywords)
            )

            if wants_file_analysis:
                # Get uploaded files for this session
                from services.file_service import FileService
                file_service = FileService(self.event_bus)

                # Get session files from database
                db_manager = await get_database()
                async with db_manager.get_connection() as conn:
                    files_result = await conn.fetch(
                        "SELECT id, original_name, file_type FROM files WHERE session_id = $1 AND state = 'complete'",
                        session_id
                    )

                if files_result:
                    logger.info(f"Found {len(files_result)} uploaded files for session {session_id}")

                    # GATED WORKFLOW FIX: Instead of automatically starting analysis,
                    # just inform the user about the files and let frontend handle the workflow
                    first_file = files_result[0]
                    filename = first_file['original_name']

                    await self._send_assistant_message(
                        session_id,
                        f"I found files in this session. Let me analyze them for HVAC control sequences. I'll extract text first for your review before proceeding with analysis."
                    )
                    # Note: The frontend gated workflow will handle text extraction and approval
                    return

                else:
                    # No files found - let user know
                    await self._send_assistant_message(
                        session_id,
                        "I don't see any uploaded files in this session. Please upload a PDF or document file first, then ask me to analyze it."
                    )
                    return

            # Default: start analysis with just text (no automatic analysis for file workflows)
            # Only start analysis pipeline for pure text conversations
            analysis_id = await self.start_analysis_pipeline(session_id, text)
            logger.info(f"Started analysis {analysis_id} from text input")

        except Exception as e:
            logger.error(f"Error in _start_analysis_from_text: {e}")
            await self._send_assistant_message(
                session_id,
                f"I encountered an error while trying to analyze your request: {str(e)}"
            )
    
    async def _run_analysis_pipeline(self, session_id: str, analysis_id: str, text: Optional[str], source_ids: List[str]) -> None:
        """Run the complete analysis pipeline with progress updates."""
        try:
            # Stage 1: Parse
            await self.event_bus.publish(
                session_id,
                Event(
                    type="message",
                    session_id=session_id,
                    operation="analysis",
                    data={
                        "type": "analysis.progress",
                        "analysisId": analysis_id,
                        "progress": 0.1,
                        "stage": "parse"
                    }
                )
            )
            
            await asyncio.sleep(2)  # Simulate processing
            
            # Stage 2: Normalize
            await self.event_bus.publish(
                session_id,
                Event(
                    type="message",
                    session_id=session_id,
                    operation="analysis",
                    data={
                        "type": "analysis.progress",
                        "analysisId": analysis_id,
                        "progress": 0.5,
                        "stage": "normalize"
                    }
                )
            )
            
            await asyncio.sleep(2)  # Simulate processing
            
            # Stage 3: Synthesize
            await self.event_bus.publish(
                session_id,
                Event(
                    type="message",
                    session_id=session_id,
                    operation="analysis",
                    data={
                        "type": "analysis.progress",
                        "analysisId": analysis_id,
                        "progress": 0.8,
                        "stage": "synthesize"
                    }
                )
            )
            
            await asyncio.sleep(2)  # Simulate processing
            
            # Complete analysis
            analysis_result = await self.analyze_document_content(session_id, text or "Default analysis", "hvac_analysis")
            
            # Create analysis summary
            summary = {
                "equipmentType": "Single-zone AHU",
                "operatingModes": ["Occupied", "Unoccupied"],
                "schedules": [
                    {"name": "Occupancy Schedule", "type": "weekly", "schedule": "Mon-Fri 7AM-6PM"}
                ],
                "alarms": [
                    {"name": "High Temperature", "condition": "SAT > 85°F", "action": "Alarm notification"}
                ],
                "ioPoints": analysis_result.get("io_points", []),
                "controlBlocks": analysis_result.get("control_blocks", []),
                "pseudoCode": "\n".join([step.get("code", "") for step in analysis_result.get("pseudocode", [])])
            }
            
            # Emit analysis completed event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="message",
                    session_id=session_id,
                    operation="analysis",
                    data={
                        "type": "analysis.completed",
                        "analysisId": analysis_id,
                        "summary": summary
                    }
                )
            )
            
            # Automatically start BOG generation
            await self.start_bog_generation(session_id, analysis_id)
            
        except Exception as e:
            logger.error(f"Error in analysis pipeline: {e}")
            await self.event_bus.publish(
                session_id,
                Event(
                    type="message",
                    session_id=session_id,
                    operation="analysis",
                    data={
                        "type": "analysis.failed",
                        "analysisId": analysis_id,
                        "error": str(e),
                        "retryable": True
                    }
                )
            )
    
    async def _run_bog_generation(self, session_id: str, analysis_id: str, artifact_id: str) -> None:
        """Run BOG generation with progress updates."""
        try:
            # Simulate BOG generation process
            await asyncio.sleep(3)
            
            # Create mock BOG file
            bog_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<bog version="2.1" generated="{datetime.now().isoformat()}">
    <metadata>
        <session_id>{session_id}</session_id>
        <analysis_id>{analysis_id}</analysis_id>
        <artifact_id>{artifact_id}</artifact_id>
    </metadata>
    <equipment>
        <ahu name="AHU-1" type="single-zone">
            <points>
                <input name="SAT_Sensor" type="AI" units="degF"/>
                <output name="SAT_Setpoint" type="AO" units="degF"/>
            </points>
            <control_blocks>
                <pid name="Temperature_Control" input="SAT_Sensor" output="SAT_Setpoint"/>
            </control_blocks>
        </ahu>
    </equipment>
</bog>"""
            
            # Save BOG file (mock implementation)
            filename = f"bog-{session_id}-{artifact_id}.xml"
            
            # Emit BOG completed event
            await self.event_bus.publish(
                session_id,
                Event(
                    type="message",
                    session_id=session_id,
                    operation="bog_generation",
                    data={
                        "type": "bog.completed",
                        "bogId": artifact_id,
                        "artifactId": artifact_id
                    }
                )
            )
            
            # Emit artifact available events
            await self.event_bus.publish(
                session_id,
                Event(
                    type="message",
                    session_id=session_id,
                    operation="artifacts",
                    data={
                        "type": "artifact.available",
                        "artifactId": f"analysis-{analysis_id}",
                        "type": "analysis",
                        "downloadUrl": f"/api/files/analysis-{analysis_id}/download"
                    }
                )
            )
            
            await self.event_bus.publish(
                session_id,
                Event(
                    type="message",
                    session_id=session_id,
                    operation="artifacts",
                    data={
                        "type": "artifact.available",
                        "artifactId": artifact_id,
                        "type": "bog",
                        "downloadUrl": f"/api/files/{artifact_id}/download"
                    }
                )
            )
            
        except Exception as e:
            logger.error(f"Error in BOG generation: {e}")
            await self.event_bus.publish(
                session_id,
                Event(
                    type="message",
                    session_id=session_id,
                    operation="bog_generation",
                    data={
                        "type": "bog.failed",
                        "bogId": artifact_id,
                        "error": str(e),
                        "retryable": True
                    }
                )
            )
    async def _send_assistant_message(self, session_id: str, content: str) -> None:
        """Send an assistant message via WebSocket."""
        await self.event_bus.publish(
            session_id,
            Event(
                type="chat",
                session_id=session_id,
                operation="chat",
                data={
                    "content": content,
                    "is_complete": True,
                    "message_type": "assistant"
                }
            )
        )

        # Also save to database
        try:
            await self._save_message_to_db(session_id, "assistant", content, {"automated": True})
        except Exception as e:
            logger.error(f"Failed to save automated message to database: {e}")

    async def _send_analysis_results(self, session_id: str, analysis_result: dict, filename: str) -> None:
        """Send formatted analysis results to the user."""
        try:
            # Format the analysis results nicely
            io_points = analysis_result.get("io_points", [])
            control_blocks = analysis_result.get("control_blocks", [])
            quality_score = analysis_result.get("quality_score", 0)

            result_message = f"""## 📊 Analysis Complete for {filename}

**Quality Score:** {quality_score:.1%}

### 🔌 I/O Points ({len(io_points)} found)
"""
            for point in io_points[:5]:  # Show first 5
                name = point.get("name", "Unknown")
                ptype = point.get("type", "Unknown")
                desc = point.get("description", "")
                result_message += f"- **{name}** ({ptype}): {desc}\n"

            if len(io_points) > 5:
                result_message += f"- ... and {len(io_points) - 5} more points\n"

            result_message += f"\n### ⚙️ Control Blocks ({len(control_blocks)} found)\n"
            for block in control_blocks[:3]:  # Show first 3
                name = block.get("name", "Unknown")
                btype = block.get("type", "Unknown")
                desc = block.get("description", "")
                result_message += f"- **{name}** ({btype}): {desc}\n"

            if len(control_blocks) > 3:
                result_message += f"- ... and {len(control_blocks) - 3} more blocks\n"

            result_message += "\n✅ Analysis complete! You can now request BOG file generation."

            await self._send_assistant_message(session_id, result_message)

        except Exception as e:
            logger.error(f"Error sending analysis results: {e}")
            await self._send_assistant_message(
                session_id,
                f"Analysis completed, but I had trouble formatting the results: {str(e)}"
            )

    async def _get_session_file_context(self, session_id: str) -> str:
        """Get file context information for the session."""
        try:
            db = await get_database()
            files_result = await db.fetch_all(
                "SELECT id, original_name, file_type, file_size FROM files WHERE session_id = $1 AND state = 'complete'",
                session_id
            )

            if not files_result:
                return ""

            context_lines = []
            for file_record in files_result:
                file_id = file_record['id']
                filename = file_record['original_name']
                file_type = file_record['file_type'] or 'unknown'
                file_size = file_record['file_size'] or 0

                # Format file size
                if file_size > 1024 * 1024:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                elif file_size > 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size} bytes"

                context_lines.append(f"- {filename} (ID: {file_id}, Type: {file_type}, Size: {size_str})")

            return "\n".join(context_lines)

        except Exception as e:
            logger.error(f"Error getting session file context: {e}")
            return ""

    def _is_file_analysis_request(self, message: str) -> bool:
        """Check if the user is requesting file analysis."""
        message_lower = message.lower()
        analysis_keywords = ['analyze', 'analysis', 'extract', 'process', 'review', 'examine']
        file_keywords = ['file', 'document', 'upload', 'pdf', 'doc', 'attachment']

        has_analysis_keyword = any(keyword in message_lower for keyword in analysis_keywords)
        has_file_keyword = any(keyword in message_lower for keyword in file_keywords)

        return has_analysis_keyword and has_file_keyword

    async def _handle_file_analysis_request(self, session_id: str, message: str) -> None:
        """Handle a file analysis request with proper tool calling."""
        try:
            # Inform user we're starting analysis
            await self._send_assistant_message(
                session_id,
                "🔍 I found files in this session. Let me analyze them for HVAC control sequences..."
            )

            # Get files from session
            db = await get_database()
            files_result = await db.fetch_all(
                "SELECT id, original_name, file_type FROM files WHERE session_id = $1 AND state = 'complete'",
                session_id
            )

            if not files_result:
                await self._send_assistant_message(
                    session_id,
                    "I don't see any completed file uploads in this session. Please upload a PDF or document first."
                )
                return

            # Process each file
            for file_record in files_result:
                file_id = file_record['id']
                filename = file_record['original_name']
                file_type = file_record['file_type'] or 'unknown'

                await self._analyze_uploaded_file(session_id, file_id, filename, file_type)

        except Exception as e:
            logger.error(f"Error handling file analysis request: {e}")
            await self._send_assistant_message(
                session_id,
                f"I encountered an error while analyzing your files: {str(e)}"
            )

    async def _analyze_uploaded_file(self, session_id: str, file_id: int, filename: str, file_type: str) -> None:
        """Analyze a specific uploaded file."""
        try:
            # Get file content based on type
            if 'pdf' in file_type.lower():
                content = await self._extract_pdf_text(file_id)
            else:
                content = await self._extract_text_content(file_id)

            if not content:
                await self._send_assistant_message(
                    session_id,
                    f"⚠️ Could not extract text content from {filename}. The file might be image-based or corrupted."
                )
                return

            # Perform HVAC analysis
            await self._send_assistant_message(
                session_id,
                f"📄 Analyzing {filename} ({len(content)} characters extracted)..."
            )

            analysis_result = await self.analyze_document_content(
                session_id=session_id,
                content=content,
                analysis_type='hvac_analysis'
            )

            # Send formatted results
            await self._send_analysis_results(session_id, analysis_result, filename)

        except Exception as e:
            logger.error(f"Error analyzing file {filename}: {e}")
            await self._send_assistant_message(
                session_id,
                f"❌ Error analyzing {filename}: {str(e)}"
            )

    async def _extract_pdf_text(self, file_id: int) -> str:
        """Extract text from PDF file."""
        try:
            # Use the file service to get file content
            from services.file_service import FileService
            file_service = FileService(self.event_bus)

            file_content = await file_service.get_file_data(file_id)
            if not file_content:
                return ""

            # For now, return a placeholder. In production, you'd use a PDF text extraction library
            # like PyPDF2, pdfplumber, or call an external service
            return f"[PDF Content Extracted - {len(file_content)} bytes. Text extraction would be implemented here.]"

        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""

    async def _extract_text_content(self, file_id: int) -> str:
        """Extract text content from text-based files."""
        try:
            from services.file_service import FileService
            file_service = FileService(self.event_bus)

            file_content = await file_service.get_file_data(file_id)
            if not file_content:
                return ""

            # Try to decode as UTF-8
            try:
                return file_content.decode('utf-8')
            except UnicodeDecodeError:
                # Try other encodings
                for encoding in ['latin1', 'cp1252', 'iso-8859-1']:
                    try:
                        return file_content.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                return "[Binary file - unable to extract text]"

        except Exception as e:
            logger.error(f"Error extracting text content: {e}")
            return ""

    async def _get_available_tools(self, session_id: str) -> List[Dict[str, Any]]:
        """Get available tools for OpenAI function calling."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "analyze_file",
                    "description": "Analyze an uploaded file for HVAC control sequences and extract I/O points",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_id": {
                                "type": "string",
                                "description": "The ID of the file to analyze"
                            },
                            "analysis_type": {
                                "type": "string",
                                "enum": ["hvac_analysis", "sequence_extraction", "io_point_extraction"],
                                "description": "Type of analysis to perform"
                            }
                        },
                        "required": ["file_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_session_files",
                    "description": "List all uploaded files in the current session",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "The session ID to list files for"
                            }
                        },
                        "required": ["session_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_bog_file",
                    "description": "Generate a BOG file from analysis results",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "analysis_id": {
                                "type": "string",
                                "description": "The analysis ID to generate BOG from"
                            },
                            "equipment_type": {
                                "type": "string",
                                "description": "Type of HVAC equipment (AHU, VAV, FCU, etc.)"
                            }
                        },
                        "required": ["analysis_id"]
                    }
                }
            }
        ]

        return tools

    async def _handle_tool_call(self, session_id: str, tool_call) -> None:
        """Handle OpenAI tool calls."""
        try:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            logger.info(f"Handling tool call: {function_name} with args: {function_args}")

            if function_name == "analyze_file":
                file_id = function_args.get("file_id")
                analysis_type = function_args.get("analysis_type", "hvac_analysis")

                # Get file info
                db = await get_database()
                file_info = await db.fetch_one(
                    "SELECT original_name, file_type FROM files WHERE id = $1",
                    int(file_id)
                )

                if file_info:
                    await self._analyze_uploaded_file(
                        session_id,
                        int(file_id),
                        file_info['original_name'],
                        file_info['file_type'] or 'unknown'
                    )
                else:
                    await self._send_assistant_message(
                        session_id,
                        f"❌ File with ID {file_id} not found."
                    )

            elif function_name == "list_session_files":
                file_context = await self._get_session_file_context(session_id)
                if file_context:
                    await self._send_assistant_message(
                        session_id,
                        f"📁 **Files in this session:**\n{file_context}"
                    )
                else:
                    await self._send_assistant_message(
                        session_id,
                        "📁 No files found in this session."
                    )

            elif function_name == "generate_bog_file":
                analysis_id = function_args.get("analysis_id")
                equipment_type = function_args.get("equipment_type", "AHU")

                await self._send_assistant_message(
                    session_id,
                    f"🔧 Starting BOG file generation for analysis {analysis_id} ({equipment_type})..."
                )

                # Start BOG generation
                bog_id = await self.start_bog_generation(session_id, analysis_id)

            else:
                logger.warning(f"Unknown tool call: {function_name}")
                await self._send_assistant_message(
                    session_id,
                    f"❓ Unknown tool requested: {function_name}"
                )

        except Exception as e:
            logger.error(f"Error handling tool call: {e}")
            await self._send_assistant_message(
                session_id,
                f"❌ Error executing tool: {str(e)}"
            )

