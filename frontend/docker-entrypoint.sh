#!/bin/sh

# Replace environment variables in the built React app
# This allows runtime configuration without rebuilding

# Create a config file that can be loaded at runtime
cat <<EOF > /usr/share/nginx/html/config.js
window.RUNTIME_CONFIG = {
  API_URL: "${REACT_APP_API_URL:-http://localhost:8000}",
  N8N_URL: "${REACT_APP_N8N_URL:-http://localhost:5678}"
};
EOF

# Execute the command passed to the container
exec "$@"
