# Etapa base: dependencias (Angular 22 exige Node 22; ver D-15)
FROM node:22-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci

# Desarrollo: el compose monta ./frontend en /app y un volumen en /app/node_modules.
# El proxy de /api apunta a http://backend:8000 (proxy.conf.docker.json).
FROM base AS dev
COPY . .
EXPOSE 4200
CMD ["npx", "ng", "serve", "--host", "0.0.0.0", "--configuration", "docker", "--poll", "2000"]

# Compilación de producción
FROM base AS build
COPY . .
RUN npx ng build --configuration production

# Producción: nginx sirve la SPA y reenvía /api al backend
FROM nginx:1.27-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/chibchaweb/browser /usr/share/nginx/html
EXPOSE 80
