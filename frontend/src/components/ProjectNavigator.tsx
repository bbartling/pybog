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
  Database
} from 'lucide-react';

interface Session {
  id: string;
  name: string;
  createdAt: Date | string;
}

interface ProjectNavigatorProps {
  sessionId: string;
  sessions: Session[];
  currentAnalysis?: any;
  messages: any[];
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
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['sessions']));
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

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

  // Extract uploaded files from messages
  const uploadedFiles = messages
    .filter(m => m.files && m.files.length > 0)
    .flatMap(m => m.files)
    .map((file, idx) => ({
      id: `file-${idx}`,
      name: file.name,
    }));

  // Extract BOG files
  const bogFiles = messages
    .filter(m => m.metadata?.downloadUrl)
    .map((m, idx) => ({
      id: m.id,
      name: m.metadata?.fileName || `BOG_${idx + 1}.json`,
      url: m.metadata?.downloadUrl,
    }));

  return (
    <div style={{
      width: '280px',
      height: '100%',
      background: '#f8f9fa',
      borderRight: '1px solid #e5e7eb',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: 'Segoe UI, Tahoma, sans-serif',
      fontSize: '13px',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px',
        background: '#ffffff',
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}>
        <Database size={16} style={{ color: '#7c3aed' }} />
        <div style={{ flex: 1, fontWeight: 600, color: '#374151' }}>
          Project Navigator
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {/* Sessions Section */}
        <div>
          <div
            onClick={() => toggleSection('sessions')}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '8px 12px',
              background: '#ffffff',
              borderBottom: '1px solid #e5e7eb',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            {expandedSections.has('sessions') ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            <FolderOpen size={14} style={{ marginLeft: '4px', color: '#7c3aed' }} />
            <span style={{ flex: 1, marginLeft: '8px', fontWeight: 500 }}>
              Chat Sessions ({sessions.length})
            </span>
            <Plus
              size={14}
              onClick={(e) => {
                e.stopPropagation();
                onCreateSession();
              }}
              style={{ cursor: 'pointer', color: '#10b981' }}
            />
          </div>

          {expandedSections.has('sessions') && (
            <div style={{ background: '#ffffff' }}>
              {sessions.map((session) => {
                const isActive = session.id === sessionId;
                const isEditing = editingSessionId === session.id;

                return (
                  <div
                    key={session.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '6px 24px',
                      background: isActive ? '#ede9fe' : 'transparent',
                      borderLeft: isActive ? '3px solid #7c3aed' : '3px solid transparent',
                      cursor: 'pointer',
                    }}
                    onClick={() => !isEditing && onSwitchSession(session.id)}
                  >
                    <Folder size={12} style={{ color: isActive ? '#7c3aed' : '#6b7280' }} />
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
                            padding: '2px 4px',
                            border: '1px solid #7c3aed',
                            borderRadius: '3px',
                            fontSize: '12px',
                            background: '#ffffff',
                          }}
                          autoFocus
                        />
                        <Save
                          size={12}
                          onClick={(e) => {
                            e.stopPropagation();
                            saveRename();
                          }}
                          style={{ marginLeft: '4px', cursor: 'pointer', color: '#10b981' }}
                        />
                        <X
                          size={12}
                          onClick={(e) => {
                            e.stopPropagation();
                            cancelRename();
                          }}
                          style={{ marginLeft: '4px', cursor: 'pointer', color: '#ef4444' }}
                        />
                      </>
                    ) : (
                      <>
                        <span style={{
                          flex: 1,
                          marginLeft: '8px',
                          color: isActive ? '#581c87' : '#374151',
                          fontWeight: isActive ? 500 : 400,
                        }}>
                          {session.name}
                        </span>
                        <Edit3
                          size={12}
                          onClick={(e) => {
                            e.stopPropagation();
                            startRename(session);
                          }}
                          style={{ marginRight: '4px', cursor: 'pointer', color: '#6b7280' }}
                        />
                        <Trash2
                          size={12}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (window.confirm(`Delete session "${session.name}"?`)) {
                              onDeleteSession(session.id);
                            }
                          }}
                          style={{ cursor: 'pointer', color: '#ef4444' }}
                        />
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Files Section */}
        {sessionId && (
          <>
            <div
              onClick={() => toggleSection('files')}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '8px 12px',
                background: '#ffffff',
                borderBottom: '1px solid #e5e7eb',
                borderTop: '1px solid #e5e7eb',
                marginTop: '1px',
                cursor: 'pointer',
                userSelect: 'none',
              }}
            >
              {expandedSections.has('files') ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              <Folder size={14} style={{ marginLeft: '4px' }} />
              <span style={{ flex: 1, marginLeft: '8px', fontWeight: 500 }}>
                Files ({uploadedFiles.length + bogFiles.length})
              </span>
            </div>

            {expandedSections.has('files') && (
              <div style={{ background: '#ffffff', padding: '4px 0' }}>
                {uploadedFiles.length === 0 && bogFiles.length === 0 ? (
                  <div style={{
                    padding: '8px 24px',
                    color: '#9ca3af',
                    fontStyle: 'italic',
                    fontSize: '12px',
                  }}>
                    No files uploaded
                  </div>
                ) : (
                  <>
                    {uploadedFiles.map((file) => (
                      <div
                        key={file.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          padding: '4px 24px',
                          cursor: 'pointer',
                        }}
                      >
                        <FileText size={12} style={{ color: '#6b7280' }} />
                        <span style={{ marginLeft: '8px', fontSize: '12px' }}>{file.name}</span>
                      </div>
                    ))}
                    {bogFiles.map((file) => (
                      <div
                        key={file.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          padding: '4px 24px',
                          cursor: 'pointer',
                        }}
                      >
                        <FileText size={12} style={{ color: '#10b981' }} />
                        <span style={{ flex: 1, marginLeft: '8px', fontSize: '12px' }}>{file.name}</span>
                        <Download
                          size={12}
                          onClick={() => window.open(file.url, '_blank')}
                          style={{ cursor: 'pointer', color: '#3b82f6' }}
                        />
                      </div>
                    ))}
                  </>
                )}
              </div>
            )}
          </>
        )}

        {/* Analysis Section */}
        {currentAnalysis && (
          <div
            onClick={() => toggleSection('analysis')}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '8px 12px',
              background: '#ffffff',
              borderBottom: '1px solid #e5e7eb',
              borderTop: '1px solid #e5e7eb',
              marginTop: '1px',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            {expandedSections.has('analysis') ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            <Database size={14} style={{ marginLeft: '4px', color: '#10b981' }} />
            <span style={{ flex: 1, marginLeft: '8px', fontWeight: 500 }}>
              Analysis Results
            </span>
          </div>
        )}

        {expandedSections.has('analysis') && currentAnalysis && (
          <div style={{ background: '#ffffff', padding: '8px 24px', fontSize: '12px' }}>
            <div style={{ marginBottom: '8px' }}>
              <strong>I/O Points:</strong>
              <div style={{ marginLeft: '12px', marginTop: '4px' }}>
                Inputs: {currentAnalysis.inputs?.length || 0}<br />
                Outputs: {currentAnalysis.outputs?.length || 0}
              </div>
            </div>
            {currentAnalysis.blocks && (
              <div>
                <strong>Logic Blocks:</strong> {currentAnalysis.blocks.length}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ProjectNavigator;
