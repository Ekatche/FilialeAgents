# =======================================================
# Dockerfile pour le frontend Next.js
# Version mise à jour avec support WebSocket et affichage des agents
# =======================================================
FROM node:20-alpine AS base

LABEL maintainer="OpenAiAgents Team"
LABEL description="Frontend Next.js avec suivi des agents en temps réel"
LABEL version="2.0.0"
LABEL features="WebSocket client,Real-time agent display,Radix UI Progress"

# Installation des dépendances uniquement si nécessaire
FROM base AS deps
# Vérification de libc6-compat pour Alpine
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copie des fichiers de dépendances et installation
COPY package.json package-lock.json* ./
RUN npm install

# Phase de build
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Variables d'environnement pour le build
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_URL=http://localhost:8012
ENV NEXT_PUBLIC_WS_URL=ws://localhost:8012

# Build de l'application
RUN npm run build

# Phase de production
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public

# Set the correct permission for prerender cache
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Copie automatiquement les fichiers de sortie en utilisant les traces
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3001

ENV PORT=3001
ENV HOSTNAME="0.0.0.0"

# Variables d'environnement pour WebSocket
ENV NEXT_PUBLIC_API_URL=http://localhost:8012
ENV NEXT_PUBLIC_WS_URL=ws://localhost:8012

# Commande de démarrage
CMD ["node", "server.js"]