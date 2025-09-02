import React, { useState, useRef, useEffect } from 'react';
import { 
  Download, Upload, Send, FileText, CheckCircle, XCircle, Loader2,
  ChevronRight, ChevronDown, Folder, Package, Cpu, Settings, AlertCircle
} from 'lucide-react';
import apiService, { ChatMessage } from './services/apiService';
import { AnalysisData } from './components/AnalysisBlock';
import N4WorkbenchLayout from './components/N4WorkbenchLayout';

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  messageType?: 'status' | 'analysis' | 'artifact' | 'user' | 'processing' | 'error';
  content: string;
  timestamp: Date;
  files?: File[];
  metadata?: {
    analysisData?: AnalysisData;
    downloadUrl?: string;
    status?: 'processing' | 'complete' | 'error' | 'awaiting_approval';
  };
}

// WebSocket message types
interface WebSocketMessage {
  type: string;
  sessionId: string;
  timestamp: string;
  analysis?: AnalysisData;
  downloadUrl?: string;
  message?: string;
}


interface UploadedDocument {
  id: string;
  name: string;
  type: string;
  size: number;
  uploadDate: Date;
  content?: string;
}

interface BogFile {
  id: string;
  name: string;
  generatedDate: Date;
  downloadUrl: string;
  componentCount: number;
  status: 'ready' | 'generating' | 'error';
}
const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentSessionId] = useState(() => `session_${Date.now()}`);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [bogFiles, setBogFiles] = useState<BogFile[]>([]);
  const [currentWorkflowState, setCurrentWorkflowState] = useState<'idle' | 'analyzing' | 'awaiting_approval' | 'generating' | 'complete'>('idle');
  const [currentAnalysis, setCurrentAnalysis] = useState<AnalysisData | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // WebSocket connection setup
  useEffect(() => {
    const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
    const ws = new WebSocket(`${wsUrl}/ws/${currentSessionId}`);

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data);
        console.log('WebSocket message received:', data);

        switch (data.type) {
          case 'connected':
            console.log('WebSocket connection confirmed');
            break;

          case 'analysis_complete':
            if (data.analysis) {
              setCurrentAnalysis(data.analysis);
              setCurrentWorkflowState('awaiting_approval');
              
              // Add analysis message to chat
              const analysisMessage: Message = {
                id: `analysis-${Date.now()}`,
                type: 'assistant',
                messageType: 'analysis',
                content: 'HVAC System Analysis Complete',
                timestamp: new Date(data.timestamp),
                metadata: { analysisData: data.analysis }
              };
              
              setMessages(prev => [...prev, analysisMessage]);
            }
            break;

          case 'bog_generated':
            setCurrentWorkflowState('complete');
            
            // Add completion message to chat
            const completionMessage: Message = {
              id: `completion-${Date.now()}`,
              type: 'assistant',
              messageType: 'artifact',
              content: data.message || 'BOG file generated successfully!',
              timestamp: new Date(data.timestamp),
              metadata: { downloadUrl: data.downloadUrl }
            };
            
            setMessages(prev => [...prev, completionMessage]);
            break;

          default:
            console.log('Unknown WebSocket message type:', data.type);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    // Cleanup on unmount
    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [currentSessionId]);

  useEffect(() => {
    // Initialize with system ready message
    setMessages([{
      id: 'system_init',
      type: 'assistant',
      content: `PyBOG Control Builder - System Ready

🔧 N8N Workflow Engine: Checking connection...
📊 BOG Generation Service: Standby
📁 File Processing: Ready

Upload HVAC control sequence documents or describe your control requirements to generate BOG files for Niagara Workbench.`,
      timestamp: new Date()
    }]);

    checkSystemHealth();
  }, []);

  const checkSystemHealth = async () => {
    try {
      await apiService.healthCheck();
      
      // Update system status message
      setMessages(prev => prev.map(msg => 
        msg.id === 'system_init' 
          ? {
              ...msg,
              content: `PyBOG Control Builder - System Ready

✅ N8N Workflow Engine: Connected  
✅ BOG Generation Service: Online
✅ File Processing: Ready

Upload HVAC control sequence documents or describe your control requirements to generate BOG files for Niagara Workbench.`
            }
          : msg
      ));
    } catch (error) {
      setMessages(prev => prev.map(msg => 
        msg.id === 'system_init' 
          ? {
              ...msg,
              content: `PyBOG Control Builder - Connection Error

❌ N8N Workflow Engine: Disconnected
❌ BOG Generation Service: Offline
⚠️  File Processing: Limited

Please check N8N service and try again.`
            }
          : msg
      ));
    }
  };

  const addMessage = (message: Message) => {
    setMessages(prev => [...prev, message]);
  };

  const sendMessage = async () => {
    if (!inputText.trim() && uploadedFiles.length === 0) return;

    const userMessage: Message = {
      id: `user_${Date.now()}`,
      type: 'user',
      content: inputText,
      timestamp: new Date(),
      files: uploadedFiles.length > 0 ? [...uploadedFiles] : undefined
    };

    addMessage(userMessage);
    const currentInput = inputText;
    const currentFiles = [...uploadedFiles];
    setInputText('');
    setUploadedFiles([]);
    setIsLoading(true);
    setCurrentWorkflowState('analyzing');
    try {
      // Prepare file contents for N8N processing
      const fileContents = currentFiles.length > 0 ? await Promise.all(
        currentFiles.map(async (file) => {
          try {
            const content = await apiService.fileToText(file);
            return {
              filename: file.name,
              mimeType: file.type,
              content: content,
              size: file.size
            };
          } catch (error) {
            console.error('Failed to process file:', file.name, error);
            return {
              filename: file.name,
              mimeType: file.type,
              content: `Error reading file: ${file.name}`,
              size: file.size
            };
          }
        })
      ) : [];

      // Send to N8N via API service
      const chatMessage: ChatMessage = {
        action: 'sendMessage',
        sessionId: currentSessionId,
        chatInput: currentInput,
        files: fileContents
      };

      const result = await apiService.sendChatMessage(chatMessage);

      // Process AI response
      let displayText = '';
      let downloadUrl = '';

      if (typeof result === 'string') {
        displayText = result;
      } else if (result.response || result.message) {
        displayText = result.response || result.message;
        
        // Check for BOG file generation
        if (displayText.toLowerCase().includes('bog') && displayText.toLowerCase().includes('generated')) {
          const newBog: BogFile = {
            id: `bog_${Date.now()}`,
            name: `Generated_${currentInput.substring(0, 20).replace(/[^a-zA-Z0-9]/g, '_')}.bog`,
            generatedDate: new Date(),
            downloadUrl: result.download_url || `#download_${Date.now()}`,
            componentCount: Math.floor(Math.random() * 30) + 5,
            status: 'ready'
          };
          setBogFiles(prev => [...prev, newBog]);
        }
      } else if (result.success === false) {
        displayText = `❌ N8N Processing Error: ${result.error || result.message || 'Unknown error occurred'}`;
      } else if (Object.keys(result).length === 0) {
        displayText = `⚠️ No Response: N8N workflow returned empty response. Check workflow configuration.`;
      } else {
        displayText = `🔧 Processing Result:\n${JSON.stringify(result, null, 2)}`;
      }
      // Add AI response as system message
      const assistantMessage: Message = {
        id: `assistant_${Date.now()}`,
        type: 'assistant',
        content: displayText,
        timestamp: new Date()
      };

      addMessage(assistantMessage);

      // Handle BOG file download if available
      downloadUrl = result.download_url || 
                   result.downloadUrl ||
                   (result.data && result.data.download_url) ||
                   '';

      if (downloadUrl) {
        const downloadMessage: Message = {
          id: `download_${Date.now()}`,
          type: 'assistant',
          content: `✅ BOG File Generated Successfully!

📥 Download: ${downloadUrl}

Import this BOG file into Niagara Workbench to use the generated control logic wiresheet.`,
          timestamp: new Date()
        };
        addMessage(downloadMessage);
      }

    } catch (error) {
      console.error('N8N communication error:', error);
      const errorMessage: Message = {
        id: `error_${Date.now()}`,
        type: 'assistant',
        content: `❌ System Connection Error

Failed to connect to N8N workflow service:
${error instanceof Error ? error.message : 'Unknown connection error'}

Please ensure:
- N8N service is running
- Workflow is activated  
- Network connectivity is available`,
        timestamp: new Date()
      };
      addMessage(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };


  // Helper function to determine message type
  const getMessageType = (message: Message): string => {
    if (message.messageType) {
      return message.messageType;
    }
    
    // Legacy message type detection
    const isUser = message.type === 'user';
    if (isUser) return 'user';
    
    const content = message.content.toLowerCase();
    if (content.includes('analysis complete') || content.includes('hvac system analysis')) {
      return 'analysis';
    }
    if (content.includes('bog file generated') || content.includes('download')) {
      return 'artifact';
    }
    
    return 'system-status';
  };

  // Approval handlers for AnalysisBlock
  const handleApproveAnalysis = async () => {
    if (!currentAnalysis) return;
    
    try {
      setCurrentWorkflowState('generating');
      setIsLoading(true);
      
      // Call API to approve analysis
      const response = await fetch(`http://localhost:8000/api/sessions/${currentSessionId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: currentSessionId,
          approved: true
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to approve analysis');
      }
      
      // Add status message
      const statusMessage: Message = {
        id: `status-${Date.now()}`,
        type: 'assistant',
        messageType: 'status',
        content: '✅ Analysis approved! Generating BOG file...',
        timestamp: new Date()
      };
      
      addMessage(statusMessage);
      
    } catch (error) {
      console.error('Error approving analysis:', error);
      setCurrentWorkflowState('awaiting_approval');
      
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        type: 'assistant',
        messageType: 'status',
        content: `❌ Failed to approve analysis: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date()
      };
      
      addMessage(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRequestChanges = async (feedback: string) => {
    if (!currentAnalysis) return;
    
    try {
      setCurrentWorkflowState('idle');
      
      // Call API to submit feedback
      const response = await fetch(`http://localhost:8000/api/sessions/${currentSessionId}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ feedback })
      });
      
      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }
      
      // Add feedback message
      const feedbackMessage: Message = {
        id: `feedback-${Date.now()}`,
        type: 'user',
        messageType: 'user',
        content: `Changes requested: ${feedback}`,
        timestamp: new Date()
      };
      
      const statusMessage: Message = {
        id: `status-${Date.now()}`,
        type: 'assistant',
        messageType: 'status',
        content: '📝 Feedback received. Re-analyzing with your requested changes...',
        timestamp: new Date()
      };
      
      addMessage(feedbackMessage);
      addMessage(statusMessage);
      
      // Reset current analysis
      setCurrentAnalysis(null);
      
    } catch (error) {
      console.error('Error submitting feedback:', error);
      
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        type: 'assistant',
        messageType: 'error',
        content: `❌ Failed to submit feedback: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date()
      };
      
      addMessage(errorMessage);
    }
  };


  // Convert messages for WorkbenchLayout
  const workbenchMessages = messages.map(msg => ({
    id: msg.id,
    type: msg.type as 'user' | 'assistant' | 'system',
    content: msg.content,
    timestamp: msg.timestamp,
    component: msg.type === 'user' ? 'string-writable' as const : 
               msg.messageType === 'analysis' ? 'folder' as const :
               msg.messageType === 'artifact' ? 'bool-writable' as const :
               'enum-writable' as const
  }));

  // Convert BOG files for WorkbenchLayout
  const workbenchBogFiles = bogFiles.map(bog => ({
    id: bog.id,
    name: bog.name,
    size: bog.componentCount * 1024, // Estimate size
    timestamp: bog.generatedDate,
    status: bog.status as 'ready' | 'generating'
  }));

  const handleSendMessage = async (text: string, files: File[]) => {
    if (!text.trim() && files.length === 0) return;

    // Add user message
    const userMessage: Message = {
      id: `user_${Date.now()}`,
      type: 'user',
      messageType: 'user',
      content: text || `Uploaded ${files.length} file(s)`,
      timestamp: new Date(),
      files: files.length > 0 ? files : undefined
    };
    addMessage(userMessage);

    // Add processing status
    const processingMessage: Message = {
      id: `processing_${Date.now()}`,
      type: 'system',
      messageType: 'processing',
      content: files.length > 0 ? 'Processing documents...' : 'Analyzing requirements...',
      timestamp: new Date()
    };
    addMessage(processingMessage);

    setIsLoading(true);
    setCurrentWorkflowState('analyzing');

    try {
      // Process files if any
      const fileContents = files.length > 0 ? await Promise.all(
        files.map(async (file) => {
          try {
            const content = await apiService.fileToText(file);
            return {
              filename: file.name,
              mimeType: file.type,
              content: content,
              size: file.size
            };
          } catch (error) {
            console.error('Failed to process file:', file.name, error);
            return {
              filename: file.name,
              mimeType: file.type,
              content: `Error reading file: ${file.name}`,
              size: file.size
            };
          }
        })
      ) : [];

      // Send to API
      const chatMessage: ChatMessage = {
        action: 'sendMessage',
        sessionId: currentSessionId,
        chatInput: text,
        files: fileContents
      };

      const result = await apiService.sendChatMessage(chatMessage);
      
      // Remove processing message
      setMessages(prev => prev.filter(msg => msg.messageType !== 'processing'));

      // Process response
      let displayText = '';
      if (typeof result === 'string') {
        displayText = result;
      } else if (result.response || result.message) {
        displayText = result.response || result.message;
      } else {
        displayText = JSON.stringify(result, null, 2);
      }

      const assistantMessage: Message = {
        id: `assistant_${Date.now()}`,
        type: 'assistant',
        messageType: 'status',
        content: displayText,
        timestamp: new Date()
      };
      addMessage(assistantMessage);

    } catch (error) {
      console.error('Error:', error);
      // Remove processing message
      setMessages(prev => prev.filter(msg => msg.messageType !== 'processing'));
      
      const errorMessage: Message = {
        id: `error_${Date.now()}`,
        type: 'assistant',
        messageType: 'error',
        content: `❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date()
      };
      addMessage(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <N4WorkbenchLayout
      messages={messages}
      isLoading={isLoading}
      bogFiles={workbenchBogFiles}
      onSendMessage={sendMessage}
      onApproveAnalysis={handleApproveAnalysis}
      onRequestChanges={handleRequestChanges}
      workflowState={currentWorkflowState}
      currentAnalysis={currentAnalysis}
    />
  );
};

export default App;
