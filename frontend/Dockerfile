FROM node:20-bullseye as build

WORKDIR /app

# Increase Node.js memory limit
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Install dependencies first (better layer caching)
COPY package*.json ./
RUN npm install
COPY . .

RUN npm run build

FROM nginx:alpine

# Create a non-root user
RUN adduser -D -H -u 101 -s /sbin/nologin nginx

# Create necessary directories with proper permissions
RUN mkdir -p /var/cache/nginx /var/log/nginx /var/run \
    && chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx \
    && chown -R nginx:nginx /var/run \
    && chown -R nginx:nginx /usr/share/nginx/html \
    && chmod -R 755 /usr/share/nginx/html \
    && chmod -R 755 /var/cache/nginx \
    && chmod -R 755 /var/log/nginx \
    && chmod -R 755 /var/run

WORKDIR /usr/share/nginx/html

# Set default port
ENV PORT=80

# Copy built files and nginx config
COPY --from=build /app/dist .
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Set proper permissions for nginx config
RUN chown nginx:nginx /etc/nginx/conf.d/default.conf \
    && chmod 644 /etc/nginx/conf.d/default.conf

# Switch to non-root user
USER nginx

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"] 