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