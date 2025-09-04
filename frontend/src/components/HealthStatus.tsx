import React, { useState, useEffect } from 'react';
import { Activity, Database, Server, Cpu, AlertCircle, CheckCircle } from 'lucide-react';

interface ServiceStatus {
  name: string;
  status: 'checking' | 'online' | 'offline' | 'error';
  message?: string;
  icon: React.ReactNode;
}

const HealthStatus: React.FC = () => {
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: 'API', status: 'checking', icon: <Server size={14} /> },
    { name: 'Database', status: 'checking', icon: <Database size={14} /> },
    { name: 'n8n', status: 'checking', icon: <Cpu size={14} /> },
    { name: 'WebSocket', status: 'checking', icon: <Activity size={14} /> },
  ]);
  const [isExpanded, setIsExpanded] = useState(false);

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
  
  const allOnline = services.every(s => s.status === 'online');
  const hasIssues = services.some(s => s.status === 'offline' || s.status === 'error');
  
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
        <span style={{ 
          fontSize: 10,
          color: '#9ca3af',
          marginLeft: 'auto'
        }}>
          {isExpanded ? '▲' : '▼'}
        </span>
      </div>
      
      {isExpanded && (
        <div style={{ padding: '8px 12px' }}>
          {services.map((service, index) => (
            <div 
              key={index}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 0',
                borderBottom: index < services.length - 1 ? '1px solid #f3f4f6' : 'none'
              }}
            >
              <span style={{ color: getStatusColor(service.status) }}>
                {service.icon}
              </span>
              <span style={{ fontSize: 12, color: '#374151', flex: 1 }}>
                {service.name}
              </span>
              {/* Quick links */}
              {service.name === 'API' && (
                <a href={(window as any).RUNTIME_CONFIG?.API_URL?.replace(/\/$/, '') + '/docs'} target="_blank" rel="noreferrer" style={{ fontSize: 10, color: '#3b82f6' }}>Docs</a>
              )}
              {service.name === 'n8n' && (
                <a href={(window as any).RUNTIME_CONFIG?.N8N_URL || 'http://localhost:5678'} target="_blank" rel="noreferrer" style={{ fontSize: 10, color: '#3b82f6' }}>Open</a>
              )}
              {getStatusIcon(service.status)}
              <span style={{ 
                fontSize: 10, 
                color: getStatusColor(service.status),
                fontWeight: 500
              }}>
                {service.status === 'checking' ? '...' : service.status.toUpperCase()}
              </span>
            </div>
          ))}
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
