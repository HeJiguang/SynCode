FROM node:22-alpine AS deps

WORKDIR /workspace

COPY frontend/package.json frontend/package-lock.json ./
COPY frontend/apps ./apps
COPY frontend/packages ./packages
COPY frontend/tsconfig.base.json ./tsconfig.base.json

RUN npm ci

FROM deps AS builder

ARG APP_NAME

WORKDIR /workspace

RUN npm run build -w @aioj/${APP_NAME}

FROM node:22-alpine AS runner

ARG APP_NAME

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

WORKDIR /workspace

COPY --from=builder /workspace /workspace

EXPOSE 3000

CMD ["sh", "-c", "npm run start -w @aioj/${APP_NAME} -- --hostname 0.0.0.0 --port 3000"]
