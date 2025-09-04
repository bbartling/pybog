"""
N8N Integration Module for PyBOG
Handles proper file forwarding to N8N workflows
"""

import httpx
import json
import logging
from typing import Dict, Any, Optional
from fastapi import UploadFile, HTTPException
import io

logger = logging.getLogger(__name__)

class N8NIntegration:
    def __init__(self, n8n_url: str = "http://n8n:5678"):
        self.n8n_url = n8n_url
        
    async def send_document_to_ingestion_workflow(
        self, 
        session_id: str,
        file: UploadFile,
        message: str = "",
        history: list = None
    ) -> Dict[str, Any]:
        """
        Send document to N8N ingestion (if used). Keeps payload keys camelCase.
        """
        try:
            # Prepare the multipart form data
            files = {
                'files0': (file.filename, await file.read(), file.content_type or 'application/octet-stream')
            }
            
            # JSON data goes in form fields
            data = {
                'sessionId': session_id,
                'message': message or f"Process document: {file.filename}",
                'history': json.dumps(history or [])
            }
            
            # If you later add a dedicated ingestion webhook, update the path here
            webhook_url = f"{self.n8n_url}/webhook/pybog-analyze"
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    webhook_url,
                    files=files,
                    data=data
                )
                
                if 200 <= response.status_code < 300:
                    return {
                        "success": True,
                        "data": response.json(),
                        "message": "Document sent to N8N workflow successfully"
                    }
                else:
                    logger.error(f"N8N workflow returned {response.status_code}: {response.text}")
                    return {
                        "success": False,
                        "error": f"Workflow error: {response.status_code}",
                        "details": response.text
                    }
                    
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to N8N: {e}")
            return {
                "success": False,
                "error": "Failed to connect to N8N workflow engine",
                "details": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error in N8N integration: {e}")
            return {
                "success": False,
                "error": "Unexpected error",
                "details": str(e)
            }
    
    async def trigger_analysis_workflow(
        self,
        session_id: str,
        text: str,
        extracted_text: str = "",
        conversation_history: list = None
    ) -> Dict[str, Any]:
        """
        Trigger the live Analysis workflow via /webhook/pybog-analyze.
        """
        try:
            payload = {
                "sessionId": session_id,
                "message": text,
                "extracted_text": extracted_text,
                "conversationHistory": conversation_history or []
            }
            
            webhook_url = f"{self.n8n_url}/webhook/pybog-analyze"
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    webhook_url,
                    json=payload
                )
                
                if 200 <= response.status_code < 300:
                    return {
                        "success": True,
                        "data": response.json(),
                        "message": "Analysis workflow triggered successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Workflow error: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Failed to trigger analysis workflow: {e}")
            return {
                "success": False,
                "error": "Failed to trigger analysis",
                "details": str(e)
            }
    
    async def approve_and_generate_bog(
        self,
        session_id: str,
        approved: bool = True,
        feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call the live Generation workflow webhook (pybog-approve).
        If approved=True, action='approve'; otherwise action='refine'.
        """
        try:
            action = "approve" if approved else "refine"
            payload = {
                "sessionId": session_id,
                "action": action,
            }
            if feedback:
                payload["feedback"] = feedback
            
            webhook_url = f"{self.n8n_url}/webhook/pybog-approve"
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    webhook_url,
                    json=payload
                )
                
                if 200 <= response.status_code < 300:
                    return {
                        "success": True,
                        "data": response.json(),
                        "message": "BOG generation initiated" if approved else "Refinement submitted"
                    }
                else:
                    logger.error(f"Generation webhook returned {response.status_code}: {response.text}")
                    return {
                        "success": False,
                        "error": f"Workflow error: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Failed to call generation workflow: {e}")
            return {
                "success": False,
                "error": "Failed to call generation workflow",
                "details": str(e)
            }

# Singleton instance
n8n_integration = N8NIntegration()
