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

# Create runtime config - using environment variables or defaults
RUN echo 'window.RUNTIME_CONFIG = { API_URL: "http://localhost:8765", N8N_URL: "http://localhost:5789" };' > /usr/share/nginx/html/config.js

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
