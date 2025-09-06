import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Database, 
  Server, 
  Wifi, 
  WifiOff,
  CheckCircle,
  AlertCircle,
  XCircle,
  RefreshCw,
  Zap,
  HardDrive,
  ExternalLink
} from 'lucide-react';
import websocketService from '../services/websocketService';

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'warning' | 'error' | 'unknown';
  message: string;
  details?: any;
}

interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'error';
  services: {
    api: ServiceStatus;
    database: ServiceStatus;
    redis: ServiceStatus;
    n8n: ServiceStatus;
    websocket: ServiceStatus;
  };
  metrics?: {
    activeConnections: number;
    memoryUsage: string;
    cpuUsage?: number;
    uptime: string;
  };
}

interface SystemMonitorProps {
  position?: 'top' | 'bottom';
}

const SystemMonitor: React.FC<SystemMonitorProps> = ({ position = 'bottom' }) => {
  const [systemHealth, setSystemHealth] = useState<SystemHealth>({
    overall: 'healthy',
    services: {
      api: { name: 'API Server', status: 'unknown', message: 'Checking...' },
      database: { name: 'PostgreSQL', status: 'unknown', message: 'Checking...' },
      redis: { name: 'Redis Cache', status: 'unknown', message: 'Checking...' },
      n8n: { name: 'n8n Workflow', status: 'unknown', message: 'Checking...' },
      websocket: { name: 'WebSocket', status: 'unknown', message: 'Checking...' }
    }
  });
  const [isExpanded, setIsExpanded] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Check health status
  const checkHealth = async () => {
    setIsRefreshing(true);
    try {
      const response = await fetch('http://localhost:8000/api/health');
      if (response.ok) {
        const data = await response.json();
        
        // Map API response to our structure
        const services: SystemHealth['services'] = {
          api: {
            name: 'API Server',
            status: data.services?.api?.healthy ? 'healthy' : 'error',
            message: data.services?.api?.message || 'API is running',
            details: data.services?.api?.details
          },
          database: {
            name: 'PostgreSQL',
            status: data.services?.database?.healthy ? 'healthy' : 'error',
            message: data.services?.database?.message || 'Database connected',
            details: data.services?.database?.details
          },
          redis: {
            name: 'Redis Cache',
            status: data.services?.redis?.healthy ? 'healthy' : 
                   data.services?.redis ? 'warning' : 'error',
            message: data.services?.redis?.message || 'Redis operational',
            details: data.services?.redis?.details
          },
          n8n: {
            name: 'n8n Workflow',
            status: data.services?.n8n?.healthy ? 'healthy' : 'warning',
            message: data.services?.n8n?.message || 'Workflow engine ready',
            details: data.services?.n8n?.details
          },
          websocket: {
            name: 'WebSocket',
            status: websocketService.isConnected() ? 'healthy' : 'warning',
            message: websocketService.isConnected() ? 
              'Real-time connection active' : 'Not connected',
            details: { sessionId: websocketService.getCurrentSessionId() }
          }
        };

        // Calculate overall health
        const statuses = Object.values(services).map(s => s.status);
        const overall = statuses.includes('error') ? 'error' :
                       statuses.includes('warning') ? 'degraded' : 'healthy';

        setSystemHealth({
          overall,
          services,
          metrics: {
            activeConnections: data.services?.websockets?.details?.connections || 0,
            memoryUsage: data.services?.docker?.details?.memory || 'N/A',
            uptime: data.services?.docker?.details?.uptime || 'N/A'
          }
        });
      }
    } catch (error) {
      console.error('Health check failed:', error);
      setSystemHealth(prev => ({
        ...prev,
        overall: 'error',
        services: {
          ...prev.services,
          api: { name: 'API Server', status: 'error', message: 'Connection failed' }
        }
      }));
    } finally {
      setIsRefreshing(false);
      setLastUpdate(new Date());
    }
  };

  // Initial health check and periodic refresh
  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Subscribe to WebSocket health updates
  useEffect(() => {
    const unsubscribe = websocketService.on('health_update', (event) => {
      console.log('[SystemMonitor] Health update:', event.data);
      // Update health based on WebSocket data
      if (event.data) {
        checkHealth(); // Refresh on health updates
      }
    });
    return unsubscribe;
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle size={16} style={{ color: '#10b981' }} />;
      case 'warning':
        return <AlertCircle size={16} style={{ color: '#f59e0b' }} />;
      case 'error':
        return <XCircle size={16} style={{ color: '#ef4444' }} />;
      default:
        return <AlertCircle size={16} style={{ color: '#6b7280' }} />;
    }
  };

  const getOverallColor = () => {
    switch (systemHealth.overall) {
      case 'healthy':
        return '#10b981';
      case 'degraded':
        return '#f59e0b';
      case 'error':
        return '#ef4444';
      default:
        return '#6b7280';
    }
  };

  const containerStyle: React.CSSProperties = position === 'top' ? {
    position: 'fixed',
    top: '20px',
    right: '20px',
    zIndex: 1000,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  } : {
    position: 'fixed',
    bottom: '20px',
    right: '20px',
    zIndex: 1000,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  };

  return (
    <div style={containerStyle}>
      {/* Compact View */}
      <div
        style={{
          background: '#ffffff',
          borderRadius: '12px',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          cursor: 'pointer',
          minWidth: '200px',
          border: `2px solid ${getOverallColor()}`,
          transition: 'all 0.3s ease'
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <Activity size={20} style={{ color: getOverallColor() }} />
        <div style={{ flex: 1 }}>
          <div style={{ 
            fontSize: '12px', 
            color: '#6b7280',
            marginBottom: '2px'
          }}>
            System Status
          </div>
          <div style={{ 
            fontSize: '14px', 
            fontWeight: 600,
            color: getOverallColor(),
            textTransform: 'capitalize'
          }}>
            {systemHealth.overall}
          </div>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            checkHealth();
          }}
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          <RefreshCw 
            size={16} 
            style={{ 
              color: '#6b7280',
              animation: isRefreshing ? 'spin 1s linear infinite' : 'none'
            }} 
          />
        </button>
      </div>

      {/* Expanded View */}
      {isExpanded && (
        <div
          style={{
            position: 'absolute',
            ...(position === 'top' ? { top: '60px' } : { bottom: '60px' }),
            right: 0,
            background: '#ffffff',
            borderRadius: '12px',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
            padding: '20px',
            width: '360px',
            maxHeight: '400px',
            overflowY: 'auto',
            zIndex: 1001
          }}
        >
          <div style={{ marginBottom: '16px' }}>
            <h3 style={{ 
              margin: 0, 
              fontSize: '16px', 
              fontWeight: 600,
              color: '#111827',
              marginBottom: '4px'
            }}>
              System Health Monitor
            </h3>
            <div style={{ 
              fontSize: '12px', 
              color: '#6b7280' 
            }}>
              Last updated: {lastUpdate.toLocaleTimeString()}
            </div>
          </div>

          {/* Services Status */}
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ 
              fontSize: '14px', 
              fontWeight: 600,
              color: '#374151',
              marginBottom: '12px'
            }}>
              Services
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {Object.entries(systemHealth.services).map(([key, service]) => {
                // Define service URLs
                const serviceUrls: Record<string, string | undefined> = {
                  api: 'http://localhost:8000/docs',  // FastAPI docs
                  database: 'http://localhost:5050',  // pgAdmin
                  n8n: 'http://localhost:5678',
                  redis: undefined,  // No web UI for Redis by default
                  websocket: undefined  // WebSocket has no separate UI
                };
                const serviceUrl = serviceUrls[key];
                
                return (
                <div
                  key={key}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '8px 12px',
                    background: '#f9fafb',
                    borderRadius: '8px',
                    gap: '8px',
                    position: 'relative'
                  }}
                >
                  {key === 'database' && <Database size={16} style={{ color: '#6b7280' }} />}
                  {key === 'redis' && <HardDrive size={16} style={{ color: '#6b7280' }} />}
                  {key === 'api' && <Server size={16} style={{ color: '#6b7280' }} />}
                  {key === 'n8n' && <Zap size={16} style={{ color: '#6b7280' }} />}
                  {key === 'websocket' && (
                    service.status === 'healthy' ? 
                      <Wifi size={16} style={{ color: '#6b7280' }} /> :
                      <WifiOff size={16} style={{ color: '#6b7280' }} />
                  )}
                  <div style={{ flex: 1 }}>
                    <div style={{ 
                      fontSize: '13px', 
                      fontWeight: 500,
                      color: '#1f2937'
                    }}>
                      {service.name}
                    </div>
                    <div style={{ 
                      fontSize: '11px', 
                      color: '#6b7280',
                      marginTop: '2px'
                    }}>
                      {service.message}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    {getStatusIcon(service.status)}
                    {serviceUrl && (
                      <button
                        onClick={() => window.open(serviceUrl, '_blank')}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          cursor: 'pointer',
                          padding: '2px',
                          display: 'flex',
                          alignItems: 'center',
                          opacity: 0.6,
                          transition: 'opacity 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                        onMouseLeave={(e) => e.currentTarget.style.opacity = '0.6'}
                        title={`Open ${service.name}`}
                      >
                        <ExternalLink size={14} style={{ color: '#6b7280' }} />
                      </button>
                    )}
                  </div>
                </div>
              );
              })}
            </div>
          </div>

          {/* Metrics */}
          {systemHealth.metrics && (
            <div>
              <h4 style={{ 
                fontSize: '14px', 
                fontWeight: 600,
                color: '#374151',
                marginBottom: '12px'
              }}>
                Metrics
              </h4>
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '8px',
                fontSize: '12px'
              }}>
                <div style={{
                  padding: '8px',
                  background: '#f3f4f6',
                  borderRadius: '6px'
                }}>
                  <div style={{ color: '#6b7280', marginBottom: '2px' }}>Connections</div>
                  <div style={{ fontWeight: 600, color: '#1f2937' }}>
                    {systemHealth.metrics.activeConnections}
                  </div>
                </div>
                <div style={{
                  padding: '8px',
                  background: '#f3f4f6',
                  borderRadius: '6px'
                }}>
                  <div style={{ color: '#6b7280', marginBottom: '2px' }}>Memory</div>
                  <div style={{ fontWeight: 600, color: '#1f2937' }}>
                    {systemHealth.metrics.memoryUsage}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
};

export default SystemMonitor;
