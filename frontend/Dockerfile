# Minimal production image: serve prebuilt React app via nginx
# We intentionally avoid a Node build stage because the repo includes build/
# and we want deterministic output matching the committed build.
FROM nginx:alpine

# Copy production build directly
COPY build /usr/share/nginx/html

# Copy nginx site config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Generate runtime config at container start via nginx entrypoint hook
COPY docker-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
RUN sed -i 's/\r$//' /docker-entrypoint.d/40-runtime-config.sh && chmod +x /docker-entrypoint.d/40-runtime-config.sh

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
