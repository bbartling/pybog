#!/bin/sh
# Generate runtime config.js for the frontend using environment variables
# Priority: RUNTIME_* > REACT_APP_* > defaults
API="${RUNTIME_API_URL:-${REACT_APP_API_URL:-http://localhost:8000}}"
N8N="${RUNTIME_N8N_URL:-${REACT_APP_N8N_URL:-http://localhost:5678}}"

cat > /usr/share/nginx/html/config.js <<EOF
window.RUNTIME_CONFIG = { API_URL: "${API}", N8N_URL: "${N8N}" };
EOF

