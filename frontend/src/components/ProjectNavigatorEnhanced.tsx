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
  Eye
} from 'lucide-react';

interface Session {
  id: string;
  name: string;
  createdAt: Date | string;
}

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  sessionId?: string;
  files?: File[];
  metadata?: {
    downloadUrl?: string;
    fileName?: string;
  };
  timestamp?: Date;
}

interface ProjectNavigatorProps {
  sessionId: string;
  sessions: Session[];
  currentAnalysis?: any;
  messages: Message[];
  onCreateSession: () => void;
  onSwitchSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onRenameSession?: (id: string, name: string) => void;
}

const ProjectNavigator: React.FC<ProjectNavigatorProps> = ({
  sessionId,
  sessions,
  currentAnalysis,
  messages,
  onCreateSession,
  onSwitchSession,
  onDeleteSession,
  onRenameSession,
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['sessions', `session-${sessionId}`])
  );
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

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
    setEditingName(session.name);
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

  // Filter messages and files for current session
  const sessionMessages = messages.filter(m => 
    !m.sessionId || m.sessionId === sessionId
  );

  // Extract uploaded files from session messages
  const uploadedFiles = sessionMessages
    .filter(m => m.files && m.files.length > 0)
    .flatMap((m, msgIdx) => 
      m.files!.map((file, fileIdx) => ({
        id: `file-${m.id}-${fileIdx}`,
        name: file.name,
        messageId: m.id,
        size: file.size,
        type: file.type
      }))
    );

  // Extract BOG files from session messages
  const bogFiles = sessionMessages
    .filter(m => m.metadata?.downloadUrl)
    .map((m, idx) => ({
      id: m.id,
      name: m.metadata?.fileName || `BOG_${idx + 1}.json`,
      url: m.metadata?.downloadUrl,
      messageId: m.id
    }));

  return (
    <div style={{
      width: '300px',
      height: '100%',
      background: '#fafbfc',
      borderRight: '1px solid #d1d5db',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
      fontSize: '14px',
      color: '#1f2937',
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 16px',
        background: '#ffffff',
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}>
        <Database size={18} style={{ color: '#7c3aed' }} />
        <div style={{ 
          flex: 1, 
          fontWeight: 600, 
          fontSize: '15px',
          color: '#111827',
          letterSpacing: '-0.025em' 
        }}>
          Project Navigator
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {/* Sessions Section */}
        <div key="sessions-section">
          <div
            onClick={() => toggleSection('sessions')}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '10px 14px',
              background: '#ffffff',
              borderBottom: '1px solid #e5e7eb',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            {expandedSections.has('sessions') ? 
              <ChevronDown size={16} style={{ color: '#6b7280' }} /> : 
              <ChevronRight size={16} style={{ color: '#6b7280' }} />
            }
            <FolderOpen size={16} style={{ marginLeft: '6px', color: '#7c3aed' }} />
            <span style={{ 
              flex: 1, 
              marginLeft: '10px', 
              fontWeight: 500,
              fontSize: '14px',
              color: '#374151'
            }}>
              Chat Sessions ({sessions.length})
            </span>
            <Plus
              size={16}
              onClick={(e) => {
                e.stopPropagation();
                onCreateSession();
              }}
              style={{ 
                cursor: 'pointer', 
                color: '#10b981',
                padding: '2px',
                borderRadius: '4px',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            />
          </div>

          {expandedSections.has('sessions') && (
            <div style={{ background: '#fcfcfd' }}>
              {sessions.map((session) => {
                const isActive = session.id === sessionId;
                const isEditing = editingSessionId === session.id;
                const sessionFiles = messages.filter(m => 
                  !m.sessionId || m.sessionId === session.id
                ).filter(m => m.files && m.files.length > 0).flatMap(m => m.files!);

                return (
                  <div key={session.id}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '8px 28px',
                        background: isActive ? '#f3f0ff' : 'transparent',
                        borderLeft: isActive ? '3px solid #7c3aed' : '3px solid transparent',
                        cursor: 'pointer',
                        transition: 'background-color 0.15s',
                      }}
                      onClick={() => !isEditing && onSwitchSession(session.id)}
                      onMouseEnter={(e) => {
                        if (!isActive && !isEditing) {
                          e.currentTarget.style.backgroundColor = '#f9fafb';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive && !isEditing) {
                          e.currentTarget.style.backgroundColor = 'transparent';
                        }
                      }}
                    >
                      <Folder size={14} style={{ color: isActive ? '#7c3aed' : '#9ca3af' }} />
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
                              marginLeft: '8px',
                              padding: '3px 6px',
                              border: '1px solid #7c3aed',
                              borderRadius: '4px',
                              fontSize: '13px',
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
                          <span style={{
                            flex: 1,
                            marginLeft: '10px',
                            color: isActive ? '#581c87' : '#4b5563',
                            fontWeight: isActive ? 500 : 400,
                            fontSize: '13px',
                          }}>
                            {session.name}
                          </span>
                          <span style={{
                            fontSize: '11px',
                            color: '#9ca3af',
                            marginRight: '8px',
                          }}>
                            {sessionFiles.length > 0 && `${sessionFiles.length} files`}
                          </span>
                          <Edit3
                            size={14}
                            onClick={(e) => {
                              e.stopPropagation();
                              startRename(session);
                            }}
                            style={{ 
                              marginRight: '6px', 
                              cursor: 'pointer', 
                              color: '#6b7280',
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
                              color: '#ef4444',
                              opacity: 0.7,
                              transition: 'opacity 0.2s'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                            onMouseLeave={(e) => e.currentTarget.style.opacity = '0.7'}
                          />
                        </>
                      )}
                    </div>

                    {/* Show files under active session */}
                    {isActive && expandedSections.has(`session-${session.id}`) && (
                      <div style={{ background: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
                        {/* Uploaded Files subsection */}
                        {uploadedFiles.length > 0 && (
                          <div style={{ paddingLeft: '44px', paddingTop: '4px' }}>
                            <div style={{ 
                              fontSize: '11px', 
                              color: '#6b7280', 
                              fontWeight: 500,
                              marginBottom: '4px',
                              textTransform: 'uppercase',
                              letterSpacing: '0.05em'
                            }}>
                              Uploaded Files
                            </div>
                            {uploadedFiles.map((file) => (
                              <div
                                key={file.id}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  padding: '4px 0',
                                  cursor: 'pointer',
                                  fontSize: '12px',
                                  color: '#4b5563',
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.color = '#1f2937'}
                                onMouseLeave={(e) => e.currentTarget.style.color = '#4b5563'}
                              >
                                <FileText size={12} style={{ color: '#9ca3af', marginRight: '6px' }} />
                                <span style={{ flex: 1 }}>{file.name}</span>
                                <Eye size={12} style={{ color: '#6b7280', marginRight: '4px' }} />
                              </div>
                            ))}
                          </div>
                        )}

                        {/* BOG Files subsection */}
                        {bogFiles.length > 0 && (
                          <div style={{ paddingLeft: '44px', paddingTop: '8px', paddingBottom: '8px' }}>
                            <div style={{ 
                              fontSize: '11px', 
                              color: '#6b7280', 
                              fontWeight: 500,
                              marginBottom: '4px',
                              textTransform: 'uppercase',
                              letterSpacing: '0.05em'
                            }}>
                              Generated BOG Files
                            </div>
                            {bogFiles.map((file) => (
                              <div
                                key={file.id}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  padding: '4px 0',
                                  cursor: 'pointer',
                                  fontSize: '12px',
                                  color: '#4b5563',
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.color = '#1f2937'}
                                onMouseLeave={(e) => e.currentTarget.style.color = '#4b5563'}
                              >
                                <FileText size={12} style={{ color: '#10b981', marginRight: '6px' }} />
                                <span style={{ flex: 1 }}>{file.name}</span>
                                <Download
                                  size={12}
                                  onClick={() => window.open(file.url, '_blank')}
                                  style={{ 
                                    cursor: 'pointer', 
                                    color: '#3b82f6',
                                    marginRight: '4px'
                                  }}
                                />
                              </div>
                            ))}
                          </div>
                        )}

                        {uploadedFiles.length === 0 && bogFiles.length === 0 && (
                          <div style={{
                            paddingLeft: '44px',
                            padding: '8px 44px',
                            fontSize: '12px',
                            color: '#9ca3af',
                            fontStyle: 'italic',
                          }}>
                            No files in this session
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Analysis Section - Only show for current session */}
        {currentAnalysis && sessionId && (
          <>
            <div
              onClick={() => toggleSection('analysis')}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '10px 14px',
                background: '#ffffff',
                borderBottom: '1px solid #e5e7eb',
                borderTop: '1px solid #e5e7eb',
                marginTop: '1px',
                cursor: 'pointer',
                userSelect: 'none',
              }}
            >
              {expandedSections.has('analysis') ? 
                <ChevronDown size={16} style={{ color: '#6b7280' }} /> : 
                <ChevronRight size={16} style={{ color: '#6b7280' }} />
              }
              <Database size={16} style={{ marginLeft: '6px', color: '#10b981' }} />
              <span style={{ 
                flex: 1, 
                marginLeft: '10px', 
                fontWeight: 500,
                fontSize: '14px',
                color: '#374151'
              }}>
                Analysis Results
              </span>
            </div>

                {expandedSections.has('analysis') && (
              <div style={{ 
                background: '#fcfcfd', 
                padding: '12px 20px', 
                fontSize: '13px',
                color: '#4b5563'
              }}>
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ 
                    fontWeight: 600, 
                    color: '#1f2937',
                    marginBottom: '6px'
                  }}>
                    I/O Points
                  </div>
                  <div style={{ 
                    marginLeft: '16px', 
                    lineHeight: '1.5'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Input Points:</span>
                      <span style={{ fontWeight: 500, color: '#7c3aed' }}>
                        {currentAnalysis.inputs?.length || 0}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Output Points:</span>
                      <span style={{ fontWeight: 500, color: '#10b981' }}>
                        {currentAnalysis.outputs?.length || 0}
                      </span>
                    </div>
                  </div>
                </div>
                {currentAnalysis.blocks && currentAnalysis.blocks.length > 0 && (
                  <div>
                    <div style={{ 
                      fontWeight: 600, 
                      color: '#1f2937',
                      marginBottom: '6px'
                    }}>
                      Logic Blocks
                    </div>
                    <div style={{ marginLeft: '16px' }}>
                      <span>Total Blocks:</span>
                      <span style={{ 
                        marginLeft: '8px', 
                        fontWeight: 500, 
                        color: '#3b82f6' 
                      }}>
                        {currentAnalysis.blocks.length}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ProjectNavigator;
