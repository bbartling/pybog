// services/apiService.ts
export interface SensorInput {
  name: string;
  type: string;
  units: string;
  default_value: number;
  range_min?: number;
  range_max?: number;
}

export interface ActuatorOutput {
  name: string;
  type: string;
  control_type: string;
  range: string;
  default_value: number;
}

export interface ControlSequence {
  name: string;
  type: string;
  description: string;
  components: string[];
  logic?: string;
}

export interface BogGenerationRequest {
  bog_name: string;
  session_id?: string;
  inputs: SensorInput[];
  outputs: ActuatorOutput[];
  control_sequences: ControlSequence[];
  setpoints: Record<string, number>;
  alarms: any[];
  metadata: Record<string, any>;
}

export interface BogGenerationResponse {
  success: boolean;
  session_id: string;
  bog_file_path?: string;
  download_url?: string;
  components_processed: Record<string, number>;
  message: string;
  errors: string[];
}

export interface ChatMessage {
  action: string;
  sessionId: string;
  chatInput: string;
  files: Array<{
    filename: string;
    mimeType: string;
    content: string;
    size: number;
  }>;
}

class ApiService {
  private readonly baseUrl: string;
  private readonly n8nUrl: string;

  constructor() {
    this.baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    this.n8nUrl = process.env.REACT_APP_N8N_URL || 'http://localhost:5678';
  }

  // Health check
  async healthCheck(): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/health`);
      return await response.json();
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  }

  // Send chat message through n8n workflow
  async sendChatMessage(message: ChatMessage): Promise<any> {
    try {
      const response = await fetch(`${this.n8nUrl}/webhook/pybog-chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(message)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const responseText = await response.text();
      
      // Try to parse as JSON, fallback to text
      try {
        return responseText ? JSON.parse(responseText) : {};
      } catch (parseError) {
        return { message: responseText || 'Empty response from server' };
      }
    } catch (error) {
      console.error('Chat message failed:', error);
      throw error;
    }
  }

  // Generate BOG file
  async generateBog(request: BogGenerationRequest): Promise<BogGenerationResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/generate-bog`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      return await response.json();
    } catch (error) {
      console.error('BOG generation failed:', error);
      throw error;
    }
  }

  // Validate schema before generation
  async validateSchema(inputs: SensorInput[], outputs: ActuatorOutput[], sequences: ControlSequence[]): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/validate-schema`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          inputs,
          outputs,
          control_sequences: sequences
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Schema validation failed:', error);
      throw error;
    }
  }
  // Download BOG file
  async downloadBogFile(sessionId: string, filename: string): Promise<Blob> {
    try {
      const response = await fetch(`${this.baseUrl}/api/download/${sessionId}/${filename}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: File not found`);
      }

      return await response.blob();
    } catch (error) {
      console.error('Download failed:', error);
      throw error;
    }
  }

  // Convert file to text content for processing
  async fileToText(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === 'string') {
          resolve(reader.result);
        } else {
          reject(new Error('Failed to read file as text'));
        }
      };
      reader.onerror = reject;
      
      // For text files, read as text. For others, attempt text reading
      // In production, you'd use proper libraries like pdf-parse or mammoth
      if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
        reader.readAsText(file);
      } else if (file.type === 'application/pdf') {
        // For PDF files, this is a fallback - proper PDF parsing would be needed
        reader.readAsText(file);
      } else if (file.type.includes('word') || file.name.endsWith('.docx')) {
        // For DOCX files, this is a fallback - mammoth.js would be better
        reader.readAsText(file);
      } else {
        reader.readAsText(file);
      }
    });
  }

  // Get session state from database
  async getSessionState(sessionId: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}/state`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Failed to get session state:', error);
      throw error;
    }
  }

  // Get full session history from Postgres (hvac_chat_memory)
  async getSessionHistory(sessionId: string, limit = 100): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}/history?limit=${limit}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Failed to get session history:', error);
      throw error;
    }
  }

  // Approve analysis and continue workflow
  async approveAnalysis(sessionId: string, approved: boolean, feedback?: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          approved,
          feedback
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to approve analysis:', error);
      throw error;
    }
  }

  // Submit feedback for changes
  async submitFeedback(sessionId: string, feedback: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ feedback })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      throw error;
    }
  }

  // Start session state polling
  startSessionPolling(sessionId: string, callback: (state: any) => void): NodeJS.Timeout {
    const poll = async () => {
      try {
        const state = await this.getSessionState(sessionId);
        callback(state);
      } catch (error) {
        console.error('Polling error:', error);
      }
    };
    
    return setInterval(poll, 2000); // Poll every 2 seconds
  }

  // Stop session polling
  stopSessionPolling(intervalId: NodeJS.Timeout): void {
    clearInterval(intervalId);
  }

  // Convert file to base64 for transmission
  async fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === 'string') {
          // Remove the data URL prefix
          resolve(reader.result.split(',')[1]);
        } else {
          reject(new Error('Failed to read file'));
        }
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  // Create a new session
  async createSession(sessionId: string, description: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          description
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to create session:', error);
      throw error;
    }
  }

  // Upload file for session
  async uploadSessionFile(sessionId: string, file: File): Promise<any> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('session_id', sessionId);
      
      const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}/upload`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Failed to upload file:', error);
      throw error;
    }
  }
}

export const apiService = new ApiService();
export default apiService;