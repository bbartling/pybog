# Multi-stage build: Build React app with correct environment variables
FROM node:18 AS build

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Set build-time environment variables
ARG REACT_APP_API_URL=http://localhost:8847
ARG REACT_APP_WS_URL=ws://localhost:8847
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV REACT_APP_WS_URL=$REACT_APP_WS_URL

# Build the app
RUN npm run build

# Production stage: serve built app via nginx
FROM nginx:alpine

# Copy built app from build stage
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx site config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Generate runtime config at container start via nginx entrypoint hook
COPY docker-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
RUN sed -i 's/\r$//' /docker-entrypoint.d/40-runtime-config.sh && chmod +x /docker-entrypoint.d/40-runtime-config.sh

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
