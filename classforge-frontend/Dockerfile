# Etapa 1: Compilación de la aplicación Angular 17
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build -- --configuration production

# Etapa 2: Servidor NGINX para producción
FROM nginx:alpine

COPY --from=build /app/dist/classforge-frontend/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
