import React, { useState, useEffect } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  FileText,
  Plus,
  Trash2,
  Edit3,
  Save,
  X,
  Download,
  Database,
  Eye,
  MessageSquare,
  FileCode,
  BarChart3,
  Clock
} from 'lucide-react';
import FileViewerModal from './FileViewerModal';
import { ChatMessage, Session } from '../types/ChatMessage';

interface ProjectNavigatorProps {
  sessionId: string;
  sessions: Session[];
  currentAnalysis?: any;
  messages: ChatMessage[];
  sessionFiles?: { file_id: string; filename: string; file_type: string; file_size: number; preview_url: string; }[];
  onCreateSession: () => void;
  onSwitchSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onRenameSession?: (id: string, name: string) => void;
  onClearAllSessions?: () => void;
}

const ProjectNavigator: React.FC<ProjectNavigatorProps> = ({
  sessionId,
  sessions,
  currentAnalysis,
  messages,
  sessionFiles = [],
  onCreateSession,
  onSwitchSession,
  onDeleteSession,
  onRenameSession,
  onClearAllSessions,
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['sessions', `session-${sessionId}`])
  );
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerFile, setViewerFile] = useState<{ 
    name: string; 
    url: string; 
    type?: 'pdf' | 'text' | 'json' | 'docx' | 'unknown';
    file_id?: string;
    file_size?: number;
    mime_type?: string;
    state?: string;
    created_at?: string;
  } | null>(null);

  // Update expanded sections when session changes
  useEffect(() => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      newSet.add(`session-${sessionId}`);
      return newSet;
    });
  }, [sessionId]);

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(section)) {
        newSet.delete(section);
      } else {
        newSet.add(section);
      }
      return newSet;
    });
  };

  const startRename = (session: Session) => {
    setEditingSessionId(session.id);
    setEditingName(session.name || '');
  };

  const saveRename = () => {
    if (editingSessionId && editingName.trim() && onRenameSession) {
      onRenameSession(editingSessionId, editingName.trim());
    }
    setEditingSessionId(null);
    setEditingName('');
  };

  const cancelRename = () => {
    setEditingSessionId(null);
    setEditingName('');
  };

  // Simple helper to get files for current session
  const getSessionFiles = (sid: string) => {
    // Use session files from props if available, otherwise fall back to message parsing for BOG files
    const sessionMsgs = messages.filter(m => !m.sessionId || m.sessionId === sid);
    
    // Get stored files from session data
    const storedFiles = sid === sessionId ? sessionFiles : [];
    
    // Extract BOG files from messages
    const bogFiles = sessionMsgs
      .filter(m => {
        const meta = m.metadata;
        return (meta?.downloadUrl || meta?.bogFilePath) && 
               (meta?.fileName?.includes('.json') || meta?.fileName?.includes('BOG') || 
                meta?.fileName?.includes('.bog') || m.messageType === 'artifact');
      })
      .map((m) => {
        const meta = m.metadata!;
        let fileName = meta.fileName || meta.bogFilePath || 'BOG.json';
        if (fileName.includes('/')) {
          fileName = fileName.split('/').pop() || fileName;
        }
        return {
          id: m.id,
          name: fileName,
          url: meta.downloadUrl || meta.bogFilePath,
          messageId: m.id
        };
      });
    
    return { 
      uploaded: [], // No longer needed
      stored: storedFiles.map(f => ({
        id: f.file_id,
        name: f.filename,
        size: f.file_size,
        type: f.file_type,
        previewUrl: f.preview_url
      })),
      bog: bogFiles 
    };
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflow: 'hidden',
      fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
      fontSize: '13px',
      color: '#3F3F4B',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px',
        background: '#FFFFFF',
        borderBottom: '2px solid #3F3F4B',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '8px',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <Database size={16} style={{ color: '#6B7280' }} />
          <div style={{ 
            fontWeight: 700, 
            fontSize: '12px',
            color: '#3F3F4B',
            textTransform: 'uppercase',
            letterSpacing: '0.08em' 
          }}>
            CHAT SESSIONS
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={onCreateSession}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: '#569BFF',
              color: '#FFFFFF',
              border: '2px solid #3F3F4B',
              borderRadius: '8px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 4px 0 0 #3F3F4B';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            + New
          </button>
          
          {onClearAllSessions && sessions.length > 1 && (
            <button
              onClick={onClearAllSessions}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                background: '#FF6B6B',
                color: '#FFFFFF',
                border: '2px solid #3F3F4B',
                borderRadius: '8px',
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 4px 0 0 #3F3F4B';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              Clear All
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div style={{ 
        flex: 1, 
        overflow: 'auto', 
        padding: '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        {/* Sessions List */}

        {sessions.map((session) => {
          const isActive = session.id === sessionId;
          const isEditing = editingSessionId === session.id;
          const isExpanded = expandedSections.has(`session-${session.id}`);
          
          // Get files specific to this session
          const { stored: storedFiles, bog: bogFiles } = getSessionFiles(session.id);
          const totalFileCount = storedFiles.length;
          
          const messageCount = messages.filter(m => !m.sessionId || m.sessionId === session.id).length;
          const hasAnalysis = currentAnalysis && session.id === sessionId;

          return (
            <div 
              key={session.id}
              style={{
                background: '#FFFFFF',
                border: isActive ? '2px solid #569BFF' : '2px solid #E5E7EB',
                borderRadius: '10px',
                overflow: 'hidden',
                transition: 'all 0.2s ease',
                boxShadow: isActive ? '2px 2px 0 0 rgba(86, 155, 255, 0.2)' : 'none',
              }}
            >
              {/* Session Card Header */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '10px 12px',
                  background: isActive ? 'linear-gradient(to right, #F0F9FF, #E6F3FE)' : '#FFFFFF',
                  cursor: 'pointer',
                  borderBottom: isExpanded ? '1px solid #E5E7EB' : 'none',
                }}
                onClick={() => !isEditing && onSwitchSession(session.id)}
              >
                <div 
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleSection(`session-${session.id}`);
                  }}
                  style={{ marginRight: '8px', cursor: 'pointer' }}
                >
                  {isExpanded ? 
                    <ChevronDown size={14} style={{ color: '#6B7280' }} /> : 
                    <ChevronRight size={14} style={{ color: '#6B7280' }} />
                  }
                </div>
                <MessageSquare size={14} style={{ color: isActive ? '#569BFF' : '#6B7280', marginRight: '8px' }} />
                {isEditing ? (
                  <>
                    <input
                      type="text"
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && saveRename()}
                      onClick={(e) => e.stopPropagation()}
                      style={{
                        flex: 1,
                        padding: '4px 8px',
                        border: '2px solid #569BFF',
                        borderRadius: '6px',
                        fontSize: '13px',
                        fontWeight: 500,
                        background: '#ffffff',
                        outline: 'none',
                      }}
                      autoFocus
                    />
                    <Save
                      size={14}
                      onClick={(e) => {
                        e.stopPropagation();
                        saveRename();
                      }}
                      style={{ 
                        marginLeft: '6px', 
                        cursor: 'pointer', 
                        color: '#10b981' 
                      }}
                    />
                    <X
                      size={14}
                      onClick={(e) => {
                        e.stopPropagation();
                        cancelRename();
                      }}
                      style={{ 
                        marginLeft: '4px', 
                        cursor: 'pointer', 
                        color: '#ef4444' 
                      }}
                    />
                  </>
                ) : (
                  <>
                    <div style={{ flex: 1 }}>
                      <div style={{
                        color: isActive ? '#3F3F4B' : '#6B7280',
                        fontWeight: isActive ? 600 : 500,
                        fontSize: '13px',
                        marginBottom: '2px',
                      }}>
                        {session.name || 'Untitled Session'}
                      </div>
                      <div style={{ 
                        display: 'flex', 
                        gap: '12px',
                        fontSize: '11px',
                        color: '#9CA3AF'
                      }}>
                        {messageCount > 0 && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <MessageSquare size={10} />
                            {messageCount}
                          </span>
                        )}
                        {totalFileCount > 0 && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <FileText size={10} />
                            {totalFileCount}
                          </span>
                        )}
                        {hasAnalysis && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <BarChart3 size={10} />
                            Analysis
                          </span>
                        )}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '4px' }}>
                      <Edit3
                        size={14}
                        onClick={(e) => {
                          e.stopPropagation();
                          startRename(session);
                        }}
                        style={{ 
                          cursor: 'pointer', 
                          color: '#6B7280',
                          opacity: 0.7,
                          transition: 'opacity 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                        onMouseLeave={(e) => e.currentTarget.style.opacity = '0.7'}
                      />
                      <Trash2
                        size={14}
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteSession(session.id);
                        }}
                        style={{ 
                          cursor: 'pointer', 
                          color: '#EF4444',
                          opacity: 0.7,
                          transition: 'opacity 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                        onMouseLeave={(e) => e.currentTarget.style.opacity = '0.7'}
                      />
                    </div>
                  </>
                )}
              </div>

              {/* Expandable Content - Only show for the specific expanded session */}
              {isExpanded && (
                <div style={{ 
                  padding: '12px',
                  background: '#FAFBFC',
                  borderTop: '1px solid #E5E7EB'
                }}>
                  {/* Session Info */}
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center',
                    gap: '4px',
                    marginBottom: '12px',
                    fontSize: '11px',
                    color: '#6B7280'
                  }}>
                    <Clock size={12} />
                    <span>
                      Created: {new Date(session.createdAt).toLocaleDateString()}
                    </span>
                  </div>

                  {/* Files Section - Stored files from postgres */}
                  {storedFiles.length > 0 && (
                    <div style={{ marginBottom: '12px' }}>
                      <div style={{ 
                        fontSize: '11px', 
                        color: '#3F3F4B', 
                        fontWeight: 600,
                        marginBottom: '8px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}>
                        <FileCode size={12} />
                        Files ({storedFiles.length})
                      </div>
                      <div style={{ 
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px'
                      }}>
                        {storedFiles.map((file) => (
                          <div
                            key={file.id}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              padding: '6px 8px',
                              background: '#FFFFFF',
                              border: '1px solid #E5E7EB',
                              borderRadius: '6px',
                              fontSize: '12px',
                              color: '#6B7280',
                              transition: 'all 0.2s ease',
                              cursor: 'pointer',
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.borderColor = '#569BFF';
                              e.currentTarget.style.background = '#F0F9FF';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.borderColor = '#E5E7EB';
                              e.currentTarget.style.background = '#FFFFFF';
                            }}
                            onClick={() => {
                              setViewerFile({ 
                                name: file.name, 
                                url: file.previewUrl,
                                file_id: file.id,
                                file_size: file.size,
                                mime_type: file.type,
                                state: 'complete'
                              });
                              setViewerOpen(true);
                            }}
                          >
                            <FileText size={12} style={{ color: '#569BFF', marginRight: '6px' }} />
                            <span style={{ flex: 1, fontWeight: 500 }}>{file.name}</span>
                            <Eye 
                              size={12} 
                              style={{ color: '#6B7280', cursor: 'pointer' }} 
                              onClick={(e) => {
                                e.stopPropagation();
                                setViewerFile({ 
                                  name: file.name, 
                                  url: file.previewUrl,
                                  file_id: file.id,
                                  file_size: file.size,
                                  mime_type: file.type,
                                  state: 'complete'
                                });
                                setViewerOpen(true);
                              }}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Generated BOG Files */}
                  {bogFiles.length > 0 && (
                    <div>
                      <div style={{ 
                        fontSize: '11px', 
                        color: '#3F3F4B', 
                        fontWeight: 600,
                        marginBottom: '8px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}>
                        <BarChart3 size={12} />
                        Generated BOG Files
                      </div>
                      <div style={{ 
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px'
                      }}>
                        {bogFiles.map((file) => (
                          <div
                            key={file.id}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              padding: '6px 8px',
                              background: 'linear-gradient(to right, #F0FDF4, #DCFCE7)',
                              border: '1px solid #10B981',
                              borderRadius: '6px',
                              fontSize: '12px',
                              color: '#065F46',
                              fontWeight: 500,
                              cursor: 'pointer',
                              transition: 'all 0.2s ease',
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.transform = 'translateX(4px)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.transform = 'translateX(0)';
                            }}
                            onClick={() => window.open(file.url, '_blank')}
                          >
                            <FileCode size={12} style={{ color: '#10B981', marginRight: '6px' }} />
                            <span style={{ flex: 1 }}>{file.name}</span>
                            <Download
                              size={12}
                              style={{ 
                                cursor: 'pointer', 
                                color: '#10B981'
                              }}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
        
        {/* Analysis Section - Show when analysis exists for current session */}
        {currentAnalysis && sessionId && (
          <div style={{
            marginTop: '12px',
            background: '#FFFFFF',
            border: '2px solid #10B981',
            borderRadius: '10px',
            overflow: 'hidden',
          }}>
            <div
            onClick={() => toggleSection('analysis')}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '10px 12px',
              background: 'linear-gradient(to right, #F0FDF4, #DCFCE7)',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            {expandedSections.has('analysis') ? 
              <ChevronDown size={14} style={{ color: '#065F46' }} /> : 
              <ChevronRight size={14} style={{ color: '#065F46' }} />
            }
            <BarChart3 size={14} style={{ marginLeft: '8px', color: '#10B981' }} />
            <span style={{ 
              flex: 1, 
              marginLeft: '8px', 
              fontWeight: 600,
              fontSize: '13px',
              color: '#065F46'
            }}>
              Analysis Results
            </span>
          </div>

          {expandedSections.has('analysis') && (
            <div style={{ 
              padding: '12px',
              background: '#FAFBFC',
              borderTop: '1px solid #10B981'
            }}>
              <div style={{ marginBottom: '12px' }}>
                <div style={{ 
                  fontWeight: 600, 
                  fontSize: '12px',
                  color: '#065F46',
                  marginBottom: '8px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em'
                }}>
                  I/O Points Summary
                </div>
                <div style={{ 
                  display: 'flex',
                  gap: '12px',
                  flexWrap: 'wrap'
                }}>
                  <div style={{
                    flex: 1,
                    minWidth: '100px',
                    padding: '8px',
                    background: '#FFFFFF',
                    border: '1px solid #E5E7EB',
                    borderRadius: '6px',
                    textAlign: 'center'
                  }}>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#569BFF' }}>
                      {currentAnalysis.inputs?.length || 0}
                    </div>
                    <div style={{ fontSize: '11px', color: '#6B7280', marginTop: '2px' }}>Inputs</div>
                  </div>
                  <div style={{
                    flex: 1,
                    minWidth: '100px',
                    padding: '8px',
                    background: '#FFFFFF',
                    border: '1px solid #E5E7EB',
                    borderRadius: '6px',
                    textAlign: 'center'
                  }}>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#10B981' }}>
                      {currentAnalysis.outputs?.length || 0}
                    </div>
                    <div style={{ fontSize: '11px', color: '#6B7280', marginTop: '2px' }}>Outputs</div>
                  </div>
                </div>
              </div>
              {currentAnalysis.blocks && currentAnalysis.blocks.length > 0 && (
                <div>
                  <div style={{ 
                    fontWeight: 600, 
                    fontSize: '12px',
                    color: '#065F46',
                    marginBottom: '8px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em'
                  }}>
                    Logic Blocks: {currentAnalysis.blocks.length}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
      </div>
      {/* File Viewer Modal */}
      <FileViewerModal
        isOpen={viewerOpen}
        file={viewerFile}
        onClose={() => setViewerOpen(false)}
      />
    </div>
  );
};

export default ProjectNavigator;
