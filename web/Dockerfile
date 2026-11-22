FROM node:20-alpine AS builder

WORKDIR /app
COPY packages/contracts/ts /app/packages/contracts/ts
COPY web/package.json web/package-lock.json /app/web/
WORKDIR /app/web
RUN npm ci

COPY web/ /app/web/

ARG NEXT_PUBLIC_API_BASE=""
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
COPY --from=builder /app/web/.next/standalone ./
COPY --from=builder /app/web/.next/static ./.next/static
COPY --from=builder /app/web/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
