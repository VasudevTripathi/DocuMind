# Stage 1: Build React SPA
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package specs and install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build argument for backend API URL at build time
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build production bundle
RUN npm run build

# Stage 2: Serve with lightweight Nginx
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
