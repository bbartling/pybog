# Build stage
FROM node:18 as build
WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Build arguments for environment variables
ARG REACT_APP_API_URL=http://localhost:8000
ARG REACT_APP_N8N_URL=http://localhost:5678

# Set environment variables for build
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV REACT_APP_N8N_URL=$REACT_APP_N8N_URL

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy build output
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Generate runtime config at container start via nginx entrypoint hook
# This script will generate /usr/share/nginx/html/config.js using env vars
COPY docker-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
# Normalize line endings and ensure executable
RUN sed -i 's/\r$//' /docker-entrypoint.d/40-runtime-config.sh && chmod +x /docker-entrypoint.d/40-runtime-config.sh

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
