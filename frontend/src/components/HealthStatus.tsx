import React, { useState, useEffect } from 'react';
import { Activity, Database, Server, Cpu, AlertCircle, CheckCircle, ExternalLink } from 'lucide-react';

interface ServiceStatus {
  name: string;
  status: 'checking' | 'online' | 'offline' | 'error';
  message?: string;
  icon: React.ReactNode;
}

interface HealthData {
  overall_status: string;
  services: Record<string, {
    healthy: boolean;
    status: string;
    message?: string;
    recommendation?: string;
  }>;
  issues: any[];
  recommendations: string[];
  system_info?: any;
}

interface AuditRequest {
  reqId: string;
  method: string;
  path: string;
  status: number;
  duration: number;
  timestamp: number;
}

const HealthStatus: React.FC = () => {
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: 'API', status: 'checking', icon: <Server size={14} /> },
    { name: 'Database', status: 'checking', icon: <Database size={14} /> },
    { name: 'n8n', status: 'checking', icon: <Cpu size={14} /> },
    { name: 'WebSocket', status: 'checking', icon: <Activity size={14} /> },
  ]);
  const [isExpanded, setIsExpanded] = useState(false);
  const [healthData, setHealthData] = useState<HealthData | null>(null);
  const [systemMetrics, setSystemMetrics] = useState<any>(null);
  const [recentRequests, setRecentRequests] = useState<AuditRequest[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Health WebSocket connection
  useEffect(() => {
    const cfg = (window as any).RUNTIME_CONFIG || {};
    const apiBase = cfg.API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8000';
    const wsUrl = apiBase.replace(/^http/, 'ws') + '/ws/health';
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => setWsConnected(true);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'health' && data.data) {
          setSystemMetrics(data.data);
        } else if (data.type === 'audit' && data.data) {
          setRecentRequests(prev => [...prev.slice(-19), data.data]);
        }
      } catch (e) {
        console.error('Failed to parse health message:', e);
      }
    };
    ws.onclose = () => setWsConnected(false);
    
    return () => ws.close();
  }, []);

  useEffect(() => {
    const cfg = (window as any).RUNTIME_CONFIG || {};
    const apiBase = cfg.API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8000';
    const n8nBase = cfg.N8N_URL || process.env.REACT_APP_N8N_URL || 'http://localhost:5678';

    const checkServices = async () => {
      const newStatuses = [...services];
      // API + DB
      try {
        const apiResp = await fetch(`${apiBase}/api/health`, { cache: 'no-store' });
        if (apiResp.ok) {
          const data = await apiResp.json();
          newStatuses[0] = { ...newStatuses[0], status: 'online', message: 'API Connected' };
          newStatuses[1] = { ...newStatuses[1], status: data.database ? 'online' : 'offline', message: data.database ? 'PostgreSQL Connected' : 'Database Offline' };
        } else {
          newStatuses[0] = { ...newStatuses[0], status: 'error', message: `API ${apiResp.status}` };
          newStatuses[1] = { ...newStatuses[1], status: 'offline', message: 'Database Unknown' };
        }
      } catch (e) {
        newStatuses[0] = { ...newStatuses[0], status: 'offline', message: 'API Unreachable' };
        newStatuses[1] = { ...newStatuses[1], status: 'offline', message: 'Database Unknown' };
      }

      // n8n reachability: treat 404 as OK (GET to POST-only webhook)
      try {
        const resp = await fetch(`${n8nBase}/webhook/pybog-analyze`, { method: 'GET' });
        if (resp.ok || [401,403,404].includes(resp.status)) {
          newStatuses[2] = { ...newStatuses[2], status: 'online', message: 'n8n Reachable' };
        } else {
          newStatuses[2] = { ...newStatuses[2], status: 'error', message: `n8n ${resp.status}` };
        }
      } catch (e) {
        newStatuses[2] = { ...newStatuses[2], status: 'offline', message: 'n8n Unreachable' };
      }

      // WebSocket check based on API URL
      try {
        const wsBase = apiBase.replace(/^http/i, 'ws');
        const ws = new WebSocket(`${wsBase}/ws/test`);
        ws.onopen = () => {
          newStatuses[3] = { ...newStatuses[3], status: 'online', message: 'WebSocket Connected' };
          ws.close();
          setServices([...newStatuses]);
        };
        ws.onerror = () => {
          newStatuses[3] = { ...newStatuses[3], status: 'offline', message: 'WebSocket Error' };
          setServices([...newStatuses]);
        };
      } catch (e) {
        newStatuses[3] = { ...newStatuses[3], status: 'offline', message: 'WebSocket Failed' };
      }

      setServices(newStatuses);
    };

    checkServices();
    const interval = setInterval(checkServices, 30000);
    return () => clearInterval(interval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  
  const getStatusColor = (status: ServiceStatus['status']) => {
    switch (status) {
      case 'online': return '#10b981';
      case 'offline': return '#ef4444';
      case 'error': return '#f59e0b';
      default: return '#6b7280';
    }
  };
  
  const getStatusIcon = (status: ServiceStatus['status']) => {
    switch (status) {
      case 'online': return <CheckCircle size={12} />;
      case 'offline': case 'error': return <AlertCircle size={12} />;
      default: return <div className="spinner" style={{ width: 12, height: 12 }} />;
    }
  };
  
  const getHealthColor = (percentage: number) => {
    if (percentage > 80) return '#ef4444';
    if (percentage > 60) return '#f59e0b';
    return '#10b981';
  };

  const formatBytes = (bytes: number) => {
    const gb = bytes / (1024 ** 3);
    return `${gb.toFixed(1)}GB`;
  };

  const openExternalService = (service: string) => {
    const urls = {
      n8n: (window as any).RUNTIME_CONFIG?.N8N_URL || 'http://localhost:5678',
      docs: `${(window as any).RUNTIME_CONFIG?.API_URL || 'http://localhost:8000'}/docs`,
      pgadmin: 'http://localhost:5050'
    };
    window.open(urls[service as keyof typeof urls], '_blank');
  };
  
  const allOnline = services.every(s => s.status === 'online');
  const hasIssues = services.some(s => s.status === 'offline' || s.status === 'error');
  
  // Enhanced health check
  useEffect(() => {
    const checkDetailedHealth = async () => {
      const cfg = (window as any).RUNTIME_CONFIG || {};
      const apiBase = cfg.API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8000';
      
      try {
        const response = await fetch(`${apiBase}/api/health`, { cache: 'no-store' });
        if (response.ok) {
          const health = await response.json();
          setHealthData(health);
        }
      } catch (e) {
        setHealthData({
          overall_status: 'error',
          services: {},
          issues: [{ message: 'Cannot reach API server' }],
          recommendations: ['Start the API server: docker-compose up api']
        });
      }
    };
    
    checkDetailedHealth();
    const interval = setInterval(checkDetailedHealth, 15000);
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div style={{
      position: 'fixed',
      top: 16,
      right: 16,
      zIndex: 1000,
      background: 'white',
      borderRadius: 8,
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      border: '1px solid #e5e7eb',
      minWidth: isExpanded ? 250 : 120,
      transition: 'all 0.3s ease',
    }}>
      <div 
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          padding: '8px 12px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          borderBottom: isExpanded ? '1px solid #e5e7eb' : 'none',
        }}
      >
        <div style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: allOnline ? '#10b981' : hasIssues ? '#ef4444' : '#f59e0b',
          animation: hasIssues ? 'pulse 2s infinite' : 'none'
        }} />
        <span style={{ 
          fontSize: 12, 
          fontWeight: 600,
          color: '#374151'
        }}>
          System {allOnline ? 'Online' : hasIssues ? 'Issues' : 'Checking'}
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <button 
            onClick={(e) => { e.stopPropagation(); openExternalService('n8n'); }}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#6b7280',
              cursor: 'pointer',
              padding: 4,
            }}
            title="Open n8n"
          >
            <ExternalLink size={12} />
          </button>
          <span style={{ fontSize: 10, color: '#9ca3af' }}>
            {isExpanded ? '▲' : '▼'}
          </span>
        </div>
      </div>
      
      {isExpanded && (
        <div style={{ padding: 12, fontSize: 12 }}>
          {/* Issues and Recommendations */}
          {healthData && (healthData.issues.length > 0 || healthData.recommendations.length > 0) && (
            <div style={{ marginBottom: 12 }}>
              <h4 style={{ margin: '0 0 8px 0', fontWeight: 600, color: '#dc2626' }}>
                ⚠️ Issues Detected
              </h4>
              {healthData.issues.map((issue, idx) => (
                <div key={idx} style={{ 
                  background: '#fef2f2', 
                  border: '1px solid #fecaca', 
                  borderRadius: 4, 
                  padding: 8, 
                  marginBottom: 4,
                  fontSize: 11
                }}>
                  <div style={{ fontWeight: 600, color: '#dc2626' }}>{issue.status || 'Issue'}</div>
                  <div style={{ color: '#7f1d1d' }}>{issue.message}</div>
                  {issue.recommendation && (
                    <div style={{ 
                      marginTop: 4, 
                      padding: 4, 
                      background: '#f0f9ff', 
                      border: '1px solid #bae6fd',
                      borderRadius: 2,
                      color: '#0c4a6e'
                    }}>
                      💡 {issue.recommendation}
                    </div>
                  )}
                </div>
              ))}
              
              {healthData.recommendations.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <h5 style={{ margin: '0 0 4px 0', fontWeight: 600, color: '#0891b2' }}>
                    Recommended Actions:
                  </h5>
                  {healthData.recommendations.map((rec, idx) => (
                    <div key={idx} style={{ 
                      background: '#ecfdf5', 
                      border: '1px solid #a7f3d0', 
                      borderRadius: 4, 
                      padding: 6, 
                      marginBottom: 2,
                      fontSize: 11,
                      color: '#064e3b'
                    }}>
                      🔧 {rec}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* System Resources */}
          {systemMetrics && (
            <div style={{ marginBottom: 12 }}>
              <h4 style={{ margin: '0 0 8px 0', fontWeight: 600 }}>System Resources</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, textAlign: 'center' }}>
                <div>
                  <div style={{ color: getHealthColor(systemMetrics.system.cpu_percent), fontWeight: 600 }}>
                    {systemMetrics.system.cpu_percent.toFixed(1)}%
                  </div>
                  <div style={{ color: '#6b7280', fontSize: 10 }}>CPU</div>
                </div>
                <div>
                  <div style={{ color: getHealthColor(systemMetrics.system.memory_percent), fontWeight: 600 }}>
                    {systemMetrics.system.memory_percent.toFixed(1)}%
                  </div>
                  <div style={{ color: '#6b7280', fontSize: 10 }}>Memory</div>
                </div>
                <div>
                  <div style={{ color: getHealthColor(systemMetrics.system.disk_percent), fontWeight: 600 }}>
                    {systemMetrics.system.disk_percent.toFixed(1)}%
                  </div>
                  <div style={{ color: '#6b7280', fontSize: 10 }}>Disk</div>
                </div>
              </div>
            </div>
          )}

          {/* Containers */}
          {systemMetrics?.containers && Object.keys(systemMetrics.containers).length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <h4 style={{ margin: '0 0 8px 0', fontWeight: 600 }}>Containers</h4>
              {Object.entries(systemMetrics.containers).map(([name, container]: [string, any]) => (
                <div key={name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontFamily: 'monospace', fontSize: 11 }}>
                    {name.replace('pybog-', '')}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      padding: '2px 6px',
                      borderRadius: 4,
                      fontSize: 10,
                      background: container.status === 'running' ? '#dcfce7' : '#fee2e2',
                      color: container.status === 'running' ? '#16a34a' : '#dc2626'
                    }}>
                      {container.status}
                    </span>
                    <span style={{ color: '#6b7280', fontSize: 10 }}>
                      {formatBytes(container.memory_usage)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Recent Requests */}
          {recentRequests.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <h4 style={{ margin: '0 0 8px 0', fontWeight: 600 }}>Recent Requests</h4>
              <div style={{ maxHeight: 100, overflow: 'auto' }}>
                {recentRequests.slice(-5).map((req, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 2 }}>
                    <span style={{ fontFamily: 'monospace' }}>{req.method} {req.path}</span>
                    <span style={{ color: req.status >= 400 ? '#dc2626' : '#16a34a' }}>
                      {req.status} ({req.duration}ms)
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Service Links */}
          <div style={{ display: 'flex', gap: 4 }}>
            <button 
              onClick={() => openExternalService('n8n')}
              style={{
                flex: 1,
                padding: 6,
                fontSize: 10,
                background: '#dbeafe',
                color: '#1d4ed8',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer'
              }}
            >
              n8n
            </button>
            <button 
              onClick={() => openExternalService('docs')}
              style={{
                flex: 1,
                padding: 6,
                fontSize: 10,
                background: '#dcfce7',
                color: '#16a34a',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer'
              }}
            >
              API Docs
            </button>
            <button 
              onClick={() => openExternalService('pgadmin')}
              style={{
                flex: 1,
                padding: 6,
                fontSize: 10,
                background: '#f3e8ff',
                color: '#7c3aed',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer'
              }}
            >
              pgAdmin
            </button>
          </div>
        </div>
      )}
      
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        .spinner {
          border: 2px solid #f3f4f6;
          border-top: 2px solid #3b82f6;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default HealthStatus;
