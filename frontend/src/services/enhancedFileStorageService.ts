/**
 * Enhanced File Storage Service
 * 
 * FIXES the file upload and storage system by:
 * 1. Preserving files as base64 data for resend/replay functionality  
 * 2. Attaching files to chat sessions persistently
 * 3. Enabling file modal rendering with preview capabilities
 * 4. Supporting retry/resend operations with original file data
 * 5. Integrating with backend for proper file management
 */

export interface StoredFile {
  id: string;
  name: string;
  size: number;
  type: string;
  sessionId: string;
  messageId?: string;
  uploadedAt: Date;
  
  // File data for resend/retry (stored as base64)
  base64Data?: string;
  
  // Backend integration
  backendFileId?: string;
  downloadUrl?: string;
  previewUrl?: string;
  
  // Processing status
  status: 'uploading' | 'uploaded' | 'processing' | 'processed' | 'error';
  error?: string;
  
  // Metadata
  metadata?: {
    extractedText?: string;
    pageCount?: number;
    wordCount?: number;
    hvacTermsFound?: string[];
    processingTime?: number;
  };
}

export interface FileUploadProgress {
  fileId: string;
  loaded: number;
  total: number;
  percentage: number;
  stage: 'uploading' | 'processing' | 'complete';
}

class EnhancedFileStorageService {
  private files = new Map<string, StoredFile>();
  private progressListeners = new Map<string, Set<(progress: FileUploadProgress) => void>>();
  private storageKey = 'pybog_stored_files';
  
  constructor() {
    this.loadFromStorage();
  }
  
  /**
   * Store files from File objects with base64 data preservation
   */
  async storeFiles(sessionId: string, files: File[], messageId?: string): Promise<StoredFile[]> {
    const storedFiles: StoredFile[] = [];
    
    for (const file of files) {
      try {
        // Convert to base64 for persistent storage
        const base64Data = await this.fileToBase64(file);
        
        const storedFile: StoredFile = {
          id: `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          name: file.name,
          size: file.size,
          type: file.type,
          sessionId,
          messageId,
          uploadedAt: new Date(),
          base64Data,
          status: 'uploading'
        };
        
        this.files.set(storedFile.id, storedFile);
        storedFiles.push(storedFile);
        
        console.log(`[FileStorage] Stored file ${storedFile.name} with base64 data (${base64Data.length} chars)`);
        
        // Emit progress
        this.emitProgress(storedFile.id, { 
          fileId: storedFile.id, 
          loaded: file.size, 
          total: file.size, 
          percentage: 100, 
          stage: 'uploading' 
        });
        
      } catch (error) {
        console.error('[FileStorage] Failed to store file:', file.name, error);
        
        // Store without base64 data but mark as error
        const errorFile: StoredFile = {
          id: `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          name: file.name,
          size: file.size,
          type: file.type,
          sessionId,
          messageId,
          uploadedAt: new Date(),
          status: 'error',
          error: error instanceof Error ? error.message : 'Failed to process file'
        };
        
        this.files.set(errorFile.id, errorFile);
        storedFiles.push(errorFile);
      }
    }
    
    this.saveToStorage();
    return storedFiles;
  }
  
  /**
   * Update file with backend information
   */
  updateFile(fileId: string, updates: Partial<StoredFile>): void {
    const file = this.files.get(fileId);
    if (!file) {
      console.warn('[FileStorage] File not found for update:', fileId);
      return;
    }
    
    const updatedFile = { ...file, ...updates };
    this.files.set(fileId, updatedFile);
    this.saveToStorage();
    
    console.log(`[FileStorage] Updated file ${file.name}:`, updates);
  }
  
  /**
   * Get files for a session
   */
  getSessionFiles(sessionId: string): StoredFile[] {
    return Array.from(this.files.values())
      .filter(file => file.sessionId === sessionId)
      .sort((a, b) => b.uploadedAt.getTime() - a.uploadedAt.getTime());
  }
  
  /**
   * Get files for a specific message
   */
  getMessageFiles(messageId: string): StoredFile[] {
    return Array.from(this.files.values())
      .filter(file => file.messageId === messageId);
  }
  
  /**
   * Get a specific file
   */
  getFile(fileId: string): StoredFile | undefined {
    return this.files.get(fileId);
  }
  
  /**
   * Convert stored file back to File object for resending
   */
  async restoreFileObject(fileId: string): Promise<File | null> {
    const storedFile = this.files.get(fileId);
    if (!storedFile || !storedFile.base64Data) {
      console.warn('[FileStorage] Cannot restore file - no base64 data:', fileId);
      return null;
    }
    
    try {
      // Convert base64 back to File object
      const response = await fetch(storedFile.base64Data);
      const blob = await response.blob();
      
      const file = new File([blob], storedFile.name, {
        type: storedFile.type,
        lastModified: storedFile.uploadedAt.getTime()
      });
      
      console.log(`[FileStorage] Restored File object for ${storedFile.name}`);
      return file;
      
    } catch (error) {
      console.error('[FileStorage] Failed to restore File object:', error);
      return null;
    }
  }
  
  /**
   * Restore multiple files for resending
   */
  async restoreMessageFiles(messageId: string): Promise<File[]> {
    const storedFiles = this.getMessageFiles(messageId);
    const restoredFiles: File[] = [];
    
    for (const storedFile of storedFiles) {
      const file = await this.restoreFileObject(storedFile.id);
      if (file) {
        restoredFiles.push(file);
      }
    }
    
    console.log(`[FileStorage] Restored ${restoredFiles.length}/${storedFiles.length} files for message ${messageId}`);
    return restoredFiles;
  }
  
  /**
   * Delete file
   */
  deleteFile(fileId: string): boolean {
    const deleted = this.files.delete(fileId);
    if (deleted) {
      this.saveToStorage();
      console.log('[FileStorage] Deleted file:', fileId);
    }
    return deleted;
  }
  
  /**
   * Delete all files for a session
   */
  deleteSessionFiles(sessionId: string): number {
    let deletedCount = 0;
    
    // Use Array.from to avoid downlevel iteration issues
    const entries = Array.from(this.files.entries());
    for (const [fileId, file] of entries) {
      if (file.sessionId === sessionId) {
        this.files.delete(fileId);
        deletedCount++;
      }
    }
    
    if (deletedCount > 0) {
      this.saveToStorage();
      console.log(`[FileStorage] Deleted ${deletedCount} files for session ${sessionId}`);
    }
    
    return deletedCount;
  }
  
  /**
   * Subscribe to upload progress
   */
  onProgress(fileId: string, callback: (progress: FileUploadProgress) => void): () => void {
    if (!this.progressListeners.has(fileId)) {
      this.progressListeners.set(fileId, new Set());
    }
    
    const listeners = this.progressListeners.get(fileId)!;
    listeners.add(callback);
    
    return () => {
      listeners.delete(callback);
      if (listeners.size === 0) {
        this.progressListeners.delete(fileId);
      }
    };
  }
  
  /**
   * Emit progress update
   */
  private emitProgress(fileId: string, progress: FileUploadProgress): void {
    const listeners = this.progressListeners.get(fileId);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(progress);
        } catch (error) {
          console.error('[FileStorage] Progress callback error:', error);
        }
      });
    }
  }
  
  /**
   * Generate file preview URL from base64 data
   */
  getFilePreviewUrl(fileId: string): string | null {
    const file = this.files.get(fileId);
    if (!file || !file.base64Data) {
      return null;
    }
    
    // For images, return base64 data URL directly
    if (file.type.startsWith('image/')) {
      return file.base64Data;
    }
    
    // For other files, use backend preview URL if available
    return file.previewUrl || null;
  }
  
  /**
   * Get file statistics for a session
   */
  getSessionFileStats(sessionId: string): {
    totalFiles: number;
    totalSize: number;
    byType: Record<string, number>;
    byStatus: Record<string, number>;
  } {
    const sessionFiles = this.getSessionFiles(sessionId);
    
    const stats = {
      totalFiles: sessionFiles.length,
      totalSize: sessionFiles.reduce((sum, file) => sum + file.size, 0),
      byType: {} as Record<string, number>,
      byStatus: {} as Record<string, number>
    };
    
    for (const file of sessionFiles) {
      // Count by type
      const type = file.type.split('/')[0] || 'unknown';
      stats.byType[type] = (stats.byType[type] || 0) + 1;
      
      // Count by status
      stats.byStatus[file.status] = (stats.byStatus[file.status] || 0) + 1;
    }
    
    return stats;
  }
  
  /**
   * Convert File to base64 data URL
   */
  private async fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = () => {
        if (typeof reader.result === 'string') {
          resolve(reader.result);
        } else {
          reject(new Error('Failed to convert file to base64'));
        }
      };
      
      reader.onerror = () => {
        reject(new Error('FileReader error'));
      };
      
      reader.readAsDataURL(file);
    });
  }
  
  /**
   * Load files from localStorage
   */
  private loadFromStorage(): void {
    try {
      const stored = localStorage.getItem(this.storageKey);
      if (stored) {
        const data = JSON.parse(stored);
        
        // Convert dates back from strings
        for (const [fileId, fileData] of Object.entries(data)) {
          const file = fileData as any;
          if (file.uploadedAt) {
            file.uploadedAt = new Date(file.uploadedAt);
          }
          this.files.set(fileId, file);
        }
        
        console.log(`[FileStorage] Loaded ${this.files.size} files from storage`);
      }
    } catch (error) {
      console.error('[FileStorage] Failed to load from storage:', error);
    }
  }
  
  /**
   * Save files to localStorage
   */
  private saveToStorage(): void {
    try {
      const data: Record<string, StoredFile> = {};
      
      // Only store recent files to avoid localStorage quota issues
      const cutoff = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000); // 7 days ago
      
      const entries = Array.from(this.files.entries());
      for (const [fileId, file] of entries) {
        if (file.uploadedAt > cutoff) {
          data[fileId] = file;
        }
      }
      
      localStorage.setItem(this.storageKey, JSON.stringify(data));
      
      // Clean up old files from memory too
      for (const [fileId, file] of entries) {
        if (file.uploadedAt <= cutoff) {
          this.files.delete(fileId);
        }
      }
      
    } catch (error) {
      console.error('[FileStorage] Failed to save to storage:', error);
      
      // If storage is full, try clearing old files and saving again
      if (error instanceof Error && error.name === 'QuotaExceededError') {
        this.clearOldFiles();
        try {
          const data: Record<string, StoredFile> = {};
          for (const [fileId, file] of this.files.entries()) {
            // Only save essential data for recent files
            data[fileId] = {
              ...file,
              base64Data: undefined // Remove base64 data to save space
            };
          }
          localStorage.setItem(this.storageKey, JSON.stringify(data));
          console.warn('[FileStorage] Saved without base64 data due to storage quota');
        } catch (secondError) {
          console.error('[FileStorage] Failed to save even without base64 data:', secondError);
        }
      }
    }
  }
  
  /**
   * Clear old files from storage
   */
  private clearOldFiles(): void {
    const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000); // 1 day ago
    let deletedCount = 0;
    
    for (const [fileId, file] of this.files.entries()) {
      if (file.uploadedAt <= cutoff) {
        this.files.delete(fileId);
        deletedCount++;
      }
    }
    
    console.log(`[FileStorage] Cleared ${deletedCount} old files`);
  }
  
  /**
   * Get storage usage information
   */
  getStorageInfo(): {
    totalFiles: number;
    totalSizeEstimate: number;
    hasBase64Data: number;
    oldestFile: Date | null;
    newestFile: Date | null;
  } {
    const files = Array.from(this.files.values());
    
    return {
      totalFiles: files.length,
      totalSizeEstimate: files.reduce((sum, file) => sum + file.size + (file.base64Data?.length || 0), 0),
      hasBase64Data: files.filter(f => f.base64Data).length,
      oldestFile: files.length > 0 ? new Date(Math.min(...files.map(f => f.uploadedAt.getTime()))) : null,
      newestFile: files.length > 0 ? new Date(Math.max(...files.map(f => f.uploadedAt.getTime()))) : null
    };
  }
  
  /**
   * Clean up all data
   */
  cleanup(): void {
    this.files.clear();
    this.progressListeners.clear();
    localStorage.removeItem(this.storageKey);
    console.log('[FileStorage] Cleanup completed');
  }
}

// Export singleton instance
export const enhancedFileStorageService = new EnhancedFileStorageService();
export default enhancedFileStorageService;