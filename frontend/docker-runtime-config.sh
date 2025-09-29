#!/bin/sh
# Generate runtime config.js for the frontend using environment variables
# Priority: RUNTIME_* > REACT_APP_* > defaults
API="${RUNTIME_API_URL:-${REACT_APP_API_URL:-http://localhost:8847}}"
WS="${RUNTIME_WS_URL:-${REACT_APP_WS_URL:-ws://localhost:8847}}"

cat > /usr/share/nginx/html/config.js <<EOF
window.RUNTIME_CONFIG = { 
  API_URL: "${API}",
  WS_URL: "${WS}"
};
EOF

