const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Use environment variable for backend URL, fallback to Docker service name
  const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://backend:8000';
  const wsUrl = process.env.REACT_APP_WS_BACKEND_URL || 'ws://backend:8000';
  
  console.log('Setting up proxy to backend:', backendUrl);
  console.log('Setting up WebSocket proxy to:', wsUrl);
  
  app.use(
    '/api',
    createProxyMiddleware({
      target: backendUrl,
      changeOrigin: true,
      logLevel: 'debug',
      onError: (err, req, res) => {
        console.error('Proxy error:', err);
      },
      onProxyReq: (proxyReq, req, res) => {
        console.log('Proxying request:', req.method, req.url);
      }
    })
  );
  
  app.use(
    '/ws',
    createProxyMiddleware({
      target: wsUrl,
      ws: true,
      changeOrigin: true,
      logLevel: 'debug',
      onError: (err, req, res) => {
        console.error('WebSocket proxy error:', err);
      }
    })
  );
};